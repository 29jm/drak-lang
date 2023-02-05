from typing import List
from drak.middle_end.ir_utils import Instr # TODO: move to some outer module?

def __inline_asm_printer(asm) -> str:
    header = "__asm__ volatile ("
    body = '\n'.join(f"\"{line}\\n\"" for line in asm)
    footer = ");"
    return header + body + footer

def __raw_printer(asm, strip_comments=False) -> str:
    def _indent(line: str) -> str:
        ls = line.strip()
        comment = ls.find('//')
        if strip_comments and comment != -1:
            ls = ls[:comment].strip()
        if ls and not ls.endswith(':') and not ls.startswith('.'):
            return '    ' + ls
        return ls
    asm = (_indent(line) for line in asm)
    asm = [line for line in asm if line.strip() != ""]
    return '\n'.join(_indent(line) for line in asm) + '\n'

def instr_to_asm(instr: Instr) -> List[str]:
    def operand_to_asm(op):
        if isinstance(op, list):
            subops = ', '.join(str(subop) for subop in op)
            return '{' + subops + '}'
        return op

    ins, ops = instr[0], instr[1:]
    asm = [instr]

    if ins == 'func_def':
        asm = [
            [ops[0] + ':'],
            ['push {r4-r12, lr}']
        ]
    elif ins == 'func_call':
        asm = [['bl', ops[0]]]
    elif ins == 'func_ret':
        asm = [['pop {r4-r12, lr}']]
        if ops and ops[0] != 'r0':
            asm.append(['mov', 'r0', ops[0], ';'])
        asm.append(['bx', 'lr'])

    return [f'{line[0]} {", ".join(operand_to_asm(op) for op in line[1:])}'
                for line in asm]

def intermediate_to_asm(ilblock: List[Instr]):
    asm = []
    for ins in ilblock:
        asm.extend(instr_to_asm(ins))
    return __raw_printer(asm)