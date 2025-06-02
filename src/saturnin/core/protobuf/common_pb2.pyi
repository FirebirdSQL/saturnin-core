from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ServiceTypeEnum(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SVC_TYPE_UNKNOWN: _ClassVar[ServiceTypeEnum]
    SVC_TYPE_DATA_PROVIDER: _ClassVar[ServiceTypeEnum]
    SVC_TYPE_DATA_FILTER: _ClassVar[ServiceTypeEnum]
    SVC_TYPE_DATA_CONSUMER: _ClassVar[ServiceTypeEnum]
    SVC_TYPE_PROCESSING: _ClassVar[ServiceTypeEnum]
    SVC_TYPE_EXECUTOR: _ClassVar[ServiceTypeEnum]
    SVC_TYPE_CONTROL: _ClassVar[ServiceTypeEnum]
    SVC_TYPE_OTHER: _ClassVar[ServiceTypeEnum]

class SeverityLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SEVERITY_UNKNOWN: _ClassVar[SeverityLevel]
    SEVERITY_INFO: _ClassVar[SeverityLevel]
    SEVERITY_WARNING: _ClassVar[SeverityLevel]
    SEVERITY_ERROR: _ClassVar[SeverityLevel]
    SEVERITY_CRITICAL: _ClassVar[SeverityLevel]
SVC_TYPE_UNKNOWN: ServiceTypeEnum
SVC_TYPE_DATA_PROVIDER: ServiceTypeEnum
SVC_TYPE_DATA_FILTER: ServiceTypeEnum
SVC_TYPE_DATA_CONSUMER: ServiceTypeEnum
SVC_TYPE_PROCESSING: ServiceTypeEnum
SVC_TYPE_EXECUTOR: ServiceTypeEnum
SVC_TYPE_CONTROL: ServiceTypeEnum
SVC_TYPE_OTHER: ServiceTypeEnum
SEVERITY_UNKNOWN: SeverityLevel
SEVERITY_INFO: SeverityLevel
SEVERITY_WARNING: SeverityLevel
SEVERITY_ERROR: SeverityLevel
SEVERITY_CRITICAL: SeverityLevel

class GenericDataRecord(_message.Message):
    __slots__ = ("sequence", "data")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    data: _struct_pb2.Struct
    def __init__(self, sequence: _Optional[int] = ..., data: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class GenericDataPackage(_message.Message):
    __slots__ = ("records",)
    RECORDS_FIELD_NUMBER: _ClassVar[int]
    records: _containers.RepeatedCompositeFieldContainer[GenericDataRecord]
    def __init__(self, records: _Optional[_Iterable[_Union[GenericDataRecord, _Mapping]]] = ...) -> None: ...
