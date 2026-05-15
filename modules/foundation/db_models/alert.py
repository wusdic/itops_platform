"""
告警模型定义
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base


class AlertLevel(str, Enum):
    """告警级别枚举"""
    CRITICAL = 'critical'   # 紧急 - P1
    HIGH = 'high'          # 严重 - P2
    MEDIUM = 'medium'      # 中等 - P3
    LOW = 'low'            # 低 - P4
    INFO = 'info'          # 信息


class AlertStatus(str, Enum):
    """告警状态枚举"""
    ACTIVE = 'active'          # 活跃/未处理
    ACKNOWLEDGED = 'acknowledged'  # 已确认
    RESOLVED = 'resolved'      # 已解决
    CLOSED = 'closed'          # 已关闭
    SUPPRESSED = 'suppressed'  # 已抑制


class AlertCategory(str, Enum):
    """告警分类枚举"""
    PERFORMANCE = 'performance'     # 性能告警
    FAULT = 'fault'                 # 故障告警
    SECURITY = 'security'           # 安全告警
    CAPACITY = 'capacity'           # 容量告警
    AVAILABILITY = 'availability'   # 可用性告警
    CONFIG = 'config'               # 配置变更
    OTHER = 'other'                 # 其他


class Alert(Base):
    """
    告警模型
    
    统一存储所有类型的告警信息
    """
    __tablename__ = 'alerts'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 告警标识
    alert_key = Column(String(256), index=True, comment='告警唯一标识')
    
    # 关联设备
    device_id = Column(Integer, ForeignKey('devices.id'), index=True, comment='设备ID')
    device_name = Column(String(128), comment='设备名称')
    device_ip = Column(String(64), comment='设备IP')
    
    # 告警基本信息
    level = Column(SQLEnum(AlertLevel), nullable=False, index=True, comment='告警级别')
    category = Column(SQLEnum(AlertCategory), comment='告警分类')
    title = Column(String(256), nullable=False, comment='告警标题')
    message = Column(Text, comment='告警详情')
    
    # 告警值
    metric_name = Column(String(128), comment='指标名称')
    metric_value = Column(String(128), comment='指标值')
    current_value = Column(String(128), comment='当前值')
    threshold = Column(String(128), comment='阈值')
    unit = Column(String(32), comment='单位')
    
    # 状态
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE, index=True, comment='状态')
    
    # 时间
    first_occurred_at = Column(DateTime, comment='首次发生时间')
    occurred_at = Column(DateTime, default=datetime.now, comment='发生时间')
    acknowledged_at = Column(DateTime, comment='确认时间')
    resolved_at = Column(DateTime, comment='解决时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 处理信息
    acknowledged_by = Column(String(64), comment='确认人')
    resolved_by = Column(String(64), comment='解决人')
    assignee = Column(String(64), comment='处理人')
    
    # 关联信息
    workorder_id = Column(Integer, ForeignKey('work_orders.id'), comment='关联工单ID')
    incident_id = Column(String(64), comment='关联事件ID')
    
    # 计数
    count = Column(Integer, default=1, comment='发生次数')
    duration = Column(Integer, default=0, comment='持续时间(秒)')
    
    # 额外信息
    tags = Column(String(256), comment='标签')
    remark = Column(Text, comment='备注')
    resolution_note = Column(Text, comment='解决备注')

    # 原始数据
    raw_data = Column(Text, comment='原始告警数据')
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    source = Column(String(64), comment='告警来源')
    
    # 索引
    __table_args__ = (
        Index('idx_alert_status_level', 'status', 'level'),
        Index('idx_alert_device_time', 'device_id', 'occurred_at'),
        Index('idx_alert_first_occurred', 'first_occurred_at'),
    )
    
    def __repr__(self):
        return f"<Alert(id={self.id}, level='{self.level.value}', title='{self.title}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'alert_key': self.alert_key,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_ip': self.device_ip,
            'level': self.level.value if self.level else None,
            'category': self.category.value if self.category else None,
            'title': self.title,
            'message': self.message,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'threshold': self.threshold,
            'status': self.status.value if self.status else None,
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at else None,
            'duration': self.duration,
            'count': self.count,
            'assignee': self.assignee,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AlertRule(Base):
    """
    告警规则模型
    
    定义告警触发规则
    """
    __tablename__ = 'alert_rules'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 规则基本信息
    name = Column(String(128), nullable=False, unique=True, comment='规则名称')
    description = Column(String(512), comment='规则描述')
    category = Column(SQLEnum(AlertCategory), comment='分类')
    
    # 启用状态
    enabled = Column(Boolean, default=True, comment='是否启用')
    
    # 匹配条件
    expression = Column(Text, nullable=False, comment='匹配表达式')
    
    # 告警级别
    level = Column(SQLEnum(AlertLevel), nullable=False, comment='告警级别')
    
    # 阈值配置
    threshold_value = Column(String(128), comment='阈值')
    comparison = Column(String(16), default='>', comment='比较方式: >, <, =, >=, <=, !=')
    duration_seconds = Column(Integer, default=0, comment='持续时间(秒)')
    
    # 采集源
    metric_source = Column(String(64), comment='指标来源')
    metric_name = Column(String(128), comment='指标名称')
    
    # 设备过滤
    device_type_filter = Column(String(256), comment='设备类型过滤')
    device_id_filter = Column(String(256), comment='设备ID过滤')
    tags_filter = Column(String(256), comment='标签过滤')
    
    # 处理配置
    auto_acknowledge = Column(Boolean, default=False, comment='自动确认')
    auto_resolve = Column(Boolean, default=False, comment='自动解决')
    create_workorder = Column(Boolean, default=False, comment='自动创建工单')
    
    # 通知配置
    notify_enabled = Column(Boolean, default=True, comment='是否通知')
    notify_channels = Column(String(256), comment='通知渠道: email,dingtalk,feishu,sms')
    notify_receivers = Column(String(256), comment='通知接收人')
    notify_interval = Column(Integer, default=300, comment='重复通知间隔(秒)')
    
    # 抑制配置
    suppress_enabled = Column(Boolean, default=False, comment='是否启用抑制')
    suppress_duration = Column(Integer, default=300, comment='抑制时间(秒)')
    suppress_key = Column(String(256), comment='抑制键')
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String(64))
    updated_by = Column(String(64))
    
    def __repr__(self):
        return f"<AlertRule(id={self.id}, name='{self.name}', enabled={self.enabled})>"


class AlertNotification(Base):
    """告警通知记录模型"""
    __tablename__ = 'alert_notifications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey('alerts.id'), index=True, comment='告警ID')
    
    channel = Column(String(32), comment='通知渠道: email,dingtalk,feishu')
    receiver = Column(String(128), comment='接收人')
    status = Column(String(32), default='pending', comment='发送状态')
    error_message = Column(String(512), comment='错误信息')
    
    sent_at = Column(DateTime, comment='发送时间')
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<AlertNotification(id={self.id}, channel='{self.channel}', status='{self.status}')>"


class AlertAuditLog(Base):
    """
    告警审计日志模型
    记录告警的所有操作历史，用于审计追溯
    """
    __tablename__ = 'alert_audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联告警
    alert_id = Column(Integer, ForeignKey('alerts.id'), index=True, nullable=False, comment='告警ID')
    alert_key = Column(String(256), comment='告警标识')

    # 操作信息
    action = Column(String(64), nullable=False, comment='操作类型: create, acknowledge, resolve, close, update, delete')
    operator = Column(String(64), comment='操作人')
    operator_ip = Column(String(64), comment='操作人IP')

    # 操作详情
    field_name = Column(String(64), comment='被修改的字段名')
    old_value = Column(Text, comment='旧值')
    new_value = Column(Text, comment='新值')
    reason = Column(Text, comment='操作原因/备注')

    # 关联工单
    workorder_id = Column(Integer, ForeignKey('work_orders.id'), comment='关联工单ID')

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='操作时间')

    # 元数据
    user_agent = Column(String(256), comment='用户代理')
    request_id = Column(String(64), comment='请求ID')

    # 索引
    __table_args__ = (
        Index('idx_audit_alert_time', 'alert_id', 'created_at'),
        Index('idx_audit_operator_time', 'operator', 'created_at'),
        Index('idx_audit_action', 'action', 'created_at'),
    )

    def __repr__(self):
        return f"<AlertAuditLog(id={self.id}, alert_id={self.alert_id}, action='{self.action}')>"