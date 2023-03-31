
Firebird log parser
===================

Metadata
--------

name:
  saturnin.firebird.log.parser

description:
  Firebird log parser microservice

classification:
  firebird-log/parser

OID:
  1.3.6.1.4.1.53446.1.1.0.3.4.1.2

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.firebird.log.parser

UUID:
  a93975c3-d8c4-5e19-b898-09391cafa8d8

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA FILTER that reads blocks of Firebird log text from input data
pipe, and sends parsed Firebird log entries as :ref:`LogEntry <log-entry>` protobuf messages
into output data pipe.


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
   - Only `application/x.fb.proto;type=saturnin.core.protobuf.fblog.LogEntry` MIME type is
     allowed for `output_pipe_format`.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html

