#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           fb_trace_parse/api.py
# DESCRIPTION:    API for Firebird trace parser microservice
# CREATED:        18.01.2021
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

"""Saturnin microservices - API for Firebird trace parser microservice

This microservice is a DATA_FILTER that reads blocks of Firebird trace session text protocol
from input data pipe, and sends parsed Firebird trace entries into output data pipe.
"""

from __future__ import annotations
import uuid
from functools import partial
from saturnin.base import (create_config, VENDOR_UID, Error, MIME, MIME_TYPE_TEXT,
                           MIME_TYPE_PROTO, AgentDescriptor, ServiceDescriptor)
from saturnin.lib.data.filter import DataFilterConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.firebird.trace.parser
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.1.0.3.4.2.2'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.1.1'

TRACE_PROTO =  'saturnin.core.protobuf.fbtrace.TraceEntry'
TRACE_FORMAT = MIME(f'{MIME_TYPE_PROTO};type={TRACE_PROTO}')

# Configuration

class FbTraceParserConfig(DataFilterConfig):
    """Firebird log parser microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        #
        self.input_pipe_format.default = MIME('text/plain;charset=utf-8')
        self.input_pipe_format.set_value(MIME('text/plain;charset=utf-8'))
        self.output_pipe_format.default = TRACE_FORMAT
        self.output_pipe_format.set_value(TRACE_FORMAT)
    def validate(self) -> None:
        """Extended validation.

        - Only 'text/plain' MIME type is alowed for `input_pipe_format`.
        - Only 'charset' and 'errors' MIME parameters are alowed for `input_pipe_format`.
        - Only `TRACE_FORMAT` MIME type is allowed for `output_pipe_format`.

        Raises:
            Error: When any check fails.
        """
        super().validate()
        # Input Pipe format
        fmt = self.input_pipe_format
        if fmt.value.mime_type != MIME_TYPE_TEXT:
            raise Error(f"MIME type '{fmt.value.mime_type}' is not a valid input format")
        # MIME parameters
        for param in fmt.value.params.keys():
            if param not in ('charset', 'errors'):
                raise Error(f"Unknown MIME parameter '{param}' in pipe format")
        # Output Pipe format
        fmt = self.output_pipe_format
        if fmt.value.mime_type != MIME_TYPE_PROTO:
            raise Error(f"MIME type '{fmt.value.mime_type}' is not a valid output format")
        if fmt.value.params['type'] != TRACE_PROTO:
            raise Error(f"Unsupported protobuf type '{fmt.value.params['type']}'")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name='saturnin.firebird.trace.parser',
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="firebird-trace/parser")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Firebird trace parser microservice",
                      facilities=[],
                      factory='saturnin.core.fb_trace_parse.service:FbTraceParserMicro',
                      config=partial(create_config, FbTraceParserConfig, SERVICE_UID,
                                     f'{SERVICE_AGENT.name}_service'))
