"""
BM-06 通知渠道模块
支持邮件、钉钉、飞书、企业微信、webhook等通知方式
"""

from .notification_service import (
    NotificationType,
    NotificationConfig,
    NotificationMessage,
    NotificationManager,
    NotificationChannel,
    get_notification_manager,
    init_notification_manager,
    send_dingtalk_message,
    send_feishu_message,
    send_wechat_work_message,
)

__all__ = [
    "NotificationType",
    "NotificationConfig",
    "NotificationMessage",
    "NotificationManager",
    "NotificationChannel",
    "get_notification_manager",
    "init_notification_manager",
    "send_dingtalk_message",
    "send_feishu_message",
    "send_wechat_work_message",
]

__version__ = "1.0.0"