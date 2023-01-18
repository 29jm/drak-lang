#!/usr/bin/env python3

import argparse as arg
from pathlib import Path
import drak.parser.parser as parser
import drak.compiler.compiler as compiler
import drak.compiler.liveness as liveness
import drak.compiler.ir_utils as ir_utils
import subprocess

def compile(source: Path, dest: Path, args):
    with open(source, 'r') as src, open(dest, 'w') as dst:
        toks = parser.parse(src.read())
        output = compiler.compile_to_asm(toks, args.strip_comments)
        dst.write(output)

        opt = compiler.compile(toks)
        if args.emit_only:
            print('\n'.join(('\n\t'.join(str(line) for line in block)) for block in opt))
        if args.cfg:
            # opt[0] = [['main:'],
            #     ['mov', 'REG4', '#50'],
            #     ['cmp', 'REG4', '#3'],
            #     ['bne', '.main_if_1'],
            #     ['mov', 'REG4', '#0'],
            #     ['b', '.main_if_2'],
            #     ['.main_if_1:'],
            #     ['mov', 'REG4', '#1'],
            #     ['.main_if_2:'],
            #     ['mov', 'r0', 'REG4'],
            #     ['b', '.main_end'],
            #     ['.main_end:'], ['bx', 'lr']]
            bblocks = ir_utils.basic_blocks(opt[0])
            cfg = ir_utils.control_flow_graph(bblocks)
            lifetimes = liveness.block_liveness2(bblocks, cfg)
            domf = ir_utils.dominance_frontier(cfg)
            bblocks = ir_utils.phi_insertion(bblocks, cfg, domf, lifetimes)
            bblocks = ir_utils.renumber_variables(bblocks, cfg)
            bblocks = ir_utils.simpliphy(bblocks)
            lifetimes = liveness.block_liveness2(bblocks, cfg)
            dot = ir_utils.print_cfg_as_dot(cfg, bblocks, lifetimes)
            svg = subprocess.run(['dot', '-Tsvg'], text=True, input=dot, stdout=subprocess.PIPE)
            subprocess.run(['display', '-resize', '800x600'], text=True, input=svg.stdout)

    name_asm = (dest.parent / dest.stem).with_suffix('.asm')
    name_o = (dest.parent / dest.stem).with_suffix('.o')
    name_prog = dest.parent / dest.stem

    if args.emit_only or args.cfg:
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
    parser.add_argument('-C', '--cfg', dest='cfg', action='store_true', default=False)
    args = parser.parse_args()

    if not args.output:
        args.output = Path(f'{args.source.parent / args.source.stem}.asm')

    compile(args.source.absolute(), args.output.absolute(), args)

if __name__ == '__main__':
    main()