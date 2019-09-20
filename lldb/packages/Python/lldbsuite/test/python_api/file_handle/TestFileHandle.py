"""
Test lldb lldb Python API for file handles.
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


class BadIO(io.TextIOBase):
    def writable(self):
        return True
    def write(self, s):
        raise Exception('OH NOE')


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

    def comment(self, *args):
        if self.session is not None:
            print(*args, file=self.session)

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
    def test_sbfile_write(self):
        try:
            with open('output', 'w') as f:
                sbf = lldb.SBFile()
                self.assertFalse(sbf.IsValid())
                sbf.SetDescriptor(f.fileno(), "w", False)
                self.assertTrue(sbf.IsValid())
                sbf.Write(b'FOO\nBAR')
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
                sbf = lldb.SBFile()
                sbf.SetDescriptor(f.fileno(), "r", False)
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
                sbf = lldb.SBFile()
                sbf.SetDescriptor(f.fileno(), "w", False)
                status = debugger.SetOutputFile(sbf)
                if status.Fail():
                    raise Exception(status)
                handle_command(debugger, 'script 1+2')

            with open('output', 'r') as f:
                self.assertEqual(f.read().strip(), '3')

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)

    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_file_out(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                status = debugger.SetOutputFile(f)
                if status.Fail():
                    raise Exception(status)
                handle_command(debugger, 'script 1+2')

            with open('output', 'r') as f:
                self.assertEqual(f.read().strip(), '3')

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)

    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_help(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                sbf = lldb.SBFile()
                sbf.SetDescriptor(f.fileno(), "w", False)
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
    def test_help(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                status = debugger.SetOutputFile(f)
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

            with open('output', 'r') as f:
                output = f.read()
                self.assertTrue(re.search(r'Show a list of all debugger commands', output))
                self.assertTrue(re.search(r'QUUX', output))

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_close(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:
                status = debugger.SetOutputFile(f)
                if status.Fail():
                    raise Exception(status)
                handle_command(debugger, "help help", collect_result=False)
                # make sure the file wasn't closed early.
                f.write("\nZAP\n")
                lldb.SBDebugger.Destroy(debugger)
                # check that output file was closed when debugger was destroyed.
                with self.assertRaises(ValueError):
                    f.write("\nQUUX\n")

            with open('output', 'r') as f:
                output = f.read()
                self.assertTrue(re.search(r'Show a list of all debugger commands', output))
                self.assertTrue(re.search(r'ZAP', output))

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

                outsbf = lldb.SBFile()
                outsbf.SetDescriptor(outf.fileno(), "w", False)
                status = debugger.SetOutputFile(outsbf)
                if status.Fail():
                    raise Exception(status)

                insbf = lldb.SBFile()
                insbf.SetDescriptor(inf.fileno(), "r", False)
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
    def test_inout(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('input', 'w') as f:
                f.write("help help\n")

            with open('output', 'w') as outf, open('input', 'r') as inf:

                status = debugger.SetOutputFile(outf)
                if status.Fail():
                    raise Exception(status)

                status = debugger.SetInputFile(inf)
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
    def test_binary_inout(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('input', 'w') as f:
                f.write("help help\n")

            with open('output', 'wb') as outf, open('input', 'rb') as inf:

                status = debugger.SetOutputFile(outf)
                if status.Fail():
                    raise Exception(status)

                status = debugger.SetInputFile(inf)
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

                sbf = lldb.SBFile()
                sbf.SetDescriptor(f.fileno(), 'w', False)
                status = debugger.SetErrorFile(sbf)
                if status.Fail():
                    raise Exception(status)

                handle_command(debugger, 'lolwut', raise_on_fail=False, collect_result=False)

            with open('output', 'r') as f:
                errors = f.read()
                self.assertTrue(re.search(r'error:.*lolwut', errors))

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_file_error(self):

        debugger = lldb.SBDebugger.Create()
        try:
            with open('output', 'w') as f:

                status = debugger.SetErrorFile(f)
                if status.Fail():
                    raise Exception(status)

                handle_command(debugger, 'lolwut', raise_on_fail=False, collect_result=False)

            with open('output', 'r') as f:
                errors = f.read()
                self.assertTrue(re.search(r'error:.*lolwut', errors))

        finally:
            self.RemoveTempFile('output')
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_legacy_file_error(self):

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
    @skipIf(py_version=['<', (3,)])
    def test_string_out(self):
        f = io.StringIO()
        debugger = lldb.SBDebugger.Create()
        try:
            status = debugger.SetOutputFile(f)
            if status.Fail():
                raise Exception(status)
            handle_command(debugger, "script 'foobar'")
            self.assertEqual(f.getvalue().strip(), "'foobar'")
        finally:
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_stdout(self):
        f = io.StringIO()
        debugger = lldb.SBDebugger.Create()
        try:
            status = debugger.SetOutputFile(f)
            if status.Fail():
                raise Exception(status)
            handle_command(debugger, r"script sys.stdout.write('foobar\n')")
            self.assertEqual(f.getvalue().strip(), "foobar\n7")
        finally:
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_string_error(self):

        f = io.StringIO()
        debugger = lldb.SBDebugger.Create()
        try:
            status = debugger.SetErrorFile(f)
            if status.Fail():
                raise Exception
            handle_command(debugger, 'lolwut', raise_on_fail=False, collect_result=False)

            errors = f.getvalue()
            self.assertTrue(re.search(r'error:.*lolwut', errors))

        finally:
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_string_inout(self):

        debugger = lldb.SBDebugger.Create()
        try:

            inf = io.StringIO("help help\nhelp b\n")
            outf = io.StringIO()

            status = debugger.SetOutputFile(outf)
            if status.Fail():
                raise Exception(status)

            status = debugger.SetInputFile(inf)
            if status.Fail():
                raise Exception(status)

            opts = lldb.SBCommandInterpreterRunOptions()
            debugger.RunCommandInterpreter(True, False, opts, 0, False, False)
            debugger.GetOutputFile().Flush()

            self.assertTrue(re.search(r'Show a list of all debugger commands', outf.getvalue()))
            self.assertTrue(re.search(r'Set a breakpoint', outf.getvalue()))

        finally:
            lldb.SBDebugger.Destroy(debugger)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_bytes_inout(self):

        debugger = lldb.SBDebugger.Create()
        try:

            inf = io.BytesIO(b"help help\nhelp b\n")
            outf = io.BytesIO()

            status = debugger.SetOutputFile(outf)
            if status.Fail():
                raise Exception(status)

            status = debugger.SetInputFile(inf)
            if status.Fail():
                raise Exception(status)

            opts = lldb.SBCommandInterpreterRunOptions()
            debugger.RunCommandInterpreter(True, False, opts, 0, False, False)
            debugger.GetOutputFile().Flush()

            self.assertTrue(re.search(b'Show a list of all debugger commands', outf.getvalue()))
            self.assertTrue(re.search(b'Set a breakpoint', outf.getvalue()))

        finally:
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


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_replace_stdout_with_nonfile(self):

        f = io.StringIO()

        with replace_stdout(f):

            class Nothing():
                pass

            debugger = lldb.SBDebugger.Create()
            try:
                with replace_stdout(Nothing):
                    self.assertEqual(sys.stdout, Nothing)
                    handle_command(debugger, 'script sys.stdout.write("lol")',
                        collect_result=False)
                    self.assertEqual(sys.stdout, Nothing)
            finally:
                lldb.SBDebugger.Destroy(debugger)

            sys.stdout.write(u"FOO")

        self.assertEqual(f.getvalue(), "FOO")


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_stream_error(self):

        messages = list()

        io = BadIO()
        debugger = lldb.SBDebugger.Create()
        try:
            debugger.SetOutputFile(io)
            debugger.SetLoggingCallback(messages.append)
            handle_command(debugger, 'log enable lldb script')
            handle_command(debugger, 'script 1')

        finally:
            lldb.SBDebugger.Destroy(debugger)

        self.comment(messages)
        self.assertTrue(any('OH NOE' in msg for msg in messages))


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_identity(self):
        f = io.StringIO()
        sbf = lldb.SBFile()
        sbf.SetFile(f)
        self.assertTrue(f is sbf.GetFile())
        sbf.Close()
        self.assertTrue(f.closed)

        f = io.StringIO()
        sbf.SetFileBorrowed(f)
        self.assertTrue(f is sbf.GetFile())
        sbf.Close()
        self.assertFalse(f.closed)

        try:
            with open('output', 'w') as f:
                sbf.SetFile(f)
                self.assertTrue(f is sbf.GetFile())
                sbf.Close()
                self.assertTrue(f.closed)

            with open('output', 'w') as f:
                sbf.SetFileBorrowed(f)
                self.assertFalse(f is sbf.GetFile())
                sbf.Write(b"foobar\n")
                self.assertEqual(f.fileno(), sbf.GetFile().fileno())
                sbf.Close()
                self.assertFalse(f.closed)

            with open('output', 'r') as f:
                self.assertEqual("foobar", f.read().strip())

            with open('output', 'wb') as f:
                sbf.SetFileBorrowedForcingUseOfScriptingIOMethods(f)
                self.assertTrue(f is sbf.GetFile())
                sbf.Write(b"foobar\n")
                self.assertEqual(f.fileno(), sbf.GetFile().fileno())
                sbf.Close()
                self.assertFalse(f.closed)

            with open('output', 'r') as f:
                self.assertEqual("foobar", f.read().strip())

            with open('output', 'wb') as f:
                sbf.SetFileForcingUseOfScriptingIOMethods(f)
                self.assertTrue(f is sbf.GetFile())
                sbf.Write(b"foobar\n")
                self.assertEqual(f.fileno(), sbf.GetFile().fileno())
                sbf.Close()
                self.assertTrue(f.closed)

            with open('output', 'r') as f:
                self.assertEqual("foobar", f.read().strip())


        finally:
            self.RemoveTempFile('output')
