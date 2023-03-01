#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           text_writer/api.py
# DESCRIPTION:    API for Text file writer microservice
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

"""Saturnin microservices - API for Text file writer microservice

This microservice is a DATA_CONSUMER that wites blocks of text from input data pipe to file.
"""

from __future__ import annotations
from firebird.base.config import MIMEOption, StrOption, EnumOption
import uuid
from functools import partial
from firebird.base.protobuf import is_msg_registered
from saturnin.base import (VENDOR_UID, Error, FileOpenMode, AgentDescriptor, create_config,
                           ServiceDescriptor, MIME, MIME_TYPE_TEXT, MIME_TYPE_PROTO)
from saturnin.lib.data.onepipe import DataConsumerConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.text.writer
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.1.0.3.1.2'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.2.1'

SUPPORTED_MIME = (MIME_TYPE_TEXT, MIME_TYPE_PROTO)

# Configuration

class TextWriterConfig(DataConsumerConfig):
    """Text file writer microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        # Adjust default batch_size to compensate default 64K messages in producers
        self.batch_size.default = 5
        self.batch_size.value = 5
        #: File specification
        self.filename: StrOption = StrOption('filename', "File specification", required=True)
        #: File data format specification
        self.file_format: MIMEOption = \
            MIMEOption('file_format', "File data format specification", required=True,
                       default=MIME('text/plain;charset=utf-8'))
        #: File I/O mode
        self.file_mode: EnumOption = \
            (EnumOption('file_mode', FileOpenMode, "File I/O mode", required=False,
                        default=FileOpenMode.WRITE))
    def validate(self) -> None:
        """Extended validation.

        - Only 'text/plain' MIME type is alowed for `file_format`.
        - Only 'text/plain' and 'application/x.fb.proto' MIME types are alowed for `pipe_format`.
        - Only 'charset' and 'errors' MIME parameters are alowed for `file_format` and
          `pipe_format` specifications of type 'plain/text'.
        - Only FileOpenMode.WRITE is allowed for stdout and stderr.
        - FileOpenMode.READ is not supported.
        """
        super().validate()
        if (self.filename.value.lower() in ['stdout', 'stderr'] and
            self.file_mode.value != FileOpenMode.WRITE):
            raise Error("STD[OUT|ERR] support only WRITE open mode")
        if self.file_mode.value not in (FileOpenMode.APPEND, FileOpenMode.CREATE,
                                        FileOpenMode.RENAME, FileOpenMode.WRITE):
            raise Error(f"File open mode '{self.file_mode.value.name}' not supported")
        # File format
        if self.file_format.value.mime_type != MIME_TYPE_TEXT:
            raise Error(f"Only '{MIME_TYPE_TEXT}' file format supported")
        for param in self.file_format.value.params.keys():
            if param not in ('charset', 'errors'):
                raise Error(f"Unknown MIME parameter '{param}' in file format")
        # Pipe format
        if self.pipe_format.value.mime_type not in SUPPORTED_MIME:
            raise Error(f"MIME type '{self.pipe_format.value.mime_type}' is not a valid input format")
        if self.pipe_format.value.mime_type == MIME_TYPE_TEXT:
            for param in self.pipe_format.value.params.keys():
                if param not in ('charset', 'errors'):
                    raise Error(f"Unknown MIME parameter '{param}' in pipe format")
        elif self.pipe_format.value.mime_type == MIME_TYPE_PROTO:
            for param in self.pipe_format.value.params.keys():
                if param != 'type':
                    raise Error(f"Unknown MIME parameter '{param}' in pipe format")
            proto_class = self.pipe_format.value.params.get('type')
            if not is_msg_registered(proto_class):
                raise Error(f"Unknown protobuf message type '{proto_class}'")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.text.writer",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="text/writer")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Text writer microservice",
                      facilities=[],
                      factory='saturnin.core.text_writer.service:TextWriterMicro',
                      config=partial(create_config, TextWriterConfig, SERVICE_UID,
                                     f'{SERVICE_AGENT.name}_service'))
