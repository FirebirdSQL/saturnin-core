
Protobuf filter
===============

Metadata
--------

name:
  saturnin.proto.filter

description:
  Protobuf data filter microservice

classification:
  proto/filter

OID:
  1.3.6.1.4.1.53446.1.1.0.3.3.2

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.proto.filter

UUID:
  37937949-5102-5458-a801-c327b536d51e

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA FILTER that converts protobuf messages to text:

- INPUT: protobuf messages
- PROCESSING: uses expressions / functions evaluating data from protobuf message to filter
  data for output
- OUTPUT: protobuf messages

.. important::

   The namespace for functions and expressions contain only globals and module `datetime`.

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

include_expr:
  `~firebird.base.types.PyExpr`: Data inclusion Python expression

include_func:
  `~firebird.base.types.PyCallable`: Data inclusion Python function with signature
  `def f(data: Any) -> bool:`.

exclude_expr:
  `~firebird.base.types.PyExpr`: Data exclusion Python expression

exclude_func:
  `~firebird.base.types.PyCallable`: Data exclusion Python function with signature
  `def f(data: Any) -> bool:`.

.. important::

   - Input/output format is required and must be MIME_TYPE_PROTO
   - Input and output MIME 'type' params must be present and the same
   - At least one filter options must have a value
   - Only one from include and exclude methods could be defined

Example configurations that work with `saturnin.core.protobuf.fblog` protobuf package:

.. code-block:: cfg

  [log-filter]
  agent = 37937949-5102-5458-a801-c327b536d51e
  input_pipe = pipe-1
  input_pipe_address = inproc://${input_pipe}
  input_pipe_mode = connect
  input_pipe_format = application/x.fb.proto;type=saturnin.core.protobuf.fblog.LogEntry
  ;
  output_pipe = pipe-2
  output_pipe_address = inproc://${output_pipe}
  output_pipe_mode = bind
  output_pipe_format = application/x.fb.proto;type=saturnin.core.protobuf.fblog.LogEntry

  include_expr = (data.timestamp.ToDatetime() > datetime.datetime.fromisoformat('2019-01-01')) and (data.facility not in [0, 10])

  exclude_func =
      | def foo(data: Any) -> bool:
      |     return data.code == 151


.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html

