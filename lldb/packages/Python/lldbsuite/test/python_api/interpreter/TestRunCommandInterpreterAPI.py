"""Test the RunCommandInterpreter API."""

import os
import lldb
from lldbsuite.test.decorators import *
from lldbsuite.test.lldbtest import *

class CommandRunInterpreterAPICase(TestBase):

    mydir = TestBase.compute_mydir(__file__)

    def setUp(self):
        TestBase.setUp(self)

        self.stdin_path = self.getBuildArtifact("stdin.txt")

        #print("!!!", self.stdin_path)

        with open(self.stdin_path, 'w') as input_handle:
            input_handle.write("nonexistingcommand\nquit\n")

        self.input_handle = open(self.stdin_path, 'r')
        status = self.dbg.SetInputFile(lldb.SBFile.Create(self.input_handle, borrow=True))

        print("!!!", self.input_handle.fileno())
        print("!!!!!2", self.dbg.GetInputFile().GetFile().fileno())
        print("!!!!!3", self.dbg.GetInputFile().GetFile().fileno())
        print("!!!!!4", self.dbg.GetInputFile().GetFile().fileno())
        print("!!!!!5", self.dbg.GetInputFile().GetFile().fileno())

        self.assertEqual(self.input_handle.fileno(), self.dbg.GetInputFile().GetFile().fileno())
        self.assertTrue(status.Success())

        # x = bytearray(50)
        # self.dbg.GetInputFile().Read(x)
        # print("!!!!", x)


        # No need to track the output
        devnull = open(os.devnull, 'w')
        #self.dbg.SetOutputFileHandle(devnull, False)
        #self.dbg.SetErrorFileHandle(devnull, False)

    @add_test_categories(['pyapi'])
    def test_run_session_with_error_and_quit(self):
        """Run non-existing and quit command returns appropriate values"""

        print("!!!!!6", self.dbg.GetInputFile().GetFile().fileno())

        n_errors, quit_requested, has_crashed = self.dbg.RunCommandInterpreter(
                True, False, lldb.SBCommandInterpreterRunOptions(), 0, False,
                False)

        self.assertFalse(has_crashed)
        self.assertTrue(quit_requested)
        self.assertGreater(n_errors, 0)
