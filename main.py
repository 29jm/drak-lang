from drak_parser import Token, TokenId, AstNode, parse

from typing import List

source = """
var = 30
if (var > 2 + 1) {
    peter = var
    local_thing = (32 + 12) + peter
    var = 3
    return local_thing
}
"""

def build_symbols(ast: List[Token]):
    def scan_node(node: AstNode|Token, syms={}):
        token = node.token if isinstance(node, AstNode) else node
        if token.token_id == TokenId.OP_ASSIGN:
            lhs, rhs = node.children
            if not isinstance(lhs, Token):
                print("Error, expected symbol on lhs of assignment")
                return syms
            syms[lhs.value] = None # TODO: gather useful info?
            syms.update(scan_node(rhs, syms))
        elif token.token_id == TokenId.IDENTIFIER:
            if not token.value in syms:
                print(f"Error, variable {token.value} referenced before assignment")
                return syms
        else: # Just browse for identifiers
            if isinstance(node, AstNode):
                for child_node in node.children:
                    syms.update(scan_node(child_node, syms))
        return syms
    syms = {}
    if not isinstance(ast, list):
        ast = [ast]
    for node in ast:
        syms.update(scan_node(node, syms))
    return syms

if __name__ == '__main__':
    ast = parse(source)
    print(source)
    print(ast)
    print(build_symbols(ast))