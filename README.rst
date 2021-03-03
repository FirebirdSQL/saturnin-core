======================
Saturnin core services
======================

This repository contains core set of services for Saturnin.

The saturnin-core package (released on PyPI) contains only modules required by some
Saturnin core services (they may list it as dependency).

The core services itself are not distributed via PyPI, but as separate ZIP package(s) that
are installed via "saturnin-pkg" utility from "saturnin" package.

You may either download the "core" services package from `gihub releases`_, or you may
create such Saturnin package(s) yourself by simply ZIP the directory for particular service,
or ZIP entire content of "services" directory to make a "budle" package.

.. _gihub releases: https://github.com/FirebirdSQL/saturnin-core/releases
