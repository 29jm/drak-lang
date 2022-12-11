# Drak

```
def factorial(n) {
    if n == 1 {
        return 1;
    }

    return n * factorial(n - 1);
}

n = factorial(10);
print(n);
```

```sh
>> python drak_interpreter.py test.drak
>> 3628800
```

The above is Drak. Drak is also:
+ An interpreted language
+ That currently doesn't handle strings
+ Using a top-down parser
+ The thing that made me understand parsing basics
+ Written in Python
+ Striving for a readable implementation

As you can see there is not much to it. You can find its full grammar at the top of `drak_parser.py`.

## Calc parser

In this repo you will also find `calc_parser.py`, a short and sweet parser/interpreter of mathematical expressions of the form `3+4*2-(14/(6*3))`, or more precisely, following the grammar below:
```ebnf
expression = term, { add_op, term } ;
term       = factor, { mul_op, factor } ;
factor     = number | "(", expression, ")" ;
add_op     = "+" | "-" ;
mul_op     = "*" | "/" ;
number     = digit, { digit } ;
digit      = "0" | "..." | "9" ;
```

It uses the same parsing logic as Drak, but being a much simpler language, it would be a better starting point for understanding parsing concepts. In fact, here is the full parsing logic:

```py
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
        tree = AstNode(op, [tree, rhs])
    return tree

def evaluate(tree: AstNode) -> int:
    if not tree.children:
        return int(tree.token_value())
    return op_map[tree.token_id()](evaluate(tree.left()), evaluate(tree.right()))

```

With that you can just run `evaluate(expression(tokenize("3+4*2-(14/(6*3))")))` and get nice results.

Yes, some utility functions aren't show here, like `look`, `match`, `tokenize`, and the `Token` things - you can find them in `parser_utils.py`.