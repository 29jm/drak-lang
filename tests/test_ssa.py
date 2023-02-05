import unittest
import copy
from drak.middle_end.liveness import *
from drak.middle_end.ssa import *

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

class TestIRBlocks(unittest.TestCase):
    def test_phi_insertion(self):
        bblocks = basic_blocks(copy.deepcopy(simple_phi))
        cfg = control_flow_graph(bblocks)
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

    def test_simpliphying(self):
        bblocks = basic_blocks(simple_phi)
        cfg = control_flow_graph(bblocks)
        lifetimes = block_liveness2(bblocks, cfg)
        phi_inserted = phi_insertion(bblocks, cfg, lifetimes)
        ren = renumber_variables(phi_inserted, cfg)
        phi_solved = simpliphy(ren)
        has_phi = False
        for block in phi_solved:
            for instr in block:
                if instr[0] == 'PHI':
                    has_phi = True
        self.assertFalse(has_phi, 'Phi functions not eliminated completely')