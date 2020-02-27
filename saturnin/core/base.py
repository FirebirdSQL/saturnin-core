#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/base.py
# DESCRIPTION:    ZeroMQ messaging - base classes and other definitions
# CREATED:        28.2.2019
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

"Saturnin - ZeroMQ messaging - base classes and other definitions"

import typing as t
import uuid
from weakref import proxy
from time import monotonic
import zmq
from zmq import Frame, ZMQError, EAGAIN, EHOSTUNREACH
from .types import ZMQAddress, ZMQAddressList, RoutingID, Origin, SocketMode, Direction, \
     InvalidMessageError, ChannelError
from .debug import logging, log_on_start, log_on_end

# Constants

#: Internal routing ID
INTERNAL_ROUTE = b'INTERNAL'
#: Default time limit in seconds for how long session could be suspended before it's cancelled
RESUME_TIMEOUT = 10

# Loggers

log_chnmgr = logging.getLogger('saturnin.core.base.channel_mngr')
"""Logger for channel managers"""
log_chn = logging.getLogger('saturnin.core.base.channel')
"""Logger for channels"""
log_msghnd = logging.getLogger('saturnin.core.base.msg_handler')
"""Logger for message handlers"""
log_ssn = logging.getLogger('saturnin.core.base.session')
"""Logger for sessions"""

#log_chnmgr.setLevel(logging.DEBUG)
#log_chn.setLevel(logging.DEBUG)
#log_msghnd.setLevel(logging.DEBUG)

# Types

TSession = t.TypeVar('TSession', bound='Session')
"""Session type"""
TMessageHandler = t.TypeVar('TMessageHandler', bound='MessageHandler')
"""Message handler type"""
TMessageFactory = t.Callable[[], t.TypeVar('TMessage', bound='Message')]
"""Message factory callable"""
TCancelSessionCallback = t.Callable[[TMessageHandler, TSession], None]
"""Session cancelation callback"""
TSockOpts = t.Dict[str, t.Any]
"""ZMQ socket options"""

# Functions

def peer_role(my_role: Origin) -> Origin:
    """Return role for peer."""
    return Origin.CLIENT if my_role == Origin.SERVICE else Origin.SERVICE

def get_unique_key(dict_: t.Dict[int, t.Any]) -> int:
    """Returns int key value that is not in dictionary."""
    i = 1
    while i in dict_:
        i += 1
    return i

def msg_bytes(msg: t.Union[bytes, bytearray, Frame]) -> t.Union[bytes, bytearray]:
    """Return message frame as bytes."""
    return msg.bytes if isinstance(msg, Frame) else msg

# Manager for ZMQ channels
class ChannelManager:
    """Manager of ZeroMQ communication channels.

Attributes:
    ctx (:class:`zmq.Context`): ZMQ Context instance
    deferred (List[Tuple[Callable,List]]): List with deferred work. Contains tuples with
        callable and arguments.
"""
    def __init__(self, context: zmq.Context):
        """
Args:
    context (:class:`zmq.Context`): ZMQ Context instance.
"""
        self.ctx: zmq.Context = context
        self.deferred: t.List[t.Tuple[t.Callable, t.List]] = []
        self._ch: t.Dict[int, Channel] = {}
        self._poller: zmq.Poller = zmq.Poller()
        self.__chmap: t.Dict[zmq.Socket, Channel] = {}
    @log_on_start("{_fn}({lambda_callback})", logger=log_chnmgr,
                  post_process={'callback': lambda x: getattr(x, '__qualname__', 'UNKNOWN')})
    def defer(self, callback: t.Callable[[t.List], None], *args) -> None:
        """Adds callback with arguments into stack with deferred work."""
        self.deferred.append((callback, args))
    def is_deferred(self, callback: t.Callable, *args) -> bool:
        """Returns true if callback with arguments is already registered."""
        return (callback, args) in self.deferred
    @log_on_start("{_fn}(process_all={process_all})", logger=log_chnmgr)
    def process_deferred(self, process_all: bool = False) -> None:
        """Process one or all deferred callback(s). All processed tasks are removed from
:attr:`deferred` queue.
"""
        if self.deferred:
            if process_all:
                que = self.deferred
                self.deferred = []
                while que:
                    callback, args = que.pop(0)
                    callback(*args)
            else:
                callback, args = self.deferred.pop(0)
                callback(*args)
    def create_socket(self, socket_type: int, **kwargs) -> zmq.Socket:
        """Create new ZMQ socket.

Arguments:
    socket_type: The socket type, which can be any of the 0MQ socket types:
                 REQ, REP, PUB, SUB, PAIR, DEALER, ROUTER, PULL, PUSH, etc.
    kwargs: keyword arguments are passed to the `__init__` method of the socket class.
"""
        return self.ctx.socket(socket_type, **kwargs)
    @log_on_start("{_fn}({channel.__class__.__name__}) [identity={channel.identity}]",
                  logger=log_chnmgr)
    def add(self, channel: 'Channel') -> None:
        """Add channel to the manager."""
        channel._mngr = proxy(self)
        i = get_unique_key(self._ch)
        channel.uid = i
        self._ch[i] = channel
        channel.create_socket()
    @log_on_start("{_fn}({channel.__class__.__name__}) [identity={channel.identity}]",
                  logger=log_chnmgr)
    def remove(self, channel: 'Channel') -> None:
        """Remove channel from the manager."""
        self.unregister(channel)
        channel._mngr = None
        del self._ch[channel.uid]
        channel.uid = None
    def is_registered(self, channel: 'Channel') -> bool:
        """Returns True if channel is registered in Poller."""
        assert channel.socket, "Channel socket not created"
        return channel.socket in self._poller._map
    def register(self, channel: 'Channel') -> None:
        """Register channel in Poller."""
        if not self.is_registered(channel):
            if __debug__: log_chnmgr.debug("register(%s) [identity=%s]",
                                           channel.__class__.__name__, channel.identity)
            self._poller.register(channel.socket, zmq.POLLIN)
            self.__chmap[channel.socket] = channel
    def unregister(self, channel: 'Channel') -> None:
        """Unregister channel from Poller."""
        if self.is_registered(channel):
            if __debug__: log_chnmgr.debug("unregister(%s) [identity=%s]",
                                           channel.__class__.__name__, channel.identity)
            self._poller.unregister(channel.socket)
            del self.__chmap[channel.socket]
    def wait(self, timeout: int = None) -> t.Dict:
        """Wait for I/O events on registered channnels.

Arguments:
    timeout: The timeout in milliseconds. `None` value means `infinite`.

Returns:
    Dictionary [TChannel, events].
"""
        return dict((self.__chmap[skt], e) for skt, e in self._poller.poll(timeout))
    @log_on_end("Channel manager shut down", logger=log_chnmgr)
    @log_on_start("Shutting down channel manager", logger=log_chnmgr)
    def shutdown(self, *args) -> None:
        """Close all managed channels.

Arguments:
    linger (int): Linger parameter for :meth:`Channel.close`
"""
        for chn in self.channels:
            self.unregister(chn)
            chn.close(*args)

    channels: t.ValuesView = property(lambda self: self._ch.values(),
                                      doc="Channels associated with manager")

# Base Classes
class Message:
    """Base class for protocol message.

The base class simply holds ZMQ multipart message in its :attr:`~Message.data` attribute.
Child classes can override :meth:`~Message.from_zmsg()` and :meth:`~Message.as_zmsg()`
methods to pack/unpack some or all parts of ZMQ message into their own attributes. In such
a case, unpacked data must be removed from :attr:`~Message.data` attribute.

Abstract methods:
   :meth:`validate_zmsg()`

Attributes:
    data (list[bytes]):  Sequence of data frames
"""
    def __init__(self):
        self.data: t.List[bytes] = []
    def from_zmsg(self, frames: t.Sequence) -> None:
        """Populate message data from sequence of ZMQ data frames.

Arguments:
    frames: Sequence of frames that should be deserialized.
"""
        self.data = list(frames)
    def as_zmsg(self) -> t.List:
        """Returns message as sequence of ZMQ data frames."""
        return self.data.copy()
    def clear(self) -> None:
        """Clears message data."""
        self.data.clear()
    def copy(self) -> 'Message':
        """Returns copy of the message."""
        msg = Message()
        msg.data = self.data.copy()
        return msg
    @classmethod
    def validate_zmsg(cls, zmsg: t.Sequence) -> None:
        """`Abstract` method. Verifies that sequence of ZMQ frames is a valid message.

Arguments:
    zmsg: Sequence of ZMQ frames for validation.

Raises:
    InvalidMessageError: When formal error is detected in any zmsg frame.
"""
        raise NotImplementedError
    def has_data(self) -> bool:
        """Returns True if :attr:`data` attribute is not empty."""
        return len(self.data) > 0
    def has_zmq_frames(self) -> bool:
        """Returns True if any item in :attr:`data` attribute is a :class:`zmq.Frame` object
(False if all are bytes).
"""
        for item in self.data:
            if isinstance(item, Frame):
                return True
        return False


class Session:
    """Base Peer Session class.

Attributes:
    routing_id (bytes): Channel routing ID
    endpoint (str): Connected service endpoint address, if any
    pending_since (float): Value is either None or :func:`~time.monotonic` time of first
        unsuccessful send operation (i.e. notes time of suspension and start of
        :attr:`MessageHandler.resume_timeout` period)
    messages (list[Message]): List of deferred messages
    discarded (bool): True if sessions was discarded
"""
    def __init__(self, routing_id: RoutingID):
        self.routing_id: RoutingID = routing_id
        self.endpoint_address: t.Optional[ZMQAddress] = None
        self.pending_since: t.Optional[float] = None
        self.messages: t.List[Message] = []
        self.discarded = False
    @log_on_start("{__fn}(#frames={len_zmsg})", logger=log_ssn, post_process={'zmsg': len})
    def send_later(self, zmsg: t.List) -> None:
        """Add ZMQ message to deferred queue"""
        if not self.messages:
            self.pending_since = monotonic()
        self.messages.append(zmsg)
    def get_next_message(self) -> t.List:
        """Returns next deferred message"""
        return self.messages[0]
    def is_suspended(self) -> bool:
        """Returns True if session is suspended (waiting for successful resend of queued
messages)"""
        return self.pending_since is not None
    def message_sent(self) -> None:
        """Notify session that first queued message was successfully sent, so it could be
removed from queue. Also resets timeout for resend."""
        self.messages.pop(0)
        self.pending_since = None

class Protocol:
    """Base class for protocol.

The main purpose of protocol class is to validate ZMQ messages and create protocol messages.
This base class defines common interface for parsing and validation. Descendant classes
typically add methods for creation of protocol messages.

Attributes:
   OID:        string with protocol OID (dot notation). MUST be set in child class.
   UID:        UUID instance that identifies the protocol. MUST be set in child class.
   REVISION:   Protocol revision (default 1)
"""
    OID: str = '1.3.6.1.4.1.53446.1.5' # firebird.butler.protocol
    UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, OID)
    REVISION: int = 1
    def __init__(self, message_factory: TMessageFactory = Message):
        """
Arguments:
    message_factory: Callable that returns :class:`Message` instance
"""
        self.message_factory: TMessageFactory = message_factory
    def has_greeting(self) -> bool:
        """Returns True if protocol uses greeting messages.

The base Protocol class always returns False.
"""
        return False
    def parse(self, zmsg: t.Sequence) -> Message:
        """Parse ZMQ message into protocol message.

Arguments:
    zmsg: Sequence of bytes or :class:`zmq.Frame` instances that must be a valid protocol message.

Returns:
    New protocol message instance with parsed ZMQ message. The base Protocol implementation
    returns base :class:`Message` instance.

Raises:
    InvalidMessageError: If message is not a valid protocol message.
"""
        msg = self.message_factory()
        msg.from_zmsg(zmsg)
        return msg
    def is_valid(self, zmsg: t.List, origin: Origin) -> bool:
        """Return True if ZMQ message is a valid protocol message, otherwise returns False.

Exceptions other than :class:`~saturnin.core.types.InvalidMessageError` are not caught.

Arguments:
    zmsg: Sequence of bytes or :class:`zmq.Frame` instances
    origin: Origin of received message in protocol context.
"""
        try:
            self.validate(zmsg, origin)
        except InvalidMessageError:
            return False
        else:
            return True
    def validate(self, zmsg: t.Sequence, origin: Origin, **kwargs) -> None:
        """Verifies that sequence of ZMQ data frames is a valid protocol message.

The BaseProtocol implementation does nothing.

Arguments:
    zmsg:   Sequence of bytes or :class:`zmq.Frame` instances.
    origin: Origin of received message in protocol context.
    kwargs: Additional keyword-only arguments

Raises:
    InvalidMessageError: If message is not a valid protocol message.
"""
        return

class Channel:
    """Base Class for ZeroMQ communication channel (socket).

Attributes:
    routed:      True if channel uses internal routing
    socket_type: ZMQ socket type
    direction:   Direction of transmission [default: SocketDirection.BOTH]
    socket:      ZMQ socket for transmission of messages
    handler:     Message handler used to process messages received from peer(s)
    uid:         Unique channel ID used by channel manager
    mngr_poll:   True if channel should register its socket into manager Poller
    snd_timeout: Timeout for send operations
    rcv_timeout: Timeout for receive operations
    endpoints:   List of binded/connected endpoints
    flags:       ZMQ flags used by :meth:`send` and :meth:`receive`
    sock_opts:   Dictionary with socket options that should be set after socket creation.
    mode:        BIND/CONNECT mode for socket.
    manager:     The channel manager to which this channel belongs.
    identity:    Identity value for ZMQ socket.
"""
    @log_on_start("{__fn}(identity={identity!r},mngr_poll={mngr_poll!r},"\
                  "snd_timeout={snd_timeout!r},rcv_timeout={rcv_timeout!r},flags={flags!r},"\
                  "sock_opts={sock_opts!r})", logger=log_chn)
    def __init__(self, identity: bytes, mngr_poll: bool = True, snd_timeout: int = 100,
                 rcv_timeout: int = 100, flags: int = zmq.NOBLOCK, sock_opts: TSockOpts = None):
        """Base Class for ZeroMQ communication channel (socket).

Arguments:
    identity: Identity for ZMQ socket.
    mngr_poll: True to register into Channel Manager `Poller`. [default=True]
    snd_timeout: Timeout for send operation on the socket in milliseconds. [default=100]
    rcv_timeout: Timeout for receive operation on the socket in milliseconds. [default=100]
    flags: Flags for send() and receive(). [default=NOBLOCK]
    sock_opts: Dictionary with socket options that should be set after socket creation.
"""
        self.socket_type: int = None
        self.direction: Direction = Direction.BOTH
        self._identity: bytes = identity
        self._mngr_poll: bool = mngr_poll
        self._snd_timeout: int = snd_timeout
        self._rcv_timeout: int = rcv_timeout
        self._mode: SocketMode = SocketMode.UNKNOWN
        self.handler: TMessageHandler = None
        self.uid: int = None
        self._mngr: ChannelManager = None
        self.socket: zmq.Socket = None
        self.routed: bool = False
        self.endpoints: ZMQAddressList = []
        self.flags = flags
        self.sock_opts = sock_opts
        self.configure()
    def __set_mngr_poll(self, value: bool) -> None:
        """Sets mngr_poll"""
        if not value:
            self.manager.unregister(self)
        elif self.endpoints:
            self.manager.register(self)
        self._mngr_poll = value
    def __set_snd_timeout(self, timeout: int) -> None:
        """Sets snd_timeout."""
        self.socket.sndtimeo = timeout
        self._snd_timeout = timeout
    def __set_rcv_timeout(self, timeout: int) -> None:
        """Sets rcv_timeout."""
        self.socket.rcvtimeo = timeout
        self._rcv_timeout = timeout
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        """Called by :meth:`__init__` to configure the channel parameters."""
    @log_on_start("{__fn}()", logger=log_chn)
    def drop_socket(self) -> None:
        """Unconditionally drops the ZMQ socket"""
        try:
            if self.socket and not self.socket.closed:
                self.socket.close(0)
        except ZMQError:
            pass
        self.socket = None
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def create_socket(self) -> None:
        """Create ZMQ socket for this channel.

Called when channel is assigned to manager.
"""
        self.socket = self.manager.create_socket(self.socket_type)
        if self._identity:
            self.socket.identity = self._identity
        self.socket.immediate = 1
        self.socket.sndtimeo = self._snd_timeout
        self.socket.rcvtimeo = self._rcv_timeout
        if self.sock_opts:
            for name, value in self.sock_opts.items():
                setattr(self.socket, name, value)
    def _first_endpoint(self) -> None:
        """Called after the first endpoint is successfully opened.

Registers channel socket into manager Poller if required.
"""
        if self.mngr_poll:
            self.manager.register(self)
    def _last_endpoint(self) -> None:
        """Called after the last endpoint is successfully closed.

Unregisters channel socket from manager Poller.
"""
        self.manager.unregister(self)
    @log_on_start("{__fn}({endpoint!r})", logger=log_chn)
    def bind(self, endpoint: ZMQAddress) -> ZMQAddress:
        """Bind the 0MQ socket to an address.

Returns:
    The endpoint address. The returned address MAY differ from original address when
    wildcard specification is used.

Raises:
    ChannelError: On attempt to a) bind another endpoint for PAIR socket, or b) bind
        to already binded endpoint.
"""
        assert self.mode != SocketMode.CONNECT
        if (self.socket.socket_type == zmq.PAIR) and self.endpoints:
            raise ChannelError("Cannot open multiple endpoints for PAIR socket")
        if endpoint in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' already openned")
        self.socket.bind(endpoint)
        if '*' in endpoint:
            endpoint = ZMQAddress(str(self.socket.LAST_ENDPOINT, 'utf8'))
        self._mode = SocketMode.BIND
        if not self.endpoints:
            self._first_endpoint()
        self.endpoints.append(endpoint)
        return endpoint
    @log_on_start("{__fn}({endpoint!r})", logger=log_chn)
    def unbind(self, endpoint: ZMQAddress = None) -> None:
        """Unbind from an address (undoes a call to `bind()`).

Arguments:
    endpoint: Endpoint address or None to unbind from all binded endpoints.
              Note: The address must be the same as the addresss returned by :meth:`bind`.

Raises:
    ChannelError: If channel is not binded to specified `endpoint`.
"""
        assert self.mode == SocketMode.BIND
        if endpoint and endpoint not in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' not openned")
        addrs = [endpoint] if endpoint else self.endpoints
        for addr in addrs:
            self.socket.unbind(addr)
            self.endpoints.remove(addr)
        if not self.endpoints:
            self._last_endpoint()
            self._mode = SocketMode.UNKNOWN
    @log_on_start("{__fn}({endpoint!r},routing_id={routing_id})", logger=log_chn)
    def connect(self, endpoint: ZMQAddress, routing_id: RoutingID = None) -> None:
        """Connect to a remote channel.

Raises:
    ChannelError: On attempt to a) connect another endpoint for PAIR socket, or b) connect
        to already connected endpoint.
"""
        assert self.mode != SocketMode.BIND
        if (self.socket.socket_type == zmq.PAIR) and self.endpoints:
            raise ChannelError("Cannot open multiple endpoints for PAIR socket")
        if endpoint in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' already openned")
        if self.routed and routing_id:
            self.socket.connect_rid = routing_id
        self.socket.connect(endpoint)
        self._mode = SocketMode.CONNECT
        if not self.endpoints:
            self._first_endpoint()
        self.endpoints.append(endpoint)
    @log_on_start("{__fn}({endpoint!r})", logger=log_chn)
    def disconnect(self, endpoint: ZMQAddress = None) -> None:
        """Disconnect from a remote socket (undoes a call to `connect()`).

Arguments:
    endpoint: Endpoint address or None to disconnect from all connected endpoints.
              Note: The address must be the same as the addresss returned by :meth:`connect`.

Raises:
    ChannelError: If channel is not connected to specified `endpoint`.
"""
        assert self.mode == SocketMode.CONNECT
        if endpoint and endpoint not in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' not openned")
        addrs = [endpoint] if endpoint else self.endpoints
        for addr in addrs:
            self.socket.disconnect(addr)
            self.endpoints.remove(addr)
        if not self.endpoints:
            self._last_endpoint()
            self._mode = SocketMode.UNKNOWN
    @log_on_start("{__fn}(#frames={len_zmsg},timeout={timeout})", logger=log_chn,
                  post_process={'zmsg': len})
    def send(self, zmsg: t.List, timeout: int = None) -> None:
        """Send ZMQ multipart message."""
        assert Direction.OUT in self.direction, "Call to send() on RECEIVE-only channel"
        if timeout is not None:
            self.socket.sndtimeo = timeout
            try:
                self.socket.send_multipart(zmsg, self.flags)
            finally:
                self.socket.sndtimeo = self._snd_timeout
        else:
            self.socket.send_multipart(zmsg, self.flags)
    @log_on_end("{__fn}(timeout={timeout}) -> {len_result} frames",
                logger=log_chn, post_process={'result': len})
    def receive(self, timeout: int = None) -> t.List:
        """Receive ZMQ multipart message."""
        assert Direction.IN in self.direction, "Call to receive() on SEND-only channel"
        if timeout is not None:
            self.socket.rcvtimeo = timeout
            try:
                result = self.socket.recv_multipart(self.flags)
            finally:
                self.socket.rcvtimeo = self._rcv_timeout
            return result
        else:
            return self.socket.recv_multipart(self.flags)
    @log_on_start("{__fn}()", logger=log_chn)
    def close(self, *args) -> None:
        """Permanently closes the channel by closing the ZMQ scoket.

Arguments:
    linger: (int) Linger parameter for `zmq.socket.close()`
"""
        if self.handler:
            self.handler.closing()
        self.socket.close(*args)
    def is_active(self) -> bool:
        """Returns True if channel is active (binded or connected)."""
        return bool(self.endpoints)
    def set_handler(self, handler: TMessageHandler) -> None:
        """Assign message handler for channel."""
        if self.handler:
            self.handler.detach_channel(self)
        self.handler = handler
        self.handler.attach_channel(self)

    mode: SocketMode = property(lambda self: self._mode, doc="ZMQ Socket mode")
    manager: ChannelManager = property(lambda self: self._mngr, doc="Channel manager")
    identity: bytes = property(lambda self: self._identity, doc="ZMQ socket identity")
    mngr_poll: bool = property(lambda self: self._mngr_poll, __set_mngr_poll,
                               doc="Uses central Poller")
    snd_timeout: int = property(lambda self: self._snd_timeout, __set_snd_timeout,
                                 doc="Timeout for send operations")
    rcv_timeout: int = property(lambda self: self._rcv_timeout, __set_rcv_timeout,
                                 doc="Timeout for receive operations")

class MessageHandler:
    """Base class for message handlers.

Attributes:
    chn: Handled I/O channel
    role: Peer role
    sessions: Dictionary of active sessions, key=routing_id
    protocol: Protocol used [default: :class:`Protocol`]
    resume_timeout: Time limit in seconds for how long session could be suspended before
        it's cancelled [default: :attr:`RESUME_TIMEOUT`].
    on_cancel_session: Callback executed before session is cancelled [default: None].
"""
    def __init__(self, role: Origin, session_class: t.Type[Session] = Session):
        """Message handler initialization.

Arguments:
    chn: Channel to be handled.
    role: The role that the handler performs.
    session_class: Class for session objects [default: BaseSession].
    resume_timeout: Time limit in seconds for how long session could be suspended before
        it's cancelled [default: 10].
"""
        self.chn: Channel = None
        self._role: Origin = role
        self.sessions: t.Dict[RoutingID, Session] = {}
        self.protocol: Protocol = Protocol()
        self.resume_timeout: float = RESUME_TIMEOUT
        self.on_cancel_session: t.Optional[TCancelSessionCallback] = None
        self.__scls: t.Type[Session] = session_class
    def attach_channel(self, channel: Channel) -> None:
        """Attach handler to channel."""
        self.chn: Channel = channel
    def detach_channel(self, channel: Channel) -> None:
        """Dettach handler from channel."""
        self.chn = None
    @log_on_start("{__fn}(routing_id={routing_id!r})", logger=log_msghnd)
    def create_session(self, routing_id: RoutingID) -> Session:
        """Session object factory."""
        session = self.__scls(routing_id)
        self.sessions[routing_id] = session
        return session
    def get_session(self, routing_id: RoutingID = INTERNAL_ROUTE) -> Session:
        """Returns session object registered for route or None."""
        return self.sessions.get(routing_id)
    @log_on_start("{__fn}() [session_rid={session.routing_id!r}]", logger=log_msghnd)
    def discard_session(self, session: Session) -> None:
        """Discard session object.

If `session.endpoint` value is set, it also disconnects channel from this endpoint.

Arguments:
    session: :class:`Session` object to be discarded.
"""
        assert session.routing_id in self.sessions
        session.discarded = True
        if session.endpoint_address:
            self.chn.disconnect(session.endpoint_address)
        del self.sessions[session.routing_id]
    @log_on_start("{__fn}() [session_rid={session.routing_id!r}]", logger=log_msghnd)
    def suspend_session(self, session: Session) -> None:
        """Called by :meth:`send` when message must be deferred for later delivery.

Note:
    Default implementation does nothing. Could be overriden to disable workers, etc.
"""
    @log_on_start("{__fn}() [session_rid={session.routing_id!r}]", logger=log_msghnd)
    def resume_session(self, session: Session) -> None:
        """Called by :meth:`_retry_send` when deferred message is sent successfully.

Note:
    Default implementation does nothing. Could be overriden to enable workers, etc.
"""
    @log_on_start("{__fn}() [session_rid={session.routing_id!r}]", logger=log_msghnd)
    def cancel_session(self, session: Session) -> None:
        """Called by :meth:`_retry_send` when attempts to send the message keep failing over
specified time threashold.

Calls :attr:`on_cancel_session` callback if defined and then discards the session."""
        if self.on_cancel_session:
            self.on_cancel_session(self, session)
        self.discard_session(session)
    def closing(self) -> None:
        """Called by channel on Close event.

The base implementation separates the handler from channel to break circular reference.
"""
        self.chn = None
    def handle_invalid_message(self, session: Session, exc: InvalidMessageError) -> None:
        """Called by :meth:`receive` when message parsing raises `InvalidMessageError`.

Note:
    The base implementation does nothing.
"""
        log_msghnd.error("%s.handle_invalid_message(%s/%s)", self.__class__.__name__,
                  session.routing_id, exc)
    def handle_invalid_greeting(self, routing_id: RoutingID, exc: InvalidMessageError) -> None:
        """Called by :meth:`receive` when greeting message parsing raises `InvalidMessageError`.

Note:
    The base implementation does nothing.
"""
        log_msghnd.error("%s.handle_invalid_greeting(%s/%s)", self.__class__.__name__, routing_id, exc)
    def handle_dispatch_error(self, session: Session, msg: Message, exc: Exception) -> None:
        """Called by :meth:`receive` on Exception unhandled by :meth:`dispatch`.

Note:
    The base implementation does nothing.
"""
        log_msghnd.exception("%s.handle_dispatch_error(%s/%s)", self.__class__.__name__,
                      session.routing_id, exc)
    @log_on_start("{__fn}(address={endpoint_address!r},routing_id={routing_id!r})]",
                  logger=log_msghnd)
    def connect_peer(self, endpoint_address: str, routing_id: RoutingID = None) -> Session:
        """Connects to a remote peer and creates a session for this connection.

Arguments:
    endpoint_address: Endpoint for connection.
    routing_id:       Channel routing ID (required for routed channels)
"""
        if self.chn.routed:
            assert routing_id
        else:
            routing_id = INTERNAL_ROUTE
        self.chn.connect(endpoint_address, routing_id)
        session = self.create_session(routing_id)
        session.endpoint_address = endpoint_address
        return session
    def receive(self, zmsg: t.List = None) -> None:
        """Receive and process message from channel."""
        if not zmsg:
            zmsg = self.chn.receive()
        routing_id: bytes = zmsg.pop(0) if self.chn.routed else INTERNAL_ROUTE
        session = self.sessions.get(routing_id)
        if not session:
            if self.protocol.has_greeting():
                try:
                    self.protocol.validate(zmsg, peer_role(self.role), greeting=True)
                except InvalidMessageError as exc:
                    self.handle_invalid_greeting(routing_id, exc)
                    return
            session = self.create_session(routing_id)
        try:
            msg = self.protocol.parse(zmsg)
        except InvalidMessageError as exc:
            self.handle_invalid_message(session, exc)
            return
        try:
            self.dispatch(session, msg)
        except Exception as exc:
            self.handle_dispatch_error(session, msg, exc)
    def send(self, msg: Message, session: Session = None, defer: bool = True,
             cancel_on_error=False, timeout: int = None) -> bool:
        """Send message through channel.

Arguments:
    msg: Message to be send.
    session: Session this message belongs to. Required for routed channels [default: None].
    defer: Whether message should be deferred when send is unsuccessful [default: True].
        Ignored if session is not provided.
    cancel_on_error: Whether session should be cancelled when send is unsuccessful and
        cannot be deferred [default: False]. Ignored if session is not provided.

When `defer` is True and send fails with EAGAIN, the message is queued into session and
scheduled for retry. If send fails with EHOSTUNREACH, the session is cancelled via
:meth:`cancel_session`.

Returns:
    True when message was successfully sent or deferred. False if session was cancelled.

Raises:
    ZMQError: If send fails and `defer` is False, or: when `defer` is True and
        `cancel_on_error` is False and error is not EAGAIN/EHOSTUNREACH.
"""
        result = False
        if session:
            if session.discarded:
                log_msghnd.warning("Can't send using discarded session[%s]",
                                   session.routing_id)
                return False
        else:
            defer = False
            cancel_on_error = False
        zmsg = msg.as_zmsg()
        if self.chn.routed:
            assert session
            zmsg.insert(0, session.routing_id)
        if session and session.messages:
            # Required to keep send order
            session.send_later(zmsg)
            return True
        else:
            try:
                self.chn.send(zmsg, timeout)
            except ZMQError as err:
                # NOTE: `defer` False is a safeguard for absent session
                if err.errno == EAGAIN and defer:
                    if __debug__: log_msghnd.debug("Send failed, suspending session")
                    session.send_later(zmsg)
                    self.chn.manager.defer(self._retry_send, session)
                    self.suspend_session(session)
                elif err.errno == EHOSTUNREACH and defer:
                    log_msghnd.warning("Send failed, host unreachable")
                    self.cancel_session(session)
                else:
                    if cancel_on_error and defer:
                        self.cancel_session(session)
                    else:
                        raise
            else:
                result = True
        return result
    def _retry_send(self, session: Session = None) -> None:
        """Resend previously deferred messages through channel. If send fails with EAGAIN,
it's scheduled for another try, or session is cancelled if time from last failed attempt
exceeds :attr:`resume_timeout`.

Session is cancelled if send fails with other error than EAGAIN.

Session is resumed When first message is sent successfully, and suspended again if any
subsequent send fails.
"""
        success = True
        cancel = False
        while success and session.messages:
            zmsg = session.get_next_message()
            if __debug__: log_msghnd.debug("Resending message %s", zmsg)
            try:
                self.chn.send(zmsg)
            except ZMQError as err:
                success = False
                if err.errno == EAGAIN:
                    delta = monotonic() - session.pending_since
                    if __debug__:
                        log_msghnd.debug("Send retry failed [timeout: %s pending: %s delta: %s]",
                                         self.resume_timeout, session.pending_since, delta)
                    if delta >= self.resume_timeout:
                        cancel = True
                else:
                    log_msghnd.error("Send retry failed, errno: %s, %s", err.errno, err.strerror)
                    cancel = True
            else:
                session.message_sent()
                if __debug__: log_msghnd.debug("Pending messages: %s", len(session.messages))
                if not session.messages:
                    if __debug__: log_msghnd.debug("Resuming session")
                    self.resume_session(session)
        if session.messages and not cancel:
            self.chn.manager.defer(self._retry_send, session)
            if not session.is_suspended():
                if __debug__: log_msghnd.debug("Send retry failed, suspending session")
                session.pending_since = monotonic()
                self.suspend_session(session)
        if cancel:
            if __debug__: log_msghnd.debug("Canceling session")
            self.cancel_session(session)
    def dispatch(self, session: Session, msg: Message) -> None:
        """Process message received from peer.

Important:
    Abstract method, MUST be overridden in child classes.

Arguments:
    session: Session instance.
    msg:     Received message.
"""
        raise NotImplementedError
    def is_active(self) -> bool:
        "Returns True if handler has any active session (connection)."
        return bool(self.sessions)

    role: Origin = property(lambda self: self._role,
                            doc="The role that the handler performs.")

# Channels for individual ZMQ socket types
class DealerChannel(Channel):
    """Communication channel over DEALER socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.DEALER

class PushChannel(Channel):
    """Communication channel over PUSH socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.PUSH
        self.direction = Direction.OUT

class PullChannel(Channel):
    """Communication channel over PULL socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.PULL
        self.direction = Direction.IN

class PubChannel(Channel):
    """Communication channel over PUB socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.PUB
        self.direction = Direction.OUT

class SubChannel(Channel):
    """Communication channel over SUB socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.SUB
        self.direction = Direction.IN
    @log_on_start("{__fn}({topic!r}) [identity={self.identity!r}]", logger=log_chn)
    def subscribe(self, topic: bytes):
        "Subscribe to topic"
        self.socket.subscribe = topic
    @log_on_start("{__fn}({topic!r}) [identity={self.identity!r}]", logger=log_chn)
    def unsubscribe(self, topic: bytes):
        "Unsubscribe from topic"
        self.socket.unsubscribe = topic

class XPubChannel(Channel):
    """Communication channel over XPUB socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.XPUB
    def create_socket(self):
        "Create XPUB socket for this channel."
        super().create_socket()
        self.socket.xpub_verboser = 1 # pass subscribe and unsubscribe messages on XPUB socket

class XSubChannel(Channel):
    """Communication channel over XSUB socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.XSUB
    @log_on_start("{__fn}({topic!r}) [identity={self.identity!r}]", logger=log_chn)
    def subscribe(self, topic: bytes):
        "Subscribe to topic"
        self.socket.send_multipart(b'\x01', topic)
    @log_on_start("{__fn}({topic!r}) [identity={self.identity!r}]", logger=log_chn)
    def unsubscribe(self, topic: bytes):
        "Unsubscribe to topic"
        self.socket.send_multipart(b'\x00', topic)

class PairChannel(Channel):
    """Communication channel over PAIR socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.PAIR

class RouterChannel(Channel):
    """Communication channel over ROUTER socket.
"""
    @log_on_start("{__fn}() [identity={self.identity!r}]", logger=log_chn)
    def configure(self):
        self.socket_type = zmq.ROUTER
        self.routed = True
    def create_socket(self):
        super().create_socket()
        self.socket.router_mandatory = 1
