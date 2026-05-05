# -*- coding: utf-8 -*-
"""
ITOps Platform - Notification Channel
通知渠道
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum
from dataclasses import dataclass


class ChannelType(Enum):
    """通知渠道类型"""
    EMAIL = "email"
    SMS = "sms"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"
    FEISHU = "feishu"
    SLACK = "slack"
    WEBHOOK = "webhook"


@dataclass
class NotificationMessage:
    """通知消息"""
    title: str
    content: str
    level: str = "info"  # info, warning, error, critical
    recipients: list = None  # 根据渠道不同格式不同
    extra: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.recipients is None:
            self.recipients = []
        if self.extra is None:
            self.extra = {}


class NotificationChannel(ABC):
    """通知渠道基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """发送通知"""
        raise NotImplementedError
    
    @abstractmethod
    async def test(self, recipient: str) -> bool:
        """测试连接"""
        raise NotImplementedError
    
    @property
    def channel_type(self) -> ChannelType:
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    """邮件通知渠道"""
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.EMAIL
    
    async def send(self, message: NotificationMessage) -> bool:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            smtp_host = self.config.get("smtp_host", "localhost")
            smtp_port = self.config.get("smtp_port", 587)
            smtp_user = self.config.get("smtp_user", "")
            smtp_password = self.config.get("smtp_password", "")
            from_address = self.config.get("from_address", smtp_user)
            
            msg = MIMEMultipart()
            msg['From'] = from_address
            msg['To'] = ', '.join(message.recipients)
            msg['Subject'] = message.title
            
            # 内容
            body = MIMEText(message.content, 'html' if '<html>' in message.content else 'plain', 'utf-8')
            msg.attach(body)
            
            # 发送
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
    
    async def test(self, recipient: str) -> bool:
        test_msg = NotificationMessage(
            title="ITOps平台通知测试",
            content="这是一封测试邮件，如果您收到此邮件，说明通知配置正确。",
            recipients=[recipient]
        )
        return await self.send(test_msg)


class DingTalkChannel(NotificationChannel):
    """钉钉通知渠道"""
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.DINGTALK
    
    async def send(self, message: NotificationMessage) -> bool:
        import httpx
        
        try:
            webhook = self.config.get("webhook")
            if not webhook:
                print("钉钉webhook未配置")
                return False
            
            # 构建消息
            level_emojis = {
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🚨"
            }
            
            content = f"{level_emojis.get(message.level, 'ℹ️')} **{message.title}**\n\n{message.content}"
            
            payload = {
                "msgtype": "text",
                "text": {"content": content}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook, json=payload, timeout=10)
                return response.status_code == 200
        
        except Exception as e:
            print(f"钉钉通知发送失败: {e}")
            return False
    
    async def test(self, recipient: str) -> bool:
        test_msg = NotificationMessage(
            title="通知测试",
            content="ITOps平台通知配置测试",
            recipients=[]
        )
        return await self.send(test_msg)


class FeishuChannel(NotificationChannel):
    """飞书通知渠道"""
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.FEISHU
    
    async def send(self, message: NotificationMessage) -> bool:
        import httpx
        
        try:
            webhook = self.config.get("webhook")
            app_id = self.config.get("app_id")
            app_secret = self.config.get("app_secret")
            
            if not webhook and not (app_id and app_secret):
                print("飞书配置不完整")
                return False
            
            if app_id and app_secret:
                # 使用应用机器人
                token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
                token_response = await httpx.AsyncClient().post(
                    token_url,
                    json={"app_id": app_id, "app_secret": app_secret},
                    timeout=10
                )
                token_data = token_response.json()
                access_token = token_data.get("tenant_access_token")
                
                # 发送消息
                msg_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
                payload = {
                    "receive_id": message.recipients[0] if message.recipients else "",
                    "msg_type": "text",
                    "content": {"text": f"{message.title}\n{message.content}"}
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        msg_url,
                        json=payload,
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10
                    )
                    return response.status_code in [200, 201]
            else:
                # 使用webhook
                payload = {
                    "msg_type": "text",
                    "content": {"text": f"{message.title}\n{message.content}"}
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(webhook, json=payload, timeout=10)
                    return response.status_code == 200
        
        except Exception as e:
            print(f"飞书通知发送失败: {e}")
            return False
    
    async def test(self, recipient: str) -> bool:
        test_msg = NotificationMessage(
            title="通知测试",
            content="ITOps平台通知配置测试",
            recipients=[recipient]
        )
        return await self.send(test_msg)


class WebhookChannel(NotificationChannel):
    """通用WebHook通知渠道"""
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.WEBHOOK
    
    async def send(self, message: NotificationMessage) -> bool:
        import httpx
        
        try:
            webhook = self.config.get("webhook")
            if not webhook:
                return False
            
            headers = self.config.get("headers", {})
            headers.setdefault("Content-Type", "application/json")
            
            payload = {
                "title": message.title,
                "content": message.content,
                "level": message.level,
                "timestamp": self.config.get("timestamp", True),
            }
            
            if self.config.get("include_extra"):
                payload["extra"] = message.extra
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook, json=payload, headers=headers, timeout=10)
                return response.status_code in [200, 201, 204]
        
        except Exception as e:
            print(f"WebHook通知发送失败: {e}")
            return False
    
    async def test(self, recipient: str) -> bool:
        test_msg = NotificationMessage(
            title="通知测试",
            content="ITOps平台通知配置测试",
            recipients=[]
        )
        return await self.send(test_msg)


class NotificationService:
    """通知服务"""
    
    def __init__(self):
        self._channels: Dict[ChannelType, NotificationChannel] = {}
    
    def register_channel(self, channel_type: ChannelType, channel: NotificationChannel):
        """注册通知渠道"""
        self._channels[channel_type] = channel
    
    def get_channel(self, channel_type: ChannelType) -> Optional[NotificationChannel]:
        """获取通知渠道"""
        return self._channels.get(channel_type)
    
    async def send(self, channel_type: ChannelType, message: NotificationMessage) -> bool:
        """发送通知"""
        channel = self.get_channel(channel_type)
        if not channel:
            print(f"通知渠道 {channel_type.value} 未注册")
            return False
        
        return await channel.send(message)
    
    async def broadcast(self, message: NotificationMessage) -> Dict[ChannelType, bool]:
        """广播到所有渠道"""
        results = {}
        for channel_type, channel in self._channels.items():
            results[channel_type] = await channel.send(message)
        return results
