
Protobuf printer
================

Metadata
--------

name:
  saturnin.proto.printer

description:
  Protobuf data printer microservice

classification:
  proto/printer

OID:
  1.3.6.1.4.1.53446.1.1.0.3.3.1

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.proto.printer

UUID:
  a58a9b30-117a-529e-8084-b9f8daf96d3e

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA FILTER that converts protobuf messages to text:

- INPUT: protobuf messages
- PROCESSING: uses formatting template and data from protobuf message to create text
- OUTPUT: blocks of text

There are two options how to convert protobuf message to text:

- Template. It's used as :std:term:`f-string` expression with protobuf message acessible
  as `data` and `.TransformationUtilities` accesible as `utils`.
- Python function that accepts data and `.TransformationUtilities` as parameters and returns
  string.

Configuration
-------------

agent:
  `.UUID`: Agent identification (service UUID)

logging_id:
  `str`: Logging ID for this component instance, see `Context-based logging`_ for details.

propagate_input_error:
  `bool`: When input pipe is closed with error, close output with error as well. DEFAULT `True`.

input_pipe:
  `str`: Input Data Pipe Identification. REQUIRED option.

input_pipe_address:
  `~firebird.base.types.ZMQAddress`: Input Data Pipe endpoint address. REQUIRED option.

input_pipe_mode:
  `~saturnin.base.types.SocketMode`: Input Data Pipe Mode (bind/connect). REQUIRED option.

input_pipe_format:
  `~firebird.base.types.MIME`: Input Pipe data format specification. REQUIRED for CONNECT pipe mode.

input_batch_size:
  `int`: Input Pipe Data batch size. DEFAULT 50.

input_ready_schedule_interval:
  `int`: Input Pipe READY message schedule interval in milliseconds. See FBDP_ documentation for details. DEFAULT 1000.

output_pipe:
  `str`: Output Data Pipe Identification. REQUIRED option.

output_pipe_address:
  `~firebird.base.types.ZMQAddress`: Output Data Pipe endpoint address. REQUIRED option.

output_pipe_mode:
  `~saturnin.base.types.SocketMode`: Output Data Pipe Mode (bind/connect). REQUIRED option.

output_pipe_format:
  `~firebird.base.types.MIME`: Output Pipe data format specification. DEFAULT `text/plain;charset=utf-8`

output_batch_size:
  `int`: Output Pipe Data batch size. DEFAULT 50.

output_ready_schedule_interval:
  `int`: Output Pipe READY message schedule interval in milliseconds. See FBDP_ documentation for details. DEFAULT 1000.

template:
  `str`: Text formatting template.

func:
  `~firebird.base.types.PyCallable`: Function that returns text representation of data.
  Python function with signature: `def f(data: Any, utils: TransformationUtilities) -> str`

.. important::

   - All required options must have value other than None
   - Only 'text/plain' MIME type is supported for 'output_pipe_format'
   - Only 'application/x.fb.proto' MIME type is supported for 'input_pipe_format'
   - Exactly one from 'func' or 'template' options can have a value

Example configurations that work with `saturnin.core.protobuf.fblog` protobuf package:

.. code-block:: cfg

  [log-print2]
  agent = a58a9b30-117a-529e-8084-b9f8daf96d3e
  input_pipe = pipe-1
  input_pipe_address = inproc://${input_pipe}
  input_pipe_mode = connect
  input_pipe_format = application/x.fb.proto;type=saturnin.core.protobuf.fblog.LogEntry
  ;
  output_pipe = pipe-2
  output_pipe_address = inproc://${output_pipe}
  output_pipe_mode = bind

  ; alternate filter using template
  ;template = {data.timestamp.ToDatetime()!s} {utils.short_enum_name('saturnin.core.protobuf.SeverityLevel', data.level):8} {utils.short_enum_name('saturnin.core.protobuf.fblog.FirebirdFacility', data.facility):10} {data.code} {data.message}{utils.LF}

  func =
     | def foo(data: Any, utils: TransformationUtilities) -> str:
     |     return utils.as_json(data)


.. currentmodule:: saturnin.core.proto_printer.service

TransformationUtilities
-----------------------
.. autoclass:: TransformationUtilities


.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html
