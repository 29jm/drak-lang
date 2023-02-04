from typing import List, Dict, Set
from drak.middle_end.ir_utils import Instr, BGraph
import drak.middle_end.ir_utils as ir_utils
import itertools

def block_successors(bblocks: List[List[Instr]], block_no: int) -> Set[int]:
    """Returns the block indices of the successors of block `block_no`.
    By convention, the last block, and maybe deadcode, will have no successor.
    """
    instr = bblocks[block_no][-1]

    block_labels = []
    for b in bblocks:
        for ins in b:
            if ir_utils.is_jump_label(ins[0]):
                block_labels.append(ir_utils.get_jump_label(ins[0]))

    if not ir_utils.is_jumping(instr):
        return set([block_no + 1])
    elif instr[0] == 'func_ret':
        return set()
    elif not instr[1] in block_labels:
        return set([block_no + 1])
    else: # Jump to label, conditional or not
        target_label = instr[1]
        for i, block in enumerate(bblocks): # Search for blocks starting with `target_label`
            ins = block[0][0] # First part of first instruction of block
            if ir_utils.is_jump_label(ins) and ir_utils.get_jump_label(ins) == target_label:
                if ir_utils.is_conditional_jump(instr):
                    return set([i, block_no + 1])
                return set([i])
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
        elif ir_utils.is_jump_label(instr[0]):
            leader_indices.append(i)
        # Instructions following jumps are leaders
        elif ir_utils.is_local_jump(func_block, func_block[i-1]):
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
    The first block in the graph has index zero. No successors indicate end block.
    """
    graph: Dict[int, Set[int]] = {}
    for i in range(len(bblocks)):
        successors = block_successors(bblocks, i)
        graph[i] = set(successors)
    return graph

def predecessors(cfg: BGraph, block: int) -> Set[int]:
    preds = set()
    for maybe_pred, successors in cfg.items():
        if block in successors:
            preds.add(maybe_pred)
    return preds

def dominator_sets(cfg: BGraph) -> BGraph:
    N = set(cfg.keys())
    root = set([0])
    doms = {0: root} # CFG root dominates itself. Kinky mf.
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

def dominator_tree(cfg: BGraph) -> BGraph:
    idoms = immediate_dominators(cfg)
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

# TODO: move those to some 'presentation' module?
def print_cfg_as_dot(cfg: BGraph, bblocks, live_vars) -> str:
    def print_block(bblock) -> str:
        return "\\l".join(" ".join(str(op) for op in instr) for instr in bblock) + "\\l"
    dot = "digraph G {\n"
    for b, succ in cfg.items():
        live = ', '.join(v for v in sorted(live_vars[b]))
        dot += f'\t{b} [label="{print_block(bblocks[b])}",xlabel="{b}: {live}",shape=box]\n'
        if succ:
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