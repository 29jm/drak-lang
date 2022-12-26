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
        self.free_registers = list(range(4, 12))
        self.register_map = {}
        self.reg_to_spill = 0

    def get_free_reg(self, asm: List[Instruction]) -> str:
        if self.free_registers:
            reg = self.free_registers.pop()
            asm.append(f'// Acquiring r{reg} (free regs: {self.free_registers})')
            return f'r{reg}'
        # We need to spill a register
        to_spill = 4 + (self.reg_to_spill % 8) # Cycles [r4-r11]
        self.reg_to_spill += 1 # Update for next time
        asm.append(f'push {{r{to_spill}}} // Spilling')
        return f'r{to_spill}'

    def release_reg(self, reg: Reg, asm: List[Instruction]):
        if self.reg_to_spill > 0:
            self.reg_to_spill -= 1
            unspill_reg = 4 + (self.reg_to_spill % 8)
            asm.append([f'pop {{r{unspill_reg}}} // Unspilling'])
            return
        asm.append(f'// Releasing {reg}')
        self.free_registers.append(int(reg[1:]))

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
        return [f'mov {target_reg}, {src_reg} // Assigning {stmt.token_value()}']
    elif stmt.token_id() == TokenId.FUNC_CALL:
        asm += [f'push {{r0-r3}} // Spill for call to {stmt.token_value()} | free regs: {ctx.free_registers}']
        for i, arg in enumerate(reversed(stmt.children)):
            ret_reg = ctx.get_free_reg(asm)
            asm += compile_expression(arg, ret_reg, ctx)
            asm += [f'mov r{len(stmt.children) - i - 1}, {ret_reg}']
            ctx.release_reg(ret_reg, asm)
        asm += [f'bl {stmt.token_value()}']
        asm += [f'mov {target_reg}, r0']
        if target_reg == 'r0':
            print(f'target reg of {stmt.token_value()} is r0, will fail')
        asm += [f'pop {{r0-r3}} // Unspill after call to {stmt.token_value()} | free regs: {ctx.free_registers}']
        return asm

    op = op_map[stmt.token_id()]
    allows_immediates = stmt.token_id() in immediate_ops

    asm = compile_expression(stmt.left(), target_reg, ctx)

    if allows_immediates and stmt.right().token_id() == TokenId.NUMBER:
        rhs = f'#{stmt.right().token_value()}'
    else:
        rhs = ctx.get_free_reg(asm)
        asm += compile_expression(stmt.right(), rhs, ctx)
        ctx.release_reg(rhs, asm)

    asm += [f'{op} {target_reg}, {rhs}']

    return asm

def compile_assignment(stmt: AstNode, ctx: FnContext) -> List[Instruction]:
    asm = []
    reg = ctx.get_free_reg(asm)
    rhs = stmt.right()

    if rhs.token_id() == TokenId.NUMBER:
        asm += [f'mov {reg}, #{rhs.token_value()}']
    else:
        asm += compile_expression(rhs, reg, ctx)

    ctx.register_map[reg] = stmt.left().token_value()

    return asm

def compile_funcdef(stmt, ctx: FnContext) -> List[Instruction]:
    fn_name = stmt.token_value()
    fnctx = FnContext(fn_name)
    num_params = int(stmt.children[0].token_value())
    params = [p.token_value() for p in stmt.children[1:1+num_params]]
    body = stmt.children[1+num_params:]

    if len(params) > 4:
        print("Error, more than 4 parameters is unsupported")

    asm = [f'{fn_name}:']
    asm += ['push {r4-r12, lr}']

    for i, arg in enumerate(params):
        reg = fnctx.get_free_reg(asm)
        asm += [f'mov {reg}, r{i} // Saving func param {arg}']
        fnctx.register_map[reg] = arg

    for sub_stmt in body:
        asm += compile_statement(sub_stmt, fnctx)

    asm += [f'.{fn_name}_end:',
            'pop {r4-r12, lr}',
            'bx lr']

    return asm

def compile_func_call(stmt: AstNode, ctx: FnContext) -> List[Instruction]:
    asm = []
    ret_reg = ctx.get_free_reg(asm)
    asm += compile_expression(stmt, ret_reg, ctx)
    ctx.release_reg(ret_reg, asm)
    return asm

def compile_if(stmt: AstNode, ctx: FnContext) -> List[Instruction]:
    cond = stmt.children[0]
    jump_op = jump_op_map[cond.token_id()]
    label = f'.{ctx.function}_{ctx.get_unique()}'
    asm = []

    scratch_reg = ctx.get_free_reg(asm)
    asm += compile_expression(cond, scratch_reg, ctx)
    ctx.release_reg(scratch_reg, asm)

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
        ret_reg = ctx.get_free_reg(asm)
        asm += compile_expression(stmt.children[0], ret_reg, ctx)
        asm += [f'mov r0, {ret_reg}']
        asm += [f'b .{ctx.function}_end']
        ctx.release_reg(ret_reg, asm)

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

def __raw_printer(asm, strip_comments=False) -> str:
    def _indent(line: str) -> str:
        ls = line.strip()
        comment = ls.find('//')
        if strip_comments and comment != -1:
            ls = ls[:comment].strip()
        if ls and not ls.endswith(':') and not ls.startswith('.'):
            return '    ' + ls
        return ls
    asm = (_indent(line) for line in asm)
    asm = [line for line in asm if line.strip() != ""]
    return '\n'.join(_indent(line) for line in asm)

if __name__ == '__main__':
    from sys import argv

    if len(argv) > 1:
        src = open(argv[1], 'r').read()
        toks = parse(src)
        asm = compile(toks)
        print(__raw_printer(asm, strip_comments=False))