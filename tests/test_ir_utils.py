import unittest
from drak.middle_end.ir_utils import *

class TestIRClassifiers(unittest.TestCase):
    def test_is_jump(self):
        instr = ['b', '.main_end']
        self.assertTrue(is_jumping(instr))
        instr = ['bx', 'lr']
        self.assertTrue(is_jumping(instr))
        instr = ['beq', '.main_cond_2']
        self.assertTrue(is_jumping(instr))
        instr = ['bne', '.main_if_1']
        self.assertTrue(is_jumping(instr))
        instr = ['blt', '.main_if_1']
        self.assertTrue(is_jumping(instr))
        instr = ['ble', '.main_if_1']
        self.assertTrue(is_jumping(instr))
        instr = ['bgt', '.main_if_1']
        self.assertTrue(is_jumping(instr))
        instr = ['bge', '.main_if_1']
        self.assertTrue(is_jumping(instr))
        instr = ['func_call', '_start']
        self.assertTrue(is_jumping(instr))
        instr = ['func_ret', 'r0']
        self.assertTrue(is_jumping(instr))

    def test_is_not_jump(self):
        instr = ['bic', 'REG1', 'REG2', 'REG3']
        self.assertFalse(is_jumping(instr))
        instr = ['bfi', 'REG1', 'REG2']
        self.assertFalse(is_jumping(instr))
        instr = ['bfc', 'REG1', 'REG2']
        self.assertFalse(is_jumping(instr))
        instr = ['bkpt', '#0']
        self.assertFalse(is_jumping(instr))

class TestIRReadWrite(unittest.TestCase):
    def test_push_written(self):
        instr = ['push', ['r4-r12', 'lr']]
        self.assertEqual(vars_written_by(instr), [])
        instr = ['push', ['REG4', 'REG10']]
        self.assertEqual(vars_written_by(instr), [])

    def test_push_read(self):
        instr = ['push', ['r4-r12', 'lr']]
        self.assertEqual(vars_read_by(instr), [])
        instr = ['push', ['REG4', 'REG10']]
        self.assertEqual(vars_read_by(instr), ['REG4', 'REG10'])

    def test_pop_written(self):
        instr = ['pop', ['r4-r12', 'lr']]
        self.assertEqual(vars_written_by(instr), [])
        instr = ['pop', ['REG4', 'REG10']]
        self.assertEqual(vars_written_by(instr), ['REG4', 'REG10'])
        instr = ['pop', ['r1', 'REG9']]
        self.assertEqual(vars_written_by(instr), ['REG9'])

    def test_pop_read(self):
        instr = ['pop', ['r4-r12', 'lr']]
        self.assertEqual(vars_read_by(instr), [])
        instr = ['pop', ['REG4', 'REG10']]
        self.assertEqual(vars_read_by(instr), [])
        instr = ['pop', ['r1', 'REG10']]
        self.assertEqual(vars_read_by(instr), [])

    def test_mov_read(self):
        instr = ['mov', 'r1', '#76']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['mov', 'r1', 'REG4']
        self.assertEqual(vars_read_by(instr), ['REG4'])
        instr = ['mov', 'r1', 'r4']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['mov', 'REG5', 'r4']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['mov', 'REG5', 'REG6']
        self.assertEqual(vars_read_by(instr), ['REG6'])

    def test_mov_written(self):
        instr = ['mov', 'r1', '#76']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['mov', 'r1', 'REG4']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['mov', 'r1', 'r4']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['mov', 'REG5', 'r4']
        self.assertEqual(vars_written_by(instr), ['REG5'])
        instr = ['mov', 'REG5', 'REG6']
        self.assertEqual(vars_written_by(instr), ['REG5'])

    def test_memstore_read(self):
        instr = ['memstore', 'REG3', ['STACKID34', '#4']]
        self.assertEqual(vars_read_by(instr), ['REG3'])

    def test_memstore_written(self):
        instr = ['memstore', 'REG3', ['STACKID34', '#4']]
        self.assertEqual(vars_written_by(instr), [])

    def test_cmp_read(self):
        instr = ['cmp', 'r1', '#76']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['cmp', 'r1', 'REG4']
        self.assertEqual(vars_read_by(instr), ['REG4'])
        instr = ['cmp', 'r1', 'r4']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['cmp', 'REG5', 'r4']
        self.assertEqual(vars_read_by(instr), ['REG5'])
        instr = ['cmp', 'REG5', 'REG6']
        self.assertEqual(vars_read_by(instr), ['REG5', 'REG6'])

    def test_cmp_written(self):
        instr = ['cmp', 'r1', '#76']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['cmp', 'r1', 'REG4']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['cmp', 'r1', 'r4']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['cmp', 'REG5', 'r4']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['cmp', 'REG5', 'REG6']
        self.assertEqual(vars_written_by(instr), [])

    def test_add_written(self):
        instr = ['add', 'sp', '#0']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['add', 'r1', '#10']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['add', 'REG5', '#10']
        self.assertEqual(vars_written_by(instr), ['REG5'])
        instr = ['add', 'REG5', 'REG6']
        self.assertEqual(vars_written_by(instr), ['REG5'])
        instr = ['add', 'REG5', 'REG6', 'REG7']
        self.assertEqual(vars_written_by(instr), ['REG5'])

    def test_add_read(self):
        instr = ['add', 'sp', '#0']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['add', 'r1', '#10']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['add', 'REG5', '#10']
        self.assertEqual(vars_read_by(instr), ['REG5'])
        instr = ['add', 'REG5', 'REG6']
        self.assertEqual(vars_read_by(instr), ['REG5', 'REG6'])
        instr = ['add', 'REG5', 'REG6', 'REG7']
        self.assertEqual(vars_read_by(instr), ['REG6', 'REG7'])

    def test_sub_written(self):
        instr = ['sub', 'sp', '#0']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['sub', 'r1', '#10']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['sub', 'REG5', '#10']
        self.assertEqual(vars_written_by(instr), ['REG5'])
        instr = ['sub', 'REG5', 'REG6']
        self.assertEqual(vars_written_by(instr), ['REG5'])
        instr = ['sub', 'REG5', 'REG6', 'REG7']
        self.assertEqual(vars_written_by(instr), ['REG5'])

    def test_sub_read(self):
        instr = ['sub', 'sp', '#0']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['sub', 'r1', '#10']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['sub', 'REG5', '#10']
        self.assertEqual(vars_read_by(instr), ['REG5'])
        instr = ['sub', 'REG5', 'REG6']
        self.assertEqual(vars_read_by(instr), ['REG5', 'REG6'])
        instr = ['sub', 'REG5', 'REG6', 'REG7']
        self.assertEqual(vars_read_by(instr), ['REG6', 'REG7'])

    def test_mul_written(self):
        instr = ['mul', 'r4', 'r5']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['mul', 'REG5', 'REG6']
        self.assertEqual(vars_written_by(instr), ['REG5'])
        instr = ['mul', 'REG5', 'r1']
        self.assertEqual(vars_written_by(instr), ['REG5'])
        instr = ['mul', 'REG5', 'REG6', 'REG7']
        self.assertEqual(vars_written_by(instr), ['REG5'])

    def test_mul_read(self):
        instr = ['mul', 'r4', 'r5']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['mul', 'REG5', 'REG6']
        self.assertEqual(vars_read_by(instr), ['REG5', 'REG6'])
        instr = ['mul', 'REG5', 'r1']
        self.assertEqual(vars_read_by(instr), ['REG5'])
        instr = ['mul', 'REG5', 'REG6', 'REG7']
        self.assertEqual(vars_read_by(instr), ['REG6', 'REG7'])

    def test_bx_written(self):
        instr = ['bx', 'r4']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['bx', 'REG5']
        self.assertEqual(vars_written_by(instr), ['REG5'])

    def test_bx_read(self):
        instr = ['bx', 'r4']
        self.assertEqual(vars_read_by(instr), [])
        instr = ['bx', 'REG5']
        self.assertEqual(vars_read_by(instr), ['REG5'])

    def test_func_call_read(self):
        instr = ['func_call', 'main', ['REGF0', 'REGF5']]
        self.assertEqual(vars_read_by(instr), ['REGF0', 'REGF5'])
        instr = ['func_call', 'test', ['REGF0', 'REGF1'], ['REGF0', 'REGF1', 'REGF2']]
        self.assertEqual(vars_read_by(instr), ['REGF0', 'REGF1'])
        instr = ['func_call', '_start', [], ['REGF0']]
        self.assertEqual(vars_read_by(instr), [])

    def test_func_call_written(self):
        instr = ['func_call', 'main', ['REGF0', 'REGF5']]
        self.assertEqual(vars_written_by(instr), [])
        instr = ['func_call', 'test', ['REGF0', 'REGF1'], ['REGF0', 'REGF1', 'REGF2']]
        self.assertEqual(vars_written_by(instr), ['REGF0', 'REGF1', 'REGF2'])
        instr = ['func_call', '_start', [], ['REGF0']]
        self.assertEqual(vars_written_by(instr), ['REGF0'])

    def test_func_ret_read(self):
        instr = ['func_ret', 'REGF0']
        self.assertEqual(vars_read_by(instr), ['REGF0'])
        instr = ['func_ret']
        self.assertEqual(vars_read_by(instr), [])

    def test_func_ret_written(self):
        instr = ['func_ret', 'REGF0']
        self.assertEqual(vars_written_by(instr), [])
        instr = ['func_ret']
        self.assertEqual(vars_written_by(instr), [])