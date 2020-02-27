#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           test/t_config.py
# DESCRIPTION:    Unit tests for config
# CREATED:        20.9.2019
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

"Saturnin - Unit tests for config."

import unittest
from uuid import UUID
from decimal import Decimal
import io
from google.protobuf.struct_pb2 import Struct
from configparser import ConfigParser, ExtendedInterpolation
from saturnin.core.types import ZMQAddress, SocketType, SaturninError, ExecutionMode
from saturnin.core import config

DEFAULT_S = 'DEFAULT'
PRESENT_S = 'present'
ABSENT_S = 'absent'
BAD_S = 'bad_value'

class ValueHolder:
    "Simple values holding object"

def store_opt(d, o):
    d[o.name] = o

class TestConfig(unittest.TestCase):
    """Unit tests for saturnin.core.collection.ObjectList"""
    def setUp(self):
        self.proto: Struct = Struct()
        self.conf: ConfigParser = ConfigParser(interpolation=ExtendedInterpolation())
    def tearDown(self):
        pass
    def setConf(self, conf_str):
        self.conf.read_string(conf_str % {'DEFAULT': DEFAULT_S, 'PRESENT': PRESENT_S,
                                          'ABSENT': ABSENT_S, 'BAD': BAD_S,})
    def test_Option(self):
        self.setConf("""[%(DEFAULT)s]
option_name = DEFAULT_value
[%(PRESENT)s]
option_name = present_value
[%(ABSENT)s]
""")
        PRESENT_VAL = 'present_value'
        DEFAULT_VAL = 'DEFAULT_value'
        DEFAULT_OPT_VAL = 'DEFAULT'
        NEW_VAL = 'new_value'
        # Simple
        opt = config.Option('option_name', str, 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.Option('option_name', str, 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # Default
        opt = config.Option('option_name', str, 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # Proposal
        opt = config.Option('option_name', str, 'description', proposal="proposal")
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertEqual(opt.proposal, "proposal")
        self.assertIsNone(opt.value)
        opt.validate()
        # protobuf
        proto_value = 'proto_value'
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        self.proto.Clear()
        opt.clear()
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_StrOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = DEFAULT_value
[%(PRESENT)s]
option_name = present_value
   can be multiline
[%(ABSENT)s]
[%(BAD)s]
option_name =
""")
        PRESENT_VAL = 'present_value\ncan be multiline'
        DEFAULT_VAL = 'DEFAULT_value'
        DEFAULT_OPT_VAL = 'DEFAULT'
        NEW_VAL = 'new_value'
        # Simple
        opt = config.StrOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.StrOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, '')
        # Default
        opt = config.StrOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = 'proto_value'
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_IntOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = 10
[%(PRESENT)s]
option_name = 500
[%(ABSENT)s]
[%(BAD)s]
option_name = bad_value
""")
        PRESENT_VAL = 500
        DEFAULT_VAL = 10
        DEFAULT_OPT_VAL = 3000
        NEW_VAL = 0
        # Simple
        opt = config.IntOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, int)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.IntOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, int)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(TypeError):
            opt.load_from(self.conf, BAD_S)
        # Default
        opt = config.IntOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, int)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = 800000
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 'BAD VALUE'
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_FloatOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = 10.5
[%(PRESENT)s]
option_name = 500
[%(ABSENT)s]
[%(BAD)s]
option_name = bad_value
""")
        PRESENT_VAL = 500.0
        DEFAULT_VAL = 10.5
        DEFAULT_OPT_VAL = 3000.0
        NEW_VAL = 0.0
        # Simple
        opt = config.FloatOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, float)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.FloatOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, float)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(TypeError):
            opt.load_from(self.conf, BAD_S)
        # Default
        opt = config.FloatOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, float)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set int
        with self.assertRaises(TypeError):
            opt.set_value(10)
        with self.assertRaises(TypeError):
            opt.set_value(0)
        # protobuf
        proto_value = 800000.0
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 'BAD VALUE'
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_DecimalOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = 10.5
[%(PRESENT)s]
option_name = 500
[%(ABSENT)s]
[%(BAD)s]
option_name = bad_value
""")
        PRESENT_VAL = Decimal('500.0')
        DEFAULT_VAL = Decimal('10.5')
        DEFAULT_OPT_VAL = Decimal('3000.0')
        NEW_VAL = Decimal('0.0')
        # Simple
        opt = config.DecimalOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, Decimal)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.DecimalOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, Decimal)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        # Default
        opt = config.DecimalOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, Decimal)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set int
        with self.assertRaises(TypeError):
            opt.set_value(10)
        with self.assertRaises(TypeError):
            opt.set_value(0)
        # protobuf
        proto_value = Decimal('800000.0')
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = str(proto_value)
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 'BAD VALUE'
        with self.assertRaises(ValueError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_BoolOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = no
[%(PRESENT)s]
option_name = yes
[%(ABSENT)s]
[%(BAD)s]
option_name = bad_value
""")
        YES = True
        NO = False
        PRESENT_VAL = YES
        DEFAULT_VAL = NO
        DEFAULT_OPT_VAL = NO
        NEW_VAL = YES
        # Simple
        opt = config.BoolOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, bool)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.BoolOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, bool)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(TypeError):
            opt.load_from(self.conf, BAD_S)
        # Default
        opt = config.BoolOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, bool)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = YES
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 'BAD VALUE'
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = DEFAULT_value
[%(PRESENT)s]
option_name =
  present_value_1
  present_value_2
[%(ABSENT)s]
[%(BAD)s]
option_name =
""")
        DEFAULT_VAL = ['DEFAULT_value']
        PRESENT_VAL = ['present_value_1', 'present_value_2']
        DEFAULT_OPT_VAL = ['DEFAULT_1', 'DEFAULT_2', 'DEFAULT_3']
        NEW_VAL = ['NEW']
        # Simple
        opt = config.ListOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, [])
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOptionInt(self):
        self.setConf("""[%(DEFAULT)s]
option_name = 0
[%(PRESENT)s]
option_name = 10, 20
[%(ABSENT)s]
[%(BAD)s]
option_name = this is not an integer
""")
        DEFAULT_VAL = [0]
        PRESENT_VAL = [10, 20]
        DEFAULT_OPT_VAL = [1, 2, 3]
        NEW_VAL = [100]
        # Simple
        opt = config.ListOption('option_name', 'description', item_type='int')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True, item_type='int')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL,
                                item_type='int')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOptionFloat(self):
        self.setConf("""[%(DEFAULT)s]
option_name = 0.0
[%(PRESENT)s]
option_name = 10.1, 20.2
[%(ABSENT)s]
[%(BAD)s]
option_name = this is not a float
""")
        DEFAULT_VAL = [0.0]
        PRESENT_VAL = [10.1, 20.2]
        DEFAULT_OPT_VAL = [1.11, 2.22, 3.33]
        NEW_VAL = [100.101]
        # Simple
        opt = config.ListOption('option_name', 'description', item_type='float')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True, item_type='float')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL,
                                item_type='float')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOptionDecimal(self):
        self.setConf("""[%(DEFAULT)s]
option_name = 0.0
[%(PRESENT)s]
option_name = 10.1, 20.2
[%(ABSENT)s]
[%(BAD)s]
option_name = this is not a decimal
""")
        DEFAULT_VAL = [Decimal('0.0')]
        PRESENT_VAL = [Decimal('10.1'), Decimal('20.2')]
        DEFAULT_OPT_VAL = [Decimal('1.11'), Decimal('2.22'), Decimal('3.33')]
        NEW_VAL = [Decimal('100.101')]
        # Simple
        opt = config.ListOption('option_name', 'description', item_type='decimal')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True, item_type='decimal')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL,
                                item_type='decimal')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOptionBool(self):
        self.setConf("""[%(DEFAULT)s]
option_name = 0
[%(PRESENT)s]
option_name = yes, no
[%(ABSENT)s]
[%(BAD)s]
option_name = this is not a bool
""")
        DEFAULT_VAL = [0]
        PRESENT_VAL = [True, False]
        DEFAULT_OPT_VAL = [True, False, True]
        NEW_VAL = [True]
        # Simple
        opt = config.ListOption('option_name', 'description', item_type='bool')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True, item_type='bool')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL,
                                item_type='bool')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOptionUUID(self):
        self.setConf("""[%(DEFAULT)s]
option_name = eeb7f94a-256d-11ea-ad1d-5404a6a1fd6e
[%(PRESENT)s]
option_name = 0a7fd53a256e11eaad1d5404a6a1fd6e, 0551feb2-256e-11ea-ad1d-5404a6a1fd6e
[%(ABSENT)s]
[%(BAD)s]
option_name = this is not an uuid
""")
        DEFAULT_VAL = [UUID('eeb7f94a-256d-11ea-ad1d-5404a6a1fd6e')]
        PRESENT_VAL = [UUID('0a7fd53a-256e-11ea-ad1d-5404a6a1fd6e'),
                       UUID('0551feb2-256e-11ea-ad1d-5404a6a1fd6e')]
        DEFAULT_OPT_VAL = [UUID('2f02868c-256e-11ea-ad1d-5404a6a1fd6e'),
                           UUID('3521db30-256e-11ea-ad1d-5404a6a1fd6e'),
                           UUID('3a3e68cc-256e-11ea-ad1d-5404a6a1fd6e')]
        NEW_VAL = [UUID('3e8a4ce8-256e-11ea-ad1d-5404a6a1fd6e')]
        # Simple
        opt = config.ListOption('option_name', 'description', item_type='uuid')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True, item_type='uuid')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL,
                                item_type='uuid')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOptionMIME(self):
        self.setConf("""[%(DEFAULT)s]
option_name = application/octet-stream
[%(PRESENT)s]
option_name =
    text/plain;charset=utf-8
    text/csv
[%(ABSENT)s]
[%(BAD)s]
option_name = wrong mime specification
""")
        DEFAULT_VAL = [config.parse_mime('application/octet-stream')]

        PRESENT_VAL = [config.parse_mime('text/plain;charset=utf-8'),
                       config.parse_mime('text/csv')]
        DEFAULT_OPT_VAL = [config.parse_mime('text/html;charset=utf-8'),
                           config.parse_mime('video/mp4'),
                           config.parse_mime('image/png')]
        NEW_VAL = [config.parse_mime('audio/mpeg')]
        # Simple
        opt = config.ListOption('option_name', 'description', item_type='mime', separator='\n')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True,
                                item_type='mime', separator='\n')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL,
                                item_type='mime', separator='\n')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOptionZMQAddress(self):
        self.setConf("""[%(DEFAULT)s]
option_name = tcp://127.0.0.1:*
[%(PRESENT)s]
option_name = ipc://@my-address, inproc://my-address, tcp://127.0.0.1:9001
[%(ABSENT)s]
[%(BAD)s]
option_name = bad_value
""")
        DEFAULT_VAL = [ZMQAddress('tcp://127.0.0.1:*')]
        PRESENT_VAL = [ZMQAddress('ipc://@my-address'),
                       ZMQAddress('inproc://my-address'),
                       ZMQAddress('tcp://127.0.0.1:9001')]
        DEFAULT_OPT_VAL = [ZMQAddress('tcp://127.0.0.1:8001')]
        NEW_VAL = [ZMQAddress('inproc://my-address')]
        # Simple
        opt = config.ListOption('option_name', 'description', item_type='ZMQAddress')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True, item_type='ZMQAddress')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL,
                                item_type='ZMQAddress')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ListOptionMulti(self):
        self.setConf("""[%(DEFAULT)s]
option_name = str:DEFAULT_value
[%(PRESENT)s]
option_name =
    int: 1
    float: 1.1
    decimal: 1.01
    bool: yes
    uuid: eeb7f94a-256d-11ea-ad1d-5404a6a1fd6e
    mime: application/octet-stream
    ZMQAddress: tcp://127.0.0.1:*
[%(ABSENT)s]
[%(BAD)s]
option_name =
""")
        DEFAULT_VAL = ['DEFAULT_value']
        PRESENT_VAL = [1, 1.1, Decimal('1.01'), True,
                       UUID('eeb7f94a-256d-11ea-ad1d-5404a6a1fd6e'),
                       config.parse_mime('application/octet-stream'),
                       ZMQAddress('tcp://127.0.0.1:*')]
        DEFAULT_OPT_VAL = ['DEFAULT_1', 1, False]
        NEW_VAL = [config.parse_mime('text/plain;charset=utf-8')]
        # Simple
        opt = config.ListOption('option_name', 'description', item_type=None,
                                separator='\n')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ListOption('option_name', 'description', required=True, item_type=None,
                                separator='\n')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, [])
        # Default
        opt = config.ListOption('option_name', 'description', default=DEFAULT_OPT_VAL,
                                item_type=None, separator='\n')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ['proto_value_1', 'proto_value_2']
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ZMQAddressOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = tcp://127.0.0.1:*
[%(PRESENT)s]
option_name = ipc://@my-address
[%(ABSENT)s]
[%(BAD)s]
option_name = bad_value
""")
        PRESENT_VAL = ZMQAddress('ipc://@my-address')
        DEFAULT_VAL = ZMQAddress('tcp://127.0.0.1:*')
        DEFAULT_OPT_VAL = ZMQAddress('tcp://127.0.0.1:8001')
        NEW_VAL = ZMQAddress('inproc://my-address')
        # Simple
        opt = config.ZMQAddressOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, ZMQAddress)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ZMQAddressOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, ZMQAddress)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        # Default
        opt = config.ZMQAddressOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, ZMQAddress)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = ZMQAddress('inproc://proto-address')
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ZMQAddressListOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = tcp://127.0.0.1:*
[%(PRESENT)s]
option_name = ipc://@my-address, tcp://127.0.0.1:5001
[%(ABSENT)s]
[%(BAD)s]
option_name = bad_value
""")
        PRESENT_VAL = [ZMQAddress('ipc://@my-address'), ZMQAddress('tcp://127.0.0.1:5001')]
        DEFAULT_VAL = [ZMQAddress('tcp://127.0.0.1:*')]
        DEFAULT_OPT_VAL = [ZMQAddress('tcp://127.0.0.1:8001')]
        NEW_VAL = [ZMQAddress('inproc://my-address')]
        # Simple
        opt = config.ZMQAddressListOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.ZMQAddressListOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        # Default
        opt = config.ZMQAddressListOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, list)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = [ZMQAddress('inproc://proto-address')]
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_EnumOption(self):
        self.setConf("""[%(DEFAULT)s]
; Enum could be defined by number or by name
option_name = 1
[%(PRESENT)s]
; case does not matter
option_name = rOuTeR
[%(ABSENT)s]
[%(BAD)s]
option_name = bad_value
""")
        DEFAULT_VAL = SocketType.DEALER
        PRESENT_VAL = SocketType.ROUTER
        DEFAULT_OPT_VAL = SocketType.PUSH
        NEW_VAL = SocketType.PULL
        # Simple
        opt = config.EnumOption('option_name', SocketType, 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, SocketType)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        self.assertSequenceEqual(opt.options, SocketType)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.EnumOption('option_name', SocketType, 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, SocketType)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        # Allowed options
        opt = config.EnumOption('option_name', SocketType, 'description',
                                options=[SocketType.DEALER, SocketType.ROUTER])
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, SocketType)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        with self.assertRaises(ValueError):
            opt.set_value(NEW_VAL)
        # Default
        opt = config.EnumOption('option_name', SocketType, 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, SocketType)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value('BAD VALUE')
        # protobuf
        proto_value = SocketType.PUSH
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(ValueError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_UUIDOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = e3a57070-de0d-11e9-9b5b-5404a6a1fd6e
[%(PRESENT)s]
; as hex
option_name = fbcdd0acde0d11e99b5b5404a6a1fd6e
[%(ABSENT)s]
[%(BAD)s]
option_name = BAD_UID
""")
        PRESENT_VAL = UUID('fbcdd0ac-de0d-11e9-9b5b-5404a6a1fd6e')
        DEFAULT_VAL = UUID('e3a57070-de0d-11e9-9b5b-5404a6a1fd6e')
        DEFAULT_OPT_VAL = UUID('ede5cc42-de0d-11e9-9b5b-5404a6a1fd6e')
        NEW_VAL = UUID('92ef5c08-de0e-11e9-9b5b-5404a6a1fd6e')
        # Simple
        opt = config.UUIDOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, UUID)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.UUIDOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, UUID)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        # Default
        opt = config.UUIDOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, UUID)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = UUID('bcd80916-de0e-11e9-9b5b-5404a6a1fd6e')
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value.hex
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_MIMEOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = application/octet-stream
[%(PRESENT)s]
option_name = text/plain;charset=utf-8
[%(ABSENT)s]
[%(BAD)s]
option_name = wrong mime specification
""")
        PRESENT_VAL = 'text/plain;charset=utf-8'
        PRESENT_TYPE = 'text/plain'
        PRESENT_PARS = {'charset': 'utf-8'}
        DEFAULT_VAL = 'application/octet-stream'
        DEFAULT_TYPE = 'application/octet-stream'
        DEFAULT_PARS = {}
        DEFAULT_OPT_VAL = 'text/plain;charset=win1250'
        DEFAULT_OPT_TYPE = 'text/plain'
        DEFAULT_OPT_PARS = {'charset': 'win1250'}
        NEW_VAL = 'application/x.fb.proto;type=firebird.butler.fbsd.ErrorDescription'
        NEW_TYPE = 'application/x.fb.proto'
        NEW_PARS = {'type': 'firebird.butler.fbsd.ErrorDescription'}
        # Simple
        opt: config.MIMEOption = config.MIMEOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        self.assertIsNone(opt.mime_type)
        self.assertSequenceEqual(opt.mime_params, [])
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        self.assertEqual(opt.mime_type, PRESENT_TYPE)
        self.assertSequenceEqual(opt.mime_params, PRESENT_PARS.items())
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        self.assertEqual(opt.mime_type, DEFAULT_TYPE)
        self.assertSequenceEqual(opt.mime_params, DEFAULT_PARS.items())
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        self.assertEqual(opt.mime_type, DEFAULT_TYPE)
        self.assertSequenceEqual(opt.mime_params, DEFAULT_PARS.items())
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        self.assertEqual(opt.mime_type, NEW_TYPE)
        self.assertSequenceEqual(opt.mime_params, NEW_PARS.items())
        # Required
        opt = config.MIMEOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertEqual(opt.mime_type, PRESENT_TYPE)
        self.assertSequenceEqual(opt.mime_params, PRESENT_PARS.items())
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertEqual(opt.mime_type, DEFAULT_TYPE)
        self.assertSequenceEqual(opt.mime_params, DEFAULT_PARS.items())
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertEqual(opt.mime_type, DEFAULT_TYPE)
        self.assertSequenceEqual(opt.mime_params, DEFAULT_PARS.items())
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertEqual(opt.mime_type, NEW_TYPE)
        self.assertSequenceEqual(opt.mime_params, NEW_PARS.items())
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        # Default
        opt = config.MIMEOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        self.assertEqual(opt.mime_type, DEFAULT_OPT_TYPE)
        self.assertSequenceEqual(opt.mime_params, DEFAULT_OPT_PARS.items())
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertEqual(opt.mime_type, PRESENT_TYPE)
        self.assertSequenceEqual(opt.mime_params, PRESENT_PARS.items())
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertEqual(opt.mime_type, DEFAULT_TYPE)
        self.assertSequenceEqual(opt.mime_params, DEFAULT_PARS.items())
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertEqual(opt.mime_type, DEFAULT_TYPE)
        self.assertSequenceEqual(opt.mime_params, DEFAULT_PARS.items())
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertEqual(opt.mime_type, NEW_TYPE)
        self.assertSequenceEqual(opt.mime_params, NEW_PARS.items())
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = NEW_VAL
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertEqual(opt.mime_type, NEW_TYPE)
        self.assertSequenceEqual(opt.mime_params, NEW_PARS.items())
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_PyExprOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = this.value is None
[%(PRESENT)s]
option_name = this.value in [1, 2, 3]
[%(ABSENT)s]
[%(BAD)s]
option_name = This is not a valid Python expression
""")
        PRESENT_VAL = 'this.value in [1, 2, 3]'
        DEFAULT_VAL = 'this.value is None'
        DEFAULT_OPT_VAL = 'DEFAULT'
        NEW_VAL = 'this.value == "VALUE"'
        # Simple
        opt = config.PyExprOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Check expression code
        obj = ValueHolder()
        obj.value = "VALUE"
        self.assertTrue(eval(opt.get_expr(), {'this': obj}))
        fce = opt.get_callable('this')
        self.assertTrue(fce(obj))
        obj.value = "OTHER VALUE"
        self.assertFalse(eval(opt.get_expr(), {'this': obj}))
        self.assertFalse(fce(obj))
        # Required
        opt = config.PyExprOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(SyntaxError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.PyExprOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = 'proto_value'
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_PyCodeOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name = print("Default value")
[%(PRESENT)s]
option_name =
    | def pp(value):
    |     print("Value:",value,file=output)
    |
    | for i in [1,2,3]:
    |     pp(i)
[%(ABSENT)s]
[%(BAD)s]
option_name = This is not a valid Python expression
""")
        DEFAULT_VAL = 'print("Default value")'
        PRESENT_VAL = '\ndef pp(value):\n    print("Value:",value,file=output)\n\nfor i in [1,2,3]:\n    pp(i)'
        DEFAULT_OPT_VAL = 'DEFAULT'
        NEW_VAL = 'print("NEW value")'
        # Simple
        opt = config.PyCodeOption('option_name', 'description')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Check expression code
        out = io.StringIO()
        code = opt.get_code()
        exec(code, {'output': out})
        self.assertEqual(out.getvalue(), 'Value: 1\nValue: 2\nValue: 3\n')
        #
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.PyCodeOption('option_name', 'description', required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(SyntaxError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.PyCodeOption('option_name', 'description', default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = 'proto_value'
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_PyCallableOption(self):
        self.setConf("""[%(DEFAULT)s]
option_name =
    | def foo(value):
    |     return value * 2
[%(PRESENT)s]
option_name =
    | def foo(value):
    |     return value * 5
[%(ABSENT)s]
[%(BAD)s]
option_name = This is not a valid Python function/procedure definition
""")
        DEFAULT_VAL = '\ndef foo(value):\n    return value * 2'
        PRESENT_VAL = '\ndef foo(value):\n    return value * 5'
        DEFAULT_OPT_VAL = 'DEFAULT'
        NEW_VAL = '\ndef foo(value):\n    return value * 3'
        # Simple
        opt = config.PyCallableOption('option_name', 'description', 'value')
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Check expression code
        call = opt.get_callable()
        self.assertEqual(call(1), 5)
        #
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        # Required
        opt = config.PyCallableOption('option_name', 'description', 'value',
                                      required=True)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertTrue(opt.required)
        self.assertIsNone(opt.default)
        self.assertIsNone(opt.proposal)
        self.assertIsNone(opt.value)
        with self.assertRaises(SaturninError):
            opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.validate()
        opt.clear()
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # BAD value
        with self.assertRaises(ValueError):
            opt.load_from(self.conf, BAD_S)
        self.assertEqual(opt.value, NEW_VAL) # The value should not change
        # Default
        opt = config.PyCallableOption('option_name', 'description', 'value',
                                      default=DEFAULT_OPT_VAL)
        self.assertEqual(opt.name, 'option_name')
        self.assertEqual(opt.datatype, str)
        self.assertEqual(opt.description, 'description')
        self.assertFalse(opt.required)
        self.assertEqual(opt.default, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.default, opt.datatype)
        self.assertIsNone(opt.proposal)
        self.assertEqual(opt.value, DEFAULT_OPT_VAL)
        self.assertIsInstance(opt.value, opt.datatype)
        opt.validate()
        opt.load_from(self.conf, PRESENT_S)
        self.assertEqual(opt.value, PRESENT_VAL)
        opt.clear()
        self.assertEqual(opt.value, opt.default)
        opt.load_from(self.conf, DEFAULT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(None)
        self.assertIsNone(opt.value)
        opt.load_from(self.conf, ABSENT_S)
        self.assertEqual(opt.value, DEFAULT_VAL)
        opt.set_value(NEW_VAL)
        self.assertEqual(opt.value, NEW_VAL)
        # set float
        with self.assertRaises(TypeError):
            opt.set_value(10.0)
        # protobuf
        proto_value = 'def foo(value):\n    return value * 100'
        opt.clear()
        opt.set_value(proto_value)
        self.proto['option_name'] = proto_value
        proto_dump = str(self.proto)
        opt.load_proto(self.proto)
        self.assertEqual(opt.value, proto_value)
        self.assertIsInstance(opt.value, opt.datatype)
        self.proto.Clear()
        self.assertFalse('option_name' in self.proto)
        opt.save_proto(self.proto)
        self.assertTrue('option_name' in self.proto)
        self.assertEqual(str(self.proto), proto_dump)
        # empty proto
        opt.clear(False)
        self.proto.Clear()
        opt.load_proto(self.proto)
        self.assertIsNone(opt.value)
        # bad proto value
        self.proto['option_name'] = 1000
        with self.assertRaises(TypeError):
            opt.load_proto(self.proto)
        self.proto.Clear()
        opt.clear(False)
        opt.save_proto(self.proto)
        self.assertFalse('option_name' in self.proto)
    def test_ConfigOption(self):
        pass
    def test_ConfigListOption(self):
        pass
    def test_Config(self):
        self.setConf("""[%(PRESENT)s]
str_option = present_value
int_option = 500
float_option = 10.5
bool_option = yes
str_list_option = item 1, item_2, item 3
zaddr_option = tcp://127.0.0.1:*
zaddr_list_option = ipc://@my-addr, tcp://127.0.0.1:*
enum_option = router
uuid_option = e3a57070-de0d-11e9-9b5b-5404a6a1fd6e
""")
        OPT_STR = 'str_option'
        OPT_INT = 'int_option'
        OPT_FLOAT = 'float_option'
        OPT_BOOL = 'bool_option'
        OPT_STR_LIST = 'str_list_option'
        OPT_ZMQADDR = 'zaddr_option'
        OPT_ZMQADDR_LIST = 'zaddr_list_option'
        OPT_ENUM = 'enum_option'
        OPT_UUID = 'uuid_option'
        VALUES = {OPT_STR: 'present_value',
                  OPT_INT: 500,
                  OPT_FLOAT: 10.5,
                  OPT_BOOL: True,
                  OPT_STR_LIST: ['item 1', 'item_2', 'item 3'],
                  OPT_ZMQADDR: ZMQAddress('tcp://127.0.0.1:*'),
                  OPT_ZMQADDR_LIST: [ZMQAddress('ipc://@my-addr'),
                                     ZMQAddress('tcp://127.0.0.1:*')],
                  OPT_ENUM: SocketType.ROUTER,
                  OPT_UUID: UUID('e3a57070-de0d-11e9-9b5b-5404a6a1fd6e'),
                  }
        OPTIONS = {}
        store_opt(OPTIONS, config.StrOption(OPT_STR, 'description'))
        store_opt(OPTIONS, config.IntOption(OPT_INT, 'description'))
        store_opt(OPTIONS, config.FloatOption(OPT_FLOAT, 'description'))
        store_opt(OPTIONS, config.BoolOption(OPT_BOOL, 'description'))
        store_opt(OPTIONS, config.ListOption(OPT_STR_LIST, 'description'))
        store_opt(OPTIONS, config.ZMQAddressOption(OPT_ZMQADDR, 'description'))
        store_opt(OPTIONS, config.ZMQAddressListOption(OPT_ZMQADDR_LIST, 'description'))
        store_opt(OPTIONS, config.EnumOption(OPT_ENUM, SocketType, 'description'))
        store_opt(OPTIONS, config.UUIDOption(OPT_UUID, 'description'))
        #
        cfg = config.Config('config_name', "config description")
        for opt in OPTIONS.values():
            setattr(cfg, opt.name, opt)
        #
        self.assertListEqual(cfg.options, list(OPTIONS.values()))
        for opt in cfg.options:
            self.assertIn(opt.name, OPTIONS)
            self.assertIsInstance(opt, config.Option)
            self.assertIsNone(opt.value)
        #
        cfg.load_from(self.conf, PRESENT_S)
        for opt in cfg.options:
            self.assertEqual(VALUES[opt.name], opt.value)
        # protobuf
        cfg.clear()
        for opt_name, value in VALUES.items():
            if opt_name == OPT_UUID:
                self.proto[opt_name] = value.hex
            else:
                self.proto[opt_name] = value
        proto_dump = str(self.proto)
        #
        cfg.load_proto(self.proto)
        for opt in cfg.options:
            self.assertEqual(VALUES[opt.name], opt.value)
        #
        self.proto.Clear()
        cfg.save_proto(self.proto)
        self.assertEqual(str(self.proto), proto_dump)
    def test_MicroserviceConfig(self):
        cfg = config.MicroserviceConfig('microservice', 'description')
        self.assertTrue(hasattr(cfg, 'execution_mode'))
        self.assertIsInstance(cfg.execution_mode, config.EnumOption)
        self.assertEqual(cfg.execution_mode.value, ExecutionMode.THREAD)
    def test_ServiceConfig(self):
        cfg = config.ServiceConfig('service', 'description')
        self.assertTrue(hasattr(cfg, 'execution_mode'))
        self.assertIn('execution_mode', vars(cfg))
        self.assertIsInstance(cfg.execution_mode, config.EnumOption)
        self.assertEqual(cfg.execution_mode.value, ExecutionMode.THREAD)
        #
        self.assertTrue(hasattr(cfg, 'endpoints'))
        self.assertIn('endpoints', vars(cfg))
        self.assertIsInstance(cfg.endpoints, config.ZMQAddressListOption)
        self.assertIsNone(cfg.endpoints.value)
