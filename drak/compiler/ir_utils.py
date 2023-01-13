from __future__ import annotations
from typing import List, Dict, Set
import itertools
import copy
import re

# Intermediate representation of an instruction, e.g. ['mov', 'REG4', '#40']
# A basic block has type List[Instr].
# Note: basic blocks are groups of sequential instructions containing no jumps,
#       except possibly for the last instruction in the block.
Instr = List[str]

# Interference graph: links variables that are live together at any point in a
# basic block.
LiveSet = Set[str]
IGraph = Dict[str, LiveSet]

# Live variables at each step in a basic block.
BLives = List[LiveSet]

def vars_in(operands: List[str]) -> list:
    nonlit = []
    for op in operands:
        if isinstance(op, str) and op.startswith('REG'):
            nonlit.append(op)
        elif isinstance(op, list):
            nonlit.extend(vars_in(op))
    return nonlit

def vars_read_by(instr: Instr) -> List[str]:
    """Returns registers read by @instr."""
    if instr[0] in ['cmp', 'push', 'jmp'] or instr[0].startswith('b'):
        return vars_in(instr[1:])
    elif instr[0] in ['add', 'sub', 'mul', 'div', 'sdiv']:
        if len(instr[1:]) == 2:
            return vars_in(instr[1:])
        elif len(instr[1:]) == 3:
            return vars_in(instr[2:])
    elif instr[0] == 'str':
        return vars_in(instr[1:2])
    return vars_in(instr[2:])

def vars_written_by(instr: Instr) -> List[str]:
    """Returns registers written to by @instr."""
    if instr[0] in ['cmp', 'push']:
        return []
    elif instr[0] == 'pop':
        return vars_in(instr[1:])
    elif instr[0] == 'str':
        return vars_in(instr[2:])
    return vars_in(instr[1:2])

def is_copy_instruction(instr: Instr) -> bool:
    inputs = len(vars_read_by(instr))
    outputs = len(vars_written_by(instr))
    return instr[0].startswith('mov') and inputs == 1 and outputs == 1

def is_conditional_jump(instr: Instr) -> bool:
    suffixes = ['eq', 'ne', 'lt', 'le', 'gt', 'ge', 'hs', 'ls']
    return any(instr[0] == 'b'+cond for cond in suffixes)

def is_jumping(instr: Instr) -> bool:
    jumps = ['b', 'bx', 'blx', 'bl']
    return instr[0] in jumps or is_conditional_jump(instr)

def block_successors(bblocks: List[List[Instr]], block_no: int) -> List[int]:
    """Returns the block indices of the successors of block `block_no`.
    By convention, instruction -1 will represent return from function."""
    instr = bblocks[block_no][-1]
    if not is_jumping(instr): # Execution moves to next block
        return [block_no + 1]
    elif instr[0] == 'bx': # Return from function
        return [-1]
    else: # Jump to label, conditional or not
        is_conditional = is_conditional_jump(instr)
        target_label = instr[1]
        for i, block in enumerate(bblocks): # Search for blocks starting with `target_label`
            lead_instr = block[0]
            if ':' in lead_instr[0] and lead_instr[0].split(':')[0] == target_label:
                if is_conditional:
                    return [i, block_no + 1]
                return [i]
    print('Error, successor(s) not found')

def basic_blocks(func_block: List[Instr]) -> List[List[Instr]]:
    """Cuts up a function into basic blocks."""
    leader_indices: List[int] = [0]
    blocks: List[List[Instr]] = []

    # Compute leaders
    for i, instr in enumerate(func_block):
        # First instruction is a leader (already included)
        if i == 0:
            pass
        # Targets of a jump are leaders
        elif re.match(r'\.[a-zA-Z0-9_]+:', instr[0]):
            leader_indices.append(i)
        # Instructions following jumps are leaders
        elif is_jumping(func_block[i-1]):
            leader_indices.append(i)

    # Build blocks
    for i in range(len(leader_indices) - 1):
        l, next_l = leader_indices[i], leader_indices[i + 1]
        blocks.append(func_block[l:next_l])
    blocks.append(func_block[leader_indices[-1]:])

    return blocks

def control_flow_graph(bblocks: List[List[Instr]]) -> Dict[int, Set[int]]:
    """Computes the control flow graph of `bblocks`, represented by a dictionary
    from block index to successor block indices.
    The first block in the graph has index zero. Successor indices of -1 represent
    function returns."""
    graph: Dict[int, Set[int]] = {}
    for i in range(len(bblocks)):
        successors = block_successors(bblocks, i)
        graph[i] = set(successors)
    return graph

def print_cfg_as_dot(cfg: Dict[int, Set[int]], bblocks) -> str:
    def print_block(bblock) -> str:
        return "\\l".join(" ".join(str(op) for op in instr) for instr in bblock) + "\\l"
    dot = "digraph G {\n"
    for b, succ in cfg.items():
        dot += f'\t{b} [label="{print_block(bblocks[b])}",xlabel={b},shape=box]\n'
        dot += f"\t{b} -> {', '.join(str(s) for s in succ)}\n"
    return dot + "}\n"

def predecessors(cfg: Dict[int, Set[int]], block: int) -> Set[int]:
    preds = set()
    for maybe_pred, successors in cfg.items():
        if block in successors:
            preds.add(maybe_pred)
    return preds

def dominator_sets(cfg: Dict[int, Set[int]]) -> Dict[int, Set[int]]:
    N = set(cfg.keys())
    root = set([0])
    doms = {0: root} # CFG root dominates itself
    doms.update({block_idx: N for block_idx in N - root})
    updated = True # Make up for the lack of do-while loops

    while updated:
        updated = False
        for blockn in N - root:
            T = N
            for blockp in predecessors(cfg, blockn):
                T = T & doms[blockp]
            D = T | set([blockn])
            if D != doms[blockn]:
                doms[blockn] = D
                updated = True
    return doms

def immediate_dominators(cfg: Dict[int, Set[int]]) -> Dict[int, int]:
    idoms = {n: s - set([n]) for n, s in dominator_sets(cfg).items()}
    non_roots = set(cfg.keys()) - set([0])
    for n in non_roots:
        to_delete = set()
        for s, t in itertools.permutations(idoms[n], 2):
            if t in idoms[s]:
                to_delete.add(t)
        idoms[n].difference_update(to_delete)
    return {n: idoms[n].pop() for n in non_roots}

def dominance_frontier(cfg: Dict[int, Set[int]]) -> Dict[int, Set[int]]:
    idoms = immediate_dominators(cfg)
    df: Dict[int, Set[int]] = {n: set() for n in cfg.keys()}
    for n in cfg.keys():
        preds = predecessors(cfg, n)
        if len(preds) >= 2:
            for preds in preds:
                runner = preds
                while runner != idoms[n]:
                    df[runner].add(n)
                    runner = idoms[runner]
    return df

def definitions_in_block(bblock: List[Instr]) -> Set[str]:
    defs = set()
    for instr in bblock:
        for var in vars_written_by(instr):
            defs.add(var)
    return defs

def phi_insertion(bblocks: List[List[Instr]], df: Dict[int, Set[int]]) -> List[List[Instr]]:
    Aorig: Dict[int, Set[str]] = {}
    Aphi: Dict[int, Set[var]] = {n: set() for n in range(len(bblocks))}
    defsites: Dict[str, Set[int]] = {}
    for n in range(len(bblocks)):
        Aorig[n] = definitions_in_block(bblocks[n])
        for var in Aorig[n]:
            if not var in defsites:
                defsites[var] = set([n])
            else:
                defsites[var].add(n)
    for var in defsites.keys():
        W = copy.deepcopy(defsites[var])
        while W:
            n = W.pop()
            for block_y in df[n]:
                if var not in Aphi[block_y]:
                    bblocks[block_y].insert(0, ['mov', var, f'PHI TBD'])
                    Aphi[block_y].add(var)
                    if var in Aorig[block_y]:
                        W.add(block_y)
    return bblocks