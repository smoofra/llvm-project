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

class SBFile
{
public:

    SBFile();
    ~SBFile ();

    void SetStream (FILE *file, bool transfer_ownership);
    void SetDescriptor (int fd, const char *mode, bool transfer_ownership);

    void SetFile(lldb_private::File &file);

    %extend {
        %feature("docstring", "Like SetFile(), but the underlying file will not be closed when the SBFile is closed or destroyed.");
        void SetFileBorrowed(lldb_private::File &BORROWED) {
            self->SetFile(BORROWED);
        }

        %feature("docstring" "like SetFile(), but the python read/write methods will be called even if a file descriptor is available.");
        void SetFileForcingUseOfScriptingIOMethods(lldb_private::File &FORCE_IO_METHODS)
        {
            self->SetFile(FORCE_IO_METHODS);
        }

        void SetFileBorrowedForcingUseOfScriptingIOMethods(lldb_private::File &BORROWED_FORCE_IO_METHODS)
        {
            self->SetFile(BORROWED_FORCE_IO_METHODS);
        }
    }

    %feature("autodoc", "Read(buffer) -> SBError, bytes_read") Read;
    SBError Read(uint8_t *buf, size_t num_bytes, size_t *OUTPUT);

    %feature("autodoc", "Write(buffer) -> SBError, written_read") Write;
    SBError Write(const uint8_t *buf, size_t num_bytes, size_t *OUTPUT);

    void Flush();

    bool IsValid() const;

    SBError Close();
};

} // namespace lldb
