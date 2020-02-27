#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/client.py
# DESCRIPTION:    Base module for implementation of Firebird Butler Service Clients
# CREATED:        2.5.2019
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

"""Saturnin - Base module for implementation of Firebird Butler Service Clients
"""

import logging
import typing as t
from .types import InterfaceDescriptor, PeerDescriptor, AgentDescriptor, ClientError, \
     ZMQAddress
from .base import Channel
from .protocol import fbsp
from .protocol.fbsp import fbsp_proto

# Logger

log = logging.getLogger(__name__)
"""Client logger"""

# Classes

class ServiceClient(fbsp.ClientMessageHandler):
    """Base Service Client

Abstract methods:
    :get_handlers:  Returns Dict for mapping FBSP messages sent by service to handler methods.
    :get_interface: Returns descriptor for service interface used by client.

Attributes:
    interface_id:  Number assigned by service to interface used by client or None.
"""
    def __init__(self, chn: Channel, peer: PeerDescriptor, agent: AgentDescriptor):
        if __debug__: log.debug("%s.__init__", self.__class__.__name__)
        super().__init__()
        chn.set_handler(self)
        self.hello_df: fbsp_proto.FBSPHelloDataframe = fbsp_proto.FBSPHelloDataframe()
        self.peer: PeerDescriptor = peer
        self.agent: AgentDescriptor = agent
        self.interface_id: int = None
        self.__handlers: t.Dict = None
    def handle_exception(self, session: fbsp.Session, msg: fbsp.Message, exc: Exception) -> None:
        """Exception handler called by :meth:`~saturnin.core.base.MessageHandler.dispatch`
on exception in handler. The exception is reraised in client, because it shouold be handled
elsewhere and not swallowed by :meth:`~saturnin.core.base.MessageHandler.dispatch`.
"""
        raise exc
    def handle_welcome(self, session: fbsp.Session, msg: fbsp.WelcomeMessage) -> None:
        """Handle WELCOME message.

Save WELCOME message into `session.greeting`, notes number assigned by service to used
interface and updates message handlers.

Raises:
    ClientError: For unexpected WELCOME, or when service does not support required interface.
"""
        if __debug__: log.debug("%s.handle_welcome", self.__class__.__name__)
        super().handle_welcome(session, msg)
        intf_uid = self.get_interface().uid.bytes
        interface_id = None
        for api in msg.peer.api:
            if api.uid == intf_uid:
                interface_id = api.number
        if interface_id is None:
            raise ClientError("Service does not support required interface")
        self.interface_id = interface_id
        if self.__handlers is None:
            self.__handlers = self.handlers.copy()
        self.handlers = self.__handlers.copy()
        self.handlers.update(self.get_handlers(interface_id))
    def get_interface(self) -> InterfaceDescriptor:
        """Returns descriptor for service interface used by client.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError()
    def get_handlers(self, api_number: int) -> t.Dict:
        """Returns Dict for mapping FBSP messages sent by service to handler methods.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError()
    def open(self, endpoint: ZMQAddress, timeout: int = 1000) -> None:
        """Opens connection to service.

Arguments:
    endpoint: Service address.
    timeout:  The timeout (in milliseconds) to wait for response from service. Value None
        means no time limit. [Defailt: 1000]

Raises:
    ClientError: if connection to service fails
"""
        if __debug__: log.debug("%s.open", self.__class__.__name__)
        session = self.connect_peer(endpoint)
        token = self.new_token()
        hello: fbsp.HelloMessage = self.protocol.create_message_for(fbsp.MsgType.HELLO, token)
        self.hello_df.instance.uid = self.peer.uid.bytes
        self.hello_df.instance.pid = self.peer.pid
        self.hello_df.instance.host = self.peer.host
        self.hello_df.client.uid = self.agent.uid.bytes
        self.hello_df.client.name = self.agent.name
        self.hello_df.client.version = self.agent.version
        self.hello_df.client.vendor.uid = self.agent.vendor_uid.bytes
        self.hello_df.client.platform.uid = self.agent.platform_uid.bytes
        self.hello_df.client.platform.version = self.agent.platform_version
        fbsp.validate_hello_pb(self.hello_df)
        hello.peer.CopyFrom(self.hello_df)
        try:
            self.send(hello, session, defer=False)
            if not self.get_response(token, timeout):
                raise ClientError("Connection to service failed")
        except Exception:
            self.discard_session(session)
            raise
    def close(self):
        """Close connection to Service."""
        if __debug__: log.debug("%s.close", self.__class__.__name__)
        super().close()
        self.interface_id = None
    def is_connected(self) -> bool:
        """Returns True if client has active connection to the Service."""
        return self.interface_id is not None
