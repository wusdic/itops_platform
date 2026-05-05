"""
通知服务模块
BM-01 监控告警
提供多渠道通知（站内/邮件/企微/钉钉Webhook）、通知模板、通知调度、通知回执等功能
"""

import logging
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict
import re
import hashlib

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """通知渠道枚举"""
    IN_APP = 'in_app'           # 站内通知
    EMAIL = 'email'              # 邮件
    WECHAT_WORK = 'wechat_work'  # 企业微信
    DINGTALK = 'dingtalk'       # 钉钉
    SMS = 'sms'                 # 短信
    WEBHOOK = 'webhook'         # 通用Webhook


class NotificationPriority(Enum):
    """通知优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class NotificationStatus(Enum):
    """通知状态枚举"""
    PENDING = 'pending'      # 待发送
    SENDING = 'sending'      # 发送中
    SENT = 'sent'            # 已发送
    FAILED = 'failed'        # 发送失败
    RATE_LIMITED = 'rate_limited'  # 被限流


@dataclass
class NotificationTemplate:
    """通知模板"""
    id: str
    name: str
    channel: NotificationChannel
    
    # 模板内容
    title_template: str = ''
    content_template: str = ''
    
    # 变量定义
    variables: List[str] = field(default_factory=list)
    
    # 格式化选项
    use_markdown: bool = False
    use_html: bool = False
    
    # 配置
    config: Dict[str, Any] = field(default_factory=dict)  # 渠道特定配置
    
    def render(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        渲染模板
        
        Args:
            variables: 变量值
            
        Returns:
            渲染后的标题和内容
        """
        title = self.title_template
        content = self.content_template
        
        for var in self.variables:
            value = variables.get(var, f'{{{var}}}')
            placeholder = f'{{{var}}}'
            title = title.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))
        
        return {
            'title': title,
            'content': content
        }


@dataclass
class Notification:
    """通知"""
    id: str
    channel: NotificationChannel
    priority: NotificationPriority
    
    # 接收者
    recipients: List[str]  # 用户ID列表或联系方式列表
    
    # 内容
    title: str
    content: str
    
    # 来源信息
    source_type: str = ''  # 'alert', 'ticket', 'system'
    source_id: str = ''
    
    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)
    
    # 状态
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    # 回执
    delivery_status: str = ''
    error_message: str = ''
    retry_count: int = 0
    
    # 调度信息
    scheduled_at: Optional[datetime] = None
    sent_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'channel': self.channel.value,
            'priority': self.priority.value,
            'recipients': self.recipients,
            'title': self.title,
            'content': self.content,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'context': self.context,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'delivery_status': self.delivery_status,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'sent_count': self.sent_count
        }


@dataclass
class RateLimitRule:
    """限流规则"""
    channel: NotificationChannel
    max_count: int          # 最大发送数
    window_seconds: int     # 时间窗口（秒）
    
    def __hash__(self):
        return hash((self.channel.value, self.max_count, self.window_seconds))


@dataclass
class RecipientProfile:
    """接收者配置"""
    user_id: str
    channels: List[NotificationChannel] = field(default_factory=list)
    
    # 联系方式
    email: str = ''
    phone: str = ''
    wechat_userid: str = ''
    dingtalk_webhook: str = ''
    
    # 免打扰配置
    quiet_hours_start: str = ''  # HH:MM格式
    quiet_hours_end: str = ''    # HH:MM格式
    timezone: str = 'Asia/Shanghai'
    
    # 订阅配置
    subscribed_alerts: List[str] = field(default_factory=list)  # 订阅的告警ID列表
    min_severity: NotificationPriority = NotificationPriority.NORMAL


class NotificationService:
    """
    通知服务
    负责多渠道通知的发送、模板管理、调度、限流
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化通知服务
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # 通知模板
        self._templates: Dict[str, NotificationTemplate] = {}
        self._setup_default_templates()
        
        # 通知记录
        self._notifications: Dict[str, Notification] = {}
        
        # 限流规则
        self._rate_limits: Dict[NotificationChannel, RateLimitRule] = {}
        self._rate_limit_counters: Dict[str, List[datetime]] = defaultdict(list)
        
        # 通知静默（避免轰炸）
        self._silence_cache: Dict[str, datetime] = {}  # key -> 静默结束时间
        self._default_silence_minutes = self.config.get('default_silence_minutes', 30)
        
        # 接收者配置
        self._recipient_profiles: Dict[str, RecipientProfile] = {}
        
        # HTTP客户端（用于Webhook）
        self._http_client = None
        
        # 回调函数
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # 并发限制
        self._max_concurrent = self.config.get('max_concurrent_notifications', 10)
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        
        logger.info('NotificationService initialized')
    
    def _setup_default_templates(self) -> None:
        """设置默认模板"""
        # 告警模板 - 站内
        self._templates['alert_inapp'] = NotificationTemplate(
            id='alert_inapp',
            name='告警通知-站内',
            channel=NotificationChannel.IN_APP,
            title_template='[{severity}] {rule_name}',
            content_template='设备: {device_id}\n指标: {metric_name}\n当前值: {value}\n阈值: {threshold}\n时间: {timestamp}',
            variables=['severity', 'rule_name', 'device_id', 'metric_name', 'value', 'threshold', 'timestamp']
        )
        
        # 告警模板 - 邮件
        self._templates['alert_email'] = NotificationTemplate(
            id='alert_email',
            name='告警通知-邮件',
            channel=NotificationChannel.EMAIL,
            title_template='[ITOps告警] {severity} - {rule_name}',
            content_template='''
告警详情:
- 告警名称: {rule_name}
- 设备: {device_id}
- 指标: {metric_name}
- 当前值: {value}
- 阈值: {threshold}
- 级别: {severity}
- 时间: {timestamp}

请及时处理。
''',
            variables=['rule_name', 'device_id', 'metric_name', 'value', 'threshold', 'severity', 'timestamp'],
            use_html=False
        )
        
        # 告警模板 - 企业微信
        self._templates['alert_wechat'] = NotificationTemplate(
            id='alert_wechat',
            name='告警通知-企业微信',
            channel=NotificationChannel.WECHAT_WORK,
            title_template='[告警] {rule_name}',
            content_template='**[{severity}] {rule_name}**\n> 设备: {device_id}\n> 指标: {metric_name}\n> 当前值: {value}\n> 阈值: {threshold}',
            variables=['severity', 'rule_name', 'device_id', 'metric_name', 'value', 'threshold'],
            use_markdown=True
        )
        
        # 告警模板 - 钉钉
        self._templates['alert_dingtalk'] = NotificationTemplate(
            id='alert_dingtalk',
            name='告警通知-钉钉',
            channel=NotificationChannel.DINGTALK,
            title_template='ITOps告警通知',
            content_template='''### {severity}告警: {rule_name}

**设备**: {device_id}
**指标**: {metric_name}
**当前值**: {value}
**阈值**: {threshold}
**时间**: {timestamp}''',
            variables=['severity', 'rule_name', 'device_id', 'metric_name', 'value', 'threshold', 'timestamp'],
            use_markdown=True
        )
    
    def add_template(self, template: NotificationTemplate) -> None:
        """添加通知模板"""
        self._templates[template.id] = template
        logger.info(f'Added notification template: {template.id}')
    
    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """获取通知模板"""
        return self._templates.get(template_id)
    
    def set_rate_limit(
        self,
        channel: NotificationChannel,
        max_count: int,
        window_seconds: int
    ) -> None:
        """设置限流规则"""
        self._rate_limits[channel] = RateLimitRule(
            channel=channel,
            max_count=max_count,
            window_seconds=window_seconds
        )
        logger.info(f'Set rate limit for {channel.value}: {max_count}/{window_seconds}s')
    
    def silence(
        self,
        key: str,
        minutes: Optional[int] = None
    ) -> None:
        """
        设置静默
        
        Args:
            key: 静默键（如 rule_id:device_id）
            minutes: 静默分钟数
        """
        duration = minutes or self._default_silence_minutes
        self._silence_cache[key] = datetime.now() + timedelta(minutes=duration)
        logger.info(f'Silenced notifications for key: {key} ({duration} minutes)')
    
    def unsilence(self, key: str) -> None:
        """取消静默"""
        if key in self._silence_cache:
            del self._silence_cache[key]
            logger.info(f'Unsilenced notifications for key: {key}')
    
    def is_silenced(self, key: str) -> bool:
        """检查是否被静默"""
        if key not in self._silence_cache:
            return False
        
        if datetime.now() >= self._silence_cache[key]:
            del self._silence_cache[key]
            return False
        
        return True
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """注册回调"""
        self._callbacks[event].append(callback)
    
    async def send(
        self,
        channel: NotificationChannel,
        recipients: List[str],
        title: str,
        content: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        context: Optional[Dict[str, Any]] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Optional[Notification]:
        """
        发送通知
        
        Args:
            channel: 通知渠道
            recipients: 接收者列表
            title: 标题
            content: 内容
            priority: 优先级
            context: 上下文数据
            scheduled_at: 计划发送时间
            
        Returns:
            通知对象或None
        """
        # 检查静默
        silence_key = context.get('silence_key', '') if context else ''
        if silence_key and self.is_silenced(silence_key):
            logger.debug(f'Notification silenced for key: {silence_key}')
            return None
        
        # 生成通知ID
        notification_id = f"NOTIF-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        notification = Notification(
            id=notification_id,
            channel=channel,
            priority=priority,
            recipients=recipients,
            title=title,
            content=content,
            source_type=context.get('source_type', '') if context else '',
            source_id=context.get('source_id', '') if context else '',
            context=context or {},
            scheduled_at=scheduled_at
        )
        
        # 存储通知
        self._notifications[notification_id] = notification
        
        # 如果是计划发送，加入调度队列
        if scheduled_at:
            logger.info(f'Notification {notification_id} scheduled for {scheduled_at}')
            return notification
        
        # 直接发送
        result = await self._send_notification(notification)
        return notification if result else None
    
    async def _send_notification(self, notification: Notification) -> bool:
        """
        发送单个通知
        
        Args:
            notification: 通知对象
            
        Returns:
            是否成功
        """
        async with self._semaphore:
            try:
                notification.status = NotificationStatus.SENDING
                
                # 检查限流
                if self._is_rate_limited(notification.channel):
                    notification.status = NotificationStatus.RATE_LIMITED
                    notification.error_message = 'Rate limited'
                    logger.warning(f'Notification {notification.id} rate limited')
                    return False
                
                # 更新计数器
                self._update_rate_counter(notification.channel)
                
                # 根据渠道发送
                success = False
                if notification.channel == NotificationChannel.IN_APP:
                    success = await self._send_in_app(notification)
                elif notification.channel == NotificationChannel.EMAIL:
                    success = await self._send_email(notification)
                elif notification.channel == NotificationChannel.WECHAT_WORK:
                    success = await self._send_wechat_work(notification)
                elif notification.channel == NotificationChannel.DINGTALK:
                    success = await self._send_dingtalk(notification)
                elif notification.channel == NotificationChannel.WEBHOOK:
                    success = await self._send_webhook(notification)
                elif notification.channel == NotificationChannel.SMS:
                    success = await self._send_sms(notification)
                else:
                    logger.error(f'Unknown notification channel: {notification.channel}')
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = f'Unknown channel: {notification.channel}'
                    return False
                
                if success:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.now()
                    notification.sent_count += 1
                    logger.info(f'Notification {notification.id} sent successfully')
                else:
                    notification.status = NotificationStatus.FAILED
                    notification.retry_count += 1
                    logger.error(f'Failed to send notification {notification.id}')
                
                return success
                
            except Exception as e:
                logger.error(f'Error sending notification: {e}')
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)
                notification.retry_count += 1
                return False
    
    async def _send_in_app(self, notification: Notification) -> bool:
        """发送站内通知"""
        # 实现站内通知逻辑
        # 这里只是模拟，实际需要结合用户系统
        logger.debug(f'Sending in-app notification: {notification.id}')
        await asyncio.sleep(0.1)  # 模拟异步
        return True
    
    async def _send_email(self, notification: Notification) -> bool:
        """发送邮件通知"""
        try:
            # 获取邮件配置
            email_config = self.config.get('email', {})
            
            # 这里需要集成实际的邮件发送库
            # 如 smtplib, aiosmtplib 等
            logger.debug(f'Sending email notification: {notification.id}')
            
            # 模拟发送
            await asyncio.sleep(0.2)
            return True
            
        except Exception as e:
            logger.error(f'Failed to send email: {e}')
            notification.error_message = str(e)
            return False
    
    async def _send_wechat_work(self, notification: Notification) -> bool:
        """发送企业微信通知"""
        try:
            webhook_url = self.config.get('wechat_work_webhook', '')
            if not webhook_url:
                logger.error('WeChat Work webhook URL not configured')
                return False
            
            # 企业微信消息格式
            message = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': notification.content
                }
            }
            
            # 使用HTTP客户端发送
            logger.debug(f'Sending WeChat Work notification: {notification.id}')
            await asyncio.sleep(0.2)
            return True
            
        except Exception as e:
            logger.error(f'Failed to send WeChat Work notification: {e}')
            notification.error_message = str(e)
            return False
    
    async def _send_dingtalk(self, notification: Notification) -> bool:
        """发送钉钉通知"""
        try:
            webhook_url = self.config.get('dingtalk_webhook', '')
            if not webhook_url:
                logger.error('DingTalk webhook URL not configured')
                return False
            
            # 钉钉消息格式
            message = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': notification.title,
                    'text': notification.content
                }
            }
            
            logger.debug(f'Sending DingTalk notification: {notification.id}')
            await asyncio.sleep(0.2)
            return True
            
        except Exception as e:
            logger.error(f'Failed to send DingTalk notification: {e}')
            notification.error_message = str(e)
            return False
    
    async def _send_webhook(self, notification: Notification) -> bool:
        """发送通用Webhook通知"""
        try:
            webhook_url = notification.context.get('webhook_url', '')
            if not webhook_url:
                logger.error('Webhook URL not specified')
                return False
            
            payload = {
                'title': notification.title,
                'content': notification.content,
                'timestamp': datetime.now().isoformat(),
                'source': notification.source_type,
                'source_id': notification.source_id,
                'context': notification.context
            }
            
            logger.debug(f'Sending webhook notification: {notification.id}')
            await asyncio.sleep(0.2)
            return True
            
        except Exception as e:
            logger.error(f'Failed to send webhook notification: {e}')
            notification.error_message = str(e)
            return False
    
    async def _send_sms(self, notification: Notification) -> bool:
        """发送短信通知"""
        try:
            # 需要集成短信服务商SDK
            logger.debug(f'Sending SMS notification: {notification.id}')
            await asyncio.sleep(0.5)
            return True
            
        except Exception as e:
            logger.error(f'Failed to send SMS: {e}')
            notification.error_message = str(e)
            return False
    
    def _is_rate_limited(self, channel: NotificationChannel) -> bool:
        """检查是否被限流"""
        rule = self._rate_limits.get(channel)
        if not rule:
            return False
        
        key = f"{channel.value}:count"
        timestamps = self._rate_limit_counters[key]
        
        # 清理过期记录
        now = datetime.now()
        cutoff = now - timedelta(seconds=rule.window_seconds)
        self._rate_limit_counters[key] = [t for t in timestamps if t > cutoff]
        
        return len(self._rate_limit_counters[key]) >= rule.max_count
    
    def _update_rate_counter(self, channel: NotificationChannel) -> None:
        """更新限流计数器"""
        key = f"{channel.value}:count"
        self._rate_limit_counters[key].append(datetime.now())
    
    async def send_alert_notification(
        self,
        alert_data: Dict[str, Any],
        channels: List[NotificationChannel],
        recipients: List[str]
    ) -> List[Optional[Notification]]:
        """
        发送告警通知
        
        Args:
            alert_data: 告警数据
            channels: 通知渠道列表
            recipients: 接收者列表
            
        Returns:
            发送的通知列表
        """
        notifications = []
        
        for channel in channels:
            template_id = f"alert_{channel.value}"
            template = self._templates.get(template_id)
            
            if not template:
                logger.warning(f'Template not found for channel: {channel.value}')
                continue
            
            # 渲染模板
            rendered = template.render(alert_data)
            
            # 发送通知
            notification = await self.send(
                channel=channel,
                recipients=recipients,
                title=rendered['title'],
                content=rendered['content'],
                priority=NotificationPriority.HIGH,
                context={
                    'source_type': 'alert',
                    'source_id': alert_data.get('alert_id', ''),
                    'alert_data': alert_data,
                    'silence_key': f"{alert_data.get('rule_id')}:{alert_data.get('device_id')}"
                }
            )
            notifications.append(notification)
        
        return notifications
    
    async def retry_failed(self, max_retries: int = 3) -> int:
        """
        重试失败的通知
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            重试成功的通知数量
        """
        retried = 0
        
        for notification in self._notifications.values():
            if notification.status != NotificationStatus.FAILED:
                continue
            
            if notification.retry_count >= max_retries:
                continue
            
            success = await self._send_notification(notification)
            if success:
                retried += 1
        
        return retried
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """获取通知"""
        return self._notifications.get(notification_id)
    
    def get_notifications(
        self,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None,
        limit: int = 100
    ) -> List[Notification]:
        """获取通知列表"""
        notifications = list(self._notifications.values())
        
        if channel:
            notifications = [n for n in notifications if n.channel == channel]
        if status:
            notifications = [n for n in notifications if n.status == status]
        
        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications[:limit]
    
    def mark_as_read(self, notification_id: str) -> bool:
        """标记通知为已读"""
        notification = self._notifications.get(notification_id)
        if notification:
            notification.read_at = datetime.now()
            return True
        return False
    
    async def start(self) -> None:
        """启动通知服务"""
        if self._running:
            return
        
        self._running = True
        logger.info('NotificationService started')
        
        # 启动定时任务
        self._tasks.append(asyncio.create_task(self._cleanup_task()))
        self._tasks.append(asyncio.create_task(self._retry_task()))
    
    async def stop(self) -> None:
        """停止通知服务"""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        self._tasks.clear()
        logger.info('NotificationService stopped')
    
    async def _cleanup_task(self) -> None:
        """清理过期数据"""
        interval = self.config.get('cleanup_interval', 3600)  # 1小时
        
        while self._running:
            try:
                # 清理过期的静默记录
                now = datetime.now()
                expired_keys = [
                    k for k, v in self._silence_cache.items()
                    if now >= v
                ]
                for key in expired_keys:
                    del self._silence_cache[key]
                
                # 清理旧的限流计数器
                for key in list(self._rate_limit_counters.keys()):
                    timestamps = self._rate_limit_counters[key]
                    cutoff = now - timedelta(hours=1)
                    self._rate_limit_counters[key] = [t for t in timestamps if t > cutoff]
                
                logger.debug(f'Cleanup completed: {len(expired_keys)} silence records cleared')
                
            except Exception as e:
                logger.error(f'Error in cleanup task: {e}')
            
            await asyncio.sleep(interval)
    
    async def _retry_task(self) -> None:
        """重试失败通知"""
        interval = self.config.get('retry_interval', 300)  # 5分钟
        
        while self._running:
            try:
                retried = await self.retry_failed()
                if retried > 0:
                    logger.info(f'Retried {retried} failed notifications')
            except Exception as e:
                logger.error(f'Error in retry task: {e}')
            
            await asyncio.sleep(interval)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        notifications = list(self._notifications.values())
        
        return {
            'total_notifications': len(notifications),
            'pending': len([n for n in notifications if n.status == NotificationStatus.PENDING]),
            'sending': len([n for n in notifications if n.status == NotificationStatus.SENDING]),
            'sent': len([n for n in notifications if n.status == NotificationStatus.SENT]),
            'failed': len([n for n in notifications if n.status == NotificationStatus.FAILED]),
            'rate_limited': len([n for n in notifications if n.status == NotificationStatus.RATE_LIMITED]),
            'by_channel': {
                ch.value: len([n for n in notifications if n.channel == ch])
                for ch in NotificationChannel
            },
            'silence_cache_size': len(self._silence_cache)
        }