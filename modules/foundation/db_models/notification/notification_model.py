"""
通知渠道数据库模型
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Index
from sqlalchemy.sql import func
from modules.foundation.db_models.base import Base


class NotificationChannel(str, Enum):
    """通知渠道枚举 - 支持email/sms/webhook三种渠道"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationChannelModel(Base):
    """通知渠道模型"""
    __tablename__ = "notification_channels"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    channel_type = Column(String(20), nullable=False, index=True)  # email, dingtalk, feishu, wechat_work, webhook
    
    # 通用配置
    enabled = Column(Boolean, default=True)
    webhook_url = Column(Text)
    timeout = Column(Integer, default=30)
    
    # 邮件配置
    smtp_host = Column(String(200))
    smtp_port = Column(Integer, default=25)
    smtp_user = Column(String(200))
    smtp_password = Column(String(200))
    smtp_use_tls = Column(Boolean, default=False)
    from_email = Column(String(200))
    from_name = Column(String(100), default="IT运维平台")
    
    # 钉钉/飞书/企微配置
    webhook_token = Column(Text)  # 多个用逗号分隔
    webhook_secret = Column(String(200))
    
    # 告警级别过滤 (JSON数组)
    alert_levels = Column(Text)  # JSON: ["critical", "warning"]
    
    # 接收者配置
    recipients = Column(Text)  # JSON数组
    
    # 其他配置
    extra_config = Column(JSON)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class NotificationLog(Base):
    """通知发送日志"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 渠道信息
    channel_id = Column(Integer, index=True)
    channel_name = Column(String(100))
    channel_type = Column(String(20), index=True)
    
    # 消息内容
    title = Column(String(200))
    content = Column(Text)
    
    # 接收者
    recipients = Column(Text)  # JSON数组
    
    # 发送结果
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    status_code = Column(Integer)
    
    # 关联告警
    alert_id = Column(String(100), index=True)
    alert_level = Column(String(20))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration_ms = Column(Integer)  # 发送耗时


class NotificationTargetRule(Base):
    """
    通知目标规则模型
    定义告警通知的目标规则和接收者配置
    """
    __tablename__ = "notification_target_rules"

    id = Column(Integer, primary_key=True, index=True)

    # 规则基本信息
    name = Column(String(128), nullable=False, unique=True, comment='规则名称')
    description = Column(String(512), comment='规则描述')

    # 启用状态
    enabled = Column(Boolean, default=True, comment='是否启用')

    # 规则类型
    rule_type = Column(String(32), nullable=False, comment='规则类型: alert_level, device, category, custom')
    
    # 匹配条件 (JSON格式)
    # alert_level: {"levels": ["critical", "high"]}
    # device: {"device_ids": [1, 2], "device_types": ["server"]}
    # category: {"categories": ["performance", "fault"]}
    # custom: {"expression": "level == critical && device_name.startswith(prod-)"}
    match_conditions = Column(Text, comment='匹配条件(JSON)')

    # 通知配置
    notify_channels = Column(Text, nullable=False, comment='通知渠道(JSON): ["email", "dingtalk"]')
    notify_receivers = Column(Text, comment='通知接收人(JSON)')
    
    # 通知策略
    notify_interval = Column(Integer, default=300, comment='重复通知间隔(秒), 0表示不重复')
    max_notify_count = Column(Integer, default=3, comment='最大通知次数')
    
    # 升级策略 (JSON)
    escalation_config = Column(Text, comment='升级配置(JSON)')
    # 例如: {"critical": [{"after_seconds": 300, "channels": ["sms"]}]}

    # 抑制配置
    suppress_enabled = Column(Boolean, default=False, comment='是否启用抑制')
    suppress_until = Column(DateTime, comment='抑制截止时间')

    # 时段配置 (JSON)
    time_windows = Column(Text, comment='允许的通知时段(JSON)')
    # 例如: [{"days": [1,2,3,4,5], "start_hour": 9, "end_hour": 18}]

    # 元数据
    priority = Column(Integer, default=100, comment='优先级, 数字越小优先级越高')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(64))
    updated_by = Column(String(64))

    # 索引
    __table_args__ = (
        Index('idx_target_rule_enabled', 'enabled', 'priority'),
        Index('idx_target_rule_type', 'rule_type', 'enabled'),
    )

    def __repr__(self):
        return f"<NotificationTargetRule(id={self.id}, name='{self.name}', rule_type='{self.rule_type}')>"


class NotificationTarget(Base):
    """
    通知对象配置模型 (B3)
    支持按告警级别/设备分组/指标名称配置通知对象
    支持email/sms/webhook三种渠道
    """
    __tablename__ = "notification_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    name = Column(String(128), nullable=False, unique=True, comment='通知对象名称')
    description = Column(String(512), comment='通知对象描述')

    # 渠道配置
    channel = Column(String(20), nullable=False, comment='通知渠道: email, sms, webhook')

    # 渠道配置详情 (JSON格式)
    channel_config = Column(Text, comment='渠道配置详情(JSON)')

    # 启用状态
    enabled = Column(Boolean, default=True, comment='是否启用')

    # 匹配条件 (JSON格式)
    match_conditions = Column(Text, comment='匹配条件(JSON)')

    # 通知策略
    notify_interval = Column(Integer, default=300, comment='重复通知间隔(秒)')
    max_notify_count = Column(Integer, default=3, comment='最大通知次数')

    # 升级配置 (JSON)
    escalation_config = Column(Text, comment='升级配置(JSON)')

    # 抑制配置
    suppress_enabled = Column(Boolean, default=False, comment='是否启用抑制')
    suppress_until = Column(DateTime, comment='抑制截止时间')

    # 时段配置 (JSON)
    time_windows = Column(Text, comment='允许的通知时段(JSON)')

    # 优先级
    priority = Column(Integer, default=100, comment='优先级')

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(64))
    updated_by = Column(String(64))

    # 索引
    __table_args__ = (
        Index('idx_target_enabled', 'enabled', 'priority'),
        Index('idx_target_channel', 'channel', 'enabled'),
    )

    def __repr__(self):
        return f"<NotificationTarget(id={self.id}, name='{self.name}', channel='{self.channel}')>"

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'channel': self.channel,
            'channel_config': json.loads(self.channel_config) if self.channel_config else {},
            'enabled': self.enabled,
            'match_conditions': json.loads(self.match_conditions) if self.match_conditions else {},
            'notify_interval': self.notify_interval,
            'max_notify_count': self.max_notify_count,
            'escalation_config': json.loads(self.escalation_config) if self.escalation_config else None,
            'suppress_enabled': self.suppress_enabled,
            'suppress_until': self.suppress_until.isoformat() if self.suppress_until else None,
            'time_windows': json.loads(self.time_windows) if self.time_windows else None,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
        }