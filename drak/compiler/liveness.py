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
    return set(READREGS(sblock))

def KILL(sblock, suffixes: dict):
    written = WRITREGS(sblock)
    for writ in written:
        suffixes[writ] = suffixes.get(writ, 0) + 1
    return set(written)

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
        a, b = WRITREGS(blocks[i]), READREGS(blocks[i])
        if not a or not b: # Either no write or no read
            continue
        copy_related = blocks[i][0] == 'mov' and len(b) == 1
        interfere = len(a) == 1 and a[0] in igraph[b[0]]
        if copy_related and not interfere: # Coalesce
            blocks = rename(blocks, a[0], b[0])
            lifetimes = [set(rename(life, a[0], b[0])) for life in lifetimes]
    return lifetimes, blocks

def simplify(blocks: list, lifetimes: list) -> list:
    """Deletes:
        - mov a, a
        - movlike a, [deps]|nodeps // when a is dead everywhere
    """
    simplified = []
    for block in blocks:
        a, b = WRITREGS(block), READREGS(block)
        if block[0] == 'mov' and a and b and len(b) == 1 and len(a) == 1 and a[0] == b[0]:
            continue
        elif a and len(a) == 1 and not any(a[0] in life for life in lifetimes):
            continue
        simplified.append(block)
    return simplified

def allocate(blocks: list, variables: set, registers: list) -> list:
    for var in variables:
        reg = registers.pop(0)
        blocks = rename(blocks, var, reg)
    return blocks

def _all_non_litteral(operands: list) -> list:
    nonlit = []
    for op in operands:
        if isinstance(op, str) and op.startswith('REG'):
            nonlit.append(op)
        elif isinstance(op, list):
            nonlit.extend(_all_non_litteral(op))
    return nonlit

def READREGS(instr) -> list:
    """Returns registers read by @instr."""
    if instr[0] in ['cmp', 'push', 'jmp'] or instr[0].startswith('b'):
        return _all_non_litteral(instr[1:])
    elif instr[0] == 'str':
        return _all_non_litteral(instr[1:2])
    return _all_non_litteral(instr[2:])

def WRITREGS(instr) -> list:
    """Returns registers written to by @instr."""
    if instr[0] == 'cmp':
        return []
    elif instr[0] == 'pop':
        return _all_non_litteral(instr[1:])
    elif instr[0] == 'str':
        return _all_non_litteral(instr[2:])
    return _all_non_litteral(instr[1:2])

asm = [
    [
        ['A', I.NODEPS],
        ['D', I.NODEPS],
        ['B', ['A']],
        ['A', I.NODEPS],
        ['C', ['B', 'D']],
        [I.USE, ['B', 'C']],
    ],
    [
        ['mov', 'REG4', '#100'],
        ['mov', 'REG7', '#101'],
        ['mov', 'REG5', 'REG4'],
        ['mov', 'REG4', '#110'],
        ['add', 'REG6', 'REG5', 'REG7'],
        ['sub', 'r0', 'REG5', 'REG6'],
    ]
]

if __name__ == '__main__':
    blocks = asm[1]
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