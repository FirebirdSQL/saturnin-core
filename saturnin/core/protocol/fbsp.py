#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/fbsp.py
# DESCRIPTION:    Reference implementation of Firebird Butler Service Protocol
#                 See https://firebird-butler.readthedocs.io/en/latest/rfc/4/FBSP.html
# CREATED:        21.2.2019
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

"""Saturnin - Reference implementation of Firebird Butler Service Protocol.

See https://firebird-butler.readthedocs.io/en/latest/rfc/4/FBSP.html
"""

import logging
import typing as t
import uuid
from struct import pack, unpack
from time import monotonic
import zmq
from firebird.butler import fbsp_pb2 as fbsp_proto, fbsd_pb2 as fbsd_proto
from ..types import Enum, Flag, Token, RoutingID, Origin, State, \
     ServiceError, ClientError, InvalidMessageError
from .. import base
from ..base import get_unique_key, peer_role, msg_bytes
from ..debug import logging, log_on_start, log_on_end

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.protocol.fbsp
PROTOCOL_OID = '1.3.6.1.4.1.53446.1.5.1'
"""FBSP protocol OID (`firebird.butler.protocol.fbsp`)"""
PROTOCOL_UID = uuid.uuid5(uuid.NAMESPACE_OID, PROTOCOL_OID)
"""FBSP protocol UID (:func:`~uuid.uuid5` - NAMESPACE_OID)"""
PROTOCOL_REVISION = 1
"""FBSP protocol revision number"""

# Message header
HEADER_FMT_FULL = '!4sBBH8s'
"""FBSP protocol control frame :mod:`struct` format"""
HEADER_FMT = '!4xBBH8s'
"""FBSP protocol control frame :mod:`struct` format without FOURCC"""
FOURCC = b'FBSP'
"""FBSP protocol identification (FOURCC)"""
VERSION_MASK = 7
"""FBSP protocol version mask"""
ERROR_TYPE_MASK = 31
"""FBSP protocol error mask"""

# Logger

log = logging.getLogger(__name__)
"""FBSP logger"""
#log.setLevel(logging.DEBUG)

# Enums

class MsgType(Enum):
    """FBSP Message Type"""
    UNKNOWN = 0 # Not a valid option, defined only to handle undefined values
    HELLO = 1   # initial message from client
    WELCOME = 2 # initial message from service
    NOOP = 3    # no operation, used for keep-alive & ping purposes
    REQUEST = 4 # client request
    REPLY = 5   # service response to client request
    DATA = 6    # separate data sent by either client or service
    CANCEL = 7  # cancel request
    STATE = 8   # operating state information
    CLOSE = 9   # sent by peer that is going to close the connection
    ERROR = 31  # error reported by service

class MsgFlag(Flag):
    """FBSP message flag"""
    NONE = 0
    ACK_REQ = 1
    ACK_REPLY = 2
    MORE = 4

class ErrorCode(Enum):
    """FBSP Error Code"""
    # Errors indicating that particular request cannot be satisfied
    INVALID_MESSAGE = 1
    PROTOCOL_VIOLATION = 2
    BAD_REQUEST = 3
    NOT_IMPLEMENTED = 4
    ERROR = 5
    INTERNAL_SERVICE_ERROR = 6
    REQUEST_TIMEOUT = 7
    TOO_MANY_REQUESTS = 8
    FAILED_DEPENDENCY = 9
    FORBIDDEN = 10
    UNAUTHORIZED = 11
    NOT_FOUND = 12
    GONE = 13
    CONFLICT = 14
    PAYLOAD_TOO_LARGE = 15
    INSUFFICIENT_STORAGE = 16
    # Fatal errors indicating that connection would/should be terminated
    SERVICE_UNAVAILABLE = 2000
    FBSP_VERSION_NOT_SUPPORTED = 2001

# Protocol Buffer (fbsp.proto) validators

def __invalid_if(expr: bool, protobuf: str, field: str) -> None:
    """Raise InvalidMessage exception when expr is True."""
    if expr:
        raise InvalidMessageError(f"Missing required field '{protobuf}.{field}'")

def validate_vendor_id_pb(pbo: fbsd_proto.VendorId) -> None:
    """Validate `fbsp.VendorId` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    name = 'VendorId'
    __invalid_if(pbo.uid == 0, name, 'uid')

def validate_platform_id_pb(pbo: fbsd_proto.PlatformId) -> None:
    """Validate `fbsp.PlatformId` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    name = 'PlatformId'
    __invalid_if(pbo.uid == 0, name, 'uid')
    __invalid_if(pbo.version == 0, name, 'version')

def validate_agent_id_pb(pbo: fbsd_proto.AgentIdentification) -> None:
    """Validate `fbsp.AgentIdentification` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    name = 'AgentIdentification'
    __invalid_if(pbo.uid == 0, name, 'uid')
    __invalid_if(pbo.name == 0, name, 'name')
    __invalid_if(pbo.version == 0, name, 'version')
    __invalid_if(not pbo.HasField('vendor'), name, 'vendor')
    __invalid_if(not pbo.HasField('platform'), name, 'platform')
    validate_vendor_id_pb(pbo.vendor)
    validate_platform_id_pb(pbo.platform)

def validate_peer_id_pb(pbo: fbsd_proto.PeerIdentification) -> None:
    """Validate `fbsp.PeerIdentification` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    name = 'PeerIdentification'
    __invalid_if(len(pbo.uid) == 0, name, 'uid')
    __invalid_if(pbo.pid == 0, name, 'pid')
    __invalid_if(len(pbo.host) == 0, name, 'host')

def validate_error_desc_pb(pbo: fbsd_proto.ErrorDescription) -> None:
    """Validate `fbsp.ErrorDescription` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    name = 'ErrorDescription'
    __invalid_if(pbo.code == 0, name, 'code')
    __invalid_if(len(pbo.description) == 0, name, 'description')

def validate_interface_spec_pb(pbo: fbsd_proto.InterfaceSpec) -> None:
    """Validate `fbsp.InterfaceSpec` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    name = 'InterfaceSpec'
    __invalid_if(pbo.number == 0, name, 'number')
    __invalid_if(len(pbo.uid) == 0, name, 'uid')

def validate_cancel_pb(pbo: fbsp_proto.FBSPCancelRequests) -> None:
    """Validate `fbsp.CancelRequests` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    name = 'CancelRequests'
    __invalid_if(len(pbo.token) == 0, name, 'token')

def validate_hello_pb(pbo: fbsp_proto.FBSPHelloDataframe) -> None:
    """Validate `fbsp.HelloDataframe` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    #name = "HelloDataframe"
    validate_peer_id_pb(pbo.instance)
    validate_agent_id_pb(pbo.client)

def validate_welcome_pb(pbo: fbsp_proto.FBSPWelcomeDataframe) -> None:
    """Validate `fbsp.WelcomeDataframe` protobuf.

Raises:
    InvalidMessage: for missing required fields.
"""
    name = 'WelcomeDataframe'
    validate_peer_id_pb(pbo.instance)
    validate_agent_id_pb(pbo.service)
    __invalid_if(len(pbo.api) == 0, name, 'api')
    for ispec in pbo.api:
        validate_interface_spec_pb(ispec)

# Functions

def bb2h(value_hi: int, value_lo: int) -> int:
    """Compose two bytes into word value."""
    return unpack('!H', pack('!BB', value_hi, value_lo))[0]

def uid2uuid(lines: t.Sequence) -> t.List:
    """Replace ugly escaped "uid" strings with standard UUID string format in sequence of
lines.
"""
    result = []
    for line in lines:
        text = line.strip()
        if text.startswith('uid:') or '_uid:' in text or '_uids' in text:
            i = line[line.index('"')+1:line.rindex('"')]
            uid = uuid.UUID(bytes=eval(f'b"{i}"'))
            line = line.replace(i, str(uid))
        result.append(line)
    return result

# Base Message Classes

class Message(base.Message):
    """Base FBSP Message.

Attributes:
    message_type: Type of message
    header:       FBSP control frame (bytes)
    flasg:        flags (int)
    type_data:    Data associated with message (int)
    token:        Message token (bytearray)
    data:         List of data frames
"""
    def __init__(self):
        super().__init__()
        self.message_type: MsgType = MsgType.UNKNOWN
        self.type_data: int = 0
        self.flags: MsgFlag = MsgFlag(0)
        self.token: Token = bytearray(8)
    def _unpack_data(self) -> None:
        """Called when all fields of the message are set. Usefull for data
deserialization."""
    def _pack_data(self, frames: list) -> None:
        """Called when serialization is requested."""
    def _get_printout_ex(self) -> str:
        """Called for printout of attributes defined by descendant classes."""
        return ""
    def from_zmsg(self, frames: t.Sequence) -> None:
        """Populate message attributes from sequence of ZMQ data frames. The :attr:`data`
attribute does not contain the FBSP control frame. Also, the descendant classes may
unpack some data frames into additional attributes they define.

Arguments:
    frames: Sequence of frames that should be deserialized.
"""
        _, flags, self.type_data, self.token = unpack(HEADER_FMT, frames[0])
        self.flags = MsgFlag(flags)
        self.data = frames[1:]  # First frame is a control frame
        self._unpack_data()
    def as_zmsg(self) -> t.List:
        """Returns message as sequence of ZMQ data frames."""
        zmsg = []
        zmsg.append(self.get_header())
        self._pack_data(zmsg)
        zmsg.extend(self.data)
        return zmsg
    def get_header(self) -> bytes:
        """Return message header (FBSP control frame)."""
        return pack(HEADER_FMT_FULL, FOURCC, (self.message_type << 3) | PROTOCOL_REVISION,
                    self.flags, self.type_data, self.token)
    def has_more(self) -> bool:
        """Returns True if message has `MORE` flag set."""
        return MsgFlag.MORE in self.flags
    def has_ack_req(self) -> bool:
        """Returns True if message has `ACK_REQ` flag set."""
        return MsgFlag.ACK_REQ in self.flags
    def has_ack_reply(self) -> bool:
        """Returns True if message has `ACK_REPLY` flag set."""
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
        self.token = bytearray(8)
        self.type_data = 0
        self.flags = MsgFlag(0)
    def copy(self) -> 'Message':
        """Returns copy of the message."""
        msg = super().copy()
        msg.message_type = self.message_type
        msg.type_data = self.type_data
        msg.flags = self.flags
        msg.token = self.token.copy()
        return msg
    def shall_ack(self) -> bool:
        """Returns True if message must be acknowledged."""
        return self.has_ack_req() and self.message_type in (MsgType.NOOP, MsgType.REQUEST,
                                                            MsgType.REPLY, MsgType.DATA,
                                                            MsgType.STATE, MsgType.CANCEL)
    @classmethod
    def validate_cframe(cls, zmsg: t.Sequence) -> None:
        """Verifies that first frame in sequence has valid structure of FBSP control
frame."""
        if not zmsg:
            raise InvalidMessageError("Empty message")
        fbsp_header = msg_bytes(zmsg[0])
        if len(fbsp_header) != 16:
            raise InvalidMessageError("Message header must be 16 bytes long")
        try:
            fourcc, control_byte, flags, _ = unpack('!4sBB10s', fbsp_header)
        except Exception as exp:
            raise InvalidMessageError("Can't parse the control frame") from exp
        if fourcc != FOURCC:
            raise InvalidMessageError("Invalid FourCC")
        if (control_byte & VERSION_MASK) != PROTOCOL_REVISION:
            raise InvalidMessageError("Invalid protocol version")
        if (flags | 7) > 7:
            raise InvalidMessageError("Invalid flags")
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        """Verifies that sequence of ZMQ zmsg frames is a valid FBSP base message.

It validates only FBSP Control Frame. FBSP Data Frames are validated in child classes.
This method does not consider the :class:`~saturnin.core.types.Origin` of the ZMQ message
(see :meth:`Protocol.validate`).

Arguments:
    zmsg: Sequence of ZMQ message frames for validation.

Raises:
    InvalidMessageError: When formal error is detected in first zmsg frame.
"""
        cls.validate_cframe(zmsg)
        (control_byte, type_data) = unpack('!4xBxH8x', msg_bytes(zmsg[0]))
        message_type = MsgType(control_byte >> 3)
        if (message_type in (MsgType.REQUEST, MsgType.STATE)) and (type_data == 0):
            raise InvalidMessageError("Zero Request Code not allowed")
        if (message_type == MsgType.ERROR) and (type_data >> 5 == 0):
            raise InvalidMessageError("Zero Error Code not allowed")
        if (message_type == MsgType.ERROR) and ((type_data & ERROR_TYPE_MASK)
                                                not in (MsgType.HELLO, MsgType.NOOP,
                                                        MsgType.REQUEST, MsgType.DATA,
                                                        MsgType.CANCEL, MsgType.CLOSE)):
            raise InvalidMessageError("Invalid Request Code '%d' for ERROR message"
                                      % (type_data & ERROR_TYPE_MASK))
    def get_printout(self, with_data=True) -> str:
        """Returns printable, multiline representation of message.
"""
        flags = ', '.join(self.flags.get_flag_names())
        lines = [f"Message type: {self.message_type.name}",
                 f"Flags: {flags if flags else 'NONE'}",
                 f"Type data: {self.type_data}",
                 f"Token: {unpack('Q', self.token)[0]}"
                ]
        extra = self._get_printout_ex()
        if extra:
            lines.extend(extra.strip().split('\n'))
        lines.append(f"# data frames: {len(self.data)}")
        if with_data and self.data:
            for index, frame in enumerate(self.data, 1):
                lines.append(f"{index}: {frame}")
        return '\n'.join(lines)

class HandshakeMessage(Message):
    """Base FBSP client/service handshake message (`HELLO` or `WELCOME`).
    The message includes basic information about the Peer.

Attributes:
    peer: Parsed protobuf message with peer information
"""
    def __init__(self):
        super().__init__()
        self.peer = None
    def _unpack_data(self) -> None:
        """Called when all fields of the message are set. Deserializes data into attributes."""
        self.peer.ParseFromString(self.data.pop(0))
    def _pack_data(self, frames: list) -> None:
        """Called when serialization is requested."""
        frames.append(self.peer.SerializeToString())
    def _get_printout_ex(self) -> str:
        """Called for printout of attributes defined by descendant classes."""
        # protobuf returns UUIDs as ugly escaped strings
        # we prefer standard UUID string format
        return "Peer:\n%s" % '\n'.join(uid2uuid(str(self.peer).splitlines()))
        #lines = []
        #for line in str(self.peer).splitlines():
            #if line.strip().startswith('uid:'):
                #i = line[line.index('"')+1:line.rindex('"')]
                #uuid = UUID(bytes=eval(f'b"{i}"'))
                #line = line.replace(i, str(uuid))
            #lines.append(line)
        #return "Peer:\n%s" % '\n'.join(lines)
    def clear(self) -> None:
        super().clear()
        self.peer.Clear()
    def copy(self) -> 'HandshakeMessage':
        """Returns copy of the message."""
        msg: HandshakeMessage = super().copy()
        msg.peer.CopyFrom(self.peer)
        return msg

class HelloMessage(HandshakeMessage):
    """The `HELLO` message is a Client request to open a Connection to the Service.
The message includes basic information about the Client and Connection parameters
required by the Client.

Attributes:
    peer: Parsed `fbsp.FBSPHelloDataframe` protobuf message with peer information
"""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.HELLO
        self.peer: fbsp_proto.FBSPHelloDataframe = fbsp_proto.FBSPHelloDataframe()
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        super().validate_zmsg(zmsg)
        try:
            frame = fbsp_proto.FBSPHelloDataframe()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_hello_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for HELLO message") from exc

class WelcomeMessage(HandshakeMessage):
    """The `WELCOME` message is the response of the Service to the `HELLO` message sent by
the Client, which confirms the successful creation of the required Connection and announces
basic parameters of the Service and the Connection.

Attributes:
    peer: Parsed `fbsp.FBSPWelcomeDataframe` protobuf message with peer information
"""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.WELCOME
        self.peer: fbsp_proto.FBSPWelcomeDataframe = fbsp_proto.FBSPWelcomeDataframe()
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        super().validate_zmsg(zmsg)
        try:
            frame = fbsp_proto.FBSPWelcomeDataframe()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_welcome_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for WELCOME message") from exc

class NoopMessage(Message):
    """The `NOOP` message means no operation. It’s intended for keep alive purposes and
peer availability checks."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.NOOP
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        super().validate_zmsg(zmsg)
        if len(zmsg) > 1:
            raise InvalidMessageError("Data frames not allowed for NOOP")

class APIMessage(Message):
    """Base FBSP client/service API message (`REQUEST`, `REPLY`, `STATE`).
The message includes information about the API call (interface ID and API Code).
"""
    def __get_request_code(self) -> int:
        return self.type_data
    def __get_api_code(self) -> int:
        return unpack('!BB', pack('!H', self.type_data))[1]
    def __set_api_code(self, value: int) -> None:
        self.type_data = bb2h(self.interface_id, value)
    def __get_interface(self) -> int:
        return unpack('!BB', pack('!H', self.type_data))[0]
    def __set_interface(self, value: int) -> None:
        self.type_data = bb2h(value, self.api_code)
    def _get_printout_ex(self) -> str:
        """Called for printout of attributes defined by descendant classes."""
        lines = [f"Interface ID: {self.interface_id}",
                 f"API code: {self.api_code}"
                ]
        return '\n'.join(lines)
    interface_id: int = property(__get_interface, __set_interface,
                                 doc="Interface ID (high byte of Request Code)")
    api_code: int = property(__get_api_code, __set_api_code,
                             doc="API Code (lower byte of Request Code)")
    request_code: int = property(__get_request_code,
                                 doc="Request Code (Interface ID + API Code)")

class RequestMessage(APIMessage):
    """The `REQUEST` message is a Client request to the Service."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.REQUEST

class ReplyMessage(APIMessage):
    """The `REPLY` message is a Service reply to the `REQUEST` message previously sent by Client."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.REPLY

class DataMessage(Message):
    """The `DATA` message is intended for delivery of arbitrary data between connected peers."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.DATA

class CancelMessage(Message):
    """The `CANCEL` message represents a request for a Service to stop processing the previous
request from the Client.

Attributes:
    cancel_reqest: Parsed `fbsp.FBSPCancelRequests` protobuf message
"""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.CANCEL
        self.cancel_reqest: fbsp_proto.FBSPCancelRequests = fbsp_proto.FBSPCancelRequests()
    def _unpack_data(self) -> None:
        self.cancel_reqest.ParseFromString(msg_bytes(self.data.pop(0)))
    def _pack_data(self, frames: list) -> None:
        frames.append(self.cancel_reqest.SerializeToString())
    def _get_printout_ex(self) -> str:
        """Called for printout of attributes defined by descendant classes."""
        return f"Cancel request:\n{self.cancel_reqest}"
    def clear(self) -> None:
        super().clear()
        self.cancel_reqest.Clear()
    def copy(self) -> 'CancelMessage':
        """Returns copy of the message."""
        msg: CancelMessage = super().copy()
        msg.cancel_reqest.ParseFromString(self.cancel_reqest.SerializeToString())
        return msg
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        super().validate_zmsg(zmsg)
        if len(zmsg) > 2:
            raise InvalidMessageError("CANCEL must have exactly one data frame")
        try:
            frame = fbsp_proto.FBSPCancelRequests()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_cancel_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for CANCEL") from exc

class StateMessage(APIMessage):
    """The `STATE` message is sent by Service to report its operating state to the Client."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.STATE
        self._state: fbsp_proto.FBSPStateInformation = fbsp_proto.FBSPStateInformation()
    def __get_state(self) -> State:
        return State(self._state.state)
    def __set_state(self, value: State) -> None:
        self._state.state = value
    def _unpack_data(self) -> None:
        self._state.ParseFromString(msg_bytes(self.data.pop(0)))
    def _pack_data(self, frames: list) -> None:
        frames.append(self._state.SerializeToString())
    def _get_printout_ex(self) -> str:
        """Called for printout of attributes defined by descendant classes."""
        lines = [f"State: {self.state.name}",
                 f"Interface ID: {self.interface_id}",
                 f"API code: {self.api_code}"
                ]
        return '\n'.join(lines)
    def clear(self) -> None:
        super().clear()
        self._state.Clear()
    def copy(self) -> 'StateMessage':
        """Returns copy of the message."""
        msg: StateMessage = super().copy()
        msg._state.CopyFrom(self._state)
        return msg
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        super().validate_zmsg(zmsg)
        if len(zmsg) > 2:
            raise InvalidMessageError("STATE must have exactly one data frame")
        try:
            frame = fbsp_proto.FBSPStateInformation()
            frame.ParseFromString(msg_bytes(zmsg[1]))
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for STATE") from exc

    state: State = property(__get_state, __set_state, doc="Service state")

class CloseMessage(Message):
    """The `CLOSE` message notifies the receiver that sender is going to close the Connection."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.CLOSE

class ErrorMessage(Message):
    """The `ERROR` message notifies the Client about error condition detected by Service.

Attributes:
    errors: List of parsed `fbsp.ErrorDescription` protobuf messages with error information
"""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.ERROR
        self.errors: t.List[fbsd_proto.ErrorDescription] = []
    def __get_error_code(self) -> int:
        return ErrorCode(self.type_data >> 5)
    def __set_error_code(self, value: ErrorCode) -> None:
        self.type_data = (value << 5) | (self.type_data & ERROR_TYPE_MASK)
    def __get_relates_to(self) -> MsgType:
        return MsgType(self.type_data & ERROR_TYPE_MASK)
    def __set_relates_to(self, value: MsgType) -> None:
        self.type_data &= ~ERROR_TYPE_MASK
        self.type_data |= value
    def _unpack_data(self) -> None:
        while self.data:
            err = fbsd_proto.ErrorDescription()
            err.ParseFromString(msg_bytes(self.data.pop(0)))
            self.errors.append(err)
    def _pack_data(self, frames: list) -> None:
        for err in self.errors:
            frames.append(err.SerializeToString())
    def _get_printout_ex(self) -> str:
        """Called for printout of attributes defined by descendant classes."""
        lines = [f"Error code: {self.error_code.name}",
                 f"Relates to: {self.relates_to.name}",
                 f"# Error frames: {len(self.errors)}",
                ]
        for index, err in enumerate(self.errors, 1):
            lines.append(f"@{index}:")
            lines.append(f"{err}")
        return '\n'.join(lines)
    def clear(self) -> None:
        super().clear()
        self.errors.clear()
    def copy(self) -> 'ErrorMessage':
        """Returns copy of the message."""
        msg: ErrorMessage = super().copy()
        for error in self.errors:
            err = fbsd_proto.ErrorDescription()
            err.CopyFrom(error)
            msg.errors.append(err)
        return msg
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        super().validate_zmsg(zmsg)
        frame = fbsd_proto.ErrorDescription()
        for i, segment in enumerate(zmsg[1:]):
            try:
                frame.ParseFromString(msg_bytes(segment))
                validate_error_desc_pb(frame)
                frame.Clear()
            except Exception as exc:
                raise InvalidMessageError("Invalid data frame %d for ERROR" % i) from exc
    def add_error(self) -> fbsd_proto.ErrorDescription:
        """Return newly created ErrorDescription associated with message."""
        frame = fbsd_proto.ErrorDescription()
        self.errors.append(frame)
        return frame

    error_code: ErrorCode = property(fget=__get_error_code, fset=__set_error_code,
                                     doc="Error code")
    relates_to: MsgType = property(fget=__get_relates_to, fset=__set_relates_to,
                                   doc="Message type this error relates to")

# Session, Protocol and Message Handlers

class Session(base.Session):
    """FBSP session. Contains information about peer.

Attributes:
    greeting: :class:`HelloMessage` or :class:`WelcomeMessage` received from peer.
"""
    def __init__(self, routing_id: RoutingID):
        super().__init__(routing_id)
        self.greeting: t.Union[fbsp_proto.FBSPHelloDataframe,
                               fbsp_proto.FBSPWelcomeDataframe] = None
        self._handles: t.Dict[int, RequestMessage] = {}
        self._requests: t.Dict[bytes, RequestMessage] = {}
    def get_handle(self, msg: RequestMessage) -> int:
        """Create new `handle` for request message.

The `handle` is unsigned short integer value that could be used to retrieve the message
from internal storage via :meth:`get_request()`. The message must be previously stored
in session with :meth:`note_request()`. Handle could be used in protocols that use `DATA`
messages send by client to assiciate them with particular request (handle is passed in
`type_data` field of `DATA` message).

Returns:
    Message handle.
"""
        assert msg.token in self._requests
        msg = self._requests[msg.token]
        if hasattr(msg, 'handle'):
            hnd = getattr(msg, 'handle')
        else:
            hnd = get_unique_key(self._handles)
            self._handles[hnd] = msg
            setattr(msg, 'handle', hnd)
        return hnd
    def is_handle_valid(self, hnd: int) -> bool:
        """Returns True if handle is valid."""
        return hnd in self._handles
    def get_request(self, token: Token = None, handle: int = None) -> RequestMessage:
        """Returns stored :class:`RequestMessage` with given `token` or `handle`."""
        assert ((handle is not None) and (handle in self._handles) or
                (token is not None) and (token in self._requests))
        if token is None:
            msg = self._handles[handle]
        else:
            msg = self._requests[token]
        return msg
    def note_request(self, msg: RequestMessage) -> int:
        """Stores REQUEST message into session for later use.

It uses message `token` as key to request data store.
"""
        self._requests[msg.token] = msg
    def request_done(self, request: t.Union[bytes, RequestMessage]) -> None:
        """Removes :class:`RequestMessage` from session.

Arguments:
    request: `RequestMessage` instance or `token` associated with request message.
"""
        key = request.token if isinstance(request, Message) else request
        assert key in self._requests
        msg = self._requests[key]
        if hasattr(msg, 'handle'):
            del self._handles[getattr(msg, 'handle')]
            delattr(msg, 'handle')
        del self._requests[key]

    requests: t.List = property(lambda self: self._requests.values(),
                                doc="List of noted request messages")
    peer_id: bytes = property(lambda self: uuid.UUID(bytes=self.greeting.peer.instance.uid),
                              doc="Peer ID")
    host: str = property(lambda self: self.greeting.peer.instance.host, doc="Peer host")
    pid: int = property(lambda self: self.greeting.peer.instance.pid, doc="Peer process ID")
    agent_id: bytes = property(lambda self: uuid.UUID(bytes=self.greeting.peer.service.uid),
                               doc="Peer agent ID")
    name: str = property(lambda self: self.greeting.peer.service.name, doc="Peer agent name")
    version: str = property(lambda self: self.greeting.peer.service.version,
                            doc="Peer agent version")
    vendor: bytes = property(lambda self: uuid.UUID(bytes=self.greeting.peer.service.vendor.uid),
                             doc="Peer agent vendor ID")
    platform: bytes = property(lambda self: uuid.UUID(bytes=self.greeting.peer.service.platform.uid),
                               doc="Peer agent platform ID")
    platform_version: str = property(lambda self: self.greeting.peer.service.platform.version,
                                     doc="Peer agent platform version")
    classification: str = property(lambda self: self.greeting.peer.service.classification,
                                   doc="Peer agent classification")

class Protocol(base.Protocol):
    """4/FBSP - Firebird Butler Service Protocol

The main purpose of protocol class is to validate ZMQ messages and create FBSP messages.
"""
    OID: str = PROTOCOL_OID
    """FBSP protocol OID (dot notation)"""
    UID: uuid.UUID = PROTOCOL_UID
    """FBSP protocol UID"""
    REVISION: int = PROTOCOL_REVISION
    """FBSP protocol revision number"""
    ORIGIN_MESSAGES: t.Dict[Origin, t.Tuple[MsgType]] = \
        {Origin.SERVICE: (MsgType.ERROR, MsgType.WELCOME, MsgType.NOOP,
                          MsgType.REPLY, MsgType.DATA, MsgType.STATE,
                          MsgType.CLOSE),
         Origin.CLIENT: (MsgType.HELLO, MsgType.NOOP, MsgType.REQUEST,
                         MsgType.CANCEL, MsgType.DATA, MsgType.CLOSE)
         }
    """Valid FBSP message types by :class:`~saturnin.core.types.Origin`"""
    VALID_ACK: t.List[MsgType] = (MsgType.NOOP, MsgType.REQUEST, MsgType.REPLY, \
                                  MsgType.DATA, MsgType.STATE, MsgType.CANCEL)
    """Valid FBSP message types for `ACK_REQUEST` flag"""
    MESSAGE_MAP: t.Dict[MsgType, Message] \
        = {MsgType.HELLO: HelloMessage,
           MsgType.WELCOME: WelcomeMessage,
           MsgType.NOOP: NoopMessage,
           MsgType.REQUEST: RequestMessage,
           MsgType.REPLY: ReplyMessage,
           MsgType.DATA: DataMessage,
           MsgType.CANCEL: CancelMessage,
           MsgType.STATE: StateMessage,
           MsgType.CLOSE: CloseMessage,
           MsgType.ERROR: ErrorMessage,
           }
    """Mapping from message type to specific Message class"""
    @classmethod
    def instance(cls) -> 'Protocol':
        """Returns global FBSP protocol instance."""
        return _FBSP_INSTANCE
    def create_message_for(self, message_type: MsgType, token: Token = None,
                           type_data: int = None,
                           flags: MsgFlag = None) -> Message:
        """Create new :class:`Message` child class instance for particular FBSP message type.

Uses :attr:`message_map` dictionary to find appropriate Message descendant for the messsage.
Raises an exception if no entry is found.

Arguments:
    message_type: Type of message to be created
    token:        Message token
    type_data:    Message control data
    flags:        Flags

Returns:
    New :class:`Message` instance.

Raises:
    ValueError: If there is no class associated with `message_type`.
"""
        cls = self.MESSAGE_MAP.get(message_type)
        if not cls:
            raise ValueError(f"Unknown message type: {message_type}")
        msg = cls()
        if token is not None:
            msg.token = token
        if type_data is not None:
            msg.type_data = type_data
        if flags is not None:
            msg.flags = flags
        return msg
    def create_ack_reply(self, msg: Message) -> Message:
        """Returns new Message that is an `ACK-REPLY` response message.
"""
        reply = self.create_message_for(msg.message_type, msg.token, msg.type_data,
                                        msg.flags)
        reply.clear_flag(MsgFlag.ACK_REQ)
        reply.set_flag(MsgFlag.ACK_REPLY)
        return reply
    def create_welcome_reply(self, msg: HelloMessage) -> WelcomeMessage:
        """Create new WelcomeMessage that is a reply to client's HELLO.

Arguments:
    hello:  :class:`HelloMessage` from the client

Returns:
    New :class:`WelcomeMessage` instance.
"""
        return self.create_message_for(MsgType.WELCOME, msg.token)
    def create_error_for(self, msg: Message, error_code: Enum) -> ErrorMessage:
        """Create new ErrorMessage that relates to specific message.

Arguments:
    message:    :class:`Message` instance that error relates to
    error_code: Error code

Returns:
    New :class:`ErrorMessage` instance.
"""
        err = self.create_message_for(MsgType.ERROR, msg.token)
        err.relates_to = msg.message_type
        err.error_code = error_code
        return err
    def create_reply_for(self, msg: RequestMessage) -> ReplyMessage:
        """Create new ReplyMessage for specific RequestMessage.

Arguments:
    message: :class:`RequestMessage` instance that reply relates to
    value:   State code

Returns:
    New :class:`ReplyMessage` instance.
"""
        return self.create_message_for(MsgType.REPLY, msg.token, msg.type_data)
    def create_state_for(self, msg: RequestMessage, value: int) -> StateMessage:
        """Create new StateMessage that relates to specific RequestMessage.

Arguments:
    message: :class:`RequestMessage` instance that state relates to
    value:   State code

Returns:
    New :class:`StateMessage` instance.
"""
        msg = self.create_message_for(MsgType.STATE, msg.token, msg.type_data)
        msg.state = value
        return msg
    def create_data_for(self, msg: RequestMessage) -> DataMessage:
        """Create new DataMessage for reply to specific RequestMessage.

Arguments:
    message: :class:`RequestMessage` instance that data relates to

Returns:
    New :class:`DataMessage` instance.
"""
        return self.create_message_for(MsgType.DATA, msg.token)
    def create_request_for(self, interface_id: int, api_code: Enum,
                           token: Token = None) -> RequestMessage:
        """Create new :class:`RequestMessage` for specific API call.

Arguments:
    interface_id: Interface Identification Number
    api_code:     API Code
    token:        Message token

Returns:
    New :class:`RequestMessage` (or descendant) instance.
"""
        return self.create_message_for(MsgType.REQUEST, token, bb2h(interface_id, api_code))
    def has_greeting(self) -> bool:
        """Returns True if protocol uses greeting messages."""
        return True
    def parse(self, zmsg: t.Sequence) -> Message:
        """Parse ZMQ message into protocol message.

Arguments:
    zmsg: Sequence of bytes or :class:`zmq.Frame` instances that are a valid FBSP Message.

Returns:
    New :class:`Message` instance with parsed ZMQ message.
"""
        control_byte: int
        flags: int
        type_data: int
        token: Token
        #
        header = msg_bytes(zmsg[0])
        control_byte, flags, type_data, token = unpack(HEADER_FMT, header)
        #
        msg = self.create_message_for(control_byte >> 3, token, type_data, flags)
        msg.from_zmsg(zmsg)
        return msg
    def validate(self, zmsg: t.Sequence, origin: Origin, **kwargs) -> None:
        """Validate that ZMQ message is a valid FBSP message.

Arguments:
    zmsg:   Sequence of bytes or :class:`zmq.Frame` instances.
    origin: Origin of received message in protocol context.
    kwargs: Additional keyword-only arguments.

Keyword args:
    greeting: (bool) If True, the message is validated as greeting message from origin.

Raises:
    InvalidMessageError: If message is not a valid FBSP message.
"""
        Message.validate_cframe(zmsg)
        (control_byte, flags) = unpack('!4xBB10x', msg_bytes(zmsg[0]))
        msg_type = control_byte >> 3
        try:
            if msg_type == 0:
                raise ValueError()
            message_type = MsgType(msg_type)
        except ValueError:
            raise InvalidMessageError(f"Illegal message type {msg_type}")
        flags = MsgFlag(flags)
        if kwargs.get('greeting', False):
            if not (((message_type == MsgType.HELLO) and (origin == Origin.CLIENT)) or
                    ((message_type == MsgType.WELCOME) and (origin == Origin.SERVICE))):
                raise InvalidMessageError(f"Invalid greeting "
                                          f"{message_type.name} from {origin.name}")
        if message_type not in self.ORIGIN_MESSAGES[origin]:
            if MsgFlag.ACK_REPLY not in flags:
                raise InvalidMessageError(f"Illegal message type "
                                          f"{message_type.name} from {origin.name}")
            if message_type not in self.VALID_ACK:
                raise InvalidMessageError(f"Illegal ACK message type "
                                          f"{message_type.name} from {origin.name}")
        self.MESSAGE_MAP[message_type].validate_zmsg(zmsg)

_FBSP_INSTANCE = Protocol()

@log_on_end("{__fn}() -> {result!r}", logger=log)
def exception_for(msg: ErrorMessage) -> ServiceError:
    """Returns :class:`~saturnin.core.types.ServiceError` exception from ERROR message."""
    desc = [f"{msg.error_code.name}, relates to {msg.relates_to.name}"]
    for err in msg.errors:
        desc.append(f"#{err.code} : {err.description}")
    exc = ServiceError('\n'.join(desc))
    return exc

def note_exception(err_msg: ErrorMessage, exc: Exception) -> None:
    """Store information from exception into :class:`ErrorMessage`."""
    to_note = exc
    while to_note:
        errdesc = err_msg.add_error()
        if hasattr(exc, 'code'):
            errdesc.code = getattr(exc, 'code')
        errdesc.description = str(exc)
        to_note = exc.__cause__

# Types

TFBSPMessageHandler = t.Callable[[Session, Message], None]

class BaseFBSPHandler(base.MessageHandler):
    """Base class for FBSP message handlers.

Uses :attr:`handlers` dictionary to route received messages to appropriate handlers.
Child classes may update this table with their own handlers in `__init__()`.
Dictionary key could be either a `tuple(<message_type>,<type_data>)` or just `<message_type>`.

Messages handled:
    :unknown: Raises :class:`NotImplementedError`
    :NOOP:    Sends `ACK_REPLY` back if required, otherwise it will do nothing.
    :DATA:    Raises :class:`NotImplementedError`
    :CLOSE:   Raises :class:`NotImplementedError`

Attributes:
    handlers: Dictionary that maps message types to handler methods.
"""
    def __init__(self, role: Origin):
        super().__init__(role, Session)
        self.handlers: t.Dict[MsgType, TFBSPMessageHandler] = \
            {MsgType.NOOP: self.handle_noop,
             MsgType.DATA: self.handle_data,
             MsgType.CLOSE: self.handle_close,
             }
        self.protocol: Protocol = Protocol.instance()
    def send_protocol_violation(self, session: Session, msg: Message) -> None:
        """Sends ERROR/PROTOCOL_VIOLATION message."""
        errmsg = self.protocol.create_error_for(msg, ErrorCode.PROTOCOL_VIOLATION)
        err = errmsg.add_error()
        err.description = "Received message is a valid FBSP message, but does not " \
            "conform to the protocol."
        self.send(errmsg, session)
    @log_on_start("{__fn}()", logger=log)
    def do_nothing(self, session: Session, msg: Message) -> None:
        """Message handler that does nothing. Useful for cases when message must be handled
but no action is required.
"""
        pass
    def handle_exception(self, session: Session, msg: Message, exc: Exception) -> None:
        """Exception handler called by :meth:`dispatch` on exception in handler.

Note:
    The default implementation only logs exception.
"""
        log.exception("Internal error in message handler")
    def handle_unknown(self, session: Session, msg: Message) -> None:
        """Default message handler. Called by :meth:`dispatch` when no appropriate message handler
is found in :attr:`handlers` dictionary.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    @log_on_start("{__fn}()", logger=log)
    def handle_noop(self, session: Session, msg: NoopMessage) -> None:
        """Handle `NOOP` message. Sends `ACK_REPLY` back if required, otherwise it will do nothing."""
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
    def handle_data(self, session: Session, msg: DataMessage) -> None:
        """Handle `DATA` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    def handle_close(self, session: Session, msg: CloseMessage) -> None:
        """Handle `CLOSE` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    @log_on_start("{__fn}() [msg={msg.message_type.name},rid={session.routing_id!r}]",
                  logger=log)
    def dispatch(self, session: Session, msg: Message) -> None:
        """Process message received from peer.

Uses :attr:`handlers` dictionary to find appropriate handler for the messsage.
First looks for `(message_type, type_data)` entry, then for `message_type`.
If no appropriate handler is located, calls :meth:`handle_unknown`.

Arguments:
    session: Session attached to peer
    msg:     FBSP message received from client
"""
        handler: TFBSPMessageHandler = self.handlers.get((msg.message_type, msg.type_data))
        if not handler:
            handler = self.handlers.get(msg.message_type)
        if handler:
            try:
                handler(session, msg)
            except Exception as exc:
                self.handle_exception(session, msg, exc)
        else:
            self.handle_unknown(session, msg)
    @log_on_start("{__fn}() [msg={msg.message_type.name},rid={lambda_session!r}]",
                  logger=log, post_process={'session': lambda x: x.routing_id if x is not None else None,})
    def send(self, msg: Message, session: Session = None, defer: bool = True,
             cancel_on_error=False, timeout: int = None) -> bool:
        super().send(msg, session, defer, cancel_on_error, timeout)

class ServiceMessagelHandler(BaseFBSPHandler):
    """Base class for Service handlers that process messages from Client.

Uses :attr:`~BaseFBSPHandler.handlers` dictionary to route received messages to appropriate
handlers. Child classes may update this table with their own handlers in `__init__()`.
Dictionary key could be either a `tuple(<message_type>,<type_data>)` or just `<message_type>`.

Messages handled:
    :unknown: Sends ERROR/INVALID_MESSAGE back to the client
    :HELLO:   Sets session.greeting. MUST be overridden to send WELCOME message.
    :WELCOME: Sends ERROR/PROTOCOL_VIOLATION
    :NOOP:    Sends ACK_REPLY back if required, otherwise it will do nothing
    :REQUEST: Fall-back that sends an ERROR/BAD_REQUEST message
    :REPLY:   Handles ACK_REPLY, sends ERROR/PROTOCOL_VIOLATION if it's not the ACK_REPLY
    :DATA:    Sends ERROR/PROTOCOL_VIOLATION
    :CANCEL:  Raises :class:`NotImplementedError`
    :STATE:   Sends ERROR/PROTOCOL_VIOLATION
    :CLOSE:   Discards current session
    :ERROR:   Sends ERROR/PROTOCOL_VIOLATION
"""
    def __init__(self):
        super().__init__(Origin.SERVICE)
        self.handlers.update({MsgType.HELLO: self.handle_hello,
                              MsgType.REQUEST: self.handle_request,
                              MsgType.CANCEL: self.handle_cancel,
                              MsgType.REPLY: self.handle_reply,
                              MsgType.WELCOME: self.send_protocol_violation,
                              MsgType.STATE: self.send_protocol_violation,
                              MsgType.ERROR: self.send_protocol_violation,
                             })
    @log_on_start("{__fn}()", logger=log)
    def close(self):
        """Close all connections to Clients."""
        session: Session
        while self.sessions:
            _, session = self.sessions.popitem()
            try:
                if not session.messages:
                    self.send(self.protocol.create_message_for(MsgType.CLOSE,
                                                               session.greeting.token),
                              session, False) # do not defer this message
            except:
                # channel could be already closed from other side, as we are closing it too
                # we can ignore any send errors
                pass
    def send_error(self, session: Session, related_msg: t.Union[HelloMessage, RequestMessage],
                   error_code: ErrorCode, description: str, app_code: int = None,
                   exc: Exception = None) -> None:
        """Sends `ERROR` message to peer.

Arguments:
    session:     Session that identifies the receiver.
    related_msg: HELLO or REQUEST message this error relates to.
    error_code:  Error code.
    description: Error description.
    app_code:    Optional application-specific error code.
    exc:         Exception that should be noted in error message
"""
        err: ErrorMessage = self.protocol.create_error_for(related_msg, error_code)
        errd = err.add_error()
        if app_code:
            errd.code = app_code
        errd.description = description
        if exc:
            note_exception(err, exc)
        self.send(err, session)
    def handle_exception(self, session: Session, msg: Message, exc: Exception) -> None:
        """Exception handler called by :meth:`dispatch` on exceptions in message handler.

Note:
    The default implementation sends ERROR/INTERNAL_SERVICE_ERROR to the Client and logs
    exception.
"""
        related_msg = msg if isinstance(msg, RequestMessage) else session.greeting
        self.send_error(session, related_msg, ErrorCode.INTERNAL_SERVICE_ERROR,
                        "Internal error in message handler", exc=exc)
        log.exception("Internal error in message handler")
    def handle_invalid_message(self, session: Session, exc: InvalidMessageError) -> None:
        """Called by :meth:`receive` when message parsing raises :Class:`InvalidMessageError`.

Sends ERROR/INVALID_MESSAGE back to the Client.
"""
        log.error("%s.handle_invalid_message(%s/%s)", self.__class__.__name__,
                  session.routing_id, exc)
        err_msg: ErrorMessage = self.protocol.create_error_for(session.greeting,
                                                               ErrorCode.INVALID_MESSAGE)
        note_exception(err_msg, exc)
        self.send(err_msg, session)
    def handle_invalid_greeting(self, routing_id: RoutingID, exc: InvalidMessageError) -> None:
        """Called by :meth:`receive` when greeting message parsing raises :class:`InvalidMessageError`.

Note:
    The default implementation only logs error.
"""
        log.error("%s.handle_invalid_greeting(%s)", self.__class__.__name__, exc)
    def handle_dispatch_error(self, session: Session, msg: Message, exc: Exception) -> None:
        """Called by :meth:`receive` on Exception unhandled by :meth:`dispatch`.

Sends ERROR/INTERNAL_SERVICE_ERROR back to the Client.
"""
        log.error("%s.handle_dispatch_error(%s/%s)", self.__class__.__name__,
                  session.routing_id, exc)
        err_msg: ErrorMessage = self.protocol.create_error_for(msg, ErrorCode.INTERNAL_SERVICE_ERROR)
        note_exception(err_msg, exc)
        self.send(err_msg, session)
    def handle_ack_reply(self, session: Session, msg: Message) -> None:
        """Called by :meth:`handle_reply` to handle REPLY/ACK_REPLY message.

Note:
    The default implementation does nothing.
"""
        if __debug__: log.debug("%s.handle_ack_reply", self.__class__.__name__)
    @log_on_start("{__fn}()", logger=log)
    def handle_unknown(self, session: Session, msg: Message) -> None:
        """Default message handler for unrecognized messages.

Sends ERROR/PROTOCOL_VIOLATION back to the Client.
"""
        errmsg: ErrorMessage = self.protocol.create_error_for(session.greeting, ErrorCode.PROTOCOL_VIOLATION)
        err = errmsg.add_error()
        err.description = "The service does not know how to process this message"
        self.send(errmsg, session)
    @log_on_start("{__fn}()", logger=log)
    def handle_data(self, session: Session, msg: DataMessage) -> None:
        """Default message handler for `DATA` messages.

Note:
    Default implementation sends ERROR/PROTOCOL_VIOLATION back to the Client.
"""
        err_msg: ErrorMessage = self.protocol.create_error_for(msg, ErrorCode.PROTOCOL_VIOLATION)
        err = err_msg.add_error()
        err.description = "Data message not allowed"
        self.send(err_msg, session)
    @log_on_start("{__fn}()", logger=log)
    def handle_close(self, session: Session, msg: CloseMessage) -> None:
        """Handle `CLOSE` message.

If :attr:`~saturnin.core.base.Session.endpoint` is set in session, disconnects underlying
channel from it. Then discards the session.
"""
        self.discard_session(session)
    @log_on_start("{__fn}()", logger=log)
    def handle_hello(self, session: Session, msg: HelloMessage) -> None:
        """Handle `HELLO` message.

Important:
    This method MUST be overridden in child classes to send WELCOME message back to the client.
    Overriding method must call `super().handle_hello(session, msg)`.
"""
        session.greeting = msg
    @log_on_start("{__fn}()", logger=log)
    def handle_request(self, session: Session, msg: RequestMessage) -> None:
        """Handle Client `REQUEST` message.

Note:
   This handler implementation provides a fall-back handler for unsupported request codes
   (not defined in `handler` table) that sends back an ERROR/BAD_REQUEST message.
"""
        self.send(self.protocol.create_error_for(msg, ErrorCode.BAD_REQUEST), session)
    def handle_cancel(self, session: Session, msg: CancelMessage) -> None:
        """Handle `CANCEL` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    @log_on_start("{__fn}()", logger=log)
    def handle_reply(self, session: Session, msg: ReplyMessage):
        """Handle `REPLY` message.

Note:
    The client SHALL not send `REPLY` message to the service, unless it's an `ACK_REPLY`.
    If it's an `ACK_REPLY`, the handler calls :meth:`handle_ack_reply`, otherwise it
    sends ERRO/PROTOCOL_VIOLATION message to the client.
"""
        if msg.has_ack_reply():
            self.handle_ack_reply(session, msg)
        else:
            self.send_protocol_violation(session, msg)

class ClientMessageHandler(BaseFBSPHandler):
    """Base class for Client handlers that process messages from Service.

Uses :attr:`~BaseFBSPHandler.handlers` dictionary to route received messages to appropriate
handlers. Child classes may update this table with their own handlers in `__init__()`.
Dictionary key could be either a `tuple(<message_type>,<type_data>)` or just `<message_type>`.

Messages handled:
    :unknown: Raises :class:`~saturnin.core.types.ClientError`
    :HELLO:   Raises :class:`~saturnin.core.types.ClientError`
    :WELCOME: Store WELCOME to session.greeting or raise :class:`~saturnin.core.types.ClientError`
              on unexpected one.
    :NOOP:    Sends ACK_REPLY back if required, otherwise it will do nothing.
    :REQUEST: Raises :class:`~saturnin.core.types.ClientError`
    :REPLY:   Raises :class:`NotImplementedError`
    :DATA:    Raises :class:`NotImplementedError`
    :CANCEL:  Raises :class:`~saturnin.core.types.ClientError`
    :STATE:   Raises :class:`NotImplementedError`
    :CLOSE:   Disconnects the service, closes the session, and raises
              :class:`~saturnin.core.types.ClientError`.
    :ERROR:   Raises :class:`NotImplementedError`

Attributes:
    last_token_seen: Token from last message processed by `handle_*` handlers or None.
"""
    def __init__(self):
        super().__init__(Origin.CLIENT)
        self.handlers.update({MsgType.WELCOME: self.handle_welcome,
                              MsgType.REPLY: self.handle_reply,
                              MsgType.STATE: self.handle_state,
                              MsgType.ERROR: self.handle_error,
                              MsgType.HELLO: self.raise_protocol_violation,
                              MsgType.REQUEST: self.raise_protocol_violation,
                              MsgType.CANCEL: self.raise_protocol_violation,
                             })
        self._tcnt: int = 0 # Token generator
        self.last_token_seen: Token = None
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    def raise_protocol_violation(self, session: Session, msg: Message) -> None:
        """Unconditionally raises :class:`~saturnin.core.types.ClientError`"""
        raise ClientError(f"Protocol violation from service, message type: {msg.message_type.name}")
    def new_token(self) -> Token:
        """Return newly created `token` value."""
        self._tcnt += 1
        return pack('Q', self._tcnt)
    @log_on_start("{__fn}()", logger=log)
    def close(self) -> None:
        """Close connection to Service."""
        session: Session = self.get_session()
        if session:
            try:
                if not session.messages:
                    self.send(self.protocol.create_message_for(MsgType.CLOSE,
                                                               session.greeting.token),
                              session, False) # do not defer this message
            except:
                # channel could be already closed from other side, as we are closing it too
                # we can ignore any send errors
                pass
            self.discard_session(session)
    def handle_invalid_message(self, session: Session, exc: InvalidMessageError) -> None:
        """Called by :meth:`get_response` when message parsing raises `InvalidMessageError`.

Raises:
   ClientError: Unconditionally
"""
        log.error("%s.handle_invalid_message(%s/%s)", self.__class__.__name__,
                  session.routing_id, exc)
        raise ClientError("Invalid message received from service") from exc
    def handle_invalid_greeting(self, routing_id: RoutingID, exc: InvalidMessageError) -> None:
        """Called by :meth:`receive` when greeting message parsing raises `InvalidMessageError`.

Raises:
    ClientError: Unconditionally
"""
        log.error("%s.handle_invalid_greeting(%s/%s)", self.__class__.__name__, routing_id, exc)
        raise ClientError("Invalid greeting received from service") from exc
    @log_on_start("{__fn}() [token={token!r},timeout={timeout}]", logger=log)
    def get_response(self, token: Token, timeout: int = None) -> bool:
        """Get reponse from Service.

Process incomming messages until timeout reaches out or response arrives. Valid response
is any message with token equal to: a) passed `token` argument or b) token from
session.greeting.

Arguments:
    token:   Token used for request
    timeout: Timeout (in milliseconds) for request [default: infinity]

Important:
    - All registered handler methods must store token of handled message into
      `last_token_seen` attribute.
    - Does not work with routed channels, and channels without active session.
    - Exceptions raised by message or error handlers are propagated to the caller.

Returns:
    True if response arrives in time, False on timeout (or when called overriden
    :meth:`handle_invalid_message` or :meth:`handle_invalid_greeting` handler does not
    raise an exception).

Raises:
    ClientError: When invalid greeting or message is received from service.
    Exception: Also `handle_*` message handlers may raise exceptions.
"""
        assert not self.chn.routed, "Routed channels are not supported"
        stop = False
        session: Session = self.get_session()
        assert session, "Active session required"
        start = monotonic()
        while not stop:
            self.last_token_seen = None
            event = self.chn.socket.poll(timeout)
            if event == zmq.POLLIN:
                zmsg = self.chn.receive()
                if not session.greeting:
                    try:
                        self.protocol.validate(zmsg, peer_role(self.role), greeting=True)
                    except InvalidMessageError as exc:
                        self.handle_invalid_greeting(session.routing_id, exc)
                        return False
                try:
                    msg = self.protocol.parse(zmsg)
                except InvalidMessageError as exc:
                    self.handle_invalid_message(session, exc)
                    return False
                self.dispatch(session, msg)
            if self.last_token_seen and self.last_token_seen in (token, session.greeting.token):
                return True
            if timeout:
                stop = round((monotonic() - start) * 1000) >= timeout
        return False
    @log_on_start("{__fn}()", logger=log)
    def handle_unknown(self, session: Session, msg: Message) -> None:
        """Default message handler for unrecognized messages.

Raises:
    ClientError: Unconditionally
"""
        raise ClientError(f"The client does not know how to process received "
                          f"{msg.message_type.name}:{msg.type_data} message")
    @log_on_start("{__fn}()", logger=log)
    def handle_close(self, session: Session, msg: CloseMessage) -> None:
        """Handle `CLOSE` message.

If :attr:`~saturnin.core.base.Session.endpoint` is set in session, disconnects underlying
channel from it. Then discards the session and raises :class:`~saturnin.core.types.ClientError`.
"""
        self.last_token_seen = msg.token
        self.discard_session(session)
        raise ClientError("The service has closed the connection.")
    @log_on_start("{__fn}()", logger=log)
    def handle_welcome(self, session: Session, msg: WelcomeMessage) -> None:
        """Handle `WELCOME` message.

Saves WELCOME message into `session.greeting`.

Raises:
    ClientError: for unexpected WELCOME.
"""
        self.last_token_seen = msg.token
        if not session.greeting:
            session.greeting = msg
        else:
            raise ClientError("Unexpected WELCOME message")
    def handle_reply(self, session: Session, msg: ReplyMessage) -> None:
        """Handle Service `REPLY` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    def handle_state(self, session: Session, msg: StateMessage) -> None:
        """Handle `STATE` message.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    def handle_error(self, session: Session, msg: ErrorMessage) -> None:
        """Handle `ERROR` message received from Service.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
