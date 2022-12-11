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
    elif statement.token_id() == TokenId.FUNC_CALL:
        args = [interpret_expression(arg, pvars) for arg in statement.children]
        if statement.token_value() == 'print':
            print(*args)
        else:
            func = pvars[statement.token_value()]
            print("Error, defining functions not implemented")

def interpret_program(program: List[AstNode]):
    pvars = {}
    for statement in program:
        interpret_statement(statement, pvars)
    return pvars

source = """
a = 0;
b = 1;
while b < 3000 {
    print(a + b);
    c = a;
    a = b;
    b = a + c;
}
"""

if __name__ == '__main__':
    toks = parse(source)
    print(interpret_program(toks))