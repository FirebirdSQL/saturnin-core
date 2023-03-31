
Text file reader
================

Metadata
--------

name:
  saturnin.text.reader

description:
  Text reader microservice

classification:
  text/reader

OID:
  1.3.6.1.4.1.53446.1.1.0.3.1.1

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.text.reader

UUID:
  936d2670-93d8-5c45-84a7-b8dbc799ad97

facilities:
  None

API:
  None

Usage
-----

This microservice is a DATA PROVIDER that sends blocks of text from file (incl. stdin) to
output data pipe (using FBDP_ protocol).

Data is sent in blocks of the same size (except for the last one). The default block size is 64K.

The MIME type for the data transfer is `text/plain`, and may include `charset` and `errors`
parameters.

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

     Please note that this service by default sends up to 64K in single message, so either
     keep this parameter at low numbers, or adjust the `max_chars` value as well.

ready_schedule_interval:
  `int`: READY message schedule interval in milliseconds. See FBDP_ documentation for details. DEFAULT 1000.

filename:
  `str`: File specification. Either path to file or `stdin`. REQUIRED option.

file_format:
  `~firebird.base.types.MIME`: File data format specification. REQUIRED option. DEFAULT `text/plain;charset=utf-8`

max_chars:
  `int`: Max. number of characters transmitted in one message. REQUIRED option. DEFAULT 65535.

.. important::

   - Only 'text/plain' MIME type is alowed for `file_format` and `pipe_format`
     specifications.
   - Only 'charset' and 'errors' MIME parameters are alowed for `file_format` and
     `pipe_format` specifications.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html
