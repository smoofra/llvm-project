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


@contextlib.contextmanager
def replace_stdout(new):
    old = sys.stdout
    sys.stdout = new
    try:
        yield
    finally:
        sys.stdout = old

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

    debugger.GetOutputFile().Flush()
    debugger.GetErrorFile().Flush()

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
    def test_legacy_file_err_with_get(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                debugger.SetErrorFileHandle(f, False)
                handle_command(debugger, 'lolwut', raise_on_fail=False, collect_result=False)
                debugger.GetErrorFileHandle().write('FOOBAR\n')

            with open('output', 'r') as f:
                errors = f.read()
                self.assertTrue(re.search(r'error:.*lolwut', errors))
                self.assertTrue(re.search(r'FOOBAR', errors))

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


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_out(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                sbf = lldb.SBFile(f.fileno(), "w", False)
                status = debugger.SetOutputFile(sbf)
                if status.Fail():
                    raise Exception(status)
                handle_command(debugger, 'script 1+2')
                debugger.GetOutputFile().Write(b'quux')

            with open('output', 'r') as f:
                self.assertEqual(readStrippedLines(f), ['3', 'quux'])

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)

    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_help(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                sbf = lldb.SBFile(f.fileno(), "w", False)
                status = debugger.SetOutputFile(sbf)
                if status.Fail():
                    raise Exception(status)
                handle_command(debugger, "help help", collect_result=False)

            with open('output', 'r') as f:
                self.assertTrue(re.search(r'Show a list of all debugger commands', f.read()))

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_immediate(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                ret = lldb.SBCommandReturnObject()
                ret.SetImmediateOutputFile(f)
                interpreter = debugger.GetCommandInterpreter()
                interpreter.HandleCommand("help help", ret)
                # make sure the file wasn't closed early.
                f.write("\nQUUX\n")

            ret = None # call destructor and flush streams

            with open('output', 'r') as f:
                output = f.read()
                self.assertTrue(re.search(r'Show a list of all debugger commands', output))
                self.assertTrue(re.search(r'QUUX', output))

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_inout(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('input', 'w') as f:
                f.write("help help\n")

            with open('output', 'w') as outf, open('input', 'r') as inf:

                outsbf = lldb.SBFile(outf.fileno(), "w", False)
                status = debugger.SetOutputFile(outsbf)
                if status.Fail():
                    raise Exception(status)

                insbf = lldb.SBFile(inf.fileno(), "r", False)
                status = debugger.SetInputFile(insbf)
                if status.Fail():
                    raise Exception(status)

                opts = lldb.SBCommandInterpreterRunOptions()
                debugger.RunCommandInterpreter(True, False, opts, 0, False, False)
                debugger.GetOutputFile().Flush()

            with open('output', 'r') as f:
                self.assertTrue(re.search(r'Show a list of all debugger commands', f.read()))

        finally:
            self.RemoveTempFile('output')
            self.RemoveTempFile('input')
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_error(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:

                sbf = lldb.SBFile(f.fileno(), 'w', False)
                status = debugger.SetErrorFile(sbf)
                if status.Fail():
                    raise Exception(status)

                handle_command(debugger, 'lolwut', raise_on_fail=False, collect_result=False)

                debugger.GetErrorFile().Write(b'\nzork\n')

            with open('output', 'r') as f:
                errors = f.read()
                self.assertTrue(re.search(r'error:.*lolwut', errors))
                self.assertTrue(re.search(r'zork', errors))

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)



    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_replace_stdout(self):
        f = io.StringIO()
        debugger = lldb.SBDebugger.Create()
        try:
            with replace_stdout(f):
                self.assertEqual(sys.stdout, f)
                handle_command(debugger, 'script sys.stdout.write("lol")',
                    collect_result=False)
                self.assertEqual(sys.stdout, f)
        finally:
            lldb.SBDebugger.Destroy(debugger)

