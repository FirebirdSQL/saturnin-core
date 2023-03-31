#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           text_filter/service.py
# DESCRIPTION:    Text line filter microservice
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

"""Saturnin microservices - Text line filter microservice

This microservice is a DATA_FILTER that reads blocks of text from input data pipe, and
writes lines that meet the specified conditions as blocks of text into output data pipe.
"""

from __future__ import annotations
from typing import List, Callable, cast
import re
from saturnin.base import StopError, MIME, MIME_TYPE_TEXT, Channel, SocketMode
from saturnin.lib.data.filter import DataFilterMicro, ErrorCode, FBDPSession, FBDPMessage
from .api import TextFilterConfig


# Classes

class TextLineFilterMicro(DataFilterMicro):
    """Implementation of Text line filter microservice.
    """
    def __regex_match(self, line: str) -> bool:
        "Helper filter function that check line against defined regex"
        return self.regex.search(line) is not None
    def initialize(self, config: TextFilterConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        self.log_context = 'main'
        #
        self.max_chars: int = config.max_chars.value
        self.filter_func: Callable = None
        if config.regex.value is not None:
            self.regex = re.compile(config.regex.value)
            self.filter_func = self.__regex_match
        elif config.expr.value is not None:
            self.filter_func = config.expr.value.get_callable('line')
        else:
            self.filter_func = config.func.value
        #
        self.input_lefover = None
        self.to_write: int = self.max_chars
        self.output_buffer: List[str] = []
        #
        if self.input_pipe_mode is SocketMode.CONNECT:
            self.input_protocol.on_init_session = self.handle_init_session
        if self.output_pipe_mode is SocketMode.CONNECT:
            self.output_protocol.on_init_session = self.handle_init_session
    def handle_init_session(self, channel: Channel, session: FBDPSession) -> None:
        """Event executed from `send_open()` to set additional information to newly
        created session instance.
        """
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
    def handle_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Event handler executed when client connects to INPUT or OUTPUT data pipe via
        OPEN message.
        """
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
        #
        self.to_write = self.max_chars
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
        self.handle_accept_client(channel, session)
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
        self.handle_accept_client(channel, session)
    def handle_output_produce_data(self, channel: Channel, session: FBDPSession, msg: FBDPMessage) -> None:
        """Event handler executed to store data into outgoing DATA message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            msg: DATA message that will be sent to client.
        """
        if not self.output:
            raise StopError("EOF", code=ErrorCode.OK)
        data = self.output.popleft()
        try:
            msg.data_frame = data.encode(encoding=session.charset, errors=session.errors)
        except UnicodeError as exc:
            raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
    def handle_input_accept_data(self, channel: Channel, session: FBDPSession, data: bytes) -> None:
        """Event handler executed to process data received in DATA message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            data: Data received from client.
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
        for line in lines:
            if self.filter_func(line):
                line += '\n'
                line_size = len(line)
                if self.to_write - line_size >= 0:
                    self.to_write -= line_size
                    self.output_buffer.append(line)
                else:
                    self.output_buffer.append(line[:self.to_write])
                    buf = ''.join(self.output_buffer)
                    self.store_output(buf)
                    output_leftover = line[self.to_write:]
                    self.output_buffer = [output_leftover]
                    self.to_write = self.max_chars - len(output_leftover)
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
        """
        buf = ''.join(self.output_buffer)
        self.store_output(buf)
