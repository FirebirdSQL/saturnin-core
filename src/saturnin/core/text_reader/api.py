#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           text_reader/api.py
# DESCRIPTION:    API for Text file reader microservice
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

"""Saturnin microservices - API for Text file reader microservice

This microservice is a DATA_PROVIDER that sends blocks of text from file to output data pipe.
"""

from __future__ import annotations
from firebird.base.config import MIMEOption, StrOption, IntOption
import uuid
from functools import partial
from saturnin.base import (VENDOR_UID, Error, AgentDescriptor, ServiceDescriptor, MIME,
                           MIME_TYPE_TEXT, create_config)
from saturnin.lib.data.onepipe import DataProviderConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.text.reader
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.1.0.3.1.1'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.2.1'

# Configuration

class TextReaderConfig(DataProviderConfig):
    """Text file reader microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        # Adjust default batch_size to compensate default 64K messages
        self.batch_size.default = 5
        self.batch_size.value = 5
        #: File specification
        self.filename: StrOption = StrOption('filename', "File specification", required=True)
        #: File data format specification
        self.file_format: MIMEOption = \
            MIMEOption('file_format', "File data format specification", required=True,
                       default=MIME('text/plain;charset=utf-8'))
        #: Max. number of characters transmitted in one message
        self.max_chars: IntOption = \
            IntOption('max_chars',
                      "Max. number of characters transmitted in one message",
                      required=True, default=65535)
    def validate(self) -> None:
        """Extended validation.

        - Only 'text/plain' MIME type is alowed for `file_format` and `pipe_format`
          specifications.
        - Only 'charset' and 'errors' MIME parameters are alowed for `file_format` and
          `pipe_format` specifications.
        """
        super().validate()
        # File format
        if self.file_format.value.mime_type != MIME_TYPE_TEXT:
            raise Error("Only 'text/plain' file format supported")
        for param in self.file_format.value.params.keys():
            if param not in ('charset', 'errors'):
                raise Error(f"Unknown MIME parameter '{param}' in file format")
        # Pipe format
        if self.pipe_format.value.mime_type != MIME_TYPE_TEXT:
            raise Error("Only 'text/plain' pipe format supported")
        for param in self.pipe_format.value.params.keys():
            if param not in ('charset', 'errors'):
                raise Error(f"Unknown MIME parameter '{param}' in pipe format")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.text.reader",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="text/reader")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Text reader microservice",
                      facilities=[],
                      factory='saturnin.core.text_reader.service:TextReaderMicro',
                      config=partial(create_config, TextReaderConfig, SERVICE_UID,
                                     f'{SERVICE_AGENT.name}_service'))
