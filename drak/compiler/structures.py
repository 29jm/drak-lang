from typing import List, Dict, NamedTuple
from drak.parser.utils import *
from drak.compiler.idtype import IdType

Asm = List[str]
Reg = int

class Symbol(NamedTuple):
    type: IdType
    register: int

class FnContext:
    function: str
    unique_counter: int
    free_registers: List[int]
    reg_to_spill: int
    symbols: Dict[str, Symbol]
    functions: List[str]
    stack_used: int

    def __init__(self, func: str) -> None:
        self.function = func
        self.unique_counter = 0
        self.free_registers = list(range(4, 12))
        self.reg_to_spill = 0
        self.symbols = {} # identifier -> Symbol
        self.functions = {} # func_identifier -> [arg types]
        self.stack_used = 0

    def get_free_reg(self, asm: Asm) -> Reg:
        if self.free_registers:
            reg = self.free_registers.pop()
            asm.append(f'// Acquiring r{reg} (free regs: {self.free_registers})')
            return reg
        # We need to spill a register
        to_spill = 4 + (self.reg_to_spill % 8) # Cycles [r4-r11]
        self.reg_to_spill += 1 # Update for next time
        asm.append(f'push {{r{to_spill}}} // Spilling')
        return to_spill

    def release_reg(self, reg: Reg, asm: Asm):
        if self.reg_to_spill > 0:
            self.reg_to_spill -= 1
            unspill_reg = 4 + (self.reg_to_spill % 8)
            asm.append(f'pop {{r{unspill_reg}}} // Unspilling')
            return
        asm.append(f'// Releasing r{reg}')
        self.free_registers.append(reg)

    def reg_for_name(self, name: str) -> Reg:
        return self.symbols[name].register

    def get_symbols(self):
        return self.symbols.keys()

    def get_unique(self) -> int:
        self.unique_counter += 1
        return self.unique_counter

# Operations that evaluate to a boolean
boolean_ops = [
    TokenId.OP_EQ, TokenId.OP_NEQ,
    TokenId.OP_LT, TokenId.OP_GT
]

# Operations whose implementing instruction allows an immediate RHS
immediate_ops = set(boolean_ops + [
    TokenId.OP_PLUS, TokenId.OP_MINUS
])

# Maps infix operations to implementing instructions
op_map = {
    TokenId.OP_PLUS: 'add',
    TokenId.OP_MINUS: 'sub',
    TokenId.OP_MUL: 'mul',
    TokenId.OP_DIV: 'sdiv',
}

op_map.update({bool_op: 'cmp' for bool_op in boolean_ops})

# Maps a boolean operation to the conditional jump that doesn't jump on True
jump_op_map_inversed = {
    TokenId.OP_EQ: 'bne',
    TokenId.OP_NEQ: 'beq',
    TokenId.OP_GT: 'ble',
    TokenId.OP_LT: 'bge'
}

jump_op_map = {
    TokenId.OP_EQ: 'beq',
    TokenId.OP_NEQ: 'bne',
    TokenId.OP_GT: 'bgt',
    TokenId.OP_LT: 'blt'
}