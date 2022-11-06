#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           proto_printer/api.py
# DESCRIPTION:    API for Protobuf printer microservice
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
# Copyright (c) 2020 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin microservices - API for Protobuf printer microservice

This microservice is a DATA_FILTER:

- INPUT: protobuf messages
- PROCESSING: uses formatting template and data from protobuf message to create text
- OUTPUT: blocks of text
"""

from __future__ import annotations
import uuid
from functools import partial
from firebird.base.config import create_config, StrOption, PyCallableOption
from firebird.base.protobuf import is_msg_registered
from saturnin.base import (VENDOR_UID, Error, MIME, MIME_TYPE_TEXT, MIME_TYPE_PROTO,
                           SocketMode, AgentDescriptor, ServiceDescriptor)
from saturnin.lib.data.filter import DataFilterConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.proto.printer
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.2.0.3.3.1'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.2.1'

# Configuration

class ProtoPrinterConfig(DataFilterConfig):
    """Data printer microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        #
        self.output_pipe_format.default = MIME('text/plain;charset=utf-8')
        self.output_pipe_format.set_value(MIME('text/plain;charset=utf-8'))
        #
        self.template: StrOption = \
            StrOption('template', "Text formatting template")
        self.func: PyCallableOption = \
            PyCallableOption('func',
                             "Function that returns text representation of data",
                             'def f(data: Any, utils: TransformationUtilities) -> str:\n  ...\n')
    def validate(self) -> None:
        """Extended validation.

           - whether all required options have value other than None
           - that 'input_pipe_format' MIME type is 'text/plain'
           - that 'output_pipe_format' MIME type is 'application/x.fb.proto'
           - that exactly one from 'func' or 'template' options have a value
           - that 'func' option value could be compiled

        Raises:
            Error: When any check fails.
        """
        super().validate()
        #
        if self.output_pipe_format.value.mime_type != MIME_TYPE_TEXT:
            raise Error(f"Only '{MIME_TYPE_TEXT}' output format allowed.")
        if self.input_pipe_format.value is None:
            if self.input_pipe_mode.value is SocketMode.CONNECT:
                raise Error("Input pipe: `format` is required for CONNECT mode.")
        else:
            if self.input_pipe_format.value.mime_type != MIME_TYPE_PROTO:
                raise Error(f"Only '{MIME_TYPE_PROTO}' input format allowed.")
            if 'type' not in self.input_pipe_format.value.params:
                raise Error(f"Missing required 'type' MIME parameter in input format.")
            if not is_msg_registered(proto_class := self.input_pipe_format.value.params.get('type')):
                raise Error(f"Unknown protobuf message type '{proto_class}'")
        #
        defined = 0
        for opt in (self.template, self.func):
            if opt.value is not None:
                defined += 1
        if defined != 1:
            raise Error("Configuration must contain either 'template' or 'func' option")
        #
        try:
            self.func.value
        except Exception as exc:
            raise Error("Invalid code definition in 'func' option") from exc

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.proto.printer",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="proto/printer")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Protobuf data printer microservice",
                      facilities=[],
                      package='saturnin.core.proto_printer',
                      factory='saturnin.core.proto_printer.service:ProtoPrinterMicro',
                      config=partial(create_config, ProtoPrinterConfig,
                                     f'{SERVICE_AGENT.name}_service'))
