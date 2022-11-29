#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           fb_log_parse/api.py
# DESCRIPTION:    API for Firebird log parser microservice
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

"""Saturnin microservices - API for Firebird log parser microservice

This microservice is a DATA_FILTER that reads blocks of Firebird log text from input data
pipe, and sends parsed Firebird log entries into output data pipe.
"""

from __future__ import annotations
import uuid
from functools import partial
from firebird.base.config import create_config
from saturnin.base import (VENDOR_UID, Error, MIME, MIME_TYPE_TEXT, MIME_TYPE_PROTO,
                           AgentDescriptor, ServiceDescriptor)
from saturnin.lib.data.filter import DataFilterConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.firebird.log.parser
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.2.0.3.4.1.2'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.2.1'

LOG_PROTO =  'saturnin.core.protobuf.fblog.LogEntry'
LOG_FORMAT = MIME(f'{MIME_TYPE_PROTO};type={LOG_PROTO}')

# Configuration

class FbLogParserConfig(DataFilterConfig):
    """Firebird log parser microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        #
        self.input_pipe_format.default = MIME('text/plain;charset=utf-8')
        self.input_pipe_format.set_value(MIME('text/plain;charset=utf-8'))
        self.output_pipe_format.default = LOG_FORMAT
        self.output_pipe_format.set_value(LOG_FORMAT)
    def validate(self) -> None:
        """Extended validation.

        - Only 'text/plain' MIME type is alowed for `input_pipe_format`.
        - Only 'charset' and 'errors' MIME parameters are alowed for `input_pipe_format`.
        - Only `LOG_FORMAT` MIME type is allowed for `output_pipe_format`.

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
        if fmt.value.params['type'] != LOG_PROTO:
            raise Error(f"Unsupported protobuf type '{fmt.value.params['type']}'")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name='saturnin.firebird.log.parser',
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="firebird-log/parser")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Firebird log parser microservice",
                      facilities=[],
                      factory='saturnin.core.fb_log_parse.service:FbLogParserMicro',
                      config=partial(create_config, FbLogParserConfig,
                                     f'{SERVICE_AGENT.name}_service'))
