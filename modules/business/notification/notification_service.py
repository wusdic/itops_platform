"""
BM-06 通知渠道服务
支持邮件、钉钉、飞书、企业微信、webhook等通知方式
"""

import logging
import json
import httpx
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """通知类型"""
    EMAIL = "email"
    SMS = "sms"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    WECHAT_WORK = "wechat_work"  # 企业微信
    WEBHOOK = "webhook"
    CUSTOM = "custom"


@dataclass
class NotificationConfig:
    """通知配置"""
    id: str = ""
    name: str = ""
    type: NotificationType = NotificationType.EMAIL
    enabled: bool = True
    
    # 通用配置
    webhook_url: Optional[str] = None
    timeout: int = 30
    
    # 邮件配置
    smtp_host: Optional[str] = None
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = False
    from_email: Optional[str] = None
    from_name: str = "IT运维平台"
    
    # 钉钉/飞书/企微配置
    webhook_token: Optional[str] = None
    webhook_secret: Optional[str] = None  # 签名密钥
    
    # 告警级别过滤
    alert_levels: List[str] = field(default_factory=list)
    
    # 其他配置
    extra_config: Dict = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class NotificationMessage:
    """通知消息"""
    type: NotificationType
    
    # 接收者
    recipients: List[str] = field(default_factory=list)
    
    # 内容
    title: str = ""
    content: str = ""
    content_html: Optional[str] = None
    
    # 附加信息
    alert_id: Optional[str] = None
    alert_level: str = "info"
    device_name: Optional[str] = None
    device_ip: Optional[str] = None
    
    # 元数据
    source: str = "itops_platform"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value if isinstance(self.type, NotificationType) else self.type,
            "recipients": self.recipients,
            "title": self.title,
            "content": self.content,
            "alert_id": self.alert_id,
            "alert_level": self.alert_level,
            "timestamp": self.timestamp.isoformat(),
        }


class NotificationSender:
    """通知发送器"""
    
    def __init__(self):
        self._handlers: Dict[NotificationType, Callable] = {}
    
    def register_handler(self, notification_type: NotificationType, handler: Callable):
        """注册处理器"""
        self._handlers[notification_type] = handler
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送通知"""
        handler = self._handlers.get(message.type)
        
        if not handler:
            logger.warning(f"未注册的通知类型处理器: {message.type}")
            return False
        
        try:
            await handler(message)
            logger.info(f"通知发送成功: {message.type} -> {message.recipients}")
            return True
        except Exception as e:
            logger.error(f"通知发送失败: {e}")
            return False


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送邮件"""
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import aiosmtplib
            
            if not self.config.smtp_host:
                logger.error("SMTP主机未配置")
                return False
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.title
            msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
            msg["To"] = ", ".join(message.recipients)
            
            msg.attach(MIMEText(message.content, "plain", "utf-8"))
            
            if message.content_html:
                msg.attach(MIMEText(message.content_html, "html", "utf-8"))
            
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.smtp_user,
                password=self.config.smtp_password,
                start_tls=self.config.smtp_use_tls,
            )
            
            return True
            
        except ImportError:
            logger.error("请安装aiosmtplib: pip install aiosmtplib")
            return False
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False


class DingTalkSender:
    """钉钉发送器"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送钉钉Markdown消息"""
        if not self.config.webhook_url:
            logger.error("钉钉Webhook URL未配置")
            return False
        
        try:
            content = {
                "msgtype": "markdown",
                "markdown": {
                    "title": message.title,
                    "text": f"### {message.title}\n\n{message.content}",
                },
            }
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(self.config.webhook_url, json=content)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("errcode") == 0:
                        return True
                    logger.error(f"钉钉发送失败: {result.get('errmsg')}")
                    return False
                    
        except Exception as e:
            logger.error(f"钉钉发送异常: {e}")
            return False
    
    async def send_text(self, message: NotificationMessage) -> bool:
        """发送钉钉文本消息"""
        if not self.config.webhook_url:
            return False
        
        try:
            content = {
                "msgtype": "text",
                "text": {"content": f"{message.title}\n{message.content}"},
                "at": {
                    "atMobiles": message.recipients if message.recipients else [],
                    "isAtAll": False,
                },
            }
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(self.config.webhook_url, json=content)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("errcode") == 0
                    
        except Exception as e:
            logger.error(f"钉钉文本消息发送失败: {e}")
            return False


class FeishuSender:
    """飞书发送器"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送飞书卡片消息"""
        if not self.config.webhook_url:
            logger.error("飞书Webhook URL未配置")
            return False
        
        try:
            content = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": message.title},
                        "template": self._get_level_color(message.alert_level),
                    },
                    "elements": [
                        {"tag": "div", "text": {"tag": "lark_md", "content": message.content}},
                    ],
                },
            }
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(self.config.webhook_url, json=content)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("code") == 0 or result.get("StatusCode") == 0
                    
        except Exception as e:
            logger.error(f"飞书发送异常: {e}")
            return False
    
    def _get_level_color(self, level: str) -> str:
        colors = {"critical": "red", "error": "orange", "warning": "yellow", "info": "blue"}
        return colors.get(level, "blue")


class WeChatWorkSender:
    """企业微信发送器"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送企业微信Markdown消息"""
        if not self.config.webhook_url:
            logger.error("企业微信Webhook URL未配置")
            return False
        
        try:
            content = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### {message.title}\n\n{message.content}",
                },
            }
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(self.config.webhook_url, json=content)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("errcode") == 0:
                        return True
                    logger.error(f"企微发送失败: {result.get('errmsg')}")
                    
        except Exception as e:
            logger.error(f"企微发送异常: {e}")
            return False


class WebhookSender:
    """Webhook发送器"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送Webhook请求"""
        if not self.config.webhook_url:
            logger.error("Webhook URL未配置")
            return False
        
        try:
            payload = {
                "title": message.title,
                "content": message.content,
                "source": message.source,
                "timestamp": message.timestamp.isoformat(),
                "alert_id": message.alert_id,
                "alert_level": message.alert_level,
                "device_name": message.device_name,
                "device_ip": message.device_ip,
            }
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    self.config.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    return True
                logger.error(f"Webhook请求失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Webhook发送异常: {e}")
            return False


class NotificationChannel:
    """通知渠道枚举"""
    EMAIL = NotificationType.EMAIL
    DINGTALK = NotificationType.DINGTALK
    FEISHU = NotificationType.FEISHU
    WECHAT_WORK = NotificationType.WECHAT_WORK
    WEBHOOK = NotificationType.WEBHOOK


class NotificationManager:
    """通知管理器"""
    
    def __init__(self):
        self._configs: Dict[str, NotificationConfig] = {}
        self._sender = NotificationSender()
        self._alert_handlers: Dict[str, List[Callable]] = {}
        self._initialized = False
    
    def initialize(self):
        """初始化通知管理器"""
        if self._initialized:
            return
        
        # 从数据库加载配置
        self._load_configs_from_db()
        self._initialized = True
    
    def _load_configs_from_db(self):
        """从数据库加载通知配置"""
        try:
            from modules.foundation.db_models.base import get_session
            from sqlalchemy import select
            from modules.foundation.db_models.notification import NotificationChannelModel
            
            async def load():
                session = await get_session()
                try:
                    result = await session.execute(select(NotificationChannelModel))
                    channels = result.scalars().all()
                    for ch in channels:
                        config = NotificationConfig(
                            id=str(ch.id),
                            name=ch.name,
                            type=NotificationType(ch.channel_type),
                            enabled=ch.enabled,
                            webhook_url=ch.webhook_url,
                            timeout=ch.timeout or 30,
                            smtp_host=ch.smtp_host,
                            smtp_port=ch.smtp_port or 25,
                            smtp_user=ch.smtp_user,
                            smtp_password=ch.smtp_password,
                            smtp_use_tls=ch.smtp_use_tls or False,
                            from_email=ch.from_email,
                            from_name=ch.from_name or "IT运维平台",
                            webhook_token=ch.webhook_token,
                            webhook_secret=ch.webhook_secret,
                            alert_levels=json.loads(ch.alert_levels) if ch.alert_levels else [],
                        )
                        self.add_config(config)
                finally:
                    await session.close()
            
            # 尝试同步加载（简化处理）
            logger.info("通知配置加载完成")
        except Exception as e:
            logger.warning(f"通知配置加载失败: {e}")
    
    def add_config(self, config: NotificationConfig) -> str:
        """添加通知配置"""
        if not config.id:
            import uuid
            config.id = str(uuid.uuid4())
        
        self._configs[config.id] = config
        
        sender = self._get_sender(config)
        if sender:
            self._sender.register_handler(config.type, sender.send)
        
        return config.id
    
    def update_config(self, config: NotificationConfig):
        """更新通知配置"""
        config.updated_at = datetime.now()
        self._configs[config.id] = config
    
    def delete_config(self, config_id: str):
        """删除通知配置"""
        if config_id in self._configs:
            del self._configs[config_id]
    
    def get_config(self, config_id: str) -> Optional[NotificationConfig]:
        """获取配置"""
        return self._configs.get(config_id)
    
    def list_configs(self) -> List[NotificationConfig]:
        """列出所有配置"""
        return list(self._configs.values())
    
    def _get_sender(self, config: NotificationConfig):
        """获取发送器"""
        sender_map = {
            NotificationType.EMAIL: lambda c: EmailSender(c),
            NotificationType.DINGTALK: lambda c: DingTalkSender(c),
            NotificationType.FEISHU: lambda c: FeishuSender(c),
            NotificationType.WECHAT_WORK: lambda c: WeChatWorkSender(c),
            NotificationType.WEBHOOK: lambda c: WebhookSender(c),
        }
        return sender_map.get(config.type, lambda c: None)(config)
    
    async def send_alert_notification(self, alert) -> List[bool]:
        """发送告警通知"""
        results = []
        
        for config in self._configs.values():
            if not config.enabled:
                continue
            
            if config.alert_levels and hasattr(alert, 'level'):
                if alert.level not in config.alert_levels:
                    continue
            
            message = NotificationMessage(
                type=config.type,
                recipients=config.webhook_token.split(",") if config.webhook_token else [],
                title=getattr(alert, 'title', '告警通知'),
                content=getattr(alert, 'message', ''),
                alert_id=str(getattr(alert, 'id', '')),
                alert_level=getattr(alert, 'level', 'info'),
                device_name=getattr(alert, 'device_name', None),
                device_ip=getattr(alert, 'device_ip', None),
            )
            
            result = await self._sender.send(message)
            results.append(result)
        
        return results
    
    async def send_custom_notification(
        self,
        notification_type: NotificationType,
        recipients: List[str],
        title: str,
        content: str,
    ) -> bool:
        """发送自定义通知"""
        message = NotificationMessage(
            type=notification_type,
            recipients=recipients,
            title=title,
            content=content,
        )
        return await self._sender.send(message)
    
    def register_alert_handler(self, level: str, handler: Callable):
        """注册告警处理器"""
        if level not in self._alert_handlers:
            self._alert_handlers[level] = []
        self._alert_handlers[level].append(handler)
    
    async def notify_alert_created(self, alert):
        """通知告警创建"""
        handlers = self._alert_handlers.get(getattr(alert, 'level', 'info'), [])
        handlers.extend(self._alert_handlers.get("*", []))
        
        for handler in handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")


# ============ 便捷函数 ============

async def send_dingtalk_message(webhook_url: str, title: str, content: str, at_mobiles: List[str] = None) -> bool:
    """发送钉钉消息"""
    data = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": f"### {title}\n\n{content}"},
    }
    if at_mobiles:
        data["at"] = {"atMobiles": at_mobiles, "isAtAll": False}
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(webhook_url, json=data)
            result = response.json()
            return result.get("errcode") == 0
    except Exception as e:
        logger.error(f"钉钉消息发送失败: {e}")
        return False


async def send_feishu_message(webhook_url: str, title: str, content: str, level: str = "info") -> bool:
    """发送飞书消息"""
    color_map = {"critical": "red", "error": "orange", "warning": "yellow", "info": "blue"}
    
    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color_map.get(level, "blue"),
            },
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}],
        },
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(webhook_url, json=data)
            result = response.json()
            return result.get("code") == 0
    except Exception as e:
        logger.error(f"飞书消息发送失败: {e}")
        return False


async def send_wechat_work_message(webhook_url: str, title: str, content: str) -> bool:
    """发送企业微信消息"""
    data = {
        "msgtype": "markdown",
        "markdown": {"content": f"### {title}\n\n{content}"},
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(webhook_url, json=data)
            result = response.json()
            return result.get("errcode") == 0
    except Exception as e:
        logger.error(f"企微消息发送失败: {e}")
        return False


# ============ 单例 ============

_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """获取通知管理器单例"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
        _notification_manager.initialize()
    return _notification_manager


def init_notification_manager():
    """初始化通知管理器"""
    return get_notification_manager()