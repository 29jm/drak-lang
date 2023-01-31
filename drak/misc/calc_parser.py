#!/usr/bin/env python3

from drak.frontend.utils import *

# Grammar:
# expression = term, { add_op, term } ;
# term       = factor, { mul_op, factor } ;
# factor     = number | "(", expression, ")" ;
# add_op     = "+" | "-" ;
# mul_op     = "*" | "/" ;
# number     = digit, { digit } ;
# digit      = ? regex [0-9] ? ;

add_ops = [TokenId.OP_PLUS, TokenId.OP_MINUS]
mul_ops = [TokenId.OP_MUL, TokenId.OP_DIV]

op_map = {
    TokenId.OP_PLUS: lambda x, y: x + y,
    TokenId.OP_MINUS: lambda x, y: x - y,
    TokenId.OP_MUL: lambda x, y: x * y,
    TokenId.OP_DIV: lambda x, y: x / y
}

def expression(tokens: List[Token]) -> AstNode:
    tree = term(tokens)
    while look(tokens) in add_ops:
        op = match(tokens, add_ops)
        rhs = term(tokens)
        tree = AstNode(op, [tree, rhs])
    return tree

def factor(tokens: List[Token]) -> AstNode:
    if look(tokens) == TokenId.RBRACE_LEFT:
        match(tokens, TokenId.RBRACE_LEFT)
        tree = expression(tokens)
        match(tokens, TokenId.RBRACE_RIGHT)
    else:
        number = match(tokens, TokenId.NUMBER)
        tree = AstNode(number)
    return tree

def term(tokens: List[Token]) -> AstNode:
    tree = factor(tokens)
    while look(tokens) in mul_ops:
        op = match(tokens, mul_ops)
        rhs = factor(tokens)
        tree = AstNode(op, [tree, rhs]) # LHS of '*' in (a/b)*c is (a/b)
    return tree

def evaluate(tree: AstNode) -> int:
    if tree.token_id() == TokenId.NUMBER:
        return int(tree.token_value())
    return op_map[tree.token_id()](evaluate(tree.left()), evaluate(tree.right()))

if __name__ == '__main__':
    import readline
    try:
        while (src := input("expr: ")):
            print(evaluate(expression(tokenize(src))))
    except EOFError:
        pass