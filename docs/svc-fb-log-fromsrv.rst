
Firebird log from server provider
=================================

Metadata
--------

name:
  saturnin.firebird.log.fromsrv

description:
  Firebird log from server provider microservice

classification:
  firebird-log/provider

OID:
  1.3.6.1.4.1.53446.1.1.0.3.4.1.1

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.firebird.log.fromsrv

UUID:
  212657dc-2618-5f4b-a8f5-d8d42e99fe7e

facilities:
  firebird

API:
  None

Usage
-----

This microservice is a DATA PROVIDER that fetches Firebird log from Firebird server via
services and send it as blocks of text to output data pipe (using FBDP_ protocol).

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

server:
  `str`: Firebird server indetification (in driver configuration). REQUIRED option.

max_chars:
  `int`: Max. number of characters transmitted in one message. REQUIRED option. DEFAULT 65535.

.. important::

   - Only 'text/plain' MIME type is alowed for `pipe_format`.
   - Only 'charset' and 'errors' MIME parameters are alowed for `pipe_format`.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html

