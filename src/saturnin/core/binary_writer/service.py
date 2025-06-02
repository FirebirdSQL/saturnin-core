# SPDX-FileCopyrightText: 2021-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           binary_writer/service.py
# DESCRIPTION:    Binary data file writer microservice
# CREATED:        05.01.2021
#
# The contents of this file are subject to the MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Copyright (c) 2021 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin microservices - Binary data file writer microservice

This microservice is a DATA_CONSUMER that receives binary data from an input
data pipe and writes it to a specified file or standard stream.

Configuration Options:
----------------------
The service uses `BinaryWriterConfig`, which inherits from `DataConsumerConfig`
(which in turn inherits from `BaseDataPipeConfig`). Key configuration options include:

Inherited from `DataConsumerConfig` (and `BaseDataPipeConfig`):
  - `pipe` (str, required): Identifier for the data pipe.
  - `pipe_address` (ZMQAddress, required): ZMQ endpoint address for the data pipe.
  - `pipe_mode` (SocketMode, required): Specifies if the service should BIND (server)
    or CONNECT (client) to the `pipe_address`.
  - `pipe_format` (MIME, optional): Specifies the required MIME type of the input
    data stream from the client.
    - If set: The client *must* provide data in this exact format (MIME type and
      parameters). If the client's format differs, or if the client provides no
      format, the connection is rejected with `ErrorCode.DATA_FORMAT_NOT_SUPPORTED`.
    - If not set (default): The client *must not* specify a data format. If the
      client sends a data format, the connection is rejected with
      `ErrorCode.DATA_FORMAT_NOT_SUPPORTED`.
  - `batch_size` (int, default: 50): Controls FBDP message batching.
    Defines the number of DATA messages to receive in one batch.
  - `stop_on_close` (bool, default: True): If True, the service will stop
    when the data pipe is closed by the client or due to an error.

Specific to `BinaryWriterConfig`:
  - `filename` (str, required): Path to the output file. Special values 'stdout'
    or 'stderr' (case-insensitive) can be used to write to standard output or
    error streams respectively.
  - `file_mode` (FileOpenMode, default: WRITE): Defines how the output file is opened.
    - `CREATE`: Opens the file for exclusive creation ('xb'). Fails if the file already exists.
    - `WRITE`: Opens the file for writing ('wb'). Truncates the file if it exists.
      This is the only mode allowed for 'stdout' and 'stderr'.
    - `RENAME`: If the target file exists, it's backed up by appending a '.N'
      suffix (e.g., 'output.txt.1'), and then the new data is written to the
      original filename ('wb').
    - `APPEND`: Opens the file for appending ('ab'). Data is written to the end
      of the file if it exists, or a new file is created.
    - `READ` mode is not supported and will cause a configuration validation error.
  - `file_type` (FileStorageType, required): Specifies how binary data is written.
    - `STREAM`: Data is written directly to the file as a continuous stream.
    - `BLOCK`: Each data chunk received from the pipe is prefixed by its length
      (a 4-byte network-order unsigned integer) before being written to the file.

Service Behavior:
-----------------
1.  Initialization (`initialize`):
    - The service initializes its FBDP communication channel based on `pipe_address`
      and `pipe_mode`.
    - Configuration values (filename, file mode, file type, pipe format) are
      stored for later use.

2.  Client Connection (`handle_accept_client`):
    - When a client connects:
        - The client's requested data pipe ID is validated against the service's `pipe` ID.
        - The client's data format is validated against the service's `pipe_format`
          configuration as described above. The `super().handle_accept_client`
          performs initial validation, and `BinaryWriterMicro` adds a specific check.
        - If validation passes, the output file specified by `filename` is opened
          using the `_open_file()` method, according to `file_mode`.
        - `_open_file()` handles:
            - Special filenames ('stdout', 'stderr').
            - File mode logic: 'xb' for CREATE, 'wb' for WRITE/RENAME, 'ab' for APPEND.
            - For RENAME mode, if the target file exists, it attempts to rename the
              existing file to `filename.N` before opening the new file.
        - Failure to open the file (e.g., permissions, exclusive creation conflict,
          rename failure) results in a `StopError`, and the client connection is
          closed, typically with `ErrorCode.ERROR` or a specific code from validation.

3.  Data Consumption (`handle_accept_data`):
    - This handler is called for each DATA message received from the client.
    - The output file must be open; if not (e.g., first data packet after a lazy open),
      `_open_file()` is called.
    - If `file_type` is `BLOCK`:
        - The length of the received `data` chunk is packed into a 4-byte,
          big-endian unsigned integer (`!I`).
        - This length prefix is written to the file, followed by the `data` chunk itself.
    - If `file_type` is `STREAM`:
        - The received `data` chunk is written directly to the file.
    - File I/O errors during `write()` (e.g., disk full, permissions) will result
      in a `StopError` being raised, typically with `ErrorCode.INTERNAL_ERROR`,
      leading to the client connection being closed.

4.  Pipe Closure (`handle_pipe_closed`):
    - This handler is executed when the data pipe is closed, either normally by the
      client (sending a CLOSE message), due to an error, or by the service itself
      (e.g. after an error during data handling).
    - It ensures the output file is closed via `_close_file()`.
    - If `stop_on_close` is True (the default), the service will initiate its
      shutdown sequence.
    - If the closure was due to an exception, the service's outcome is set to ERROR.

This microservice is designed for scenarios where binary data needs to be reliably
streamed from a client application or another Saturnin component and stored into a
file or standard stream, with options for how the file is opened and how data is formatted.
"""

from __future__ import annotations

import os
from struct import pack
from typing import BinaryIO, cast

from saturnin.base import MIME, Channel, FileOpenMode, StopError
from saturnin.lib.data.onepipe import DataConsumerMicro, ErrorCode, FBDPMessage, FBDPSession

from .api import BinaryWriterConfig, FileStorageType

# Classes

class BinaryWriterMicro(DataConsumerMicro):
    """Implementation of binary data file writer microservice.
    """
    SYSIO: tuple[str, str, str] = ('stdin', 'stdout', 'stderr')
    def _open_file(self) -> None:
        """Opens the output file based on the service configuration.

        Handles special filenames 'stdin', 'stdout', 'stderr' and different file open modes
        (CREATE, WRITE, RENAME, APPEND). For RENAME mode, if the target file exists, it's backed up by
        appending a '.N' suffix. Sets `self.file` to the opened `BinaryIO` stream.

        Raises:
            StopError: If the file cannot be opened or renamed.
        """
        self._close_file()
        if self.filename.lower() in self.SYSIO:
            fspec = self.SYSIO.index(self.filename.lower())
        else:
            fspec = self.filename
        if self.file_mode is FileOpenMode.CREATE:
            file_mode = 'xb'
        elif self.file_mode is FileOpenMode.WRITE:
            file_mode = 'wb'
        elif self.file_mode is FileOpenMode.RENAME:
            file_mode = 'wb'
            if isinstance(fspec, str) and os.path.isfile(self.filename):
                i = 1
                dest = f'{self.filename}.{i}'
                while os.path.isfile(dest):
                    i += 1
                    dest = f'{self.filename}.{i}'
                try:
                    os.rename(self.filename, dest)
                except Exception as exc:
                    raise StopError("File rename failed") from exc
        elif self.file_mode is FileOpenMode.APPEND:
            file_mode = 'ab'
        try:
            self.file = open(fspec, mode=file_mode,
                             closefd=self.filename.lower() not in self.SYSIO)
        except Exception as exc:
            raise StopError("Failed to open output file") from exc
    def _close_file(self) -> None:
        "Close the output file if necessary."
        if self.file:
            self.file.close()
            self.file = None
    def initialize(self, config: BinaryWriterConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        # Configuration
        self.fmt: MIME | None = config.pipe_format.value
        self.file: BinaryIO | None = None
        self.filename: str = config.filename.value
        self.file_mode: FileOpenMode = config.file_mode.value
        self.file_type: FileStorageType = config.file_type.value
    def handle_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Event handler executed when client connects to the data pipe via OPEN message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        The session attributes `data_pipe`, `pipe_socket`, `data_format` and `params`
        contain information sent by client, and the event handler validates the request.

        If request should be rejected, it raises the `StopError` exception with `code`
        attribute containing the `ErrorCode` to be returned in CLOSE message.
        """
        super().handle_accept_client(channel, session)
        if session.data_format != self.fmt:
            raise StopError(f"Data format '{session.data_format}' is not a valid input format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        # Client reqest is ok, we'll open the file we are configured to work with.
        self._open_file()
    def handle_accept_data(self, channel: Channel, session: FBDPSession, data: bytes) -> None:
        """Event executed to process data received in DATA message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            data: Data received from client.

        The event handler may cancel the transmission by raising the `StopError` exception
        with `code` attribute containing the `ErrorCode` to be returned in CLOSE message.

        Note:
            The ACK-REQUEST in received DATA message is handled automatically by protocol.

        Important:
            The base implementation simply raises StopError with ErrorCode.OK code, so
            the descendant class must override this method without super() call.
        """
        if self.file is None:
            self._open_file()
        try:
            if self.file_type is FileStorageType.BLOCK:
                self.file.write(pack('!I', len(data)))
            self.file.write(data)
        except Exception as exc:
            raise StopError(f"Failed to write data to file '{self.filename}'",
                            code=ErrorCode.INTERNAL_ERROR) from exc
    def handle_pipe_closed(self, channel: Channel, session: FBDPSession, msg: FBDPMessage,
                           exc: Exception | None=None) -> None:
        """Event handler executed when CLOSE message is received or sent, to release any
        resources associated with current transmission.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with peer.
            msg: Received/sent CLOSE message.
            exc: Exception that caused the error.
        """
        super().handle_pipe_closed(channel, session, msg, exc)
        self._close_file()
