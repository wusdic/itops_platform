"""
告警触发器模块
BM-01 监控告警
提供告警生成、告警升级策略、告警确认、告警处理、告警关闭等功能
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio

from .monitor import AlertSeverity
from .rules import AlertEvent, AlertState

logger = logging.getLogger(__name__)


class TicketStatus(Enum):
    """工单状态枚举"""
    OPEN = 'open'
    ACKNOWLEDGED = 'acknowledged'
    ASSIGNED = 'assigned'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    CLOSED = 'closed'


class EscalationLevel(Enum):
    """升级级别枚举"""
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    MAX = 4


@dataclass
class EscalationPolicy:
    """升级策略"""
    level: int
    wait_seconds: int  # 等待时间
    notify_channels: List[str]  # 通知渠道
    assignees: List[str] = field(default_factory=list)  # 分配给谁
    actions: List[str] = field(default_factory=list)  # 执行动作
    description: str = ''


@dataclass
class AlertTicket:
    """告警工单"""
    id: str
    alert_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: TicketStatus
    
    # 基本信息
    device_id: str
    metric_name: str
    value: float
    threshold_value: float
    message: str
    
    # 时间和用户
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    
    # 分配信息
    assignee: Optional[str] = None
    assignee_group: Optional[str] = None
    
    # 升级信息
    escalation_level: int = 0
    escalation_count: int = 0
    last_escalated_at: Optional[datetime] = None
    
    # 元数据
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 关联信息
    related_tickets: List[str] = field(default_factory=list)
    linked_incidents: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'status': self.status.value,
            'device_id': self.device_id,
            'metric_name': self.metric_name,
            'value': self.value,
            'threshold_value': self.threshold_value,
            'message': self.message,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'acknowledged_by': self.acknowledged_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'closed_by': self.closed_by,
            'assignee': self.assignee,
            'assignee_group': self.assignee_group,
            'escalation_level': self.escalation_level,
            'escalation_count': self.escalation_count,
            'last_escalated_at': self.last_escalated_at.isoformat() if self.last_escalated_at else None,
            'labels': self.labels,
            'annotations': self.annotations,
            'notes': self.notes,
            'history': self.history,
            'related_tickets': self.related_tickets,
            'linked_incidents': self.linked_incidents
        }
    
    def add_note(self, content: str, user: str) -> None:
        """添加备注"""
        note = {
            'content': content,
            'user': user,
            'timestamp': datetime.now().isoformat()
        }
        self.notes.append(note)
        self._add_history('note_added', note)
    
    def _add_history(self, action: str, details: Any) -> None:
        """添加历史记录"""
        entry = {
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.history.append(entry)
    
    @property
    def is_open(self) -> bool:
        return self.status == TicketStatus.OPEN
    
    @property
    def is_acknowledged(self) -> bool:
        return self.status in [TicketStatus.ACKNOWLEDGED, TicketStatus.ASSIGNED, 
                              TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED]
    
    @property
    def age_minutes(self) -> int:
        return int((datetime.now() - self.created_at).total_seconds() / 60)
    
    @property
    def unacknowledged_minutes(self) -> int:
        if self.acknowledged_at:
            return int((self.acknowledged_at - self.created_at).total_seconds() / 60)
        return self.age_minutes


class AlertTrigger:
    """
    告警触发器
    负责告警的生成、升级、确认、处理、关闭
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化告警触发器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # 工单存储
        self._tickets: Dict[str, AlertTicket] = {}
        self._alert_to_ticket: Dict[str, str] = {}  # alert_id -> ticket_id
        
        # 升级策略
        self._escalation_policies: List[EscalationPolicy] = []
        self._setup_default_escalation()
        
        # 回调函数
        self._ticket_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._notification_callbacks: List[Callable] = []
        
        # 自动关闭配置
        self._auto_close_interval = self.config.get('auto_close_interval', 86400)  # 24小时
        self._auto_resolve_threshold = self.config.get('auto_resolve_threshold', 3600)  # 1小时
        
        # SLA配置
        self._sla_config = self.config.get('sla', {
            'critical': {'acknowledge': 15, 'resolve': 60},
            'error': {'acknowledge': 30, 'resolve': 240},
            'warning': {'acknowledge': 60, 'resolve': 480},
            'info': {'acknowledge': 120, 'resolve': 1440}
        })
        
        logger.info('AlertTrigger initialized')
    
    def _setup_default_escalation(self) -> None:
        """设置默认升级策略"""
        self._escalation_policies = [
            EscalationPolicy(
                level=1,
                wait_seconds=300,  # 5分钟
                notify_channels=['email'],
                description='Level 1: 通知值班人员'
            ),
            EscalationPolicy(
                level=2,
                wait_seconds=600,  # 10分钟
                notify_channels=['email', 'sms'],
                assignees=['on_call_manager'],
                description='Level 2: 通知运维经理'
            ),
            EscalationPolicy(
                level=3,
                wait_seconds=900,  # 15分钟
                notify_channels=['email', 'sms', 'phone'],
                assignees=['team_lead'],
                description='Level 3: 升级到团队负责人'
            ),
        ]
    
    def add_escalation_policy(self, policy: EscalationPolicy) -> None:
        """添加升级策略"""
        self._escalation_policies.append(policy)
        self._escalation_policies.sort(key=lambda p: p.level)
    
    def register_ticket_callback(self, event: str, callback: Callable) -> None:
        """注册工单回调"""
        self._ticket_callbacks[event].append(callback)
    
    def register_notification_callback(self, callback: Callable) -> None:
        """注册通知回调"""
        self._notification_callbacks.append(callback)
    
    def create_ticket(self, alert: AlertEvent) -> Optional[AlertTicket]:
        """
        从告警事件创建工单
        
        Args:
            alert: 告警事件
            
        Returns:
            创建的工单或None
        """
        # 检查是否已有工单
        if alert.id in self._alert_to_ticket:
            logger.warning(f'Ticket already exists for alert {alert.id}')
            return self._tickets.get(self._alert_to_ticket[alert.id])
        
        # 生成工单ID - 使用微秒确保唯一性
        import random
        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{alert.rule_id[:4]}-{random.randint(1000, 9999)}"
        
        now = datetime.now()
        ticket = AlertTicket(
            id=ticket_id,
            alert_id=alert.id,
            rule_id=alert.rule_id,
            rule_name=alert.rule_name,
            severity=alert.severity,
            status=TicketStatus.OPEN,
            device_id=alert.device_id,
            metric_name=alert.metric_name,
            value=alert.value,
            threshold_value=alert.threshold_value,
            message=alert.message,
            created_at=now,
            updated_at=now,
            labels=alert.labels,
            annotations=alert.annotations
        )
        
        # 存储工单
        self._tickets[ticket_id] = ticket
        self._alert_to_ticket[alert.id] = ticket_id
        
        # 触发回调
        self._trigger_ticket_callbacks(ticket, 'created')
        
        logger.info(f'Created ticket {ticket_id} for alert {alert.id}')
        return ticket
    
    def acknowledge_ticket(
        self,
        ticket_id: str,
        user: str,
        note: Optional[str] = None
    ) -> bool:
        """
        确认工单
        
        Args:
            ticket_id: 工单ID
            user: 确认用户
            note: 备注
            
        Returns:
            是否成功
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            logger.error(f'Ticket {ticket_id} not found')
            return False
        
        now = datetime.now()
        ticket.status = TicketStatus.ACKNOWLEDGED
        ticket.acknowledged_at = now
        ticket.acknowledged_by = user
        ticket.updated_at = now
        
        if note:
            ticket.add_note(note, user)
        
        # 更新标签
        ticket.labels['acknowledged_by'] = user
        ticket.labels['acknowledged_at'] = now.isoformat()
        
        # 触发回调
        self._trigger_ticket_callbacks(ticket, 'acknowledged')
        
        logger.info(f'Ticket {ticket_id} acknowledged by {user}')
        return True
    
    def assign_ticket(
        self,
        ticket_id: str,
        assignee: str,
        assignee_group: Optional[str] = None,
        user: str = 'system'
    ) -> bool:
        """
        分配工单
        
        Args:
            ticket_id: 工单ID
            assignee: 分配给谁
            assignee_group: 分配组
            user: 操作人
            
        Returns:
            是否成功
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            logger.error(f'Ticket {ticket_id} not found')
            return False
        
        ticket.assignee = assignee
        ticket.assignee_group = assignee_group
        ticket.status = TicketStatus.ASSIGNED
        ticket.updated_at = datetime.now()
        
        ticket._add_history('assigned', {
            'assignee': assignee,
            'assignee_group': assignee_group,
            'by': user
        })
        
        # 触发回调
        self._trigger_ticket_callbacks(ticket, 'assigned')
        
        logger.info(f'Ticket {ticket_id} assigned to {assignee}')
        return True
    
    def start_work(
        self,
        ticket_id: str,
        user: str
    ) -> bool:
        """
        开始处理工单
        
        Args:
            ticket_id: 工单ID
            user: 处理人
            
        Returns:
            是否成功
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.updated_at = datetime.now()
        
        ticket._add_history('work_started', {'by': user})
        
        self._trigger_ticket_callbacks(ticket, 'work_started')
        return True
    
    def resolve_ticket(
        self,
        ticket_id: str,
        user: str,
        resolution: str = '',
        note: Optional[str] = None
    ) -> bool:
        """
        解决工单
        
        Args:
            ticket_id: 工单ID
            user: 解决人
            resolution: 解决方案
            note: 备注
            
        Returns:
            是否成功
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        
        now = datetime.now()
        ticket.status = TicketStatus.RESOLVED
        ticket.resolved_at = now
        ticket.resolved_by = user
        ticket.updated_at = now
        
        if resolution:
            ticket.annotations['resolution'] = resolution
        if note:
            ticket.add_note(note, user)
        
        ticket._add_history('resolved', {
            'by': user,
            'resolution': resolution
        })
        
        # 触发回调
        self._trigger_ticket_callbacks(ticket, 'resolved')
        
        logger.info(f'Ticket {ticket_id} resolved by {user}')
        return True
    
    def close_ticket(
        self,
        ticket_id: str,
        user: str,
        note: Optional[str] = None
    ) -> bool:
        """
        关闭工单
        
        Args:
            ticket_id: 工单ID
            user: 关闭人
            note: 备注
            
        Returns:
            是否成功
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        
        now = datetime.now()
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = now
        ticket.closed_by = user
        ticket.updated_at = now
        
        if note:
            ticket.add_note(note, user)
        
        ticket._add_history('closed', {'by': user})
        
        # 触发回调
        self._trigger_ticket_callbacks(ticket, 'closed')
        
        logger.info(f'Ticket {ticket_id} closed by {user}')
        return True
    
    def escalate_ticket(self, ticket_id: str) -> bool:
        """
        升级工单
        
        Args:
            ticket_id: 工单ID
            
        Returns:
            是否成功
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        
        # 找到下一级升级策略
        next_level = ticket.escalation_level + 1
        if next_level > EscalationLevel.MAX.value:
            logger.warning(f'Ticket {ticket_id} already at max escalation level')
            return False
        
        policy = None
        for p in self._escalation_policies:
            if p.level == next_level:
                policy = p
                break
        
        if not policy:
            logger.error(f'No escalation policy for level {next_level}')
            return False
        
        now = datetime.now()
        ticket.escalation_level = next_level
        ticket.escalation_count += 1
        ticket.last_escalated_at = now
        ticket.updated_at = now
        
        # 触发通知
        self._trigger_escalation_notification(ticket, policy)
        
        ticket._add_history('escalated', {
            'level': next_level,
            'policy': policy.description,
            'notify_channels': policy.notify_channels
        })
        
        self._trigger_ticket_callbacks(ticket, 'escalated')
        
        logger.info(f'Ticket {ticket_id} escalated to level {next_level}')
        return True
    
    def _trigger_escalation_notification(
        self,
        ticket: AlertTicket,
        policy: EscalationPolicy
    ) -> None:
        """触发升级通知"""
        notification_data = {
            'type': 'escalation',
            'ticket': ticket.to_dict(),
            'level': policy.level,
            'channels': policy.notify_channels,
            'assignees': policy.assignees,
            'actions': policy.actions
        }
        
        for callback in self._notification_callbacks:
            try:
                callback(notification_data)
            except Exception as e:
                logger.error(f'Error in escalation notification: {e}')
    
    def check_escalation(self) -> List[str]:
        """
        检查需要升级的工单
        
        Returns:
            已升级的工单ID列表
        """
        now = datetime.now()
        escalated = []
        
        for ticket in self._tickets.values():
            # 只检查OPEN和ACKNOWLEDGED状态的工单
            if ticket.status not in [TicketStatus.OPEN, TicketStatus.ACKNOWLEDGED]:
                continue
            
            # 找到当前级别的策略
            policy = None
            for p in self._escalation_policies:
                if p.level == ticket.escalation_level:
                    policy = p
                    break
            
            if not policy:
                continue
            
            # 检查是否需要升级
            last_check = ticket.last_escalated_at or ticket.created_at
            elapsed = (now - last_check).total_seconds()
            
            if elapsed >= policy.wait_seconds:
                if self.escalate_ticket(ticket.id):
                    escalated.append(ticket.id)
        
        return escalated
    
    def check_sla(self) -> List[Dict[str, Any]]:
        """
        检查SLA合规性
        
        Returns:
            违反SLA的工单列表
        """
        violations = []
        now = datetime.now()
        
        for ticket in self._tickets.values():
            if ticket.status == TicketStatus.CLOSED:
                continue
            
            sla = self._sla_config.get(ticket.severity.value, {})
            
            # 检查确认SLA
            ack_limit = sla.get('acknowledge', 60)
            if not ticket.acknowledged_at:
                ack_age = ticket.age_minutes
                if ack_age > ack_limit:
                    violations.append({
                        'ticket_id': ticket.id,
                        'type': 'acknowledge',
                        'age_minutes': ack_age,
                        'limit_minutes': ack_limit
                    })
            
            # 检查解决SLA
            resolve_limit = sla.get('resolve', 1440)
            if ticket.resolved_at:
                resolve_age = int((ticket.resolved_at - ticket.created_at).total_seconds() / 60)
            else:
                resolve_age = ticket.age_minutes
            
            if resolve_age > resolve_limit:
                violations.append({
                    'ticket_id': ticket.id,
                    'type': 'resolve',
                    'age_minutes': resolve_age,
                    'limit_minutes': resolve_limit
                })
        
        return violations
    
    def get_ticket(self, ticket_id: str) -> Optional[AlertTicket]:
        """获取工单"""
        return self._tickets.get(ticket_id)
    
    def get_tickets(
        self,
        status: Optional[TicketStatus] = None,
        severity: Optional[AlertSeverity] = None,
        assignee: Optional[str] = None,
        limit: int = 100
    ) -> List[AlertTicket]:
        """获取工单列表"""
        tickets = list(self._tickets.values())
        
        if status:
            tickets = [t for t in tickets if t.status == status]
        if severity:
            tickets = [t for t in tickets if t.severity == severity]
        if assignee:
            tickets = [t for t in tickets if t.assignee == assignee]
        
        # 按创建时间降序
        tickets.sort(key=lambda t: t.created_at, reverse=True)
        
        return tickets[:limit]
    
    def get_open_tickets(self) -> List[AlertTicket]:
        """获取未关闭的工单"""
        return [t for t in self._tickets.values() 
                if t.status != TicketStatus.CLOSED]
    
    def get_tickets_by_device(self, device_id: str) -> List[AlertTicket]:
        """获取设备相关的工单"""
        return [t for t in self._tickets.values() if t.device_id == device_id]
    
    def get_tickets_by_rule(self, rule_id: str) -> List[AlertTicket]:
        """获取规则相关的工单"""
        return [t for t in self._tickets.values() if t.rule_id == rule_id]
    
    def auto_resolve(self) -> int:
        """
        自动解决已恢复的告警工单
        
        Returns:
            解决的工单数量
        """
        resolved = 0
        now = datetime.now()
        
        for ticket in list(self._tickets.values()):
            if ticket.status != TicketStatus.RESOLVED:
                continue
            
            if ticket.resolved_at:
                elapsed = (now - ticket.resolved_at).total_seconds()
                
                # 检查是否需要自动关闭
                if elapsed >= self._auto_close_interval:
                    self.close_ticket(ticket.id, 'system', 'Auto-closed after resolution')
                    resolved += 1
        
        return resolved
    
    def _trigger_ticket_callbacks(self, ticket: AlertTicket, event: str) -> None:
        """触发工单回调"""
        callbacks = self._ticket_callbacks.get(event, [])
        callbacks.extend(self._ticket_callbacks.get('*', []))
        
        for callback in callbacks:
            try:
                callback(ticket, event)
            except Exception as e:
                logger.error(f'Error in ticket callback: {e}')
    
    async def start(self) -> None:
        """启动告警触发器"""
        if self._running:
            return
        
        self._running = True
        logger.info('AlertTrigger started')
        
        # 启动定时任务
        self._tasks.append(asyncio.create_task(self._escalation_check_task()))
        self._tasks.append(asyncio.create_task(self._auto_resolve_task()))
    
    async def stop(self) -> None:
        """停止告警触发器"""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        self._tasks.clear()
        logger.info('AlertTrigger stopped')
    
    async def _escalation_check_task(self) -> None:
        """升级检查定时任务"""
        interval = self.config.get('escalation_check_interval', 60)
        
        while self._running:
            try:
                self.check_escalation()
            except Exception as e:
                logger.error(f'Error in escalation check: {e}')
            
            await asyncio.sleep(interval)
    
    async def _auto_resolve_task(self) -> None:
        """自动解决定时任务"""
        interval = self.config.get('auto_resolve_interval', 300)
        
        while self._running:
            try:
                self.auto_resolve()
            except Exception as e:
                logger.error(f'Error in auto resolve: {e}')
            
            await asyncio.sleep(interval)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        tickets = list(self._tickets.values())
        
        return {
            'total_tickets': len(tickets),
            'open_tickets': len([t for t in tickets if t.status == TicketStatus.OPEN]),
            'acknowledged_tickets': len([t for t in tickets if t.status == TicketStatus.ACKNOWLEDGED]),
            'in_progress_tickets': len([t for t in tickets if t.status == TicketStatus.IN_PROGRESS]),
            'resolved_tickets': len([t for t in tickets if t.status == TicketStatus.RESOLVED]),
            'closed_tickets': len([t for t in tickets if t.status == TicketStatus.CLOSED]),
            'escalated_tickets': len([t for t in tickets if t.escalation_level > 0]),
            'tickets_by_severity': {
                s.value: len([t for t in tickets if t.severity.name == s.name])
                for s in AlertSeverity
            }
        }