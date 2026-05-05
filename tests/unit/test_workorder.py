"""
BM-02 工单管理模块单元测试
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.insert(0, '/workspace/itops_platform')

from modules.foundation.db_models.base import Base
from modules.foundation.db_models.workorder import (
    WorkOrder, WorkOrderFlow, WorkOrderType, WorkOrderStatus, WorkOrderPriority
)
from modules.business.workorder.workorder import WorkOrderCore
from modules.business.workorder.flow import FlowEngine, FlowNodeType
from modules.business.workorder.approval import ApprovalHandler, ApprovalStatus, ApprovalMode
from modules.business.workorder.stats import WorkOrderStats
from modules.business.workorder.change import ChangeManager, ChangeStatus


# 测试数据库配置
TEST_DB_URL = 'sqlite:///:memory:'


@pytest.fixture
def db_engine():
    """创建测试数据库引擎"""
    engine = create_engine(TEST_DB_URL, echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """创建测试数据库会话"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def workorder_core(db_session):
    """创建工单核心对象"""
    return WorkOrderCore(db_session)


@pytest.fixture
def flow_engine(db_session):
    """创建流程引擎对象"""
    return FlowEngine(db_session)


@pytest.fixture
def approval_handler(db_session):
    """创建审批处理器对象"""
    return ApprovalHandler(db_session)


@pytest.fixture
def stats_handler(db_session):
    """创建统计分析对象"""
    return WorkOrderStats(db_session)


@pytest.fixture
def change_manager(db_session, workorder_core):
    """创建变更管理器对象"""
    return ChangeManager(db_session)


class TestWorkOrderCore:
    """工单核心功能测试"""
    
    def test_generate_order_no(self, workorder_core):
        """测试工单编号生成"""
        order_no = workorder_core.generate_order_no(WorkOrderType.FAULT)
        assert order_no.startswith('FAU')
        assert len(order_no) == 15
    
    def test_create_workorder(self, workorder_core):
        """测试创建工单"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user',
            description='Test description',
            priority=WorkOrderPriority.P2
        )
        
        assert workorder.id is not None
        assert workorder.order_no.startswith('FAU')
        assert workorder.title == 'Test WorkOrder'
        assert workorder.status == WorkOrderStatus.PENDING
        assert workorder.priority == WorkOrderPriority.P2
    
    def test_get_by_id(self, workorder_core):
        """测试根据ID获取工单"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        result = workorder_core.get_by_id(workorder.id)
        assert result is not None
        assert result.id == workorder.id
        assert result.title == 'Test WorkOrder'
    
    def test_get_by_id_not_found(self, workorder_core):
        """测试根据ID获取不存在的工单"""
        result = workorder_core.get_by_id(99999)
        assert result is None
    
    def test_list_workorders(self, workorder_core):
        """测试查询工单列表"""
        # 创建多个工单
        for i in range(5):
            workorder_core.create(
                title=f'Test WorkOrder {i}',
                order_type=WorkOrderType.FAULT,
                creator='test_user'
            )
        
        results, total = workorder_core.list(page=1, page_size=10)
        assert total == 5
        assert len(results) == 5
    
    def test_list_filter_by_status(self, workorder_core):
        """测试按状态过滤查询"""
        wo = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        results, total = workorder_core.list(status=WorkOrderStatus.PENDING)
        assert total >= 1
        
        results, total = workorder_core.list(status=WorkOrderStatus.CLOSED)
        assert total == 0
    
    def test_update_workorder(self, workorder_core):
        """测试更新工单"""
        workorder = workorder_core.create(
            title='Original Title',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        updated = workorder_core.update(
            workorder.id,
            operator='test_user',
            title='Updated Title',
            description='Updated description'
        )
        
        assert updated.title == 'Updated Title'
        assert updated.description == 'Updated description'
    
    def test_change_status(self, workorder_core):
        """测试状态变更"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        success, msg, wo = workorder_core.change_status(
            workorder.id,
            WorkOrderStatus.PROCESSING,
            'test_user'
        )
        
        assert success is True
        assert wo.status == WorkOrderStatus.PROCESSING
        
        # 验证状态已持久化到数据库
        refreshed_wo = workorder_core.get_by_id(workorder.id)
        assert refreshed_wo.status == WorkOrderStatus.PROCESSING
    
    def test_assign_workorder(self, workorder_core):
        """测试分配工单"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        success, msg, wo = workorder_core.assign(
            workorder.id,
            assignee='handler_user',
            assignee_email='handler@example.com'
        )
        
        assert success is True
        assert wo.assignee == 'handler_user'
        assert wo.assignee_email == 'handler@example.com'
    
    def test_add_progress(self, workorder_core):
        """测试添加处理进度"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        progress_data = {'step': 1, 'action': 'diagnosis', 'result': 'completed'}
        success, msg, wo = workorder_core.add_progress(
            workorder.id,
            progress_data,
            'test_user'
        )
        
        assert success is True
        assert wo.handling_progress is not None
        progress = json.loads(wo.handling_progress)
        assert len(progress) == 1
        assert progress[0]['data']['step'] == 1
    
    def test_sla_status(self, workorder_core):
        """测试SLA状态"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user',
            priority=WorkOrderPriority.P2
        )
        
        sla = workorder_core.get_sla_status(workorder.id)
        assert sla['sla_response_time'] == 30
        assert sla['sla_resolve_time'] == 240
    
    def test_pending_count(self, workorder_core):
        """测试待处理工单统计"""
        workorder_core.create(
            title='Test WorkOrder 1',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        workorder_core.create(
            title='Test WorkOrder 2',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        counts = workorder_core.get_pending_count()
        assert counts.get('pending', 0) >= 2
    
    def test_batch_assign(self, workorder_core):
        """测试批量分配"""
        wos = []
        for i in range(3):
            wo = workorder_core.create(
                title=f'Test WorkOrder {i}',
                order_type=WorkOrderType.FAULT,
                creator='test_user'
            )
            wos.append(wo.id)
        
        result = workorder_core.batch_assign(wos, 'handler_user', 'handler@example.com')
        
        assert result['total'] == 3
        assert result['success'] == 3
        assert result['failed'] == 0


class TestFlowEngine:
    """流程引擎测试"""
    
    def test_init_builtin_flows(self, flow_engine):
        """测试内置流程初始化"""
        assert 'standard_workorder' in flow_engine._flow_definitions
        assert 'emergency_fault' in flow_engine._flow_definitions
        assert 'change_management' in flow_engine._flow_definitions
    
    def test_get_flow_definition(self, flow_engine):
        """测试获取流程定义"""
        flow = flow_engine.get_flow_definition('standard_workorder')
        assert flow is not None
        assert flow.name == '标准工单流程'
        assert len(flow.nodes) == 4
    
    def test_flow_nodes(self, flow_engine):
        """测试流程节点"""
        flow = flow_engine.get_flow_definition('standard_workorder')
        
        start_node = flow.get_start_node()
        assert start_node is not None
        assert start_node.type == FlowNodeType.START
        
        end_nodes = flow.get_end_nodes()
        assert len(end_nodes) == 1
        assert end_nodes[0].type == FlowNodeType.END
    
    def test_start_flow(self, flow_engine, workorder_core):
        """测试启动流程"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        instance = flow_engine.start_flow(
            workorder.id,
            'standard_workorder',
            {'initiator': 'test_user'}
        )
        
        assert instance is not None
        assert instance.instance_id.startswith('FLOW-')
        assert instance.status == 'running'
        assert instance.current_node_id == 'start'
    
    def test_execute_node(self, flow_engine, workorder_core):
        """测试执行流程节点"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        instance = flow_engine.start_flow(
            workorder.id,
            'standard_workorder'
        )
        
        success, msg, inst = flow_engine.execute_node(
            instance.id,
            action='complete',
            operator='test_user'
        )
        
        assert success is True
        assert inst.current_node_id == 'process'
    
    def test_flow_history(self, flow_engine, workorder_core):
        """测试流程历史"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        instance = flow_engine.start_flow(workorder.id, 'standard_workorder')
        history = flow_engine.get_flow_history(instance.id)
        
        assert len(history) >= 1
        assert history[0].action == 'enter'


class TestApprovalHandler:
    """审批处理器测试"""
    
    def test_create_approval(self, approval_handler, workorder_core):
        """测试创建审批"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        approvers = [
            {'approver': 'approver1', 'email': 'approver1@example.com', 'role': 'supervisor'},
            {'approver': 'approver2', 'email': 'approver2@example.com', 'role': 'manager'}
        ]
        
        records = approval_handler.create_approval(
            work_order_id=workorder.id,
            approvers=approvers,
            mode=ApprovalMode.ONE,
            timeout_minutes=1440
        )
        
        assert len(records) == 2
        assert records[0].status == ApprovalStatus.PENDING.value
    
    def test_approve(self, approval_handler, workorder_core):
        """测试审批通过"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        approvers = [{'approver': 'approver1', 'email': 'approver1@example.com'}]
        records = approval_handler.create_approval(workorder.id, approvers)
        
        success, msg, record = approval_handler.approve(
            records[0].id,
            'approver1',
            comment='Approved'
        )
        
        assert success is True
        assert record.status == ApprovalStatus.APPROVED.value
        assert record.action == 'approve'
    
    def test_reject(self, approval_handler, workorder_core):
        """测试审批拒绝"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        approvers = [{'approver': 'approver1', 'email': 'approver1@example.com'}]
        records = approval_handler.create_approval(workorder.id, approvers)
        
        success, msg, record = approval_handler.reject(
            records[0].id,
            'approver1',
            comment='Rejected'
        )
        
        assert success is True
        assert record.status == ApprovalStatus.REJECTED.value
        assert record.action == 'reject'
    
    def test_check_approval_complete(self, approval_handler, workorder_core):
        """测试检查审批完成"""
        workorder = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        approvers = [{'approver': 'approver1', 'email': 'approver1@example.com'}]
        records = approval_handler.create_approval(workorder.id, approvers, mode=ApprovalMode.ONE)
        
        result = approval_handler.check_approval_complete(workorder.id)
        assert result['complete'] is False
        
        # 通过审批
        approval_handler.approve(records[0].id, 'approver1')
        
        result = approval_handler.check_approval_complete(workorder.id)
        assert result['complete'] is True
        assert result['result'] == 'approved'
    
    def test_delegation(self, approval_handler):
        """测试审批代理"""
        delegation = approval_handler.create_delegation(
            delegator='user1',
            delegate='user2',
            reason='vacation'
        )
        
        assert delegation is not None
        assert delegation.delegator == 'user1'
        assert delegation.delegate == 'user2'
        assert delegation.is_active is True


class TestWorkOrderStats:
    """统计分析测试"""
    
    def test_workorder_count(self, stats_handler, workorder_core):
        """测试工单数量统计"""
        for i in range(3):
            workorder_core.create(
                title=f'Test WorkOrder {i}',
                order_type=WorkOrderType.FAULT,
                creator='test_user'
            )
        
        counts = stats_handler.get_workorder_count(group_by='status')
        assert len(counts) > 0
    
    def test_processing_time_stats(self, stats_handler, workorder_core):
        """测试处理时效统计"""
        wo = workorder_core.create(
            title='Test WorkOrder',
            order_type=WorkOrderType.FAULT,
            creator='test_user'
        )
        
        stats = stats_handler.get_processing_time_stats()
        assert 'count' in stats
    
    def test_sla_compliance_stats(self, stats_handler, workorder_core):
        """测试SLA合规率统计"""
        stats = stats_handler.get_sla_compliance_stats()
        assert 'total' in stats
        assert 'response_rate' in stats
        assert 'resolve_rate' in stats
    
    def test_satisfaction_stats(self, stats_handler, workorder_core):
        """测试满意度统计"""
        stats = stats_handler.get_satisfaction_stats()
        assert 'total' in stats
    
    def test_category_breakdown(self, stats_handler, workorder_core):
        """测试分类统计"""
        for i in range(5):
            workorder_core.create(
                title=f'Test WorkOrder {i}',
                order_type=WorkOrderType.FAULT,
                creator='test_user'
            )
        
        breakdown = stats_handler.get_category_breakdown('type')
        assert len(breakdown) > 0


class TestChangeManager:
    """变更管理测试"""
    
    def test_generate_change_no(self, change_manager):
        """测试变更编号生成"""
        change_no = change_manager.generate_change_no('normal')
        assert change_no.startswith('CHG-N')
    
    def test_create_change(self, change_manager, workorder_core):
        """测试创建变更"""
        workorder = workorder_core.create(
            title='Change Request',
            order_type=WorkOrderType.CHANGE,
            creator='test_user'
        )
        
        change = change_manager.create(
            work_order_id=workorder.id,
            title='Test Change',
            applicant='test_user',
            change_type='normal',
            risk_level='medium'
        )
        
        assert change.id is not None
        assert change.change_no.startswith('CHG-N')
        assert change.title == 'Test Change'
        assert change.status == ChangeStatus.DRAFT.value
    
    def test_submit_for_review(self, change_manager, workorder_core):
        """测试提交变更评审"""
        workorder = workorder_core.create(
            title='Change Request',
            order_type=WorkOrderType.CHANGE,
            creator='test_user'
        )
        
        change = change_manager.create(
            work_order_id=workorder.id,
            title='Test Change',
            applicant='test_user'
        )
        
        reviewers = [
            {'name': 'reviewer1', 'email': 'reviewer1@example.com', 'role': 'supervisor'}
        ]
        
        success, msg, ch = change_manager.submit_for_review(
            change.id,
            reviewers,
            'CAB'
        )
        
        assert success is True
        assert ch.status == ChangeStatus.PENDING_REVIEW.value
    
    def test_add_review_comment(self, change_manager, workorder_core):
        """测试添加评审意见"""
        workorder = workorder_core.create(
            title='Change Request',
            order_type=WorkOrderType.CHANGE,
            creator='test_user'
        )
        
        change = change_manager.create(
            work_order_id=workorder.id,
            title='Test Change',
            applicant='test_user'
        )
        
        change_manager.submit_for_review(
            change.id,
            [{'name': 'reviewer', 'email': 'reviewer@example.com', 'role': 'supervisor'}]
        )
        
        success, msg, ch = change_manager.add_review_comment(
            change.id,
            'reviewer',
            'Looks good',
            'approve'
        )
        
        assert success is True
        comments = json.loads(ch.review_comments)
        assert len(comments) == 1
    
    def test_schedule_change(self, change_manager, workorder_core):
        """测试变更排期"""
        workorder = workorder_core.create(
            title='Change Request',
            order_type=WorkOrderType.CHANGE,
            creator='test_user'
        )
        
        change = change_manager.create(
            work_order_id=workorder.id,
            title='Test Change',
            applicant='test_user'
        )
        
        # 提交评审并批准
        change_manager.submit_for_review(
            change.id,
            [{'name': 'reviewer', 'email': 'reviewer@example.com', 'role': 'supervisor'}]
        )
        change_manager.add_review_comment(
            change.id, 'reviewer', 'Approved', 'approve'
        )
        change_manager.approve_change(
            change.id, 'approver',
            [{'name': 'approver', 'email': 'approver@example.com'}]
        )
        
        # 排期
        scheduled_start = datetime.now() + timedelta(days=1)
        scheduled_end = datetime.now() + timedelta(days=2)
        
        success, msg, ch = change_manager.schedule(
            change.id,
            scheduled_start,
            scheduled_end
        )
        
        assert success is True
        assert ch.status == ChangeStatus.SCHEDULED.value
    
    def test_implementation_flow(self, change_manager, workorder_core, db_session):
        """测试变更实施流程"""
        workorder = workorder_core.create(
            title='Change Request',
            order_type=WorkOrderType.CHANGE,
            creator='test_user'
        )
        
        change = change_manager.create(
            work_order_id=workorder.id,
            title='Test Change',
            applicant='test_user'
        )
        
        # 简化流程测试 - 直接设置为SCHEDULED
        change.status = ChangeStatus.SCHEDULED.value
        db_session.commit()
        
        success, msg, ch = change_manager.start_implementation(
            change.id,
            'implementor',
            'implementor@example.com'
        )
        
        assert success is True
        assert ch.status == ChangeStatus.IN_PROGRESS.value
        assert ch.implementor == 'implementor'
        
        # 添加实施步骤
        step = {'order': 1, 'name': 'Step 1', 'command': 'echo test'}
        success, msg, ch = change_manager.add_implementation_step(
            change.id,
            step,
            'implementor'
        )
        
        assert success is True
        
        # 完成实施
        success, msg, ch = change_manager.complete_implementation(change.id)
        assert success is True
        assert ch.status == ChangeStatus.COMPLETED.value
    
    def test_verify_change(self, change_manager, workorder_core, db_session):
        """测试验证变更"""
        workorder = workorder_core.create(
            title='Change Request',
            order_type=WorkOrderType.CHANGE,
            creator='test_user'
        )
        
        change = change_manager.create(
            work_order_id=workorder.id,
            title='Test Change',
            applicant='test_user'
        )
        
        # 设置为已完成
        change.status = ChangeStatus.COMPLETED.value
        db_session.commit()
        
        success, msg, ch = change_manager.verify(
            change.id,
            'All tests passed',
            'verifier'
        )
        
        assert success is True
        assert ch.status == ChangeStatus.VERIFIED.value
        assert ch.verification_by == 'verifier'
    
    def test_rollback_change(self, change_manager, workorder_core, db_session):
        """测试回滚变更"""
        workorder = workorder_core.create(
            title='Change Request',
            order_type=WorkOrderType.CHANGE,
            creator='test_user'
        )
        
        change = change_manager.create(
            work_order_id=workorder.id,
            title='Test Change',
            applicant='test_user',
            rollback_plan='Run rollback script'
        )
        
        # 设置为实施中
        change.status = ChangeStatus.IN_PROGRESS.value
        db_session.commit()
        
        success, msg, ch = change_manager.rollback(
            change.id,
            'Test failed',
            'operator'
        )
        
        assert success is True
        assert ch.status == ChangeStatus.ROLLED_BACK.value
        assert ch.rollback_reason == 'Test failed'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
