#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           test/t_fbsp.py
# DESCRIPTION:    Unit tests for FBSP implementation
# CREATED:        26.2.2019
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

"Saturnin - Unit tests for FBSP implementation."

import unittest
import io
from uuid import UUID
from struct import pack
from saturnin.core import VENDOR_UID, PLATFORM_UID
from saturnin.core.protocol import fbsp
from saturnin.core.base import Origin

def get_token(val):
    "Return FBSP message token from integer."
    return pack('Q', val)

class TestMessages(unittest.TestCase):
    """Basic tests for FBSP Message classes"""
    def setUp(self):
        self.out = io.StringIO()
        self._fbsp = fbsp.Protocol.instance()
    def tearDown(self):
        self.out.close()
    def print_msg(self, msg: fbsp.Message) -> None:
        "Print message"
        print(msg.get_printout(), file=self.out)
        print("=" * 10, file=self.out)
        #print(self.out.getvalue())
    def check_msg(self, msg: fbsp.Message, origin: Origin) -> fbsp.Message:
        "Serialize, validate and parse the message."
        zmsg = msg.as_zmsg()
        self._fbsp.validate(zmsg, origin)
        return self._fbsp.parse(zmsg)
    def create_hello(self) -> fbsp.HelloMessage:
        "Creates test HELLO message"
        msg: fbsp.HelloMessage = self._fbsp.create_message_for(fbsp.MsgType.HELLO, get_token(1))
        msg.peer.instance.uid = UUID('c24bdd24-46be-11e9-8f39-5404a6a1fd6e').bytes
        msg.peer.instance.pid = 100
        msg.peer.instance.host = "localhost"
        msg.peer.client.uid = UUID('c9cf8bcc-46be-11e9-8f39-5404a6a1fd6e').bytes
        msg.peer.client.name = "Agent name"
        msg.peer.client.version = "1.0"
        msg.peer.client.vendor.uid = VENDOR_UID.bytes
        msg.peer.client.platform.uid = PLATFORM_UID.bytes
        msg.peer.client.platform.version = "1.0"
        return msg
    def create_request(self) -> fbsp.Message:
        "Creates test REQUEST/1.1 message"
        return self._fbsp.create_request_for(1, 1, get_token(4))
    def test_hello(self):
        "HELLO message"
        expect = """Message type: HELLO
Flags: NONE
Type data: 0
Token: 1
Peer:
instance {
  uid: "c24bdd24-46be-11e9-8f39-5404a6a1fd6e"
  pid: 100
  host: "localhost"
}
client {
  uid: "c9cf8bcc-46be-11e9-8f39-5404a6a1fd6e"
  name: "Agent name"
  version: "1.0"
  vendor {
    uid: "a86ff2d2-73eb-593f-8b14-f2f7af0233d1"
  }
  platform {
    uid: "c26a6600-d579-5ec7-a9d6-5b0a8b214d3f"
    version: "1.0"
  }
}
# data frames: 0
==========
"""
        try:
            msg = self.create_hello()
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_welcome(self):
        "WELCOME message"
        expect = """Message type: WELCOME
Flags: NONE
Type data: 0
Token: 1
Peer:
instance {
  uid: "b69daa46-46c0-11e9-8f39-5404a6a1fd6e"
  pid: 100
  host: "localhost"
}
service {
  uid: "bcaabd34-46c0-11e9-8f39-5404a6a1fd6e"
  name: "Agent name"
  version: "1.0"
  vendor {
    uid: "a86ff2d2-73eb-593f-8b14-f2f7af0233d1"
  }
  platform {
    uid: "c26a6600-d579-5ec7-a9d6-5b0a8b214d3f"
    version: "1.0"
  }
}
api {
  number: 1
  uid: "7f7ffc56-66a2-11e9-b502-5404a6a1fd6e"
}
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_welcome_reply(self.create_hello())
            msg.peer.instance.uid = UUID('b69daa46-46c0-11e9-8f39-5404a6a1fd6e').bytes
            msg.peer.instance.pid = 100
            msg.peer.instance.host = "localhost"
            msg.peer.service.uid = UUID('bcaabd34-46c0-11e9-8f39-5404a6a1fd6e').bytes
            msg.peer.service.name = "Agent name"
            msg.peer.service.version = "1.0"
            msg.peer.service.vendor.uid = VENDOR_UID.bytes
            msg.peer.service.platform.uid = PLATFORM_UID.bytes
            msg.peer.service.platform.version = "1.0"
            api = msg.peer.api.add()
            api.number = 1
            api.uid = UUID('7f7ffc56-66a2-11e9-b502-5404a6a1fd6e').bytes

            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.CLIENT)
            parsed = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_noop(self):
        "NOOP message"
        expect = """Message type: NOOP
Flags: ACK_REQ
Type data: 0
Token: 3
# data frames: 0
==========
Message type: NOOP
Flags: ACK_REPLY
Type data: 0
Token: 3
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_message_for(fbsp.MsgType.NOOP, get_token(3),
                                                flags=fbsp.MsgFlag.ACK_REQ)
            self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            # ACK Response
            zmsg = self._fbsp.create_ack_reply(parsed).as_zmsg()
            self._fbsp.validate(zmsg, Origin.SERVICE)
            noop_reply = self._fbsp.parse(zmsg)
            self.print_msg(noop_reply)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_request(self):
        "REQUEST message"
        expect = """Message type: REQUEST
Flags: NONE
Type data: 257
Token: 4
Interface ID: 1
API code: 1
# data frames: 0
==========
"""
        try:
            msg = self.create_request()
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_reply(self):
        "REPLY message"
        expect = """Message type: REPLY
Flags: NONE
Type data: 257
Token: 4
Interface ID: 1
API code: 1
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_reply_for(self.create_request())
            #msg.abilities.can_repeat_messages = 1
            #with self.assertRaises(fbsp.InvalidMessageError):
                #self.check_msg(msg, Origin.CLIENT)
            parsed = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_data(self):
        "DATA message"
        expect = """Message type: DATA
Flags: NONE
Type data: 0
Token: 4
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_data_for(self.create_request())
            self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_cancel(self):
        "CANCEL message"
        expect = """Message type: CANCEL
Flags: NONE
Type data: 0
Token: 7
Cancel request:
token: "\\004\\000\\000\\000\\000\\000\\000\\000"
# data frames: 0
==========
"""
        try:
            msg: fbsp.CancelMessage = self._fbsp.create_message_for(fbsp.MsgType.CANCEL, get_token(7))

            msg.cancel_reqest.token = get_token(4)
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_state(self):
        "STATE message"
        expect = """Message type: STATE
Flags: NONE
Type data: 257
Token: 4
State: RUNNING
Interface ID: 1
API code: 1
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_state_for(self.create_request(), fbsp.fbsd_proto.STATE_RUNNING)
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.CLIENT)
            parsed: fbsp.StateMessage = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(parsed.state, fbsp.fbsd_proto.STATE_RUNNING)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_close(self):
        "CLOSE message"
        expect = """Message type: CLOSE
Flags: NONE
Type data: 0
Token: 1
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_message_for(fbsp.MsgType.CLOSE, get_token(1))
            self.check_msg(msg, Origin.SERVICE)
            parsed = self.check_msg(msg, Origin.CLIENT)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))
    def test_error(self):
        "ERROR message"
        expect = """Message type: ERROR
Flags: NONE
Type data: 132
Token: 4
Error code: NOT_IMPLEMENTED
Relates to: REQUEST
# Error frames: 1
@1:
code: 1
description: "Additional error description"
# data frames: 0
==========
"""
        try:
            msg = self._fbsp.create_error_for(self.create_request(),
                                              fbsp.ErrorCode.NOT_IMPLEMENTED)
            err = msg.add_error()
            err.code = 1
            err.description = "Additional error description"
            with self.assertRaises(fbsp.InvalidMessageError):
                self.check_msg(msg, Origin.CLIENT)
            parsed = self.check_msg(msg, Origin.SERVICE)
            self.print_msg(parsed)
            self.assertEqual(expect, self.out.getvalue())
        except fbsp.InvalidMessageError as exc:
            self.fail(str(exc))

if __name__ == '__main__':
    unittest.main()
