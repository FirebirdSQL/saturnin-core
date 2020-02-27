#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/config.py
# DESCRIPTION:    Classes for configuration definitions
# CREATED:        27.8.2019
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

"""Saturnin - Classes for configuration definitions"""

import typing as t
import uuid
import decimal
import configparser
from .types import Enum, ZMQAddress, ZMQAddressList, TStringList, ExecutionMode, \
     SocketMode, SaturninError
from google.protobuf.struct_pb2 import Struct, ListValue
import datetime

# Types

TOnValidate = t.Callable[['Config'], None]
TMIMESpec = t.Tuple[t.Optional[str], t.Dict[str, str]]

# Functions

def parse_mime(mime_spec: str) -> TMIMESpec:
    """Parses mime type specification.

Arguments:
    mime_spec: mime type specification in format 'type/subtype[;param=value;...]'

Returns:
    Tuple (mime_type, mime_params)

Raises:
    ValueError: When value does not contain valid MIME specification
"""
    mime_type = None
    mime_params = {}
    if mime_spec:
        dfm = [x.strip() for x in mime_spec.split(';')]
        mime_type: str = dfm.pop(0).lower()
        try:
            main, subtype = mime_type.split('/')
        except:
            raise ValueError("MIME type specification must be 'type/subtype[;param=value;...]'")
        if main not in ['text', 'image', 'audio', 'video', 'application', 'multipart', 'message']:
            raise ValueError(f"MIME type '{main}' not supported")
        try:
            mime_params = dict((k.strip(), v.strip()) for k, v
                                            in (x.split('=') for x in dfm))
        except:
            raise ValueError("Wrong specification of MIME type parameters")
    return (mime_type, mime_params)

# Classes

class Option:
    """Configuration option (with string value).

Attributes:
    name:        Option name.
    datatype:    Option datatype [Any].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value [default: False].
    default:     Default value [default: None].
    proposal:    Text with proposed configuration entry value (if it's different from default)
                 [default: None].
    value:       Current option value.
"""
    def __init__(self, name: str, datatype: t.Type, description: str, required: bool = False,
                 default: t.Any = None, proposal: str = None):
        assert datatype is not None, "datatype required"
        assert default is None or isinstance(default, datatype)
        self.name: str = name
        self.datatype: t.Type = datatype
        self.description: str = description
        self.required: bool = required
        self.default: t.Any = default
        self.proposal: str = proposal
        self._value: t.Any = default
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    value: New option value.

Raises:
    TypeError: When the new value is of the wrong type.
"""
        if value is None:
            self.clear(False)
        else:
            if not isinstance(value, self.datatype):
                raise TypeError(f"Option '{self.name}' value must be a "
                                f"'{self.datatype.__name__}',"
                                f" not '{type(value).__name__}'")
            self._value = value
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout. The default implemenetation returns
`str(value)`.

Arguments:
   value: Value that is not None and has option datatype.
"""
        return str(value)
    def clear(self, to_default: bool = True) -> None:
        """Clears the option value.

Arguments:
    to_default: If True, sets the option value to default value, else to None.
"""
        self._value = self.default if to_default else None
    def get_as_str(self):
        """Returns value as string suitable for reading."""
        return '<UNDEFINED>' if self.value is None else self._format_value(self.value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            self.set_value(value)
    def validate(self) -> None:
        """Validates option value.

Raises:
    SaturninError: For incorrect option value.
"""
        if self.required and self.value is None:
            raise SaturninError(f"The configuration does not define a value for"
                                f" the required option '{self.name}'")
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            self.set_value(proto[self.name])
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto[self.name] = self.value
    def get_printout(self) -> str:
        """Return option printout in 'name = value' format."""
        return '%s = %s' % (self.name, self.get_as_str())
    value = property(lambda self: self._value, doc="Option value")

class StrOption(Option):
    """Configuration option with string value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [str].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: str = None, proposal: str = None):
        super().__init__(name, str, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        result = value
        if '\n' in result:
            lines = []
            for line in result.splitlines(True):
                if lines:
                    lines.append('  ' + line)
                else:
                    lines.append(line)
            result = ''.join(lines)
        return result
    value: str = property(lambda self: self._value, doc="Option value")

class IntOption(Option):
    """Configuration option with integer value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [int]
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: int = None, proposal: str = None):
        super().__init__(name, int, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return str(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        try:
            value = config.getint(section, self.name, vars=vars_, fallback=None)
        except ValueError as exc:
            raise TypeError(f"Option '{self.name}' value must be a "
                            f"'{self.datatype.__name__}'") from exc
        if value is not None:
            self.set_value(value)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, float):
                value = int(value)
            # We intentionally send value of wrong type to set_value() for error report
            self.set_value(value)
    value: int = property(lambda self: self._value, doc="Option value")

class FloatOption(Option):
    """Configuration option with float value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [float].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: float = None, proposal: str = None):
        super().__init__(name, float, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return str(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        try:
            value = config.getfloat(section, self.name, vars=vars_, fallback=None)
        except ValueError as exc:
            raise TypeError(f"Option '{self.name}' value must be a "
                            f"'{self.datatype.__name__}'") from exc
        if value is not None:
            self.set_value(value)
    value: float = property(lambda self: self._value, doc="Option value")

class DecimalOption(Option):
    """Configuration option with decimal.Decimal value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [decimal.Decimal].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: decimal.Decimal = None, proposal: str = None):
        super().__init__(name, decimal.Decimal, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return str(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        try:
            value = config.get(section, self.name, vars=vars_, fallback=None)
        except ValueError as exc:
            raise TypeError(f"Option '{self.name}' value must be a "
                            f"'{self.datatype.__name__}'") from exc
        if value is not None:
            try:
                self.set_value(decimal.Decimal(value))
            except decimal.DecimalException as exc:
                raise ValueError(str(exc))
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            try:
                self.set_value(decimal.Decimal(proto[self.name]))
            except decimal.DecimalException as exc:
                raise ValueError(str(exc))
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto[self.name] = str(self.value)
    value: decimal.Decimal = property(lambda self: self._value, doc="Option value")

class BoolOption(Option):
    """Configuration option with boolean value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [bool].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: bool = None, proposal: str = None):
        super().__init__(name, bool, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return 'yes' if value else 'no'
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        try:
            value = config.getboolean(section, self.name, vars=vars_, fallback=None)
        except ValueError as exc:
            raise TypeError(f"Option '{self.name}' value must be a "
                            f"'{self.datatype.__name__}'") from exc
        if value is not None:
            self.set_value(value)
    value: bool = property(lambda self: self._value, doc="Option value")

class ListOption(Option):
    """Configuration option with list of values.

Attributes:
    name:        Option name.
    datatype:    Option datatype [list].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
    item_type:   Datatype of list items as string type name. Value `None` means that each
                 item could have different datatype. In such a case each value in config
                 file must have format: `type_name:value_as_str`
    separator:   String that separates values when options value is readed from configparser.
                 Default separator is None. It's possible to use a line break as separator.
                 If separator is None and the value contains line breaks, it uses
                 the line break as separator, otherwise it uses comma as separator.
    ITEM_TYPES:  Supported data types: str, int, float, decimal, bool, uuid, mime, ZMQAddress
    BOOLEAN_STATES: Supported boolean states: 0, 1, yes, no, true, false, on, off

Important:
    When option is read from ConfigParser, empty values are ignored.
"""
    ITEM_TYPES = ['str', 'int', 'float', 'decimal', 'bool', 'uuid', 'mime', 'ZMQAddress',
                  None]
    BOOLEAN_STATES = {'1': True, 'yes': True, 'true': True, 'on': True,
                      '0': False, 'no': False, 'false': False, 'off': False}
    def __init__(self, name: str, description: str, required: bool = False,
                 default: list = None, proposal: str = None, item_type: str = 'str',
                 separator: t.Optional[str] = None):
        assert item_type in self.ITEM_TYPES
        super().__init__(name, list, description, required, default, proposal)
        self.item_type: str = item_type
        self.separator: t.Optional[str] = separator
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        sep = self.separator
        sep += '    ' if self.separator == '\n' else ' '
        return sep.join(value)
    def _convert_str(self, value) -> str:
        """Converts value to str"""
        return str(value)
    def _convert_int(self, value) -> int:
        """Converts value to int"""
        return int(value)
    def _convert_float(self, value) -> float:
        """Converts value to float"""
        return float(value)
    def _convert_decimal(self, value) -> decimal.Decimal:
        """Converts value to decimal"""
        try:
            val = decimal.Decimal(value)
        except decimal.DecimalException as exc:
            raise ValueError(str(exc))
        return val
    def _convert_bool(self, value) -> bool:
        """Converts value to bool"""
        if value.lower() not in self.BOOLEAN_STATES:
            raise ValueError('Not a boolean: %s' % value)
        return self.BOOLEAN_STATES[value.lower()]
    def _convert_uuid(self, value) -> uuid.UUID:
        """Converts value to uuid"""
        return uuid.UUID(value)
    def _convert_mime(self, value) -> TMIMESpec:
        """Converts value to mime"""
        return parse_mime(value)
    def _convert_ZMQAddress(self, value) -> ZMQAddress:
        """Converts value to ZMQAddress"""
        return ZMQAddress(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            if value.strip():
                items = []
                if self.separator is None:
                    self.separator = '\n' if '\n' in value else ','
                separator = self.separator
                for item in (i for i in value.split(separator) if i.strip()):
                    if self.item_type is None:
                        itype, item = item.split(':', 1)
                    else:
                        itype = self.item_type
                    converter = getattr(self, '_convert_' + itype.strip())
                    items.append(converter(item.strip()))
                self.set_value(items)
            else:
                self.set_value([])
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, ListValue):
                self.set_value(list(value))
            else:
                raise TypeError(f"Option '{self.name}' value must be a "
                                f"'{self.datatype.__name__}', not "
                                f"'{type(value).__name__}'")
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto.get_or_create_list(self.name).extend(self.value)
    value: TStringList = property(lambda self: self._value, doc="Option value")

class ZMQAddressOption(Option):
    """Configuration option with ZMQAddress value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [TZMQAddress].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: ZMQAddress = None, proposal: str = None):
        super().__init__(name, ZMQAddress, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return value
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            self.set_value(ZMQAddress(value))
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            self.set_value(ZMQAddress(proto[self.name]))
    value: ZMQAddress = property(lambda self: self._value, doc="Option value")

class ZMQAddressListOption(Option):
    """Configuration option with list of ZMQAddresses value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [TZMQAddressList].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: ZMQAddressList = None, proposal: str = None):
        super().__init__(name, list, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return ', '.join(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            if value.strip():
                self.set_value([ZMQAddress(value.strip()) for value in value.split(',')])
            else:
                self.set_value([])
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, ListValue):
                self.set_value([ZMQAddress(addr) for addr in value])
            else:
                raise TypeError(f"Option '{self.name}' value must be a "
                                f"'{self.datatype.__name__}', not "
                                f"'{type(value).__name__}'")
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto.get_or_create_list(self.name).extend(self.value)
    value: ZMQAddressList = property(lambda self: self._value, doc="Option value")

class EnumOption(Option):
    """Configuration option with enum value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [Enum]
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    options:     List of allowed enum values.
    value:       Current option value.
"""
    def __init__(self, name: str, enum_class: Enum, description: str, required: bool = False,
                 default: Enum = None, proposal: str = None, options: t.List = None):
        super().__init__(name, enum_class, description, required, default, proposal)
        self.options: t.Iterable = enum_class if options is None else options
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return value.name
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    value: New option value.

Raises:
    TypeError:  When the new value is of the wrong type.
    ValueError: When the new value is not allowed.
"""
        if value is None:
            self.clear(False)
        else:
            if not isinstance(value, self.datatype):
                raise TypeError(f"Option '{self.name}' value must be a "
                                f"'{self.datatype.__name__}', not "
                                f"'{type(value).__name__}'")
            if value not in self.options:
                raise ValueError(f"Value '{self.value}' not allowed for option '{self.name}'")
            self._value = value
    def __fromstr(self, value: str):
        if value.isdigit():
            value = int(value)
            if value in t.cast(t.Type[Enum], self.datatype).get_value_map():
                self.set_value(t.cast(t.Type[Enum], self.datatype).get_value_map()[value])
            else:
                raise ValueError(f"Illegal value '{value}' for enum type "
                                 f"'{self.datatype.__name__}'")
        else:
            value = value.upper()
            if value in t.cast(t.Type[Enum], self.datatype).get_member_map():
                self.set_value(t.cast(t.Type[Enum], self.datatype).get_member_map()[value])
            else:
                raise ValueError(f"Illegal value '{value}' for enum type "
                                 f"'{self.datatype.__name__}'")
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            self.__fromstr(value)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, str):
                self.__fromstr(value)
            else:
                self.set_value(self.datatype(value))
    value: Enum = property(lambda self: self._value, doc="Option value")

class UUIDOption(Option):
    """Configuration option with UUID value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [uuid.UUID].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: uuid.UUID = None, proposal: str = None):
        super().__init__(name, uuid.UUID, description, required, default, proposal)
        self._value: uuid.UUID = default
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return str(self.value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            self.set_value(uuid.UUID(value))
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, str):
                value = uuid.UUID(value)
            self.set_value(value)
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto[self.name] = self.value.hex
    value: uuid.UUID = property(lambda self: self._value, doc="Option value")

class MIMEOption(Option):
    """Configuration option with MIME type specification value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [str].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
    mime_type:   MIME type specification 'type/subtype'
    mime_params: MIME type parameters
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: str = None, proposal: str = None):
        super().__init__(name, str, description, required, default, proposal)
        self.__mime_type: str = None
        self.__mime_params: t.Dict[str, str] = {}
        self.__parse_value(self._value)
    def __parse_value(self, value: str) -> None:
        self.__mime_type, self.__mime_params = parse_mime(value)
    def clear(self, to_default: bool = True) -> None:
        """Clears the option value.

Arguments:
    to_default: If True, sets the option value to default value, else to None.
"""
        value = self.default if to_default else None
        self.__parse_value(value)
        self._value = value
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    value: New option value.

Raises:
    TypeError:  When the new value is of the wrong type.
    ValueError: When the new value is not allowed.
"""
        if value is None:
            self.clear(False)
        else:
            if not isinstance(value, self.datatype):
                raise TypeError(f"Option '{self.name}' value must be a "
                                f"'{self.datatype.__name__}', not "
                                f"'{type(value).__name__}'")
            self.__parse_value(value)
            self._value = value
    def get_param(self, name: str, default: str = None) -> str:
        """Returns value of specified MIME parameter, or default value if parameter value
is not specified in MIME format.

Arguments:
    name: Name of the MIME parameter
    defalt: Default parameter value
"""
        return self.__mime_params.get(name, default)
    value: str = property(lambda self: self._value, doc="Option value")
    mime_type: str = property(lambda self: self.__mime_type, doc="MIME type/subtype")
    mime_params: t.ItemsView[str, str] = property(lambda self: self.__mime_params.items(),
                                                  doc="MIME type/subtype")

class PyExprOption(StrOption):
    """String configuration option with Python expression value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [str].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    value: New option value.

Raises:
    TypeError: When new value is of the wrong type.
    SyntaxError: When new value is not a valid Python expression.
"""
        if value is not None:
            compile(value, 'PyExprOption', 'eval')
        super().set_value(value)
    def get_expr(self):
        """Returns expression as code ready for evaluation, or None"""
        if self.value is not None:
            return compile(self.value, f"PyExprOption({self.name})", 'eval')
        return None
    def get_callable(self, arguments: str = ''):
        """Returns expression as callable function ready for execution, or None.

Arguments:
    arguments: String with arguments (names separated by coma) for returned function.
"""
        if self.value is not None:
            ns = {'datetime': datetime}
            code = compile(f"def expr({arguments}):\n    return {self.value}",
                           f"PyExprOption({self.name})", 'exec')
            eval(code, ns)
            return ns['expr']
        return None

class PyCodeOption(StrOption):
    """String configuration option with Python code value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [str].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.

Important:
    Python code must be properly indented, but ConfigParser multiline string values have
    leading whitespace removed. To circumvent this, the `PyCodeOption` supports assigment
    of text values where lines start with `|` character. This character is removed, along
    with any number of subsequent whitespace characters that are between `|` and first
    non-whitespace character on first line starting with `|`.
"""
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    value: New option value.

Raises:
    TypeError: When new value is of the wrong type.
    SyntaxError: When new value is not a valid Python expression.
"""
        if value is not None:
            if not isinstance(value, self.datatype):
                raise TypeError(f"Option '{self.name}' value must be a "
                                f"'{self.datatype.__name__}', not "
                                f"'{type(value).__name__}'")
            lines = []
            indent = None
            for line in value.split('\n'):
                if line.startswith('|'):
                    if indent is None:
                        indent = (len(line[1:]) - len(line[1:].strip())) + 1
                    lines.append(line[indent:])
                else:
                    lines.append(line)
            value = '\n'.join(lines)
            compile(value, 'PyCodeOption', 'exec')
        super().set_value(value)
    def get_code(self):
        """Returns expression as code ready for execution, or None"""
        if self.value is not None:
            return compile(self.value, f"PyCodeOption({self.name})", 'exec')
        return None

class PyCallableOption(StrOption):
    """String configuration option with Python callable value.

Attributes:
    name:          Option name.
    datatype:      Option datatype [str].
    description:   Option description. Can span multiple lines.
    required:      True if option must have a value.
    default:       Default value.
    proposal:      Text with proposed configuration entry (if it's different from default).
    value:         Current option value.
    arguments:     String with callable signature (arguments)
    callable_name: Function/procedure name

Important:
    Python code must be properly indented, but ConfigParser multiline string values have
    leading whitespace removed. To circumvent this, the `PyCodeOption` supports assigment
    of text values where lines start with `|` character. This character is removed, along
    with any number of subsequent whitespace characters that are between `|` and first
    non-whitespace character on first line starting with `|`.
"""
    def __init__(self, name: str, description: str, arguments: str, required: bool = False,
                 default: str = None, proposal: str = None):
        super().__init__(name, description, required, default, proposal)
        self.arguments: str = arguments
        self.callable_name: str = ''
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    value: New option value.

Raises:
    TypeError: When new value is of the wrong type.
    ValueError: When value is not correct.
    SyntaxError: When new value is not a valid Python code.
"""
        if value is not None:
            if not isinstance(value, self.datatype):
                raise TypeError(f"Option '{self.name}' value must be a "
                                f"'{self.datatype.__name__}', not "
                                f"'{type(value).__name__}'")
            lines = []
            indent = None
            for line in value.split('\n'):
                if line.startswith('|'):
                    if indent is None:
                        indent = (len(line[1:]) - len(line[1:].strip())) + 1
                    lines.append(line[indent:])
                else:
                    lines.append(line)
            for line in lines:
                if line.lower().startswith('def '):
                    i = 4
                    size = len(line)
                    while i < size and line[i].isalnum():
                        i += 1
                    self.callable_name = line[4:i]
                    hdr = f"def {self.callable_name}({self.arguments}):"
                    break
            if not self.callable_name:
                raise ValueError("The option value does not contain Python function definition")
            value = '\n'.join(lines)
            hdr = f"def {self.callable_name}({self.arguments}):"
            if hdr not in value:
                raise ValueError("The callable does not have the required signature:\n%s" % hdr)
            compile(value, 'PyCallableOption', 'exec')
        super().set_value(value)
    def get_callable(self):
        "Returns expression as code ready for execution, or None"
        if self.value is not None:
            ns = {}
            code = compile(self.value, f"PyCallableOption({self.name})", 'exec')
            eval(code, ns)
            return ns[self.callable_name]
        return None

class ConfigOption(Option):
    """Configuration option with TConfig value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [TConfig].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
"""
    def __init__(self, name: str, config_class: t.Type['Config'], description: str,
                 required: bool = False, proposal: str = None,
                 on_validate: TOnValidate = None):
        super().__init__(name, config_class, description, required, proposal=proposal)
        self._value: Config = None
        self.__on_validate = on_validate
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return value.name
    def validate(self) -> None:
        """Checks whether required option has value other than None. Also validates Config
options.

Raises:
    SaturninError: When required option does not have a value.
"""
        super().validate()
        if self.value is not None:
            self.value.validate()
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        section_name = config.get(section, self.name, vars=vars_, fallback=None)
        if isinstance(section_name, str):
            self.value = self.datatype(section_name, self.description)
            self.value.on_validate = self.__on_validate
            self.value.load_from(config, section_name, vars_)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            self.value = self.datatype(f"{self.name}_value", self.description)
            self.value.on_validate = self.__on_validate
            self.value.load_proto(proto.get_or_create_struct(self.name))
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.value is not None:
            self.value.save_proto(proto.get_or_create_struct(self.name))

class ConfigListOption(Option):
    """Configuration option with list of TConfig value.

Attributes:
    name:        Option name.
    datatype:    Option datatype [TConfig].
    description: Option description. Can span multiple lines.
    required:    True if option must have a value.
    default:     Default value.
    proposal:    Text with proposed configuration entry (if it's different from default).
    value:       Current option value.
    cfg_class:   Configuration class (TClass descendant).
"""
    def __init__(self, name: str, config_class: t.Type['Config'], description: str,
                 required: bool = False, proposal: str = None,
                 on_validate: TOnValidate = None):
        super().__init__(name, config_class, description, required, proposal=proposal)
        self._value: t.List['Config'] = None
        self.__on_validate = on_validate
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout."""
        return ', '.join(cfg.name for cfg in value)
    def validate(self) -> None:
        """Checks whether required option has value other than None. Also validates options
of all defined Configs.

Raises:
    SaturninError: When required option does not have a value.
"""
        super().validate()
        if self.value is not None:
            for cfg in self.value:
                cfg.validate()
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
    vars_:   Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        section_names = config.get(section, self.name, vars=vars_, fallback=None)
        if isinstance(section_names, str):
            self.value = []
            for section_name in (value.strip() for value in section_names.split(',')):
                cfg: Config = self.datatype(section_name, self.description)
                cfg.on_validate = self.__on_validate
                cfg.load_from(config, section_name, vars_)
                self.value.append(cfg)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.name in proto:
            i = 1
            for cfg_proto in proto[self.name]:
                cfg: Config = self.datatype(f"{self.name}_value_{i}", self.description)
                cfg.on_validate = self.__on_validate
                cfg.load_proto(cfg_proto)
                self.value.append(cfg)
                i += 1
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto_list = proto.get_or_create_list(self.name)
            for cfg in self.value:
                cfg.save_proto(proto_list.add_struct())

class Config:
    """Collection of configuration options.

Attributes:
    name: Name associated with Config (default section name).
    description: Configuration description. Can span multiple lines.
    <option_name>: Defined options are directly accessible as instance attaributes.
"""
    def __init__(self, name: str, description: str):
        self.name: str = name
        self.description: str = description
    def validate(self) -> None:
        """Checks whether:
    - all required options have value other than None.
    - all options are defined as config attribute with the same name as option name

Raises exception when any constraint required by configuration is violated.
"""
        for option in self.options:
            option.validate()
            if getattr(self, option.name, None) is None:
                raise SaturninError(f"Option '{option.name}' is not defined as "
                                    f"attribute with the same name")
    def clear(self) -> None:
        """Clears all option values."""
        for option in self.options:
            option.clear()
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update configuration.

Arguments:
    config:  ConfigParser instance with configuration values.
    section: Name of ConfigParser section that should be used to get new configuration values.
"""
        try:
            for option in self.options:
                option.load_from(config, section, vars_)
        except Exception as exc:
            raise SaturninError(f"Configuration error: {exc}") from exc
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        for option in self.options:
            option.load_proto(proto)
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    proto: protobuf `Struct` message.
"""
        for option in self.options:
            option.save_proto(proto)
    def get_printout(self) -> t.List[str]:
        """Return list of text lines with printout of current configuration"""
        lines = [option.get_printout() for option in self.options]
        lines.insert(0, f"Configuration [{self.name}]:")
        return lines
    options: t.List[Option] = property(lambda self: [v for k, v
                                                     in vars(self).items()
                                                     if isinstance(v, Option)],
                                              doc="Options Dict[name, Option].")

class MicroserviceConfig(Config):
    """Base Task (microservice) configuration.

Configuration options:
    :execution_mode: Task execution mode.

Attributes:
    name: Name associated with Config (default section name).
    description: Configuration description. Can span multiple lines.
    <option_name>: Defined options are directly accessible as instance attaributes.
"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.execution_mode: EnumOption = \
            EnumOption('execution_mode', ExecutionMode, "Task execution mode",
                       default=ExecutionMode.THREAD)

class ServiceConfig(MicroserviceConfig):
    """Base Service configuration.

Configuration options:
    :endpoints: Service endpoints.
    :execution_mode: Service execution mode.

Attributes:
    name: Name associated with Config (default section name).
    description: Configuration description. Can span multiple lines.
    <option_name>: Defined options are directly accessible as instance attaributes.
"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.endpoints: ZMQAddressListOption = \
            ZMQAddressListOption('endpoints', "Service endpoints", required=True)

class MicroDataProviderConfig(MicroserviceConfig):
    """Base data PROVIDER microservice configuration.

Configuration options:
    :execution_mode: Task execution mode
    :stop_on_close: Stop microservice when output pipe is closed
    :output_pipe: Output Data Pipe Identification
    :output_address: Output Data Pipe endpoint address
    :output_mode: Output Data Pipe Mode (BIND/CONNECT)
    :output_format: Output Pipe data format specification
    :output_batch_size: Output data batch size

Attributes:
    name: Name associated with Config (default section name).
    description: Configuration description. Can span multiple lines.
    <option_name>: Defined options are directly accessible as instance attaributes.
"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.stop_on_close: BoolOption = \
            BoolOption('stop_on_close',
                       "Stop microservice when output pipe is closed",
                       default=True)
        self.output_pipe: StrOption = \
            StrOption('output_pipe', "Output Data Pipe Identification",
                      required=True)
        self.output_address: ZMQAddressOption = \
            ZMQAddressOption('output_address', "Output Data Pipe endpoint address",
                             required=True)
        self.output_mode: EnumOption = \
            EnumOption('output_mode', SocketMode, "Output Data Pipe Mode",
                       required=True, default=SocketMode.CONNECT)
        self.output_format: MIMEOption = \
            MIMEOption('output_format', "Output Pipe data format specification")
        self.output_batch_size: IntOption = \
            IntOption('output_batch_size', "Output data batch size",
                      required=True, default=50)

class MicroDataConsumerConfig(MicroserviceConfig):
    """Base data CONSUMER microservice configuration.

Configuration options:
    :execution_mode: Task execution mode
    :stop_on_close: Stop microservice when input pipe is closed
    :input_pipe: Input Data Pipe Identification
    :input_address: Input Data Pipe endpoint address
    :input_mode: Input Data Pipe Mode (BIND/CONNECT)
    :input_format: Input Pipe data format specification
    :input_batch_size: Input data batch size

Attributes:
    name: Name associated with Config (default section name).
    description: Configuration description. Can span multiple lines.
    <option_name>: Defined options are directly accessible as instance attaributes.
"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.stop_on_close: BoolOption = \
            BoolOption('stop_on_close', "Stop microservice when input pipe is closed",
                       default=True)
        self.input_pipe: StrOption = \
            StrOption('input_pipe', "Input Data Pipe Identification")
        self.input_address: ZMQAddressOption = \
            ZMQAddressOption('input_address', "Input Data Pipe endpoint address")
        self.input_mode: EnumOption = \
            EnumOption('input_mode', SocketMode, "Input Data Pipe Mode",
                       default=SocketMode.CONNECT)
        self.input_format: MIMEOption = \
            MIMEOption('input_format', "Input Pipe data format specification")
        self.input_batch_size: IntOption = \
            IntOption('input_batch_size', "Input data batch size", default=50)

class MicroDataFilterConfig(MicroserviceConfig):
    """Base data PROVIDER microservice configuration.

Configuration options:
    :execution_mode: Task execution mode
    :stop_on_close: Stop microservice when output pipe is closed
    :input_pipe: Input Data Pipe Identification
    :input_address: Input Data Pipe endpoint address
    :input_mode: Input Data Pipe Mode (BIND/CONNECT)
    :input_format: Input Pipe data format specification
    :input_batch_size: Input data batch size
    :output_pipe: Output Data Pipe Identification
    :output_address: Output Data Pipe endpoint address
    :output_mode: Output Data Pipe Mode (BIND/CONNECT)
    :output_format: Output Pipe data format specification
    :output_batch_size: Output data batch size

Attributes:
    name: Name associated with Config (default section name).
    description: Configuration description. Can span multiple lines.
    <option_name>: Defined options are directly accessible as instance attaributes.
"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.stop_on_close: BoolOption = \
            BoolOption('stop_on_close', "Stop microservice when output pipe is closed",
                       default=True)
        self.input_pipe: StrOption = \
            StrOption('input_pipe', "Input Data Pipe Identification")
        self.input_address: ZMQAddressOption = \
            ZMQAddressOption('input_address', "Input Data Pipe endpoint address")
        self.input_mode: EnumOption = \
            EnumOption('input_mode', SocketMode, "Input Data Pipe Mode",
                       default=SocketMode.CONNECT)
        self.input_format: MIMEOption = \
            MIMEOption('input_format', "Input Pipe data format specification")
        self.input_batch_size: IntOption = \
            IntOption('input_batch_size', "Input data batch size", default=50)
        self.output_pipe: StrOption = \
            StrOption('output_pipe', "Output Data Pipe Identification", required=True)
        self.output_address: ZMQAddressOption = \
            ZMQAddressOption('output_address', "Output Data Pipe endpoint address",
                             required=True)
        self.output_mode: EnumOption = \
            EnumOption('output_mode', SocketMode, "Output Data Pipe Mode",
                       required=True, default=SocketMode.CONNECT)
        self.output_format: MIMEOption = \
            MIMEOption('output_format', "Output Pipe data format specification")
        self.output_batch_size: IntOption = \
            IntOption('output_batch_size', "Output data batch size", required=True,
                      default=50)

def create_config(_cls: t.Type[Config], name: str, description: str) -> Config:
    """Return newly created Config instance. Intended to be used with :func:`functools.partial`
in :attr:`~saturnin.core.types.ServiceDescriptor.config` definitions.
"""
    return _cls(name, description)

def get_config_lines(option: Option) -> t.List:
    """Returns list containing text lines suitable for use in configuration file processed
with :class:`~configparser.ConfigParser`.

Text lines with configuration start with comment marker ; and end with newline.
"""
    lines = [f"; {option.name}\n",
             f"; {'-' * len(option.name)}\n",
             ";\n",
             f"; data type: {option.datatype.__name__}\n",
             ";\n"]
    if option.required:
        description = '[REQUIRED] ' + option.description
    else:
        description = '[optional] ' + option.description
    for line in description.split('\n'):
        lines.append(f"; {line}\n")
    lines.append(';\n')
    if option.proposal:
        lines.append(f";{option.name} = <UNDEFINED>, "
                     f"proposed value: {option.proposal}\n")
    else:
        default = (option._format_value(option.default) if option.default is not None
                   else '<UNDEFINED>')
        lines.append(f";{option.name} = {default}\n")
    return lines

