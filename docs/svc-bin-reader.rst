
Binary data file reader
=======================

Metadata
--------

name:
  saturnin.binary.reader

description:
  Binary data reader microservice

classification:
  binary/reader

OID:
  1.3.6.1.4.1.53446.1.1.0.3.2.1

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.binary.reader

UUID:
  3db461de-f32e-5514-910d-7d021a2436a5

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA PROVIDER that sends blocks of binary data read from a file
(incl. stdin) to output data pipe (using FBDP_ protocol).

Data is sent in blocks of:

- Fixed size.
- Variable size where the size of each block is stored in the file as 4 bytes before the
  data itself.

.. important::

   The MIME type for the transmitted data must be defined in an appropriate way that
   guarantees the correct processing of the data by the receiving service.

.. note::

   This service is primarily intended for working with files created by the binary data
   writer service.


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
  `str`: File specification (path to file). REQUIRED option.

block_size:
  `int`: Data block size in bytes (-1 when size as longint is stored before the data)

.. important::

   'block_size' must be positive or -1.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html
