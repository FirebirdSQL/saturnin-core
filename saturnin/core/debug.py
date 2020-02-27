#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/debug.py
# DESCRIPTION:    Helpers for debugging (runtime)
# CREATED:        23.10.2019
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
# Debug log decorators are based on logdecorator module
# https://github.com/sighalt/logdecorator
# and some recipes from Python Logging Cookbook.
#
# Contributor(s): Pavel Císař (initial code)
#                 ______________________________________.

"""Saturnin - Helpers for debugging (runtime)
"""

import typing as t
import inspect
import logging
from functools import wraps

class BraceMessage(object):
    """Logging message with curly-brace formatting. Copied from Python Logging Cookbook."""
    def __init__(self, fmt: str, args, kwargs):
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs
    def __str__(self):
        return self.fmt.format(*self.args, **self.kwargs)

class DebugLoggingDecorator(object):
    """Base decorator for debug logging. It's not applied on decorated function/method if
__debug__ is False (optimized Python code).

The log message supports curly-brace formatting. Both positional and keyword arguments of
decorated callable are available by name for interpolation.

Additionally, the arguments values could be transformed or augmented to new attributes for
interpolation using a dict with [<argumnet_name>,<callable(argument_value)>] definitions.
The return value from callable is available as `<callable.__name__>_<argument_name>` along
argument names.

If `logger` instance is not explicitly defined, the decorator uses logger for module name
of decorated callable.

Example:
    `{'mylist': len}` will define `len_mylist` containing length of `myslist` (list) argument.

Attributes:
    message: Debug message (with curly-brace formatting)
    post_process: A disctionary with description of function/method attribute post-processing
        [default: None]
"""
    def __init__(self, message: str, logger: logging.Logger=None, post_process: t.Dict=None):
        self.message: str = message
        self.__logger:logging.Logger = logger
        self.post_process: t.Dict = post_process
    def do_post_process(self, adict):
        """Execute callables defined in `post_process`"""
        if self.post_process:
            for attr, fn in self.post_process.items():
                #print("Attr:", attr, " Value:", adict.get(attr))
                if attr in adict:
                    name = fn.__name__ if fn.__name__ != '<lambda>' else 'lambda'
                    adict['%s_%s' % (name, attr)] = fn(adict[attr])
    def before_execution(self, fn, args, kwargs):
        """Executed before decorated callable"""
        pass
    def after_execution(self, fn, result, args, kwargs):
        """Executed after decorated callable"""
        pass
    def _get_logger(self, fn):
        """Returns logger. If logger is not defined yet, creates logger for module name of
decorated callable."""
        if self.__logger is None:
            self.__logger = logging.getLogger(fn.__module__)
        return self.__logger
    @staticmethod
    def msg_params(fn, args: t.List, kwargs: t.Dict) -> t.MutableMapping:
        """Build dict with callable arguments for message interpolation"""
        signature = inspect.signature(fn)
        result = signature.bind_partial(*args, **kwargs).arguments
        for name, value in signature.parameters.items():
            if value.default != inspect._empty and name not in result:
                result[name] = value.default
        if 'self' in result:
            result['__fn'] = f"{result['self'].__class__.__name__}.{fn.__name__}"
        else:
            result['__fn'] = fn.__qualname__
        result['_fn'] = fn.__name__
        return result
    def __call__(self, fn: t.Callable) -> t.Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            self.before_execution(fn, args, kwargs)
            result = fn(*args, **kwargs)
            self.after_execution(fn, result, args, kwargs)
            return result

        return wrapper if __debug__ else fn

class log_on_start(DebugLoggingDecorator):
    """Decorator that logs debug message before decorated callable is executed."""
    def before_execution(self, fn, args, kwargs):
        """Executed before decorated callable"""
        logger = self._get_logger(fn)
        msg_params = self.msg_params(fn, args, kwargs)
        self.do_post_process(msg_params)
        #print(msg_params)
        logger.debug(BraceMessage(self.message, [], msg_params))

class log_on_end(DebugLoggingDecorator):
    """Decorator that logs debug message after decorated callable is executed.

Attributes:
    result_fmt_var: Name of message format variable with value returned by decorated
        callable [default: 'result']
"""
    def __init__(self, message, logger=None, post_process=None,
                 result_fmt_var='result'):
        super().__init__(message, logger=logger, post_process=post_process)
        self.result_fmt_var = result_fmt_var
    def after_execution(self, fn, result, args, kwargs):
        """Executed after decorated callable"""
        logger = self._get_logger(fn)
        msg_params = self.msg_params(fn, args, kwargs)
        msg_params[self.result_fmt_var] = result
        self.do_post_process(msg_params)
        logger.debug(BraceMessage(self.message, [], msg_params))
