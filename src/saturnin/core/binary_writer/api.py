# SPDX-FileCopyrightText: 2021-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           binary_writer/api.py
# DESCRIPTION:    API for binary data file writer microservice
# CREATED:        05.01.2021
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

"""Saturnin microservices - API for binary data file writer microservice

This microservice is a DATA_CONSUMER that wites binary data from input data pipe to file.
"""

from __future__ import annotations
from firebird.base.config import StrOption, EnumOption
import uuid
from enum import Enum, auto
from functools import partial
from saturnin.base import (create_config, VENDOR_UID, Error, FileOpenMode, AgentDescriptor,
                           ServiceDescriptor)
from saturnin.lib.data.onepipe import DataConsumerConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.binary.writer
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.1.0.3.2.2'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.1.1'

class FileStorageType(Enum):
    """Binary data storage type.
    """
    STREAM = auto()
    BLOCK = auto()

# Configuration

class BinaryWriterConfig(DataConsumerConfig):
    """Text file writer microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        #: File specification
        self.filename: StrOption = StrOption('filename', "File specification", required=True)
        #: File I/O mode
        self.file_mode: EnumOption = \
            (EnumOption('file_mode', FileOpenMode, "File I/O mode", required=False,
                        default=FileOpenMode.WRITE))
        #: File data storage type
        self.file_type: EnumOption = \
            (EnumOption('file_type', FileStorageType, "File data storage type", required=True))
    def validate(self) -> None:
        """Extended validation.

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

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.binary.writer",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="binary/writer")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Binary data writer microservice",
                      facilities=[],
                      factory='saturnin.core.binary_writer.service:BinaryWriterMicro',
                      config=partial(create_config, BinaryWriterConfig, SERVICE_UID,
                                     f'{SERVICE_AGENT.name}_service'))
