
Protobuf aggregator
===================

Metadata
--------

name:
  saturnin.proto.aggregator

description:
  Protobuf data aggregator microservice

classification:
  proto/aggregator

OID:
  1.3.6.1.4.1.53446.1.1.0.3.3.3

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.proto.aggregator

UUID:
  a676dc59-7eba-5f37-82a2-73115e933a42

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA FILTER that converts protobuf messages to text:

- INPUT: protobuf messages
- PROCESSING: uses expressions / functions evaluating data from protobuf message to aggregate data for output
- OUTPUT: protobuf messages

Supported aggregation functions: `count`, `min`, `max`, `sum`, `avg`

The aggregation is cotroled by two configuration parameters: `group_by` and `aggreagte`.

Both parameters are of type list of strings. First, the `group_by` parameter: each string
consists of the output item name followed by a colon and the specification of the input
protobuf item to be used, in the format "data.<item name>". Similarly, for the `aggregate`
parameter, the string consists of the name of the aggregation function followed by a colon,
and then the specification of the input data item to be passed to the aggregation function,
in the same format as for the `group_by` parameter.

The output of the filter are messages of type :ref:`GenericDataRecord <gen-data-record>`.

.. important::

   Data is sent only after the input is closed!


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

group_by:
  `List[str]`: Specification of fields that are 'group by' key. REQUIRED option.

aggregate:
  `List[str]`: Specification for aggregates. REQUIRED option.


func:
  `~firebird.base.types.PyCallable`: Function that returns text representation of data.
  Python function with signature: `def f(data: Any, utils: TransformationUtilities) -> str`


.. important::

   - The MIME type for 'input_format' must be 'application/x.fb.proto'
   - The MIME type for 'output_format' must be 'application/x.fb.proto;type=saturnin.core.protobuf.common.GenDataRecord'
   - The 'aggregate' values must have format '<aggregate_func>:<field_spec>', and
     <aggregate_func> must be from supported functions

Example:

.. code-block:: cfg

  [log-filter]
  agent = a676dc59-7eba-5f37-82a2-73115e933a42
  input_pipe = pipe-1
  input_pipe_address = inproc://${input_pipe}
  input_pipe_mode = connect
  input_pipe_format = application/x.fb.proto;type=saturnin.core.protobuf.fblog.LogEntry

  output_pipe = pipe-2
  output_pipe_address = inproc://${output_pipe}
  output_pipe_mode = bind
  output_pipe_format = application/x.fb.proto;type=saturnin.core.protobuf.GenericDataRecord

  group_by =
      code:data.code
      message:data.message
  ; The data spec. for "count" function is optional
  aggregate =
      count:
      avg:len(data.params)

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html


