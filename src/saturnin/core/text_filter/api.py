#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           text_filter/api.py
# DESCRIPTION:    API for Text line filter microservice
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

"""Saturnin microservices - API for Text line filter microservice

This microservice is a DATA_FILTER that reads blocks of text from input data pipe, and
writes lines that meet the specified conditions as blocks of text into output data pipe.
"""

from __future__ import annotations
import uuid
import re
from functools import partial
from firebird.base.config import create_config, StrOption, IntOption, PyExprOption, \
     PyCallableOption
from saturnin.base import VENDOR_UID, Error, pkg_name, AgentDescriptor, \
     ServiceDescriptor, MIME_TYPE_TEXT
from saturnin.lib.data.filter import DataFilterConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.text.linefilter
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.2.0.3.1.3'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.2.1'

# Configuration

class TextFilterConfig(DataFilterConfig):
    """Text line filter microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        #: Max. number of characters transmitted in one message
        self.max_chars: IntOption = \
            IntOption('max_chars',
                      "Max. number of characters transmitted in one message",
                      required=True, default=65535)
        #: Filter by regular expression
        self.regex: StrOption = StrOption('regex', "Regular expression")
        #: Filter by Python expression
        self.expr: PyExprOption = PyExprOption('expr', "Python expression")
        #: Filter by Python function
        self.func: PyCallableOption = \
            PyCallableOption('func',
                             "Python function with signature: def fname(line: str) -> bool",
                             'def f(line: str) -> bool:\n  ...\n')
    def validate(self) -> None:
        """Extended validation.

        - Exactly one filter definition must be provided.
        - Only 'text/plain' MIME types are alowed for input and output `pipe_format`.
        - Only 'charset' and 'errors' MIME parameters are alowed for input and output
          `pipe_format`.
        - Regex is valid.
        """
        super().validate()
        # Pipe format
        for fmt in (self.input_pipe_format, self.output_pipe_format):
            if fmt.value.mime_type != MIME_TYPE_TEXT:
                raise Error(f"MIME type '{fmt.value.mime_type}' is not a valid input format")
            # MIME parameters
            for param in fmt.value.params.keys():
                if param not in ('charset', 'errors'):
                    raise Error(f"Unknown MIME parameter '{param}' in pipe format")
        # Filters
        defined = 0
        for opt in (self.regex, self.expr, self.func):
            if opt.value is not None:
                defined += 1
        if defined != 1:
            raise Error("Configuration must contain exactly one filter definition.")
        # regex
        if self.regex.value is not None:
            re.compile(self.regex.value)

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.text.linefilter",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="text/filter")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Text line filter microservice",
                      facilities=[],
                      package='saturnin.core.text_filter',
                      factory='saturnin.core.text_filter.service:TextLineFilterMicro',
                      config=partial(create_config, TextFilterConfig,
                                     f'{SERVICE_AGENT.name}_service'))
