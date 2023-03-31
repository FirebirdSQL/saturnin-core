
Binary data file writer
=======================

Metadata
--------

name:
  saturnin.binary.writer

description:
  Binary data writer microservice

classification:
  binary/writer

OID:
  1.3.6.1.4.1.53446.1.1.0.3.2.2

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.binary.writer

UUID:
  4e606fdf-3fa9-5d18-a714-9448a8085aab

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA CONSUMER that wites binary data from input data pipe
(using FBDP_ protocol) to file (incl. stdout/stderr).

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

Service supports two types of data files:

STREAM:
  Classic data files where data are written continuously.

BLOCK:
  Each message received is written as single block preceded by data size (as a 4 byte integer).

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
  `int`: Data batch size. See FBDP_ documentation for details. DEFAULT 50.

ready_schedule_interval:
  `int`: READY message schedule interval in milliseconds. See FBDP_ documentation for details. DEFAULT 1000.

filename:
  `str`: File specification. Either path to file, `stdout` or `stderr`. REQUIRED option.

file_mode:
  `~saturnin.base.types.FileOpenMode`: File I/O mode. DEFAULT `WRITE`.

file_type:
  `.FileStorageType`: File data storage type (`stream` or `block`). REQUIRED option.

.. important::

   - Only file_mode `WRITE` is allowed for `stdout` and `stderr`.
   - file_mode `READ` is not supported.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html
