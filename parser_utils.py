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

_token_map = {
    r'\s+': None,
    r'[0-9]+': TokenId.NUMBER,
    r'\(': TokenId.RBRACE_LEFT,
    r'\)': TokenId.RBRACE_RIGHT,
    r'\+': TokenId.OP_PLUS,
    r'-': TokenId.OP_MINUS,
    r'\*': TokenId.OP_MUL,
    r'/': TokenId.OP_DIV
}

def tokenize(src: str, token_map=_token_map) -> List[Token]:
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
    return tokens[0].token_id if tokens else None