#!/usr/bin/env python3

from __future__ import annotations
from typing import List
from parser_utils import AstNode, Token, TokenId
from drak_parser import parse

op_map = {
    TokenId.OP_PLUS: lambda x, y: x + y,
    TokenId.OP_MINUS: lambda x, y: x - y,
    TokenId.OP_MUL: lambda x, y: x * y,
    TokenId.OP_DIV: lambda x, y: x / y,
    TokenId.OP_EQ: lambda x, y: x == y,
    TokenId.OP_GT: lambda x, y: x > y,
    TokenId.OP_LT: lambda x, y: x < y
}

class DrakFunction:
    def __init__(self, name: str, params: List[str], body: List[AstNode]) -> None:
        self.name = name
        self.params = params
        self.body = body

def interpret_expression(expr: AstNode, pvars: dict):
    if expr.token_id() == TokenId.NUMBER:
        return int(expr.token_value())
    elif expr.token_id() == TokenId.IDENTIFIER:
        return pvars[expr.token_value()]

    op = op_map[expr.token_id()]
    lhs = interpret_expression(expr.left(), pvars)
    rhs = interpret_expression(expr.right(), pvars)

    return op(lhs, rhs)

def interpret_statement(statement: AstNode, pvars: dict):
    if statement.token_id() == TokenId.ASSIGN:
        lhs = statement.left().value
        rhs = interpret_expression(statement.right(), pvars)
        pvars[lhs] = rhs
    elif statement.token_id() == TokenId.IF:
        cond = interpret_expression(statement.left(), pvars)
        if cond != True:
            return
        for inner_statement in statement.children[1:]:
            interpret_statement(inner_statement, pvars)
    elif statement.token_id() == TokenId.WHILE:
        cond = interpret_expression(statement.left(), pvars)
        while cond:
            for inner_statement in statement.children[1:]:
                interpret_statement(inner_statement, pvars)
            cond = interpret_expression(statement.left(), pvars)
    elif statement.token_id() == TokenId.FN_DEF:
        fn_name = statement.token_value()
        num_params = int(statement.children[0].token_value())
        params = [p.token_value() for p in statement.children[1:1+num_params]]
        body = statement.children[1+num_params:]
        pvars[fn_name] = DrakFunction(fn_name, params, body)
    elif statement.token_id() == TokenId.FUNC_CALL:
        if statement.token_value() == 'print':
            args = [interpret_expression(arg, pvars) for arg in statement.children]
            print(*args)
        else:
            func = pvars[statement.token_value()]
            if not isinstance(func, DrakFunction):
                print(f"Error, {statement.token_value()} is not a function")
                return
            if len(statement.children) != len(func.params):
                print(f"Error, wrong number of parameters for call to {statement.token_value()}")
                return
            args = [interpret_expression(arg, pvars) for arg in statement.children]
            fvars = pvars.copy()
            for i, param in enumerate(func.params): # Set parameters to passed argument values
                fvars[param] = args[i]
            for statement in func.body:
                interpret_statement(statement, fvars)
            

def interpret_program(program: List[AstNode]):
    pvars = {}
    for statement in program:
        interpret_statement(statement, pvars)
    return pvars

source = """
def fn(a, b) {
    foo = a + b;
    print(foo);
}
foo = 0;
fn(10, 12);
print(foo);
"""
# source = """
# a = 0;
# b = 1;
# while b < 3000 {
#     print(a + b);
#     c = a;
#     a = b;
#     b = a + c;
# }
# """

if __name__ == '__main__':
    toks = parse(source)
    print(interpret_program(toks))