# SPDX-FileCopyrightText: 2021-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           fb_trace_session/api.py
# DESCRIPTION:    API for Firebird trace session provider microservice
# CREATED:        06.01.2021
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

"""Saturnin microservices - API for Firebird trace session provider microservice

This microservice is a DATA_PROVIDER that runs trace session on Firebird server via
services and send trace output as blocks of text to output data pipe.
"""

from __future__ import annotations

import uuid
from functools import partial

from firebird.base.config import IntOption, StrOption
from saturnin.base import MIME_TYPE_TEXT, VENDOR_UID, AgentDescriptor, Error, ServiceDescriptor, create_config
from saturnin.lib.data.onepipe import DataProviderConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.firebird.trace.session
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.1.0.3.4.2.1'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.1.1'

# Configuration

class FbTraceSessionConfig(DataProviderConfig):
    """Firebird trace session provider microservice configuration.
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
        #: Trace session configuration
        self.trace: StrOption = \
            StrOption('trace', "Trace session configuration", required=True)
        #: Trace session name
        self.session_name: StrOption = \
            StrOption('session_name', "Trace session name")
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
                    name='saturnin.firebird.trace.session',
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification='firebird-trace/session')

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Firebird trace session provider microservice",
                      facilities=['firebird'],
                      factory='saturnin.core.fb_trace_session.service:FbTraceSessionMicro',
                      config=partial(create_config, FbTraceSessionConfig, SERVICE_UID,
                                     f'{SERVICE_AGENT.name}_service'))
