//===-- SWIG Interface for SBFile -----------------------------------------===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

%include <pybuffer.i>

%pybuffer_binary(const uint8_t *buf, size_t num_bytes);
%pybuffer_mutable_binary(uint8_t *buf, size_t num_bytes);

namespace lldb {

%feature("docstring",
"Represents a file."
) SBFile;

struct FileBorrow {};
struct FileForceScriptingIO {};
struct FileBorrowAndForceScriptingIO {};

class SBFile
{
public:


    SBFile();

    %feature("docstring", "
    Initialize a SBFile from a file descriptor.  mode is
    'r', 'r+', or 'w', like fdopen.");
    SBFile(int fd, const char *mode, bool transfer_ownership);

    %feature("docstring", "initialize a SBFile from a python file object");
    SBFile(FileSP file);

    %feature("docstring", "
    Like SBFile(f), but the underlying file will
    not be closed when the SBFile is closed or destroyed.");
    SBFile(FileBorrow, FileSP BORROWED);

    %feature("docstring" "
    like SetFile(f), but the python read/write methods will be called even if
    a file descriptor is available.");
    SBFile(FileForceScriptingIO, FileSP FORCE_IO_METHODS);

    %feature("docstring" "
    like SetFile(f), but the python read/write methods will be called even
    if a file descriptor is available -- and the underlying file will not
    be closed when the SBFile is closed or destroyed.");
    SBFile(FileBorrowAndForceScriptingIO, FileSP BORROWED_FORCE_IO_METHODS);

    ~SBFile ();

    %feature("autodoc", "Read(buffer) -> SBError, bytes_read") Read;
    SBError Read(uint8_t *buf, size_t num_bytes, size_t *OUTPUT);

    %feature("autodoc", "Write(buffer) -> SBError, written_read") Write;
    SBError Write(const uint8_t *buf, size_t num_bytes, size_t *OUTPUT);

    void Flush();

    bool IsValid() const;

    SBError Close();
};

} // namespace lldb
