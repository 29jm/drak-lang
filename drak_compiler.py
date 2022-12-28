#!/usr/bin/env python3

from __future__ import annotations
from typing import List, Dict, NamedTuple
from parser_utils import AstNode, TokenId
from drak_parser import parse

Asm = List[str]
Reg = int

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

class Symbol(NamedTuple):
    type: str = ''
    register: int = 0

class FnContext:
    function: str
    unique_counter: int
    free_registers: List[int]
    reg_to_spill: int
    symbols: Dict[str, Symbol]
    functions: List[str]

    def __init__(self, func: str) -> None:
        self.function = func
        self.unique_counter = 0
        self.free_registers = list(range(4, 12))
        self.reg_to_spill = 0
        self.symbols = {} # identifier -> Symbol
        self.functions = {} # func_identifier -> [arg types]

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

def compile_expression(stmt: AstNode, target_reg: Reg, ctx: FnContext, asm: Asm) -> Symbol:
    if stmt.token_id() == TokenId.NUMBER:
        asm.append(f'mov r{target_reg}, #{stmt.token_value()}')
        return 'int'
    elif stmt.token_id() == TokenId.IDENTIFIER:
        if not stmt.token_value() in ctx.get_symbols():
            print("Error, unknown identifier on lhs of assignment")
        src_reg = ctx.reg_for_name(stmt.token_value())
        if src_reg == target_reg:
            return ctx.symbols[stmt.token_value()].type
        asm.append(f'mov r{target_reg}, r{src_reg} // Assigning {stmt.token_value()}')
        return ctx.symbols[stmt.token_value()].type
    elif stmt.token_id() == TokenId.FUNC_CALL:
        fn_name = stmt.token_value()

        if not fn_name in ctx.functions.keys():
            print(f'Error, function {fn_name} called before definition')
        if target_reg == 0:
            print(f'// target reg of {stmt.token_value()} is r0, will fail')

        asm.append(f'push {{r0-r3}} // Spill for call to {fn_name} | free regs: {ctx.free_registers}')

        for i, arg in enumerate(stmt.children):
            ret_reg = ctx.get_free_reg(asm) # TBD type check arguments
            arg_type = compile_expression(arg, ret_reg, ctx, asm)
            asm.append(f'mov r{i}, r{ret_reg}')
            ctx.release_reg(ret_reg, asm)

        asm.append(f'bl {fn_name}')
        asm.append(f'mov r{target_reg}, r0')
        asm.append(f'pop {{r0-r3}} // Unspill after call to {fn_name} | free regs: {ctx.free_registers}')

        return ctx.functions[fn_name][0]

    op = op_map[stmt.token_id()]
    allows_immediates = stmt.token_id() in immediate_ops
    lhs_type = compile_expression(stmt.left(), target_reg, ctx, asm)

    if lhs_type != 'int':
        print('Arihthmetic on non-integers not yet supported')

    if allows_immediates and stmt.right().token_id() == TokenId.NUMBER:
        asm.append(f'{op} r{target_reg}, #{stmt.right().token_value()}')
    else:
        reg = ctx.get_free_reg(asm)
        rhs_type = compile_expression(stmt.right(), reg, ctx, asm)
        asm.append(f'{op} r{target_reg}, r{reg}')
        ctx.release_reg(reg, asm)

    return 'bool' if op in boolean_ops else 'int'

def compile_assignment(stmt: AstNode, ctx: FnContext) -> Asm:
    asm = []

    # Find type of right hand side

    lhs_name = stmt.left().token_value()

    if lhs_name in ctx.get_symbols():
        asm += [f'// Reassigning {lhs_name}']
        reg = ctx.reg_for_name(lhs_name)
    else:
        reg = ctx.get_free_reg(asm)
        ctx.symbols[lhs_name] = Symbol('int', reg)

    rhs = stmt.right()

    if rhs.token_id() == TokenId.NUMBER:
        asm += [f'mov r{reg}, #{rhs.token_value()}']
    else:
        type = compile_expression(rhs, reg, ctx, asm) # TBD type

    return asm

def compile_funcdef(stmt, ctx: FnContext) -> Asm:
    fn_name = stmt.token_value()
    fnctx = FnContext(fn_name)
    num_params = int(stmt.children[0].token_value())
    params = [p.token_value() for p in stmt.children[1:1+num_params]]
    body = stmt.children[1+num_params:]

    if len(params) > 4:
        print("Error, more than 4 parameters is unsupported")

    ctx.functions[fn_name] = ['int'] + ['int' for _ in params] # TBD argtypes + ret type first
    fnctx.functions = ctx.functions.copy()

    asm = [f'{fn_name}:']
    asm += ['push {r4-r12, lr}']

    for i, arg in enumerate(params):
        reg = fnctx.get_free_reg(asm)
        asm += [f'mov r{reg}, r{i} // Saving func param {arg}']
        fnctx.symbols[arg] = Symbol('int', reg)

    for sub_stmt in body:
        asm += compile_statement(sub_stmt, fnctx)

    asm += [f'.{fn_name}_end:',
            'pop {r4-r12, lr}',
            'bx lr']

    return asm

def compile_func_call(stmt: AstNode, ctx: FnContext) -> Asm:
    asm = []
    ret_reg = ctx.get_free_reg(asm)
    _ = compile_expression(stmt, ret_reg, ctx, asm) # TBD, type?
    ctx.release_reg(ret_reg, asm)
    return asm

def compile_if(stmt: AstNode, ctx: FnContext) -> Asm:
    cond = stmt.children[0]
    jump_op = jump_op_map_inversed[cond.token_id()]
    label = f'.{ctx.function}_if_{ctx.get_unique()}'
    asm = []

    scratch_reg = ctx.get_free_reg(asm)
    type = compile_expression(cond, scratch_reg, ctx, asm) # TBD check bool
    ctx.release_reg(scratch_reg, asm)

    asm += [f'{jump_op} {label}']

    for i, sub_stmt in enumerate(stmt.children[1:]):
        if sub_stmt.token_id() == TokenId.ELSE:
            break

        asm += compile_statement(sub_stmt, ctx)

    asm += [f'{label}:']

    for sub_stmt in stmt.children[1+i].children:
        asm += compile_statement(sub_stmt, ctx)

    return asm

def compile_while(stmt: AstNode, ctx: FnContext) -> Asm:
    cond = stmt.children[0]
    jump_op = jump_op_map[cond.token_id()]
    label = f'.{ctx.function}_while_begin_{ctx.get_unique()}'
    label_cond = f'.{ctx.function}_while_cond_{ctx.get_unique()}'
    asm = []

    asm += [f'b {label_cond}']
    asm += [f'{label}:']

    for sub_stmt in stmt.children[1:]:
        asm += compile_statement(sub_stmt, ctx)

    asm += [f'{label_cond}:']
    scratch_reg = ctx.get_free_reg(asm)
    type = compile_expression(cond, scratch_reg, ctx, asm) # TBD type bool
    ctx.release_reg(scratch_reg, asm)
    asm += [f'{jump_op} {label}']

    return asm

def compile_statement(stmt: AstNode, ctx: FnContext) -> Asm:
    asm = []

    if stmt.token_id() == TokenId.ASSIGN:
        asm += compile_assignment(stmt, ctx)
    elif stmt.token_id() == TokenId.FN_DEF:
        asm += compile_funcdef(stmt, ctx)
    elif stmt.token_id() == TokenId.FUNC_CALL:
        asm += compile_func_call(stmt, ctx)
    elif stmt.token_id() == TokenId.IF:
        asm += compile_if(stmt, ctx)
    elif stmt.token_id() == TokenId.WHILE:
        asm += compile_while(stmt, ctx)
    elif stmt.token_id() == TokenId.RETURN:
        ret_reg = ctx.get_free_reg(asm)
        type = compile_expression(stmt.children[0], ret_reg, ctx, asm) # TBD type rval
        asm += [f'mov r0, r{ret_reg}']
        asm += [f'b .{ctx.function}_end']
        ctx.release_reg(ret_reg, asm)

    return asm

def compile(prog: List[AstNode]) -> Asm:
    ctx = FnContext('_start')
    ctx.functions['print_char'] = ['int']
    asm = asm_prolog

    for stmt in prog:
        asm += compile_statement(stmt, ctx)

    return asm

def compile_to_asm(prog: List[AstNode]) -> str:
    return __raw_printer(compile(prog))

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
    return '\n'.join(_indent(line) for line in asm) + '\n'

if __name__ == '__main__':
    from sys import argv

    if len(argv) > 1:
        src = open(argv[1], 'r').read()
        toks = parse(src)
        asm = compile(toks)
        print(__raw_printer(asm, strip_comments=False))