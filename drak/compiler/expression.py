from drak.parser.utils import TokenId
from drak.compiler.structures import *
from drak.compiler.idtype import IntType, BoolType

def compile_expression(stmt: AstNode, target_reg: Reg, ctx: FnContext, asm: Asm) -> str:
    if stmt.token_id() == TokenId.NUMBER:
        asm.append(f'mov r{target_reg}, #{stmt.token_value()}')
        return IntType
    elif stmt.token_id() == TokenId.IDENTIFIER:
        if stmt.token_value() in ['true', 'false']:
            value = 1 if stmt.token_value() == 'true' else 0
            asm.append(f'mov r{target_reg}, #{value}')
            return BoolType
        elif not stmt.token_value() in ctx.get_symbols():
            print("Error, unknown identifier on lhs of assignment")
            return # Error
        else:
            vartype, src_reg = ctx.symbols[stmt.token_value()]
            if vartype.dimensions and stmt.children: # array type, check for indices
                dimensions = vartype.dimensions[:] # Copy dimensions to avoid modifying type
                offset_current = ctx.get_free_reg(asm)
                asm.append(f'mov r{target_reg}, r{src_reg}')
                asm.append(f'add r{target_reg}, #4') # Array size is first uint32; skip it
                for index_stmt in stmt.children:
                    _ = compile_expression(index_stmt, offset_current, ctx, asm) # check int TODO
                    asm.append(f'add r{target_reg}, r{offset_current}, lsl #2') # TODO size to move offset
                    dimensions.pop(0)
                asm.append(f'ldr r{target_reg}, [r{target_reg}, #0]')
                ctx.release_reg(offset_current, asm)
                return IdType(vartype.base_type, dimensions)
            elif src_reg != target_reg: # Scalars: only move things around if needed
                asm.append(f'mov r{target_reg}, r{src_reg} // Assigning {stmt.token_value()}')
            return vartype
    elif stmt.token_id() == TokenId.FUNC_CALL:
        return compile_function_call(stmt, target_reg, ctx, asm)
    elif stmt.token_id() in boolean_ops:
        op = op_map[stmt.token_id()]
        jump_op = jump_op_map[stmt.token_id()]
        lhs_type = compile_expression(stmt.left(), target_reg, ctx, asm)
        reg = ctx.get_free_reg(asm)
        rhs_type = compile_expression(stmt.right(), reg, ctx, asm)
        cond_label = f'.{ctx.function}_cond_{ctx.get_unique()}'
        asm.extend([f'{op} r{target_reg}, r{reg}',
                    f'mov r{target_reg}, #1',
                    f'{jump_op} {cond_label}',
                    f'mov r{target_reg}, #0',
                    f'{cond_label}:'])
        ctx.release_reg(reg, asm)
        if lhs_type != rhs_type:
            print(f'Error, type mismatch in boolean expression, {lhs_type} vs. {rhs_type}')
        return BoolType

    op = op_map[stmt.token_id()]
    allows_immediates = stmt.token_id() in immediate_ops
    lhs_type = compile_expression(stmt.left(), target_reg, ctx, asm)

    if lhs_type != IntType:
        print('Arihthmetic on non-integers not yet supported')

    if allows_immediates and stmt.right().token_id() == TokenId.NUMBER:
        asm.append(f'{op} r{target_reg}, #{stmt.right().token_value()}')
    else:
        reg = ctx.get_free_reg(asm)
        rhs_type = compile_expression(stmt.right(), reg, ctx, asm)
        asm.append(f'{op} r{target_reg}, r{reg}')
        ctx.release_reg(reg, asm)

    return lhs_type

def compile_function_call(stmt: AstNode, target_reg: Reg, ctx: FnContext, asm: Asm):
    fn_name = stmt.token_value()

    if not fn_name in ctx.functions.keys():
        print(f'Error, function {fn_name} called before definition')
    if target_reg == 0:
        print(f'// target reg of {stmt.token_value()} is r0, will fail')

    asm.append(f'push {{r0-r3}} // Spill for call to {fn_name} | free regs: {ctx.free_registers}')

    paramtypes = ctx.functions[fn_name][1:]
    for (i, arg), paramtype in zip(enumerate(stmt.children), paramtypes):
        ret_reg = ctx.get_free_reg(asm)
        argtype = compile_expression(arg, ret_reg, ctx, asm)
        asm.append(f'mov r{i}, r{ret_reg}')
        ctx.release_reg(ret_reg, asm)

        if argtype != paramtype:
            print(f'Error, in call to {fn_name}, expected argument of type {paramtype}, got {argtype}')

    asm.append(f'bl {fn_name}')

    if target_reg:
        asm.append(f'mov r{target_reg}, r0')

    asm.append(f'pop {{r0-r3}} // Unspill after call to {fn_name} | free regs: {ctx.free_registers}')

    return ctx.functions[fn_name][0]