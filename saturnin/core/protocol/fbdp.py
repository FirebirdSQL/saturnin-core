#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/fbdp.py
# DESCRIPTION:    Firebird Butler Data Pipe Protocol
#                 See https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
# CREATED:        30.7.2019
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

"""Saturnin - Reference implementation of Firebird Butler Data Pipe Protocol

See https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
"""

import logging
import typing as t
import uuid
from struct import unpack, pack
from time import monotonic
from zmq import ZMQError
from firebird.butler import fbdp_pb2 as fbdp_proto, fbsd_pb2 as fbsd_proto
from ..types import Enum, Flag, ZMQAddress, Origin, Direction, PipeSocket, \
     InvalidMessageError, StopError
from ..debug import logging, log_on_start
from .. import base
from ..base import msg_bytes

# Constants

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.protocol.fbdp
PROTOCOL_OID: str = '1.3.6.1.4.1.53446.1.5.2'
"""FBDP protocol OID (`firebird.butler.protocol.fbdp`)"""
PROTOCOL_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, PROTOCOL_OID)
"""FBDP protocol UID (:func:`~uuid.uuid5` - NAMESPACE_OID)"""
PROTOCOL_REVISION: int = 1
"""FBDP protocol revision number"""

HEADER_FMT_FULL : str = '!4sBBH'
"""FBDP protocol control frame :mod:`struct` format"""
HEADER_FMT: str = '!4xBBH'
"""FBDP protocol control frame :mod:`struct` format without FOURCC"""
FOURCC: bytes = b'FBDP'
"""FBDP protocol identification (FOURCC)"""
VERSION_MASK: int = 7
"""FBDP protocol version mask"""

DATA_BATCH_SIZE: int = 50
"""Default data batch size"""
READY_PROBE_INTERVAL: int = 10
"""Default READY-probe interval (seconds)"""
READY_PROBE_COUNT: int = 10
"""Default READY-probe count"""

# Logger

log: logging.Logger = logging.getLogger(__name__)
"""FBDP logger"""
#log.setLevel(logging.DEBUG)

# Enums

class MsgType(Enum):
    """FBDP Message Type"""
    UNKNOWN = 0 # not a valid message type
    OPEN = 1    # initial message from client
    READY = 2   # transfer negotiation message
    NOOP = 3    # no operation, used for keep-alive & ping purposes
    DATA = 4    # user data
    CLOSE = 5   # sent by peer that is going to close the connection

class MsgFlag(Flag):
    """FBDP message flag"""
    NONE = 0
    ACK_REQ = 1
    ACK_REPLY = 2

class ErrorCode(Enum):
    """FBDP Error Code"""
    # No error
    OK = 0
    # General errors
    INVALID_MESSAGE = 1
    PROTOCOL_VIOLATION = 2
    ERROR = 3
    INTERNAL_ERROR = 4
    INVALID_DATA = 5
    TIMEOUT = 6
    # Errors that prevent the connection from opening
    PIPE_ENDPOINT_UNAVAILABLE = 100
    FBDP_VERSION_NOT_SUPPORTED = 101
    NOT_IMPLEMENTED = 102
    DATA_FORMAT_NOT_SUPPORTED = 103


# Classes

class Message(base.Message):
    """FBDP Message.

Attributes:
    message_type: Type of message
    type_data:    Data associated with message (int)
    flags:        Message flags
    data:         List of message frames
    data_frame:   Data frame associated with message type (or None)
"""
    def __init__(self):
        super().__init__()
        self.message_type: MsgType = MsgType.UNKNOWN
        self.flags: MsgFlag = MsgFlag(0)
        self.type_data: int = 0
        self.data_frame: t.Union[None, fbdp_proto.FBDPOpenDataframe,
                                 t.List[fbsd_proto.ErrorDescription]] = None
    def from_zmsg(self, frames: t.Sequence) -> None:
        """Populate message attributes from sequence of ZMQ data frames. The `data`
attribute contains a copy of all message frames.

Arguments:
    frames: Sequence of frames that should be deserialized.
"""
        super().from_zmsg(frames)
        control_byte, flags, self.type_data = unpack(HEADER_FMT, self.data.pop(0))
        self.message_type = MsgType(control_byte >> 3)
        self.flags = MsgFlag(flags)
        if self.message_type == MsgType.OPEN:
            self.data_frame = fbdp_proto.FBDPOpenDataframe()
            self.data_frame.ParseFromString(self.data.pop(0))
        elif self.message_type == MsgType.DATA:
            self.data_frame = self.data.pop(0) if self.data else None
        elif self.message_type == MsgType.CLOSE:
            self.type_data = ErrorCode(self.type_data)
            self.data_frame = []
            while self.data:
                err = fbsd_proto.ErrorDescription()
                err.ParseFromString(self.data.pop(0))
                self.data_frame.append(err)
    def as_zmsg(self) -> t.List:
        """Returns message as sequence of ZMQ data frames."""
        zmsg = []
        zmsg.append(self.get_header())
        if self.message_type == MsgType.OPEN:
            zmsg.append(self.data_frame.SerializeToString())
        elif (self.message_type == MsgType.DATA and self.data_frame is not None):
            zmsg.append(self.data_frame)
        elif self.message_type == MsgType.CLOSE:
            while self.data_frame:
                zmsg.append(self.data_frame.pop(0).SerializeToString())
        return zmsg
    def get_header(self) -> bytes:
        """Return message header (FBDP control frame)."""
        return pack(HEADER_FMT_FULL, FOURCC, (self.message_type << 3) | PROTOCOL_REVISION,
                    self.flags, self.type_data)
    def has_ack_req(self) -> bool:
        """Returns True if message has ACK_REQ flag set."""
        return MsgFlag.ACK_REQ in self.flags
    def has_ack_reply(self) -> bool:
        """Returns True if message has ASK_REPLY flag set."""
        return MsgFlag.ACK_REPLY in self.flags
    def set_flag(self, flag: MsgFlag) -> None:
        """Set flag specified by `flag` mask."""
        self.flags |= flag
    def clear_flag(self, flag: MsgFlag) -> None:
        """Clear flag specified by `flag` mask."""
        self.flags &= ~flag
    def clear(self) -> None:
        """Clears message attributes."""
        super().clear()
        self.message_type = MsgType.UNKNOWN
        self.type_data = 0
        self.flags = 0
        self.data_frame = None
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        """Verifies that sequence of ZMQ zmsg frames is a valid FBDP message.

Arguments:
    zmsg: Sequence of ZMQ message frames for validation.

Raises:
    InvalidMessageError: When formal error is detected.
"""
        if not zmsg:
            raise InvalidMessageError("Empty message")
        fbdp_header = msg_bytes(zmsg[0])
        if len(fbdp_header) != 8:
            raise InvalidMessageError("Message header must be 8 bytes long")
        try:
            fourcc, control_byte, flags, _ = unpack(HEADER_FMT_FULL, fbdp_header)
        except Exception as exp:
            raise InvalidMessageError("Can't parse the control frame") from exp
        if fourcc != FOURCC:
            raise InvalidMessageError("Invalid FourCC")
        if (control_byte & VERSION_MASK) != PROTOCOL_REVISION:
            raise InvalidMessageError("Invalid protocol version")
        if (flags | 3) > 3:
            raise InvalidMessageError("Invalid flags")
        msg_type = control_byte >> 3
        try:
            if msg_type == 0:
                raise ValueError()
            message_type = MsgType(msg_type)
        except ValueError:
            raise InvalidMessageError(f"Illegal message type {msg_type}")
        if message_type == MsgType.OPEN:
            if len(zmsg) != 2:
                raise InvalidMessageError("OPEN message must have a dataframe")
            try:
                fpb = fbdp_proto.FBDPOpenDataframe()
                fpb.ParseFromString(msg_bytes(zmsg[1]))
                if not fpb.data_pipe:
                    raise ValueError("Missing 'data_pipe' specification")
                pipe_socket = PipeSocket(fpb.pipe_stream)
                if pipe_socket == 0:
                    raise ValueError("Invalid 'pipe_stream'")
                if not fpb.data_format:
                    raise ValueError("Missing 'data_format' specification")
            except Exception as exc:
                raise InvalidMessageError("Invalid data frame for OPEN message") from exc
        elif (message_type == MsgType.CLOSE and len(zmsg) > 1):
            fpb = fbsd_proto.ErrorDescription()
            for frame in zmsg[1:]:
                fpb.ParseFromString(frame)
                if not fpb.description:
                    raise InvalidMessageError("Missing error description")
        elif (message_type == MsgType.DATA and len(zmsg) > 2):
            raise InvalidMessageError("DATA message may have only one data frame")
        elif (message_type in (MsgType.READY, MsgType.NOOP) and len(zmsg) > 1):
            raise InvalidMessageError("Data frames not allowed for READY and NOOP messages")
    def copy(self) -> 'Message':
        """Returns copy of the message."""
        msg: Message = super().copy()
        msg.message_type = self.message_type
        msg.flags = self.flags
        msg.type_data = self.type_data
        if self.message_type == MsgType.OPEN:
            msg.data_frame = fbdp_proto.FBDPOpenDataframe()
            msg.data_frame.CopyFrom(self.data_frame)
        elif self.message_type == MsgType.CLOSE:
            msg.data_frame = []
            for frame in self.data_frame:
                err = fbsd_proto.ErrorDescription()
                err.CopyFrom(frame)
                msg.data_frame.append(err)
        else:
            msg.data_frame = self.data_frame
        return msg
    def note_exception(self, exc: Exception):
        """Store information from exception into CLOSE Message."""
        assert self.message_type == MsgType.CLOSE
        errdesc = fbsd_proto.ErrorDescription()
        if hasattr(exc, 'code'):
            errdesc.code = getattr(exc, 'code')
        errdesc.description = str(exc)
        self.data_frame.append(errdesc)
    def get_printout(self, separator: str = '\n') -> str:
        """Returns printable, multiline representation of message.
"""
        lines = [f"Message type: {self.message_type.name}",
                 f"Flags: {self.flags}",
                 f"Type data: {self.type_data}",
                ]
        if self.message_type == MsgType.OPEN:
            lines.extend(str(self.data_frame).split('\n'))
        elif (self.message_type == MsgType.DATA and self.data_frame is not None):
            try:
                data_str = self.data_frame.decode('utf8')
            except:
                data_str = self.data_frame.hex()
            lines.append(data_str)
        elif self.message_type == MsgType.CLOSE:
            for data in self.data_frame:
                lines.extend(str(data).split('\n'))
        return separator.join(lines)

class Session(base.Session):
    """FBDP session. Contains information about Data Pipe.

Attributes:
    batch_size (int): Desired DATA batch size [default: DATA_BATCH_SIZE].
    ready (int): DATA batch size received in last READY message.
    transmit (int): Number of DATA messages that remain to be transmitted since last READY message.
    data_pipe (str): Data Pipe Identification.
    pipe_stream (:class:`~saturnin.core.types.PipeSocket`): Data Pipe stream Identification.
    data_format (str): Specification of format for user data transmitted in DATA messages.
"""
    def __init__(self, routing_id: bytes):
        super().__init__(routing_id)
        self.batch_size = DATA_BATCH_SIZE
        self.ready: int = None
        self.transmit = None
        self.data_pipe: str = None
        self.pipe_stream: PipeSocket = None
        self.data_format: str = None

class ServerSession(Session):
    """Extended FBDP session for pipe Servers. Adds information about READY probes.

Attributes:
    probe_countdown (int): Number of remaining READY probes before session is closed
        [default: READY_PROBE_COUNT].
    zero_ready_at (float): Value is either None or monotonic() time when last READY(0)
        was received.
"""
    def __init__(self, routing_id: bytes):
        super().__init__(routing_id)
        self.probe_countdown = READY_PROBE_COUNT
        self.zero_ready_at = None

class Protocol(base.Protocol):
    """9/FBDP - Firebird Butler Data Pipe Protocol

The main purpose of protocol class is to validate ZMQ messages and create FBDP messages.

Attributes:
    message_factory (:data:`~saturnin.core.base.TMessageFactory`): Callable that returns FBDP Message instance.
"""
    OID: str = PROTOCOL_OID
    """FBDP protocol OID (dot notation)"""
    UID: uuid.UUID = PROTOCOL_UID
    """FBDP protocol UID"""
    REVISION: int = PROTOCOL_REVISION
    """FBDP protocol revision number"""
    def __init__(self, message_factory: base.TMessageFactory = Message):
        super().__init__(message_factory)
    @classmethod
    def instance(cls) -> 'Protocol':
        """Returns global FBDP protocol instance with default message factory."""
        return _FBDP_INSTANCE
    def create_message_for(self, message_type: int, type_data: int = None,
                           flags: MsgFlag = None) -> Message:
        """Create new :class:`Message` child class instance for particular FBDP message type.

Arguments:
    message_type: Type of message to be created
    type_data:    Message control data
    flags:        Flags

Returns:
    New :class:`Message` instance.
"""
        msg = self.message_factory()
        msg.message_type = message_type
        if type_data is not None:
            msg.type_data = type_data
        if flags is not None:
            msg.flags = flags
        if msg.message_type == MsgType.OPEN:
            msg.data_frame = fbdp_proto.FBDPOpenDataframe()
        elif msg.message_type == MsgType.CLOSE:
            msg.data_frame = []
        return msg
    def create_ack_reply(self, msg: Message) -> Message:
        """Returns new Message that is an ACK-REPLY response message.
"""
        reply = self.create_message_for(msg.message_type, msg.type_data, msg.flags)
        reply.clear_flag(MsgFlag.ACK_REQ)
        reply.set_flag(MsgFlag.ACK_REPLY)
        return reply
    def has_greeting(self) -> bool:
        """Returns True if protocol uses greeting messages."""
        return True
    def parse(self, zmsg: t.Sequence) -> Message:
        """Parse ZMQ message into protocol message.

Arguments:
    zmsg: Sequence of bytes or :class:`zmq.Frame` instances that must be a valid protocol message.

Returns:
    New protocol message instance with parsed ZMQ message. The BaseProtocol implementation
    returns BaseMessage instance.

Raises:
    InvalidMessageError: If message is not a valid protocol message.
"""
        msg = self.message_factory()
        msg.from_zmsg(zmsg)
        return msg
    def validate(self, zmsg: t.Sequence, origin: Origin, **kwargs) -> None:
        """Validate that ZMQ message is a valid FBSP message.

Arguments:
    zmsg:   Sequence of bytes or :class:`zmq.Frame` instances.
    origin: Origin of received message in protocol context.
    kwargs: Additional keyword-only arguments.

keyword args:
    greeting (bool): If True, the message is validated as greeting message from origin.

Raises:
    InvalidMessageError: If message is not a valid FBDP message.
"""
        Message.validate_zmsg(zmsg)
        if kwargs.get('greeting', False):
            control_byte, _, _ = unpack(HEADER_FMT, msg_bytes(zmsg[0]))
            message_type = MsgType(control_byte >> 3)
            if not (((message_type == MsgType.OPEN) and (origin == Origin.CLIENT)) or
                    ((message_type == MsgType.READY) and (origin == Origin.SERVICE)) or
                    ((message_type == MsgType.CLOSE) and (origin == Origin.SERVICE))):
                raise InvalidMessageError(f"Invalid greeting {message_type.name} from {origin.name}")

_FBDP_INSTANCE = Protocol()

# Callback events

TPipeHandler = t.TypeVar('TPipeHandler', bound='BaseFBDPHandler')
"""Data pipe message handler"""
TPipeClientHandler = t.TypeVar('TPipeClientHandler', bound='PipeClientHandler')
"""Data pipe `Client` message handler"""
TPipeServerHandler = t.TypeVar('TPipeServerHandler', bound='PipeServerHandler')
"""Data pipe `Server` message handler"""
TOnPipeClosed = t.Callable[[TPipeHandler, Session, Message], None]
"""PipeClosed event handler"""
TOnBatchStart = t.Callable[[TPipeHandler, Session], None]
"""BatchStart event handler"""
TOnDataConfirmed = t.Callable[[TPipeHandler, Session], None]
"""DataConfirmed event handler"""
TOnAcceptData = t.Callable[[TPipeHandler, Session, t.Any], int]
"""AcceptData event handler"""
TOnAcceptClient = t.Callable[[TPipeServerHandler, Session, str, PipeSocket, str], int]
"""AcceptClient event handler"""
TOnBatchEnd = t.Callable[[TPipeServerHandler, Session], None]
"""BatchEnd event handler"""
TOnServerReady = t.Callable[[TPipeClientHandler, Session, int], int]
"""ServerReady event handler"""

class BaseFBDPHandler(base.MessageHandler):
    """Base class for FBDP message handlers.

Uses :attr:`~saturnin.core.base.MessageHandler.handlers` dictionary to route received
messages to appropriate handlers.

Important:
   Protocol uses message factory that returns singleton message instance owned by handler.

Messages handled:
    :unknown: Discards session, sends `CLOSE(INVALID_MESSAGE)` if pipe is open.
    :OPEN:    Raises :class:`NotImplementedError`
    :READY:   Raises :class:`NotImplementedError`
    :NOOP:    Sends `ACK_REPLY` back if required, otherwise it will do nothing.
    :DATA:    Raises :class:`NotImplementedError`
    :CLOSE:   Raises :class:`NotImplementedError`

Attributes:
    batch_size: Default DATA batch size for connections [default: :data:`DATA_BATCH_SIZE`].
    on_pipe_closed: Callback executed when `CLOSE` message is received.
    handlers: Dictionary that maps message types to handler methods
"""
    def __init__(self, role: Origin, session_class: t.Type[Session], batch_size: int = None):
        """Message handler initialization.

Arguments:
    role: The role that the handler performs.
    batch_size: Optional default DATA batch size for connections.
"""
        super().__init__(role, session_class)
        self.__msg = Message()
        self.batch_size = batch_size if batch_size else DATA_BATCH_SIZE
        self.handlers = {MsgType.OPEN: self.handle_open,
                         MsgType.READY: self.handle_ready,
                         MsgType.NOOP: self.handle_noop,
                         MsgType.DATA: self.handle_data,
                         MsgType.CLOSE: self.handle_close,
                        }
        self.protocol: Protocol = Protocol(self.message_factory)
        self.on_pipe_closed: TOnPipeClosed = self.__on_pipe_close
    def __on_pipe_close(self, handler: TPipeHandler, session: Session, msg: Message) -> None:
        """Default callback that does nothing."""
    def create_session(self, routing_id: bytes) -> Session:
        """Session object factory."""
        session = super().create_session(routing_id)
        session.batch_size = self.batch_size
        return session
    def message_factory(self) -> Message:
        """Returns private :class:`Message` instance. The instance is cleared before returning."""
        self.__msg.clear()
        return self.__msg
    @log_on_start("{__fn}()", logger=log)
    def handle_unknown(self, session: Session, msg: Message) -> None:
        """Default message handler. Called by :meth:`dispatch` when no appropriate message
handler is found in :attr:`handlers` dictionary.
"""
        if session.data_pipe:
            self.send_close(session, ErrorCode.INVALID_MESSAGE)
        self.discard_session(session)
    def handle_open(self, session: Session, msg: Message) -> None:
        """Handle `OPEN` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    def handle_ready(self, session: Session, msg: Message) -> None:
        """Handle `READY` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    @log_on_start("{__fn}()", logger=log)
    def handle_noop(self, session: Session, msg: Message) -> None:
        """Handle `NOOP` message. Sends `ACK_REPLY` back if required, otherwise it will do nothing."""
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
    def handle_data(self, session: Session, msg: Message) -> None:
        """Handle `DATA` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    def handle_close(self, session: Session, msg: Message) -> None:
        """Handle `CLOSE` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    @log_on_start("{__fn}() [msg={msg.message_type.name}]",
                  logger=log)
    def dispatch(self, session: Session, msg: Message) -> None:
        """Process message received from peer.

Uses :attr:`handlers` dictionary to find appropriate handler for the messsage.
If no appropriate handler is located, calls :meth:`handle_unknown`.

Arguments:
    session: Session attached to peer.
    msg:     FBDP message received from client.
"""
        handler = self.handlers.get(msg.message_type)
        if handler:
            handler(session, msg)
        else:
            self.handle_unknown(session, msg)
    @log_on_start("{__fn}() [batch_size={batch_size}]",
                  logger=log)
    def send_ready(self, session: Session, batch_size: int, defer: bool = True) -> None:
        """Send `READY` message to client
"""
        msg = self.protocol.create_message_for(MsgType.READY, batch_size)
        if not self.send(msg, session, defer):
            raise StopError("Broken pipe")
    @log_on_start("{__fn}() [error_code={error_code}]",
                  logger=log)
    def send_close(self, session: Session, error_code: ErrorCode,
                   exc: Exception = None) -> None:
        """Sends `CLOSE` message to peer and discards the session."""
        msg = self.protocol.create_message_for(MsgType.CLOSE, error_code)
        if exc:
            msg.note_exception(exc)
            if __debug__:
                log.exception("Pipe CLOSE due to exception", exc_info=exc)
        try:
            self.log_pipe_close(session, msg, Direction.OUT)
            self.send(msg, session, False) # do not defer this message
        except ZMQError:
            pass
        except Exception as exc:
            exc.__traceback__ = None
            log.warning("Unexpected error while sending FBDP:CLOSE", exc_info=exc)
        finally:
            self.discard_session(session)
            self.on_pipe_closed(self, session, msg)
    def log_pipe_close(self, session: Session, msg: Message, direction: Direction) -> None:
        """Logs info(OK) or error."""
        writer = log.info if msg.type_data == ErrorCode.OK else log.error
        writer("Pipe %s:CLOSE(%s) [%s:%s]", direction.name, msg.type_data.name,
               session.pipe_stream.name, session.data_pipe)
    @log_on_start("{__fn}()", logger=log)
    def close(self):
        """Close the data pipe connection."""
        session: Session = self.get_session()
        if session is not None:
            if session.data_pipe:
                self.send_close(session, ErrorCode.OK)
            else:
                self.discard_session(session)

class PipeServerHandler(BaseFBDPHandler):
    """Base class for Data Pipe Servers.

Messages handled:
    :OPEN:  Calls `on_accept_client()`. Sends READY on success, CLOSE on error.
    :READY: Non-zero READY calls `on_batch_start()` for PIPE_OUPUT & PIPE_MONITOR.
        Zero READY schedules next READY-probe or cancels the session.
    :DATA:  For PIPE_INPUT calls `on_accept_data()` and handles ACK_REQ.
        For PIPE_OUPUT & PIPE_MONITOR handles ACK_REPLY by calling `on_data_confirmed()`,
        otherwise sends CLOSE(PROTOCOL_VIOLATION).
    :CLOSE: Calls `on_pipe_closed()` and discards the session.

Attributes:
    ready_probe_interval (int): READY probe interval [default: :data:`READY_PROBE_INTERVAL`]
    ready_probe_count (int): Number of READY probes before session is closed
        [default: :data:`READY_PROBE_COUNT`]
    confirm_processing (bool): Whether ACK_REPLY message for DATA/ACK_REQ should be sent
        before (False) or after (True) call to `on_accept_data()` callback [default: False].
    on_accept_client (:class:`TOnAcceptClient`): PRODUCER callback executed when pipe is
        connected
    on_accept_data (:class:`TOnAcceptData`): CONSUMER callback executed when DATA message
        is received for PIPE_INPUT.
    on_batch_start (:class:`TOnBatchStart`): PRODUCER callback executed when non-zero READY
        is received for PIPE_OUPUT/PIPE_MONITOR.
    on_batch_end (:class:`TOnBatchEnd`): CONSUMER callback executed when all DATA messages
        in batch are transmitted.
    on_data_confirmed (:class:`TOnDataConfirmed`): PRODUCER callback executed when
        ACK_REPLY on sent DATA is received.
"""
    def __init__(self, batch_size: int = None):
        super().__init__(Origin.SERVICE, ServerSession, batch_size)
        self.ready_probe_interval: int = READY_PROBE_INTERVAL
        self.ready_probe_count: int = READY_PROBE_COUNT
        self.confirm_processing: bool = False
        self.on_accept_client: TOnAcceptClient = self.__on_accept_client
        self.on_accept_data: TOnAcceptData = self.__on_accept_data
        self.on_batch_start: TOnBatchStart = self.__on_batch_start
        self.on_batch_end: TOnBatchEnd = self.__on_batch_end
        self.on_data_confirmed: TOnDataConfirmed = self.__on_data_confirmed
    def __send_ready_probe(self, session: Session) -> None:
        """Send READY probe."""
        if monotonic() - session.zero_ready_at < self.ready_probe_interval:
            self.chn.manager.defer(self.__send_ready_probe, session)
        else:
            try:
                session.probe_countdown -= 1
                self.send_ready(session, session.batch_size)
            except Exception as exc:
                exc.__traceback__ = None
                log.error("Pipe READY send failed [SRV:%s:%s]", session.pipe_stream,
                          session.data_pipe, exc_info=exc)
                self.cancel_session(session)
    def __on_accept_client(self, handler: TPipeServerHandler, session: Session,
                          data_pipe: str, pipe_stream: PipeSocket, data_format: str) -> int:
        """Default PRODUCER callback that logs warning and returns zero."""
        log.warning("Callback 'on_accept_client' not defined, pipe %s:%s [%s]",
                    pipe_stream.name, data_pipe, data_format)
        return 0
    def __on_accept_data(self, handler: TPipeServerHandler, session: Session, data: bytes) -> int:
        """Default CONSUMER callback that logs warning and returns `ErrorCode.OK`."""
        log.warning("Callback 'on_accept_data' not defined, pipe %s:%s [%s]",
                    session.pipe_stream.name, session.data_pipe, session.data_format)
        return ErrorCode.OK
    def __on_batch_start(self, handler: TPipeServerHandler, session: Session) -> None:
        """Default PRODUCER callback that logs error and send `CLOSE(INTERNAL_ERROR)`."""
        log.error("Callback 'on_batch_start' not defined, pipe %s:%s [%s]",
                    session.pipe_stream.name, session.data_pipe, session.data_format)
        self.send_close(session, ErrorCode.INTERNAL_ERROR)
    @log_on_start("{__fn}()", logger=log)
    def __on_batch_end(self, handler: TPipeServerHandler, session: Session) -> None:
        """Default CONSUMER callback that always sends `READY(batch_size)`."""
        try:
            self.send_ready(session, self.batch_size)
        except Exception as exc:
            exc.__traceback__ = None
            log.error("Pipe READY send failed [SRV:%s:%s]", session.pipe_stream,
                      session.data_pipe, exc_info=exc)
            self.cancel_session(session)
    @log_on_start("{__fn}()", logger=log)
    def __on_data_confirmed(self, handler: TPipeServerHandler, session: Session) -> None:
        "Default PRODUCER callback that does nothing."
    @log_on_start("{__fn}()", logger=log)
    def handle_open(self, session: Session, msg: Message) -> None:
        "Handle `OPEN` message."
        error_code = None
        exc = None
        ready = session.batch_size
        stream = PipeSocket(msg.data_frame.pipe_stream)
        try:
            session.batch_size = ready
            session.data_pipe = msg.data_frame.data_pipe
            session.pipe_stream = stream
            session.data_format = msg.data_frame.data_format
            ready = self.on_accept_client(self, session, msg.data_frame.data_pipe,
                                          stream, msg.data_frame.data_format)
            log.info("Pipe OPEN [SRV:%s:%s] READY(%s)", stream.name, msg.data_frame.data_pipe,
                     ready)
            self.send_ready(session, ready, False) # not deferred
        except (StopError, ZMQError) as err:
            error_code = getattr(err, 'code', ErrorCode.ERROR)
            exc = err
        except Exception as err:
            error_code = ErrorCode.INTERNAL_ERROR
            exc = err
            log.exception("Unhandled exception in on_accept_client() callback.")
        if error_code:
            self.send_close(session, error_code, exc)
    @log_on_start("{__fn}() [ready={msg.type_data}]", logger=log)
    def handle_ready(self, session: Session, msg: Message) -> None:
        """Handle `READY` message."""
        session.ready = msg.type_data
        session.transmit = msg.type_data
        if session.ready == 0:
            if session.probe_countdown > 0:
                session.zero_ready_at = monotonic()
                self.chn.manager.defer(self.__send_ready_probe, session)
            else:
                self.send_close(session, ErrorCode.TIMEOUT)
        else:
            session.zero_ready_at = None
            session.probe_countdown = self.ready_probe_count
            if session.pipe_stream != PipeSocket.INPUT:
                self.on_batch_start(self, session)
    @log_on_start("{__fn}()", logger=log)
    def handle_data(self, session: Session, msg: Message) -> None:
        """Handle `DATA` message."""
        if session.pipe_stream == PipeSocket.INPUT:
            if msg.has_ack_req() and not self.confirm_processing:
                # We must create reply message directly to keep received message
                reply = Message()
                reply.message_type = msg.message_type
                reply.type_data = msg.type_data
                reply.set_flag(MsgFlag.ACK_REPLY)
                if not self.send(msg, session, cancel_on_error=True):
                    return
            try:
                error_code = self.on_accept_data(self, session, msg.data_frame)
            except Exception as exc:
                self.send_close(session, ErrorCode.INTERNAL_ERROR, exc=exc)
                return
            if msg.has_ack_req() and self.confirm_processing:
                if not self.send(self.protocol.create_ack_reply(msg), session,
                                 cancel_on_error=True):
                    return
            if error_code:
                self.send_close(session, error_code)
            else:
                session.transmit -= 1
                if session.transmit == 0:
                    self.on_batch_end(self, session)
        else:
            if msg.has_ack_reply():
                self.on_data_confirmed(self, session)
            else:
                # Only peers attached to PIPE_INPUT can send DATA messages
                self.send_close(session, ErrorCode.PROTOCOL_VIOLATION)
    @log_on_start("{__fn}()", logger=log)
    def handle_close(self, session: Session, msg: Message) -> None:
        """Handle `CLOSE` message."""
        try:
            self.log_pipe_close(session, msg, Direction.IN)
            self.on_pipe_closed(self, session, msg)
        except:
            log.exception("Unhandled exception in Pipe IN:CLOSE [SRV:%s:%s]",
                          session.pipe_stream, session.data_pipe)
        finally:
            self.discard_session(session)


class PipeClientHandler(BaseFBDPHandler):
    """Base class for Data Pipe Clients.

Messages handled:
    :OPEN:  Sends CLOSE(PROTOCOL_VIOLATION).
    :READY: For non-zero READY calls `on_server_ready()` to determine reply READY value.
        When reply READY is non-zero, calls `on_batch_start()` for PIPE_INPUT.
    :DATA:  For PIPE_OUPUT/PIPE_MONITOR calls `on_accept_data()` and handles ACK_REQ.
        For PIPE_INPUT handles ACK_REPLY by calling `on_data_confirmed()`,
        otherwise sends CLOSE(PROTOCOL_VIOLATION).
    :CLOSE: Calls `on_pipe_closed()` and discards the session.

Attributes:
    confirm_processing (bool): Whether ACK_REPLY message for DATA/ACK_REQ should be sent
        before (False) or after (True) call to `on_accept_data()` callback [default: False].
    on_server_ready (:class:`TOnServerReady`): Executed when non-zero READY is received
        from server. Default implementation returns batch_size if < session.batch_size,
        else session.batch_size.
    on_accept_data (:class:`TOnAcceptData`): Executed by CONSUMER when DATA message is
       received from PIPE_OUPUT/PIPE_MONITOR. Default implementation logs warning and
       returns ErrorCode.OK.
    on_batch_start (:class:`TOnBatchStart`): Executed by PRODUCER when non-zero READY is
        received for PIPE_INPUT. Default implementation logs warning.
    on_data_confirmed (:class:`TOnDataConfirmed`): PRODUCER callback executed when
        ACK_REPLY on sent DATA is received.
"""
    def __init__(self, batch_size: int = None):
        super().__init__(Origin.SERVICE, Session, batch_size)
        self.confirm_processing: bool = False
        self.on_server_ready: TOnServerReady = self.__on_server_ready
        self.on_accept_data: TOnAcceptData = self.__on_accept_data
        self.on_batch_start: TOnBatchStart = self.__on_batch_start
        self.on_data_confirmed: TOnDataConfirmed = self.__on_data_confirmed
    def __on_accept_data(self, handler: TPipeClientHandler, session: Session, data: bytes) -> int:
        """Default CONSUMER callback that logs warning and returns ErrorCode.OK."""
        log.warning("Callback 'on_accept_data' not defined, pipe %s:%s [%s]",
                    session.pipe_stream.name, session.data_pipe, session.data_format)
        return ErrorCode.OK
    def __on_server_ready(self, handler: TPipeClientHandler, session: Session, batch_size: int) -> int:
        """Default callback that returns batch_size if < session.batch_size, else session.batch_size."""
        return min(batch_size, session.batch_size)
    def __on_batch_start(self, handler: TPipeClientHandler, session: Session) -> None:
        """Default PRODUCER callback that logs warning."""
        log.warning("Callback 'on_batch_start' not defined, pipe %s:%s [%s]",
                    session.pipe_stream.name, session.data_pipe, session.data_format)
    @log_on_start("{__fn}()", logger=log)
    def __on_data_confirmed(self, handler: TPipeClientHandler, session: Session) -> None:
        """Default PRODUCER callback that does nothing."""
    @log_on_start("{__fn}()", logger=log)
    def handle_open(self, session: Session, msg: Message) -> None:
        """Handle `OPEN` message."""
        self.send_close(session, ErrorCode.PROTOCOL_VIOLATION)
    @log_on_start("{__fn}() [ready={msg.type_data}]", logger=log)
    def handle_ready(self, session: Session, msg: Message) -> None:
        """Handle `READY` message."""
        # session.ready is None for first READY from server
        ready = min(msg.type_data, self.on_server_ready(self, session, msg.type_data))
        log.debug("on_server_ready(%s)->%s", msg.type_data, ready)
        session.ready = ready
        session.transmit = ready
        try:
            self.send_ready(session, ready)
        except Exception as exc:
            exc.__traceback__ = None
            log.error("Pipe READY send failed [CLI:%s:%s]", session.pipe_stream,
                      session.data_pipe, exc_info=exc)
        if not session.discarded and (ready > 0) and (session.pipe_stream == PipeSocket.INPUT):
            self.on_batch_start(self, session)
    @log_on_start("{__fn}()", logger=log)
    def handle_data(self, session: Session, msg: Message) -> None:
        """Handle `DATA` message."""
        if session.pipe_stream == PipeSocket.INPUT:
            if msg.has_ack_reply():
                self.on_data_confirmed(self, session)
            else:
                # We can't accept DATA messages while connected to PIPE_INPUT
                self.send_close(session, ErrorCode.PROTOCOL_VIOLATION)
        else:
            session.transmit -= 1
            if session.transmit < 0:
                self.send_close(session, ErrorCode.PROTOCOL_VIOLATION)
            else:
                if msg.has_ack_req() and not self.confirm_processing:
                    # We must create reply message directly to keep received message
                    reply = Message()
                    reply.message_type = msg.message_type
                    reply.type_data = msg.type_data
                    reply.set_flag(MsgFlag.ACK_REPLY)
                    if not self.send(msg, session, cancel_on_error=True):
                        return
                try:
                    error_code = self.on_accept_data(self, session, msg.data_frame)
                except Exception as exc:
                    self.send_close(session, ErrorCode.INTERNAL_ERROR, exc=exc)
                    return
                if msg.has_ack_req() and self.confirm_processing:
                    if not self.send(self.protocol.create_ack_reply(msg), session,
                                     cancel_on_error=True):
                        return
                if error_code:
                    self.send_close(session, error_code)
    @log_on_start("{__fn}()", logger=log)
    def handle_close(self, session: Session, msg: Message) -> None:
        """Handle `CLOSE` message."""
        try:
            self.log_pipe_close(session, msg, Direction.IN)
            self.on_pipe_closed(self, session, msg)
        except:
            log.exception("Unhandled exception in Pipe IN:CLOSE [CLI:%s:%s]",
                          session.pipe_stream, session.data_pipe)
        finally:
            self.discard_session(session)
    @log_on_start("{__fn}({pipe_addr},{data_pipe},{pipe_stream.name},{data_format})]", logger=log)
    def open(self, pipe_addr: ZMQAddress, data_pipe: str, pipe_stream: PipeSocket,
             data_format: str) -> Session:
        """Opens connection to the Data Pipe.

Arguments:
    pipe_addr:   Data Pipe endpoint.
    data_pipe:   Data Pipe Identification.
    pipe_stream: Data Pipe stream Identification.
    data_format: Specification of format for user data transmitted in DATA messages.
"""
        session = self.connect_peer(pipe_addr)
        session.data_pipe = data_pipe
        session.pipe_stream = pipe_stream
        session.data_format = data_format
        #
        msg = self.protocol.create_message_for(MsgType.OPEN)
        msg.data_frame.data_pipe = data_pipe
        msg.data_frame.pipe_stream = pipe_stream
        msg.data_frame.data_format = data_format
        self.send(msg, session) # Can defer this message
        return session
