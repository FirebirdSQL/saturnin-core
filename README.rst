======================
Saturnin core services
======================

This repository contains core set of services for Saturnin.

To install these services, it's necessary to properly initialize the `saturnin`
deployment (see documentation for `saturnin`).

The best way to install this package is via Saturnin CLI manager::

   saturnin install saturnin-core

The core set of services for Saturnin currently contains next services:

* Text file reader microservice [saturnin.text.reader]
* Text file writer microservice [saturnin.text.writer]
* Text line filter microservice [saturnin.text.linefilter]
* Binary data file reader microservice [saturnin.binary.reader]
* Binary data file writer microservice [saturnin.binary.writer]
* Protobuf printer microservice [saturnin.proto.printer]
* Protobuf filter microservice [saturnin.proto.filter]
* Protobuf aggregator microservice [saturnin.proto.aggregator]
* Firebird log from server provider microservice [saturnin.firebird.log.fromsrv]
* Firebird log parser microservice [saturnin.firebird.log.parser]
* Firebird trace parser microservice [saturnin.firebird.trace.parser]
* Firebird trace session provider microservice [saturnin.firebird.trace.session]

