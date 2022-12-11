#!/usr/bin/env python3

from parser_utils import *

# Grammar:
# program         = statement, { statement }
# statement       = assignment | if-statement | while-statement | func-def | func-call-stmt | return-stmt
# assignment      = identifier, "=", expression, ";"
# if-statement    = "if", bool-expression, "{", { statement }, "}"
# while-statement = "while", bool-expression, "{", { statement }, "}"
# func-def        = "def", identifier, "(", { identifier, { ",", identifier } }, ")", "{", { statement }, "}"
# func-call-stmt  = func-call, ";"
# return-stmt     = "return", expression, ";"
# func-call       = identifier, "(", { expression, { ",", expression } }, ")"
# expression      = term_0, { bool_op, term_0 }
# bool-expression = expression, bool_op, expression
# term_0          = term_1, { add_op, term_1 }
# term_1          = term_2, { mul_op, term_2 }
# term_2          = number | "(", expression, ")" | func-call
# bool_op         = ">" | "<" | "=="
# add_op          = "+" | "-"
# mul_op          = "*" | "/"
# number          = digit, { digit }
# digit           = "0" | ... | "9"

ops_0 = [TokenId.OP_EQ, TokenId.OP_NEQ, TokenId.OP_GT, TokenId.OP_LT]
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
    if look(tokens) == TokenId.IDENTIFIER and look(tokens, 1) == TokenId.ASSIGN:
        tree = assignment(tokens)
    elif look(tokens) == TokenId.IDENTIFIER and look(tokens, 1) == TokenId.RBRACE_LEFT:
        tree = func_call_stmt(tokens)
    elif look(tokens) == TokenId.FN_DEF:
        tree = func_def(tokens)
    elif look(tokens) == TokenId.IF:
        tree = if_statement(tokens)
    elif look(tokens) == TokenId.WHILE:
        tree = while_statement(tokens)
    elif look(tokens) == TokenId.RETURN:
        tree = return_stmt(tokens)
    return tree

def assignment(tokens: List[AstNode]) -> AstNode:
    lhs = match(tokens, TokenId.IDENTIFIER)
    op = match(tokens, TokenId.ASSIGN)
    rhs = expression(tokens)
    _ = match(tokens, TokenId.SEMICOLON)
    return AstNode(op, [lhs, rhs])

def func_call_stmt(tokens: List[AstNode]) -> AstNode:
    tree = func_call(tokens)
    _ = match(tokens, TokenId.SEMICOLON)
    return tree

def func_call(tokens: List[AstNode]) -> AstNode:
    fn_name = match(tokens, TokenId.IDENTIFIER)
    _ = match(tokens, TokenId.RBRACE_LEFT)

    args = []
    if look(tokens) != TokenId.RBRACE_RIGHT: # Arguments
        args.append(expression(tokens))
        while look(tokens) == TokenId.COMMA:
            _ = match(tokens, TokenId.COMMA)
            args.append(expression(tokens))
    _ = match(tokens, TokenId.RBRACE_RIGHT)

    return AstNode(Token(TokenId.FUNC_CALL, fn_name.value), args)

def func_def(tokens: List[AstNode]) -> AstNode:
    _ = match(tokens, TokenId.FN_DEF)
    name = match(tokens, TokenId.IDENTIFIER).value
    _ = match(tokens, TokenId.RBRACE_LEFT)

    params = []
    if look(tokens) != TokenId.RBRACE_RIGHT: # Parameters
        params.append(AstNode(match(tokens, TokenId.IDENTIFIER)))
        while look(tokens) == TokenId.COMMA:
            _ = match(tokens, TokenId.COMMA)
            params.append(AstNode(match(tokens, TokenId.IDENTIFIER)))

    _ = match(tokens, TokenId.RBRACE_RIGHT)
    _ = match(tokens, TokenId.CBRACE_LEFT)

    body = []
    while look(tokens) != TokenId.CBRACE_RIGHT: # Func body
        body.append(statement(tokens))

    _ = match(tokens, TokenId.CBRACE_RIGHT)

    return AstNode(Token(TokenId.FN_DEF, name),
        [AstNode(Token(TokenId.NUMBER, str(len(params))))] + # Number of parameters
        params                                             + # Actual parameters
        body                                                 # Function body
    )

def if_statement(tokens: List[AstNode]) -> AstNode:
    op = match(tokens, TokenId.IF)
    cond = bool_expression(tokens)
    _ = match(tokens, TokenId.CBRACE_LEFT)
    body = []

    while look(tokens) != TokenId.CBRACE_RIGHT:
        body.append(statement(tokens))

    _ = match(tokens, TokenId.CBRACE_RIGHT)

    return AstNode(op, [cond] + body)

def while_statement(tokens: List[AstNode]) -> AstNode:
    op = match(tokens, TokenId.WHILE)
    cond = bool_expression(tokens)
    _ = match(tokens, TokenId.CBRACE_LEFT)
    body = []

    while look(tokens) != TokenId.CBRACE_RIGHT:
        body.append(statement(tokens))

    _ = match(tokens, TokenId.CBRACE_RIGHT)

    return AstNode(op, [cond] + body)

def return_stmt(tokens: List[AstNode]) -> AstNode:
    op = match(tokens, TokenId.RETURN)
    retval = expression(tokens)
    _ = match(tokens, TokenId.SEMICOLON)
    return AstNode(op, [retval])

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

def term_2(tokens: List[Token]) -> AstNode: # Factors: nums, parens, fn calls
    if look(tokens) == TokenId.RBRACE_LEFT:
        _ = match(tokens, TokenId.RBRACE_LEFT)
        tree = expression(tokens)
        _ = match(tokens, TokenId.RBRACE_RIGHT)
    elif look(tokens) == TokenId.IDENTIFIER and look(tokens, 1) == TokenId.RBRACE_LEFT:
        tree = func_call(tokens)
    else:
        final = match(tokens, [TokenId.NUMBER, TokenId.IDENTIFIER])
        tree = AstNode(final)
    return tree

source = """
def func(a, b) {
    foo = a + b;
    return foo;
}
foo = func(1, 2) + 2;
"""

if __name__ == '__main__':
    tokens = tokenize(source)
    # print(tokens)
    print(program(tokens))