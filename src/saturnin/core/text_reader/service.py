# SPDX-FileCopyrightText: 2018-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           text_reader/service.py
# DESCRIPTION:    Text file reader microservice
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

"""Saturnin Microservices - Text File Reader

This module implements the Text File Reader microservice for the Saturnin
platform.

It provides the `TextReaderMicro` class, which acts as a `DATA_PROVIDER`
in the Firebird Data Protocol (FBDP). The service reads text content from a
specified file (or standard input stream) in configurable chunks and sends
these chunks as data frames over an output data pipe to a connected client.

Core Functionality:
- Acts as a DATA_PROVIDER, serving text data.
- Reads content from a local file or standard input (`stdin`).
- Transmits data in chunks to a connected data consumer.

File Input Handling:
- The input source is specified by the `filename` configuration option. This can
  be a path to a regular file or the special name `stdin`.
- The `file_format` configuration (which must be `text/plain`) dictates the
  `charset` (e.g., `utf-8`, `ascii`) and `errors` strategy (e.g., `strict`,
  `replace`) used for decoding the content read from the file/stream.

Data Transmission / Pipe Output:
- Data is sent over the data pipe as `text/plain`.
- The text read from the file is encoded into bytes for transmission using a
  `charset` and `errors` strategy. These are determined by:
  - The client's request (if the service is in LISTENING mode and the client
    specifies format parameters in its OPEN message).
  - The service's `pipe_format` configuration (if the service is in CONNECTING
    mode, or if the client does not specify).
- Text is read and sent in chunks, with the maximum number of characters per
  data message controlled by the `max_chars` configuration option.

Configuration:
  The service is configured using `TextReaderConfig` (defined in `.api`), which
  specifies:
  - `filename`: The source file path or `stdin`.
  - `file_format`: MIME type and parameters for reading the input file.
  - `max_chars`: Maximum characters to send in a single data message.
  - `pipe_format`: Default data format for the output pipe when initiating a connection.

The primary class in this module is:
- `TextReaderMicro`: Implements the text file reader microservice logic.
"""

from __future__ import annotations

from typing import TextIO, cast

from saturnin.base import MIME, MIME_TYPE_TEXT, Channel, SocketMode, StopError
from saturnin.lib.data.onepipe import DataProviderMicro, ErrorCode, FBDPMessage, FBDPSession

from .api import TextReaderConfig

# Classes

class TextReaderMicro(DataProviderMicro):
    """Implements the core logic for the Text File Reader microservice.

    This microservice acts as a `DATA_PROVIDER`, reading text from a file
    and sending it over an output data pipe using the Firebird Data Protocol (FBDP).

    It handles the opening, reading, and encoding of text from a specified file.
    to provide data blocks to a connected client via an output data pipe.
    Configuration options include the input filename, file encoding,
    and maximum characters per message.
    """
    SYSIO = ('stdin', 'stdout', 'stderr')
    def _open_file(self) -> None:
        """Opens the input file specified in the configuration.

        Handles standard files as well as special filenames like 'stdin'.
        The file is opened with encoding and error handling options derived
        from `file_format` configuration.

        Raises:
            StopError: If the file cannot be opened, with `ErrorCode.ERROR`.
        """
        self._close_file()
        if self.filename.lower() in self.SYSIO:
            fspec = self.SYSIO.index(self.filename.lower())
        else:
            fspec = self.filename
        try:
            self.file = open(fspec,
                             encoding=self.file_format.params.get('charset', 'ascii'),
                             errors=self.file_format.params.get('errors', 'strict'),
                             closefd=self.filename.lower() not in self.SYSIO)
        except Exception as exc:
            raise StopError("Failed to open input file", code = ErrorCode.ERROR) from exc
    def _close_file(self) -> None:
        """Closes the currently open input file, if any.

        Sets `self.file` to None after closing.
        """
        if self.file:
            self.file.close()
            self.file = None
    def initialize(self, config: TextReaderConfig) -> None:
        """Initializes the microservice with the given configuration.

        Calls the parent class's initialize method, then sets up specific
        attributes from the `TextReaderConfig`, such as filename, file format,
        and maximum characters per message. It also registers a session
        initialization handler if the service is in CONNECT mode.

        Arguments:
            config: The configuration object for this microservice.
        """
        super().initialize(config)
        # Configuration
        self.file: TextIO | None = None
        self.filename: str | None = config.filename.value
        self.file_format: MIME | None = config.file_format.value
        self.max_chars: int | None = config.max_chars.value
        if self.pipe_mode is SocketMode.CONNECT:
            self.protocol.on_init_session = self.handle_init_session # type: ignore
    def handle_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Handles a new client connection initiated by an OPEN message.

        This event handler validates the client's requested data format.
        It ensures the MIME type is 'text/plain' and that only 'charset'
        and 'errors' parameters are used. Upon successful validation,
        it caches the charset and error handling mode in the session and
        opens the configured input file.

        Args:
            channel: The communication channel for the data pipe.
            session: The FBDP session associated with the connecting client.
                     Session attributes like `data_format` are populated by the
                     protocol from the client's OPEN message.

        Raises:
            StopError: If the client's request is invalid (e.g., unsupported
                       data format or parameters), with an appropriate `ErrorCode`
                       to be sent in the CLOSE message. Also raised if the input
                       file cannot be opened.
        """
        super().handle_accept_client(channel, session)
        if cast(MIME, session.data_format).mime_type != MIME_TYPE_TEXT:
            raise StopError("Only 'text/plain' format supported",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        for param in cast(MIME, session.data_format).params.keys():
            if param not in ('charset', 'errors'):
                raise StopError(f"Unknown MIME parameter '{param}'",
                                code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
        # Client reqest is ok, we'll open the file we are configured to work with.
        self._open_file()
    def handle_produce_data(self, channel: Channel, session: FBDPSession, msg: FBDPMessage) -> None:
        """Produces data for an outgoing FBDP DATA message.

        This handler is called when the client is ready to receive data.
        It reads up to `self.max_chars` characters from the input file,
        encodes the chunk using the session's charset and error handling mode,
        and stores the resulting bytes in `msg.data_frame`.

        Arguments:
            channel: The communication channel for the data pipe.
            session: The FBDP session associated with the client. Contains
                     cached `charset` and `errors` attributes.
            msg: The outgoing `FBDPMessage` (DATA type) to be populated.
                 The handler must set `msg.data_frame`.

        Note:
            To indicate end of data, raise StopError with ErrorCode.OK code.

            Exceptions are handled by protocol, but only StopError is checked for protocol
            ErrorCode. As we want to report INVALID_DATA properly, we have to convert
            exceptions into StopError.

        Raises:
            StopError:
                - With `ErrorCode.OK` to indicate the end of the file (EOF).
                - With `ErrorCode.INVALID_DATA` if a `UnicodeError` occurs
                  during encoding.
                - If the input file is not open and cannot be opened.
        """
        if self.file is None:
            self._open_file()
        try:
            if buf := self.file.read(self.max_chars):
                msg.data_frame = buf.encode(encoding=session.charset, errors=session.errors)
            else:
                raise StopError('OK', code=ErrorCode.OK)
        except UnicodeError as exc:
            raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
    def handle_pipe_closed(self, channel: Channel, session: FBDPSession, msg: FBDPMessage,
                           exc: Exception | None=None) -> None:
        """Handles the closure of the data pipe.

        This event handler is executed when a CLOSE message is received from
        the client or sent by this service. It ensures that any resources
        associated with the current transmission, specifically the input file,
        are released.

        Arguments:
            channel: The communication channel for the data pipe.
            session: The FBDP session associated with the peer.
            msg: The CLOSE message that was received or sent.
            exc: The exception that led to the pipe closure, if any.
        """
        super().handle_pipe_closed(channel, session, msg, exc)
        self._close_file()
    def handle_init_session(self, channel: Channel, session: FBDPSession) -> None:
        """Initializes a new session when the service initiates a connection (CONNECT mode).

        This event handler is called by `send_open()` before sending the
        OPEN message to the peer. It caches the `charset` and `errors`
        parameters from `session.data_format` (which is based on `self.pipe_format`)
        into the session object for later use during data production.

        Arguments:
            channel: The communication channel for the data pipe.
            session: The newly created `FBDPSession` instance to be initialized.
        """
        # cache attributes
        session.charset: str = cast(MIME, session.data_format).params.get('charset', 'ascii') # type: ignore
        session.errors: str = cast(MIME, session.data_format).params.get('errors', 'strict') # type: ignore
