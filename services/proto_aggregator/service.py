#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           prot_aggregator/service.py
# DESCRIPTION:    Protobuf aggregator microservice
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
# Copyright (c) 2020 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin microservices - Protobuf aggregator microservice

This microservice is a DATA_FILTER:

- INPUT: protobuf messages
- PROCESSING: uses expressions / functions evaluating data from protobuf message to
  aggregator data for output
- OUTPUT: protobuf messages
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Any
from firebird.base.signal import eventsocket
from firebird.base.protobuf import create_message, is_msg_registered
from saturnin.base import StopError, MIME_TYPE_PROTO, Channel
from saturnin.lib.data.filter import DataFilterMicro, ErrorCode, FBDPSession, FBDPMessage
from .api import ProtoAggregatorConfig, AGGREGATE_FORMAT, AGGREGATE_PROTO

# Classes

class GroupByItem:
    """GROUP BY item handler."""
    def __init__(self, spec: str):
        if ':' in spec:
            self.name, self.spec = spec.split(':')
        else:
            self.spec = spec
            self.name = spec
        ns = {}
        code = compile(f"def expr(data):\n    return {self.spec}",
                       f"group_by({self.spec})", 'exec')
        eval(code, ns)
        self._func = ns['expr']
    def get_key(self, data: Any) -> Any:
        """Returns GROUP BY key value"""
        return self._func(data)


class AggregateItem:
    """Aggregate item handler."""
    def __init__(self, spec: str):
        self.__count: int = 0
        self.__value: Any = None
        self.spec = spec
        self.aggregate_func, field_spec = spec.split(':', 1)
        if ' as ' in self.aggregate_func:
            self.aggregate_func, self.name = self.aggregate_func.split(' as ')
        else:
            self.name = self.aggregate_func
        ns = {}
        code = compile(f"def expr(data):\n    return {field_spec}",
                       f"{self.aggregate_func}({field_spec})", 'exec')
        eval(code, ns)
        self._func = ns['expr']
        #
        if self.aggregate_func == 'count':
            self.aggregate = self.agg_count
        elif self.aggregate_func == 'min':
            self.aggregate = self.agg_min
        elif self.aggregate_func == 'max':
            self.aggregate = self.agg_max
        elif self.aggregate_func in ['sum', 'avg']:
            self.aggregate = self.agg_sum_avg
    def agg_count(self, data: Any) -> None:
        """COUNT aggregate.
        """
        self.__count += 1
        self.__value = self.__count
    def agg_min(self, data: Any) -> None:
        """MIN aggregate.
        """
        self.__count += 1
        if self.__value is None:
            self.__value = self._func(data)
        else:
            self.__value = min(self.__value, self._func(data))
    def agg_max(self, data: Any) -> None:
        """MAX aggregate
        """
        self.__count += 1
        if self.__value is None:
            self.__value = self._func(data)
        else:
            self.__value = max(self.__value, self._func(data))
    def agg_sum_avg(self, data: Any) -> None:
        """SUM aggregate
        """
        self.__count += 1
        if self.__value is None:
            self.__value = self._func(data)
        else:
            self.__value += self._func(data)
    def get_result(self) -> Any:
        """Returns result of the aggregate."""
        if self.__value is not None and self.aggregate_func == 'avg':
            return self.__value / self.__count
        elif self.__value is None and self.aggregate_func == 'count':
            return 0
        else:
            return self.__value
    @eventsocket
    def aggregate(self, data: Any) -> None:
        """Process value.
        """

class ProtoAggregatorMicro(DataFilterMicro):
    """Implementation of Data aggregator microservice.
    """
    def initialize(self, config: ProtoAggregatorConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        self.log_context = 'main'
        #
        self.data: Any = None
        self.group_by: List[GroupByItem] = []
        self.agg_defs: List[str] = []
        self.aggregates: Dict[Tuple, AggregateItem] = {}
        #
        for item in config.group_by.value:
            self.group_by.append(GroupByItem(item))
        for item in config.aggregate.value:
            self.agg_defs.append(item)
        #
        proto_class = config.input_pipe_format.value.params.get('type')
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
        if session.data_format != MIME_TYPE_PROTO:
            raise StopError(f"MIME type '{session.data_format}' is not a valid input format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        proto_class = session.data_format.params.get('type')
        if self.data.DESCRIPTOR.full_name != proto_class:
            raise StopError(f"Protobuf message type '{proto_class}' not allowed",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
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
        if session.data_format != AGGREGATE_FORMAT:
            raise StopError(f"Only '{AGGREGATE_FORMAT}' output format supported",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
    def finish_input_processing(self, channel: Channel, session: FBDPSession, code: ErrorCode) -> None:
        """Called when input pipe is closed while output pipe will remain open.

        When code is ErrorCode.OK, the input was closed normally. Otherwise it indicates
        the type of problem that caused the input to be closed.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with peer.
            code:    Input pipe closing ErrorCode.
        """
        output_data = create_message(AGGREGATE_PROTO)
        batch = []
        for key, items in self.aggregates.items():
            output_data.Clear()
            i = 0
            for grp in self.group_by:
                output_data.data[grp.name] = key[i]
                i += 1
            for item in items:
                output_data.data[item.name] = item.get_result()
            batch.append(output_data.SerializeToString())
        self.store_batch_output(batch)
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
        #
        key = tuple(item.get_key(self.data) for item in self.group_by)
        agg = self.aggregates.get(key)
        if agg is None:
            agg = [AggregateItem(spec) for spec in self.agg_defs]
            self.aggregates[key] = agg
        for item in agg:
            item.aggregate(self.data)
