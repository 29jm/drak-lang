import unittest
from drak.middle_end.ir_utils import *
from drak.middle_end.graph_ops import *
from drak.middle_end.liveness import *

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

class TestLiveness(unittest.TestCase):
    def test_block_liveness(self):
        bblocks = basic_blocks(fnblocks2)
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