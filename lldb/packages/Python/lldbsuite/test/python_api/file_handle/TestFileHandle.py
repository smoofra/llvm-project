"""
Test lldb Python API for file handles.
"""

from __future__ import print_function

import contextlib
import os
import io
import re
import sys

import lldb
from lldbsuite.test.decorators import *
from lldbsuite.test.lldbtest import *
from lldbsuite.test import lldbutil


def readStrippedLines(f):
    def i():
        for line in f:
            line = line.strip()
            if line:
                yield line
    return list(i())

def handle_command(debugger, cmd, raise_on_fail=True, collect_result=True):

    ret = lldb.SBCommandReturnObject()

    if collect_result:
        interpreter = debugger.GetCommandInterpreter()
        interpreter.HandleCommand(cmd, ret)
    else:
        debugger.HandleCommand(cmd)

    if collect_result and raise_on_fail and not ret.Succeeded():
        raise Exception

    return ret.GetOutput()


class FileHandleTestCase(TestBase):

    mydir = TestBase.compute_mydir(__file__)

    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_legacy_file_out(self):
        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                debugger.SetOutputFileHandle(f, False)
                handle_command(debugger, 'script 1+1')
                debugger.GetOutputFileHandle().write('FOO\n')
            with open('output', 'r') as f:
                self.assertEqual(readStrippedLines(f), ['2', 'FOO'])
        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_legacy_file_err(self):
        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                debugger.SetErrorFileHandle(f, False)
                handle_command(debugger, 'lol', raise_on_fail=False, collect_result=False)
            lldb.SBDebugger.Destroy(debugger)
            with open('output', 'r') as f:
                self.assertTrue(re.search("is not a valid command", f.read()))
        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_invalid(self):
        sbf = lldb.SBFile()
        self.assertFalse(sbf.IsValid())
        e, n = sbf.Write(b'foo')
        self.assertTrue(e.Fail())
        self.assertEqual(n, 0)
        buffer = bytearray(100)
        e, n = sbf.Read(buffer)
        self.assertEqual(n, 0)
        self.assertTrue(e.Fail())


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_write(self):
        try:
            with open('output', 'w') as f:
                sbf = lldb.SBFile(f.fileno(), "w", False)
                self.assertTrue(sbf.IsValid())
                e, n = sbf.Write(b'FOO\nBAR')
                self.assertTrue(e.Success())
                self.assertEqual(n, 7)
                sbf.Close()
                self.assertFalse(sbf.IsValid())

            with open('output', 'r') as f:
                self.assertEqual(readStrippedLines(f), ['FOO', 'BAR'])
        finally:
            self.RemoveTempFile('output')


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_read(self):
        try:
            with open('output', 'w') as f:
                f.write('FOO')
            with open('output', 'r') as f:
                sbf = lldb.SBFile(f.fileno(), "r", False)
                self.assertTrue(sbf.IsValid())
                buffer = bytearray(100)
                e, n = sbf.Read(buffer)
                self.assertTrue(e.Success())
                self.assertEqual(buffer[:n], b'FOO')
        finally:
            self.RemoveTempFile('output')






