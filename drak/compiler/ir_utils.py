from __future__ import annotations
from typing import List, Dict, Set
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