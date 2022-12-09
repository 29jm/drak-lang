from enum import Enum, auto
from typing import List
import re

class TokenId(Enum):
    IF = auto()
    NUMBER = auto()
    CBRACE_LEFT = auto()
    CBRACE_RIGHT = auto()
    RETURN = auto()
    OP_GT = auto()
    OP_PLUS = auto()
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
    def __init__(self, token, children=[]):
        self.token = token
        self.children = children
    
    def __repr__(self) -> str:
        return f"{self.token} -> {self.children}"

all_tokens = [tok for tok in TokenId]
ops_tokens = [TokenId.OP_GT, TokenId.OP_PLUS]

number_pattern = re.compile(r'[0-9]+')
identifier_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')

source = """
if(3 > 2) {
    (32+12)
    return(4)
}
"""

def clean_source(src: str) -> str:
    return ''.join(src.replace(' ', '').splitlines())

def split_source(src: str) -> List[str]:
    parts = []

    while src:
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
        elif part == 'return':
            tokens.append(Token(TokenId.RETURN))
        elif (m := re.match(number_pattern, part)):
            tokens.append(Token(TokenId.NUMBER, int(m[0])))

    return [Token(tok) if tok is TokenId else tok for tok in tokens]

def expect(tokens: List[Token], tok_id) -> Token:
    if not isinstance(tok_id, list):
        tok_id = [tok_id]
    if tokens:
        tok = tokens.pop(0)
        if any(tok.token_id is tid for tid in tok_id):
            return tok
    return None

def take_until(tokens: List[Token], tok_id: TokenId) -> List[Token]:
    toks = []
    for tok in tokens:
        if tok.token_id is tok_id:
            break
        toks.append(tok)
    return toks

def treeify(tokens: List[Token]) -> List:
    roots = []

    while tokens:
        tok = tokens.pop(0)

        if tok.token_id == TokenId.IF:
            if not expect(tokens, TokenId.RBRACE_LEFT):
                print("Error, expected opening condition brace")
                break

            # Condition of the if will be first direct child of if
            cond_child = take_until(tokens, TokenId.RBRACE_RIGHT)
            cond_child_tree = treeify(cond_child[:])
            tokens = tokens[len(cond_child):]

            if not expect(tokens, TokenId.RBRACE_RIGHT):
                print("Error, expected closing condition brace")
                break
            if not expect(tokens, TokenId.CBRACE_LEFT):
                print("Error, expected opening if body brace")
                break

            children = take_until(tokens, TokenId.CBRACE_RIGHT)
            children_tree = treeify(children[:])
            tokens = tokens[len(children):]

            if not expect(tokens, TokenId.CBRACE_RIGHT):
                print("Error, expected closing body brace")
                break

            if not isinstance(children_tree, list):
                children_tree = [children_tree]

            roots.append(AstNode(tok, [cond_child_tree] + children_tree))
            tokens = tokens[len(children):]
        elif tok.token_id is TokenId.NUMBER:
            lhs = tok
            op = expect(tokens, ops_tokens)

            if not op:
                roots.append(lhs) # Single number
                continue

            rhs = treeify(tokens) # whatever comes next
            roots.append(AstNode(op, [lhs, rhs]))
        elif tok.token_id is TokenId.RETURN:
            if not expect(tokens, TokenId.RBRACE_LEFT):
                print("Error, expected opening brace")
                break

            children = take_until(tokens, TokenId.RBRACE_RIGHT)
            children_tree = treeify(children[:])
            tokens = tokens[len(children):]

            if not expect(tokens, TokenId.RBRACE_RIGHT):
                print("Error, expected closing brace")
                break

            roots.append(AstNode(tok, children_tree))
        elif tok.token_id is TokenId.RBRACE_LEFT:
            children = take_until(tokens, TokenId.RBRACE_RIGHT)
            children_tree = treeify(children[:])
            tokens = tokens[len(children):]
            roots.append(children_tree)

            if not expect(tokens, TokenId.RBRACE_RIGHT):
                print("Error, expected closing brace")
                break
        else:
            print(f"Error, failed to parse {tok}")

    if len(roots) == 1:
        return roots[0]
    return roots

if __name__ == '__main__':
    print(clean_source(source))
    print(split_source(clean_source((source))))
    toks = tokenize(split_source(clean_source((source))))
    print(toks)
    print([n.value for n in toks if n.token_id is TokenId.NUMBER])
    print(treeify(toks))