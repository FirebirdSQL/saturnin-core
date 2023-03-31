
Text line filter
================

Metadata
--------

name:
  saturnin.text.linefilter

description:
  Text line filter microservice

classification:
  text/filter

OID:
  1.3.6.1.4.1.53446.1.1.0.3.1.3

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.text.linefilter

UUID:
  455093ea-fd99-53c4-9b1f-b2c9b764f482

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA FILTER that uses FBDP_ protocol to read blocks of text from
input data pipe, and write lines that meet the specified conditions as blocks of text into
output data pipe.

A filter can be defined as one of the following:

- regex expression
- Python bool expression that uses `line` to refer to the line of text being processed
- Python function with signature `def fname(line: str) -> bool`

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
  `~firebird.base.types.MIME`: Output Pipe data format specification. REQUIRED for CONNECT pipe mode.

output_batch_size:
  `int`: Output Pipe Data batch size. DEFAULT 50.

output_ready_schedule_interval:
  `int`: Output Pipe READY message schedule interval in milliseconds. See FBDP_ documentation for details. DEFAULT 1000.

max_chars:
  `int`: Max. number of characters transmitted in one message. DEFAULT 65535.

regex:
  `str`: Filter by regular expression

expr:
  `~firebird.base.types.PyExpr`: Filter by Python expression (use `line` to refer to the line of text being processed)

func:
  `~firebird.base.types.PyCallable`: Filter by Python function. Python function with signature: `def fname(line: str) -> bool`

.. important::

   - Exactly one filter definition must be provided.
   - Only 'text/plain' MIME types are alowed for input and output `pipe_format`.
   - Only 'charset' and 'errors' MIME parameters are alowed for input and output `pipe_format`.
   - Regex must be valid.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html
