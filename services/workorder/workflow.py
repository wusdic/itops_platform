# -*- coding: utf-8 -*-
"""
ITOps Platform - WorkOrder Workflow
工单工作流
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


class WorkOrderStatus(Enum):
    """工单状态"""
    DRAFT = "draft"           # 草稿
    PENDING = "pending"       # 待处理
    PROCESSING = "processing" # 处理中
    PENDING_APPROVAL = "pending_approval"  # 待审批
    RESOLVED = "resolved"     # 已解决
    CLOSED = "closed"         # 已关闭
    REJECTED = "rejected"     # 已拒绝
    CANCELLED = "cancelled"   # 已取消


@dataclass
class WorkOrder:
    """工单"""
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    category: str = ""
    priority: str = "medium"  # low, medium, high, urgent
    status: WorkOrderStatus = WorkOrderStatus.PENDING
    creator_id: int = 0
    creator_name: str = ""
    handler_id: Optional[int] = None
    handler_name: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class WorkOrderWorkflow:
    """工单工作流引擎"""
    
    # 状态转换规则
    TRANSITIONS = {
        WorkOrderStatus.DRAFT: [WorkOrderStatus.PENDING, WorkOrderStatus.CANCELLED],
        WorkOrderStatus.PENDING: [WorkOrderStatus.PROCESSING, WorkOrderStatus.CANCELLED],
        WorkOrderStatus.PROCESSING: [WorkOrderStatus.RESOLVED, WorkOrderStatus.PENDING_APPROVAL, WorkOrderStatus.PENDING],
        WorkOrderStatus.PENDING_APPROVAL: [WorkOrderStatus.RESOLVED, WorkOrderStatus.REJECTED],
        WorkOrderStatus.RESOLVED: [WorkOrderStatus.CLOSED, WorkOrderStatus.PROCESSING],
        WorkOrderStatus.REJECTED: [WorkOrderStatus.PROCESSING],
        WorkOrderStatus.CLOSED: [],
        WorkOrderStatus.CANCELLED: [],
    }
    
    def __init__(self):
        self._handlers: Dict[str, callable] = {}
        self._workflows: Dict[str, List[Dict]] = {}
    
    def register_handler(self, status: WorkOrderStatus, handler: callable):
        """注册状态处理函数"""
        self._handlers[status.value] = handler
    
    def can_transition(self, current: WorkOrderStatus, target: WorkOrderStatus) -> bool:
        """检查是否可以转换"""
        return target in self.TRANSITIONS.get(current, [])
    
    def transition(self, workorder: WorkOrder, target: WorkOrderStatus) -> bool:
        """执行状态转换"""
        if not self.can_transition(workorder.status, target):
            return False
        
        # 调用处理函数
        handler = self._handlers.get(target.value)
        if handler:
            try:
                handler(workorder)
            except Exception as e:
                print(f"工作流处理函数执行失败: {e}")
                return False
        
        workorder.status = target
        workorder.updated_at = datetime.now()
        
        if target == WorkOrderStatus.RESOLVED:
            workorder.resolved_at = datetime.now()
        elif target == WorkOrderStatus.CLOSED:
            workorder.closed_at = datetime.now()
        
        return True
    
    def get_available_transitions(self, current: WorkOrderStatus) -> List[WorkOrderStatus]:
        """获取可用的状态转换"""
        return self.TRANSITIONS.get(current, [])
    
    def assign_handler(self, workorder: WorkOrder, handler_id: int, handler_name: str):
        """分配处理人"""
        workorder.handler_id = handler_id
        workorder.handler_name = handler_name
        workorder.updated_at = datetime.now()
        
        if workorder.status == WorkOrderStatus.PENDING:
            self.transition(workorder, WorkOrderStatus.PROCESSING)
    
    def resolve(self, workorder: WorkOrder, resolution: str = ""):
        """解决工单"""
        if resolution:
            workorder.custom_fields["resolution"] = resolution
        
        self.transition(workorder, WorkOrderStatus.RESOLVED)
    
    def close(self, workorder: WorkOrder):
        """关闭工单"""
        self.transition(workorder, WorkOrderStatus.CLOSED)
