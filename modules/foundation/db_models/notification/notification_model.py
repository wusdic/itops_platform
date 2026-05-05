"""
通知渠道数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from modules.foundation.db_models.base import Base


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