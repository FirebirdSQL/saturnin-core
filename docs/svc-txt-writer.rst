
Text file writer
================

Metadata
--------

name:
  saturnin.text.writer

description:
  Text writer microservice

classification:
  text/writer

OID:
  1.3.6.1.4.1.53446.1.1.0.3.1.2

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.text.writer

UUID:
  4e606fdf-3fa9-5d18-a714-9448a8085aab

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA CONSUMER that wites blocks of text from input data pipe
(using FBDP_ protocol) to file (incl. stdout/stderr).

The MIME type for the data transfer could be either `text/plain` (that may include
`charset` and `errors` parameters) or `application/x.fb.proto`. Protobuf messages are
converted to text before being written to a file.

Writing to the file can take place in several modes:

CREATE:
  If the file already exists, it is overwritten.

APPEND:
  If the file already exists, it is appended.

WRITE:
  Normal writing to a file.

RENAME:
  If the file already exists, it is renamed (a numerical extension is added to the file
  name), and writing takes place to a new file with the original name.

Configuration
-------------

agent:
  `.UUID`: Agent identification (service UUID)

logging_id:
  `str`: Logging ID for this component instance, see `Context-based logging`_ for details.

stop_on_close:
  `bool`: Stop the service when pipe is closed. DEFAULT `True`.

pipe:
  `str`: Data Pipe Identification (name). REQUIRED option.

pipe_address:
  `~firebird.base.types.ZMQAddress`: Data Pipe endpoint address. REQUIRED option.

pipe_mode:
  `~saturnin.base.types.SocketMode`: Data Pipe Mode (bind/connect). REQUIRED option.

pipe_format:
  `~firebird.base.types.MIME`: Pipe data format specification. REQUIRED for CONNECT pipe mode.

batch_size:
  `int`: Data batch size. See FBDP_ documentation for details. DEFAULT 5.

  .. note::

     Please note that this service may get a lot of text in single message, so either
     keep this parameter at low numbers, or adjust max. size of messages passed to this service.

ready_schedule_interval:
  `int`: READY message schedule interval in milliseconds. See FBDP_ documentation for details. DEFAULT 1000.

filename:
  `str`: File specification. Either path to file, `stdout` or `stderr`. REQUIRED option.

file_format:
  `~firebird.base.types.MIME`: File data format specification. REQUIRED option. DEFAULT `text/plain;charset=utf-8`

file_mode:
  `~saturnin.base.types.FileOpenMode`: File I/O mode. DEFAULT `WRITE`.

.. important::

   - Only 'text/plain' MIME type is alowed for `file_format`.
   - Only 'text/plain' and 'application/x.fb.proto' MIME types are alowed for `pipe_format`.
   - Only 'charset' and 'errors' MIME parameters are alowed for `file_format` and
     `pipe_format` specifications of type 'plain/text'.
   - Only file_mode `WRITE` is allowed for `stdout` and `stderr`.
   - file_mode `READ` is not supported.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html
