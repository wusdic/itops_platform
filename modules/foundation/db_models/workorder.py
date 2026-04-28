"""
工单模型定义
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base


class WorkOrderType(str, Enum):
    """工单类型枚举"""
    FAULT = 'fault'           # 故障工单
    CHANGE = 'change'         # 变更工单
    INSPECTION = 'inspection' # 巡检工单
    SECURITY = 'security'     # 安全工单
    DEMAND = 'demand'         # 需求工单
    QUESTION = 'question'     # 咨询工单
    OTHER = 'other'           # 其他


class WorkOrderStatus(str, Enum):
    """工单状态枚举"""
    PENDING = 'pending'       # 待处理
    PROCESSING = 'processing' # 处理中
    PENDING_APPROVAL = 'pending_approval'  # 待审批
    APPROVED = 'approved'     # 已批准
    REJECTED = 'rejected'     # 已拒绝
    RESOLVED = 'resolved'     # 已解决
    CLOSED = 'closed'         # 已关闭
    CANCELLED = 'cancelled'   # 已取消


class WorkOrderPriority(str, Enum):
    """工单优先级枚举"""
    P1 = 'P1'    # 紧急
    P2 = 'P2'    # 高
    P3 = 'P3'    # 中
    P4 = 'P4'    # 低


class WorkOrder(Base):
    """
    工单模型
    
    统一管理所有类型的运维工单
    """
    __tablename__ = 'work_orders'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 工单标识
    order_no = Column(String(64), unique=True, nullable=False, index=True, comment='工单编号')
    
    # 工单类型
    order_type = Column(SQLEnum(WorkOrderType), nullable=False, index=True, comment='工单类型')
    priority = Column(SQLEnum(WorkOrderPriority), default=WorkOrderPriority.P3, comment='优先级')
    
    # 标题和描述
    title = Column(String(256), nullable=False, comment='标题')
    description = Column(Text, comment='描述')
    
    # 关联信息
    device_id = Column(Integer, ForeignKey('devices.id'), comment='关联设备ID')
    device_name = Column(String(128), comment='关联设备名称')
    device_ip = Column(String(64), comment='关联设备IP')
    
    alert_id = Column(Integer, ForeignKey('alerts.id'), comment='关联告警ID')
    
    # 业务系统
    business_id = Column(Integer, comment='业务系统ID')
    business_name = Column(String(128), comment='业务系统名称')
    
    # 状态
    status = Column(SQLEnum(WorkOrderStatus), default=WorkOrderStatus.PENDING, index=True, comment='状态')
    
    # 影响范围
    impact = Column(String(32), comment='影响范围: whole_company, department, group, individual')
    urgency = Column(String(32), comment='紧急程度')
    
    # 时间管理
    expected_start = Column(DateTime, comment='期望开始时间')
    expected_end = Column(DateTime, comment='期望结束时间')
    actual_start = Column(DateTime, comment='实际开始时间')
    actual_end = Column(DateTime, comment='实际结束时间')
    
    # SLA
    sla_response_time = Column(Integer, comment='SLA响应时间(分钟)')
    sla_resolve_time = Column(Integer, comment='SLA解决时间(分钟)')
    sla_response_at = Column(DateTime, comment='响应时间')
    sla_resolved_at = Column(DateTime, comment='解决时间')
    
    # 人员分配
    creator = Column(String(64), nullable=False, comment='创建人')
    creator_email = Column(String(128), comment='创建人邮箱')
    assignee = Column(String(64), comment='处理人')
    assignee_email = Column(String(128), comment='处理人邮箱')
    approver = Column(String(64), comment='审批人')
    
    # 变更相关
    change_type = Column(String(64), comment='变更类型')
    change_impact = Column(Text, comment='变更影响')
    rollback_plan = Column(Text, comment='回滚方案')
    test_plan = Column(Text, comment='测试计划')
    
    # 审批流程
    approval_status = Column(String(32), comment='审批状态')
    approval_history = Column(Text, comment='审批历史JSON')
    
    # 处理记录
    handling_progress = Column(Text, comment='处理进度JSON')
    resolution = Column(Text, comment='解决方案')
    root_cause = Column(Text, comment='根本原因')
    improvement = Column(Text, comment='改进措施')
    
    # 满意度
    satisfaction = Column(Integer, comment='满意度评分(1-5)')
    feedback = Column(Text, comment='反馈意见')
    
    # 附件
    attachments = Column(Text, comment='附件列表JSON')
    
    # 标签
    tags = Column(String(256), comment='标签')
    
    # 备注
    remark = Column(Text, comment='备注')
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    closed_at = Column(DateTime, comment='关闭时间')
    
    # 软删除
    is_deleted = Column(Boolean, default=False, comment='是否删除')
    
    # 索引
    __table_args__ = (
        Index('idx_order_status_priority', 'status', 'priority'),
        Index('idx_order_creator_time', 'creator', 'created_at'),
        Index('idx_order_assignee_status', 'assignee', 'status'),
    )
    
    def __repr__(self):
        return f"<WorkOrder(id={self.id}, order_no='{self.order_no}', type='{self.order_type.value}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'order_no': self.order_no,
            'order_type': self.order_type.value if self.order_type else None,
            'priority': self.priority.value if self.priority else None,
            'title': self.title,
            'description': self.description,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_ip': self.device_ip,
            'status': self.status.value if self.status else None,
            'impact': self.impact,
            'creator': self.creator,
            'assignee': self.assignee,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expected_end': self.expected_end.isoformat() if self.expected_end else None
        }


class WorkOrderFlow(Base):
    """工单流程模型"""
    __tablename__ = 'work_order_flows'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), index=True, comment='工单ID')
    
    step_name = Column(String(64), nullable=False, comment='步骤名称')
    step_order = Column(Integer, comment='步骤顺序')
    
    operator = Column(String(64), comment='操作人')
    operator_email = Column(String(128), comment='操作人邮箱')
    
    action = Column(String(32), comment='操作: create, assign, approve, reject, resolve, close, cancel')
    from_status = Column(String(32), comment='原状态')
    to_status = Column(String(32), comment='新状态')
    
    comment = Column(Text, comment='意见/备注')
    
    created_at = Column(DateTime, default=datetime.now, comment='操作时间')
    
    def __repr__(self):
        return f"<WorkOrderFlow(id={self.id}, action='{self.action}')>"