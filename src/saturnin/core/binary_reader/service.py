# SPDX-FileCopyrightText: 2021-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           binary_reader/service.py
# DESCRIPTION:    Binary data file reader microservice
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

"""Saturnin microservices - Binary data file reader microservice

This microservice is a DATA_PROVIDER that sends blocks of binary data from file to output
data pipe.

Configuration Options:
----------------------
The service uses `BinaryReaderConfig`, which inherits from `DataProviderConfig`.
Key configuration options include:

Inherited from `DataProviderConfig` (and `BaseDataPipeConfig`):
  - `pipe` (str, required): Identifier for the data pipe.
  - `pipe_address` (ZMQAddress, required): ZMQ endpoint address for the data pipe.
  - `pipe_mode` (SocketMode, required): Specifies if the service should BIND (server)
    or CONNECT (client) to the `pipe_address`.
  - `pipe_format` (MIME, optional): If specified, this is the expected MIME type
    of the data stream. When a client connects, its proposed data format is
    validated against this. If they don't match, or if the service expects a
    format and the client provides none, the connection is rejected with
    `ErrorCode.DATA_FORMAT_NOT_SUPPORTED`. If this option is not set, the
    service accepts any data format from the client.
  - `batch_size` (int, default: 50): Controls the FBDP message batching.
  - `ready_schedule_interval` (int, default: 1000ms): Interval for sending
    FBDP READY messages.
  - `stop_on_close` (bool, default: True): If True, the service will stop
    when the data pipe is closed by the client or due to an error.

Specific to `BinaryReaderConfig`:
  - `filename` (str, required): Path to the binary file to be read.
    Special values 'stdin', 'stdout', or 'stderr' (case-insensitive) can be
    used to read from standard input, output, or error streams respectively.
    Note that reading from stdout/stderr is unusual for a data *provider*
    but supported by the file opening logic.
  - `block_size` (int, required): Defines how data is read and sent.
    - If positive: Reads fixed-size blocks of this many bytes.
    - If -1: The data stream is expected to be size-prefixed. The service
      first reads a 4-byte unsigned integer (big-endian) representing the
      size of the next data block, then reads that many bytes.
    - Other values (0 or less than -1) are invalid and will cause a
      configuration validation error.

Service Behavior:
-----------------
1.  Initialization:
    The service initializes its FBDP communication channel based on `pipe_address`
    and `pipe_mode`.

2.  Client Connection (`handle_accept_client`):
    When a client connects:
    - The client's requested data pipe ID is validated against the service's `pipe` ID.
    - If `pipe_format` is configured for the service:
        - If the client does not specify a data format, the connection is rejected.
        - If the client's specified data format (MIME type and parameters) does
          not match the service's `pipe_format`, the connection is rejected.
    - If validation passes, the file specified by `filename` is opened in binary
      read mode ('br'). Failure to open the file results in a `StopError` and
      the client connection is closed with `ErrorCode.ERROR`.

3.  Data Production (`handle_produce_data`):
    - If `block_size` is positive: The service attempts to read `block_size`
      bytes from the file.
    - If `block_size` is -1:
        - It first reads 4 bytes to determine the next block's size. If EOF is
          reached while reading these 4 bytes, or if the read is incomplete,
          it's an error or EOF.
        - If the decoded size is 0, it's treated as EOF.
        - It then attempts to read the determined number of bytes.
    - The read data block is sent to the client in an FBDP `DATA` message.
    - End of File (EOF): When EOF is cleanly reached (e.g., `read()` returns
      an empty byte string when expecting data, or a size-prefix of 0 is read),
      a `StopError` with `ErrorCode.OK` is raised, signaling the FBDP protocol
      to send a `CLOSE` message with `OK` status to the client.
    - Error Handling:
        - If there's an issue reading the size prefix (e.g., `struct.unpack`
          fails), a `StopError` with `ErrorCode.INVALID_DATA` is raised.
        - If a size is read (for `block_size == -1`) but not enough data bytes
          can be read to fulfill that size (i.e., an incomplete block at EOF),
          a `StopError` with `ErrorCode.INVALID_DATA` is raised.
        - Other file I/O errors during reading will typically propagate and
          might be caught by the base microservice framework, leading to a
          service shutdown or an FBDP `CLOSE` message with `ErrorCode.ERROR`.

4.  Pipe Closure (`handle_pipe_closed`):
    - When the data pipe is closed (either normally by the client, due to EOF,
      or due to an error), this handler is called.
    - It ensures the input file is closed.
    - If `stop_on_close` is True (the default), the service will initiate its
      shutdown sequence.
    - If the closure was due to an exception, the service's outcome is set to
      ERROR.

This microservice is designed for scenarios where binary data from a file needs
to be streamed efficiently to another component in a Saturnin system.
"""

from __future__ import annotations

from struct import unpack
from typing import BinaryIO, ClassVar, Final, cast

from saturnin.base import MIME, Channel, StopError
from saturnin.lib.data.onepipe import DataProviderMicro, ErrorCode, FBDPMessage, FBDPSession

from .api import BinaryReaderConfig

BLOCK_SIZE_INT: Final[int] = 4 # (un)pack format 'I'

# Classes

class BinaryReaderMicro(DataProviderMicro):
    """Binary file reader microservice.
    """
    SYSIO: ClassVar[tuple[str, str, str]] = ('stdin', 'stdout', 'stderr')
    def _open_file(self) -> None:
        "Open the input file."
        self._close_file()
        if self.filename.lower() in self.SYSIO:
            fspec = self.SYSIO.index(self.filename.lower())
        else:
            fspec = self.filename
        try:
            self.file = open(fspec, mode='br',
                             closefd=self.filename.lower() not in self.SYSIO)
        except Exception as exc:
            raise StopError("Failed to open input file", code = ErrorCode.ERROR) from exc
    def _close_file(self) -> None:
        "Close the input file if necessary"
        if self.file:
            self.file.close()
            self.file = None
    def initialize(self, config: BinaryReaderConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config) # Initializes self.pipe_format, self.batch_size etc.
        # Configuration specific to BinaryReader
        self.file: BinaryIO | None = None
        self.filename: str = config.filename.value
        self.block_size: int = config.block_size.value
    def handle_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Event handler executed when client connects to the data pipe via OPEN message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        The session attributes `data_pipe`, `pipe_socket`, `data_format` and `params`
        contain information sent by client, and the event handler validates the request.
        `super().handle_accept_client` converts `session.data_format` to a MIME object.

        If request should be rejected, it raises the `StopError` exception with `code`
        attribute containing the `ErrorCode` to be returned in CLOSE message.
        """
        super().handle_accept_client(channel, session)
        if self.pipe_format is not None and session.data_format != self.pipe_format:
            raise StopError(f"MIME type '{cast(MIME, session.data_format).mime_type}' is not a valid input format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        # Client reqest is ok, we'll open the file we are configured to work with.
        self._open_file()
    def handle_produce_data(self, channel: Channel, session: FBDPSession, msg: FBDPMessage) -> None:
        """Handler is executed to store data into outgoing DATA message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            msg: DATA message that will be sent to client.

        The event handler must store the data in `msg.data_frame` attribute. It may also
        set ACK-REQUEST flag and `type_data` attribute.

        The event handler may cancel the transmission by raising the `StopError` exception
        with `code` attribute containing the `ErrorCode` to be returned in CLOSE message.

        Note:
            To indicate end of data, raise StopError with ErrorCode.OK code.

        Note:
            Exceptions are handled by protocol, but only StopError is checked for protocol
            ErrorCode. As we want to report INVALID_DATA properly, we have to convert
            exceptions into StopError.

        Important:
            This method overrides the base class implementation and should not call super().
        """
        read_size: int
        if self.block_size == -1:
            # Read 4 bytes for size
            size_bytes = self.file.read(BLOCK_SIZE_INT)
            if not size_bytes: # EOF when trying to read size
                raise StopError('OK: EOF reached before reading block size', code=ErrorCode.OK)
            if len(size_bytes) < BLOCK_SIZE_INT: # Should not happen with blocking read unless true EOF
                raise StopError('Invalid data: Incomplete block size information at EOF', code=ErrorCode.INVALID_DATA)
            try:
                read_size = unpack('!I', size_bytes)[0]
            except Exception as exc: # e.g., struct.error
                raise StopError("Invalid data: Failed to unpack block size", code=ErrorCode.INVALID_DATA) from exc
            if read_size == 0: # A zero-size block can indicate EOF or just an empty block.
                               # Consistent with fixed block_size=0 which is disallowed by config.
                               # Here, it means no more data to follow if size is 0.
                raise StopError('OK: Zero size block encountered', code=ErrorCode.OK)
        else:
            read_size = self.block_size # block_size is validated to be > 0 or -1

        data_buf = self.file.read(read_size)

        if not data_buf:
            # EOF reached when trying to read the data block.
            # If block_size was -1, this means we read a size > 0 but got no data.
            if self.block_size == -1 and read_size > 0:
                raise StopError(f'Invalid data: Expected {read_size} bytes, but got EOF (incomplete block)',
                                code=ErrorCode.INVALID_DATA)
            # If fixed block_size, or if size_bytes indicated 0 (already handled), this is clean EOF.
            raise StopError('OK: EOF reached while reading data block', code=ErrorCode.OK)

        if self.block_size == -1 and len(data_buf) < read_size:
            # Read a size, but couldn't read that many bytes (partial block at EOF)
            raise StopError(f'Invalid data: Expected {read_size} bytes, got {len(data_buf)} (incomplete block at EOF)',
                            code=ErrorCode.INVALID_DATA)

        msg.data_frame = data_buf
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
        super().handle_pipe_closed(channel, session, msg, exc) # Handles stop_on_close and error outcome
        self._close_file()
