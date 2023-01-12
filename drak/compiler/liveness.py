#!/usr/bin/env python3

from __future__ import annotations
from functools import reduce
from typing import List, Tuple, Set, Dict
from drak.compiler.ir_utils import *

def GEN(instr: Instr) -> Set[str]:
    return set(vars_read_by(instr))

def KILL(instr: Instr, suffixes: Dict[str, int]) -> Set[str]:
    written = vars_written_by(instr)
    for writ in written:
        suffixes[writ] = suffixes.get(writ, 0) + 1
    return set(written)

def apply_suffixes(variables: LiveSet, suffixes: Dict[str, int]) -> list:
    suffixed: Set[str] = set()
    for var in variables:
        if var in suffixes:
            suffixed.add(f'{var}.{suffixes[var]}')
        else:
            suffixed.add(var)
    return suffixed

def renumber(instr: Instr, suffixes: Dict[str, int]) -> List[str]:
    renumbered = []
    for elem in instr:
        if isinstance(elem, str):
            renumbered.append(apply_suffixes(set([elem]), suffixes).pop())
        elif isinstance(elem, list):
            renumbered.append(renumber(elem, suffixes))
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

def liveness(blocks: List[Instr], in_state: Set[str]=set()) -> Tuple[List[Set[str]], List[Instr]]:
    """For a basic block, computes:
       - The SSA form. This is the same as the input if it is already in SSA form.
       - Live variables at each instruction, assuming `in_state` variables
         are live in the next block (in execution order).
    """
    live: Set[str] = in_state
    livetimes: List[Set[str]] = []
    suffixes: Dict[str, int] = {}
    renumbered: List[Instr] = []

    for block in reversed(blocks):
        old_suffixes = suffixes.copy()
        alived = GEN(block)
        killed = KILL(block, suffixes)
        live = (live - killed) | alived
        livetimes.append(apply_suffixes(live, old_suffixes))
        renumbered.append(renumber(block, old_suffixes))
    
    return list(reversed(livetimes)), list(reversed(renumbered))

def interference_graph(lifetimes: List[Set[str]]) -> Dict[str, Set[str]]:
    nodes: Dict[str, Set[str]] = {}

    # Initialize all nodes to no links
    for var in reduce(lambda a, b: a | b, lifetimes):
        nodes[var] = set()

    # Compute links
    for alive_together in lifetimes:
        for var in alive_together:
            nodes[var] |= alive_together - set([var])
    
    return nodes

def coalesce(blocks: List[Instr], blives: BLives, igraph: IGraph) -> Tuple[BLives, List[Instr]]:
    for i in range(len(blocks)):
        instr = blocks[i]
        written, read = vars_written_by(instr), vars_read_by(instr)
        if not written or not read:
            continue
        copy_related = is_copy_instruction(instr)
        interfere = len(written) == 1 and written[0] in igraph[read[0]]
        if copy_related and not interfere: # Coalesce
            blocks = rename(blocks, written[0], read[0])
            blives = [set(rename(life, written[0], read[0])) for life in blives]
    return blives, blocks

def simplify(blocks: List[Instr], blives: BLives) -> List[Instr]:
    """Deletes:
        - 'movlike a, a'
        - 'movlike a, <whatever>' when a is dead everywhere
    """
    simplified = []
    for block in blocks:
        a, b = vars_written_by(block), vars_read_by(block)
        if block[0] == 'mov' and a and b and len(b) == 1 and len(a) == 1 and a[0] == b[0]:
            continue
        elif a and len(a) == 1 and not any(a[0] in life for life in blives):
            continue
        simplified.append(block)
    return simplified

asm = [
    ['mov', 'REG4', '#100'],
    ['mov', 'REG7', '#101'],
    ['mov', 'REG5', 'REG4'],
    ['mov', 'REG4', '#110'],
    ['add', 'REG6', 'REG5', 'REG7'],
    ['sub', 'r0', 'REG5', 'REG6'],
]

if __name__ == '__main__':
    pass