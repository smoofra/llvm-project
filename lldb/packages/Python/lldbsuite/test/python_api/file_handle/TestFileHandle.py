"""
Test lldb Python API for file handles.
"""

from __future__ import print_function

import os
import io
import re
import sys
from contextlib import contextmanager

import lldb
from lldbsuite.test import  lldbtest
from lldbsuite.test.decorators import (
    add_test_categories, no_debug_info_test, skipIf)

class OhNoe(Exception):
    pass

class BadIO(io.TextIOBase):
    def writable(self):
        return True
    def readable(self):
        return True
    def write(self, s):
        raise OhNoe('OH NOE')
    def read(self, n):
        raise OhNoe("OH NOE")

class ReallyBadIO(io.TextIOBase):
    def writable(self):
        raise OhNoe("OH NOE!!!")

class MutableBool():
    def __init__(self, value):
        self.value = value
    def set(self, value):
        self.value = bool(value)
    def __bool__(self):
        return self.value

@contextmanager
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


class FileHandleTestCase(lldbtest.TestBase):

    mydir = lldbtest.Base.compute_mydir(__file__)

    # The way this class interacts with the debugger is different
    # than normal.   Most of these test cases will mess with the
    # debugger I/O streams, so we want a fresh debugger for each
    # test so those mutations don't interfere with each other.
    #
    # Also, the way normal tests evaluate debugger commands is
    # by using a SBCommandInterpreter directly, which captures
    # the output in a result object.   For many of tests tests
    # we want the debugger to write the  output directly to
    # its I/O streams like it would have done interactively.
    #
    # For this reason we also define handleCmd() here, even though
    # it is similar to runCmd().

    def setUp(self):
        super(FileHandleTestCase, self).setUp()
        self.debugger = lldb.SBDebugger.Create()
        self.out_filename = self.getBuildArtifact('output')
        self.in_filename = self.getBuildArtifact('input')

    def tearDown(self):
        lldb.SBDebugger.Destroy(self.debugger)
        super(FileHandleTestCase, self).tearDown()
        for name in (self.out_filename, self.in_filename):
            if os.path.exists(name):
                os.unlink(name)

    # Similar to runCmd(), but this uses the per-test debugger, and it
    # supports, letting the debugger just print the results instead
    # of collecting them.
    def handleCmd(self, cmd, check=True, collect_result=True):
        assert not check or collect_result
        ret = lldb.SBCommandReturnObject()
        if collect_result:
            interpreter = self.debugger.GetCommandInterpreter()
            interpreter.HandleCommand(cmd, ret)
        else:
            self.debugger.HandleCommand(cmd)
        self.debugger.GetOutputFile().Flush()
        self.debugger.GetErrorFile().Flush()
        if collect_result and check:
            self.assertTrue(ret.Succeeded())
        return ret.GetOutput()


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_legacy_file_out_script(self):
        with open(self.out_filename, 'w') as f:
            self.debugger.SetOutputFileHandle(f, False)
            # scripts print to output even if you capture the results
            # I'm not sure I love that behavior, but that's the way
            # it's been for a long time.  That's why this test works
            # even with collect_result=True.
            self.handleCmd('script 1+1')
            self.debugger.GetOutputFileHandle().write('FOO\n')
        with open(self.out_filename, 'r') as f:
            self.assertEqual(readStrippedLines(f), ['2', 'FOO'])


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_legacy_file_out(self):
        with open(self.out_filename, 'w') as f:
            self.debugger.SetOutputFileHandle(f, False)
            self.handleCmd('p/x 3735928559', collect_result=False, check=False)
        lldb.SBDebugger.Destroy(self.debugger)
        with open(self.out_filename, 'r') as f:
            self.assertIn('deadbeef', f.read())

    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_legacy_file_err_with_get(self):
        with open(self.out_filename, 'w') as f:
            self.debugger.SetErrorFileHandle(f, False)
            self.handleCmd('lolwut', check=False, collect_result=False)
            self.debugger.GetErrorFileHandle().write('FOOBAR\n')

        with open(self.out_filename, 'r') as f:
            errors = f.read()
            self.assertTrue(re.search(r'error:.*lolwut', errors))
            self.assertTrue(re.search(r'FOOBAR', errors))


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_legacy_file_err(self):
        with open(self.out_filename, 'w') as f:
            self.debugger.SetErrorFileHandle(f, False)
            self.handleCmd('lol', check=False, collect_result=False)
        lldb.SBDebugger.Destroy(self.debugger)
        with open(self.out_filename, 'r') as f:
            self.assertIn("is not a valid command", f.read())


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_type_errors(self):
        sbf = lldb.SBFile()
        self.assertRaises(TypeError, sbf.Write, None)
        self.assertRaises(TypeError, sbf.Read, None)
        self.assertRaises(TypeError, sbf.Read, b'this bytes is not mutable')
        self.assertRaises(TypeError, sbf.Write, u"ham sandwich")
        self.assertRaises(TypeError, sbf.Read, u"ham sandwich")


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_write(self):
        with open(self.out_filename, 'w') as f:
            sbf = lldb.SBFile(f.fileno(), "w", False)
            self.assertTrue(sbf.IsValid())
            e, n = sbf.Write(b'FOO\nBAR')
            self.assertTrue(e.Success())
            self.assertEqual(n, 7)
            sbf.Close()
            self.assertFalse(sbf.IsValid())
        with open(self.out_filename, 'r') as f:
            self.assertEqual(readStrippedLines(f), ['FOO', 'BAR'])


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_read(self):
        with open(self.out_filename, 'w') as f:
            f.write('FOO')
        with open(self.out_filename, 'r') as f:
            sbf = lldb.SBFile(f.fileno(), "r", False)
            self.assertTrue(sbf.IsValid())
            buffer = bytearray(100)
            e, n = sbf.Read(buffer)
            self.assertTrue(e.Success())
            self.assertEqual(buffer[:n], b'FOO')


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_out(self):
        with open(self.out_filename, 'w') as f:
            sbf = lldb.SBFile(f.fileno(), "w", False)
            status = self.debugger.SetOutputFile(sbf)
            if status.Fail():
                raise Exception(status)
            self.handleCmd('script 1+2')
            self.debugger.GetOutputFile().Write(b'quux')

        with open(self.out_filename, 'r') as f:
            self.assertEqual(readStrippedLines(f), ['3', 'quux'])


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_help(self):
        with open(self.out_filename, 'w') as f:
            sbf = lldb.SBFile(f.fileno(), "w", False)
            status = self.debugger.SetOutputFile(sbf)
            if status.Fail():
                raise Exception(status)
            self.handleCmd("help help", collect_result=False, check=False)
        with open(self.out_filename, 'r') as f:
            self.assertTrue(re.search(r'Show a list of all debugger commands', f.read()))


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_immediate(self):
        with open(self.out_filename, 'w') as f:
            ret = lldb.SBCommandReturnObject()
            ret.SetImmediateOutputFile(f)
            interpreter = self.debugger.GetCommandInterpreter()
            interpreter.HandleCommand("help help", ret)
            # make sure the file wasn't closed early.
            f.write("\nQUUX\n")

        ret = None # call destructor and flush streams

        with open(self.out_filename, 'r') as f:
            output = f.read()
            self.assertTrue(re.search(r'Show a list of all debugger commands', output))
            self.assertTrue(re.search(r'QUUX', output))


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_inout(self):
        with open(self.in_filename, 'w') as f:
            f.write("help help\n")

        with open(self.out_filename, 'w') as outf, open(self.in_filename, 'r') as inf:

            outsbf = lldb.SBFile(outf.fileno(), "w", False)
            status = self.debugger.SetOutputFile(outsbf)
            if status.Fail():
                raise Exception(status)

            insbf = lldb.SBFile(inf.fileno(), "r", False)
            status = self.debugger.SetInputFile(insbf)
            if status.Fail():
                raise Exception(status)

            opts = lldb.SBCommandInterpreterRunOptions()
            self.debugger.RunCommandInterpreter(True, False, opts, 0, False, False)
            self.debugger.GetOutputFile().Flush()

        with open(self.out_filename, 'r') as f:
            self.assertTrue(re.search(r'Show a list of all debugger commands', f.read()))


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_fileno_error(self):
        with open(self.out_filename, 'w') as f:

            sbf = lldb.SBFile(f.fileno(), 'w', False)
            status = self.debugger.SetErrorFile(sbf)
            if status.Fail():
                raise Exception(status)

            self.handleCmd('lolwut', check=False, collect_result=False)

            self.debugger.GetErrorFile().Write(b'\nzork\n')

        with open(self.out_filename, 'r') as f:
            errors = f.read()
            self.assertTrue(re.search(r'error:.*lolwut', errors))
            self.assertTrue(re.search(r'zork', errors))


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_replace_stdout(self):
        f = io.StringIO()
        with replace_stdout(f):
            self.assertEqual(sys.stdout, f)
            self.handleCmd('script sys.stdout.write("lol")',
                collect_result=False, check=False)
            self.assertEqual(sys.stdout, f)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_write2(self):
        with open(self.out_filename, 'w') as f:
            sbf = lldb.SBFile(f)
            e, n = sbf.Write(b'FOO\n')
            self.assertTrue(e.Success())
            self.assertEqual(n, 4)
            sbf.Close()
            self.assertTrue(f.closed)
        with open(self.out_filename, 'r') as f:
            self.assertEqual(f.read().strip(), 'FOO')


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_read2(self):
        with open(self.out_filename, 'w') as f:
            f.write('foo')
        with open(self.out_filename, 'r') as f:
            sbf = lldb.SBFile(f)
            buf = bytearray(100)
            e, n = sbf.Read(buf)
            self.assertTrue(e.Success())
            self.assertEqual(n, 3)
            self.assertEqual(buf[:n], b'foo')
            sbf.Close()
            self.assertTrue(f.closed)


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_write_borrowed(self):
        with open(self.out_filename, 'w') as f:
            sbf = lldb.SBFile(lldb.FileBorrow(), f)
            e, n = sbf.Write(b'FOO')
            self.assertTrue(e.Success())
            self.assertEqual(n, 3)
            sbf.Close()
            self.assertFalse(f.closed)
            f.write('BAR\n')
        with open(self.out_filename, 'r') as f:
            self.assertEqual(f.read().strip(), 'FOOBAR')



    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_sbfile_write_forced(self):
        with open(self.out_filename, 'w') as f:
            written = MutableBool(False)
            orig_write = f.write
            def mywrite(x):
                written.set(True)
                return orig_write(x)
            f.write = mywrite
            sbf = lldb.SBFile(lldb.FileForceScriptingIO(), f)
            e, n = sbf.Write(b'FOO')
            self.assertTrue(written)
            self.assertTrue(e.Success())
            self.assertEqual(n, 3)
            sbf.Close()
            self.assertTrue(f.closed)
        with open(self.out_filename, 'r') as f:
            self.assertEqual(f.read().strip(), 'FOO')


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_sbfile_write_forced_borrowed(self):
        with open(self.out_filename, 'w') as f:
            written = MutableBool(False)
            orig_write = f.write
            def mywrite(x):
                written.set(True)
                return orig_write(x)
            f.write = mywrite
            sbf = lldb.SBFile(lldb.FileBorrowAndForceScriptingIO(), f)
            e, n = sbf.Write(b'FOO')
            self.assertTrue(written)
            self.assertTrue(e.Success())
            self.assertEqual(n, 3)
            sbf.Close()
            self.assertFalse(f.closed)
        with open(self.out_filename, 'r') as f:
            self.assertEqual(f.read().strip(), 'FOO')


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_sbfile_write_string(self):
        f = io.StringIO()
        sbf = lldb.SBFile(f)
        e, n = sbf.Write(b'FOO')
        self.assertEqual(f.getvalue().strip(), "FOO")
        self.assertTrue(e.Success())
        self.assertEqual(n, 3)

    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_sbfile_write_bytes(self):
        f = io.BytesIO()
        sbf = lldb.SBFile(f)
        e, n = sbf.Write(b'FOO')
        self.assertEqual(f.getvalue().strip(), b"FOO")
        self.assertTrue(e.Success())
        self.assertEqual(n, 3)

    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_sbfile_read_string(self):
        f = io.StringIO('zork')
        sbf = lldb.SBFile(f)
        buf = bytearray(100)
        e, n = sbf.Read(buf)
        self.assertTrue(e.Success())
        self.assertEqual(buf[:n], b'zork')


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_sbfile_read_string_one_byte(self):
        f = io.StringIO('z')
        sbf = lldb.SBFile(f)
        buf = bytearray(1)
        e, n = sbf.Read(buf)
        self.assertTrue(e.Fail())
        self.assertEqual(n, 0)
        self.assertEqual(e.GetCString(), "can't read less than 6 bytes from a utf8 text stream")


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_sbfile_read_bytes(self):
        f = io.BytesIO(b'zork')
        sbf = lldb.SBFile(f)
        buf = bytearray(100)
        e, n = sbf.Read(buf)
        self.assertTrue(e.Success())
        self.assertEqual(buf[:n], b'zork')


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    @skipIf(py_version=['<', (3,)])
    def test_sbfile_out(self):
        with open(self.out_filename, 'w') as f:
            sbf = lldb.SBFile(f)
            status = self.debugger.SetOutputFile(sbf)
            if status.Fail():
                raise Exception(status)
            self.handleCmd('script 2+2')
        with open(self.out_filename, 'r') as f:
            self.assertEqual(f.read().strip(), '4')


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_sbfile_error(self):
        with open(self.out_filename, 'w') as f:
            sbf = lldb.SBFile(f)
            status = self.debugger.SetErrorFile(sbf)
            if status.Fail():
                raise Exception(status)
            self.handleCmd('lolwut', check=False, collect_result=False)
        with open(self.out_filename, 'r') as f:
            errors = f.read()
            self.assertTrue(re.search(r'error:.*lolwut', errors))


    @add_test_categories(['pyapi'])
    @no_debug_info_test
    def test_exceptions(self):
        self.assertRaises(TypeError, lldb.SBFile, None)
        self.assertRaises(TypeError, lldb.SBFile, "ham sandwich")
        if sys.version_info[0] < 3:
            self.assertRaises(TypeError, lldb.SBFile, ReallyBadIO())
        else:
            self.assertRaises(OhNoe, lldb.SBFile, ReallyBadIO())
            error, n = lldb.SBFile(BadIO()).Write(b"FOO")
            self.assertEqual(n, 0)
            self.assertTrue(error.Fail())
            self.assertEqual(error.GetCString(), "OhNoe('OH NOE')")
            error, n = lldb.SBFile(BadIO()).Read(bytearray(100))
            self.assertEqual(n, 0)
            self.assertTrue(error.Fail())
            self.assertEqual(error.GetCString(), "OhNoe('OH NOE')")
