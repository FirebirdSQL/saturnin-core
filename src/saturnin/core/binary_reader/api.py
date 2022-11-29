#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           binary_reader/api.py
# DESCRIPTION:    API for binary data file reader microservice
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

"""Saturnin microservices - API for binary data file reader microservice

This microservice is a DATA_PROVIDER that sends blocks of binary data from file to output
data pipe.
"""

from __future__ import annotations
from firebird.base.config import create_config, StrOption, IntOption
import uuid
from functools import partial
from saturnin.base import VENDOR_UID, Error, AgentDescriptor, ServiceDescriptor
from saturnin.lib.data.onepipe import DataProviderConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.text.reader
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.2.0.3.2.1'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.1.1'

# Configuration

class BinaryReaderConfig(DataProviderConfig):
    """Text file reader microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        #: File specification
        self.filename: StrOption = StrOption('filename', "File specification", required=True)
        #: Data block size
        self.block_size: IntOption = \
            (IntOption('block_size',
                       "Data block size in bytes (-1 when size is stored before the data)",
                       required=True, signed=True))
    def validate(self) -> None:
        """Extended validation.

        - `block_size` is positive or -1.
        """
        super().validate()
        # Blocik size
        if (self.block_size.value < -1) or (self.block_size.value == 0):
            raise Error("'block_size' must be positive or -1")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.binary.reader",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="binary/reader")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Binary data reader microservice",
                      facilities=[],
                      factory='saturnin.core.binary_reader.service:BinaryReaderMicro',
                      config=partial(create_config, BinaryReaderConfig,
                                     f'{SERVICE_AGENT.name}_service'))
