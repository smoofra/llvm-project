//===-- File.h --------------------------------------------------*- C++ -*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

#ifndef liblldb_File_h_
#define liblldb_File_h_

#include "lldb/Host/PosixApi.h"
#include "lldb/Utility/IOObject.h"
#include "lldb/Utility/Status.h"
#include "lldb/lldb-private.h"

#include <mutex>
#include <stdarg.h>
#include <stdio.h>
#include <sys/types.h>

namespace lldb_private {

class FileOps {
  friend class File;
public:
  static const int kInvalidDescriptor = -1;
  FileOps() :
    m_descriptor(kInvalidDescriptor),
    m_stream(nullptr),
    m_own_descriptor(false),
    m_own_stream(false),
    m_overrides_io(false) {};
  FileOps(FILE *stream, bool take_ownership) :
    m_descriptor(kInvalidDescriptor),
    m_stream(stream),
    m_own_descriptor(false),
    m_own_stream(take_ownership),
    m_overrides_io(false) {};
  FileOps(int descriptor, bool take_ownership) :
    m_descriptor(descriptor),
    m_stream(nullptr),
    m_own_descriptor(take_ownership),
    m_own_stream(false),
    m_overrides_io(false) {};
  virtual Status Close();
  virtual ~FileOps();
  virtual Status Write(const void *buf, size_t &num_bytes);
  virtual Status Read(void *buf, size_t &num_bytes);
  virtual Status Flush();

protected:
  int m_descriptor;
  FILE *m_stream;
  bool m_own_descriptor;
  bool m_own_stream;

  // If this is false the the FileOps is only here to manage closing
  // the stream or descriptor when all the Files that refer to it are
  // closed.   If it's true then actual io operations will be routed
  // through the FileOps.
  bool m_overrides_io;
};

/// \class File File.h "lldb/Host/File.h"
/// A file class.
///
/// A file class that divides abstracts the LLDB core from host file
/// functionality.
class File : public IOObject {
public:
  static int kInvalidDescriptor;
  static FILE *kInvalidStream;

  // NB this enum is used in the lldb platform gdb-remote packet
  // vFile:open: and existing values cannot be modified.
  enum OpenOptions {
    eOpenOptionRead = (1u << 0),  // Open file for reading
    eOpenOptionWrite = (1u << 1), // Open file for writing
    eOpenOptionAppend =
        (1u << 2), // Don't truncate file when opening, append to end of file
    eOpenOptionTruncate = (1u << 3),    // Truncate file when opening
    eOpenOptionNonBlocking = (1u << 4), // File reads
    eOpenOptionCanCreate = (1u << 5),   // Create file if doesn't already exist
    eOpenOptionCanCreateNewOnly =
        (1u << 6), // Can create file only if it doesn't already exist
    eOpenOptionDontFollowSymlinks = (1u << 7),
    eOpenOptionCloseOnExec =
        (1u << 8) // Close the file when executing a new process
  };

  static mode_t ConvertOpenOptionsForPOSIXOpen(uint32_t open_options);

  File()
      : IOObject(eFDTypeFile), m_descriptor(kInvalidDescriptor),
        m_stream(kInvalidStream), m_options(0),
        m_is_interactive(eLazyBoolCalculate),
        m_is_real_terminal(eLazyBoolCalculate),
        m_supports_colors(eLazyBoolCalculate) {}

  File(FILE *fh, bool transfer_ownership)
      : IOObject(eFDTypeFile), m_descriptor(kInvalidDescriptor),
        m_stream(fh), m_options(0),
        m_is_interactive(eLazyBoolCalculate),
        m_is_real_terminal(eLazyBoolCalculate),
        m_supports_colors(eLazyBoolCalculate),
        m_fops(std::make_shared<FileOps>(fh, transfer_ownership)) {}

  File(int fd, uint32_t options, bool transfer_ownership)
      : IOObject(eFDTypeFile), m_descriptor(fd),
        m_stream(kInvalidStream),
        m_options(options), m_is_interactive(eLazyBoolCalculate),
        m_is_real_terminal(eLazyBoolCalculate),
        m_fops(std::make_shared<FileOps>(fd, transfer_ownership)) {}

  File(const File &file)
      : IOObject(eFDTypeFile), m_descriptor(file.m_descriptor),
        m_stream(file.m_stream), m_options(file.m_options),
        m_is_interactive(file.m_is_interactive),
        m_is_real_terminal(file.m_is_real_terminal),
        m_supports_colors(file.m_supports_colors),
        m_fops(file.m_fops) {}

  File(std::shared_ptr<FileOps> fops)
      : IOObject(eFDTypeFile), m_descriptor(kInvalidDescriptor),
        m_stream(kInvalidStream), m_options(0),
        m_is_interactive(eLazyBoolCalculate),
        m_is_real_terminal(eLazyBoolCalculate),
        m_supports_colors(eLazyBoolCalculate),
        m_fops(fops) {}

  File(std::shared_ptr<FileOps> fops, int fd)
      : IOObject(eFDTypeFile), m_descriptor(fd),
        m_stream(kInvalidStream), m_options(0),
        m_is_interactive(eLazyBoolCalculate),
        m_is_real_terminal(eLazyBoolCalculate),
        m_supports_colors(eLazyBoolCalculate),
        m_fops(fops) {}

  /// Destructor.
  ///
  /// The destructor is virtual in case this class is subclassed.
  ~File() override;

  bool IsValid() const override {
    return DescriptorIsValid() || StreamIsValid() || OverridesIO();
  }

  /// Convert to pointer operator.
  ///
  /// This allows code to check a File object to see if it contains anything
  /// valid using code such as:
  ///
  /// \code
  /// File file(...);
  /// if (file)
  /// { ...
  /// \endcode
  ///
  /// \return
  ///     A pointer to this object if either the directory or filename
  ///     is valid, nullptr otherwise.
  operator bool() const { return IsValid(); }

  /// Logical NOT operator.
  ///
  /// This allows code to check a File object to see if it is invalid using
  /// code such as:
  ///
  /// \code
  /// File file(...);
  /// if (!file)
  /// { ...
  /// \endcode
  ///
  /// \return
  ///     Returns \b true if the object has an empty directory and
  ///     filename, \b false otherwise.
  bool operator!() const { return !IsValid(); }

  /// Get the file spec for this file.
  ///
  /// \return
  ///     A reference to the file specification object.
  Status GetFileSpec(FileSpec &file_spec) const;

  Status Close() override;

  /// DANGEROUS. Extract the underlying FILE* and reset this File without closing it.
  ///
  /// This is only here to support legacy SB interfaces that need to convert scripting
  /// language objects into FILE* streams.   That conversion is inherently sketchy and
  /// doing so may cause the stream to be leaked.
  ///
  ///  After calling this the File will be reset to it's original state.  It will be
  ///  invalid and it will not hold on to any resources.
  ///
  /// \return
  ///     The underlying FILE* stream from this File, if one exists and can be extracted,
  ///     nullptr otherwise.
  FILE *TakeStreamAndClear();

  int GetDescriptor() const;

  static uint32_t GetOptionsFromMode(llvm::StringRef mode);

  WaitableHandle GetWaitableHandle() override;

  void SetDescriptor(int fd, uint32_t options, bool transfer_ownership);

  FILE *GetStream();

  void SetStream(FILE *fh, bool transfer_ownership);

  void SetFile(const File &file);

  File &operator=(const File &file);

  /// Read bytes from a file from the current file position.
  ///
  /// NOTE: This function is NOT thread safe. Use the read function
  /// that takes an "off_t &offset" to ensure correct operation in multi-
  /// threaded environments.
  ///
  /// \param[in] buf
  ///     A buffer where to put the bytes that are read.
  ///
  /// \param[in,out] num_bytes
  ///     The number of bytes to read form the current file position
  ///     which gets modified with the number of bytes that were read.
  ///
  /// \return
  ///     An error object that indicates success or the reason for
  ///     failure.
  Status Read(void *buf, size_t &num_bytes) override;

  /// Write bytes to a file at the current file position.
  ///
  /// NOTE: This function is NOT thread safe. Use the write function
  /// that takes an "off_t &offset" to ensure correct operation in multi-
  /// threaded environments.
  ///
  /// \param[in] buf
  ///     A buffer where to put the bytes that are read.
  ///
  /// \param[in,out] num_bytes
  ///     The number of bytes to write to the current file position
  ///     which gets modified with the number of bytes that were
  ///     written.
  ///
  /// \return
  ///     An error object that indicates success or the reason for
  ///     failure.
  Status Write(const void *buf, size_t &num_bytes) override;

  /// Seek to an offset relative to the beginning of the file.
  ///
  /// NOTE: This function is NOT thread safe, other threads that
  /// access this object might also change the current file position. For
  /// thread safe reads and writes see the following functions: @see
  /// File::Read (void *, size_t, off_t &) \see File::Write (const void *,
  /// size_t, off_t &)
  ///
  /// \param[in] offset
  ///     The offset to seek to within the file relative to the
  ///     beginning of the file.
  ///
  /// \param[in] error_ptr
  ///     A pointer to a lldb_private::Status object that will be
  ///     filled in if non-nullptr.
  ///
  /// \return
  ///     The resulting seek offset, or -1 on error.
  off_t SeekFromStart(off_t offset, Status *error_ptr = nullptr);

  /// Seek to an offset relative to the current file position.
  ///
  /// NOTE: This function is NOT thread safe, other threads that
  /// access this object might also change the current file position. For
  /// thread safe reads and writes see the following functions: @see
  /// File::Read (void *, size_t, off_t &) \see File::Write (const void *,
  /// size_t, off_t &)
  ///
  /// \param[in] offset
  ///     The offset to seek to within the file relative to the
  ///     current file position.
  ///
  /// \param[in] error_ptr
  ///     A pointer to a lldb_private::Status object that will be
  ///     filled in if non-nullptr.
  ///
  /// \return
  ///     The resulting seek offset, or -1 on error.
  off_t SeekFromCurrent(off_t offset, Status *error_ptr = nullptr);

  /// Seek to an offset relative to the end of the file.
  ///
  /// NOTE: This function is NOT thread safe, other threads that
  /// access this object might also change the current file position. For
  /// thread safe reads and writes see the following functions: @see
  /// File::Read (void *, size_t, off_t &) \see File::Write (const void *,
  /// size_t, off_t &)
  ///
  /// \param[in,out] offset
  ///     The offset to seek to within the file relative to the
  ///     end of the file which gets filled in with the resulting
  ///     absolute file offset.
  ///
  /// \param[in] error_ptr
  ///     A pointer to a lldb_private::Status object that will be
  ///     filled in if non-nullptr.
  ///
  /// \return
  ///     The resulting seek offset, or -1 on error.
  off_t SeekFromEnd(off_t offset, Status *error_ptr = nullptr);

  /// Read bytes from a file from the specified file offset.
  ///
  /// NOTE: This function is thread safe in that clients manager their
  /// own file position markers and reads on other threads won't mess up the
  /// current read.
  ///
  /// \param[in] dst
  ///     A buffer where to put the bytes that are read.
  ///
  /// \param[in,out] num_bytes
  ///     The number of bytes to read form the current file position
  ///     which gets modified with the number of bytes that were read.
  ///
  /// \param[in,out] offset
  ///     The offset within the file from which to read \a num_bytes
  ///     bytes. This offset gets incremented by the number of bytes
  ///     that were read.
  ///
  /// \return
  ///     An error object that indicates success or the reason for
  ///     failure.
  Status Read(void *dst, size_t &num_bytes, off_t &offset);

  /// Write bytes to a file at the specified file offset.
  ///
  /// NOTE: This function is thread safe in that clients manager their
  /// own file position markers, though clients will need to implement their
  /// own locking externally to avoid multiple people writing to the file at
  /// the same time.
  ///
  /// \param[in] src
  ///     A buffer containing the bytes to write.
  ///
  /// \param[in,out] num_bytes
  ///     The number of bytes to write to the file at offset \a offset.
  ///     \a num_bytes gets modified with the number of bytes that
  ///     were read.
  ///
  /// \param[in,out] offset
  ///     The offset within the file at which to write \a num_bytes
  ///     bytes. This offset gets incremented by the number of bytes
  ///     that were written.
  ///
  /// \return
  ///     An error object that indicates success or the reason for
  ///     failure.
  Status Write(const void *src, size_t &num_bytes, off_t &offset);

  /// Flush the current stream
  ///
  /// \return
  ///     An error object that indicates success or the reason for
  ///     failure.
  Status Flush();

  /// Sync to disk.
  ///
  /// \return
  ///     An error object that indicates success or the reason for
  ///     failure.
  Status Sync();

  /// Get the permissions for a this file.
  ///
  /// \return
  ///     Bits logical OR'ed together from the permission bits defined
  ///     in lldb_private::File::Permissions.
  uint32_t GetPermissions(Status &error) const;

  /// Return true if this file is interactive.
  ///
  /// \return
  ///     True if this file is a terminal (tty or pty), false
  ///     otherwise.
  bool GetIsInteractive();

  /// Return true if this file from a real terminal.
  ///
  /// Just knowing a file is a interactive isn't enough, we also need to know
  /// if the terminal has a width and height so we can do cursor movement and
  /// other terminal manipulations by sending escape sequences.
  ///
  /// \return
  ///     True if this file is a terminal (tty, not a pty) that has
  ///     a non-zero width and height, false otherwise.
  bool GetIsRealTerminal();

  bool GetIsTerminalWithColors();

  /// Output printf formatted output to the stream.
  ///
  /// Print some formatted output to the stream.
  ///
  /// \param[in] format
  ///     A printf style format string.
  ///
  /// \param[in] ...
  ///     Variable arguments that are needed for the printf style
  ///     format string \a format.
  size_t Printf(const char *format, ...) __attribute__((format(printf, 2, 3)));

  size_t PrintfVarArg(const char *format, va_list args);

  static bool DescriptorIsValid(int descriptor) { return descriptor >= 0; };

protected:
  bool DescriptorIsValid() const { return DescriptorIsValid(m_descriptor); }

  bool StreamIsValid() const { return m_stream != kInvalidStream; }

  bool OverridesIO() const { return m_fops && m_fops->m_overrides_io; }

  void CalculateInteractiveAndTerminal();

  // Member variables
  int m_descriptor;
  FILE *m_stream;
  uint32_t m_options;
  LazyBool m_is_interactive;
  LazyBool m_is_real_terminal;
  LazyBool m_supports_colors;
  std::mutex offset_access_mutex;
  std::shared_ptr<FileOps> m_fops;

};

} // namespace lldb_private

#endif // liblldb_File_h_
