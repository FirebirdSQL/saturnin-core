#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           proto_printer/service.py
# DESCRIPTION:    Protobuf printer microservice
# CREATED:        5.1.2020
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

"""Saturnin microservices - Protobuf printer microservice

This microservice is a DATA_FILTER:

- INPUT: protobuf messages
- PROCESSING: uses formatting template and data from protobuf message to create text
- OUTPUT: blocks of text
"""

from __future__ import annotations
from typing import Dict, Sequence, ItemsView, Callable, Any, cast
from firebird.base.protobuf import create_message, is_msg_registered, get_enum_field_type, \
     get_enum_value_name
from saturnin.base import StopError, MIME, MIME_TYPE_TEXT, MIME_TYPE_PROTO, Channel, SocketMode
from saturnin.lib.data.filter import DataFilterMicro, ErrorCode, FBDPSession, FBDPMessage
from .api import ProtoPrinterConfig

# Classes

class TransformationUtilities:
    """Utility class that provides useful data to string conversion methods.
    """
    LF = '\n'
    def msg_enum_name(self, msg, field_name: str) -> str:
        """Returns name for value of the enum field.
        """
        return self.enum_name(get_enum_field_type(msg, field_name),
                              getattr(msg, field_name))
    def enum_name(self, enum_type_name: str, value: Any) -> str:
        """Returns name for the enum value.
        """
        return get_enum_value_name(enum_type_name, value)
    def short_enum_name(self, msg, field_name: str) -> str:
        """Returns name for value of the enum field. If name contains '_', returns
        only name part after last underscore.
        """
        name = get_enum_value_name(msg, field_name)
        return name.rsplit('_',1)[1] if '_' in name else name
    def value_list(self, values: Sequence, separator: str=',', end='', indent=' ') -> str:
        """Returns string with list of values from iterable.
        """
        return separator.join(f"{indent}{value}" for value in values) + end
    def items_list(self, items: ItemsView, separator: str=',', end='', indent=' ') -> str:
        """Returns string with list of key = value pairs from ItemsView.
        """
        return separator.join(f"{indent}{key} = {value}" for key, value in items) + end
    def formatted(self, fmt: str, context: Dict) -> str:
        """Returns `fmt` as f-string evaluated using values from `context` dictionary as locals.
        """
        if context:
            return eval(f'f"""{fmt}"""', globals(), context)
        else:
            return fmt

class ProtoPrinterMicro(DataFilterMicro):
    """Implementation of Protobuf printer microservice.
    """
    def initialize(self, config: ProtoPrinterConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        self.log_context = 'main'
        #
        self.transform_func: Callable[[Any], str] = None
        self.fmt: str = None
        self.data: Any = None
        self.charset = 'ascii'
        self.errors = 'strict'
        self.utils = TransformationUtilities()
        #
        if config.input_pipe_format.value is not None:
            self.data = create_message(config.input_pipe_format.value.params.get('type'))
        #
        if config.template.value is not None:
            self.transform_func = self.__format_data
            self.fmt = 'f"""'+config.template.value+'"""'
        else:
            self.transform_func = config.func.value
        #
        if self.output_pipe_mode is SocketMode.CONNECT:
            self.output_protocol.on_init_session = self.handle_init_session
    def __format_data(self, data: Any, utils: TransformationUtilities) -> str:
        """Uses format specification from configuration to produce text for output.
        """
        return eval(self.fmt, {'data': data, 'utils': utils})
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
        fmt = cast(MIME, session.data_format)
        if fmt.mime_type != MIME_TYPE_PROTO:
            raise StopError(f"MIME type '{fmt.mime_type}' is not a valid input format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        proto_class = fmt.params.get('type')
        if self.data:
            if self.data.DESCRIPTOR.full_name != proto_class:
                raise StopError(f"Protobuf message type '{proto_class}' not allowed",
                                code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        else:
            if not is_msg_registered(proto_class):
                raise StopError(f"Unknown protobuf message type '{proto_class}'",
                                code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
            self.data = create_message(proto_class)
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
        if cast(MIME, session.data_format).mime_type != MIME_TYPE_TEXT:
            raise StopError(f"MIME type '{cast(MIME, session.data_format).mime_type}' is not a valid output format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        for param in cast(MIME, session.data_format).params.keys():
            if param not in ('charset', 'errors'):
                raise StopError(f"Unknown MIME parameter '{param}'",
                                code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
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
        data: str = self.output.popleft()
        try:
            msg.data_frame = data.encode(encoding=self.charset, errors=self.errors)
        except UnicodeError as exc:
            raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
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
        try:
            self.store_output(self.transform_func(self.data, self.utils))
        except Exception:
            raise StopError("Data formatting failed", code=ErrorCode.ERROR) from exc
