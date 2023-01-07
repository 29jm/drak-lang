#!/usr/bin/env python3

from __future__ import annotations
from enum import Enum, auto
from typing import List

class I(Enum):
    NODEPS = auto()
    USE = auto()

    def __repr__(self) -> str:
        return str(self.name)

class Node:
    def __init__(self, var, links: set=set()):
        self.var = var
        self.links = links

    def __repr__(self) -> str:
        return f'{self.var} -> {self.links}'

def GEN(sblock):
    if sblock[1] != I.NODEPS:
        return set(sblock[1])
    return set()

def KILL(sblock, suffixes: dict):
    if sblock[0] != I.USE:
        suffixes[sblock[0]] = suffixes.get(sblock[0], 0) + 1
        # if sblock[0] not in suffixes:
        #     suffixes[sblock[0]] = 1
        # else:
        #     suffixes[sblock[0]] = suffixes[sblock[0]] + 1
        return set([sblock[0]])
    return set()

def apply_suffixes(variables: set, suffixes: dict) -> list:
    suffixed = set()
    for var in variables:
        if var in suffixes:
            suffixed.add(f'{var}.{suffixes[var]}')
        else:
            suffixed.add(var)
    return suffixed

def renumber(block: list, suffixes: dict) -> list:
    renumbered = []
    for elem in block:
        if isinstance(elem, str):
            renumbered.append(apply_suffixes(set([elem]), suffixes).pop())
        elif isinstance(elem, list):
            renumbered.append(renumber(elem, suffixes))
        else:
            renumbered.append(elem)
    return renumbered

def rename(block: list, source: str, dest: str) -> list:
    renamed = []
    for elem in block:
        if isinstance(elem, str) and elem == source:
            renamed.append(dest)
        elif isinstance(elem, list):
            renamed.append(rename(elem, source, dest))
        else:
            renamed.append(elem)
    return renamed

def liveness(blocks: list) -> tuple:
    live = set()
    livetimes = []
    suffixes = {}
    renumbered = []

    from copy import copy

    for block in reversed(blocks):
        old_suffixes = copy(suffixes)
        alived = GEN(block)
        killed = KILL(block, suffixes)
        live = (live - killed) | alived
        livetimes.append(apply_suffixes(live, old_suffixes))
        renumbered.append(renumber(block, old_suffixes))
    
    return list(reversed(livetimes)), list(reversed(renumbered))

def interference_graph(liveness: list) -> List[Node]:
    nodes = {}

    vars = set()
    for life in liveness:
        vars |= life
    for var in vars:
        nodes[var] = set()

    for alive_together in liveness:
        for var in alive_together:
            nodes[var] |= alive_together - set([var])
    
    return nodes

def coalesce(blocks: list, lifetimes: list, igraph: dict) -> list:
    for i in range(len(blocks)):
        a, b = blocks[i]
        if a == I.USE or b == I.NODEPS:
            continue
        copy_related = len(b) == 1
        interfere = a in igraph[b[0]]
        if copy_related and not interfere: # Coalesce
            blocks = rename(blocks, a, b[0])
            lifetimes = [set(rename(life, a, b[0])) for life in lifetimes]
    return lifetimes, blocks

def simplify(blocks: list, lifetimes: list) -> list:
    """Deletes:
        - mov a, a
        - mov a, [deps]|nodeps // when a is dead everywhere
    """
    simplified = []
    for block in blocks:
        a, b = block
        if a != I.USE and b != I.NODEPS and len(b) == 1 and a == b[0]:
            continue
        elif a != I.USE and not any(a in life for life in lifetimes):
            continue
        simplified.append(block)
    return simplified

def allocate(blocks: list, variables: set, registers: list) -> list:
    for var in variables:
        reg = registers.pop(0)
        blocks = rename(blocks, var, reg)
    return blocks

asm = [
    [
        ['A', I.NODEPS],
        ['D', I.NODEPS],
        ['B', ['A']],
        ['A', I.NODEPS],
        ['C', ['B', 'D']],
        [I.USE, ['B', 'C']],
    ],
]

if __name__ == '__main__':
    blocks = asm[0]
    length = len(blocks)
    new_length = length
    run = False
    while not run or new_length < length:
        length = len(blocks)
        lifetimes, blocksn = liveness(blocks)
        print('initial blocks: ', blocks)
        print('numbered blocks:', blocksn)
        print('liveness per instruction:', lifetimes)

        igraph = interference_graph(lifetimes)
        lifetimes, coalesced = coalesce(blocksn, lifetimes, igraph)
        simplified = simplify(coalesced, lifetimes)
        print('igraph', igraph)
        print('coalesced:', coalesced)
        print('simplified:', simplified)

        new_length = len(simplified)
        blocks = simplified
        run = True
        print(f'iteration done: lengths {length} -> {new_length}')
    vars = set()
    for lives in lifetimes:
        vars |= lives
    allocated = allocate(blocks, vars, [f'r{i}' for i in range(4, 13)])
    print('allocated:', allocated)