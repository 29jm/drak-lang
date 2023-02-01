from typing import Dict, List, Set
from functools import reduce
from drak.middle_end.ir_utils import *
from drak.middle_end.graph_ops import *
from drak.middle_end.liveness import block_liveness2

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

def phi_insertion(bblocks: List[List[Instr]], cfg: BGraph, lifetimes: Dict[int, Set[str]]) -> List[List[Instr]]:
    """Inserts phi functions into the basic blocks of a function, with correct number
    of arguments, given the control flow graph, its dominance frontier and the
    live ranges of variables live across blocks.
    """
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
    df = dominance_frontier(cfg)
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

def renumber_variables(bblocks: List[List[Instr]], cfg: BGraph) -> List[List[Instr]]:
    def noprefix(var: str) -> str:
        return var.split('.')[0]

    def rename(block):
        for i, instr in enumerate(bblocks[block]):
            if not 'PHI' in instr[0]:
                for var in vars_read_by(instr):
                    if is_fixed_alloc_variable(var):
                        continue
                    varidx = stacks[noprefix(var)][-1]
                    bblocks[block][i] = renumber_read(instr, var, f'{var}.{varidx}')
            for var in vars_written_by(instr):
                if is_fixed_alloc_variable(var):
                    continue
                counts[noprefix(var)] += 1
                varidx = counts[noprefix(var)]
                stacks[noprefix(var)].append(varidx)
                renumber_written(bblocks[block][i], var, f'{var}.{varidx}')
        for i, succ in enumerate(cfg[block]):
            for j, instr in enumerate(bblocks[succ]):
                if not 'PHI' in instr[0]:
                    continue
                pred_no = sorted(predecessors(cfg, succ)).index(block)
                phi_arg = instr[1]

                if is_fixed_alloc_variable(phi_arg):
                    continue

                idx = stacks[noprefix(phi_arg)][-1]
                bblocks[succ][j][2][pred_no] = f'{noprefix(phi_arg)}.{idx}'
        for child in domtree[block]:
            rename(child)
        for instr in bblocks[block]:
            for var in vars_written_by(instr):
                if is_fixed_alloc_variable(var):
                    continue
                stacks[noprefix(var)].pop()
        return bblocks

    domtree = dominator_tree(cfg)
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

def ssa(bblocks: List[List[Instr]], cfg: BGraph, lifetimes: BLives=None) -> List[List[Instr]]:
    if lifetimes == None:
        lifetimes = block_liveness2(bblocks, cfg)

    bblocks = phi_insertion(bblocks, cfg, lifetimes)
    bblocks = renumber_variables(bblocks, cfg)
    bblocks = simpliphy(bblocks)

    return bblocks