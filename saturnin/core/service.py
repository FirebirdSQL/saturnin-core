#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/service.py
# DESCRIPTION:    Base module for implementation of Firebird Butler Services and Microservices
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

"""Saturnin - Base module for implementation of Firebird Butler Services and Microservices
"""

import sys
import typing as t
from importlib import import_module
import time
import zmq
from .types import InterfaceDescriptor, AgentDescriptor, PeerDescriptor, ServiceDescriptor, \
     ZMQAddress, ZMQAddressList, ServiceFacilities, InvalidMessageError, ServiceError
from .debug import logging, log_on_start, log_on_end
from .base import ChannelManager, RouterChannel
from .config import Config
from .protocol.fbsp import validate_welcome_pb, fbsp_proto

# Logger

log = logging.getLogger(__name__)
"""Service logger"""

# Types

TEvent = t.TypeVar('TEvent', bound='Event')

# Functions

@log_on_start("{__fn}({spec!r})", logger=log)
def load(spec: str) -> t.Any:
    """Return object from module. Module is imported if necessary.

Arguments:
    spec: Object specification in format `module[.submodule.[submodule...]]:object_name`

"""
    module_spec, name = spec.split(':')
    if module_spec in sys.modules:
        module = sys.modules[module_spec]
    else:
        module = import_module(module_spec)
    return getattr(module, name)

# Classes

class Event:
    """Dummy Event class.
"""
    def __init__(self):
        self._flag: bool = False
    def is_set(self) -> bool:
        """Return true if and only if the internal flag is true."""
        return self._flag
    isSet = is_set
    def set(self) -> None:
        """Set the internal flag to true."""
        self._flag = True
    def clear(self) -> None:
        """Reset the internal flag to false."""
        self._flag = False
    def wait(self, timeout=0) -> bool:
        """Sleep for specified number of seconds and then return the internal flag state."""
        time.sleep(timeout)
        return self._flag


class BaseServiceImpl:
    """Base Firebird Butler Service implementation.

Configuration options (retrieved via :meth:`get`):
    :shutdown_linger:  ZMQ Linger value used on shutdown [Default 1].

Attributes:
    mngr:       ChannelManager instance. NOT INITIALIZED.
    stop_event: Event object used to stop the service.
    endpoints:  Dictionary of named lists of EndpointAddress instances to which the service
                binds. Initially empty.
"""
    def __init__(self, stop_event: t.Any):
        self.stop_event: TEvent = stop_event
        self.mngr: ChannelManager = None
        self.endpoints: t.Dict[str, ZMQAddressList] = {}
    def get(self, name: str, *args) -> t.Any:
        """Returns value of variable.

Child chlasses must define the attribute with given name, or `get_<name>(*args)` callable
that takes default value as optional argument.

Arguments:
    name:    Name of the variable.
    default: Optional defaut value. Used only for attribute, not callable.

Raises:
    AttributeError: if value couldn't be retrieved and there is no default value provided.
"""
        if hasattr(self, f'get_{name}'):
            fce = getattr(self, f'get_{name}')
            value = fce(*args)
        else:
            value = getattr(self, name, *args)
        return value
    @log_on_start("{__fn}()", logger=log)
    def validate(self) -> None:
        """Validate that service implementation is properly initialized and configured.

Raises:
    AssertionError: When any issue is detected.
"""
        assert self.mngr.channels, "Channel manager without channels"
        for chn in self.mngr.channels:
            assert chn.handler, "Channel without handler"
        if __debug__:
            assert isinstance(self.endpoints, t.Dict)
            for addr_list in self.endpoints.values():
                assert isinstance(addr_list, list)
                for item in addr_list:
                    assert isinstance(item, ZMQAddress)
    @log_on_start("{__fn}()", logger=log)
    def initialize(self, svc: 'BaseService') -> None:
        """Service initialization.

Creates the channel manager with :attr:`svc.zmq_context <BaseService.zmq_context>`.

Important:
    The descendant classes must create at least one communication channel.
"""
        self.mngr = ChannelManager(svc.zmq_context)
    @log_on_start("{__fn}()", logger=log)
    def finalize(self, svc: 'BaseService') -> None:
        """Service finalization.

Base implementation only calls :meth:`~saturnin.core.base.ChannelManager.shutdown` on
service ChannelManager. If `shutdown_linger` is not defined, uses linger 1 for forced
shutdown.
"""
        shutdown_linger = self.get('shutdown_linger', None)
        if shutdown_linger:
            self.mngr.shutdown(shutdown_linger)
        else:
            self.mngr.shutdown()
    @log_on_start("{__fn}()", logger=log)
    def configure(self, svc: 'BaseService', config: Config) -> None:
        """Service configuration.

Note:
    Default implementation does nothing.
"""
    @log_on_start("{__fn}()", logger=log)
    def idle(self) -> None:
        """Should by called by service when waiting for messages exceeds timeout. Default
implementation does nothing.
"""

class BaseService:
    """Base Firebird Butler Service.

(Base)Service defines structure of the service, while actual implementation of individual
structural parts is provided by (Base)ServiceImpl instance.

Attributes:
    impl: Service implementation.
    zmq_context: ZMQ Context instance used by service.
"""
    def __init__(self, impl: BaseServiceImpl, zmq_context: zmq.Context, config: Config):
        """
Arguments:
    impl (:class:`BaseServiceImpl`): Service implementation
    zmq_context (:class:`~zmq.Context`): ZMQ Context
    config (:class:`~saturnin.core.config.Config`): Configuration object
"""
        self.zmq_context: zmq.Context = zmq_context
        self.impl: BaseServiceImpl = impl
        self.config: Config = config
        self._ready: bool = False
    @log_on_start("{__fn}()", logger=log)
    def validate(self) -> None:
        """Validate that service is properly initialized and configured.

Raises:
    AssertionError: When any issue is detected.
"""
        self.impl.validate()
    def run(self) -> None:
        """Runs the service.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError
    @log_on_start("{__fn}() [{self.impl.agent.name}:{self.impl.agent.uid}]",
                  logger=log)
    def initialize(self) -> None:
        """Runs initialization, configuration and validation of the service implementation.

Raises:
    ServiceError: When service is not properly initialized and configured.
"""
        self.impl.initialize(self)
        self.impl.configure(self, self.config)
        try:
            self.validate()
        except Exception as exc:
            raise ServiceError("Service is not properly initialized and configured") from exc
        self._ready = True
    def start(self) -> None:
        """Starts the service. Initializes the service if necessary. Performs finalization
when :meth:`run` finishes.
"""
        log.info("Starting service %s:%s", self.impl.agent.name, self.impl.agent.uid)
        if not self._ready:
            self.initialize()
        try:
            self.run()
        except KeyboardInterrupt:
            pass
        except:
            log.exception("Fatal Error")
        finally:
            self.impl.finalize(self)
        log.info("Service %s:%s stopped", self.impl.agent.name, self.impl.agent.uid)
    ready: bool = property(lambda self: self._ready, doc="True if service is ready to start")

class MicroserviceImpl(BaseServiceImpl):
    """Base microservice implementation.

Configuration options (retrieved via :meth:`~BaseServiceImpl.get`):
    :shutdown_linger:  ZMQ Linger value used on shutdown [Default 1].

Attributes:
    mngr:        ChannelManager instance. NOT INITIALIZED.
    stop_event:  Event object used to stop the service.
    endpoints:   Dictionary of named lists of EndpointAddress instances to which the service
                 binds. Initially empty.
    agent:       AgentDescriptor.
    peer:        PeerDescriptor.
    instance_id: R/O property returning Instance UID.
"""
    def __init__(self, descriptor: ServiceDescriptor, stop_event: t.Any):
        super().__init__(stop_event)
        self.descriptor: ServiceDescriptor = descriptor
        self.facilities: ServiceFacilities = descriptor.facilities
        self.peer: PeerDescriptor = None
    def validate(self) -> None:
        """Validate that microservice implementation is properly initialized and configured.

Raises:
    AssertionError: When any issue is detected.
"""
        super().validate()
        assert isinstance(self.agent, AgentDescriptor)
        assert isinstance(self.peer, PeerDescriptor)
    agent: AgentDescriptor = property(lambda self: self.descriptor.agent, doc="Service Agent")
    instance_id: bytes = property(lambda self: self.peer.uid.bytes,
                                  doc="Service instance identification")

class ServiceImpl(MicroserviceImpl):
    """Base FBSP service implementation.

Configuration options (retrieved via :meth:`~BaseServiceImpl.get`):
    :shutdown_linger:  ZMQ Linger value used on shutdown [Default 1].

Attributes:
    mngr:        ChannelManager instance. NOT INITIALIZED.
    stop_event:  Event object used to stop the service.
    endpoints:   Dictionary of named lists of EndpointAddress instances to which the service
                 binds. Initially empty.
    agent:       AgentDescriptor.
    peer:        PeerDescriptor.
    instance_id: R/O property returning Instance UID.
    welcome_df:  WelcomeDataframe instance.
    api:         List[InterfaceDescriptor]
"""
    def __init__(self, descriptor: ServiceDescriptor, stop_event: TEvent):
        super().__init__(descriptor, stop_event)
        self.endpoints['service'] = []
        self.welcome_df: fbsp_proto.FBSPWelcomeDataframe = fbsp_proto.FBSPWelcomeDataframe()
    def validate(self) -> None:
        """Validate that service implementation is properly initialized and configured.

Raises:
    AssertionError: When any issue is detected.
"""
        super().validate()
        assert isinstance(self.api, t.Sequence)
        for interface in self.api:
            assert isinstance(interface, InterfaceDescriptor)
        try:
            validate_welcome_pb(self.welcome_df)
        except InvalidMessageError as exc:
            raise AssertionError() from exc
    def initialize(self, svc: BaseService) -> None:
        """Initialization of FBSP Welcome Data Frame. It does not fill in any
supplement for peer or agent even if they are defined in descriptors.
"""
        super().initialize(svc)
        self.welcome_df.instance.uid = self.peer.uid.bytes
        self.welcome_df.instance.pid = self.peer.pid
        self.welcome_df.instance.host = self.peer.host
        self.welcome_df.service.uid = self.agent.uid.bytes
        self.welcome_df.service.name = self.agent.name
        self.welcome_df.service.version = self.agent.version
        self.welcome_df.service.classification = self.agent.classification
        self.welcome_df.service.vendor.uid = self.agent.vendor_uid.bytes
        self.welcome_df.service.platform.uid = self.agent.platform_uid.bytes
        self.welcome_df.service.platform.version = self.agent.platform_version
        for interface in self.get('api'):
            intf = self.welcome_df.api.add()
            intf.number = interface.number
            intf.uid = interface.uid.bytes
    @log_on_start("{__fn}()", logger=log)
    def configure(self, svc: BaseService, config: Config) -> None:
        """Performs next actions:
    - Binds service router channel to specified endpoints.
"""
        for endpoint in config.endpoints.value:
            self.endpoints['service'].append(self.svc_chn.bind(endpoint))
    api: t.List[InterfaceDescriptor] = property(lambda self: self.descriptor.api,
                                                doc="Service API")


class SimpleServiceImpl(ServiceImpl):
    """Simple FBSP Service implementation.

Uses one RouterChannel to handle all service clients.

Configuration options (retrieved via :meth:`~BaseServiceImpl.get`):
    :shutdown_linger:  (int) ZMQ Linger value used on shutdown [Default 0]
    :sock_opts: (dict) ZMQ socket options for main service (router) channel [default: None]

Attributes:
    mngr:        ChannelManager instance. NOT INITIALIZED.
    stop_event:  Event object used to stop the service.
    agent:       AgentDescriptor.
    peer:        PeerDescriptor.
    instance_id: R/O property returning Instance UID (from Welcome data frame).
    endpoints:   List of EndpointAddress instances to which the service shall bind itself.
                 Initially empty.
    welcome_df:  WelcomeDataframe instance.
    api:         List[InterfaceDescriptor]
    svc_chn: Inbound RouterChannel
"""
    def __init__(self, descriptor: ServiceDescriptor, stop_event: TEvent):
        super().__init__(descriptor, stop_event)
        self.svc_chn: RouterChannel = None
    def initialize(self, svc: BaseService) -> None:
        """Creates managed (inbound) :Class:`~saturnin.core.base.RouterChannel` for service.
"""
        super().initialize(svc)
        self.svc_chn = RouterChannel(self.instance_id.hex().encode('ascii'),
                                     sock_opts=self.get('sock_opts', None))
        self.mngr.add(self.svc_chn)
