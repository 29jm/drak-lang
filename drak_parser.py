from __future__ import annotations
from enum import Enum, auto
from typing import List
import re

class TokenId(Enum):
    IF = auto()
    NUMBER = auto()
    IDENTIFIER = auto()
    CBRACE_LEFT = auto()
    CBRACE_RIGHT = auto()
    RETURN = auto()
    OP_GT = auto()
    OP_PLUS = auto()
    OP_ASSIGN = auto()
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
    def __init__(self, token: Token, children: List[AstNode]|List[Token]=[]):
        self.token = token
        self.children = children
        if not isinstance(self.children, list):
            raise Exception()

    def __repr__(self) -> str:
        return f"{self.token} -> {self.children}"

all_tokens = [tok for tok in TokenId]
ops_tokens = [TokenId.OP_GT, TokenId.OP_PLUS]

number_pattern = re.compile(r'[0-9]+')
identifier_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')

def clean_source(src: str) -> str:
    return ' '.join(src.splitlines())

def split_source(src: str) -> List[str]:
    parts = []

    while src:
        # Match separator, discard but split
        if re.match(r'\s', src[0]):
            src = src[1:]
            continue
        # Match identifier
        m = identifier_pattern.match(src)
        if m:
            parts.append(m[0])
            src = src[len(m[0]):]
            continue
        # Match number
        m = number_pattern.match(src)
        if m:
            parts.append(m[0])
            src = src[len(m[0]):]
            continue
        # Match brace
        if src[0] == '{':
            parts.append('{')
            src = src[1:]
            continue
        if src[0] == '}':
            parts.append('}')
            src = src[1:]
            continue
        if src[0] == '(':
            parts.append('(')
            src = src[1:]
            continue
        if src[0] == ')':
            parts.append(')')
            src = src[1:]
            continue
        # Match op
        if src[0] == '>':
            parts.append('>')
            src = src[1:]
            continue
        if src[0] == '+':
            parts.append('+')
            src = src[1:]
            continue
        if src[0] == '=':
            parts.append('=')
            src = src[1:]
            continue
        # Match if
        if src[:2] == 'if':
            parts.append('if')
            src = src[2:]
            continue
        # Match return
        if src[:2] == 'return':
            parts.append('return')
            src = src[len('return'):]
            continue

    return parts

def tokenize(parts: List[str]) -> List[Token]:
    tokens = []

    for part in parts:
        if part == 'if':
            tokens.append(Token(TokenId.IF))
        elif part == '(':
            tokens.append(Token(TokenId.RBRACE_LEFT))
        elif part == ')':
            tokens.append(Token(TokenId.RBRACE_RIGHT))
        elif part == '{':
            tokens.append(Token(TokenId.CBRACE_LEFT))
        elif part == '}':
            tokens.append(Token(TokenId.CBRACE_RIGHT))
        elif part == '>':
            tokens.append(Token(TokenId.OP_GT))
        elif part == '+':
            tokens.append(Token(TokenId.OP_PLUS))
        elif part == '=':
            tokens.append(Token(TokenId.OP_ASSIGN))
        elif part == 'return':
            tokens.append(Token(TokenId.RETURN))
        elif (m := re.match(number_pattern, part)):
            tokens.append(Token(TokenId.NUMBER, int(m[0])))
        elif (m := re.match(identifier_pattern, part)):
            tokens.append(Token(TokenId.IDENTIFIER, m[0]))

    return [Token(tok) if tok is TokenId else tok for tok in tokens]

def expect(tokens: List[Token], tok_id, nopop=False) -> Token:
    if not isinstance(tok_id, list):
        tok_id = [tok_id]
    if tokens:
        tok = tokens.pop(0) if not nopop else tokens[0]
        if any(tok.token_id is tid for tid in tok_id):
            return tok
    return None

def take_until(tokens: List[Token], tok_id: TokenId) -> List[Token]:
    toks = []

    while tokens and (tokens[0].token_id is not tok_id):
        toks.append(tokens.pop(0))

    return toks

def treeify(tokens: List[Token], only_expr=False) -> List:
    roots = []
    expr_found = False # Set this to true whenever a complete expression is found

    while tokens and ((not only_expr) or (not expr_found)):
        tok = tokens.pop(0)

        if tok.token_id == TokenId.IDENTIFIER:
            lhs = tok
            next_tok = expect(tokens, [TokenId.OP_ASSIGN] + ops_tokens, nopop=True)

            if not next_tok: # Lonely identifier
                roots.append(tok)
                expr_found = True
                continue

            if next_tok.token_id == TokenId.OP_ASSIGN:
                assign = tokens.pop(0) # Pop assign
                rhs = treeify(tokens, only_expr=True)
                roots.append(AstNode(assign, [lhs, rhs]))
            elif next_tok.token_id == TokenId.OP_GT:
                op = tokens.pop(0)
                rhs = treeify(tokens, only_expr=True)
                roots.append(AstNode(op, [lhs, rhs]))
                expr_found = True
        elif tok.token_id == TokenId.IF:
            # if not expect(tokens, TokenId.RBRACE_LEFT):
            #     print("Error, expected opening condition brace")
            #     break

            # Condition of the if will be first direct child of if
            cond_child = take_until(tokens, TokenId.CBRACE_LEFT)
            cond_child_tree = treeify(cond_child, only_expr=True)

            if not expect(tokens, TokenId.CBRACE_LEFT):
                print("Error, expected opening if body brace")
                break

            children = take_until(tokens, TokenId.CBRACE_RIGHT)
            children_tree = treeify(children)

            if not expect(tokens, TokenId.CBRACE_RIGHT):
                print("Error, expected closing body brace")
                break

            if not isinstance(children_tree, list):
                children_tree = [children_tree]

            roots.append(AstNode(tok, [cond_child_tree] + children_tree))
            tokens = tokens[len(children):]
        elif tok.token_id is TokenId.NUMBER:
            lhs = tok
            op = expect(tokens, ops_tokens, nopop=True)

            if not op:
                roots.append(lhs) # Single number
                expr_found = True
                continue

            op = tokens.pop(0)
            rhs = treeify(tokens, only_expr=True) # whatever comes next
            roots.append(AstNode(op, [lhs, rhs]))
            expr_found = True
        elif tok.token_id is TokenId.RETURN:
            children_tree = treeify(tokens, only_expr=True)
            roots.append(AstNode(tok, [children_tree]))
        elif tok.token_id is TokenId.RBRACE_LEFT:
            children = take_until(tokens, TokenId.RBRACE_RIGHT)
            children_tree = treeify(children)

            if not expect(tokens, TokenId.RBRACE_RIGHT):
                print("Error, expected closing brace")
                break

            roots.append(children_tree)
            expr_found = True
        else:
            print(f"Error, failed to parse {tok}")

    if len(roots) == 1:
        return roots[0]
    return roots

def parse(src: str) -> List[Token]:
    return treeify(tokenize(split_source(clean_source(src))))

if __name__ == '__main__':
    # print(clean_source(source))
    # print(split_source(clean_source((source))))
    toks = tokenize(split_source(clean_source((source))))
    # print(toks)
    print(treeify(toks))