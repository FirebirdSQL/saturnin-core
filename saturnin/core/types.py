#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/types.py
# DESCRIPTION:    Type definitions
# CREATED:        22.4.2019
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

"""Saturnin - Type definitions
"""

import typing as t
import enum
import uuid
from dataclasses import dataclass
from saturnin.core import PLATFORM_UID, PLATFORM_VERSION

# Type annotation types

TStringList = t.List[str]
"""List of strings"""
TSupplement = t.Optional[t.Dict[str, t.Any]]
"""name/value dictionary"""
Token = t.NewType('Token', bytearray)
"""Message token"""
RoutingID = t.NewType('RoutingID', bytes)
"""Routing ID"""

# Constants

MIME_TYPE_PROTO = 'application/x.fb.proto'
MIME_TYPE_TEXT = 'text/plain'

# Enums

class Enum(enum.IntEnum):
    """Extended enumeration type."""
    @classmethod
    def get_member_map(cls) -> t.Dict[str, 'Enum']:
        """Returns dictionary that maps Enum member names to Enum values (instances)."""
        return cls._member_map_
    @classmethod
    def get_value_map(cls) -> t.Dict[int, 'Enum']:
        """Returns dictionary that maps int values to Enum values (instances)."""
        return cls._value2member_map_
    @classmethod
    def auto(cls) -> int:
        """Returns int for new Enum value."""
        return enum.auto()

    def __repr__(self):
        return f"{self.__class__.__name__}.{self._name_}"

class Flag(enum.IntFlag):
    """Extended flag type."""
    def get_flags(self) -> t.List['Flag']:
        """Returns list with all flag values defined by this type"""
        return [flag for flag in self._member_map_.values()
                if flag.value != 0 and flag in self]
    def get_flag_names(self) -> t.List[str]:
        """Returns list with names of all flags defined by this type"""
        return [flag.name for flag in self._member_map_.values()
                if flag.value != 0 and flag in self]

class Origin(Enum):
    """Origin of received message in protocol context."""
    ANY = Enum.auto()
    SERVICE = Enum.auto()
    CLIENT = Enum.auto()
    # Aliases
    UNKNOWN = ANY
    PROVIDER = SERVICE
    CONSUMER = CLIENT

class SocketMode(Enum):
    """ZMQ socket mode"""
    UNKNOWN = Enum.auto()
    BIND = Enum.auto()
    CONNECT = Enum.auto()

class Direction(Flag):
    """ZMQ socket direction of transmission"""
    IN = Enum.auto()
    OUT = Enum.auto()
    BOTH = OUT | IN

class DependencyType(Enum):
    """Service dependency type"""
    UNKNOWN_DEPTYPE = 0   # Not a valid option, defined only to handle undefined values
    REQUIRED = 1          # Must be provided, can't run without it
    PREFERRED = 2         # Should be provided if available, but can run without it
    OPTIONAL = 3          # Does not need to be available as it can run without it

class ExecutionMode(Enum):
    """Service execution mode"""
    ANY = 0       # No preference
    THREAD = 1    # Run in thread
    PROCESS = 2   # Run in separate process

class AddressDomain(Enum):
    """ZMQ address domain"""
    UNKNOWN_DOMAIN = 0 # Not a valid option, defined only to handle undefined values
    LOCAL = 1          # Within process (inproc)
    NODE = 2           # On single node (ipc or tcp loopback)
    NETWORK = 3        # Network-wide (ip address or domain name)

class TransportProtocol(Enum):
    """ZMQ transport protocol"""
    UNKNOWN_PROTOCOL = 0 # Not a valid option, defined only to handle undefined values
    INPROC = 1
    IPC = 2
    TCP = 3
    PGM = 4
    EPGM = 5
    VMCI = 6

class SocketType(Enum):
    """ZMQ socket type"""
    UNKNOWN_TYPE = 0 # Not a valid option, defined only to handle undefined values
    DEALER = 1
    ROUTER = 2
    PUB = 3
    SUB = 4
    XPUB = 5
    XSUB = 6
    PUSH = 7
    PULL = 8
    STREAM = 9
    PAIR = 10

class SocketUse(Enum):
    """Socket use"""
    UNKNOWN_USE = 0 # Not a valid option, defined only to handle undefined values
    PRODUCER = 1    # Socket used to provide data to peers
    CONSUMER = 2    # Socket used to get data prom peers
    EXCHANGE = 3    # Socket used for bidirectional data exchange

class ServiceType(Enum):
    """Service type"""
    UNKNOWN_SVC_TYPE = 0  # Not a valid option, defined only to handle undefined values
    DATA_PROVIDER = 1     # Data Pipe Service that collects and pass on data.
    DATA_FILTER = 2       # Data Pipe Service that process data from input and sends results to output
    DATA_CONSUMER = 3     # Data Pipe Service that consumes input data
    PROCESSING = 4        # Service for REQEST/REPLY data processing
    EXECUTOR = 5          # Service that does things on request
    CONTROL = 6           # Service that manages other services

class ServiceFacilities(Flag):
    """Service Facilities"""
    FBSP_SOCKET = Enum.auto()      # Standard Butler Service with one socket for FBSP communication
    INPUT_AS_SERVER = Enum.auto()  # Service has/can have INPUT as datapipe SERVER (BINDs pipe INPUT)
    INPUT_AS_CLIENT = Enum.auto()  # Service has/can have INPUT as datapipe CLIENT (CONNECTs to pipe OUTPUT)
    OUTPUT_AS_SERVER = Enum.auto() # Service has/can have OUTPUT as datapipe SERVER (BINDs pipe OUTPUT)
    OUTPUT_AS_CLIENT = Enum.auto() # Service has/can have OUTPUT as datapipe CLIENT (CONNECTs to pipe INPUT)

class ServiceTestType(Enum):
    """Service test type"""
    UNKNOWN_TEST_TYPE = 0 # Not a valid option, defined only to handle undefined values
    CLIENT = 1            # Test uses service Client
    RAW = 2               # Test uses direct ZMQ messaging

class State(Enum):
    """General state information."""
    UNKNOWN_STATE = 0
    READY = 1
    RUNNING = 2
    WAITING = 3
    SUSPENDED = 4
    FINISHED = 5
    ABORTED = 6
    # Aliases
    CREATED = READY
    BLOCKED = WAITING
    STOPPED = SUSPENDED
    TERMINATED = ABORTED

class PipeSocket(Enum):
    """Data Pipe Socket identification"""
    UNKNOWN_PIPE_SOCKET = 0 # Not a valid option, defined only to handle undefined values
    INPUT = 1
    OUTPUT = 2
    MONITOR = 3

class FileOpenMode(Enum):
    """File open mode"""
    UNKNOWN_FILE_OPEN_MODE = 0 # Not a valid option, defined only to handle undefined values
    READ = 1
    CREATE = 2
    WRITE = 3
    APPEND = 4
    RENAME = 5

# Dataclasses

class Distinct:
    """Base class for dataclasses with distinct instances"""
    def get_key(self) -> t.Any:
        """Returns instance key. Used for instance hash computation.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    __hash__ = lambda self: hash(self.get_key())

@dataclass(eq=True, order=True, frozen=True)
class InterfaceDescriptor(Distinct):
    """Interface descriptor

Attributes:
    uid: Interface ID
    name: Interface name
    revision: Interface revision number
    number: Interface Identification Number assigned by Service
    requests: Enum for interface FBSP request codes
"""
    uid: uuid.UUID
    name: str
    revision: int
    number: int
    requests: Enum
    def get_key(self) -> t.Any:
        """Returns `uid` (instance key). Used for instance hash computation."""
        return self.uid

@dataclass(eq=True, order=False, frozen=True)
class AgentDescriptor(Distinct):
    """Service or Client descriptor dataclass.

Note:
    Because this is a `dataclass`, the class variables are those attributes that have
    default value. Other attributes are created in constructor.

Attributes:
    uid: Agent ID
    name: Agent name
    version: Agent version string
    vendor_uid: Vendor ID
    classification: Agent classification string
    platform_uid: Butler platform ID
    platform_version: Butler platform version string
    supplement: Optional list of supplemental information
"""
    uid: uuid.UUID
    name: str
    version: str
    vendor_uid: uuid.UUID
    classification: str
    platform_uid: uuid.UUID = PLATFORM_UID
    """Butler platform ID"""
    platform_version: str = PLATFORM_VERSION
    """Butler platform version string"""
    supplement: TSupplement = None
    """Optional list of supplemental information"""
    def get_key(self) -> t.Any:
        """Returns `uid` (instance key). Used for instance hash computation."""
        return self.uid

@dataclass(eq=True, order=False, frozen=True)
class PeerDescriptor(Distinct):
    """Peer descriptor

Attributes:
    uid: Peer ID
    pid: Peer process ID
    host: Host name
    supplement: Optional list of supplemental information
"""
    uid: uuid.UUID
    pid: int
    host: str
    supplement: TSupplement = None
    def get_key(self) -> t.Any:
        """Returns `uid` (instance key). Used for instance hash computation."""
        return self.uid

@dataclass(eq=True, order=False, frozen=True)
class ServiceDescriptor(Distinct):
    """Service descriptor

Attributes:
    agent: Service agent descriptor
    api: Service FBSP API description or `None` for microservice
    dependencies: Service dependencies (other services or interfaces)
    execution_mode: Preferred execution mode
    service_type: Type of service
    facilities: Service facilities
    description: Text describing the service
    implementation: Locator string for service implementation class
    container: Locator string for service container class
    config: Locator string for service configuration callable
    client: Locator string for service client class
    tests: Locator string for service test class
"""
    agent: AgentDescriptor
    api: t.Optional[t.List[InterfaceDescriptor]]
    dependencies: t.List[t.Tuple[DependencyType, uuid.UUID]]
    execution_mode: ExecutionMode
    service_type: ServiceType
    facilities: ServiceFacilities
    description: str
    implementation: str
    container: str
    config: t.Callable[[], 'Config']
    client: str
    tests: str
    def get_key(self) -> t.Any:
        """Returns `agent.uid` (instance key). Used for instance hash computation."""
        return self.agent.uid

# Classes

class ZMQAddress(str):
    """ZMQ endpoint address.

Descendant from builtin `str` type with additional R/O properties protocol, address and
domain.
"""
    def __new__(cls, value: t.AnyStr):
        if isinstance(value, bytes):
            value = t.cast(bytes, value).decode('utf8')
        if '://' in value:
            protocol, _ = value.split('://', 1)
            if protocol.upper() not in TransportProtocol.get_member_map():
                raise ValueError(f"Uknown protocol '{protocol}'")
        else:
            raise ValueError("Protocol specification required.")
        return str.__new__(cls, value.lower())
    def __get_protocol(self) -> TransportProtocol:
        if '://' in self:
            protocol, _ = self.split('://', 1)
            return TransportProtocol.get_member_map()[protocol.upper()]
        return TransportProtocol.UNKNOWN_PROTOCOL
    def __get_address(self) -> str:
        if '://' in self:
            _, address = self.split('://', 1)
            return address
        return ''
    def __get_domain(self) -> AddressDomain:
        if self.protocol == TransportProtocol.INPROC:
            return AddressDomain.LOCAL
        if self.protocol == TransportProtocol.IPC:
            return AddressDomain.NODE
        if self.protocol == TransportProtocol.TCP:
            if self.address.startswith('127.0.0.1') or self.address.lower().startswith('localhost'):
                return AddressDomain.NODE
            return AddressDomain.NETWORK
        if self.protocol == TransportProtocol.UNKNOWN_PROTOCOL:
            return AddressDomain.UNKNOWN_DOMAIN
        # PGM, EPGM and VMCI
        return AddressDomain.NETWORK
    protocol: TransportProtocol = property(__get_protocol, doc="Transport protocol")
    address: str = property(__get_address, doc="Address")
    domain: AddressDomain = property(__get_domain, doc="Address domain")

ZMQAddressList = t.List[ZMQAddress]

def update_meta(self, other):
    """Helper function for :class:`LateBindingProperty` class."""
    self.__name__ = other.__name__
    self.__doc__ = other.__doc__
    self.__dict__.update(other.__dict__)
    return self

class LateBindingProperty(property):
    """Property class that binds to getter/setter/deleter methods when **instance**
of class that define the property is created. This allows you to override
these methods in descendant classes (if they are not private) without
necessity to redeclare the property itself in descendant class.

Recipe from Tim Delaney, 2005/03/31
http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/408713

Example:
    .. code-block:: python

        class C(object):
            def getx(self):
                print 'C.getx'
                return self._x
            def setx(self, x):
                print 'C.setx'
                self._x = x
            def delx(self):
                print 'C.delx'
                del self._x
            x = LateBindingProperty(getx, setx, delx)

        class D(C):
            def setx(self, x):
                print 'D.setx'
                super(D, self).setx(x)
            def delx(self):
                print 'D.delx'
                super(D, self).delx()

        c = C()
        c.x = 1
        c.x
        c.x
        del c.x
        print
        d = D()
        d.x = 1
        d.x
        d.x
        del d.x

This has the advantages that:
    - You get back an actual property object (with attendant memory savings, performance increases, etc);
    - It's the same syntax as using property(fget, fset, fdel, doc) except for the name;
    - It will fail earlier (when you define the class as opposed to when you use it).
    - It's shorter ;)
    - If you inspect the property you will get back functions with the correct `__name__`, `__doc__`, etc.

"""
    def __new__(cls, fget=None, fset=None, fdel=None, doc=None):
        if fget is not None:
            def __get__(obj, objtype=None, name=fget.__name__):
                fget = getattr(obj, name)
                return fget()
            fget = update_meta(__get__, fget)
        if fset is not None:
            def __set__(obj, value, name=fset.__name__):
                fset = getattr(obj, name)
                return fset(value)
            fset = update_meta(__set__, fset)
        if fdel is not None:
            def __delete__(obj, name=fdel.__name__):
                fdel = getattr(obj, name)
                return fdel()
            fdel = update_meta(__delete__, fdel)
        return property(fget, fset, fdel, doc)


#  Exceptions

class SaturninError(Exception):
    """General exception raised by Saturnin SDK.

Uses `kwargs` to set attributes on exception instance.
"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        for name, value in kwargs.items():
            setattr(self, name, value)
class InvalidMessageError(SaturninError):
    """A formal error was detected in a message"""
class ChannelError(SaturninError):
    """Transmission channel error"""
class ServiceError(SaturninError):
    """Error raised by service"""
class ClientError(SaturninError):
    """Error raised by Client"""
class StopError(SaturninError):
    """Error that should stop furter processing."""
