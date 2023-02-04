import unittest
import copy
from drak.middle_end.ir_utils import *
from drak.middle_end.liveness import *
from drak.middle_end.ssa import *

"""
TODO: Split this file into smaller, module-sized test files.
"""

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

class TestIRBlocks(unittest.TestCase):
    fnblocks = [
        ['func_def', 'main'],
        ['push', ['r4-r12', 'lr']],
        ['mov', 'REG4', '#76'],
        ['mov', 'REG5', 'REG4'],
        ['mov', 'REG6', '#3'],
        ['cmp', 'REG5', 'REG6'],
        ['mov', 'REG5', '#1'],
        ['beq', '.main_cond_2'],
        ['mov', 'REG5', '#0'],
        ['.main_cond_2:'],
        ['bne', '.main_if_1'],
        ['mov', 'REG7', '#45'],
        ['mov', 'r0', 'REG7'],
        ['b', '.main_end'],
        ['.main_if_1:'],
        ['mov', 'REG8', '#2'],
        ['mov', 'REG9', 'REG4'],
        ['mul', 'REG8', 'REG9'],
        ['mov', 'r0', 'REG8'],
        ['b', '.main_end'],
        ['.main_end:'],
        ['add', 'sp', '#0'],
        ['pop', ['r4-r12', 'lr']],
        ['func_ret', 'r0']]

    fnblocks2 = [
        ['func_def', 'main'],
        ['push', ['r4-r12', 'lr']],
        ['mov', 'REG4', '#0'],
        ['mov', 'REG5', '#0'],
        ['.main_while_begin_1:'],
        ['mov', 'REG6', 'REG5'],
        ['mov', 'REG7', '#1000'],
        ['cmp', 'REG6', 'REG7'],
        ['bge', '.main_while_post_1'],
        ['mov', 'REG8', 'REG5'],
        ['mov', 'REG9', '#2'],
        ['mul', 'REG8', 'REG8', 'REG9'],
        ['mov', 'REG10', '#500'],
        ['cmp', 'REG8', 'REG10'],
        ['bge', '.main_if_2'],
        ['mov', 'REG11', 'REG5'],
        ['add', 'REG4', 'REG4', 'REG11'],
        ['.main_if_2:'],
        ['add', 'REG5', 'REG5', '#1'],
        ['b', '.main_while_begin_1'],
        ['.main_while_post_1:'],
        ['mov', 'REG12', '#0'],
        ['mov', 'r0', 'REG12'],
        ['b', '.main_end'],
        ['.main_end:'],
        ['add', 'sp', 'sp', '#0'],
        ['pop', ['r4-r12', 'lr']],
        ['func_ret', 'r0']]

    simple_phi = [
        ['func_def', 'main'],
        ['mov', 'REG4', '#50'],
        ['cmp', 'REG4', '#3'],
        ['bne', '.main_if_1'],
        ['mov', 'REG4', '#0'],
        ['b', '.main_if_2'],
        ['.main_if_1:'],
        ['mov', 'REG4', '#1'],
        ['.main_if_2:'],
        ['mov', 'r0', 'REG4'],
        ['b', '.main_end'],
        ['.main_end:'],
        ['func_ret', 'r0']]

    def test_basic_block_1(self):
        bblocks = basic_blocks(self.fnblocks)
        self.assertEqual(bblocks, [
            [ ['func_def', 'main'], #0
              ['push', ['r4-r12', 'lr']],
              ['mov', 'REG4', '#76'],
              ['mov', 'REG5', 'REG4'],
              ['mov', 'REG6', '#3'],
              ['cmp', 'REG5', 'REG6'],
              ['mov', 'REG5', '#1'],
              ['beq', '.main_cond_2'] ],
            [ ['mov', 'REG5', '#0'] ], # 1
            [ ['.main_cond_2:'], # 2
              ['bne', '.main_if_1'] ],
            [ ['mov', 'REG7', '#45'], # 3
              ['mov', 'r0', 'REG7'],
              ['b', '.main_end'] ],
            [ ['.main_if_1:'], # 4
              ['mov', 'REG8', '#2'],
              ['mov', 'REG9', 'REG4'],
              ['mul', 'REG8', 'REG9'],
              ['mov', 'r0', 'REG8'],
              ['b', '.main_end'] ],
            [ ['.main_end:'], # 5
              ['add', 'sp', '#0'],
              ['pop', ['r4-r12', 'lr']],
              ['func_ret', 'r0']]])

    def test_block_successors(self):
        bblocks = basic_blocks(self.fnblocks)
        self.assertEqual(block_successors(bblocks, 0), set([1, 2]))

    def test_control_flow_graph_1(self):
        bblocks = basic_blocks(self.fnblocks)
        cfg = control_flow_graph(bblocks)
        self.assertEqual(cfg, {
            0: set([1, 2]),
            1: set([2]),
            2: set([3, 4]),
            3: set([5]),
            4: set([5]),
            5: set()
        })

    def test_dominator_sets(self):
        bblocks = basic_blocks(self.fnblocks)
        cfg = control_flow_graph(bblocks)
        dom_sets = dominator_sets(cfg)
        self.assertEqual(dom_sets, {
            0: set([0]),
            1: set([0, 1]),
            2: set([0, 2]),
            3: set([0, 2, 3]),
            4: set([0, 2, 4]),
            5: set([0, 2, 5]),
        })

    def test_immediate_dominators(self):
        bblocks = basic_blocks(self.fnblocks)
        cfg = control_flow_graph(bblocks)
        idoms = immediate_dominators(cfg)
        self.assertEqual(idoms, {
            0: set(),
            1: 0,
            2: 0,
            3: 2,
            4: 2,
            5: 2
        })

    def test_dominance_frontier(self):
        cfg = {
            0: set([1]),
            1: set([5, 2]),
            2: set([3, 4]),
            3: set([4]),
            4: set([1]),
            5: set() }
        df = dominance_frontier(cfg)
        self.assertEqual(df, {
            0: set(),
            1: set([1]),
            2: set([1]),
            3: set([4]),
            4: set([1]),
        })

    def test_dominance_frontier(self):
        cfg = {
            0: set([1]),
            1: set([-1, 2]),
            2: set([3, 4]),
            3: set([4]),
            4: set([1]) }
        df = dominance_frontier(cfg)

    def test_block_liveness(self):
        bblocks = basic_blocks(self.fnblocks2)
        cfg = control_flow_graph(bblocks)
        lives = block_liveness2(bblocks, cfg)
        self.assertEqual(lives, {
            0: set(),
            1: set(['REG4', 'REG5']),
            2: set(['REG4', 'REG5']),
            3: set(['REG4', 'REG5']),
            4: set(['REG4', 'REG5']),
            5: set([]),
            6: set([]),
        })

    def test_phi_insertion(self):
        bblocks = basic_blocks(copy.deepcopy(self.simple_phi))
        cfg = control_flow_graph(bblocks)
        df = dominance_frontier(cfg)
        lifetimes = block_liveness2(bblocks, cfg)
        phi_inserted = phi_insertion(bblocks, cfg, lifetimes)
        phi_instr = phi_inserted[3][1]
        self.assertEqual(phi_instr[0], 'PHI')
        self.assertEqual(phi_instr[1], 'REG4')
        self.assertEqual(phi_instr[2][0], 'REG4')
        self.assertEqual(phi_instr[2][1], 'REG4')

    def test_renumbering_writes(self):
        instr = ['mov', 'REG4', 'REG5']
        self.assertEqual(
            renumber_written(instr, 'REG4', 'renamed'),
            ['mov', 'renamed', 'REG5'])
        instr = ['mov', 'REG4', 'REG5']
        self.assertEqual(
            renumber_written(instr, 'REG5', 'renamed'),
            ['mov', 'REG4', 'REG5'])
        instr = ['add', 'REG4', 'REG4', 'REG4']
        self.assertEqual(
            renumber_written(instr, 'REG4', 'renamed'),
            ['add', 'renamed', 'REG4', 'REG4'])
        instr = ['push', ['REG4', 'REG5', 'lr']]
        self.assertEqual(
            renumber_written(instr, 'REG4', 'renamed'),
            instr)
        instr = ['PHI', 'REG4', ['REG4', 'REG5', 'lr']]
        self.assertEqual(
            renumber_written(instr, 'REG4', 'renamed'),
            ['PHI', 'renamed', ['REG4', 'REG5', 'lr']])
        instr = ['PHI', 'REG4', ['REG4', 'REG5', 'lr']]
        self.assertEqual(
            renumber_written(instr, 'REG5', 'renamed'),
            ['PHI', 'REG4', ['REG4', 'REG5', 'lr']])

    def test_renumbering_reads(self):
        instr = ['mov', 'REG4', 'REG5']
        self.assertEqual(
            renumber_read(instr, 'REG4', 'renamed'),
            instr)
        instr = ['mov', 'REG4', 'REG5']
        self.assertEqual(
            renumber_read(instr, 'REG5', 'renamed'),
            ['mov', 'REG4', 'renamed'])
        instr = ['add', 'REG4', 'REG4', 'REG4']
        self.assertEqual(
            renumber_read(instr, 'REG4', 'renamed'),
            ['add', 'REG4', 'renamed', 'renamed'])
        instr = ['push', ['REG4', 'REG5', 'lr']]
        self.assertEqual(
            renumber_read(instr, 'REG4', 'renamed'),
            ['push', ['renamed', 'REG5', 'lr']])
        instr = ['PHI', 'REG4', ['REG4', 'REG5', 'lr']]
        self.assertEqual(
            renumber_read(instr, 'REG4', 'renamed'),
            ['PHI', 'REG4', ['renamed', 'REG5', 'lr']])
        instr = ['PHI', 'REG4', ['REG4', 'REG5', 'lr']]
        self.assertEqual(
            renumber_read(instr, 'REG4', 'renamed'),
            ['PHI', 'REG4', ['renamed', 'REG5', 'lr']])

    def test_renumering(self):
        bblocks = basic_blocks(copy.deepcopy(self.simple_phi))
        cfg = control_flow_graph(bblocks)
        lifetimes = block_liveness2(bblocks, cfg)
        with_phis = phi_insertion(bblocks, cfg, lifetimes)
        ren = renumber_variables(with_phis, cfg)
        self.assertTrue(True)

    def test_simpliphying(self):
        bblocks = basic_blocks(self.simple_phi)
        cfg = control_flow_graph(bblocks)
        df = dominance_frontier(cfg)
        lifetimes = block_liveness2(bblocks, cfg)
        phi_inserted = phi_insertion(bblocks, cfg, lifetimes)
        ren = renumber_variables(phi_inserted, cfg)
        phi_solved = simpliphy(ren)
        pass
        # phi_instr = phi_inserted[3][1]
        # self.assertEqual(phi_instr[0], 'PHI')
        # self.assertEqual(phi_instr[1], 'REG4')
        # self.assertEqual(phi_instr[2][0], 'REG4')
        # self.assertEqual(phi_instr[2][1], 'REG4')

if __name__ == '__main__':
    unittest.main()