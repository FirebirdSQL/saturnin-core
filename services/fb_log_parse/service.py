#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           fb_log_parse/service.py
# DESCRIPTION:    Firebird log parser microservice
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

"""Saturnin microservices - Firebird log parser microservice

This microservice is a DATA_FILTER that reads blocks of Firebird log text from input data
pipe, and sends parsed Firebird log entries into output data pipe.
"""

from __future__ import annotations
from typing import List, cast
from firebird.base.types import STOP
from firebird.base.protobuf import create_message
from firebird.lib.log import LogParser, LogMessage
from saturnin.base import StopError, MIME, MIME_TYPE_TEXT, MIME_TYPE_PROTO, Channel, SocketMode
from saturnin.lib.data.filter import DataFilterMicro, ErrorCode, FBDPSession, FBDPMessage
from .api import FbLogParserConfig, LOG_PROTO

# Classes

class FbLogParserMicro(DataFilterMicro):
    """Implementation of Firebird log parser microservice.
    """
    def initialize(self, config: FbLogParserConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        self.log_context = 'main'
        #
        self.proto = create_message(LOG_PROTO)
        self.entry_buf: List[str] = []
        self.parser: LogParser = LogParser()
        self.input_lefover = None
        #
        if self.input_pipe_mode is SocketMode.CONNECT:
            self.input_protocol.on_init_session = self.handle_init_session
    def handle_init_session(self, channel: Channel, session: FBDPSession) -> None:
        """Event executed from `send_open()` to set additional information to newly
        created session instance.
        """
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
    def handle_input_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Event handler executed when client connects to INPUT data pipe via OPEN message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        The session attributes `data_pipe`, `pipe_socket`, `data_format` and `params`
        contain information sent by client, and the event handler validates the request.

        If request should be rejected, it raises the `StopError` exception with `code`
        attribute containing the `ErrorCode` to be returned in CLOSE message.
        """
        super().handle_input_accept_client(channel, session)
        if cast(MIME, session.data_format).mime_type != MIME_TYPE_TEXT:
            raise StopError(f"MIME type '{cast(MIME, session.data_format).mime_type}' is not a valid input format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        for param in cast(MIME, session.data_format).params.keys():
            if param not in ('charset', 'errors'):
                raise StopError(f"Unknown MIME parameter '{param}'",
                                code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
    def handle_output_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Event handler executed when client connects to OUTPUT data pipe via OPEN message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        The session attributes `data_pipe`, `pipe_socket`, `data_format` and `params`
        contain information sent by client, and the event handler validates the request.

        If request should be rejected, it raises the `StopError` exception with `code`
        attribute containing the `ErrorCode` to be returned in CLOSE message.
        """
        super().handle_output_accept_client(channel, session)
        if cast(MIME, session.data_format).mime_type != MIME_TYPE_PROTO:
            raise StopError(f"MIME type '{cast(MIME, session.data_format).mime_type}' is not a valid output format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        if (_type := cast(MIME, session.data_format).params['type']) != LOG_PROTO:
            raise StopError(f"Unsupported protobuf type '{_type}'",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
    def handle_output_produce_data(self, channel: Channel, session: FBDPSession, msg: FBDPMessage) -> None:
        """Event handler executed to store data into outgoing DATA message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            msg: DATA message that will be sent to client.

        Important:
            The base implementation simply raises StopError with ErrorCode.OK code, so
            the descendant class must override this method without super() call.

            The event handler must `popleft()` data from `output` queue and store them in
            `msg.data_frame` attribute. It may also set ACK-REQUEST flag and `type_data`
            attribute.

            The event handler may cancel the transmission by raising the `StopError`
            exception with `code` attribute containing the `ErrorCode` to be returned in
            CLOSE message.

        Note:
            To indicate end of data, raise StopError with ErrorCode.OK code.
        """
        if not self.output:
            raise StopError("EOF", code=ErrorCode.OK)
        data: LogMessage = self.output.popleft()
        try:
            self.proto.Clear()
            self.proto.origin = data.origin
            self.proto.timestamp.FromDatetime(data.timestamp)
            self.proto.level = data.level.value
            self.proto.code = data.code
            self.proto.facility = data.facility.value
            self.proto.message = data.message
            for key, value in data.params.items():
                self.proto.params[key] = value
            msg.data_frame = self.proto.SerializeToString()
        except Exception as exc:
            raise StopError("Exception", code=ErrorCode.INVALID_DATA) from exc
    def handle_input_accept_data(self, channel: Channel, session: FBDPSession, data: bytes) -> None:
        """Event handler executed to process data received in DATA message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            data: Data received from client.

        Important:
            Any output data produced by event handler must be stored into output queue via
            `store_output()` method.

            The base implementation simply raises StopError with ErrorCode.OK code, so
            the descendant class must override this method without super() call.

            The event handler may cancel the transmission by raising the `StopError`
            exception with `code` attribute containing the `ErrorCode` to be returned in
            CLOSE message.

        Note:
            The ACK-REQUEST in received DATA message is handled automatically by protocol.
        """
        try:
            block: str = data.decode(encoding=session.charset, errors=session.errors)
        except UnicodeError as exc:
            raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
        if self.input_lefover is not None:
            block = self.input_lefover + block
            self.input_lefover = None
        lines = block.splitlines()
        if block[-1] != '\n':
            self.input_lefover = lines.pop()
        batch = []
        for line in lines:
            if (entry := self.parser.push(line)) is not None:
                batch.append(entry)
        if batch:
            self.store_batch_output(batch)
    def finish_input_processing(self, channel: Channel, session: FBDPSession, code: ErrorCode) -> None:
        """Called when input pipe is closed while output pipe will remain open.

        When code is ErrorCode.OK, the input was closed normally. Otherwise it indicates
        the type of problem that caused the input to be closed.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with peer.
            code:    Input pipe closing ErrorCode.

        Note:
            This method is not called when code is not ErrorCode.OK and `propagate_input_error`
            option is True.

            The default implementation does nothing.
        """
        if (entry := self.parser.push(STOP)) is not None:
            self.store_output(entry)
