#coding:utf-8
#
# PROGRAM/MODULE: Saturnin microservices
# FILE:           fb_trace_parse/service.py
# DESCRIPTION:    Firebird trace parser microservice
# CREATED:        18.01.2021
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
# Copyright (c) 2021 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin microservices - Firebird trace parser microservice

This microservice is a DATA_FILTER that reads blocks of Firebird trace session text protocol
from input data pipe, and sends parsed Firebird trace entries into output data pipe.
"""

from __future__ import annotations
from typing import List, cast
from firebird.base.types import STOP
from firebird.base.protobuf import create_message
from firebird.lib.trace import TraceParser, AttachmentInfo, TransactionInfo, ServiceInfo, \
     SQLInfo, ParamSet, EventTraceInit, EventTraceSuspend, EventTraceFinish, EventCreate, \
     EventDrop, EventAttach, EventDetach, EventTransactionStart, EventCommit, EventRollback, \
     EventCommitRetaining, EventRollbackRetaining, EventPrepareStatement, \
     EventStatementStart, EventStatementFinish, EventFreeStatement, EventCloseCursor, \
     EventTriggerStart, EventTriggerFinish, EventProcedureStart, EventProcedureFinish, \
     EventServiceAttach, EventServiceDetach, EventServiceStart, EventServiceQuery, \
     EventSetContext, EventError, EventWarning, EventServiceError, EventServiceWarning, \
     EventSweepStart, EventSweepProgress, EventSweepFinish, EventSweepFailed, \
     EventBLRCompile, EventBLRExecute, EventDYNExecute, EventUnknown, Status, AccessStats
from saturnin.base import StopError, MIME, MIME_TYPE_TEXT, MIME_TYPE_PROTO, Channel, SocketMode
from saturnin.lib.data.filter import DataFilterMicro, ErrorCode, FBDPSession, FBDPMessage
from .api import FbTraceParserConfig, TRACE_PROTO

# Classes

class FbTraceParserMicro(DataFilterMicro):
    """Implementation of Firebird trace parser microservice.
    """
    STATUS_MAP = [Status.UNKNOWN, Status.OK, Status.FAILED, Status.UNAUTHORIZED]
    def initialize(self, config: FbTraceParserConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        self.log_context = 'main'
        #
        self.proto = create_message(TRACE_PROTO)
        self.entry_buf: List[str] = []
        self.parser: TraceParser = TraceParser()
        self.input_lefover = None
        #
        self.data_map: Dict = {AttachmentInfo: self.store_att_info,
                               TransactionInfo: self.store_tra_info,
                               ServiceInfo: self.store_svc_info,
                               SQLInfo: self.store_sql_info,
                               ParamSet: self.store_param_set,
                               EventTraceInit: self.store_trace_init,
                               EventTraceSuspend: self.store_trace_suspend,
                               EventTraceFinish: self.store_trace_finish,
                               EventCreate: self.store_db_create,
                               EventDrop: self.store_db_drop,
                               EventAttach: self.store_db_attach,
                               EventDetach: self.store_db_detach,
                               EventTransactionStart: self.store_tra_start,
                               EventCommit: self.store_commit,
                               EventRollback: self.store_rollback,
                               EventCommitRetaining: self.store_commit_retain,
                               EventRollbackRetaining: self.store_rollback_retain,
                               EventPrepareStatement: self.store_stm_prepare,
                               EventStatementStart: self.store_stm_start,
                               EventStatementFinish: self.store_smt_finish,
                               EventFreeStatement: self.store_stm_free,
                               EventCloseCursor: self.store_cursor_close,
                               EventTriggerStart: self.store_trigger_start,
                               EventTriggerFinish: self.store_trigger_finish,
                               EventProcedureStart: self.store_proc_start,
                               EventProcedureFinish: self.store_proc_finish,
                               EventServiceAttach: self.store_svc_attach,
                               EventServiceDetach: self.store_svc_detach,
                               EventServiceStart: self.store_svc_start,
                               EventServiceQuery: self.store_svc_query,
                               EventSetContext: self.store_ctx_set,
                               EventError: self.store_error,
                               EventWarning: self.store_warning,
                               EventServiceError: self.store_svc_error,
                               EventServiceWarning: self.store_svc_warning,
                               EventSweepStart: self.store_swp_start,
                               EventSweepProgress: self.store_swp_progress,
                               EventSweepFinish: self.store_swp_finish,
                               EventSweepFailed: self.store_swp_fail,
                               EventBLRCompile: self.store_blr_compile,
                               EventBLRExecute: self.store_blr_exec,
                               EventDYNExecute: self.store_dyn_exec,
                               EventUnknown: self.store_unknown}
        #
        if self.input_pipe_mode is SocketMode.CONNECT:
            self.input_protocol.on_init_session = self.handle_init_session
    def store_att_info(self, data: AttachmentInfo) -> None:
        self.proto.att_info.id = data.attachment_id
        self.proto.att_info.database = data.database
        self.proto.att_info.charset = data.charset
        self.proto.att_info.protocol = data.protocol
        self.proto.att_info.address = data.address
        self.proto.att_info.user = data.user
        self.proto.att_info.role = data.role
        self.proto.att_info.remote_process = data.remote_process
        self.proto.att_info.remote_pid = data.remote_pid
    def store_tra_info(self, data: TransactionInfo) -> None:
        self.proto.tra_info.id = data.transaction_id
        self.proto.tra_info.att_id = data.attachment_id
        self.proto.tra_info.options.extend(data.options)
    def store_svc_info(self, data: ServiceInfo) -> None:
        self.proto.svc_info.id = data.service_id
        self.proto.svc_info.user = data.user
        self.proto.svc_info.protocol = data.protocol
        self.proto.svc_info.address = data.address
        self.proto.svc_info.remote_process = data.remote_process
        self.proto.svc_info.remote_pid = data.remote_pid
    def store_sql_info(self, data: SQLInfo) -> None:
        self.proto.sql_info.id = data.sql_id
        self.proto.sql_info.sql = data.sql
        self.proto.sql_info.plan = data.plan
    def store_param_set(self, data: ParamSet) -> None:
        self.proto.params.id = data.par_id
        for p_type, p_value in data.params:
            param = self.proto.params.params.add()
            param.type = p_type
            if p_value is None:
                p_value = '<NULL>'
            elif p_type in ['smallint', 'integer', 'bigint', 'float', 'double precision']:
                p_value = str(p_value)
            elif p_type == 'timestamp':
                p_value = p_value.strftime('%Y-%m-%dT%H:%M:%S.%f')
            elif p_type == 'date':
                p_value = p_value.strftime('%Y-%m-%d')
            elif p_type == 'time':
                p_value = p_value.strftime('%H:%M:%S.%f')
            param.value = p_value
    def store_event(self, proto, data: EventTraceInit) -> None:
        proto.event.id = data.event_id
        proto.event.timestamp.FromDatetime(data.timestamp)
    def store_access(self, proto, data: List[AccessStats]) -> None:
        for acc in data:
            p = proto.access.add()
            p.table = acc.table
            p.natural = acc.natural
            p.index = acc.index
            p.update = acc.update
            p.insert = acc.insert
            p.delete = acc.delete
            p.backout = acc.backout
            p.purge = acc.purge
            p.expunge = acc.expunge
    def store_trace_init(self, data: EventTraceInit) -> None:
        self.proto.trace_init.session = data.session_name
        self.store_event(self.proto.trace_init, data)
    def store_trace_suspend(self, data: EventTraceSuspend) -> None:
        self.proto.trace_suspend.session = data.session_name
        self.store_event(self.proto.trace_suspend, data)
    def store_trace_finish(self, data: EventTraceFinish) -> None:
        self.proto.trace_finish.session = data.session_name
        self.store_event(self.proto.trace_finish, data)
    def store_db_create(self, data: EventCreate) -> None:
        self.proto.db_create.status = self.STATUS_MAP.index(data.status)
        self.proto.db_create.att_id = data.attachment_id
        self.proto.db_create.database = data.database
        self.proto.db_create.charset = data.charset
        self.proto.db_create.protocol = data.protocol
        self.proto.db_create.address = data.address
        self.proto.db_create.user = data.user
        self.proto.db_create.role = data.role
        self.proto.db_create.remote_process = data.remote_process
        self.proto.db_create.remote_pid = data.remote_pid
        self.store_event(self.proto.db_create, data)
    def store_db_drop(self, data: EventDrop) -> None:
        self.proto.db_drop.status = self.STATUS_MAP.index(data.status)
        self.proto.db_drop.att_id = data.attachment_id
        self.proto.db_drop.database = data.database
        self.proto.db_drop.charset = data.charset
        self.proto.db_drop.protocol = data.protocol
        self.proto.db_drop.address = data.address
        self.proto.db_drop.user = data.user
        self.proto.db_drop.role = data.role
        self.proto.db_drop.remote_process = data.remote_process
        self.proto.db_drop.remote_pid = data.remote_pid
        self.store_event(self.proto.db_drop, data)
    def store_db_attach(self, data: EventAttach) -> None:
        self.proto.db_attach.status = self.STATUS_MAP.index(data.status)
        self.proto.db_attach.att_id = data.attachment_id
        self.proto.db_attach.database = data.database
        self.proto.db_attach.charset = data.charset
        self.proto.db_attach.protocol = data.protocol
        self.proto.db_attach.address = data.address
        self.proto.db_attach.user = data.user
        self.proto.db_attach.role = data.role
        self.proto.db_attach.remote_process = data.remote_process
        self.proto.db_attach.remote_pid = data.remote_pid
        self.store_event(self.proto.db_attach, data)
    def store_db_detach(self, data: EventDetach) -> None:
        self.proto.db_detach.status = self.STATUS_MAP.index(data.status)
        self.proto.db_detach.att_id = data.attachment_id
        self.proto.db_detach.database = data.database
        self.proto.db_detach.charset = data.charset
        self.proto.db_detach.protocol = data.protocol
        self.proto.db_detach.address = data.address
        self.proto.db_detach.user = data.user
        self.proto.db_detach.role = data.role
        self.proto.db_detach.remote_process = data.remote_process
        self.proto.db_detach.remote_pid = data.remote_pid
        self.store_event(self.proto.db_detach, data)
    def store_tra_start(self, data: EventTransactionStart) -> None:
        self.proto.tra_start.status = self.STATUS_MAP.index(data.status)
        self.proto.tra_start.att_id = data.attachment_id
        self.proto.tra_start.tra_id = data.transaction_id
        self.proto.tra_start.options.extend(data.options)
        self.store_event(self.proto.tra_start, data)
    def store_commit(self, data: EventCommit) -> None:
        self.proto.tra_commit.status = self.STATUS_MAP.index(data.status)
        self.proto.tra_commit.att_id = data.attachment_id
        self.proto.tra_commit.tra_id = data.transaction_id
        self.proto.tra_commit.options.extend(data.options)
        self.proto.tra_commit.run_time = data.run_time
        self.proto.tra_commit.reads = data.reads
        self.proto.tra_commit.writes = data.writes
        self.proto.tra_commit.fetches = data.fetches
        self.proto.tra_commit.marks = data.marks
        self.store_event(self.proto.tra_commit, data)
    def store_rollback(self, data: EventRollback) -> None:
        self.proto.tra_rollback.status = self.STATUS_MAP.index(data.status)
        self.proto.tra_rollback.att_id = data.attachment_id
        self.proto.tra_rollback.tra_id = data.transaction_id
        self.proto.tra_rollback.options.extend(data.options)
        self.proto.tra_rollback.run_time = data.run_time
        self.proto.tra_rollback.reads = data.reads
        self.proto.tra_rollback.writes = data.writes
        self.proto.tra_rollback.fetches = data.fetches
        self.proto.tra_rollback.marks = data.marks
        self.store_event(self.proto.tra_rollback, data)
    def store_commit_retain(self, data: EventCommitRetaining) -> None:
        self.store_event(data)
        self.proto.tra_commit_retain.status = self.STATUS_MAP.index(data.status)
        self.proto.tra_commit_retain.att_id = data.attachment_id
        self.proto.tra_commit_retain.tra_id = data.transaction_id
        self.proto.tra_commit_retain.options.extend(data.options)
        self.proto.tra_commit_retain.run_time = data.run_time
        self.proto.tra_commit_retain.reads = data.reads
        self.proto.tra_commit_retain.writes = data.writes
        self.proto.tra_commit_retain.fetches = data.fetches
        self.proto.tra_commit_retain.marks = data.marks
    def store_rollback_retain(self, data: EventRollbackRetaining) -> None:
        self.proto.tra_rollback_retain.status = self.STATUS_MAP.index(data.status)
        self.proto.tra_rollback_retain.att_id = data.attachment_id
        self.proto.tra_rollback_retain.tra_id = data.transaction_id
        self.proto.tra_rollback_retain.options.extend(data.options)
        self.proto.tra_rollback_retain.run_time = data.run_time
        self.proto.tra_rollback_retain.reads = data.reads
        self.proto.tra_rollback_retain.writes = data.writes
        self.proto.tra_rollback_retain.fetches = data.fetches
        self.proto.tra_rollback_retain.marks = data.marks
        self.store_event(self.proto.tra_rollback_retain, data)
    def store_stm_prepare(self, data: EventPrepareStatement) -> None:
        self.proto.stm_prepare.status = self.STATUS_MAP.index(data.status)
        self.proto.stm_prepare.att_id = data.attachment_id
        self.proto.stm_prepare.tra_id = data.transaction_id
        self.proto.stm_prepare.stm_id = data.statement_id
        self.proto.stm_prepare.sql_id = data.sql_id
        self.proto.stm_prepare.prepare = data.prepare_time
        self.store_event(self.proto.stm_prepare, data)
    def store_stm_start(self, data: EventStatementStart) -> None:
        self.proto.stm_start.status = self.STATUS_MAP.index(data.status)
        self.proto.stm_start.att_id = data.attachment_id
        self.proto.stm_start.tra_id = data.transaction_id
        self.proto.stm_start.stm_id = data.statement_id
        self.proto.stm_start.sql_id = data.sql_id
        self.proto.stm_start.param_id = data.param_id
        self.store_event(self.proto.stm_start, data)
    def store_smt_finish(self, data: EventStatementFinish) -> None:
        self.proto.stm_finish.status = self.STATUS_MAP.index(data.status)
        self.proto.stm_finish.att_id = data.attachment_id
        self.proto.stm_finish.tra_id = data.transaction_id
        self.proto.stm_finish.stm_id = data.statement_id
        self.proto.stm_finish.sql_id = data.sql_id
        self.proto.stm_finish.param_id = data.param_id
        self.proto.stm_finish.records = data.records
        self.proto.stm_finish.run_time = data.run_time
        self.proto.stm_finish.reads = data.reads
        self.proto.stm_finish.writes = data.writes
        self.proto.stm_finish.fetches = data.fetches
        self.proto.stm_finish.marks = data.marks
        self.store_access(self.proto.stm_finish, data.access)
        self.store_event(self.proto.stm_finish, data)
    def store_stm_free(self, data: EventFreeStatement) -> None:
        self.proto.stm_free.att_id = data.attachment_id
        self.proto.stm_free.tra_id = data.transaction_id
        self.proto.stm_free.stm_id = data.statement_id
        self.proto.stm_free.sql_id = data.sql_id
        self.store_event(self.proto.stm_free, data)
    def store_cursor_close(self, data: EventCloseCursor) -> None:
        self.proto.cursor_close.att_id = data.attachment_id
        self.proto.cursor_close.tra_id = data.transaction_id
        self.proto.cursor_close.stm_id = data.statement_id
        self.proto.cursor_close.sql_id = data.sql_id
        self.store_event(self.proto.cursor_close, data)
    def store_trigger_start(self, data: EventTriggerStart) -> None:
        self.proto.trigger_start.status = self.STATUS_MAP.index(data.status)
        self.proto.trigger_start.att_id = data.attachment_id
        self.proto.trigger_start.tra_id = data.transaction_id
        self.proto.trigger_start.trigger = data.trigger
        self.proto.trigger_start.table = data.table
        self.proto.trigger_start.t_event = data.event
        self.store_event(self.proto.trigger_start, data)
    def store_trigger_finish(self, data: EventTriggerFinish) -> None:
        self.proto.trigger_finish.status = self.STATUS_MAP.index(data.status)
        self.proto.trigger_finish.att_id = data.attachment_id
        self.proto.trigger_finish.tra_id = data.transaction_id
        self.proto.trigger_finish.trigger = data.trigger
        self.proto.trigger_finish.table = data.table
        self.proto.trigger_finish.t_event = data.event
        self.proto.trigger_finish.run_time = data.run_time
        self.proto.trigger_finish.reads = data.reads
        self.proto.trigger_finish.writes = data.writes
        self.proto.trigger_finish.fetches = data.fetches
        self.proto.trigger_finish.marks = data.marks
        self.store_access(self.proto.trigger_finish, data.access)
        self.store_event(self.proto.trigger_finish, data)
    def store_proc_start(self, data: EventProcedureStart) -> None:
        self.proto.proc_start.status = self.STATUS_MAP.index(data.status)
        self.proto.proc_start.att_id = data.attachment_id
        self.proto.proc_start.tra_id = data.transaction_id
        self.proto.proc_start.procedure = data.procedure
        self.proto.proc_start.param_id  = data.param_id
        self.store_event(self.proto.proc_start, data)
    def store_proc_finish(self, data: EventProcedureFinish) -> None:
        self.proto.proc_finish.status = self.STATUS_MAP.index(data.status)
        self.proto.proc_finish.att_id = data.attachment_id
        self.proto.proc_finish.tra_id = data.transaction_id
        self.proto.proc_finish.procedure = data.procedure
        self.proto.proc_finish.param_id  = data.param_id
        self.proto.proc_finish.run_time = data.run_time
        self.proto.proc_finish.reads = data.reads
        self.proto.proc_finish.writes = data.writes
        self.proto.proc_finish.fetches = data.fetches
        self.proto.proc_finish.marks = data.marks
        self.store_access(self.proto.proc_finish, data.access)
        self.store_event(self.proto.proc_finish, data)
    def store_svc_attach(self, data: EventServiceAttach) -> None:
        self.proto.svc_attach.status = self.STATUS_MAP.index(data.status)
        self.proto.svc_attach.svc_id = data.service_id
        self.store_event(self.proto.svc_attach, data)
    def store_svc_detach(self, data: EventServiceDetach) -> None:
        self.proto.svc_detach.status = self.STATUS_MAP.index(data.status)
        self.proto.svc_detach.svc_id = data.service_id
        self.store_event(self.proto.svc_detach, data)
    def store_svc_start(self, data: EventServiceStart) -> None:
        self.proto.status = self.STATUS_MAP.index(data.status)
        self.proto.svc_start.svc_id = data.service_id
        self.proto.svc_start.action = data.action
        self.proto.svc_start.params.extend(data.parameters)
        self.store_event(self.proto.svc_start, data)
    def store_svc_query(self, data: EventServiceQuery) -> None:
        self.proto.svc_query.status = self.STATUS_MAP.index(data.status)
        self.proto.svc_query.svc_id = data.service_id
        self.proto.svc_query.action = data.action
        self.proto.svc_query.params.extend(data.parameters)
        self.store_event(self.proto.svc_query, data)
    def store_ctx_set(self, data: EventSetContext) -> None:
        self.proto.ctx_set.att_id = data.attachment_id
        self.proto.ctx_set.tra_id = data.transaction_id
        self.proto.ctx_set.context = data.context
        self.proto.ctx_set.key = data.key
        self.proto.ctx_set.value = data.value
        self.store_event(self.proto.ctx_set, data)
    def store_error(self, data: EventError) -> None:
        self.proto.error.att_id = data.attachment_id
        self.proto.error.place = data.place
        self.proto.error.details.extend(data.details)
        self.store_event(self.proto.error, data)
    def store_warning(self, data: EventWarning) -> None:
        self.proto.warning.att_id = data.attachment_id
        self.proto.warning.place = data.place
        self.proto.warning.details.extend(data.details)
        self.store_event(self.proto.warning, data)
    def store_svc_error(self, data: EventServiceError) -> None:
        self.proto.svc_error.svc_id = data.service_id
        self.proto.svc_error.place = data.place
        self.proto.svc_error.details.extend(data.details)
        self.store_event(self.proto.svc_error, data)
    def store_svc_warning(self, data: EventServiceWarning) -> None:
        self.proto.svc_warning.svc_id = data.service_id
        self.proto.svc_warning.place = data.place
        self.proto.svc_warning.details.extend(data.details)
        self.store_event(self.proto.svc_warning, data)
    def store_swp_start(self, data: EventSweepStart) -> None:
        self.store_event(self.proto.swp_start, data)
        self.proto.swp_start.att_id = data.attachment_id
        self.proto.swp_start.oit = data.oit
        self.proto.swp_start.oat = data.oat
        self.proto.swp_start.ost = data.ost
        self.proto.swp_start.next = data.next
    def store_swp_progress(self, data: EventSweepProgress) -> None:
        self.proto.swp_progress.att_id = data.attachment_id
        self.proto.swp_progress.run_time = data.run_time
        self.proto.swp_progress.reads = data.reads
        self.proto.swp_progress.writes = data.writes
        self.proto.swp_progress.fetches = data.fetches
        self.proto.swp_progress.marks = data.marks
        self.store_access(self.proto.swp_progress, data.access)
        self.store_event(self.proto.swp_progress, data)
    def store_swp_finish(self, data: EventSweepFinish) -> None:
        self.store_event(self.proto.swp_finish, data)
        self.proto.swp_finish.att_id = data.attachment_id
        self.proto.swp_finish.oit = data.oit
        self.proto.swp_finish.oat = data.oat
        self.proto.swp_finish.ost = data.ost
        self.proto.swp_finish.next = data.next
        self.proto.swp_finish.run_time = data.run_time
        self.proto.swp_finish.reads = data.reads
        self.proto.swp_finish.writes = data.writes
        self.proto.swp_finish.fetches = data.fetches
        self.proto.swp_finish.marks = data.marks
        self.store_event(self.proto.swp_finish, data)
    def store_swp_fail(self, data: EventSweepFailed) -> None:
        self.proto.swp_fail.att_id = data.attachment_id
        self.store_event(self.proto.swp_fail, data)
    def store_blr_compile(self, data: EventBLRCompile) -> None:
        self.proto.blr_compile.status = self.STATUS_MAP.index(data.status)
        self.proto.blr_compile.att_id = data.attachment_id
        self.proto.blr_compile.stm_id = data.statement_id
        self.proto.blr_compile.content = data.content
        self.proto.blr_compile.prepare = data.prepare_time
        self.store_event(self.proto.blr_compile, data)
    def store_blr_exec(self, data: EventBLRExecute) -> None:
        self.proto.blr_exec.status = self.STATUS_MAP.index(data.status)
        self.proto.blr_exec.att_id = data.attachment_id
        self.proto.blr_exec.tra_id = data.transaction_id
        self.proto.blr_exec.stm_id = data.statement_id
        self.proto.blr_exec.content = data.content
        self.proto.blr_exec.run_time = data.run_time
        self.proto.blr_exec.reads = data.reads
        self.proto.blr_exec.writes = data.writes
        self.proto.blr_exec.fetches = data.fetches
        self.proto.blr_exec.marks = data.marks
        self.store_access(self.proto.blr_exec, data.access)
        self.store_event(self.proto.blr_exec, data)
    def store_dyn_exec(self, data: EventDYNExecute) -> None:
        self.proto.dyn_exec.status = self.STATUS_MAP.index(data.status)
        self.proto.dyn_exec.att_id = data.attachment_id
        self.proto.dyn_exec.tra_id = data.transaction_id
        self.proto.dyn_exec.content = data.content
        self.proto.dyn_exec.run_time = data.run_time
        self.store_event(self.proto.dyn_exec, data)
    def store_unknown(self, data: EventUnknown) -> None:
        self.proto.unknown.data = data.data
        self.store_event(self.proto.unknown, data)
    def handle_init_session(self, channel: Channel, session: FBDPSession) -> None:
        """Event executed from `send_open()` to set additional information to newly
        created session instance.
        """
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
    def handle_input_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Event handler executed when client connects to INPUT data pipe via OPEN message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        The session attributes `data_pipe`, `pipe_socket`, `data_format` and `params`
        contain information sent by client, and the event handler validates the request.

        If request should be rejected, it raises the `StopError` exception with `code`
        attribute containing the `ErrorCode` to be returned in CLOSE message.
        """
        super().handle_input_accept_client(channel, session)
        if cast(MIME, session.data_format).mime_type != MIME_TYPE_TEXT:
            raise StopError(f"MIME type '{cast(MIME, session.data_format).mime_type}' is not a valid input format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        for param in cast(MIME, session.data_format).params.keys():
            if param not in ('charset', 'errors'):
                raise StopError(f"Unknown MIME parameter '{param}'",
                                code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        # cache attributes
        session.charset = cast(MIME, session.data_format).params.get('charset', 'ascii')
        session.errors = cast(MIME, session.data_format).params.get('errors', 'strict')
    def handle_output_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Event handler executed when client connects to OUTPUT data pipe via OPEN message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        The session attributes `data_pipe`, `pipe_socket`, `data_format` and `params`
        contain information sent by client, and the event handler validates the request.

        If request should be rejected, it raises the `StopError` exception with `code`
        attribute containing the `ErrorCode` to be returned in CLOSE message.
        """
        super().handle_output_accept_client(channel, session)
        if cast(MIME, session.data_format).mime_type != MIME_TYPE_PROTO:
            raise StopError(f"MIME type '{cast(MIME, session.data_format).mime_type}' is not a valid output format",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        if (_type := cast(MIME, session.data_format).params['type']) != TRACE_PROTO:
            raise StopError(f"Unsupported protobuf type '{_type}'",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
    def handle_output_produce_data(self, channel: Channel, session: FBDPSession, msg: FBDPMessage) -> None:
        """Event handler executed to store data into outgoing DATA message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            msg: DATA message that will be sent to client.

        Important:
            The base implementation simply raises StopError with ErrorCode.OK code, so
            the descendant class must override this method without super() call.

            The event handler must `popleft()` data from `output` queue and store them in
            `msg.data_frame` attribute. It may also set ACK-REQUEST flag and `type_data`
            attribute.

            The event handler may cancel the transmission by raising the `StopError`
            exception with `code` attribute containing the `ErrorCode` to be returned in
            CLOSE message.

        Note:
            To indicate end of data, raise StopError with ErrorCode.OK code.
        """
        if not self.output:
            raise StopError("EOF", code=ErrorCode.OK)
        data = self.output.popleft()
        try:
            self.proto.Clear()
            store = self.data_map[type(data)]
            store(data)
            msg.data_frame = self.proto.SerializeToString()
        except Exception as exc:
            raise StopError("Exception", code=ErrorCode.INVALID_DATA) from exc
    def handle_input_accept_data(self, channel: Channel, session: FBDPSession, data: bytes) -> None:
        """Event handler executed to process data received in DATA message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            data: Data received from client.

        Important:
            Any output data produced by event handler must be stored into output queue via
            `store_output()` method.

            The base implementation simply raises StopError with ErrorCode.OK code, so
            the descendant class must override this method without super() call.

            The event handler may cancel the transmission by raising the `StopError`
            exception with `code` attribute containing the `ErrorCode` to be returned in
            CLOSE message.

        Note:
            The ACK-REQUEST in received DATA message is handled automatically by protocol.
        """
        try:
            block: str = data.decode(encoding=session.charset, errors=session.errors)
        except UnicodeError as exc:
            raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
        if self.input_lefover is not None:
            block = self.input_lefover + block
            self.input_lefover = None
        lines = block.splitlines()
        if block[-1] != '\n':
            self.input_lefover = lines.pop()
        batch = []
        for line in lines:
            if (entry := self.parser.push(line)) is not None:
                batch.extend(entry)
        if batch:
            self.store_batch_output(batch)
    def finish_input_processing(self, channel: Channel, session: FBDPSession, code: ErrorCode) -> None:
        """Called when input pipe is closed while output pipe will remain open.

        When code is ErrorCode.OK, the input was closed normally. Otherwise it indicates
        the type of problem that caused the input to be closed.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with peer.
            code:    Input pipe closing ErrorCode.

        Note:
            This method is not called when code is not ErrorCode.OK and `propagate_input_error`
            option is True.

            The default implementation does nothing.
        """
        if (entry := self.parser.push(STOP)) is not None:
            self.store_batch_output(entry)
