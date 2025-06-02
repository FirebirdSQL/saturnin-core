from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STATUS_UNKNOWN: _ClassVar[Status]
    STATUS_OK: _ClassVar[Status]
    STATUS_FAILED: _ClassVar[Status]
    STATUS_UNAUTHORIZED: _ClassVar[Status]
STATUS_UNKNOWN: Status
STATUS_OK: Status
STATUS_FAILED: Status
STATUS_UNAUTHORIZED: Status

class AttachmentInfo(_message.Message):
    __slots__ = ("id", "database", "charset", "protocol", "address", "user", "role", "remote_process", "remote_pid")
    ID_FIELD_NUMBER: _ClassVar[int]
    DATABASE_FIELD_NUMBER: _ClassVar[int]
    CHARSET_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PROCESS_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PID_FIELD_NUMBER: _ClassVar[int]
    id: int
    database: str
    charset: str
    protocol: str
    address: str
    user: str
    role: str
    remote_process: str
    remote_pid: int
    def __init__(self, id: _Optional[int] = ..., database: _Optional[str] = ..., charset: _Optional[str] = ..., protocol: _Optional[str] = ..., address: _Optional[str] = ..., user: _Optional[str] = ..., role: _Optional[str] = ..., remote_process: _Optional[str] = ..., remote_pid: _Optional[int] = ...) -> None: ...

class TransactionInfo(_message.Message):
    __slots__ = ("id", "att_id", "options")
    ID_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    id: int
    att_id: int
    options: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, id: _Optional[int] = ..., att_id: _Optional[int] = ..., options: _Optional[_Iterable[str]] = ...) -> None: ...

class ServiceInfo(_message.Message):
    __slots__ = ("id", "user", "protocol", "address", "remote_process", "remote_pid")
    ID_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PROCESS_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PID_FIELD_NUMBER: _ClassVar[int]
    id: int
    user: str
    protocol: str
    address: str
    remote_process: str
    remote_pid: int
    def __init__(self, id: _Optional[int] = ..., user: _Optional[str] = ..., protocol: _Optional[str] = ..., address: _Optional[str] = ..., remote_process: _Optional[str] = ..., remote_pid: _Optional[int] = ...) -> None: ...

class SQLInfo(_message.Message):
    __slots__ = ("id", "sql", "plan")
    ID_FIELD_NUMBER: _ClassVar[int]
    SQL_FIELD_NUMBER: _ClassVar[int]
    PLAN_FIELD_NUMBER: _ClassVar[int]
    id: int
    sql: str
    plan: str
    def __init__(self, id: _Optional[int] = ..., sql: _Optional[str] = ..., plan: _Optional[str] = ...) -> None: ...

class Param(_message.Message):
    __slots__ = ("type", "value")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    type: str
    value: str
    def __init__(self, type: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class ParamSet(_message.Message):
    __slots__ = ("id", "param")
    ID_FIELD_NUMBER: _ClassVar[int]
    PARAM_FIELD_NUMBER: _ClassVar[int]
    id: int
    param: _containers.RepeatedCompositeFieldContainer[Param]
    def __init__(self, id: _Optional[int] = ..., param: _Optional[_Iterable[_Union[Param, _Mapping]]] = ...) -> None: ...

class AccessStats(_message.Message):
    __slots__ = ("table", "natural", "index", "update", "insert", "delete", "backout", "purge", "expunge")
    TABLE_FIELD_NUMBER: _ClassVar[int]
    NATURAL_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FIELD_NUMBER: _ClassVar[int]
    INSERT_FIELD_NUMBER: _ClassVar[int]
    DELETE_FIELD_NUMBER: _ClassVar[int]
    BACKOUT_FIELD_NUMBER: _ClassVar[int]
    PURGE_FIELD_NUMBER: _ClassVar[int]
    EXPUNGE_FIELD_NUMBER: _ClassVar[int]
    table: str
    natural: int
    index: int
    update: int
    insert: int
    delete: int
    backout: int
    purge: int
    expunge: int
    def __init__(self, table: _Optional[str] = ..., natural: _Optional[int] = ..., index: _Optional[int] = ..., update: _Optional[int] = ..., insert: _Optional[int] = ..., delete: _Optional[int] = ..., backout: _Optional[int] = ..., purge: _Optional[int] = ..., expunge: _Optional[int] = ...) -> None: ...

class TraceEvent(_message.Message):
    __slots__ = ("id", "timestamp")
    ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    id: int
    timestamp: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[int] = ..., timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class EventTraceInit(_message.Message):
    __slots__ = ("event", "session")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    session: str
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., session: _Optional[str] = ...) -> None: ...

class EventTraceSuspend(_message.Message):
    __slots__ = ("event", "session")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    session: str
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., session: _Optional[str] = ...) -> None: ...

class EventTraceFinish(_message.Message):
    __slots__ = ("event", "session")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    session: str
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., session: _Optional[str] = ...) -> None: ...

class EventCreate(_message.Message):
    __slots__ = ("event", "status", "att_id", "database", "charset", "protocol", "address", "user", "role", "remote_process", "remote_pid")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    DATABASE_FIELD_NUMBER: _ClassVar[int]
    CHARSET_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PROCESS_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    database: str
    charset: str
    protocol: str
    address: str
    user: str
    role: str
    remote_process: str
    remote_pid: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., database: _Optional[str] = ..., charset: _Optional[str] = ..., protocol: _Optional[str] = ..., address: _Optional[str] = ..., user: _Optional[str] = ..., role: _Optional[str] = ..., remote_process: _Optional[str] = ..., remote_pid: _Optional[int] = ...) -> None: ...

class EventDrop(_message.Message):
    __slots__ = ("event", "status", "att_id", "database", "charset", "protocol", "address", "user", "role", "remote_process", "remote_pid")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    DATABASE_FIELD_NUMBER: _ClassVar[int]
    CHARSET_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PROCESS_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    database: str
    charset: str
    protocol: str
    address: str
    user: str
    role: str
    remote_process: str
    remote_pid: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., database: _Optional[str] = ..., charset: _Optional[str] = ..., protocol: _Optional[str] = ..., address: _Optional[str] = ..., user: _Optional[str] = ..., role: _Optional[str] = ..., remote_process: _Optional[str] = ..., remote_pid: _Optional[int] = ...) -> None: ...

class EventAttach(_message.Message):
    __slots__ = ("event", "status", "att_id", "database", "charset", "protocol", "address", "user", "role", "remote_process", "remote_pid")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    DATABASE_FIELD_NUMBER: _ClassVar[int]
    CHARSET_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PROCESS_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    database: str
    charset: str
    protocol: str
    address: str
    user: str
    role: str
    remote_process: str
    remote_pid: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., database: _Optional[str] = ..., charset: _Optional[str] = ..., protocol: _Optional[str] = ..., address: _Optional[str] = ..., user: _Optional[str] = ..., role: _Optional[str] = ..., remote_process: _Optional[str] = ..., remote_pid: _Optional[int] = ...) -> None: ...

class EventDetach(_message.Message):
    __slots__ = ("event", "status", "att_id", "database", "charset", "protocol", "address", "user", "role", "remote_process", "remote_pid")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    DATABASE_FIELD_NUMBER: _ClassVar[int]
    CHARSET_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PROCESS_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    database: str
    charset: str
    protocol: str
    address: str
    user: str
    role: str
    remote_process: str
    remote_pid: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., database: _Optional[str] = ..., charset: _Optional[str] = ..., protocol: _Optional[str] = ..., address: _Optional[str] = ..., user: _Optional[str] = ..., role: _Optional[str] = ..., remote_process: _Optional[str] = ..., remote_pid: _Optional[int] = ...) -> None: ...

class EventTransactionStart(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "options")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    options: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., options: _Optional[_Iterable[str]] = ...) -> None: ...

class EventCommit(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "options", "run_time", "reads", "writes", "fetches", "marks")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    options: _containers.RepeatedScalarFieldContainer[str]
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., options: _Optional[_Iterable[str]] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ...) -> None: ...

class EventRollback(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "options", "run_time", "reads", "writes", "fetches", "marks")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    options: _containers.RepeatedScalarFieldContainer[str]
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., options: _Optional[_Iterable[str]] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ...) -> None: ...

class EventCommitRetaining(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "options", "run_time", "reads", "writes", "fetches", "marks")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    options: _containers.RepeatedScalarFieldContainer[str]
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., options: _Optional[_Iterable[str]] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ...) -> None: ...

class EventRollbackRetaining(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "options", "run_time", "reads", "writes", "fetches", "marks")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    options: _containers.RepeatedScalarFieldContainer[str]
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., options: _Optional[_Iterable[str]] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ...) -> None: ...

class EventPrepareStatement(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "stm_id", "sql_id", "prepare")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    STM_ID_FIELD_NUMBER: _ClassVar[int]
    SQL_ID_FIELD_NUMBER: _ClassVar[int]
    PREPARE_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    stm_id: int
    sql_id: int
    prepare: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., stm_id: _Optional[int] = ..., sql_id: _Optional[int] = ..., prepare: _Optional[int] = ...) -> None: ...

class EventStatementStart(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "stm_id", "sql_id", "param_id")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    STM_ID_FIELD_NUMBER: _ClassVar[int]
    SQL_ID_FIELD_NUMBER: _ClassVar[int]
    PARAM_ID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    stm_id: int
    sql_id: int
    param_id: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., stm_id: _Optional[int] = ..., sql_id: _Optional[int] = ..., param_id: _Optional[int] = ...) -> None: ...

class EventStatementFinish(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "stm_id", "sql_id", "param_id", "records", "run_time", "reads", "writes", "fetches", "marks", "access")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    STM_ID_FIELD_NUMBER: _ClassVar[int]
    SQL_ID_FIELD_NUMBER: _ClassVar[int]
    PARAM_ID_FIELD_NUMBER: _ClassVar[int]
    RECORDS_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    stm_id: int
    sql_id: int
    param_id: int
    records: int
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    access: _containers.RepeatedCompositeFieldContainer[AccessStats]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., stm_id: _Optional[int] = ..., sql_id: _Optional[int] = ..., param_id: _Optional[int] = ..., records: _Optional[int] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ..., access: _Optional[_Iterable[_Union[AccessStats, _Mapping]]] = ...) -> None: ...

class EventFreeStatement(_message.Message):
    __slots__ = ("event", "att_id", "tra_id", "stm_id", "sql_id")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    STM_ID_FIELD_NUMBER: _ClassVar[int]
    SQL_ID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    att_id: int
    tra_id: int
    stm_id: int
    sql_id: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., stm_id: _Optional[int] = ..., sql_id: _Optional[int] = ...) -> None: ...

class EventCloseCursor(_message.Message):
    __slots__ = ("event", "att_id", "tra_id", "stm_id", "sql_id")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    STM_ID_FIELD_NUMBER: _ClassVar[int]
    SQL_ID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    att_id: int
    tra_id: int
    stm_id: int
    sql_id: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., stm_id: _Optional[int] = ..., sql_id: _Optional[int] = ...) -> None: ...

class EventTriggerStart(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "trigger", "table", "t_event")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    TABLE_FIELD_NUMBER: _ClassVar[int]
    T_EVENT_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    trigger: str
    table: str
    t_event: str
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., trigger: _Optional[str] = ..., table: _Optional[str] = ..., t_event: _Optional[str] = ...) -> None: ...

class EventTriggerFinish(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "trigger", "table", "t_event", "run_time", "reads", "writes", "fetches", "marks", "access")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    TABLE_FIELD_NUMBER: _ClassVar[int]
    T_EVENT_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    trigger: str
    table: str
    t_event: str
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    access: _containers.RepeatedCompositeFieldContainer[AccessStats]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., trigger: _Optional[str] = ..., table: _Optional[str] = ..., t_event: _Optional[str] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ..., access: _Optional[_Iterable[_Union[AccessStats, _Mapping]]] = ...) -> None: ...

class EventProcedureStart(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "procedure", "param_id")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    PROCEDURE_FIELD_NUMBER: _ClassVar[int]
    PARAM_ID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    procedure: str
    param_id: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., procedure: _Optional[str] = ..., param_id: _Optional[int] = ...) -> None: ...

class EventProcedureFinish(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "procedure", "param_id", "run_time", "reads", "writes", "fetches", "marks", "access")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    PROCEDURE_FIELD_NUMBER: _ClassVar[int]
    PARAM_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    procedure: str
    param_id: int
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    access: _containers.RepeatedCompositeFieldContainer[AccessStats]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., procedure: _Optional[str] = ..., param_id: _Optional[int] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ..., access: _Optional[_Iterable[_Union[AccessStats, _Mapping]]] = ...) -> None: ...

class EventServiceAttach(_message.Message):
    __slots__ = ("event", "status", "svc_id")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SVC_ID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    svc_id: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., svc_id: _Optional[int] = ...) -> None: ...

class EventServiceDetach(_message.Message):
    __slots__ = ("event", "status", "svc_id")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SVC_ID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    svc_id: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., svc_id: _Optional[int] = ...) -> None: ...

class EventServiceStart(_message.Message):
    __slots__ = ("event", "status", "svc_id", "action", "params")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SVC_ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    svc_id: int
    action: str
    params: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., svc_id: _Optional[int] = ..., action: _Optional[str] = ..., params: _Optional[_Iterable[str]] = ...) -> None: ...

class EventServiceQuery(_message.Message):
    __slots__ = ("event", "status", "svc_id", "action", "params")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SVC_ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    svc_id: int
    action: str
    params: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., svc_id: _Optional[int] = ..., action: _Optional[str] = ..., params: _Optional[_Iterable[str]] = ...) -> None: ...

class EventSetContext(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "context", "key", "value")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    context: str
    key: str
    value: str
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., context: _Optional[str] = ..., key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class EventError(_message.Message):
    __slots__ = ("event", "att_id", "place", "details")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    PLACE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    att_id: int
    place: str
    details: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., att_id: _Optional[int] = ..., place: _Optional[str] = ..., details: _Optional[_Iterable[str]] = ...) -> None: ...

class EventWarning(_message.Message):
    __slots__ = ("event", "att_id", "place", "details")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    PLACE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    att_id: int
    place: str
    details: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., att_id: _Optional[int] = ..., place: _Optional[str] = ..., details: _Optional[_Iterable[str]] = ...) -> None: ...

class EventServiceError(_message.Message):
    __slots__ = ("event", "svc_id", "place", "details")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    SVC_ID_FIELD_NUMBER: _ClassVar[int]
    PLACE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    svc_id: int
    place: str
    details: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., svc_id: _Optional[int] = ..., place: _Optional[str] = ..., details: _Optional[_Iterable[str]] = ...) -> None: ...

class EventServiceWarning(_message.Message):
    __slots__ = ("event", "svc_id", "place", "details")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    SVC_ID_FIELD_NUMBER: _ClassVar[int]
    PLACE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    svc_id: int
    place: str
    details: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., svc_id: _Optional[int] = ..., place: _Optional[str] = ..., details: _Optional[_Iterable[str]] = ...) -> None: ...

class EventSweepStart(_message.Message):
    __slots__ = ("event", "att_id", "oit", "oat", "ost", "next")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    OIT_FIELD_NUMBER: _ClassVar[int]
    OAT_FIELD_NUMBER: _ClassVar[int]
    OST_FIELD_NUMBER: _ClassVar[int]
    NEXT_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    att_id: int
    oit: int
    oat: int
    ost: int
    next: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., att_id: _Optional[int] = ..., oit: _Optional[int] = ..., oat: _Optional[int] = ..., ost: _Optional[int] = ..., next: _Optional[int] = ...) -> None: ...

class EventSweepProgress(_message.Message):
    __slots__ = ("event", "att_id", "run_time", "reads", "writes", "fetches", "marks", "access")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    att_id: int
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    access: _containers.RepeatedCompositeFieldContainer[AccessStats]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., att_id: _Optional[int] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ..., access: _Optional[_Iterable[_Union[AccessStats, _Mapping]]] = ...) -> None: ...

class EventSweepFinish(_message.Message):
    __slots__ = ("event", "att_id", "oit", "oat", "ost", "next", "run_time", "reads", "writes", "fetches", "marks")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    OIT_FIELD_NUMBER: _ClassVar[int]
    OAT_FIELD_NUMBER: _ClassVar[int]
    OST_FIELD_NUMBER: _ClassVar[int]
    NEXT_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    att_id: int
    oit: int
    oat: int
    ost: int
    next: int
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., att_id: _Optional[int] = ..., oit: _Optional[int] = ..., oat: _Optional[int] = ..., ost: _Optional[int] = ..., next: _Optional[int] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ...) -> None: ...

class EventSweepFailed(_message.Message):
    __slots__ = ("event", "att_id")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    att_id: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., att_id: _Optional[int] = ...) -> None: ...

class EventBLRCompile(_message.Message):
    __slots__ = ("event", "status", "att_id", "stm_id", "content", "prepare")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    STM_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    PREPARE_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    stm_id: int
    content: str
    prepare: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., stm_id: _Optional[int] = ..., content: _Optional[str] = ..., prepare: _Optional[int] = ...) -> None: ...

class EventBLRExecute(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "stm_id", "content", "run_time", "reads", "writes", "fetches", "marks", "access")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    STM_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    FETCHES_FIELD_NUMBER: _ClassVar[int]
    MARKS_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    stm_id: int
    content: str
    run_time: int
    reads: int
    writes: int
    fetches: int
    marks: int
    access: _containers.RepeatedCompositeFieldContainer[AccessStats]
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., stm_id: _Optional[int] = ..., content: _Optional[str] = ..., run_time: _Optional[int] = ..., reads: _Optional[int] = ..., writes: _Optional[int] = ..., fetches: _Optional[int] = ..., marks: _Optional[int] = ..., access: _Optional[_Iterable[_Union[AccessStats, _Mapping]]] = ...) -> None: ...

class EventDYNExecute(_message.Message):
    __slots__ = ("event", "status", "att_id", "tra_id", "content", "run_time")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ATT_ID_FIELD_NUMBER: _ClassVar[int]
    TRA_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    RUN_TIME_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    status: Status
    att_id: int
    tra_id: int
    content: str
    run_time: int
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., status: _Optional[_Union[Status, str]] = ..., att_id: _Optional[int] = ..., tra_id: _Optional[int] = ..., content: _Optional[str] = ..., run_time: _Optional[int] = ...) -> None: ...

class EventUnknown(_message.Message):
    __slots__ = ("event", "data")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    event: TraceEvent
    data: str
    def __init__(self, event: _Optional[_Union[TraceEvent, _Mapping]] = ..., data: _Optional[str] = ...) -> None: ...

class TraceEntry(_message.Message):
    __slots__ = ("att_info", "tra_info", "svc_info", "sql_info", "params", "trace_init", "trace_suspend", "trace_finish", "db_create", "db_drop", "db_attach", "db_detach", "tra_start", "tra_commit", "tra_rollback", "tra_commit_retain", "tra_rollback_retain", "stm_prepare", "stm_start", "stm_finish", "stm_free", "cursor_close", "trigger_start", "trigger_finish", "proc_start", "proc_finish", "svc_attach", "svc_detach", "svc_start", "svc_query", "ctx_set", "error", "warning", "svc_error", "svc_warning", "swp_start", "swp_progress", "swp_finish", "swp_fail", "blr_compile", "blr_exec", "dyn_exec", "unknown")
    ATT_INFO_FIELD_NUMBER: _ClassVar[int]
    TRA_INFO_FIELD_NUMBER: _ClassVar[int]
    SVC_INFO_FIELD_NUMBER: _ClassVar[int]
    SQL_INFO_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    TRACE_INIT_FIELD_NUMBER: _ClassVar[int]
    TRACE_SUSPEND_FIELD_NUMBER: _ClassVar[int]
    TRACE_FINISH_FIELD_NUMBER: _ClassVar[int]
    DB_CREATE_FIELD_NUMBER: _ClassVar[int]
    DB_DROP_FIELD_NUMBER: _ClassVar[int]
    DB_ATTACH_FIELD_NUMBER: _ClassVar[int]
    DB_DETACH_FIELD_NUMBER: _ClassVar[int]
    TRA_START_FIELD_NUMBER: _ClassVar[int]
    TRA_COMMIT_FIELD_NUMBER: _ClassVar[int]
    TRA_ROLLBACK_FIELD_NUMBER: _ClassVar[int]
    TRA_COMMIT_RETAIN_FIELD_NUMBER: _ClassVar[int]
    TRA_ROLLBACK_RETAIN_FIELD_NUMBER: _ClassVar[int]
    STM_PREPARE_FIELD_NUMBER: _ClassVar[int]
    STM_START_FIELD_NUMBER: _ClassVar[int]
    STM_FINISH_FIELD_NUMBER: _ClassVar[int]
    STM_FREE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_CLOSE_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_START_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FINISH_FIELD_NUMBER: _ClassVar[int]
    PROC_START_FIELD_NUMBER: _ClassVar[int]
    PROC_FINISH_FIELD_NUMBER: _ClassVar[int]
    SVC_ATTACH_FIELD_NUMBER: _ClassVar[int]
    SVC_DETACH_FIELD_NUMBER: _ClassVar[int]
    SVC_START_FIELD_NUMBER: _ClassVar[int]
    SVC_QUERY_FIELD_NUMBER: _ClassVar[int]
    CTX_SET_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    WARNING_FIELD_NUMBER: _ClassVar[int]
    SVC_ERROR_FIELD_NUMBER: _ClassVar[int]
    SVC_WARNING_FIELD_NUMBER: _ClassVar[int]
    SWP_START_FIELD_NUMBER: _ClassVar[int]
    SWP_PROGRESS_FIELD_NUMBER: _ClassVar[int]
    SWP_FINISH_FIELD_NUMBER: _ClassVar[int]
    SWP_FAIL_FIELD_NUMBER: _ClassVar[int]
    BLR_COMPILE_FIELD_NUMBER: _ClassVar[int]
    BLR_EXEC_FIELD_NUMBER: _ClassVar[int]
    DYN_EXEC_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_FIELD_NUMBER: _ClassVar[int]
    att_info: AttachmentInfo
    tra_info: TransactionInfo
    svc_info: ServiceInfo
    sql_info: SQLInfo
    params: ParamSet
    trace_init: EventTraceInit
    trace_suspend: EventTraceSuspend
    trace_finish: EventTraceFinish
    db_create: EventCreate
    db_drop: EventDrop
    db_attach: EventAttach
    db_detach: EventDetach
    tra_start: EventTransactionStart
    tra_commit: EventCommit
    tra_rollback: EventRollback
    tra_commit_retain: EventCommitRetaining
    tra_rollback_retain: EventRollbackRetaining
    stm_prepare: EventPrepareStatement
    stm_start: EventStatementStart
    stm_finish: EventStatementFinish
    stm_free: EventFreeStatement
    cursor_close: EventCloseCursor
    trigger_start: EventTriggerStart
    trigger_finish: EventTriggerFinish
    proc_start: EventProcedureStart
    proc_finish: EventProcedureFinish
    svc_attach: EventServiceAttach
    svc_detach: EventServiceDetach
    svc_start: EventServiceStart
    svc_query: EventServiceQuery
    ctx_set: EventSetContext
    error: EventError
    warning: EventWarning
    svc_error: EventServiceError
    svc_warning: EventServiceWarning
    swp_start: EventSweepStart
    swp_progress: EventSweepProgress
    swp_finish: EventSweepFinish
    swp_fail: EventSweepFailed
    blr_compile: EventBLRCompile
    blr_exec: EventBLRExecute
    dyn_exec: EventDYNExecute
    unknown: EventUnknown
    def __init__(self, att_info: _Optional[_Union[AttachmentInfo, _Mapping]] = ..., tra_info: _Optional[_Union[TransactionInfo, _Mapping]] = ..., svc_info: _Optional[_Union[ServiceInfo, _Mapping]] = ..., sql_info: _Optional[_Union[SQLInfo, _Mapping]] = ..., params: _Optional[_Union[ParamSet, _Mapping]] = ..., trace_init: _Optional[_Union[EventTraceInit, _Mapping]] = ..., trace_suspend: _Optional[_Union[EventTraceSuspend, _Mapping]] = ..., trace_finish: _Optional[_Union[EventTraceFinish, _Mapping]] = ..., db_create: _Optional[_Union[EventCreate, _Mapping]] = ..., db_drop: _Optional[_Union[EventDrop, _Mapping]] = ..., db_attach: _Optional[_Union[EventAttach, _Mapping]] = ..., db_detach: _Optional[_Union[EventDetach, _Mapping]] = ..., tra_start: _Optional[_Union[EventTransactionStart, _Mapping]] = ..., tra_commit: _Optional[_Union[EventCommit, _Mapping]] = ..., tra_rollback: _Optional[_Union[EventRollback, _Mapping]] = ..., tra_commit_retain: _Optional[_Union[EventCommitRetaining, _Mapping]] = ..., tra_rollback_retain: _Optional[_Union[EventRollbackRetaining, _Mapping]] = ..., stm_prepare: _Optional[_Union[EventPrepareStatement, _Mapping]] = ..., stm_start: _Optional[_Union[EventStatementStart, _Mapping]] = ..., stm_finish: _Optional[_Union[EventStatementFinish, _Mapping]] = ..., stm_free: _Optional[_Union[EventFreeStatement, _Mapping]] = ..., cursor_close: _Optional[_Union[EventCloseCursor, _Mapping]] = ..., trigger_start: _Optional[_Union[EventTriggerStart, _Mapping]] = ..., trigger_finish: _Optional[_Union[EventTriggerFinish, _Mapping]] = ..., proc_start: _Optional[_Union[EventProcedureStart, _Mapping]] = ..., proc_finish: _Optional[_Union[EventProcedureFinish, _Mapping]] = ..., svc_attach: _Optional[_Union[EventServiceAttach, _Mapping]] = ..., svc_detach: _Optional[_Union[EventServiceDetach, _Mapping]] = ..., svc_start: _Optional[_Union[EventServiceStart, _Mapping]] = ..., svc_query: _Optional[_Union[EventServiceQuery, _Mapping]] = ..., ctx_set: _Optional[_Union[EventSetContext, _Mapping]] = ..., error: _Optional[_Union[EventError, _Mapping]] = ..., warning: _Optional[_Union[EventWarning, _Mapping]] = ..., svc_error: _Optional[_Union[EventServiceError, _Mapping]] = ..., svc_warning: _Optional[_Union[EventServiceWarning, _Mapping]] = ..., swp_start: _Optional[_Union[EventSweepStart, _Mapping]] = ..., swp_progress: _Optional[_Union[EventSweepProgress, _Mapping]] = ..., swp_finish: _Optional[_Union[EventSweepFinish, _Mapping]] = ..., swp_fail: _Optional[_Union[EventSweepFailed, _Mapping]] = ..., blr_compile: _Optional[_Union[EventBLRCompile, _Mapping]] = ..., blr_exec: _Optional[_Union[EventBLRExecute, _Mapping]] = ..., dyn_exec: _Optional[_Union[EventDYNExecute, _Mapping]] = ..., unknown: _Optional[_Union[EventUnknown, _Mapping]] = ...) -> None: ...
