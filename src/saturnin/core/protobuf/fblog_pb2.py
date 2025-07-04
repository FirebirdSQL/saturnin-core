# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: saturnin/core/protobuf/fblog.proto
# Protobuf Python Version: 4.25.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import timestamp_pb2 as google_dot_protobuf_dot_timestamp__pb2
from google.protobuf import struct_pb2 as google_dot_protobuf_dot_struct__pb2
from saturnin.core.protobuf import common_pb2 as saturnin_dot_core_dot_protobuf_dot_common__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\"saturnin/core/protobuf/fblog.proto\x12\x1csaturnin.core.protobuf.fblog\x1a\x1fgoogle/protobuf/timestamp.proto\x1a\x1cgoogle/protobuf/struct.proto\x1a#saturnin/core/protobuf/common.proto\"\x89\x02\n\x08LogEntry\x12\x0e\n\x06origin\x18\x01 \x01(\t\x12-\n\ttimestamp\x18\x02 \x01(\x0b\x32\x1a.google.protobuf.Timestamp\x12\x34\n\x05level\x18\x03 \x01(\x0e\x32%.saturnin.core.protobuf.SeverityLevel\x12\x0c\n\x04\x63ode\x18\x04 \x01(\r\x12@\n\x08\x66\x61\x63ility\x18\x05 \x01(\x0e\x32..saturnin.core.protobuf.fblog.FirebirdFacility\x12\x0f\n\x07message\x18\x06 \x01(\t\x12\'\n\x06params\x18\x07 \x01(\x0b\x32\x17.google.protobuf.Struct*\x8b\x02\n\x10\x46irebirdFacility\x12\x14\n\x10\x46\x41\x43ILITY_UNKNOWN\x10\x00\x12\x13\n\x0f\x46\x41\x43ILITY_SYSTEM\x10\x01\x12\x13\n\x0f\x46\x41\x43ILITY_CONFIG\x10\x02\x12\x11\n\rFACILITY_INTL\x10\x03\x12\x13\n\x0f\x46\x41\x43ILITY_FILEIO\x10\x04\x12\x11\n\rFACILITY_USER\x10\x05\x12\x17\n\x13\x46\x41\x43ILITY_VALIDATION\x10\x06\x12\x12\n\x0e\x46\x41\x43ILITY_SWEEP\x10\x07\x12\x13\n\x0f\x46\x41\x43ILITY_PLUGIN\x10\x08\x12\x15\n\x11\x46\x41\x43ILITY_GUARDIAN\x10\t\x12\x10\n\x0c\x46\x41\x43ILITY_NET\x10\n\x12\x11\n\rFACILITY_AUTH\x10\x0b\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'saturnin.core.protobuf.fblog_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_FIREBIRDFACILITY']._serialized_start=437
  _globals['_FIREBIRDFACILITY']._serialized_end=704
  _globals['_LOGENTRY']._serialized_start=169
  _globals['_LOGENTRY']._serialized_end=434
# @@protoc_insertion_point(module_scope)
