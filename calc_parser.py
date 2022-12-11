from __future__ import annotations
from enum import Enum, auto
from typing import List
import re

class TokenId(Enum):
    NUMBER = auto()
    OP_PLUS = auto()
    OP_MINUS = auto()
    OP_MUL = auto()
    OP_DIV = auto()
    RBRACE_LEFT = auto()
    RBRACE_RIGHT = auto()

class Token:
    def __init__(self, token_id, value=None) -> None:
        self.token_id = token_id
        self.value = value

    def __repr__(self) -> str:
        return f'Token({self.token_id}, {self.value})'

    def __str__(self) -> str:
        return f'({self.token_id}, {self.value})'

class AstNode:
    def __init__(self, token: Token, children: List[AstNode]=[]):
        self.token = token
        self.children = children
        if not isinstance(self.children, list):
            raise Exception()

    def __repr__(self) -> str:
        return f"{self.token} -> {self.children}"
    
    def token_id(self) -> TokenId:
        return self.token.token_id

    def token_value(self) -> str:
        return self.token.value
    
    def left(self) -> AstNode:
        if not len(self.children) == 2:
            print("Error, accessing left/right on non-binary node")
        return self.children[0]

    def right(self) -> AstNode:
        if not len(self.children) == 2:
            print("Error, accessing left/right on non-binary node")
        return self.children[1]

all_tokens = [tok for tok in TokenId]

number_pattern = re.compile(r'[0-9]+')
token_map = {
    r'\s+': None,
    number_pattern: TokenId.NUMBER,
    r'\(': TokenId.RBRACE_LEFT,
    r'\)': TokenId.RBRACE_RIGHT,
    r'\+': TokenId.OP_PLUS,
    r'-': TokenId.OP_MINUS,
    r'\*': TokenId.OP_MUL,
    r'/': TokenId.OP_DIV
}

def tokenize(src: str) -> List[Token]:
    parts = []
    while src:
        for pattern in token_map:
            if (m := re.match(pattern, src)):
                if token_map[pattern]:
                    parts.append(Token(token_map[pattern], m[0]))
                src = src[len(m[0]):]
    return parts

def match(tokens: List[Token], token_id: TokenId|List[TokenId]) -> Token|None:
    tok = look(tokens)
    token_id = token_id if isinstance(token_id, list) else [token_id]
    if not tok:
        print(f"Error, expected {token_id}, got nothing")
        return None
    if not (tok in token_id):
        print(f"Error, expected {token_id}, got {tok}: {tokens[0]}")
        return None
    return tokens.pop(0)

def look(tokens: List[Token]) -> TokenId|None:
    return tokens[0].token_id if len(tokens) else None

# Parser-specific #################################################

# Grammar:
# expression = term, { add_op, term }
# term       = factor, { mul_op, factor }
# factor     = number | "(", expression, ")"
# add_op     = "+" | "-"
# mul_op     = "*" | "/"
# number     = digit, { digit }
# digit      = "0" | ... | "9"

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
    if not tree.children:
        return int(tree.token_value())
    return op_map[tree.token_id()](evaluate(tree.left()), evaluate(tree.right()))

def parse(src: str) -> List[Token]:
    return expression(tokenize(src))

if __name__ == '__main__':
    import readline
    try:
        while (src := input("expr: ")):
            print(evaluate(expression(tokenize(src))))
    except EOFError:
        pass