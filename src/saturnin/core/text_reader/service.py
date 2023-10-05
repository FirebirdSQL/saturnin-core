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

"""Saturnin microservices - Text file reader microservice

This microservice is a DATA_PROVIDER that sends blocks of text from file to output data pipe.
"""

from __future__ import annotations
from typing import TextIO, cast
from saturnin.base import StopError, MIME, MIME_TYPE_TEXT, Channel, SocketMode
from saturnin.lib.data.onepipe import DataProviderMicro, ErrorCode, FBDPSession, FBDPMessage
from .api import TextReaderConfig

# Classes

class TextReaderMicro(DataProviderMicro):
    """Text file reader microservice.
    """
    SYSIO = ('stdin', 'stdout', 'stderr')
    def _open_file(self) -> None:
        "Open the input file."
        self._close_file()
        if self.filename.lower() in self.SYSIO:
            fspec = self.SYSIO.index(self.filename.lower())
        else:
            fspec = self.filename
        try:
            self.file = open(fspec, mode='r',
                             encoding=self.file_format.params.get('charset', 'ascii'),
                             errors=self.file_format.params.get('errors', 'strict'),
                             closefd=self.filename.lower() not in self.SYSIO)
        except Exception as exc:
            raise StopError("Failed to open input file", code = ErrorCode.ERROR) from exc
    def _close_file(self) -> None:
        "Close the input file if necessary"
        if self.file:
            self.file.close()
            self.file = None
    def initialize(self, config: TextReaderConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        self.log_context = 'main'
        # Configuration
        self.file: TextIO = None
        self.filename: str = config.filename.value
        self.file_format: MIME = config.file_format.value
        self.max_chars: int = config.max_chars.value
        if self.pipe_mode is SocketMode.CONNECT:
            self.protocol.on_init_session = self.handle_init_session
    def handle_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Event handler executed when client connects to the data pipe via OPEN message.

        Arguments:
            session: Session associated with client.

        The session attributes `data_pipe`, `pipe_socket`, `data_format` and `params`
        contain information sent by client, and the event handler validates the request.

        If request should be rejected, it raises the `StopError` exception with `code`
        attribute containing the `ErrorCode` to be returned in CLOSE message.
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
                           exc: Exception=None) -> None:
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
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
