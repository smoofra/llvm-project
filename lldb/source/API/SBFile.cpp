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

SBFile::SBFile(const SBFile &file) {
    m_opaque_up = std::make_unique<File>(file.GetFile());
}

SBFile::SBFile(SBFile &&file) {
    std::swap(m_opaque_up, file.m_opaque_up);
}

SBFile &SBFile::operator= (const SBFile &file) {
    if (m_opaque_up) {
        m_opaque_up->SetFile(file.GetFile());
    } else {
        m_opaque_up = std::make_unique<File>(file.GetFile());
    }
    return *this;
}

void SBFile::SetFile(const lldb_private::File &file) {
    if (m_opaque_up) {
        m_opaque_up->SetFile(file);
    } else {
        m_opaque_up = std::make_unique<File>(file);
    }
}

void SBFile::SetStream(FILE *file, bool transfer_ownership) {
  m_opaque_up = std::make_unique<File>(file, transfer_ownership);
}

void SBFile::SetDescriptor(int fd, const char *mode, bool transfer_owndership) {
  auto options = File::GetOptionsFromMode(mode);
  m_opaque_up = std::make_unique<File>(fd, options, transfer_owndership);
}

SBError SBFile::Read(uint8_t *buf, size_t num_bytes, size_t *bytes_read) {
  SBError error;
  if (!m_opaque_up) {
    error.SetErrorString("invalid SBFile");
    *bytes_read = 0;
  } else {
    Status status = m_opaque_up->Read(buf, num_bytes);
    error.SetError(status);
    *bytes_read = num_bytes;
  }
  return error;
}

SBError SBFile::Write(const uint8_t *buf, size_t num_bytes,
                      size_t *bytes_written) {
  SBError error;
  if (!m_opaque_up) {
    error.SetErrorString("invalid SBFile");
    *bytes_written = 0;
  } else {
    Status status = m_opaque_up->Write(buf, num_bytes);
    error.SetError(status);
    *bytes_written = num_bytes;
  }
  return error;
}

SBError SBFile::Flush() {
  SBError error;
  if (!m_opaque_up) {
    error.SetErrorString("invalid SBFile");
  } else {
    Status status = m_opaque_up->Flush();
    error.SetError(status);
  }
  return error;
}

bool SBFile::IsValid() const { return m_opaque_up && m_opaque_up->IsValid(); }

SBError SBFile::Close() {
  SBError error;
  if (m_opaque_up) {
    Status status = m_opaque_up->Close();
    error.SetError(status);
  }
  return error;
}
