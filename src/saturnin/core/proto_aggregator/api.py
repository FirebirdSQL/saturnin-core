#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           prot_aggregator/api.py
# DESCRIPTION:    API for protobuf aggregator microservice
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

"""Saturnin microservices - API for protobuf aggregator microservice

This microservice is a DATA_FILTER:

- INPUT: protobuf messages
- PROCESSING: uses expressions / functions evaluating data from protobuf message to aggregate data for output
- OUTPUT: protobuf messages
"""

from __future__ import annotations
import uuid
from functools import partial
from firebird.base.config import ListOption
from saturnin.base import (VENDOR_UID, Error, MIME, MIME_TYPE_PROTO, AgentDescriptor,
                           ServiceDescriptor, create_config)
from saturnin.lib.data.filter import DataFilterConfig

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.proto.aggregator
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.1.0.3.3.3'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.2.1'

AGGREGATE_PROTO =  'saturnin.core.protobuf.GenericDataRecord'
AGGREGATE_FORMAT = MIME(f'{MIME_TYPE_PROTO};type={AGGREGATE_PROTO}')

AGGREGATE_FUNCTIONS = ['count', 'min', 'max', 'sum', 'avg']

# Configuration

class ProtoAggregatorConfig(DataFilterConfig):
    """Data aggregator microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        #: Specification of fields that are 'group by' key
        self.group_by: ListOption = \
            ListOption('group_by', str, "Specification of fields that are 'group by' key",
                       required=True)
        #: Specification for aggregates
        self.aggregate: ListOption = \
            ListOption('aggregate', str, "Specification for aggregates", required=True)
        #
        self.input_pipe_format.required = True
        self.output_pipe_format.required = True
        self.output_pipe_format.default = AGGREGATE_FORMAT
        self.output_pipe_format.set_value(AGGREGATE_FORMAT)
    def validate(self) -> None:
        """Extended validation.

        - that 'input_format' MIME type is 'application/x.fb.proto'
        - that 'output_format' MIME type is 'application/x.fb.proto;type=saturnin.core.protobuf.common.GenDataRecord'
        - that 'aggregate' values have format '<aggregate_func>:<field_spec>', and
          <aggregate_func> is from supported functions
        """
        super().validate()
        #
        if self.input_pipe_format.value.mime_type != MIME_TYPE_PROTO:
            raise Error(f"Only '{MIME_TYPE_PROTO}' input format allowed.")
        if self.output_pipe_format.value != AGGREGATE_FORMAT:
            raise Error(f"Only '{AGGREGATE_FORMAT}' output format allowed.")
        #
        for spec in self.aggregate.value:
            l = spec.split(':')
            if len(l) != 2:
                raise Error("The 'aggregate' values must have '<aggregate_func>:<field_spec>' format")
            func_name = l[0].lower()
            if ' as ' in func_name:
                func_name, _ = func_name.split(' as ')
            if func_name not in AGGREGATE_FUNCTIONS:
                raise Error(f"Unknown aggregate function '{func_name}'")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.proto.aggregator",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="proto/aggregator")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Protobuf data aggregator microservice",
                      facilities=[],
                      factory='saturnin.core.proto_aggregator.service:ProtoAggregatorMicro',
                      config=partial(create_config, ProtoAggregatorConfig, SERVICE_UID,
                                     f'{SERVICE_AGENT.name}_service'))
