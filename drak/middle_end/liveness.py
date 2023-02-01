#!/usr/bin/env python3

from __future__ import annotations
from functools import reduce
from typing import List, Tuple, Set, Dict
from drak.middle_end.ir_utils import *
from drak.middle_end.graph_ops import predecessors

def GEN(instr: Instr) -> Set[str]:
    return set(vars_read_by(instr))

def KILL(instr: Instr) -> Set[str]:
    return set(vars_written_by(instr))

def apply_suffixes(variables: LiveSet, suffixes: Dict[str, int]) -> list:
    suffixed: Set[str] = set()
    for var in variables:
        if var in suffixes:
            suffixed.add(f'{var}.{suffixes[var]}')
        else:
            suffixed.add(var)
    return suffixed

def renumber(instr: Instr, src: str, dst: str) -> Instr:
    renumbered = []
    for elem in instr:
        if isinstance(elem, str):
            if elem == src:
                renumbered.append(dst)
            else:
                renumbered.append(elem)
        elif isinstance(elem, list):
            renumbered.append(renumber(elem, src, dst))
        else:
            renumbered.append(elem)
    return renumbered

def rename(block: List[Instr]|Instr, source: str, dest: str) -> List[Instr]:
    renamed: List[Instr] = []
    for elem in block:
        if isinstance(elem, str) and elem == source:
            renamed.append(dest)
        elif isinstance(elem, list):
            renamed.append(rename(elem, source, dest))
        else:
            renamed.append(elem)
    return renamed

def liveness(blocks: List[Instr], out_live: Set[str]=set()) -> List[Set[str]]:
    """For a basic block in SSA form, computes live variables at each instruction,
       assuming `out_live` variables are known to be alive in the next block
       in execution order.
       Essentially propagates lifetime information backwards in the CFG.
    """
    live: Set[str] = out_live
    livetimes: List[Set[str]] = []

    for block in reversed(blocks):
        alived = GEN(block)
        killed = KILL(block)
        live = (live - killed) | alived
        livetimes.append(live)

    return list(reversed(livetimes))

def block_liveness(bblocks: List[List[Instr]], cfg: BGraph) -> Dict[int, Set[str]]:
    """Computes a Block -> {alive at block entrance} map."""
    def comp(block, comp_lifetimes: Dict[int, Set[str]], edges_visited: set) -> Dict[int, Set[str]]:
        for pred in predecessors(cfg, block):
            if (block, pred) in edges_visited:
                continue
            edges_visited.add((block, pred))
            alive_in_prev = liveness(bblocks[pred], comp_lifetimes[block])[0]
            if alive_in_prev != comp_lifetimes[pred]:
                # added = alive_in_prev - comp_lifetimes[pred]
                comp_lifetimes[pred] |= alive_in_prev
                # Mark ancestors of `pred` as "to-revisit", in case new lives propagate there
                arcs = [(pred, pp) for pp in predecessors(cfg, pred)
                    if (pred, pp) in edges_visited]
                edges_visited.difference_update(arcs)
                # for arc in arcs:
                #     if any(var not in comp_lifetimes[arc[1]] for var in added):
                #         edges_visited.remove(arc)
            new_life = comp(pred, comp_lifetimes, edges_visited)
            for b, lives in new_life.items():
                comp_lifetimes[b] |= lives
        return comp_lifetimes

    life = {n: set() for n in cfg.keys()}
    edges_visited: Set[Tuple[int, int]] = set()

    return comp(len(bblocks) - 1, life, edges_visited)

def block_liveness2(bblocks: List[List[Instr]], cfg: BGraph) -> Set[int, Set[str]]:
    worklist = set(cfg.keys())
    in_states = {n: set() for n in cfg.keys()}

    while worklist:
        block = worklist.pop()

        # Compute live vars at block exit: in_states of successors
        out_state = set()
        for succ in cfg[block]:
            out_state |= in_states[succ]

        # Compute any vars that came alive, any var killed
        alive = liveness(bblocks[block], out_state)[0]
        if alive != in_states[block]:
            in_states[block] = alive
            worklist.update(predecessors(cfg, block))

    return in_states


def coalesce(bblocks: List[Instr], igraph: Dict[str, Set[str]]) -> List[List[Instr]]:
    """Coalesce copies that don't interfere."""
    for n in range(len(bblocks)):
        i = 0
        while i < len(bblocks[n]):
            instr = bblocks[n][i]
            written, read = vars_written_by(instr), vars_read_by(instr)

            if not written or not read:
                i += 1
                continue

            copy_related = is_copy_instruction(instr)
            interfere = len(written) == 1 and written[0] in igraph[read[0]]
            fixed_register = len(written) == 1 and written[0].startswith('REGF')
            same = copy_related and written[0] == read[0]

            if same:
                bblocks[n].pop(i)
            elif copy_related and not interfere and not fixed_register: # Coalesce
                # print(f"Coalescing {written[0]} into {read[0]}")
                bblocks = rename(bblocks, written[0], read[0]) # Rename things right
                bblocks[n].pop(i)
            else:
                i += 1

    return bblocks

def interference_graph(bblocks: List[List[Instr]], cfg: BGraph) -> Dict[str, Set[str]]:
    def make_graph(lifetimes: List[Set[str]]) -> Dict[str, Set[str]]:
        nodes: Dict[str, Set[str]] = {}
        for var in reduce(lambda a, b: a | b, lifetimes):
            nodes[var] = set()
        for alive_together in lifetimes:
            for var in alive_together:
                nodes[var] |= alive_together - set([var])
        return nodes

    # Compute global lifetimes knowledge
    glob_lifetimes = block_liveness2(bblocks, cfg)

    # Compute local lifetimes knowledge, aided by the global one
    in_block_lifetimes: List[Set[str]] = []
    for n, block in enumerate(bblocks):
        out_live = set()
        for succ in cfg[n]:
            out_live |= glob_lifetimes[succ]
        in_block_lifetimes.extend(liveness(block, out_live))

    return make_graph(in_block_lifetimes)

def optimize_lifetimes(bblocks: List[List[Instr]], cfg: BGraph) -> List[List[Instr]]:
    igraph = interference_graph(bblocks, cfg)

    return coalesce(bblocks, igraph)