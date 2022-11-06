#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           fb_log_fromsrv/api.py
# DESCRIPTION:    API for Firebird log from server provider microservice
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

"""Saturnin microservices - API for Firebird log from server provider microservice

This microservice is a DATA_PROVIDER that fetches Firebird log from Firebird server via
services and send it as blocks of text to output data pipe.
"""

from __future__ import annotations
import uuid
from firebird.base.config import create_config, StrOption, IntOption
from functools import partial
from saturnin.base import (VENDOR_UID, Error, AgentDescriptor, ServiceDescriptor,
                           MIME_TYPE_TEXT)
from saturnin.lib.data.onepipe import DataProviderConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.firebird.log.fromsrv
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.2.0.3.4.1.1'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.2.1'

# Configuration

class FbLogFromSrvConfig(DataProviderConfig):
    """Firebird log from server provider microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        # Adjust default batch_size to compensate default 64K messages
        self.batch_size.default = 5
        #: Firebird server indetification (in driver configuration)
        self.server: StrOption = \
            StrOption('server', "Firebird server identification", required=True)
        #: Max. number of characters transmitted in one message
        self.max_chars: IntOption = \
            IntOption('max_chars', "Max. number of characters transmitted in one message",
                      required=True, default=65535)
    def validate(self) -> None:
        """Extended validation.

        - Only 'text/plain' MIME type is alowed for `pipe_format`.
        - Only 'charset' and 'errors' MIME parameters are alowed for `pipe_format`.
        """
        super().validate()
        # Pipe format
        if self.pipe_format.value.mime_type != MIME_TYPE_TEXT:
            raise Error("Only 'text/plain' pipe format supported")
        for param in self.pipe_format.value.params.keys():
            if param not in ('charset', 'errors'):
                raise Error(f"Unsupported MIME parameter '{param}' in pipe format")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name='saturnin.firebird.log.fromsrv',
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification='firebird-log/provider')

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Firebird log from server provider microservice",
                      facilities=['firebird'],
                      package='saturnin.core.fb_log_fromsrv',
                      factory='saturnin.core.fb_log_fromsrv.service:FbLogFromSrvMicro',
                      config=partial(create_config, FbLogFromSrvConfig,
                                     f'{SERVICE_AGENT.name}_service'))
