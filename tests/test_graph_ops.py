import unittest
from drak.middle_end.ir_utils import *
from drak.middle_end.graph_ops import *

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

class TestIRBlocks(unittest.TestCase):
    def test_basic_block_1(self):
        bblocks = basic_blocks(fnblocks)
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
        bblocks = basic_blocks(fnblocks)
        self.assertEqual(block_successors(bblocks, 0), set([1, 2]))

    def test_control_flow_graph_1(self):
        bblocks = basic_blocks(fnblocks)
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
        bblocks = basic_blocks(fnblocks)
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
        bblocks = basic_blocks(fnblocks)
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