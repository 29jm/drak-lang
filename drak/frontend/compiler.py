#!/usr/bin/env python3

from __future__ import annotations
from typing import List
from drak.frontend.utils import AstNode, TokenId, Token
from drak.frontend.parser import parse

from drak.frontend.structures import *
from drak.frontend.expression import compile_expression
from drak.frontend.idtype import IdType, IntType, BoolType

# Intrinsics
asm_prolog = [
    [
        ['func_def', '_start'],
            ['.global', '_start'],
            ['func_call', 'main'],
            ['mov', 'r7', '#1'],
            ['svc', '#0'], # Exit system call
            ['func_ret', 'r0']
    ],
    [
        ['print_char:'],
            ['push', ['r0', 'r1', 'r2', 'r7']],
            ['mov', 'r7', '#4'], # Syscall number
            ['mov', 'r0', '#1'], # stdout, hopefully
            ['mov', 'r1', 'sp'], # str address
            ['mov', 'r2', '#1'], # str len
            ['svc', '#0'],
            ['pop', ['r0', 'r1', 'r2', 'r7']],
            ['bx', 'lr']
    ]
]

def compile_assignment(stmt: AstNode, ctx: FnContext) -> Asm:
    asm = []

    lhs = stmt.left()
    lhs_name = lhs.token_value()

    if lhs_name not in ctx.get_symbols():
        print(f'Assigning to undeclared variable {lhs_name}')

    # asm += [f'// Reassigning {lhs_name}']
    lhs_type, reg = ctx.symbols[lhs_name]

    rhs = stmt.right()

    if lhs.children: # LHS has array subscript(s)
        if len(lhs_type.dimensions) != len(lhs.children):
            print("Error, reassigning array, or not enough indices")
        asm.append(['mov', 'r0', '#4']) # We'll use r0 for total index, r1 for partials
        for index_stmt in lhs.children:
            index_type = compile_expression(index_stmt, 1, ctx, asm)
            asm.append(['add', 'r0', 'r0', 'r1'])
        tmp = ctx.get_free_reg(asm)
        rhs_type = compile_expression(rhs, tmp, ctx, asm)
        asm.append(['str', f'REG{tmp}', [f'REG{reg}', 'r0', 'lsl #2']])
        ctx.release_reg(tmp, asm)
    elif lhs_type == IntType and rhs.token_id() == TokenId.NUMBER:
        asm.append(['mov', f'REG{reg}', f'#{rhs.token_value()}'])
    else: # TODO some array assign here, for both LHS and RHS, move what's in decl
        rhs_type = compile_expression(rhs, reg, ctx, asm)
        if lhs_type != rhs_type:
            print(f'Type mismatch in assignment: {lhs_type} in {lhs_name} vs. {rhs_type}')

    return asm

def compile_declaration(stmt: AstNode, ctx: FnContext) -> Asm:
    asm = []
    varname = stmt.token_value()
    vartype = IdType(stmt.children[0].token_value().split('[')[0])
    reg = ctx.get_free_reg(asm)
    tmp = ctx.get_free_reg(asm)
    ctx.symbols[varname] = Symbol(vartype, reg)

    rhs = stmt.children[1]

    if rhs.token_id() == TokenId.ARRAY:
        # Find out the array size
        vartype.dimensions = [len(rhs.children)]
        ctx.symbols[varname].type.dimensions = vartype.dimensions
        array_size = vartype.dimensions[0] * 4 # TODO: type_of_expr function really needed
        # Allocate aligned stack, with room for array size, point it to next empty slot
        aligned = (array_size + (4 + 4) + 7) & ~7
        asm.append(['stackalloc', f'STACKID{reg}', f'#{aligned}'])
        asm.append(['mov', f'REG{tmp}', f'#{array_size}'])
        asm.append(['memstore', f'REG{tmp}', [f'STACKID{reg}', '#0']])

        for i, val in enumerate(rhs.children):
            _ = compile_expression(val, tmp, ctx, asm)
            asm.append(['memstore', f'REG{tmp}', [f'STACKID{reg}', f'#{4*(i+1)}']])
        ctx.release_reg(tmp, asm)
    elif vartype not in [IntType, BoolType]:
        print(f'Error, declaring {vartype}s is not yet supported')
    else:
        assign_node = AstNode(Token(TokenId.ASSIGN), [
            AstNode(Token(TokenId.IDENTIFIER, stmt.token_value())),
            stmt.children[1]])
        asm += compile_assignment(assign_node, ctx) # TODO: hack or nice?

    return asm

def compile_funcdef(stmt, ctx: FnContext) -> Asm:
    fn_name = stmt.token_value()
    fnctx = FnContext(fn_name)
    ret_type = IdType(stmt.children[0].token_value())
    num_params = int(stmt.children[1].token_value())
    typed_params = [(p.token_value(), IdType(p.children[0].token_value()))
                        for p in stmt.children[2:2+num_params]]
    body = stmt.children[2+num_params:]

    if len(typed_params) > 4:
        print("Error, more than 4 parameters is unsupported")

    ctx.functions[fn_name] = [ret_type] + [t[1] for t in typed_params]
    fnctx.functions = ctx.functions.copy()

    asm = [['func_def', fn_name] + [f'REGF{i}' for i in range(len(typed_params))]] # TODO: ugly

    for i, (arg, argtype) in enumerate(typed_params):
        if argtype not in [IntType, BoolType]:
            print(f'Error, cannot handle type {argtype} yet')
        reg = fnctx.get_free_reg(asm)
        asm.append(['mov', f'REG{reg}', f'REGF{i}'])
        fnctx.symbols[arg] = Symbol(argtype, reg)

    for sub_stmt in body:
        asm += compile_statement(sub_stmt, fnctx)

    asm += [[f'.{fn_name}_end:'],
             ['func_ret', 'REGF0']]

    return asm

def compile_func_call(stmt: AstNode, ctx: FnContext) -> Asm:
    asm = []
    _ = compile_expression(stmt, 0, ctx, asm) # TBD, type?
    return asm

def compile_if(stmt: AstNode, ctx: FnContext) -> Asm:
    cond = stmt.children[0]
    jump_op = jump_op_map_inversed[cond.token_id()]
    label = f'.{ctx.function}_if_{ctx.get_unique()}'
    label_end = f'.{ctx.function}_if_post_{ctx.get_unique()}'
    asm = []

    scratch_reg = ctx.get_free_reg(asm)
    lhs_type = compile_expression(cond.left(), scratch_reg, ctx, asm)
    reg = ctx.get_free_reg(asm)
    rhs_type = compile_expression(cond.right(), reg, ctx, asm)
    asm.append([f'cmp', f'REG{scratch_reg}', f'REG{reg}'])
    ctx.release_reg(reg, asm)
    ctx.release_reg(scratch_reg, asm)
    asm.append([f'{jump_op}', f'{label}'])

    for i, sub_stmt in enumerate(stmt.children[1:]):
        if sub_stmt.token_id() == TokenId.ELSE:
            break

        asm += compile_statement(sub_stmt, ctx)

    if stmt.children[1+i].token_id() == TokenId.ELSE:
        asm.append(['b', label_end])
    asm.append([f'{label}:'])

    for sub_stmt in stmt.children[1+i].children:
        asm += compile_statement(sub_stmt, ctx)

    if stmt.children[1+i].token_id() == TokenId.ELSE:
        asm.append([f'{label_end}:'])

    return asm

def compile_while(stmt: AstNode, ctx: FnContext) -> Asm:
    cond = stmt.children[0]
    jump_op = jump_op_map_inversed[cond.token_id()]
    unique = ctx.get_unique()
    label = f'.{ctx.function}_while_begin_{unique}'
    label_end = f'.{ctx.function}_while_post_{unique}'
    asm = []

    asm.append([f'{label}:'])
    scratch_reg = ctx.get_free_reg(asm)
    lhs_type = compile_expression(cond.left(), scratch_reg, ctx, asm)
    reg = ctx.get_free_reg(asm)
    rhs_type = compile_expression(cond.right(), reg, ctx, asm)
    asm.append([f'cmp', f'REG{scratch_reg}', f'REG{reg}'])
    ctx.release_reg(reg, asm)
    ctx.release_reg(scratch_reg, asm)
    asm.append([f'{jump_op}', f'{label_end}'])

    for sub_stmt in stmt.children[1:]:
        asm += compile_statement(sub_stmt, ctx)

    asm.append(['b', f'{label}'])
    asm.append([f'{label_end}:'])

    return asm

def compile_statement(stmt: AstNode, ctx: FnContext) -> Asm:
    asm = []

    if stmt.token_id() == TokenId.DECLARATION:
        asm += compile_declaration(stmt, ctx)
    elif stmt.token_id() == TokenId.ASSIGN:
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
        type = compile_expression(stmt.children[0], ret_reg, ctx, asm)
        asm.append(['mov', 'REGF0', f'REG{ret_reg}'])
        asm.append(['b', f'.{ctx.function}_end'])
        ctx.release_reg(ret_reg, asm)

        if type != ctx.functions[ctx.function][0]:
            print(f'Error, in {ctx.function}, expected return type {ctx.functions[ctx.function][0]}, got {type}')

    return asm

def compile(prog: List[AstNode]) -> List[List[Asm]]:
    ctx = FnContext('_start')
    ctx.functions['print_char'] = [IdType('none'), IntType]
    asm = asm_prolog

    for stmt in prog:
        asm += [compile_statement(stmt, ctx)]

    return asm

if __name__ == '__main__':
    from sys import argv

    if len(argv) > 1:
        src = open(argv[1], 'r').read()
        toks = parse(src)
        asm = compile(toks)
        print(__raw_printer(asm, strip_comments=False))