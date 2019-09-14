//===-- SBFile.cpp ------------------------------------------*- C++ -*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

#include "lldb/API/SBFile.h"
#include "lldb/API/SBError.h"
#include "lldb/Host/File.h"

using namespace lldb;
using namespace lldb_private;

SBFile::~SBFile() {}

SBFile::SBFile() {}

SBFile::SBFile(FILE *file, bool transfer_ownership) {
  m_opaque_sp = std::make_shared<File>(file, transfer_ownership);
}

SBFile::SBFile(int fd, const char *mode, bool transfer_owndership) {
  auto options = File::GetOptionsFromMode(mode);
  m_opaque_sp = std::make_shared<File>(fd, options, transfer_owndership);
}

SBError SBFile::Read(uint8_t *buf, size_t num_bytes, size_t *bytes_read) {
  SBError error;
  if (!m_opaque_sp) {
    error.SetErrorString("invalid SBFile");
    *bytes_read = 0;
  } else {
    Status status = m_opaque_sp->Read(buf, num_bytes);
    error.SetError(status);
    *bytes_read = num_bytes;
  }
  return error;
}

SBError SBFile::Write(const uint8_t *buf, size_t num_bytes,
                      size_t *bytes_written) {
  SBError error;
  if (!m_opaque_sp) {
    error.SetErrorString("invalid SBFile");
    *bytes_written = 0;
  } else {
    Status status = m_opaque_sp->Write(buf, num_bytes);
    error.SetError(status);
    *bytes_written = num_bytes;
  }
  return error;
}

SBError SBFile::Flush() {
  SBError error;
  if (!m_opaque_sp) {
    error.SetErrorString("invalid SBFile");
  } else {
    Status status = m_opaque_sp->Flush();
    error.SetError(status);
  }
  return error;
}

bool SBFile::IsValid() const { return m_opaque_sp && m_opaque_sp->IsValid(); }

SBError SBFile::Close() {
  SBError error;
  if (m_opaque_sp) {
    Status status = m_opaque_sp->Close();
    error.SetError(status);
  }
  return error;
}
