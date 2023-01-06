#!/usr/bin/env python3

from __future__ import annotations
from enum import Enum, auto
from typing import List

class I(Enum):
    NODEPS = auto()
    USE = auto()

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
        if sblock[0] not in suffixes:
            suffixes[sblock[0]] = 1
        else:
            suffixes[sblock[0]] = suffixes[sblock[0]] + 1
        return set([sblock[0]])
    return set()

def apply_suffixes(variables: set, suffixes: dict) -> list:
    return set(f'{v}_{suffixes.get(v, 1)}' for v in variables)

def renumber(block: list, suffixes: dict) -> list:
    renumbered = []
    for elem in block:
        if isinstance(elem, str):
            renumbered.append(apply_suffixes(elem, suffixes).pop())
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

def liveness(blocks: list) -> list:
    live = set()
    livetimes = []
    suffixes = {}
    renumbered = []

    for block in reversed(blocks):
        new_suffixes = suffixes.copy()
        alived = GEN(block)
        killed = KILL(block, new_suffixes)
        live = (live - killed) | alived
        livetimes.append(apply_suffixes(live, suffixes))
        renumbered.append(renumber(block, suffixes))
        suffixes = new_suffixes
    
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

def coalesce(blocks: list, igraph: dict) -> list:
    for i in range(len(blocks)):
        a, b = blocks[i]
        if a == I.USE or b == I.NODEPS:
            continue
        copy_related = len(b) == 1
        interfere = a in igraph[b[0]]
        if copy_related and not interfere: # Coalesce
            blocks = rename(blocks, a, b[0])
    return blocks

asm = [
    [
        ['A', I.NODEPS],
        ['B', ['A']],
        ['A', I.NODEPS],
        ['C', ['B', 'D']],
        [I.USE, ['B']],
    ],
    # [
    #     [I.C, [I.A, I.B]],
    #     [I.D, I.NODEPS]
    # ],
    # [
    #     [I.C, I.NODEPS],
    #     [I.USE, [I.B, I.D, I.C]]
    # ]
]

if __name__ == '__main__':
    # tree = parse(source)
    # print(tree[0].children[2])
    # compile_func_call(tree[0].children[2])
    blocks = asm[0]
    lifetimes, blocksn = liveness(blocks)
    print(blocks)
    print(blocksn)
    print(lifetimes)
    igraph = interference_graph(lifetimes)
    print(igraph)
    coalesced = coalesce(blocksn, lifetimes, igraph)
    print(coalesced)