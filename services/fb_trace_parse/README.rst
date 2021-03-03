===========================================
Saturnin firebird-trace-parser microservice
===========================================

Firebird-trace-parser is a Saturnin DATA_FILTER microservice that reads blocks of Firebird
trace session text protocol from input data pipe, and sends parsed Firebird trace entries
as "saturnin.protobuf.fbtrace.TraceEntry" protobuf messages into output data pipe.
