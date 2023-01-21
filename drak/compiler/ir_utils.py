from __future__ import annotations
from typing import List, Dict, Set
from functools import reduce
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

# Graphs of basic blocks: Control flow, dominator, etc...
BGraph = Dict[int, Set[int]]

# Live variables at each step in a basic block.
BLives = List[LiveSet]

# Regexes
regex_label = r'(\.?[a-zA-Z0-9_]+):'

def vars_in(operands: List[str]) -> list:
    nonlit = []
    for op in operands:
        if isinstance(op, str) and op.startswith('REG'):
            nonlit.append(op)
        elif isinstance(op, list):
            nonlit.extend(vars_in(op))
    return nonlit

def ops_read_by(instr: Instr) -> List[int]:
    """Returns the indices in @instr containing operands being read."""
    indices = list(range(len(instr)))
    if instr[0] in ['cmp', 'push', 'jmp'] or instr[0].startswith('b'):
        return indices[1:]
    elif instr[0] in ['add', 'sub', 'mul', 'div', 'sdiv']:
        if len(instr[1:]) == 2:
            return indices[1:]
        elif len(instr[1:]) == 3:
            return indices[2:]
    elif instr[0] == 'str':
        return [1]
    return indices[2:]

def ops_written_by(instr: Instr) -> List[int]:
    """Returns the indices in @instr containing operands being written."""
    indices = list(range(len(instr)))
    if instr[0] in ['cmp', 'push']:
        return []
    elif instr[0] == 'pop':
        return indices[1:]
    elif instr[0] == 'str':
        return indices[2:]
    return indices[1:2]

def vars_read_by(instr: Instr) -> List[str]:
    """Returns registers read by @instr."""
    return vars_in(instr[op] for op in ops_read_by(instr))

def vars_written_by(instr: Instr) -> List[str]:
    """Returns registers written to by @instr."""
    return vars_in(instr[op] for op in ops_written_by(instr))

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

def is_local_jump(block: List[Instr], instr: Instr) -> bool:
    """Returns whether the instruction performs a function-local jump, which is not
    a recursive call either.
    """
    if not is_jumping(instr):
        return False

    for ins in block[1:]: # Don't consider first instruction: it's the function label
        if (m := re.match(regex_label, ins[0])):
            if m.group(1) == instr[1]:
                return True

    return False

def block_successors(bblocks: List[List[Instr]], block_no: int) -> List[int]:
    """Returns the block indices of the successors of block `block_no`.
    By convention, instruction -1 will represent return from function."""
    instr = bblocks[block_no][-1]

    block_labels = []
    for b in bblocks:
        for ins in b:
            if (m := re.match(regex_label, ins[0])):
                block_labels.append(m.group(1))
    block_labels.pop(0) # Pop function label

    if not is_jumping(instr):
        return [block_no + 1]
    elif instr[0] == 'bx': # Return from function
        return [-1]
    elif not instr[1] in block_labels:
        return [block_no + 1]
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
        elif re.match(regex_label, instr[0]):
            leader_indices.append(i)
        # Instructions following jumps are leaders
        elif is_local_jump(func_block, func_block[i-1]):
            leader_indices.append(i)

    # Build blocks
    for i in range(len(leader_indices) - 1):
        l, next_l = leader_indices[i], leader_indices[i + 1]
        blocks.append(func_block[l:next_l])
    blocks.append(func_block[leader_indices[-1]:])

    return blocks

def control_flow_graph(bblocks: List[List[Instr]]) -> BGraph:
    """Computes the control flow graph of `bblocks`, represented by a dictionary
    from block index to successor block indices.
    The first block in the graph has index zero. Successor indices of -1 represent
    function returns.
    """
    graph: Dict[int, Set[int]] = {}
    for i in range(len(bblocks)):
        successors = block_successors(bblocks, i)
        graph[i] = set(successors)
    return graph

def print_cfg_as_dot(cfg: BGraph, bblocks, live_vars) -> str:
    def print_block(bblock) -> str:
        return "\\l".join(" ".join(str(op) for op in instr) for instr in bblock) + "\\l"
    dot = "digraph G {\n"
    for b, succ in cfg.items():
        live = ', '.join(v for v in sorted(live_vars[b]))
        dot += f'\t{b} [label="{print_block(bblocks[b])}",xlabel="{b}: {live}",shape=box]\n'
        dot += f"\t{b} -> {', '.join(str(s) for s in succ)}\n"
    return dot + "}\n"

def print_igraph(cfg: Dict[str, Set[str]], colors: Dict[str, str], names=False) -> str:
    dot = "strict graph G {\n"
    for var, connected in cfg.items():
        label = colors[var]
        links = '{' + ', '.join(f'"{v}"' for v in sorted(connected)) + '}'
        if links != '{}':
            if names:
                dot += f'\t"{var}" [label="{label}"]\n'
            else:
                dot += f'\t"{var}" [color="{label}"]\n'
            dot += f'\t"{var}" -- {links}\n'
    return dot + "}\n"

def predecessors(cfg: BGraph, block: int) -> Set[int]:
    preds = set()
    for maybe_pred, successors in cfg.items():
        if block in successors:
            preds.add(maybe_pred)
    return preds

def dominator_sets(cfg: BGraph) -> BGraph:
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

def immediate_dominators(cfg: BGraph) -> Dict[int, int]:
    idoms = {n: s - set([n]) for n, s in dominator_sets(cfg).items()}
    non_roots = set(cfg.keys()) - set([0])
    for n in non_roots:
        to_delete = set()
        for s, t in itertools.permutations(idoms[n], 2):
            if t in idoms[s]:
                to_delete.add(t)
        idoms[n].difference_update(to_delete)
    return {n: idoms[n].pop() for n in non_roots} | {0: set()}

def dominator_tree(idoms: Dict[int, int]) -> BGraph:
    domtree: BGraph = {n: set() for n in idoms.keys()}
    for block in idoms.keys():
        for other in idoms.keys():
            if idoms[other] == block:
                domtree[block].add(other)
    return domtree

def dominance_frontier(cfg: BGraph) -> BGraph:
    idoms = immediate_dominators(cfg)
    df: Dict[int, Set[int]] = {n: set() for n in cfg.keys()}
    for n in cfg.keys():
        preds = predecessors(cfg, n)
        if len(preds) >= 2:
            for pred in preds:
                runner = pred
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

def phi_insertion(bblocks: List[List[Instr]], cfg: BGraph, df: BGraph, lifetimes: Dict[int, Set[str]]) -> List[List[Instr]]:
    # Describes variable assignments, per block
    var_map: Dict[int, Set[str]] = {}
    # Describes existing phi funcs, per block
    phi_map: Dict[int, Set[var]] = {n: set() for n in range(len(bblocks))}
    # Describes blocks where each variable is assigned to
    defsites: Dict[str, Set[int]] = {}
    for n in range(len(bblocks)):
        var_map[n] = definitions_in_block(bblocks[n])
        for var in var_map[n]:
            if not var in defsites:
                defsites[var] = set([n])
            else:
                defsites[var].add(n)
    globs = reduce(lambda x, y: x | y, lifetimes.values(), set())
    for var in set(defsites.keys()) & globs:
        W = defsites[var]
        while W:
            n = W.pop()
            for block_y in df[n]:
                # We don't have a phi function for var in block_y yet, place it
                if var not in phi_map[block_y]:
                    insert_at = 0 if ':' in bblocks[block_y][0] else 1
                    phi_args = [var] * len(predecessors(cfg, block_y))
                    bblocks[block_y].insert(insert_at, ['PHI', var, phi_args])
                    phi_map[block_y].add(var)
                    # We've just added an assignment to `var`: iterate
                    if var not in var_map[block_y]:
                        W.add(block_y)
    return bblocks

def renumber_instr_ops(instr: Instr, ops: List[int], src: str, dst: str) -> Instr:
    for idx in ops:
        if isinstance(instr[idx], list):
            for i, op in enumerate(instr[idx]):
                if op == src:
                    instr[idx][i] = dst
        if instr[idx] == src:
            instr[idx] = dst
    return instr

def renumber_written(instr: Instr, src: str, dst: str) -> Instr:
    return renumber_instr_ops(instr, ops_written_by(instr), src, dst)

def renumber_read(instr: Instr, src: str, dst: str) -> Instr:
    return renumber_instr_ops(instr, ops_read_by(instr), src, dst)

def renumber_variables(bblocks: List[List[Instr]], cfg: BGraph) -> List[List[Instr]]:
    def noprefix(var: str) -> str:
        return var.split('.')[0]

    def rename(block):
        for i, instr in enumerate(bblocks[block]):
            if not 'PHI' in instr[0]:
                for var in vars_read_by(instr):
                    varidx = stacks[var][-1]
                    bblocks[block][i] = renumber_read(instr, var, f'{var}.{varidx}')
            for var in vars_written_by(instr):
                counts[var] += 1
                varidx = counts[var]
                stacks[var].append(varidx)
                renumber_written(bblocks[block][i], var, f'{var}.{varidx}')
        for i, succ in enumerate(cfg[block]):
            for j, instr in enumerate(bblocks[succ]):
                if not 'PHI' in instr[0]:
                    continue
                pred_no = sorted(predecessors(cfg, succ)).index(block)
                phi_arg = instr[1]
                idx = stacks[noprefix(phi_arg)][-1]
                bblocks[succ][j][2][pred_no] = f'{noprefix(phi_arg)}.{idx}'
        for child in domtree[block]:
            rename(child)
        for instr in bblocks[block]:
            for var in vars_written_by(instr):
                stacks[noprefix(var)].pop()
        return bblocks

    domtree = dominator_tree(immediate_dominators(cfg))
    varlist = set()
    counts: Dict[str, int] = {}
    stacks: Dict[str, List[int]] = {}
    for n in cfg.keys():
        varlist |= definitions_in_block(bblocks[n])
    for var in varlist:
        counts[var] = 0
        stacks[var] = []

    return rename(0)

def simpliphy(bblocks: List[List[Instr]]) -> List[List[Instr]]:
    """"Resolves phi functions into the appropriate copy operations.
    Mode of operation:
    For every phi function assignment x_i = φ(x_j, x_j', ...):
        For every argument x_j of φ:
            Let (block, idx) be the block and instruction at which x_j is defined.
            Insert a copy instruction `mov x_i, x_j` after (block, idx).
        Delete the phi function assignment.
    """
    # Gather rough locations of variable definitions
    defs: Dict[str, int] = {}
    for block in range(len(bblocks)):
        for var in definitions_in_block(bblocks[block]):
            defs[var] = block
    # Hunt for phi functions
    for block in bblocks:
        i = 0
        while i < len(block):
            instr = block[i]
            if 'PHI' not in instr[0]:
                i += 1
                continue
            phi_assigned: str = instr[1]
            phi_args: List[str] = instr[2]
            # Insert a copy at the end of the block defining each phi argument
            for phi_arg in phi_args:
                source_block = defs[phi_arg]
                blen = len(bblocks[source_block])
                insert_at = blen - 1 if is_jumping(bblocks[source_block][-1]) else blen
                bblocks[source_block].insert(insert_at, ['mov', phi_assigned, phi_arg])
            # Delete the phi function assignment
            block.pop(i)
            # Intentionally don't increment `i`
    return bblocks