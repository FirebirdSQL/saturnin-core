# SPDX-FileCopyrightText: 2019-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           text_writer/service.py
# DESCRIPTION:    Text file writer microservice
# CREATED:        18.12.2019
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
# Copyright (c) 2019 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin microservices - Text file writer microservice implementation.

This module provides the `TextWriterMicro` service, a DATA_CONSUMER that
receives data from an input data pipe and writes it to a specified file or
standard output stream.

Core Functionality:
- Receives data chunks from a connected data producer.
- Writes the received data to a local file, `stdout`, or `stderr`.

Input Data Handling:
- Supports input data in `text/plain` format. The character set (`charset`)
  and error handling strategy (`errors`) for decoding are determined by the
  client's request or the service's `pipe_format` configuration.
- Supports input data in `application/x.fb.proto` format. The specific
  Protocol Buffer message `type` must be specified. The service converts
  the parsed protobuf message to its string representation before writing.

Output File Handling:
- The output is always written as text. The `charset` and `errors` for encoding
  are defined by the service's `file_format` configuration (which must be `text/plain`).
- Supports various file opening modes:
  - `CREATE`: Creates a new file; fails if the file already exists.
  - `WRITE`: Overwrites the file if it exists, or creates it. For `stdout`/`stderr`.
  - `APPEND`: Appends to the file if it exists, or creates it.
  - `RENAME`: If the target file exists, it's renamed (e.g., `file.txt` to `file.txt.1`)
    before a new file is created for writing.

Configuration:
  The service is configured using `TextWriterConfig` (defined in `.api`), which
  specifies:
  - `filename`: The target output file path or special names `stdout`/`stderr`.
  - `file_format`: The MIME type and parameters (e.g., `charset`) for the output file.
  - `file_mode`: The mode for opening the output file.
  - `pipe_format`: The expected data format from the input pipe, used when the
    service initiates the connection.

The primary class in this module is:
- `TextWriterMicro`: Implements the text file writer microservice logic.
"""

from __future__ import annotations

import os
from typing import TextIO, cast

from firebird.base.protobuf import create_message, is_msg_registered
from saturnin.base import MIME, MIME_TYPE_PROTO, MIME_TYPE_TEXT, Channel, FileOpenMode, SocketMode, StopError
from saturnin.lib.data.onepipe import DataConsumerMicro, ErrorCode, FBDPMessage, FBDPSession

from .api import SUPPORTED_MIME, TextWriterConfig

# Classes

class TextWriterMicro(DataConsumerMicro):
    """Implementation of Text file writer microservice.
    """
    SYSIO = ('stdin', 'stdout', 'stderr')
    def _open_file(self) -> None:
        "Open the output file."
        self._close_file()
        if self.filename.lower() in self.SYSIO:
            fspec = self.SYSIO.index(self.filename.lower())
        else:
            fspec = self.filename
        if self.file_mode is FileOpenMode.CREATE:
            file_mode = 'x'
        elif self.file_mode is FileOpenMode.WRITE:
            file_mode = 'w'
        elif self.file_mode is FileOpenMode.RENAME:
            file_mode = 'w'
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
            file_mode = 'a'
        try:
            self.file = open(fspec, mode=file_mode,
                             encoding=self.file_format.params.get('charset', 'ascii'),
                             errors=self.file_format.params.get('errors', 'strict'),
                             closefd=self.filename.lower() not in self.SYSIO)
        except Exception as exc:
            raise StopError("Failed to open output file") from exc
    def _close_file(self) -> None:
        "Close the output file if necessary."
        if self.file:
            self.file.close()
            self.file = None
    def initialize(self, config: TextWriterConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        # Configuration
        self.file: TextIO | None = None
        self.filename: str = config.filename.value
        self.file_format: MIME = config.file_format.value
        self.file_mode: FileOpenMode = config.file_mode.value
        if self.pipe_mode is SocketMode.CONNECT:
            self.protocol.on_init_session = self.handle_init_session
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
        if cast(MIME, session.data_format).mime_type not in SUPPORTED_MIME:
            raise StopError(f"MIME type '{cast(MIME, session.data_format).mime_type}' is not a valid input format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        if cast(MIME, session.data_format).mime_type == MIME_TYPE_TEXT:
            for param in cast(MIME, session.data_format).params.keys():
                if param not in ('charset', 'errors'):
                    raise StopError(f"Unknown MIME parameter '{param}'",
                                    code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
            # cache attributes
            session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
            session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
        elif cast(MIME, session.data_format).mime_type == MIME_TYPE_PROTO:
            for param in cast(MIME, session.data_format).params.keys():
                if param != 'type':
                    raise StopError(f"Unknown MIME parameter '{param}'",
                                    code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
            proto_class = cast(MIME, session.data_format).params.get('type')
            if not is_msg_registered(proto_class):
                raise StopError(f"Unknown protobuf message type '{proto_class}'",
                                code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
            # cache attributes
            session.proto = create_message(proto_class)
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
        if session.data_format.mime_type == MIME_TYPE_PROTO:
            try:
                session.proto.ParseFromString(data)
            except Exception as exc:
                raise StopError("Protobuf error", code=ErrorCode.INVALID_DATA) from exc
            self.file.write(str(session.proto))
        else:
            try:
                self.file.write(data.decode(encoding=session.charset, errors=session.errors))
            except UnicodeError as exc:
                raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
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
    def handle_init_session(self, channel: Channel, session: FBDPSession) -> None:
        """Event executed from `send_open()` to set additional information to newly
        created session instance.
        """
        # cache attributes
        if cast(MIME, session.data_format).mime_type == MIME_TYPE_TEXT:
            session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
            session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
        elif cast(MIME, session.data_format).mime_type == MIME_TYPE_PROTO:
            session.proto = create_message(cast(MIME, session.data_format).params.get('type'))
