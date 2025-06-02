# SPDX-FileCopyrightText: 2018-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           proto_filter/service.py
# DESCRIPTION:    Protobuf filter microservice
# CREATED:        20.1.2020
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

"""Saturnin microservices - Protobuf filter microservice

This module provides the `ProtoFilterMicro` service, a DATA_FILTER that
selectively passes Protocol Buffer (protobuf) messages from an input data pipe
to an output data pipe based on user-defined criteria.

Core Functionality:
- Acts as a DATA_FILTER, conditionally forwarding protobuf messages.
- Receives protobuf messages of a configurable type from an input data pipe.
- Evaluates a Python expression or calls a Python function against each
  incoming message to determine if it should be passed through.
- Sends the filtered protobuf messages (of the same type as input) to an
  output data pipe.

Input Data Handling (Input Pipe):
- Expects data in `application/x.fb.proto` format.
- The specific input protobuf message `type` (e.g., `my.custom.Message`) must be
  specified in the `input_pipe_format` configuration.

Filtering Logic:
- Filtering is based on either an "include" or "exclude" condition.
  - Include: If the condition evaluates to True, the message is passed.
  - Exclude: If the condition evaluates to True, the message is dropped.
- The condition is defined by one of the following configuration options:
  `include_expr`, `include_func`, `exclude_expr`, or `exclude_func`.
- Expressions/functions are evaluated with the incoming protobuf message instance
  available as the `data` variable. The `datetime` module is also available
  in the evaluation context for expressions.

Output Data Handling (Output Pipe):
- Produces data in `application/x.fb.proto` format.
- The output protobuf message `type` is the same as the input message `type`.

Configuration:
  The service is configured using `ProtoFilterConfig` (defined in `.api`), which
  specifies:
  - `input_pipe_format`: The MIME type and `type` of the input protobuf messages.
  - `output_pipe_format`: The MIME type and `type` for the output (must match input).
  - `include_expr` / `include_func`: For inclusion-based filtering.
  - `exclude_expr` / `exclude_func`: For exclusion-based filtering.
  Only one of these four filter options can be active.

The primary class in this module is:
- `ProtoFilterMicro`: Implements the protobuf message filtering logic.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from typing import Any

from firebird.base.protobuf import create_message, is_msg_registered
from saturnin.base import MIME, MIME_TYPE_PROTO, Channel, StopError
from saturnin.lib.data.filter import DataFilterMicro, ErrorCode, FBDPMessage, FBDPSession

from .api import ProtoFilterConfig

# Classes

class ProtoFilterMicro(DataFilterMicro):
    """Implementation of Protobuf filter microservice.
    """
    def __check_fmt(self, fmt: MIME) -> None:
        if fmt.mime_type != MIME_TYPE_PROTO:
            raise StopError(f"MIME type '{fmt.mime_type}' is not a valid input format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        proto_class = fmt.params.get('type')
        if self.data.DESCRIPTOR.full_name != proto_class:
            raise StopError(f"Protobuf message type '{proto_class}' not allowed",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
    def initialize(self, config: ProtoFilterConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        #
        self.include_func: Callable[[Any], bool] | None = None
        self.exclude_func: Callable[[Any], bool] | None = None
        self.data: Any = None
        self.fmt: MIME = None
        #
        if config.include_expr.value is not None:
            self.include_func = config.include_expr.value.get_callable('data',
                                                                       {'datetime': datetime,})
        if config.include_func.value is not None:
            self.include_func = config.include_func.value
        if config.exclude_expr.value is not None:
            self.exclude_func = config.exclude_expr.value.get_callable('data',
                                                                       {'datetime': datetime,})
        if config.exclude_func.value is not None:
            self.exclude_func = config.exclude_func.value
        #
        self.fmt = config.input_pipe_format.value
        proto_class = self.fmt.params.get('type')
        if not is_msg_registered(proto_class):
            raise StopError(f"Unknown protobuf message type '{proto_class}'",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        self.data = create_message(proto_class)
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
        self.__check_fmt(session.data_format)
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
        self.__check_fmt(session.data_format)
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
        msg.data_frame = self.output.popleft()
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
            self.data.ParseFromString(data)
        except Exception as exc:
            raise StopError("Exception", code=ErrorCode.INVALID_DATA) from exc
        if self.include_func and not self.include_func(self.data):
            return
        if self.exclude_func and self.exclude_func(self.data):
            return
        self.store_output(self.data.SerializeToString())
