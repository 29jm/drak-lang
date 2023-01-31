#!/usr/bin/env python3

from __future__ import annotations
from typing import List
from drak.frontend.utils import AstNode, Token, TokenId
from drak.frontend.parser import parse

op_map = {
    TokenId.OP_PLUS: lambda x, y: x + y,
    TokenId.OP_MINUS: lambda x, y: x - y,
    TokenId.OP_MUL: lambda x, y: x * y,
    TokenId.OP_DIV: lambda x, y: x / y,
    TokenId.OP_EQ: lambda x, y: x == y,
    TokenId.OP_NEQ: lambda x, y: x != y,
    TokenId.OP_GT: lambda x, y: x > y,
    TokenId.OP_LT: lambda x, y: x < y
}

class DrakFunctionContext:
    def __init__(self, func: str) -> None:
        self.pvars = {}
        self.function = func
        self.returning = False
        self.return_value = None
        self.tail_call_opportunity = False

class DrakFunction:
    def __init__(self, name: str, params: List[str], body: List[AstNode]) -> None:
        self.name = name
        self.params = params
        self.body = body

    def __repr__(self) -> str:
        return f"DrakFunction: {self.name}({self.params})"

def interpret_expression(expr: AstNode, ctx: DrakFunctionContext):
    if expr.token_id() == TokenId.NUMBER:
        return int(expr.token_value())
    elif expr.token_id() == TokenId.IDENTIFIER:
        return ctx.pvars[expr.token_value()]
    elif expr.token_id() == TokenId.FUNC_CALL:
        return interpret_func_call(expr, ctx)

    op = op_map[expr.token_id()]
    lhs = interpret_expression(expr.left(), ctx)
    rhs = interpret_expression(expr.right(), ctx)

    return op(lhs, rhs)

def interpret_func_call(func_stmt: AstNode, ctx: DrakFunctionContext):
    if func_stmt.token_value() == 'print':
        args = [interpret_expression(arg, ctx) for arg in func_stmt.children]
        print(*args)
        return
    func = ctx.pvars[func_stmt.token_value()]
    if not isinstance(func, DrakFunction):
        print(f"Error, {func_stmt.token_value()} is not a function")
        return
    if len(func_stmt.children) != len(func.params):
        print(f"Error, wrong number of parameters for call to {func_stmt.token_value()}")
        return
    args = [interpret_expression(arg, ctx) for arg in func_stmt.children]
    fn_ctx = DrakFunctionContext(func_stmt.token_value())
    fn_ctx.pvars = ctx.pvars.copy() # Functions can't affect outer state, but can read/write a copy of it

    for param, arg in zip(func.params, args): # Set parameters to passed argument values
        fn_ctx.pvars[param] = arg

    i = 0
    while i < len(func.body):
        statement = func.body[i]
        interpret_statement(statement, fn_ctx)
        if fn_ctx.tail_call_opportunity:
            func_stmt = statement.children[0]
            args = [interpret_expression(arg, fn_ctx) for arg in func_stmt.children]
            for param, arg in zip(func.params, args): # Set parameters to passed argument values
                fn_ctx.pvars[param] = arg
            fn_ctx.tail_call_opportunity = False
            i = 0
            continue
        if fn_ctx.returning:
            return fn_ctx.return_value
        i += 1

def interpret_statement(statement: AstNode, ctx: DrakFunctionContext):
    if statement.token_id() == TokenId.ASSIGN:
        lhs = statement.left().value
        rhs = interpret_expression(statement.right(), ctx)
        ctx.pvars[lhs] = rhs
    elif statement.token_id() == TokenId.IF:
        cond = interpret_expression(statement.left(), ctx)
        if cond != True:
            return
        for inner_statement in statement.children[1:]:
            interpret_statement(inner_statement, ctx)
    elif statement.token_id() == TokenId.WHILE:
        cond = interpret_expression(statement.left(), ctx)
        while cond:
            for inner_statement in statement.children[1:]:
                interpret_statement(inner_statement, ctx)
            cond = interpret_expression(statement.left(), ctx)
    elif statement.token_id() == TokenId.FN_DEF:
        fn_name = statement.token_value()
        num_params = int(statement.children[0].token_value())
        params = [p.token_value() for p in statement.children[1:1+num_params]]
        body = statement.children[1+num_params:]
        ctx.pvars[fn_name] = DrakFunction(fn_name, params, body)
    elif statement.token_id() == TokenId.FUNC_CALL:
        interpret_func_call(statement, ctx)
    elif statement.token_id() == TokenId.RETURN:
        if len(statement.children) == 1:
            fun = statement.left()
            if fun.token_id() == TokenId.FUNC_CALL and fun.token_value() == ctx.function:
                ctx.tail_call_opportunity = True
                return
        ctx.returning = True
        ctx.return_value = interpret_expression(statement.children[0], ctx)

def interpret_program(program: List[AstNode]):
    ctx = DrakFunctionContext('__start')

    for statement in program:
        interpret_statement(statement, ctx)
    return ctx.pvars

source = """
def fac2(n) {
    def facc(n, acc) {
        print(n);
        if n == 1 { return acc; }
        return facc(n - 1, acc * n);
    }

    return facc(n, 1);
}

print(fac2(400));
"""

if __name__ == '__main__':
    from sys import argv

    if len(argv) > 1:
        filename = argv[1]
        with open(filename, 'r') as fd:
            source = fd.read()
            interpret_program(parse(source))
    else:
        toks = parse(source)
        interpret_program(toks)