
Firebird trace parser
=====================

Metadata
--------

name:
  saturnin.firebird.trace.parser

description:
  Firebird trace parser microservice

classification:
  firebird-trace/parser

OID:
  1.3.6.1.4.1.53446.1.1.0.3.4.2.2

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.firebird.trace.parser

UUID:
  0d7e327a-912e-57a7-bcdd-47f03ab14db0

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA FILTER that reads blocks of Firebird trace session text protocol
from input data pipe, and sends parsed Firebird trace entries as :ref:`TraceEntry <trace-entry>`
protobuf messages into output data pipe.


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

.. important::

   - Only 'text/plain' MIME type is alowed for `input_pipe_format`.
   - Only 'charset' and 'errors' MIME parameters are alowed for `input_pipe_format`.
   - Only `application/x.fb.proto;type=saturnin.core.protobuf.fbtrace.TraceEntry` MIME type
     is allowed for `output_pipe_format`.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html

