#!/usr/bin/env python3

import argparse as arg
from pathlib import Path
import drak.parser.parser as parser
import drak.compiler.compiler as compiler
import drak.compiler.liveness as liveness
import subprocess

def compile(source: Path, dest: Path, args):
    with open(source, 'r') as src, open(dest, 'w') as dst:
        toks = parser.parse(src.read())
        output = compiler.compile_to_asm(toks, args.strip_comments)
        dst.write(output)

        opt = compiler.compile(toks)
        print('\n'.join(('\n\t'.join(str(line) for line in block)) for block in opt))

    name_asm = (dest.parent / dest.stem).with_suffix('.asm')
    name_o = (dest.parent / dest.stem).with_suffix('.o')
    name_prog = dest.parent / dest.stem

    if args.emit_only:
        return

    subprocess.run([
        'arm-none-eabi-as',
        name_asm,
        '-o',
        name_o])
    subprocess.run([
        'arm-none-eabi-gcc',
        '-march=armv7',
        '-mthumb',
        '-nostdlib',
        name_o,
        '-o',
        name_prog])

def main():
    parser = arg.ArgumentParser(
        prog='Drak Compiler',
        description='Compiles Drak source code to ARM assembly',
        epilog='Version 0.0.1 alpha')
    
    parser.add_argument('source', type=Path)
    parser.add_argument('-o', '--output', dest='output', type=Path)
    parser.add_argument('-s', '--strip-comments',
                        dest='strip_comments', action='store_true', default=False)
    parser.add_argument('-E', '--emit-only', dest='emit_only', action='store_true', default=False)
    args = parser.parse_args()

    if not args.output:
        args.output = Path(f'{args.source.parent / args.source.stem}.asm')

    compile(args.source.absolute(), args.output.absolute(), args)

if __name__ == '__main__':
    main()