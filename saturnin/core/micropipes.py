#coding:utf-8
#
# PROGRAM/MODULE: saturnin-core
# FILE:           saturnin/core/micropipes.py
# DESCRIPTION:    Base module for implementation of Firebird Butler Microservices that
#                 use datapipes to provide, process or consume data
# CREATED:        17.12.2019
#
# The contents of this file are subject to the MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Copyright (c) 2019 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin - Base module for implementation of Firebird Butler Microservices that use
datapipes to provide, process or consume data.
"""

import typing as t
import logging
from .types import SocketMode, ServiceDescriptor, ServiceFacilities
from .base import DealerChannel
from .config import MicroDataProviderConfig, MicroDataConsumerConfig, \
     MicroDataFilterConfig
from .service import MicroserviceImpl, BaseService
from .datapipe import END_OF_DATA, DataPipe, InputPipe, OutputPipe, Session, Message, \
     ErrorCode

# Logger

log = logging.getLogger(__name__)

# Classes

class MicroDataProviderImpl(MicroserviceImpl):
    """Base implementation of data DATA_PROVIDER microservice.

Attributes:
    out_pipe: Output data pipe.
    out_chn:  Dealer channel used by output data pipe.
    stop_on_close: If True, microservice is stopped when output pipe is closed.

Important:
    This class does use generic `on_accept_client`, `on_server_connected` and `on_server_ready`
    data pipe callbacks. If you want custom callbacks, they must be implemented in descendant
    and assigned to :attr:`out_pipe` in :meth:`configure_provider()`.
"""
    def __init__(self, descriptor: ServiceDescriptor, stop_event: t.Any):
        super().__init__(descriptor, stop_event)
        self.out_pipe: OutputPipe = OutputPipe(self.on_pipe_closed)
        self.out_chn: DealerChannel = None
        self.stop_on_close = True
    def __deferred_shutdown(self, *args) -> None:
        """Shut down the service on idle. This is a workaround to problem found in ZMQ,
where pending messages are not delivered via TCP transport to the peer before context is
shut down despite infinite linger.
"""
        self.stop_event.set()
    def produce_output(self, pipe: DataPipe, session: Session) -> t.Any:
        """Called to aquire next data payload to be send via output pipe.

Returns:
    a) `None` when data are not yet available.
    b) `datapipe.END_OF_DATA` object if there is no more data to send.
    c) Data to be sent in FBDP `data_frame`. They must be in correct format.

Raises:
    StopError: Alternate method to signal END OF DATA stream.
    SaturninError: For expected error conditions. If exception has `code` attribute,
        it must contain valid FBDP ErrorCode that is sent in CLOSE message. If attribute
        is not defined, the CLOSE message will contain ErrorCode.ERROR code.
    Exception: For unexpected error conditions. The pipe is closed with code
        ErrorCode.INTERNAL_ERROR.
"""
        raise NotImplementedError
    def configure_provider(self, config: MicroDataProviderConfig) -> None:
        """Called to configure the data provider.

This method must raise an exception if data format assigned to output pipe is invalid.
"""
        raise NotImplementedError
    def on_pipe_closed(self, pipe: DataPipe, session: Session, msg: Message) -> None:
        """General callback that logs info(OK) or error, and closes the input file."""
        if __debug__: log.debug('%s.on_pipe_closed [%s]', self.__class__.__name__, pipe.pipe_id)
        if self.stop_on_close:
            self.mngr.defer(self.__deferred_shutdown)
    def initialize(self, svc: BaseService) -> None:
        super().initialize(svc)
        self.out_chn = DealerChannel(b'%s-out' % self.instance_id.hex().encode('ascii'),
                                      sock_opts=self.get('out_sock_opts', None))
        self.out_pipe.set_channel(self.out_chn)
        self.mngr.add(self.out_chn)
    def configure(self, svc: BaseService, config: MicroDataProviderConfig) -> None:
        """Service configuration."""
        config.validate() # Fail early
        self.stop_on_close = config.stop_on_close.value
        self.out_pipe.pipe_id = config.output_pipe.value
        self.out_pipe.address = config.output_address.value
        self.out_pipe.batch_size = config.output_batch_size.value
        self.out_pipe.set_format(config.output_format)
        # batch_size must be assigned before set_mode()
        self.out_pipe.set_mode(config.output_mode.value)
        self.out_pipe.on_produce_data = self.produce_output
        #
        self.configure_provider(config)
        # Open pipe
        if self.out_pipe.mode == SocketMode.BIND:
            self.facilities = ServiceFacilities.OUTPUT_AS_SERVER
            self.out_pipe.open()
        else:
            self.facilities = ServiceFacilities.OUTPUT_AS_CLIENT
            self.mngr.defer(self.out_pipe.open)
    def finalize(self, svc: BaseService) -> None:
        """Service finalization."""
        self.out_pipe.close()
        super().finalize(svc)


class MicroDataConsumerImpl(MicroserviceImpl):
    """Base implementation of data DATA_CONSUMER microservice.

Attributes:
    in_pipe: Input data pipe.
    in_chn:  Dealer channel used by input data pipe.
    stop_on_close: If True, microservice is stopped when input pipe is closed.

Important:
    This class does use generic `on_accept_client`, `on_server_connected` and `on_server_ready`
    data pipe callbacks. If you want custom callbacks, they must be implemented in descendant
    and assigned to :attr:`in_pipe` in :meth:`configure_consumer()`.
"""
    def __init__(self, descriptor: ServiceDescriptor, stop_event: t.Any):
        super().__init__(descriptor, stop_event)
        self.in_pipe: InputPipe = InputPipe(self.on_pipe_closed)
        self.in_chn: DealerChannel = None
        self.stop_on_close = True
    def __deferred_shutdown(self, *args) -> None:
        """Shut down the service on idle. This is a workaround to problem found in ZMQ,
where pending messages are not delivered via TCP transport to the peer before context is
shut down despite infinite linger.
"""
        self.stop_event.set()
    def accept_input(self, pipe: DataPipe, session: Session, data: bytes) -> t.Optional[int]:
        """Called to process next data payload aquired from input pipe.

Returns:
    a) `None` when data were sucessfuly processed.
    b) FBDP `ErrorCode` if error was encountered.

Raises:
    Exception: For unexpected error conditions. The pipe is closed with code
        ErrorCode.INTERNAL_ERROR.
"""
        raise NotImplementedError
    def configure_consumer(self, config: MicroDataConsumerConfig) -> None:
        """Called to configure the data consumer.

This method must raise an exception if data format assigned to input pipe is invalid.
"""
        raise NotImplementedError
    def on_pipe_closed(self, pipe: DataPipe, session: Session, msg: Message) -> None:
        """General callback that logs info(OK) or error, and closes the input file."""
        if __debug__: log.debug('%s.on_pipe_closed [%s]', self.__class__.__name__, pipe.pipe_id)
        if self.stop_on_close:
            self.mngr.defer(self.__deferred_shutdown)
    def initialize(self, svc: BaseService) -> None:
        super().initialize(svc)
        self.in_chn = DealerChannel(b'%s-in' % self.instance_id.hex().encode('ascii'),
                                      sock_opts=self.get('in_sock_opts', None))
        self.in_pipe.set_channel(self.in_chn)
        self.mngr.add(self.in_chn)
    def configure(self, svc: BaseService, config: MicroDataConsumerConfig) -> None:
        """Service configuration."""
        config.validate() # Fail early
        self.stop_on_close = config.stop_on_close.value
        self.in_pipe.pipe_id = config.input_pipe.value
        self.in_pipe.address = config.input_address.value
        self.in_pipe.batch_size = config.input_batch_size.value
        self.in_pipe.set_format(config.input_format)
        # batch_size must be assigned before set_mode()
        self.in_pipe.set_mode(config.input_mode.value)
        self.in_pipe.on_accept_data = self.accept_input
        #
        self.configure_consumer(config)
        # Open pipe
        if self.in_pipe.mode == SocketMode.BIND:
            self.facilities = ServiceFacilities.INPUT_AS_SERVER
            self.in_pipe.open()
        else:
            self.facilities = ServiceFacilities.INPUT_AS_CLIENT
            self.mngr.defer(self.in_pipe.open)
    def finalize(self, svc: BaseService) -> None:
        """Service finalization."""
        self.in_pipe.close()
        super().finalize(svc)

class MicroDataFilterImpl(MicroserviceImpl):
    """Base implementation of data DATA_FILTER microservice.

Attributes:
    in_pipe:  Input data pipe.
    in_chn:   Dealer channel used by input data pipe.
    out_pipe: Output data pipe.
    out_chn:  Dealer channel used by output data pipe.
    out_que:  Output queue with processed data that should be send.
    stop_on_close: If True, microservice is stopped when output pipe is closed.

Important:
    This class does use generic `on_accept_client`, `on_server_connected` and `on_server_ready`
    data pipe callbacks. If you want custom callbacks, they must be implemented in descendant
    and assigned to :attr:`out_pipe` in :meth:`configure_filter()`.
"""
    def __init__(self, descriptor: ServiceDescriptor, stop_event: t.Any):
        super().__init__(descriptor, stop_event)
        self.in_pipe: InputPipe = InputPipe(self.on_input_closed)
        self.out_pipe: OutputPipe = OutputPipe(self.on_output_closed)
        self.in_chn: DealerChannel = None
        self.out_chn: DealerChannel = None
        self.out_que: t.List = []
        self.stop_on_close = True
    def __deferred_shutdown(self, *args) -> None:
        """Shut down the service on idle. This is a workaround to problem found in ZMQ,
where pending messages are not delivered via TCP transport to the peer before context is
shut down despite infinite linger.
"""
        self.stop_event.set()
    def finish_processing(self, session: Session) -> None:
        """Called to process any remaining input data when input pipe is closed normally.

Important:
    The default implementation does nothing.
"""
    def accept_input(self, pipe: DataPipe, session: Session, data: bytes) -> t.Optional[int]:
        """Called to process next data payload aquired from input pipe.

Important:
    This method must store produced output data into :attr:`out_que`. If there are no more
    data for output, it must store `datapipe.END_OF_DATA` object to the queue.

    If input data are not complete to produce output data, they must be stored into
    :attr:`in_que` for later processing.

Returns:
    a) `None` when data were sucessfuly processed.
    b) FBDP `ErrorCode` if error was encontered.

Raises:
    Exception: For unexpected error conditions. The pipe is closed with code
        ErrorCode.INTERNAL_ERROR.
"""
        raise NotImplementedError
    def produce_output(self, pipe: DataPipe, session: Session) -> t.Any:
        """Called to aquire next data payload from :attr:`out_que` to be send via output pipe.
"""
        if self.out_que:
            return self.out_que.pop(0)
    def configure_filter(self, config: MicroDataFilterConfig) -> None:
        """Called to configure the data filter.

This method must raise an exception if data format assigned to output or input pipe is invalid.
"""
        raise NotImplementedError
    def on_input_closed(self, pipe: DataPipe, session: Session, msg: Message) -> None:
        """General callback that logs info(OK) or error, and closes the input file."""
        if __debug__: log.debug('%s.on_pipe_closed [%s]', self.__class__.__name__, pipe.pipe_id)
        # if we still have data in input queue and pipe was closed normally, process them
        if msg.type_data == ErrorCode.OK:
            # this can turn out any way, so ignore errors
            try:
                self.finish_processing(session)
            except:
                pass
        # If we have active output, signal end of data
        if self.out_pipe.hnd.is_active():
            self.out_que.append(END_OF_DATA)
        # If both pipes are closed and we should stop, schedule shutdown
        if (not self.in_pipe.hnd.is_active() and
            not self.out_pipe.hnd.is_active() and self.stop_on_close):
            self.mngr.defer(self.__deferred_shutdown)
    def on_output_closed(self, pipe: DataPipe, session: Session, msg: Message) -> None:
        """General callback that logs info(OK) or error, and closes the input file."""
        if __debug__: log.debug('%s.on_pipe_closed [%s]', self.__class__.__name__, pipe.pipe_id)
        # close input as well
        if self.in_pipe.hnd.is_active():
            self.in_pipe.close()
        self.out_que.clear() # clear the out queue, we may wait for another consumer
        # If both pipes are closed and we should stop, schedule shutdown
        if (not self.in_pipe.hnd.is_active() and
            not self.out_pipe.hnd.is_active() and self.stop_on_close):
            self.mngr.defer(self.__deferred_shutdown)
    def initialize(self, svc: BaseService) -> None:
        super().initialize(svc)
        self.in_chn = DealerChannel(b'%s-in' % self.instance_id.hex().encode('ascii'),
                                      sock_opts=self.get('in_sock_opts', None))
        self.out_chn = DealerChannel(b'%s-out' % self.instance_id.hex().encode('ascii'),
                                      sock_opts=self.get('out_sock_opts', None))
        self.in_pipe.set_channel(self.in_chn)
        self.out_pipe.set_channel(self.out_chn)
        self.mngr.add(self.in_chn)
        self.mngr.add(self.out_chn)
    def configure(self, svc: BaseService, config: MicroDataFilterConfig) -> None:
        """Service configuration."""
        config.validate() # Fail early
        self.stop_on_close = config.stop_on_close.value
        # Input data pipe
        self.in_pipe.pipe_id = config.input_pipe.value
        self.in_pipe.address = config.input_address.value
        self.in_pipe.batch_size = config.input_batch_size.value
        self.in_pipe.set_format(config.input_format)
        # batch_size must be assigned before set_mode()
        self.in_pipe.set_mode(config.input_mode.value)
        self.in_pipe.on_accept_data = self.accept_input
        # Output data pipe
        self.out_pipe.pipe_id = config.output_pipe.value
        self.out_pipe.address = config.output_address.value
        self.out_pipe.batch_size = config.output_batch_size.value
        self.out_pipe.set_format(config.output_format)
        # batch_size must be assigned before set_mode()
        self.out_pipe.set_mode(config.output_mode.value)
        self.out_pipe.on_produce_data = self.produce_output
        #
        self.configure_filter(config)
        # Open pipes
        self.facilities = 0
        if self.in_pipe.mode == SocketMode.BIND:
            self.facilities |= ServiceFacilities.INPUT_AS_SERVER
            self.in_pipe.open()
        else:
            self.facilities |= ServiceFacilities.INPUT_AS_CLIENT
            self.mngr.defer(self.in_pipe.open)
        if self.out_pipe.mode == SocketMode.BIND:
            self.facilities |= ServiceFacilities.OUTPUT_AS_SERVER
            self.out_pipe.open()
        else:
            self.facilities |= ServiceFacilities.OUTPUT_AS_CLIENT
            self.mngr.defer(self.out_pipe.open)
    def finalize(self, svc: BaseService) -> None:
        """Service finalization."""
        for pipe in (self.in_pipe, self.out_pipe):
            pipe.close()
        super().finalize(svc)

