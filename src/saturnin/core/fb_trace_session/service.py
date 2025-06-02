# SPDX-FileCopyrightText: 2021-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           fb_trace_session/service.py
# DESCRIPTION:    Firebird trace session provider microservice
# CREATED:        06.01.2021
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

"""Saturnin microservices - Firebird trace session provider.

This microservice is a DATA_PROVIDER that runs trace session on Firebird server via
services and send trace output as blocks of text to output data pipe.

This module provides the `FbTraceSessionMicro` service, a DATA_PROVIDER that
initiates and manages a trace session on a Firebird server. It captures the
trace output and sends it as blocks of text over an output data pipe.

Core Functionality:
- Acts as a DATA_PROVIDER, serving text data from a Firebird trace session.
- Connects to a specified Firebird server using the `firebird-driver`.
- Starts a new trace session on the server using a provided trace configuration.
- Retrieves the live text output from the running trace session.
- Transmits the trace output in chunks to a connected data consumer.
- Stops the trace session when the data transmission is complete or interrupted.

Data Source (Firebird Trace Session):
- The target Firebird server is specified by the `server` configuration option,
  which refers to a server definition in the Firebird driver configuration.
- The `trace` configuration option provides the configuration string
  that defines what events the trace session will capture.
- An optional `session_name` can be provided for the trace session on the server.

Data Transmission / Pipe Output:
- Data is sent over the data pipe as `text/plain`.
- The trace output text read from the server is encoded into bytes for transmission.
  The `charset` (e.g., `utf-8`, `ascii`) and `errors` strategy (e.g., `strict`,
  `replace`) for this encoding are determined by:
  - The client's request (if the service is in LISTENING mode and the client
    specifies format parameters in its OPEN message).
  - The service's `pipe_format` configuration (if the service is in CONNECTING
    mode, or if the client does not specify).
- Trace output is read and sent in chunks, with the maximum number of characters
  per data message controlled by the `max_chars` configuration option.

Configuration:
  The service is configured using `FbTraceSessionConfig` (defined in `.api`), which
  specifies:
  - `server`: The Firebird server identification (from driver configuration).
  - `max_chars`: Maximum characters to send in a single data message.
  - `trace`: The XML trace configuration string.
  - `session_name`: An optional name for the trace session.
  - `pipe_format`: Default data format (`text/plain` with optional `charset`
    and `errors`) for the output pipe when initiating a connection.

The primary class in this module is:
- `FbTraceSessionMicro`: Implements the Firebird trace session provider logic.
"""

from __future__ import annotations

from typing import cast

from firebird.driver import Server, connect_server
from saturnin.base import MIME, MIME_TYPE_TEXT, Channel, SocketMode, StopError
from saturnin.lib.data.onepipe import DataProviderMicro, ErrorCode, FBDPMessage, FBDPSession

from .api import FbTraceSessionConfig

# Classes

class FbTraceSessionMicro(DataProviderMicro):
    """Implementation of Firebird trace session provider microservice.
    """
    def _read(self, max_chars: int) -> str | None:
        "Read `max_chars` characters from service"
        to_read = max_chars - len(self.in_buffer)
        eof = False
        lines = []
        if self.in_buffer:
            lines.append(self.in_buffer)
            self.in_buffer = ''
        while not eof and to_read > 0:
            line = self.svc.readline()
            eof = line is None
            if not eof:
                line_size = len(line)
                if to_read - line_size >= 0:
                    to_read -= line_size
                    lines.append(line)
                else:
                    lines.append(line[:to_read])
                    self.in_buffer = line[to_read:]
                    to_read = 0
        if lines:
            return ''.join(lines)
        return None
    def _start_session(self) -> None:
        """Request log from Firebird server.
        """
        self._close_session()
        self.svc.trace.start(config=self.session_conf, name=self.session_name)
    def _close_session(self) -> None:
        """Close log from Firebird server.
        """
        if self.session_id is not None:
            with connect_server(self.server) as svc:
                svc.trace.stop(session_id=self.session_id)
            self.session_id = None
    def initialize(self, config: FbTraceSessionConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        self.svc: Server | None = None
        self.in_buffer: str = ''
        # Configuration
        self.server: str = config.server.value
        self.max_chars: int = config.max_chars.value
        self.session_conf: str = config.trace.value
        self.session_name: str = config.session_name.value
        self.session_id: int | None = None
        #
        if self.pipe_mode is SocketMode.CONNECT:
            self.protocol.on_init_session = self.handle_init_session
    def aquire_resources(self) -> None:
        """Aquire resources required by component (open files, connect to other services etc.).

        Must raise an exception when resource aquisition fails.
        """
        super().aquire_resources()
        self.svc = connect_server(self.server)
    def release_resources(self) -> None:
        """Release resources aquired by component (close files, disconnect from other services etc.)
        """
        super().release_resources()
        if self.svc:
            self.svc.close()
            self.svc = None
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
                raise StopError(f"Unsupported MIME parameter '{param}'",
                                code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
        # Client reqest is ok, we'll open the file we are configured to work with.
        self._start_session()
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
        try:
            if buf := self._read(self.max_chars):
                msg.data_frame = buf.encode(encoding=session.charset, errors=session.errors)
            else:
                raise StopError('OK', code=ErrorCode.OK)
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
        self._close_session()
    def handle_init_session(self, channel: Channel, session: FBDPSession) -> None:
        """Event executed from `send_open()` to set additional information to newly
        created session instance.
        """
        self._start_session()
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
