
===========
Usage Guide
===========

Butler Services
===============

Saturnin currently supports two types of Butler services:

* **Standard Butler services**. These services use the FBSP_ protocol and work in client/server
  mode.

  To use these services, you need client software that is capable of calling their APIs.
  Subsequently, it is sufficient to start the service with the required configuration in the
  `Saturnin container`_, and enter the address of the service entry point to the client program.

  To save system resources and simplify management, multiple services can be run in a single
  container.

* **Microservices**. These are primarily data processing services that use the FBDP_ protocol
  to echange data with other services.

  These services are typically combined into data processing pipelines. All services involved
  in processing are typically run within a single `Saturnin container`_.

Saturnin recipes
================

To run services within Saturnin container, you need a special configuration file (with classic
.INI file structure) called `Saturnin recipe`_. Each service to be started in the container
must have its own section with the appropriate configuration (an overview of configuration
parameters can be found in the description of individual services).

.. seealso::

   The creation and use of recipes is described in the `Saturnin Usage Guide`_.

Service endpoints
=================

The most important element of the configuration of any service is the specification of its
endpoints. Each Butler service communicates through messages passed by the ZeroMQ_ library.
This library makes it possible to use a whole range of communication protocols (transports).

Endpoint address
----------------

A Service endpoint is a string consisting of a `transport` `://` followed by an `address`.
The transport specifies the underlying protocol to use. The address specifies
the transport-specific address to bind/connect to.

ZeroMQ provides the the following transports:

tcp:
    Unicast transport using TCP.

    For the TCP transport, the transport is `tcp`, and the meaning of the address part is
    TCP address followed by a colon and the TCP port number to use.

    .. tip::

       This protocol is the most appropriate choice for all endpoints to be accessible
       outside the container in which the service is operated.

    .. seealso:: For detailed information about TCP endpoints, see zmq-tcp_ documentation.

ipc:
    Local inter-process communication transport. This transport passes messages between
    local processes using a system-dependent IPC mechanism.

    .. important::

       The inter-process transport is currently only implemented on operating systems that
       provide UNIX domain sockets.

    For the inter-process transport, the transport is `ipc`, and the meaning of the address
    part is arbitrary string identifying the pathname to create.

    .. seealso:: For detailed information about IPC endpoints, see zmq-ipc_ documentation.

inproc:
    Local in-process (inter-thread) communication transport. This transport passes messages
    via memory directly between threads sharing a single ØMQ context.

    For the in-process transport, the transport is `inproc`, and the meaning of the address
    part is an arbitrary string identifying the name to create. The name must be unique within
    the Saturnin container context.

    .. tip::

       This protocol is the most appropriate choice for all endpoints that are used only
       for communication between services running within the same container.

    .. seealso:: For detailed information about INPROC endpoints, see zmq-inproc_ documentation.

pgm, epgm:
    Reliable multicast transport using PGM.

    .. seealso:: For detailed information about PGM, EPGM endpoints, see zmq-pgm_ documentation.

vmci:
    Virtual machine communications interface (VMCI).

    .. seealso:: For detailed information about VMCI endpoints, see zmq-vmci_ documentation.

Bind vs Connect
---------------

The context (and thus the internal creation method) of endpoints is mostly given by the way
they are used by the service.

* Endpoints for standard services define the addresses and transport protocols to which
  the service `binds` and through which clients connect to the service.

* Endpoints used by a service to communicate with other services are used to `connect` to those
  services.

However, some services may use endpoints, requiring the specification of whether the service
should bind or connect to them. These are typically endpoints used to transfer data between
services via the FBDP_ protocol. In this scenario, the endpoint represents a data pipe,
where one of the services is the provider and the other is the consumer of the data. According
to the specification of the FBDP_ protocol, the party that binds to the endpoint determines
the basic parameters of the communication. As a practical matter, the endpoint through which
the service provides its outputs should be bound, and the endpoint used by the service for
its inputs should be connected.

.. note::

   Exceptions to this recommendation are scenarios that use a data-bus service that defines
   a fixed connection point for all data pipes that other services connect to, regardless
   of whether they are producers or consumers.

Here is a sample recipe to print Firebird log on screen using two Saturnin microservices
that are composed to data processing pipeline connected via INPROC transport:

.. code-block:: cfg

   ; 1. Recipe parameters
   [saturnin.recipe]
   recipe_type = bundle
   execution_mode = normal
   description = Simple recipe that print log from local Firebird server.

   ; 2. Bundle content
   [bundle]
   agents = from-server, writer

   ; Helper section to centralize definition of shared parameters
   [pipe]
   name = pipe-1
   address = inproc://pipe-1

   ; 3. Confguration of components
   [from-server]
   agent = 212657dc-2618-5f4b-a8f5-d8d42e99fe7e
   pipe = ${pipe:name}
   pipe_address = ${pipe:address}
   pipe_mode = bind
   pipe_format = text/plain;charset=utf-8
   server = local

   [writer]
   agent = 4e606fdf-3fa9-5d18-a714-9448a8085aab
   pipe = ${pipe:name}
   pipe_address = ${pipe:address}
   pipe_mode = connect
   pipe_format = text/plain;charset=utf-8
   filename = stdout
   file_format = text/plain;charset=utf-8
   file_mode = write



.. _setuptools: https://pypi.org/project/setuptools/
.. _ctypes: http://docs.python.org/library/ctypes.html
.. _PYPI: https://pypi.org/
.. _pip: https://pypi.org/project/pip/
.. _pipx: https://pypa.github.io/pipx/
.. _firebird-base: https://firebird-base.rtfd.io
.. _firebird-driver: https://pypi.org/project/firebird-driver/
.. _introduction to Firebird Butler: https://firebird-butler.readthedocs.io/en/latest/introduction.html
.. _saturnin-core: https://github.com/FirebirdSQL/saturnin-core
.. _Saturnin CORE: https://saturnin-core.rtfd.io/
.. _Saturnin SDK: https://saturnin-sdk.rtfd.io/
.. _saturnin-sdk: https://github.com/FirebirdSQL/saturnin-sdk
.. _FBSP: https://firebird-butler.readthedocs.io/en/latest/rfc/4/FBSP.html
.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Firebird Butler services: https://firebird-butler.readthedocs.io/en/latest/rfc/3/FBSD.html
.. _firebird-uuid: https://github.com/FirebirdSQL/firebird-uuid
.. _Saturnin Usage Guide: https://saturnin.readthedocs.io/en/latest/
.. _Saturnin container: https://saturnin.readthedocs.io/en/latest/usage-guide.html#service-containers
.. _Saturnin recipe: https://saturnin.readthedocs.io/en/latest/usage-guide.html#saturnin-recipes
.. _ZeroMQ: https://zeromq.org/
.. _zmq-tcp: http://api.zeromq.org/master:zmq-tcp
.. _zmq-ipc: http://api.zeromq.org/master:zmq-ipc
.. _zmq-inproc: http://api.zeromq.org/master:zmq-inproc
.. _zmq-pgm: http://api.zeromq.org/master:zmq-pgm
.. _zmq-vmci: http://api.zeromq.org/master:zmq-vmci
