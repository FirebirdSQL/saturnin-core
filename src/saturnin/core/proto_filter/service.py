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

This microservice is a DATA_FILTER:

- INPUT: protobuf messages
- PROCESSING: uses expressions / functions evaluating data from protobuf message to filter data for output
- OUTPUT: protobuf messages
"""

from __future__ import annotations
from typing import Callable, Any
import datetime
from firebird.base.protobuf import create_message, is_msg_registered
from saturnin.base import StopError, MIME, MIME_TYPE_PROTO, Channel
from saturnin.lib.data.filter import DataFilterMicro, ErrorCode, FBDPSession, FBDPMessage
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
        self.log_context = 'main'
        #
        self.include_func: Callable = None
        self.exclude_func: Callable = None
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
