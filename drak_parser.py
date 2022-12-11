#!/usr/bin/env python3

from parser_utils import *

# Grammar:
# program         = statement, { statement }
# statement       = assignment | if-statement
# assignment      = identifier, "=", expression, ";"
# if-statement    = "if", bool-expression, "{", { statement }, "}"
# expression      = term_0, { bool_op, term_0 }
# bool-expression = expression, bool_op, expression
# term_0          = term_1, { add_op, term_1 }
# term_1          = term_2, { mul_op, term_2 }
# term_2          = number | "(", expression, ")"
# bool_op         = ">" | "<" | "=="
# add_op          = "+" | "-"
# mul_op          = "*" | "/"
# number          = digit, { digit }
# digit           = "0" | ... | "9"

ops_0 = [TokenId.OP_EQ, TokenId.OP_GT, TokenId.OP_LT]
ops_1 = [TokenId.OP_PLUS, TokenId.OP_MINUS]
ops_2 = [TokenId.OP_MUL, TokenId.OP_DIV]

def parse(source: str) -> List[AstNode]:
    return program(tokenize(source))

def program(tokens: List[Token]) -> List[AstNode]:
    # TODO: Make some JoinStatement AstNode to keep a tree
    tree = [statement(tokens)]
    while look(tokens):
        tree.append(statement(tokens))
    return tree

def statement(tokens: List[Token]) -> AstNode:
    if look(tokens) == TokenId.IDENTIFIER:
        tree = assignment(tokens)
    elif look(tokens) == TokenId.IF:
        tree = if_statement(tokens)
    return tree

def assignment(tokens: List[AstNode]) -> AstNode:
    lhs = match(tokens, TokenId.IDENTIFIER)
    op = match(tokens, TokenId.ASSIGN)
    rhs = expression(tokens)
    _ = match(tokens, TokenId.SEMICOLON)
    return AstNode(op, [lhs, rhs])

def if_statement(tokens: List[AstNode]) -> AstNode:
    op = match(tokens, TokenId.IF)
    cond = bool_expression(tokens)
    _ = match(tokens, TokenId.CBRACE_LEFT)
    body = []

    while look(tokens) != TokenId.CBRACE_RIGHT:
        body.append(statement(tokens))

    _ = match(tokens, TokenId.CBRACE_RIGHT)

    return AstNode(op, [cond] + body)

def bool_expression(tokens: List[AstNode]) -> AstNode:
    expr = expression(tokens)
    if expr.token_id() not in ops_0:
        print("Error, expected boolean expression")
    return expr

def expression(tokens: List[AstNode]) -> AstNode:
    tree = term_0(tokens)
    while look(tokens) in ops_0:
        op = match(tokens, ops_0)
        rhs = term_0(tokens)
        tree = AstNode(op, [tree, rhs])
    return tree

def term_0(tokens: List[AstNode]) -> AstNode: # Boolean ops
    tree = term_1(tokens)
    while look(tokens) in ops_1:
        op = match(tokens, ops_1)
        rhs = term_1(tokens)
        tree = AstNode(op, [tree, rhs])
    return tree

def term_1(tokens: List[AstNode]) -> AstNode: # Add ops
    tree = term_2(tokens)
    while look(tokens) in ops_2:
        op = match(tokens, ops_2)
        rhs = term_2(tokens)
        tree = AstNode(op, [tree, rhs])
    return tree

def term_2(tokens: List[Token]) -> AstNode: # Factors: nums and ()
    if look(tokens) == TokenId.RBRACE_LEFT:
        _ = match(tokens, TokenId.RBRACE_LEFT)
        tree = expression(tokens)
        _ = match(tokens, TokenId.RBRACE_RIGHT)
    else:
        final = match(tokens, [TokenId.NUMBER, TokenId.IDENTIFIER])
        tree = AstNode(final)
    return tree

source = """
foo = (3 + 5) * 2;
if foo > 4*2 {
    foo = 42;
    bar = foo;
}
"""

if __name__ == '__main__':
    tokens = tokenize(source)
    # print(tokens)
    print(program(tokens))