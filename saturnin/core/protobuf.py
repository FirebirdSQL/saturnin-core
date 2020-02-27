#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/protobuf.py
# DESCRIPTION:    Saturnin registry for Google Protocol Buffer message handlers
# CREATED:        27.12.2019
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

"""Saturnin - Saturnin registry for Google Protocol Buffer message handlers
"""

import typing as t
from pkg_resources import iter_entry_points
from google.protobuf.descriptor import EnumDescriptor
from .types import Distinct, dataclass, SaturninError
from .collections import Registry

# Classes

@dataclass(eq=True, order=True, frozen=True)
class ProtoMessageType(Distinct):
    """Google protobuf message type"""
    name: str
    constructor: t.Callable
    def get_key(self) -> t.Any:
        """Returns `name`."""
        return self.name

@dataclass(eq=True, order=True, frozen=True)
class ProtoEnumType(Distinct):
    """Google protobuf enum type"""
    descriptor: EnumDescriptor
    def get_key(self) -> t.Any:
        """Returns `name`."""
        return self.name
    def __getattr__(self, name):
        """Returns the value corresponding to the given enum name."""
        if name in self.descriptor.values_by_name:
            return self.descriptor.values_by_name[name].number
        raise AttributeError
    def keys(self):
        """Return a list of the string names in the enum.

These are returned in the order they were defined in the .proto file.
"""
        return [value_descriptor.name
            for value_descriptor in self.descriptor.values]
    def values(self):
        """Return a list of the integer values in the enum.

These are returned in the order they were defined in the .proto file.
"""
        return [value_descriptor.number
            for value_descriptor in self.descriptor.values]
    def items(self):
        """Return a list of the (name, value) pairs of the enum.

These are returned in the order they were defined in the .proto file.
"""
        return [(value_descriptor.name, value_descriptor.number)
            for value_descriptor in self.descriptor.values]
    def get_value_name(self, number: int) -> str:
        """Returns a string containing the name of an enum value."""
        if number in self.descriptor.values_by_number:
            return self.descriptor.values_by_number[number].name
        raise ValueError(f"Enum {self.descriptor.name} has no name defined for value {number}")
    name = property(lambda self: self.descriptor.full_name)
        
_msgreg = Registry()
_enumreg = Registry()

def create_message(name: str) -> t.Any:
    """Returns protobuf message instance of specified `name`."""
    msg: ProtoMessageType = _msgreg.get(name)
    if msg is None:
        raise SaturninError(f"Unregistered protobuf message '{name}'")
    return msg.constructor()

def is_msg_registered(name: str) -> bool:
    """Returns True if specified `name` refers to registered protobuf message type"""
    return name in _msgreg

def is_enum_registered(name: str) -> bool:
    """Returns True if specified `name` refers to registered protobuf enum type"""
    return name in _enumreg

def get_enum_type(name: str) -> ProtoEnumType:
    """Returns wrapper instance for protobuf enum type with specified `name`."""
    e: ProtoEnumType = _enumreg.get(name)
    if e is None:
        raise SaturninError(f"Unregistered protobuf enum type '{name}'")
    return e

def get_enum_field_type(msg, field_name: str) -> str:
    """Returns name of enum type for message enum field"""
    fdesc = msg.DESCRIPTOR.fields_by_name.get(field_name)
    if fdesc is None:
        raise SaturninError(f"Message does not have field '{field_name}'")
    return fdesc.enum_type.full_name

def get_enum_value_name(enum_type_name: str, value: t.Any) -> str:
    """Returns name for the enum value"""
    enum = get_enum_type(enum_type_name)
    if enum is None:
        raise SaturninError(f"Unknown enum type '{enum_type_name}'")
    return enum.get_value_name(value)

# Load registered protobuf packages
for desc in (entry.load() for entry in iter_entry_points('firebird.butler.protobuf')):
    for msg_desc in desc.message_types_by_name.values():
        _msgreg.store(ProtoMessageType(msg_desc.full_name, msg_desc._concrete_class))
    for enum_desc in desc.enum_types_by_name.values():
        _enumreg.store(ProtoEnumType(enum_desc))
