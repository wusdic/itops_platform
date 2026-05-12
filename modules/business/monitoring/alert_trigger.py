"""
告警触发自动化模块
BM-01 监控告警
提供告警触发规则管理、自动触发、触发历史等功能
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import json
import asyncio

logger = logging.getLogger(__name__)


class TriggerStatus(str, Enum):
    """触发状态枚举"""
    PENDING = 'pending'       # 待触发
    TRIGGERED = 'triggered'  # 已触发
    SUPPRESSED = 'suppressed'  # 已抑制
    EXPIRED = 'expired'      # 已过期


class TriggerCondition(str, Enum):
    """触发条件枚举"""
    THRESHOLD = 'threshold'           # 阈值触发
    CHANGE = 'change'                 # 变化触发
    RATE = 'rate'                     # 速率触发
    CONSTANT = 'constant'             # 持续触发
    EXPRESSION = 'expression'         # 表达式触发


@dataclass
class TriggerRule:
    """触发规则"""
    id: str
    name: str
    description: str = ''
    
    # 启用状态
    enabled: bool = True
    
    # 触发条件类型
    condition_type: TriggerCondition = TriggerCondition.THRESHOLD
    
    # 匹配条件 (JSON格式)
    # threshold: {"metric": "cpu_usage", "operator": ">", "value": 80}
    # change: {"metric": "cpu_usage", "change_percent": 50}
    # rate: {"metric": "cpu_usage", "rate": "increase", "threshold": 10}
    # constant: {"metric": "cpu_usage", "duration_seconds": 300}
    # expression: {"expr": "cpu_usage > 80 && memory_usage > 90"}
    match_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # 告警配置
    alert_level: str = 'warning'  # critical, high, medium, low, info
    alert_title_template: str = '{metric}告警'
    alert_message_template: str = '{metric}超过阈值，当前值:{value}，阈值:{threshold}'
    
    # 作用域过滤
    device_ids: List[int] = field(default_factory=list)  # 设备ID列表
    device_types: List[str] = field(default_factory=list)  # 设备类型列表
    tags_filter: Dict[str, str] = field(default_factory=dict)  # 标签过滤
    
    # 抑制配置
    suppress_enabled: bool = False
    suppress_duration: int = 300  # 抑制时间(秒)
    suppress_key: Optional[str] = None  # 抑制键
    
    # 触发间隔
    trigger_interval: int = 60  # 触发间隔(秒)，避免重复触发
    
    # 触发后的动作
    actions: List[Dict[str, Any]] = field(default_factory=list)
    # [{"type": "notify", "channels": ["email", "dingtalk"]}, {"type": "webhook", "url": "..."}]
    
    # 时间窗口配置
    time_windows: List[Dict[str, Any]] = field(default_factory=list)
    # [{"days": [1,2,3,4,5,6,7], "start_hour": 9, "end_hour": 18}]
    
    # 元数据
    priority: int = 100  # 优先级
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = 'system'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'condition_type': self.condition_type.value if isinstance(self.condition_type, TriggerCondition) else self.condition_type,
            'match_conditions': self.match_conditions,
            'alert_level': self.alert_level,
            'alert_title_template': self.alert_title_template,
            'alert_message_template': self.alert_message_template,
            'device_ids': self.device_ids,
            'device_types': self.device_types,
            'tags_filter': self.tags_filter,
            'suppress_enabled': self.suppress_enabled,
            'suppress_duration': self.suppress_duration,
            'suppress_key': self.suppress_key,
            'trigger_interval': self.trigger_interval,
            'actions': self.actions,
            'time_windows': self.time_windows,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }


@dataclass
class TriggerEvent:
    """触发事件"""
    id: str
    rule_id: str
    rule_name: str
    status: TriggerStatus
    
    # 触发信息
    trigger_time: datetime
    metric_name: str
    metric_value: float
    threshold_value: float
    device_id: int
    device_name: str
    device_ip: str
    
    # 告警信息
    alert_id: Optional[str] = None
    alert_level: str = 'warning'
    alert_title: str = ''
    alert_message: str = ''
    
    # 元数据
    conditions_snapshot: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'status': self.status.value if isinstance(self.status, TriggerStatus) else self.status,
            'trigger_time': self.trigger_time.isoformat() if self.trigger_time else None,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'threshold_value': self.threshold_value,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_ip': self.device_ip,
            'alert_id': self.alert_id,
            'alert_level': self.alert_level,
            'alert_title': self.alert_title,
            'alert_message': self.alert_message,
            'conditions_snapshot': self.conditions_snapshot,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AlertTriggerEngine:
    """
    告警触发引擎
    负责规则的评估、触发、执行动作
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._rules: Dict[str, TriggerRule] = {}
        self._events: Dict[str, TriggerEvent] = {}
        self._last_trigger_time: Dict[str, datetime] = {}  # rule_id -> last trigger time
        self._suppressed_keys: Dict[str, datetime] = {}  # suppress_key -> expire_time
        
        # 回调函数
        self._trigger_callbacks: List[Callable] = []
        self._action_handlers: Dict[str, Callable] = {}
        
        # 注册默认动作处理器
        self._register_default_handlers()
        
        logger.info('AlertTriggerEngine initialized')
    
    def _register_default_handlers(self):
        """注册默认动作处理器"""
        # notify动作处理器
        async def notify_handler(action: Dict[str, Any], event: TriggerEvent):
            logger.info(f"Notify action: channels={action.get('channels')}, event={event.id}")
            # 实际实现会调用NotificationManager发送通知
            return True
        
        # webhook动作处理器
        async def webhook_handler(action: Dict[str, Any], event: TriggerEvent):
            logger.info(f"Webhook action: url={action.get('url')}, event={event.id}")
            # 实际实现会发送HTTP请求
            return True
        
        # create_ticket动作处理器
        async def ticket_handler(action: Dict[str, Any], event: TriggerEvent):
            logger.info(f"Create ticket action: event={event.id}")
            # 实际实现会创建工单
            return True
        
        self._action_handlers['notify'] = notify_handler
        self._action_handlers['webhook'] = webhook_handler
        self._action_handlers['create_ticket'] = ticket_handler
    
    def register_action_handler(self, action_type: str, handler: Callable):
        """注册动作处理器"""
        self._action_handlers[action_type] = handler
    
    def register_trigger_callback(self, callback: Callable):
        """注册触发回调"""
        self._trigger_callbacks.append(callback)
    
    def add_rule(self, rule: TriggerRule) -> str:
        """添加触发规则"""
        self._rules[rule.id] = rule
        logger.info(f'Added trigger rule: {rule.id} - {rule.name}')
        return rule.id
    
    def update_rule(self, rule: TriggerRule):
        """更新触发规则"""
        rule.updated_at = datetime.now()
        self._rules[rule.id] = rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除触发规则"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[TriggerRule]:
        """获取规则"""
        return self._rules.get(rule_id)
    
    def list_rules(self, enabled_only: bool = False) -> List[TriggerRule]:
        """列出规则"""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return sorted(rules, key=lambda r: r.priority)
    
    def evaluate_threshold(
        self,
        metric_name: str,
        value: float,
        operator: str,
        threshold: float
    ) -> bool:
        """评估阈值条件"""
        ops = {
            '>': lambda v, t: v > t,
            '<': lambda v, t: v < t,
            '>=': lambda v, t: v >= t,
            '<=': lambda v, t: v <= t,
            '==': lambda v, t: v == t,
            '!=': lambda v, t: v != t,
        }
        op_func = ops.get(operator, ops['>'])
        return op_func(value, threshold)
    def evaluate_change(
        self,
        current_value: float,
        previous_value: float,
        change_percent: float
    ) -> bool:
        """评估变化条件"""
        if previous_value == 0:
            return current_value > 0
        change = abs((current_value - previous_value) / previous_value * 100)
        return change >= change_percent
    
    def evaluate_rate(
        self,
        current_value: float,
        previous_value: float,
        rate_threshold: float
    ) -> bool:
        """评估速率条件"""
        rate = current_value - previous_value
        return abs(rate) >= rate_threshold
    
    def evaluate_constant(
        self,
        duration_seconds: int,
        start_time: datetime
    ) -> bool:
        """评估持续条件"""
        elapsed = (datetime.now() - start_time).total_seconds()
        return elapsed >= duration_seconds
    
    def evaluate_expression(self, expr: str, context: Dict[str, Any]) -> bool:
        """评估表达式条件"""
        try:
            # 简单表达式评估，支持基本操作符
            # 实际生产环境应使用安全的表达式引擎
            allowed_chars = set('0123456789.+-*/%<>=!&|()三角函数sqrt pow cos sin tan abs _')
            if not all(c in allowed_chars or c.isalnum() or c.isspace() for c in expr):
                return False
            result = eval(expr, {"__builtins__": {}}, context)
            return bool(result)
        except Exception as e:
            logger.error(f"Expression evaluation error: {e}")
            return False
    
    def _check_time_windows(self, rule: TriggerRule) -> bool:
        """检查是否在允许的时间窗口内"""
        if not rule.time_windows:
            return True  # 没有配置时间窗口，默认允许
        
        now = datetime.now()
        current_day = now.weekday()  # 0=Monday, 6=Sunday
        current_hour = now.hour
        
        for window in rule.time_windows:
            days = window.get('days', [0, 1, 2, 3, 4, 5, 6])
            start_hour = window.get('start_hour', 0)
            end_hour = window.get('end_hour', 23)
            
            if current_day in days and start_hour <= current_hour <= end_hour:
                return True
        
        return False
    
    def _is_suppressed(self, rule: TriggerRule, device_id: int, metric_name: str) -> bool:
        """检查是否被抑制"""
        if not rule.suppress_enabled:
            return False
        
        # 检查suppress_key
        suppress_key = rule.suppress_key or f"{rule.id}:{device_id}:{metric_name}"
        
        # 检查是否在抑制列表中
        if suppress_key in self._suppressed_keys:
            expire_time = self._suppressed_keys[suppress_key]
            if datetime.now() < expire_time:
                return True
            else:
                # 抑制已过期，移除
                del self._suppressed_keys[suppress_key]
        
        return False
    
    def _add_suppress(self, rule: TriggerRule, device_id: int, metric_name: str):
        """添加抑制"""
        if rule.suppress_enabled:
            suppress_key = rule.suppress_key or f"{rule.id}:{device_id}:{metric_name}"
            expire_time = datetime.now() + timedelta(seconds=rule.suppress_duration)
            self._suppressed_keys[suppress_key] = expire_time
    
    def _should_trigger(self, rule: TriggerRule, device_id: int, metric_name: str) -> bool:
        """检查是否应该触发"""
        # 检查启用状态
        if not rule.enabled:
            return False
        
        # 检查时间窗口
        if not self._check_time_windows(rule):
            return False
        
        # 检查触发间隔
        last_time = self._last_trigger_time.get(rule.id)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < rule.trigger_interval:
                return False
        
        # 检查抑制
        if self._is_suppressed(rule, device_id, metric_name):
            return False
        
        return True
    
    def _generate_alert_info(self, rule: TriggerRule, metric_name: str, value: float, threshold: float) -> tuple:
        """生成告警标题和消息"""
        title = rule.alert_title_template.format(
            metric=metric_name,
            value=value,
            threshold=threshold
        )
        message = rule.alert_message_template.format(
            metric=metric_name,
            value=value,
            threshold=threshold
        )
        return title, message
    
    async def evaluate_and_trigger(
        self,
        metric_name: str,
        value: float,
        device_id: int,
        device_name: str,
        device_ip: str,
        previous_value: Optional[float] = None,
        duration_seconds: Optional[int] = None,
        start_time: Optional[datetime] = None
    ) -> List[TriggerEvent]:
        """
        评估指标并触发符合条件的规则
        
        Args:
            metric_name: 指标名称
            value: 当前值
            device_id: 设备ID
            device_name: 设备名称
            device_ip: 设备IP
            previous_value: 前一个值(用于变化/速率评估)
            duration_seconds: 持续时间(用于持续条件评估)
            start_time: 开始时间(用于持续条件评估)
        
        Returns:
            触发的事件列表
        """
        triggered_events = []
        
        for rule in self.list_rules(enabled_only=True):
            # 过滤设备范围
            if rule.device_ids and device_id not in rule.device_ids:
                continue
            
            # 检查是否应该触发
            if not self._should_trigger(rule, device_id, metric_name):
                continue
            
            # 评估条件
            conditions = rule.match_conditions
            condition_type = rule.condition_type
            
            triggered = False
            threshold_value = 0
            
            try:
                if condition_type == TriggerCondition.THRESHOLD:
                    operator = conditions.get('operator', '>')
                    threshold_value = conditions.get('value', 0)
                    triggered = self.evaluate_threshold(metric_name, value, operator, threshold_value)
                
                elif condition_type == TriggerCondition.CHANGE:
                    if previous_value is None:
                        continue
                    change_percent = conditions.get('change_percent', 50)
                    triggered = self.evaluate_change(value, previous_value, change_percent)
                    threshold_value = conditions.get('change_percent', 50)
                
                elif condition_type == TriggerCondition.RATE:
                    if previous_value is None:
                        continue
                    threshold_value = conditions.get('threshold', 10)
                    triggered = self.evaluate_rate(value, previous_value, threshold_value)
                
                elif condition_type == TriggerCondition.CONSTANT:
                    if duration_seconds is None or start_time is None:
                        continue
                    triggered = self.evaluate_constant(duration_seconds, start_time)
                    threshold_value = conditions.get('duration_seconds', 300)
                
                elif condition_type == TriggerCondition.EXPRESSION:
                    context = {
                        'value': value,
                        'previous_value': previous_value,
                        'metric': metric_name,
                        'device_id': device_id,
                        'device_name': device_name,
                    }
                    triggered = self.evaluate_expression(conditions.get('expr', ''), context)
                
                if triggered:
                    # 生成告警信息
                    alert_title, alert_message = self._generate_alert_info(
                        rule, metric_name, value, threshold_value
                    )
                    
                    # 创建触发事件
                    import uuid
                    event = TriggerEvent(
                        id=str(uuid.uuid4()),
                        rule_id=rule.id,
                        rule_name=rule.name,
                        status=TriggerStatus.TRIGGERED,
                        trigger_time=datetime.now(),
                        metric_name=metric_name,
                        metric_value=value,
                        threshold_value=threshold_value,
                        device_id=device_id,
                        device_name=device_name,
                        device_ip=device_ip,
                        alert_level=rule.alert_level,
                        alert_title=alert_title,
                        alert_message=alert_message,
                        conditions_snapshot=conditions,
                    )
                    
                    # 添加抑制
                    self._add_suppress(rule, device_id, metric_name)
                    
                    # 更新最后触发时间
                    self._last_trigger_time[rule.id] = datetime.now()
                    
                    # 存储事件
                    self._events[event.id] = event
                    triggered_events.append(event)
                    
                    # 触发回调
                    for callback in self._trigger_callbacks:
                        try:
                            await callback(event)
                        except Exception as e:
                            logger.error(f"Trigger callback error: {e}")
                    
                    # 执行动作
                    await self._execute_actions(rule, event)
            
            except Exception as e:
                logger.error(f"Rule {rule.id} evaluation error: {e}")
        
        return triggered_events
    
    async def _execute_actions(self, rule: TriggerRule, event: TriggerEvent):
        """执行规则动作"""
        for action in rule.actions:
            action_type = action.get('type')
            handler = self._action_handlers.get(action_type)
            
            if handler:
                try:
                    await handler(action, event)
                except Exception as e:
                    logger.error(f"Action {action_type} execution error: {e}")
    
    def get_event(self, event_id: str) -> Optional[TriggerEvent]:
        """获取触发事件"""
        return self._events.get(event_id)
    
    def list_events(
        self,
        rule_id: Optional[str] = None,
        status: Optional[TriggerStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TriggerEvent]:
        """列出触发事件"""
        events = list(self._events.values())
        
        if rule_id:
            events = [e for e in events if e.rule_id == rule_id]
        
        if status:
            events = [e for e in events if e.status == status]
        
        if start_time:
            events = [e for e in events if e.trigger_time >= start_time]
        
        if end_time:
            events = [e for e in events if e.trigger_time <= end_time]
        
        # 按时间倒序
        events.sort(key=lambda e: e.trigger_time, reverse=True)
        
        return events[:limit]
    
    def clear_old_events(self, hours: int = 24):
        """清理旧事件"""
        cutoff = datetime.now() - timedelta(hours=hours)
        to_remove = [
            event_id for event_id, event in self._events.items()
            if event.created_at < cutoff
        ]
        for event_id in to_remove:
            del self._events[event_id]
        logger.info(f"Cleared {len(to_remove)} old events")


# 全局触发引擎实例
_trigger_engine: Optional[AlertTriggerEngine] = None


def get_trigger_engine() -> AlertTriggerEngine:
    """获取触发引擎单例"""
    global _trigger_engine
    if _trigger_engine is None:
        _trigger_engine = AlertTriggerEngine()
    return _trigger_engine


def init_trigger_engine(config: Optional[Dict[str, Any]] = None) -> AlertTriggerEngine:
    """初始化触发引擎"""
    global _trigger_engine
    _trigger_engine = AlertTriggerEngine(config)
    return _trigger_engine
