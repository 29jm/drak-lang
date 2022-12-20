#!/usr/bin/env python3

from __future__ import annotations
from typing import List, Tuple
from parser_utils import AstNode, TokenId
from drak_parser import parse

Symbol = str
Instruction = str
Reg = str

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
jump_op_map = {
    TokenId.OP_EQ: 'bne',
    TokenId.OP_NEQ: 'beq',
    TokenId.OP_GT: 'ble',
    TokenId.OP_LT: 'bge'
}

# Intrinsics
asm_prolog = """
    .global _start
    _start:
    bl main
    mov r7, #1
    svc #0
    print_char:
        push {r0, r1, r2, r7}
        mov r7, #4 // Syscall number
        mov r0, #1 // stdout, hopefully
        mov r1, sp // str address
        mov r2, #1 // str len
        svc #0
        pop {r0, r1, r2, r7}
        bx lr
""".strip().splitlines()

class FnContext:
    def __init__(self, func: str) -> None:
        self.vars = {}
        self.function = func
        self.unique_counter = 0
        self.free_registers = [f'r{n}' for n in range(4, 12)]
        self.register_map = {}

    def get_free_reg(self) -> str:
        return self.free_registers.pop(0)

    def release_reg(self, reg: Reg):
        if int(reg[1]) > 3: # Don't put arg registers in the pool
            self.free_registers.append(reg)

    def reassign_reg(self, reg: Reg, new_reg: Reg = None) -> List[Instruction]:
        if not reg in self.register_map:
            return ['// nothing to reassign']
            print("Error, reassigning unused register, weird")
        if not new_reg:
            new_reg = self.get_free_reg()
        self.register_map[new_reg] = self.register_map[reg] # Copy mapping
        del self.register_map[reg] # Remove previous mapping
        return [f'mov {new_reg}, {reg} // reassigned {reg} to {new_reg}']

    def reg_for_name(self, name: str) -> Reg:
        for k, v in self.register_map.items():
            if v == name:
                return k
        print(f"Error, {name} not mapped")

    def get_unique(self) -> int:
        self.unique_counter += 1
        return self.unique_counter

def compile_expression(stmt: AstNode, target_reg: str, ctx: FnContext) -> List[Instruction]:
    asm = []

    if stmt.token_id() == TokenId.NUMBER:
        return [f'mov {target_reg}, #{stmt.token_value()}']
    elif stmt.token_id() == TokenId.IDENTIFIER:
        if not stmt.token_value() in ctx.register_map.values():
            print("Error, unknown identifier on lhs of assignment")
        src_reg = ctx.reg_for_name(stmt.token_value())
        if src_reg == target_reg:
            return []
        return [f'mov {target_reg}, {src_reg}']
    elif stmt.token_id() == TokenId.FUNC_CALL:
        n_params = len(stmt.children)
        spill_asm, spill_list = None, []

        if n_params == 1:
            spill_asm, spill_list = 'r0', ['r0']
        elif n_params > 1:
            spill_asm, spill_list = f'r0-r{n_params-1}', [f'r{n}' for n in range(n_params)]

        if spill_asm:
            asm += [f'push {{{spill_asm}}}'] # Spill param registers
            # for reg in spill_list:
            #     asm += ctx.reassign_reg(reg)

        for i, arg in enumerate(stmt.children):
            asm += compile_expression(arg, f'r{i}', ctx)

        asm += [f'bl {stmt.token_value()}']

        if spill_asm:
            asm += [f'pop {{{spill_asm}}}'] # Unspill param registers

        return asm

    op = op_map[stmt.token_id()]
    allows_immediates = stmt.token_id() in immediate_ops

    asm = compile_expression(stmt.left(), target_reg, ctx)

    if allows_immediates and stmt.right().token_id() == TokenId.NUMBER:
        rhs = f'#{stmt.right().token_value()}'
    else:
        rhs = ctx.get_free_reg()
        asm += compile_expression(stmt.right(), rhs, ctx)
        ctx.release_reg(rhs)

    asm += [f'{op} {target_reg}, {rhs}']

    return asm

def compile_assignment(stmt: AstNode, ctx: FnContext) -> List[Instruction]:
    reg = ctx.get_free_reg()
    rhs = stmt.right()
    asm = []

    if rhs.token_id() == TokenId.NUMBER:
        asm += [f'mov {reg}, #{rhs.token_value()}']
    else:
        asm += compile_expression(rhs, reg, ctx)

    ctx.register_map[reg] = stmt.left().token_value()

    return asm

def compile_funcdef(stmt, ctx: FnContext) -> List[Instruction]:
    fn_name = stmt.token_value()
    num_params = int(stmt.children[0].token_value())
    params = [p.token_value() for p in stmt.children[1:1+num_params]]
    body = stmt.children[1+num_params:]

    if len(params) > 4:
        print("Error, more than 4 parameters is unsupported")

    fnctx = FnContext(fn_name)
    fnctx.register_map.update({reg: arg
        for (reg, arg) in zip(['r0', 'r1', 'r2', 'r3'], params)})

    asm = []
    asm += [f'{fn_name}:']
    asm += ['push {r4-r12, lr}']
    for sub_stmt in body:
        asm += compile_statement(sub_stmt, fnctx)

    asm += [f'.{fn_name}_end:',
            'pop {r4-r12, lr}',
            'bx lr']

    return asm

def compile_func_call(stmt: AstNode, ctx: FnContext) -> List[Instruction]:
    return compile_expression(stmt, 'r0', ctx)

def compile_if(stmt: AstNode, ctx: FnContext) -> List[Instruction]:
    cond = stmt.children[0]
    jump_op = jump_op_map[cond.token_id()]
    label = f'.{ctx.function}_{ctx.get_unique()}'

    scratch_reg = ctx.get_free_reg()
    asm = compile_expression(cond, scratch_reg, ctx)
    ctx.release_reg(scratch_reg)

    asm += [f'{jump_op} {label}']

    for sub_stmt in stmt.children[1:]:
        asm += compile_statement(sub_stmt, ctx)

    asm += [f'{label}:']

    return asm

def compile_statement(stmt: AstNode, ctx: FnContext) -> List[Instruction]:
    asm = []

    if stmt.token_id() == TokenId.ASSIGN:
        asm += compile_assignment(stmt, ctx)
    elif stmt.token_id() == TokenId.FN_DEF:
        asm += compile_funcdef(stmt, ctx)
    elif stmt.token_id() == TokenId.FUNC_CALL:
        asm += compile_func_call(stmt, ctx)
    elif stmt.token_id() == TokenId.IF:
        asm += compile_if(stmt, ctx)
    elif stmt.token_id() == TokenId.RETURN:
        asm += compile_expression(stmt.children[0], 'r0', ctx)
        asm += [f'b .{ctx.function}_end']

    return asm

def compile(prog: List[AstNode]) -> List[Instruction]:
    ctx = FnContext('_start')
    asm = asm_prolog

    for stmt in prog:
        asm += compile_statement(stmt, ctx)

    return asm

def __inline_asm_printer(asm) -> str:
    header = "__asm__ volatile ("
    body = '\n'.join(f"\"{line}\\n\"" for line in asm)
    footer = ");"
    return header + body + footer

def __raw_printer(asm) -> str:
    def _indent(line: str) -> str:
        ls = line.strip()
        if not ls.endswith(':') and not ls.startswith('.'):
            return '    ' + ls
        return ls
    return '\n'.join(_indent(line) for line in asm)

if __name__ == '__main__':
    from sys import argv

    if len(argv) > 1:
        src = open(argv[1], 'r').read()
        toks = parse(src)
        asm = compile(toks)
        print(__raw_printer(asm))