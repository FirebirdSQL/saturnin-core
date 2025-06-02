from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from saturnin.core.protobuf import common_pb2 as _common_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FirebirdFacility(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FACILITY_UNKNOWN: _ClassVar[FirebirdFacility]
    FACILITY_SYSTEM: _ClassVar[FirebirdFacility]
    FACILITY_CONFIG: _ClassVar[FirebirdFacility]
    FACILITY_INTL: _ClassVar[FirebirdFacility]
    FACILITY_FILEIO: _ClassVar[FirebirdFacility]
    FACILITY_USER: _ClassVar[FirebirdFacility]
    FACILITY_VALIDATION: _ClassVar[FirebirdFacility]
    FACILITY_SWEEP: _ClassVar[FirebirdFacility]
    FACILITY_PLUGIN: _ClassVar[FirebirdFacility]
    FACILITY_GUARDIAN: _ClassVar[FirebirdFacility]
    FACILITY_NET: _ClassVar[FirebirdFacility]
    FACILITY_AUTH: _ClassVar[FirebirdFacility]
FACILITY_UNKNOWN: FirebirdFacility
FACILITY_SYSTEM: FirebirdFacility
FACILITY_CONFIG: FirebirdFacility
FACILITY_INTL: FirebirdFacility
FACILITY_FILEIO: FirebirdFacility
FACILITY_USER: FirebirdFacility
FACILITY_VALIDATION: FirebirdFacility
FACILITY_SWEEP: FirebirdFacility
FACILITY_PLUGIN: FirebirdFacility
FACILITY_GUARDIAN: FirebirdFacility
FACILITY_NET: FirebirdFacility
FACILITY_AUTH: FirebirdFacility

class LogEntry(_message.Message):
    __slots__ = ("origin", "timestamp", "level", "code", "facility", "message", "params")
    ORIGIN_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    FACILITY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    origin: str
    timestamp: _timestamp_pb2.Timestamp
    level: _common_pb2.SeverityLevel
    code: int
    facility: FirebirdFacility
    message: str
    params: _struct_pb2.Struct
    def __init__(self, origin: _Optional[str] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., level: _Optional[_Union[_common_pb2.SeverityLevel, str]] = ..., code: _Optional[int] = ..., facility: _Optional[_Union[FirebirdFacility, str]] = ..., message: _Optional[str] = ..., params: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...
