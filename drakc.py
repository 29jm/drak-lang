#!/usr/bin/env python3

import argparse as arg
from pathlib import Path
import drak.frontend.parser as parser
import drak.frontend.compiler as compiler
import drak.middle_end.liveness as liveness
import drak.middle_end.ir_utils as ir_utils
import drak.middle_end.ssa as ssa
import drak.middle_end.coloring as coloring
import subprocess

def compile(source: Path, dest: Path, args):
    with open(source, 'r') as src, open(dest, 'w') as dst:
        toks = parser.parse(src.read())

        il = compiler.compile(toks)
        output = ""
        for func in il:
            # print(func[0])
            bblocks = ir_utils.basic_blocks(func)
            cfg = ir_utils.control_flow_graph(bblocks)
            lifetimes = liveness.block_liveness2(bblocks, cfg)
            domf = ir_utils.dominance_frontier(cfg)
            bblocks = ssa.phi_insertion(bblocks, cfg, domf, lifetimes)
            bblocks = ssa.renumber_variables(bblocks, cfg)
            bblocks = ssa.simpliphy(bblocks)

            igraph = liveness.interference_graph(bblocks)
            bblocks = liveness.coalesce(bblocks, igraph)

            bblocks = coloring.regalloc(bblocks, set([f'r{i}' for i in range(4, 13)]))
            output += ''.join(compiler.intermediate_to_asm(block) for block in bblocks)
            if args.cfg:
                lifetimes2 = liveness.block_liveness2(bblocks, cfg)
                dot_non_alloc = ir_utils.print_cfg_as_dot(cfg, bblocks, lifetimes2)
                svg = subprocess.run(['dot', '-Tsvg'], text=True, input=dot_non_alloc, stdout=subprocess.PIPE)
                subprocess.run(['display', '-resize', '800x600'], text=True, input=svg.stdout)

        dst.write(output)

        if args.emit_only:
            print('\n'.join(('\n\t'.join(str(line) for line in block)) for block in il))

    name_asm = (dest.parent / dest.stem).with_suffix('.asm')
    name_o = (dest.parent / dest.stem).with_suffix('.o')
    name_prog = dest.parent / dest.stem

    if args.emit_only or args.cfg:
        return

    subprocess.run([
        'arm-none-eabi-as',
        '-march=armv8-a',
        name_asm,
        '-o',
        name_o])
    subprocess.run([
        'arm-none-eabi-gcc',
        '-march=armv8-a',
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