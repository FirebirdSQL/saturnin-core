#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           proto_filter/api.py
# DESCRIPTION:    API for protobuf filter microservice
# CREATED:        20.1.2020
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

"""Saturnin microservices - API for protobuf filter microservice

This microservice is a DATA_FILTER:

- INPUT: protobuf messages
- PROCESSING: uses expressions / functions evaluating data from protobuf message to filter
  data for output
- OUTPUT: protobuf messages
"""

from __future__ import annotations
import uuid
from functools import partial
from firebird.base.config import create_config, PyCallableOption, PyExprOption
from saturnin.base import VENDOR_UID, Error, MIME_TYPE_PROTO, \
     pkg_name, AgentDescriptor, ServiceDescriptor
from saturnin.lib.data.filter import DataFilterConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.proto.filter
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.2.0.3.3.2'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.2.0'

# Configuration

class ProtoFilterConfig(DataFilterConfig):
    """Data filter microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.input_pipe_format.required = True
        self.output_pipe_format.required = True
        #: Inclusion filter by Python expression
        self.include_expr: PyExprOption = \
            PyExprOption('include_expr', "Data inclusion Python expression")
        #: Inclusion filter by Python function
        self.include_func: PyCallableOption = \
            PyCallableOption('include_func', "Data inclusion Python function",
                             'def f(data: Any) -> bool:\n  ...\n')
        #: Exclusion filter by Python expression
        self.exclude_expr: PyExprOption = \
            PyExprOption('exclude_expr', "Data exclusion Python expression")
        #: Exclusion filter by Python function
        self.exclude_func: PyCallableOption = \
            PyCallableOption('exclude_func', "Data exclusion Python function",
                             'def f(data: Any) -> bool:\n  ...\n')
    def validate(self) -> None:
        """Extended validation.

        - Input/output format is required and must be MIME_TYPE_PROTO
        - Input and output MIME 'type' params are present and the same
        - At least one from '*_func' / '*_expr' options have a value
        - Only one from include / exclude methods is defined
        - '*_func' option value could be compiled
        """
        super().validate()
        #
        for fmt in [self.output_pipe_format, self.input_pipe_format]:
            if fmt.value is not None:
                if fmt.value.mime_type != MIME_TYPE_PROTO:
                    raise Error(f"Only '{MIME_TYPE_PROTO}' format allowed for '{fmt.name}' option.")
                if not fmt.value.params.get('type'):
                    raise Error(f"The 'type' parameter not found in '{fmt.name}' option.")
        #
        if self.input_pipe_format.value is not None \
           and self.output_pipe_format.value is not None \
           and self.output_pipe_format.value.params.get('type') != self.input_pipe_format.value.params.get('type'):
                raise Error(f"The 'type' parameter value must be the same for both MIME format options.")
        #
        defined = 0
        for opt in [self.include_func, self.exclude_func, self.include_expr, self.exclude_expr]:
            if opt.value is not None:
                defined += 1
        if defined == 0:
            raise Error("At least one filter specification option must have a value")
        #
        for func, expr in [(self.include_func, self.include_expr),
                           (self.exclude_func, self.exclude_expr)]:
            if expr.value and func.value:
                raise Error(f"Options '{expr.name}' and '{func.name}' are mutually exclusive")
        #
        for func in [self.include_func, self.exclude_func]:
            try:
                func.value
            except Exception as exc:
                raise Error(f"Invalid code definition in '{func.name}' option") from exc


# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.proto.filter",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="proto/filter")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Protobuf data filter microservice",
                      facilities=[],
                      package=pkg_name(__name__),
                      factory=f'{pkg_name(__name__)}.service:ProtoFilterMicro',
                      config=partial(create_config, ProtoFilterConfig,
                                     f'{SERVICE_AGENT.name}_service'))
