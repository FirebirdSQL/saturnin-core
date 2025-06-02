# SPDX-FileCopyrightText: 2019-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
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

This module provides the `TextLineFilterMicro` service, a DATA_FILTER that
receives blocks of text from an input data pipe, filters these lines based on
user-defined criteria, and then writes the qualifying lines as blocks of text
to an output data pipe.

Core Functionality:
- Acts as a DATA_FILTER, selectively passing text lines.
- Receives text data in blocks from an input data pipe.
- Processes the input text line by line, reassembling lines that may span
  across multiple input data blocks.
- Applies a filter condition to each complete line.
- Sends lines that satisfy the filter condition to an output data pipe,
  also in blocks.

Input Data Handling (Input Pipe):
- Expects data in `text/plain` format.
- The character set (`charset`) and error handling strategy (`errors`) for
  decoding the input text are determined by the client's request or the
  service's `input_pipe_format` configuration.

Filtering Logic:
- Filtering is performed on a per-line basis.
- The filter condition is defined by exactly one of the following configuration options:
  - `regex`: A regular expression to match against each line.
  - `expr`: A Python expression evaluated for each line (with the line available
    as the `line` variable).
  - `func`: A Python callable that accepts the line as a string and returns `True`
    if the line should be passed.

Output Data Handling (Output Pipe):
- Produces data in `text/plain` format.
- The character set (`charset`) and error handling strategy (`errors`) for
  encoding the output text are determined by the client's request or the
  service's `output_pipe_format` configuration.
- Output text is buffered and sent in blocks, with the maximum number of
  characters per block controlled by the `max_chars` configuration option.

Configuration:
  The service is configured using `TextFilterConfig` (defined in `.api`), which
  specifies:
  - `input_pipe_format`: MIME type and parameters for the input pipe.
  - `output_pipe_format`: MIME type and parameters for the output pipe.
  - `max_chars`: Maximum characters to send in a single output data message.
  - `regex`, `expr`, or `func`: The filter definition.

The primary class in this module is:
- `TextLineFilterMicro`: Implements the text line filtering logic.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import List, cast

from saturnin.base import MIME, MIME_TYPE_TEXT, Channel, SocketMode, StopError
from saturnin.lib.data.filter import DataFilterMicro, ErrorCode, FBDPMessage, FBDPSession

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
        self.input_leftover = None
        self.to_write: int = self.max_chars
        self.output_buffer: list[str] = []
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
        if self.input_leftover is not None:
            block = self.input_leftover + block
            self.input_leftover = None
        lines = block.splitlines()
        if block[-1] != '\n':
            self.input_leftover = lines.pop()
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
