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
regex_fixed_var = r'REGF(\d+)(\.\d+)?'

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
    if instr[0] in ['cmp', 'push', 'jmp']:
        return indices[1:]
    elif instr[0] in ['add', 'sub', 'mul', 'div', 'sdiv']:
        if len(instr[1:]) == 2:
            return indices[1:]
        elif len(instr[1:]) == 3:
            return indices[2:]
    elif instr[0] == 'str':
        return [1]
    elif instr[0] == 'funcdef':
        return []
    elif instr[0] == 'bx':
        if instr[1] == 'lr' and len(instr) > 2:
            return indices[2:]
        else:
            return indices[1:]
    elif instr[0] == 'bl':
        if len(indices) >= 3:
            return indices[2:3]
        else:
            return []
    return indices[2:]

def ops_written_by(instr: Instr) -> List[int]:
    """Returns the indices in @instr containing operands being written to.
    Indices returned can refer to operands which are lists, in which case it should
    be assumed that all variables in those lists are being written to.
    """
    indices = list(range(len(instr)))
    if instr[0] in ['cmp', 'push']:
        return []
    elif instr[0] == 'pop':
        return indices[1:]
    elif instr[0] == 'str':
        return indices[2:]
    elif instr[0] == 'funcdef':
        return indices[2:]
    elif instr[0] == 'bl':
        if len(indices) >= 4:
            return indices[3:4]
        else:
            return []
    return indices[1:2]

def is_fixed_alloc_variable(var: str) -> bool:
    """Returns whether the variable is fixed to a register."""
    return re.fullmatch(regex_fixed_var, var)

def get_fixed_alloc_register(var: str) -> str:
    """Returns the register allocated to the fixed allocation variable."""
    return 'r' + re.fullmatch(regex_fixed_var, var).group(1)

def vars_read_by(instr: Instr, include_fixed=True) -> List[str]:
    """Returns registers read by @instr."""
    varlist = vars_in(instr[op] for op in ops_read_by(instr))
    if not include_fixed:
        return filter(is_fixed_alloc_variable, varlist)
    return varlist

def vars_written_by(instr: Instr, include_fixed=True) -> List[str]:
    """Returns registers written to by @instr."""
    varlist = vars_in(instr[op] for op in ops_written_by(instr))
    if not include_fixed:
        return filter(is_fixed_alloc_variable, varlist)
    return varlist

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

def block_successors(bblocks: List[List[Instr]], block_no: int) -> Set[int]:
    """Returns the block indices of the successors of block `block_no`.
    By convention, the last block, and maybe deadcode, will have no successor."""
    instr = bblocks[block_no][-1]

    block_labels = []
    for b in bblocks:
        for ins in b:
            if (m := re.match(regex_label, ins[0])):
                block_labels.append(m.group(1))

    if not is_jumping(instr):
        return set([block_no + 1])
    elif instr[0] == 'bx': # Return from function
        return set()
    elif not instr[1] in block_labels:
        return set([block_no + 1])
    else: # Jump to label, conditional or not
        is_conditional = is_conditional_jump(instr)
        target_label = instr[1]
        for i, block in enumerate(bblocks): # Search for blocks starting with `target_label`
            lead_instr = block[0]
            if ':' in lead_instr[0] and lead_instr[0].split(':')[0] == target_label:
                if is_conditional:
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

def definitions_in_block(bblock: List[Instr]) -> Set[str]:
    defs = set()
    for instr in bblock:
        for var in vars_written_by(instr):
            defs.add(var)
    return defs