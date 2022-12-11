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

def interpret_expression(expr: AstNode, vars: dict):
    if expr.token_id() == TokenId.NUMBER:
        return int(expr.token_value())
    elif expr.token_id() == TokenId.IDENTIFIER:
        return vars[expr.token_value()]

    op = op_map[expr.token_id()]
    lhs = interpret_expression(expr.left(), vars)
    rhs = interpret_expression(expr.right(), vars)

    return op(lhs, rhs)

def interpret_statement(statement: AstNode, vars: dict):
    if statement.token_id() == TokenId.ASSIGN:
        lhs = statement.left().value
        rhs = interpret_expression(statement.right(), vars)
        vars[lhs] = rhs
    elif statement.token_id() == TokenId.IF:
        cond = interpret_expression(statement.left(), vars)
        if cond != True:
            return
        for inner_statement in statement.children[1:]:
            interpret_statement(inner_statement, vars)

def interpret_program(program: List[AstNode]):
    vars = {}
    for statement in program:
        interpret_statement(statement, vars)
    return vars

source = """
foo = 16;
if foo - 5 > 10 {
    foo = 42;
    if foo > 40 {
        foo = 0
    }
}
"""

if __name__ == '__main__':
    toks = parse(source)
    print(interpret_program(toks))