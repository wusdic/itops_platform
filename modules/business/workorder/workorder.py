"""
工单核心模块
提供工单CRUD操作、状态流转、优先级管理、SLA计时等功能
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from modules.foundation.db_models.workorder import (
    WorkOrder, WorkOrderFlow, WorkOrderType, WorkOrderStatus, WorkOrderPriority
)


class WorkOrderCore:
    """
    工单核心管理类
    
    提供工单的创建、查询、更新、删除等CRUD操作
    支持状态流转、优先级管理和SLA计时
    """
    
    # 状态流转映射: 当前状态 -> 可流转到的状态
    STATUS_TRANSITIONS = {
        WorkOrderStatus.PENDING: [
            WorkOrderStatus.PROCESSING,
            WorkOrderStatus.CANCELLED
        ],
        WorkOrderStatus.PROCESSING: [
            WorkOrderStatus.PENDING_APPROVAL,
            WorkOrderStatus.RESOLVED,
            WorkOrderStatus.CLOSED,
            WorkOrderStatus.CANCELLED
        ],
        WorkOrderStatus.PENDING_APPROVAL: [
            WorkOrderStatus.APPROVED,
            WorkOrderStatus.REJECTED,
            WorkOrderStatus.PROCESSING
        ],
        WorkOrderStatus.APPROVED: [
            WorkOrderStatus.PROCESSING,
            WorkOrderStatus.RESOLVED
        ],
        WorkOrderStatus.REJECTED: [
            WorkOrderStatus.PROCESSING,
            WorkOrderStatus.CLOSED
        ],
        WorkOrderStatus.RESOLVED: [
            WorkOrderStatus.CLOSED,
            WorkOrderStatus.PROCESSING
        ],
        WorkOrderStatus.CLOSED: [],  # 已关闭不能流转
        WorkOrderStatus.CANCELLED: []  # 已取消不能流转
    }
    
    # 优先级SLA配置(分钟)
    SLA_CONFIG = {
        WorkOrderPriority.P1: {'response': 15, 'resolve': 60},
        WorkOrderPriority.P2: {'response': 30, 'resolve': 240},
        WorkOrderPriority.P3: {'response': 60, 'resolve': 480},
        WorkOrderPriority.P4: {'response': 120, 'resolve': 1440}
    }
    
    def __init__(self, db_session: Session):
        """
        初始化工单核心
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
    
    def generate_order_no(self, order_type: WorkOrderType) -> str:
        """
        生成工单编号
        
        格式: {类型缩写}{日期}{序号}
        例如: FAU20260428001
        
        Args:
            order_type: 工单类型
            
        Returns:
            工单编号
        """
        type_prefix = {
            WorkOrderType.FAULT: 'FAU',
            WorkOrderType.CHANGE: 'CHG',
            WorkOrderType.INSPECTION: 'INS',
            WorkOrderType.SECURITY: 'SEC',
            WorkOrderType.DEMAND: 'DEM',
            WorkOrderType.QUESTION: 'QUE',
            WorkOrderType.OTHER: 'OTH'
        }.get(order_type, 'WKO')
        
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 查询当天该类型工单数量
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = self.db.query(WorkOrder).filter(
            WorkOrder.order_type == order_type,
            WorkOrder.created_at >= today_start
        ).count()
        
        sequence = str(count + 1).zfill(4)
        return f"{type_prefix}{date_str}{sequence}"
    
    def create(
        self,
        title: str,
        order_type: WorkOrderType,
        creator: str,
        description: Optional[str] = None,
        priority: WorkOrderPriority = WorkOrderPriority.P3,
        device_id: Optional[int] = None,
        device_name: Optional[str] = None,
        device_ip: Optional[str] = None,
        alert_id: Optional[int] = None,
        business_id: Optional[int] = None,
        business_name: Optional[str] = None,
        impact: Optional[str] = None,
        urgency: Optional[str] = None,
        expected_start: Optional[datetime] = None,
        expected_end: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None,
        remark: Optional[str] = None,
        **kwargs
    ) -> WorkOrder:
        """
        创建工单
        
        Args:
            title: 标题
            order_type: 工单类型
            creator: 创建人
            description: 描述
            priority: 优先级
            device_id: 关联设备ID
            device_name: 关联设备名称
            device_ip: 关联设备IP
            alert_id: 关联告警ID
            business_id: 业务系统ID
            business_name: 业务系统名称
            impact: 影响范围
            urgency: 紧急程度
            expected_start: 期望开始时间
            expected_end: 期望结束时间
            tags: 标签列表
            attachments: 附件列表
            remark: 备注
            
        Returns:
            创建的工单对象
        """
        order_no = self.generate_order_no(order_type)
        
        # 设置SLA时间
        sla_config = self.SLA_CONFIG.get(priority, self.SLA_CONFIG[WorkOrderPriority.P3])
        
        workorder = WorkOrder(
            order_no=order_no,
            order_type=order_type,
            priority=priority,
            title=title,
            description=description,
            device_id=device_id,
            device_name=device_name,
            device_ip=device_ip,
            alert_id=alert_id,
            business_id=business_id,
            business_name=business_name,
            status=WorkOrderStatus.PENDING,
            impact=impact,
            urgency=urgency,
            expected_start=expected_start,
            expected_end=expected_end,
            creator=creator,
            sla_response_time=sla_config['response'],
            sla_resolve_time=sla_config['resolve'],
            tags=','.join(tags) if tags else None,
            attachments=json.dumps(attachments) if attachments else None,
            remark=remark
        )
        
        try:
            self.db.add(workorder)
            self.db.flush()
            
            # 记录创建流程
            self._record_flow(
                workorder.id,
                action='create',
                operator=creator,
                from_status=None,
                to_status=WorkOrderStatus.PENDING,
                comment='工单创建'
            )
            
            self.db.commit()
            return workorder
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_id(self, workorder_id: int) -> Optional[WorkOrder]:
        """
        根据ID获取工单
        
        Args:
            workorder_id: 工单ID
            
        Returns:
            工单对象或None
        """
        return self.db.query(WorkOrder).filter(
            WorkOrder.id == workorder_id,
            WorkOrder.is_deleted == False
        ).first()
    
    def get_by_order_no(self, order_no: str) -> Optional[WorkOrder]:
        """
        根据工单编号获取工单
        
        Args:
            order_no: 工单编号
            
        Returns:
            工单对象或None
        """
        return self.db.query(WorkOrder).filter(
            WorkOrder.order_no == order_no,
            WorkOrder.is_deleted == False
        ).first()
    
    def list(
        self,
        status: Optional[WorkOrderStatus] = None,
        order_type: Optional[WorkOrderType] = None,
        priority: Optional[WorkOrderPriority] = None,
        creator: Optional[str] = None,
        assignee: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[WorkOrder], int]:
        """
        条件查询工单列表
        
        Args:
            status: 工单状态
            order_type: 工单类型
            priority: 优先级
            creator: 创建人
            assignee: 处理人
            start_time: 创建时间起始
            end_time: 创建时间结束
            tags: 标签列表
            page: 页码
            page_size: 每页数量
            
        Returns:
            (工单列表, 总数)
        """
        query = self.db.query(WorkOrder).filter(WorkOrder.is_deleted == False)
        
        if status:
            query = query.filter(WorkOrder.status == status)
        if order_type:
            query = query.filter(WorkOrder.order_type == order_type)
        if priority:
            query = query.filter(WorkOrder.priority == priority)
        if creator:
            query = query.filter(WorkOrder.creator == creator)
        if assignee:
            query = query.filter(WorkOrder.assignee == assignee)
        if start_time:
            query = query.filter(WorkOrder.created_at >= start_time)
        if end_time:
            query = query.filter(WorkOrder.created_at <= end_time)
        if tags:
            for tag in tags:
                query = query.filter(WorkOrder.tags.contains(tag))
        
        total = query.count()
        
        workorders = query.order_by(WorkOrder.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return workorders, total
    
    def update(
        self,
        workorder_id: int,
        operator: str,
        **kwargs
    ) -> Optional[WorkOrder]:
        """
        更新工单
        
        Args:
            workorder_id: 工单ID
            operator: 操作人
            **kwargs: 更新字段
            
        Returns:
            更新后的工单对象或None
        """
        workorder = self.get_by_id(workorder_id)
        if not workorder:
            return None
        
        allowed_fields = [
            'title', 'description', 'priority', 'device_id', 'device_name',
            'device_ip', 'business_id', 'business_name', 'impact', 'urgency',
            'expected_start', 'expected_end', 'assignee', 'assignee_email',
            'change_type', 'change_impact', 'rollback_plan', 'test_plan',
            'resolution', 'root_cause', 'improvement', 'satisfaction',
            'feedback', 'tags', 'remark'
        ]
        
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_data:
            return workorder
        
        for key, value in update_data.items():
            setattr(workorder, key, value)
        
        workorder.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return workorder
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, workorder_id: int, operator: str) -> bool:
        """
        删除工单(软删除)
        
        Args:
            workorder_id: 工单ID
            operator: 操作人
            
        Returns:
            是否删除成功
        """
        workorder = self.get_by_id(workorder_id)
        if not workorder:
            return False
        
        workorder.is_deleted = True
        workorder.updated_at = datetime.now()
        
        self._record_flow(
            workorder.id,
            action='delete',
            operator=operator,
            from_status=workorder.status,
            to_status=workorder.status,
            comment='工单删除'
        )
        
        try:
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def change_status(
        self,
        workorder_id: int,
        new_status: WorkOrderStatus,
        operator: str,
        comment: Optional[str] = None
    ) -> Tuple[bool, str, Optional[WorkOrder]]:
        """
        变更工单状态
        
        Args:
            workorder_id: 工单ID
            new_status: 新状态
            operator: 操作人
            comment: 意见
            
        Returns:
            (是否成功, 消息, 工单对象)
        """
        workorder = self.get_by_id(workorder_id)
        if not workorder:
            return False, '工单不存在', None
        
        current_status = workorder.status
        
        # 检查状态流转是否合法
        allowed_transitions = self.STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed_transitions:
            return False, f'状态不能从{current_status.value}流转到{new_status.value}', None
        
        # 特殊状态处理
        now = datetime.now()
        if new_status == WorkOrderStatus.PROCESSING:
            if not workorder.actual_start:
                workorder.actual_start = now
            # SLA计时开始
            if not workorder.sla_response_at:
                workorder.sla_response_at = now
        
        elif new_status == WorkOrderStatus.RESOLVED:
            workorder.actual_end = now
            workorder.sla_resolved_at = now
        
        elif new_status == WorkOrderStatus.CLOSED:
            workorder.closed_at = now
            if workorder.sla_resolved_at is None:
                workorder.sla_resolved_at = now
        
        workorder.status = new_status
        workorder.updated_at = now
        
        # 记录流程
        action_map = {
            WorkOrderStatus.PROCESSING: 'process',
            WorkOrderStatus.PENDING_APPROVAL: 'submit_approval',
            WorkOrderStatus.APPROVED: 'approve',
            WorkOrderStatus.REJECTED: 'reject',
            WorkOrderStatus.RESOLVED: 'resolve',
            WorkOrderStatus.CLOSED: 'close',
            WorkOrderStatus.CANCELLED: 'cancel'
        }
        action = action_map.get(new_status, 'update_status')
        
        self._record_flow(
            workorder.id,
            action=action,
            operator=operator,
            from_status=current_status,
            to_status=new_status,
            comment=comment
        )
        
        try:
            self.db.commit()
            return True, f'状态已变更为{new_status.value}', workorder
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def assign(
        self,
        workorder_id: int,
        assignee: str,
        assignee_email: Optional[str] = None,
        operator: str = 'system',
        comment: Optional[str] = None
    ) -> Tuple[bool, str, Optional[WorkOrder]]:
        """
        分配工单
        
        Args:
            workorder_id: 工单ID
            assignee: 处理人
            assignee_email: 处理人邮箱
            operator: 操作人
            comment: 意见
            
        Returns:
            (是否成功, 消息, 工单对象)
        """
        workorder = self.get_by_id(workorder_id)
        if not workorder:
            return False, '工单不存在', None
        
        if workorder.status == WorkOrderStatus.CLOSED:
            return False, '工单已关闭,不能分配', None
        
        workorder.assignee = assignee
        workorder.assignee_email = assignee_email
        workorder.updated_at = datetime.now()
        
        self._record_flow(
            workorder.id,
            action='assign',
            operator=operator,
            from_status=workorder.status,
            to_status=workorder.status,
            comment=comment or f'分配给{assignee}'
        )
        
        try:
            self.db.commit()
            return True, f'工单已分配给{assignee}', workorder
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def add_progress(
        self,
        workorder_id: int,
        progress_data: Dict[str, Any],
        operator: str
    ) -> Tuple[bool, str, Optional[WorkOrder]]:
        """
        添加处理进度
        
        Args:
            workorder_id: 工单ID
            progress_data: 进度数据
            operator: 操作人
            
        Returns:
            (是否成功, 消息, 工单对象)
        """
        workorder = self.get_by_id(workorder_id)
        if not workorder:
            return False, '工单不存在', None
        
        # 解析现有进度
        handling_progress = []
        if workorder.handling_progress:
            try:
                handling_progress = json.loads(workorder.handling_progress)
            except json.JSONDecodeError:
                handling_progress = []
        
        # 添加新进度
        progress_record = {
            'timestamp': datetime.now().isoformat(),
            'operator': operator,
            'data': progress_data
        }
        handling_progress.append(progress_record)
        
        workorder.handling_progress = json.dumps(handling_progress)
        workorder.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '处理进度已添加', workorder
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_sla_status(self, workorder_id: int) -> Dict[str, Any]:
        """
        获取SLA状态
        
        Args:
            workorder_id: 工单ID
            
        Returns:
            SLA状态信息
        """
        workorder = self.get_by_id(workorder_id)
        if not workorder:
            return {}
        
        now = datetime.now()
        result = {
            'sla_response_time': workorder.sla_response_time,
            'sla_resolve_time': workorder.sla_resolve_time,
            'sla_response_at': workorder.sla_response_at,
            'sla_resolved_at': workorder.sla_resolved_at,
            'response_breached': False,
            'resolve_breached': False,
            'response_remaining': None,
            'resolve_remaining': None
        }
        
        # 计算响应超时
        if workorder.sla_response_at:
            response_deadline = workorder.sla_response_at + timedelta(
                minutes=workorder.sla_response_time or 0
            )
            if now > response_deadline:
                result['response_breached'] = True
            else:
                result['response_remaining'] = int(
                    (response_deadline - now).total_seconds() / 60
                )
        elif workorder.created_at:
            response_deadline = workorder.created_at + timedelta(
                minutes=workorder.sla_response_time or 0
            )
            if workorder.status != WorkOrderStatus.PENDING:
                result['response_remaining'] = 0
                result['response_breached'] = True
            elif now > response_deadline:
                result['response_breached'] = True
            else:
                result['response_remaining'] = int(
                    (response_deadline - now).total_seconds() / 60
                )
        
        # 计算解决超时
        if workorder.sla_resolved_at:
            result['resolve_remaining'] = 0
        elif workorder.created_at:
            resolve_deadline = workorder.created_at + timedelta(
                minutes=workorder.sla_resolve_time or 0
            )
            if now > resolve_deadline:
                result['resolve_breached'] = True
            else:
                result['resolve_remaining'] = int(
                    (resolve_deadline - now).total_seconds() / 60
                )
        
        return result
    
    def get_flow_history(self, workorder_id: int) -> List[WorkOrderFlow]:
        """
        获取工单流程历史
        
        Args:
            workorder_id: 工单ID
            
        Returns:
            流程历史列表
        """
        return self.db.query(WorkOrderFlow).filter(
            WorkOrderFlow.work_order_id == workorder_id
        ).order_by(WorkOrderFlow.created_at.desc()).all()
    
    def _record_flow(
        self,
        workorder_id: int,
        action: str,
        operator: str,
        from_status: Optional[WorkOrderStatus],
        to_status: WorkOrderStatus,
        comment: Optional[str] = None
    ) -> WorkOrderFlow:
        """
        记录流程操作
        
        Args:
            workorder_id: 工单ID
            action: 操作类型
            operator: 操作人
            from_status: 原状态
            to_status: 新状态
            comment: 意见
            
        Returns:
            流程记录对象
        """
        flow = WorkOrderFlow(
            work_order_id=workorder_id,
            step_name=f'{action}_{to_status.value}',
            action=action,
            operator=operator,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value if to_status else None,
            comment=comment
        )
        
        self.db.add(flow)
        return flow
    
    def get_pending_count(self, assignee: Optional[str] = None) -> Dict[str, int]:
        """
        获取待处理工单统计
        
        Args:
            assignee: 处理人(可选)
            
        Returns:
            各状态工单数量统计
        """
        query = self.db.query(WorkOrder).filter(WorkOrder.is_deleted == False)
        
        if assignee:
            query = query.filter(WorkOrder.assignee == assignee)
        
        result = {}
        for status in WorkOrderStatus:
            count = query.filter(WorkOrder.status == status).count()
            if count > 0:
                result[status.value] = count
        
        return result
    
    def save_draft(
        self,
        workorder_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[WorkOrderPriority] = None,
        draft_data: Optional[Dict[str, Any]] = None,
        draft_saved_at: Optional[datetime] = None
    ) -> bool:
        """
        保存工单草稿(WKO-008)
        
        - 不更新updated_at
        - 不记录操作历史
        - 只更新: title, description, priority, draft_data, draft_saved_at
        
        Args:
            workorder_id: 工单ID
            title: 标题
            description: 描述
            priority: 优先级
            draft_data: 草稿数据快照
            draft_saved_at: 草稿保存时间
            
        Returns:
            是否保存成功
        """
        workorder = self.get_by_id(workorder_id)
        if not workorder:
            return False
        
        # 只更新草稿相关字段
        if title is not None:
            workorder.title = title
        if description is not None:
            workorder.description = description
        if priority is not None:
            workorder.priority = priority
        if draft_data is not None:
            workorder.draft_data = draft_data
        if draft_saved_at is not None:
            workorder.draft_saved_at = draft_saved_at
        
        # 注意：不更新updated_at，不记录操作历史
        
        try:
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def batch_assign(
        self,
        workorder_ids: List[int],
        assignee: str,
        assignee_email: Optional[str] = None,
        operator: str = 'system'
    ) -> Dict[str, Any]:
        """
        批量分配工单
        
        Args:
            workorder_ids: 工单ID列表
            assignee: 处理人
            assignee_email: 处理人邮箱
            operator: 操作人
            
        Returns:
            批量操作结果
        """
        success_count = 0
        failed_items = []
        
        for wid in workorder_ids:
            success, msg, _ = self.assign(wid, assignee, assignee_email, operator)
            if success:
                success_count += 1
            else:
                failed_items.append({'id': wid, 'reason': msg})
        
        return {
            'total': len(workorder_ids),
            'success': success_count,
            'failed': len(failed_items),
            'failed_items': failed_items
        }
