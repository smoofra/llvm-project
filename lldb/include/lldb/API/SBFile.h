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

class LLDB_API SBFile {
  friend class SBDebugger;
public:

  SBFile (const SBFile &file);
  SBFile (SBFile &&file);
  SBFile();
  ~SBFile();

  SBFile &operator= (const SBFile &file);
  void SetStream(FILE *file, bool transfer_ownership);
  void SetDescriptor(int fd, const char *mode, bool transfer_ownership);

  SBError Read(uint8_t *buf, size_t num_bytes, size_t *bytes_read);
  SBError Write(const uint8_t *buf, size_t num_bytes, size_t *bytes_written);
  SBError Flush();
  bool IsValid() const;
  SBError Close();

  operator bool() const { return IsValid(); }
  bool operator!() const { return !IsValid(); }

private:
  void SetFile(const lldb_private::File &file);
  lldb_private::File &GetFile() const { return *m_opaque_up; }
  FileUP m_opaque_up;
};

} // namespace lldb

#endif // LLDB_SBFile_h_
