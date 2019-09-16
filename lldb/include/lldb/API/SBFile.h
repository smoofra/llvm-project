//===-- SBFile.h --------------------------------------------*- C++ -*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

#ifndef LLDB_SBFile_h_
#define LLDB_SBFile_h_

#include "lldb/API/SBDefines.h"

namespace lldb {

/* These tags make no difference at the c++ level, but
 * when the constructors are called from python they control
 * how python files are converted by SWIG into FileSP */
struct FileBorrow {};
struct FileForceScriptingIO {};
struct FileBorrowAndForceScriptingIO {};

class LLDB_API SBFile {
  friend class SBDebugger;

public:
  SBFile();
  SBFile(FileSP file_sp) : m_opaque_sp(file_sp){};
  SBFile(FileBorrow, FileSP file_sp) : m_opaque_sp(file_sp){};
  SBFile(FileForceScriptingIO, FileSP file_sp) : m_opaque_sp(file_sp){};
  SBFile(FileBorrowAndForceScriptingIO, FileSP file_sp)
      : m_opaque_sp(file_sp){};
  SBFile(FILE *file, bool transfer_ownership);
  SBFile(int fd, const char *mode, bool transfer_ownership);
  ~SBFile();

  SBError Read(uint8_t *buf, size_t num_bytes, size_t *bytes_read);
  SBError Write(const uint8_t *buf, size_t num_bytes, size_t *bytes_written);
  SBError Flush();
  bool IsValid() const;
  SBError Close();

  operator bool() const { return IsValid(); }
  bool operator!() const { return !IsValid(); }

private:
  FileSP m_opaque_sp;
};

} // namespace lldb

#endif // LLDB_SBFile_h_
