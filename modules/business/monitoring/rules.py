"""
告警规则引擎模块
BM-01 监控告警
提供告警规则定义、阈值告警、趋势告警、复合告警、告警抑制与去重、告警收敛等功能
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import json

from .monitor import MetricPoint, AlertSeverity

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """规则类型枚举"""
    THRESHOLD = 'threshold'           # 静态阈值
    DYNAMIC_THRESHOLD = 'dynamic'    # 动态阈值
    TREND = 'trend'                  # 趋势告警
    COMPOUND = 'compound'            # 复合告警
    HEALTH_CHECK = 'health_check'    # 健康检查


class AlertState(Enum):
    """告警状态枚举"""
    PENDING = 'pending'      # 待触发
    FIRING = 'firing'        # 触发中
    RESOLVED = 'resolved'    # 已恢复
    SUPPRESSED = 'suppressed' # 已抑制


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    rule_type: RuleType
    enabled: bool = True
    severity: AlertSeverity = AlertSeverity.WARNING
    
    # 匹配条件
    metric_name: str = ''
    devices: List[str] = field(default_factory=lambda: ['*'])  # *表示所有设备
    
    # 阈值配置
    thresholds: List[Dict[str, Any]] = field(default_factory=list)
    
    # 趋势配置
    trend_direction: str = ''  # 'up', 'down', 'any'
    change_threshold: float = 0.0  # 变化阈值
    
    # 复合规则配置
    sub_rules: List[str] = field(default_factory=list)  # 子规则ID列表
    composite_operator: str = 'AND'  # AND, OR
    composite_threshold: int = 1  # 满足多少个子规则触发
    
    # 时间窗口配置
    duration: int = 0  # 持续时间（秒），0表示立即触发
    evaluation_interval: int = 60  # 评估间隔（秒）
    
    # 抑制配置
    suppress_interval: int = 300  # 抑制间隔（秒）
    deduplicate_key: str = ''  # 去重键
    
    # 收敛配置
    group_by: List[str] = field(default_factory=list)  # 分组字段
    aggregation_window: int = 60  # 聚合窗口（秒）
    aggregation_func: str = 'count'  # 聚合函数: count, sum, avg, max, min
    
    # 标签和注释
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # 通知配置
    notify_channels: List[str] = field(default_factory=list)
    escalate_after: int = 0  # 升级等待时间（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'rule_type': self.rule_type.value,
            'enabled': self.enabled,
            'severity': self.severity.value,
            'metric_name': self.metric_name,
            'devices': self.devices,
            'thresholds': self.thresholds,
            'trend_direction': self.trend_direction,
            'change_threshold': self.change_threshold,
            'sub_rules': self.sub_rules,
            'composite_operator': self.composite_operator,
            'composite_threshold': self.composite_threshold,
            'duration': self.duration,
            'evaluation_interval': self.evaluation_interval,
            'suppress_interval': self.suppress_interval,
            'deduplicate_key': self.deduplicate_key,
            'group_by': self.group_by,
            'aggregation_window': self.aggregation_window,
            'aggregation_func': self.aggregation_func,
            'labels': self.labels,
            'annotations': self.annotations,
            'notify_channels': self.notify_channels,
            'escalate_after': self.escalate_after
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertRule':
        return cls(
            id=data['id'],
            name=data['name'],
            rule_type=RuleType(data.get('rule_type', 'threshold')),
            enabled=data.get('enabled', True),
            severity=AlertSeverity(data.get('severity', 'warning')),
            metric_name=data.get('metric_name', ''),
            devices=data.get('devices', ['*']),
            thresholds=data.get('thresholds', []),
            trend_direction=data.get('trend_direction', ''),
            change_threshold=data.get('change_threshold', 0.0),
            sub_rules=data.get('sub_rules', []),
            composite_operator=data.get('composite_operator', 'AND'),
            composite_threshold=data.get('composite_threshold', 1),
            duration=data.get('duration', 0),
            evaluation_interval=data.get('evaluation_interval', 60),
            suppress_interval=data.get('suppress_interval', 300),
            deduplicate_key=data.get('deduplicate_key', ''),
            group_by=data.get('group_by', []),
            aggregation_window=data.get('aggregation_window', 60),
            aggregation_func=data.get('aggregation_func', 'count'),
            labels=data.get('labels', {}),
            annotations=data.get('annotations', {}),
            notify_channels=data.get('notify_channels', []),
            escalate_after=data.get('escalate_after', 0)
        )


@dataclass
class AlertEvent:
    """告警事件"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    state: AlertState
    
    # 告警信息
    device_id: str
    metric_name: str
    value: float
    threshold_value: float
    message: str
    
    # 时间信息
    fired_at: datetime
    resolved_at: Optional[datetime] = None
    last_eval_time: Optional[datetime] = None
    
    # 标签和注释
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # 元数据
    fingerprint: str = ''  # 去重指纹
    group_key: str = ''    # 分组键
    update_count: int = 0  # 更新次数
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'state': self.state.value,
            'device_id': self.device_id,
            'metric_name': self.metric_name,
            'value': self.value,
            'threshold_value': self.threshold_value,
            'message': self.message,
            'fired_at': self.fired_at.isoformat() if self.fired_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'last_eval_time': self.last_eval_time.isoformat() if self.last_eval_time else None,
            'labels': self.labels,
            'annotations': self.annotations,
            'fingerprint': self.fingerprint,
            'group_key': self.group_key,
            'update_count': self.update_count
        }


class AlertRulesEngine:
    """
    告警规则引擎
    负责告警规则的定义、评估、执行
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化告警规则引擎
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._rules: Dict[str, AlertRule] = {}
        
        # 活跃告警
        self._active_alerts: Dict[str, AlertEvent] = {}
        
        # 抑制记录
        self._suppression_cache: Dict[str, datetime] = {}
        
        # 去重缓存
        self._deduplication_cache: Dict[str, datetime] = {}
        self._deduplication_ttl = self.config.get('deduplication_ttl', 3600)
        
        # 收敛缓冲
        self._aggregation_buffer: Dict[str, List[AlertEvent]] = defaultdict(list)
        
        # 回调函数
        self._alert_callbacks: List[Callable] = []
        
        # 状态变更回调
        self._state_change_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        logger.info('AlertRulesEngine initialized')
    
    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self._rules[rule.id] = rule
        logger.info(f'Added alert rule: {rule.id} - {rule.name}')
    
    def add_rules(self, rules: List[AlertRule]) -> None:
        """批量添加告警规则"""
        for rule in rules:
            self.add_rule(rule)
    
    def remove_rule(self, rule_id: str) -> bool:
        """删除告警规则"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f'Removed alert rule: {rule_id}')
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取告警规则"""
        return self._rules.get(rule_id)
    
    def get_all_rules(self) -> List[AlertRule]:
        """获取所有告警规则"""
        return list(self._rules.values())
    
    def get_enabled_rules(self) -> List[AlertRule]:
        """获取所有启用的告警规则"""
        return [r for r in self._rules.values() if r.enabled]
    
    def register_alert_callback(self, callback: Callable) -> None:
        """注册告警回调"""
        self._alert_callbacks.append(callback)
    
    def register_state_change_callback(
        self,
        rule_id: str,
        callback: Callable
    ) -> None:
        """注册状态变更回调"""
        self._state_change_callbacks[rule_id].append(callback)
    
    def evaluate(
        self,
        metric: MetricPoint,
        current_time: Optional[datetime] = None
    ) -> List[AlertEvent]:
        """
        评估指标是否触发告警规则
        
        Args:
            metric: 指标数据点
            current_time: 当前时间
            
        Returns:
            触发的告警事件列表
        """
        now = current_time or datetime.now()
        triggered_alerts = []
        
        # 获取匹配的规则
        matching_rules = self._get_matching_rules(metric)
        
        for rule in matching_rules:
            try:
                alert = self._evaluate_rule(rule, metric, now)
                if alert:
                    triggered_alerts.append(alert)
            except Exception as e:
                logger.error(f'Error evaluating rule {rule.id}: {e}')
        
        return triggered_alerts
    
    def _get_matching_rules(self, metric: MetricPoint) -> List[AlertRule]:
        """获取匹配的规则"""
        matching = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            # 检查规则类型
            if rule.rule_type not in [RuleType.THRESHOLD, RuleType.DYNAMIC_THRESHOLD]:
                continue
            
            # 检查指标名称
            if rule.metric_name and rule.metric_name != metric.metric_name:
                continue
            
            # 检查设备
            if '*' not in rule.devices and metric.device_id not in rule.devices:
                continue
            
            matching.append(rule)
        
        return matching
    
    def _evaluate_rule(
        self,
        rule: AlertRule,
        metric: MetricPoint,
        current_time: datetime
    ) -> Optional[AlertEvent]:
        """评估单个规则"""
        # 检查去重
        if self._is_suppressed(rule, metric):
            return None
        
        # 检查阈值
        threshold_triggered, threshold_value = self._check_thresholds(
            metric, rule.thresholds
        )
        
        if not threshold_triggered:
            # 检查是否需要恢复告警
            self._maybe_resolve_alert(rule.id, metric.device_id, current_time)
            return None
        
        # 生成告警指纹
        fingerprint = self._generate_fingerprint(rule, metric)
        
        # 检查去重
        if self._is_duplicate(fingerprint, current_time):
            return None
        
        # 生成告警
        alert = self._create_alert(
            rule=rule,
            metric=metric,
            threshold_value=threshold_value,
            fingerprint=fingerprint,
            current_time=current_time
        )
        
        # 更新活跃告警
        self._update_active_alert(alert, current_time)
        
        # 更新去重缓存
        self._deduplication_cache[fingerprint] = current_time
        
        return alert
    
    def _check_thresholds(
        self,
        metric: MetricPoint,
        thresholds: List[Dict[str, Any]]
    ) -> Tuple[bool, float]:
        """
        检查阈值
        
        Returns:
            (是否触发, 触发的阈值)
        """
        for threshold in thresholds:
            operator = threshold.get('operator', '>')
            value = threshold.get('value', 0)
            
            if self._evaluate_operator(metric.value, operator, value):
                return True, value
        
        return False, 0.0
    
    def _evaluate_operator(
        self,
        value: float,
        operator: str,
        threshold: float
    ) -> bool:
        """评估操作符"""
        operators = {
            '>': lambda v, t: v > t,
            '>=': lambda v, t: v >= t,
            '<': lambda v, t: v < t,
            '<=': lambda v, t: v <= t,
            '==': lambda v, t: abs(v - t) < 1e-9,
            '!=': lambda v, t: abs(v - t) >= 1e-9,
        }
        
        op_func = operators.get(operator)
        if op_func:
            try:
                return op_func(value, threshold)
            except Exception:
                pass
        
        return False
    
    def _is_suppressed(self, rule: AlertRule, metric: MetricPoint) -> bool:
        """检查是否被抑制"""
        key = f"{rule.id}:{metric.device_id}"
        
        if key in self._suppression_cache:
            last_suppress_time = self._suppression_cache[key]
            elapsed = (datetime.now() - last_suppress_time).total_seconds()
            
            if elapsed < rule.suppress_interval:
                return True
            
            # 抑制超时，移除
            del self._suppression_cache[key]
        
        return False
    
    def _is_duplicate(self, fingerprint: str, current_time: datetime) -> bool:
        """检查是否重复告警"""
        if fingerprint in self._deduplication_cache:
            last_time = self._deduplication_cache[fingerprint]
            elapsed = (current_time - last_time).total_seconds()
            
            if elapsed < self._deduplication_ttl:
                return True
            
            # TTL超时，移除
            del self._deduplication_cache[fingerprint]
        
        return False
    
    def _generate_fingerprint(
        self,
        rule: AlertRule,
        metric: MetricPoint
    ) -> str:
        """生成告警指纹"""
        parts = [
            rule.id,
            metric.device_id,
            metric.metric_name
        ]
        
        if rule.deduplicate_key:
            parts.append(rule.deduplicate_key)
        
        content = ':'.join(parts)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _generate_group_key(
        self,
        rule: AlertRule,
        metric: MetricPoint
    ) -> str:
        """生成分组键"""
        if not rule.group_by:
            return ''
        
        parts = [rule.id]
        for key in rule.group_by:
            if key == 'device_id':
                parts.append(metric.device_id)
            elif key == 'metric_name':
                parts.append(metric.metric_name)
            elif key in metric.tags:
                parts.append(metric.tags[key])
        
        return ':'.join(parts)
    
    def _create_alert(
        self,
        rule: AlertRule,
        metric: MetricPoint,
        threshold_value: float,
        fingerprint: str,
        current_time: datetime
    ) -> AlertEvent:
        """创建告警事件"""
        alert_id = f"{rule.id}:{metric.device_id}:{current_time.timestamp()}"
        
        message = (
            f"[{rule.severity.value.upper()}] {rule.name}\n"
            f"设备: {metric.device_id}\n"
            f"指标: {metric.metric_name}\n"
            f"当前值: {metric.value}{metric.unit}\n"
            f"阈值: {threshold_value}{metric.unit}\n"
            f"时间: {current_time.isoformat()}"
        )
        
        # 合并标签
        labels = dict(rule.labels)
        labels['device_id'] = metric.device_id
        labels['metric_name'] = metric.metric_name
        
        return AlertEvent(
            id=alert_id,
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            state=AlertState.FIRING,
            device_id=metric.device_id,
            metric_name=metric.metric_name,
            value=metric.value,
            threshold_value=threshold_value,
            message=message,
            fired_at=current_time,
            last_eval_time=current_time,
            labels=labels,
            annotations=dict(rule.annotations),
            fingerprint=fingerprint,
            group_key=self._generate_group_key(rule, metric)
        )
    
    def _update_active_alert(
        self,
        alert: AlertEvent,
        current_time: datetime
    ) -> None:
        """更新活跃告警"""
        key = f"{alert.rule_id}:{alert.device_id}"
        existing = self._active_alerts.get(key)
        
        if existing:
            # 更新已有告警
            existing.value = alert.value
            existing.threshold_value = alert.threshold_value
            existing.message = alert.message
            existing.last_eval_time = current_time
            existing.update_count += 1
            
            # 触发更新回调
            self._trigger_callbacks(existing, 'update')
        else:
            # 新增告警
            self._active_alerts[key] = alert
            
            # 触发回调
            self._trigger_callbacks(alert, 'fire')
    
    def _maybe_resolve_alert(
        self,
        rule_id: str,
        device_id: str,
        current_time: datetime
    ) -> None:
        """可能需要恢复告警"""
        key = f"{rule_id}:{device_id}"
        alert = self._active_alerts.get(key)
        
        if alert and alert.state == AlertState.FIRING:
            alert.state = AlertState.RESOLVED
            alert.resolved_at = current_time
            
            # 触发恢复回调
            self._trigger_callbacks(alert, 'resolve')
            
            # 从活跃告警中移除
            del self._active_alerts[key]
    
    def _trigger_callbacks(self, alert: AlertEvent, event_type: str) -> None:
        """触发回调函数"""
        for callback in self._alert_callbacks:
            try:
                callback(alert, event_type)
            except Exception as e:
                logger.error(f'Error in alert callback: {e}')
        
        for callback in self._state_change_callbacks.get(alert.rule_id, []):
            try:
                callback(alert, event_type)
            except Exception as e:
                logger.error(f'Error in state change callback: {e}')
    
    def evaluate_trend(
        self,
        device_id: str,
        metric_name: str,
        values: List[float],
        rule: AlertRule,
        current_time: Optional[datetime] = None
    ) -> Optional[AlertEvent]:
        """
        评估趋势告警
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            values: 值列表
            rule: 告警规则
            current_time: 当前时间
            
        Returns:
            告警事件或None
        """
        if len(values) < 2:
            return None
        
        now = current_time or datetime.now()
        
        # 计算变化率
        first_value = values[0]
        last_value = values[-1]
        
        if first_value == 0:
            change_rate = 0.0
        else:
            change_rate = ((last_value - first_value) / first_value) * 100
        
        # 检查趋势方向
        triggered = False
        if rule.trend_direction == 'up' and change_rate > rule.change_threshold:
            triggered = True
        elif rule.trend_direction == 'down' and change_rate < -rule.change_threshold:
            triggered = True
        elif rule.trend_direction == 'any' and abs(change_rate) > rule.change_threshold:
            triggered = True
        
        if not triggered:
            self._maybe_resolve_alert(rule.id, device_id, now)
            return None
        
        # 检查去重
        fingerprint = hashlib.md5(
            f"{rule.id}:{device_id}:trend".encode()
        ).hexdigest()
        
        if self._is_duplicate(fingerprint, now):
            return None
        
        # 创建告警
        metric = MetricPoint(
            device_id=device_id,
            metric_name=metric_name,
            value=last_value,
            timestamp=now,
            unit=''
        )
        
        alert = self._create_alert(
            rule=rule,
            metric=metric,
            threshold_value=rule.change_threshold,
            fingerprint=fingerprint,
            current_time=now
        )
        alert.message += f"\n变化率: {change_rate:.2f}%"
        
        self._update_active_alert(alert, now)
        return alert
    
    def evaluate_compound(
        self,
        rule: AlertRule,
        sub_alerts: Dict[str, AlertEvent],
        current_time: Optional[datetime] = None
    ) -> Optional[AlertEvent]:
        """
        评估复合告警
        
        Args:
            rule: 复合告警规则
            sub_alerts: 子规则ID到告警的映射
            current_time: 当前时间
            
        Returns:
            告警事件或None
        """
        if not rule.sub_rules:
            return None
        
        now = current_time or datetime.now()
        
        # 统计满足条件的子规则
        triggered_count = 0
        triggered_sub_rules = []
        
        for sub_rule_id in rule.sub_rules:
            if sub_rule_id in sub_alerts:
                triggered_count += 1
                triggered_sub_rules.append(sub_rule_id)
        
        # 检查是否满足触发条件
        triggered = False
        if rule.composite_operator == 'AND':
            triggered = triggered_count == len(rule.sub_rules)
        elif rule.composite_operator == 'OR':
            triggered = triggered_count > 0
        else:  # 满足数量
            triggered = triggered_count >= rule.composite_threshold
        
        if not triggered:
            return None
        
        # 检查去重
        key_parts = [rule.id] + sorted(triggered_sub_rules)
        fingerprint = hashlib.md5(':'.join(key_parts).encode()).hexdigest()
        
        if self._is_duplicate(fingerprint, now):
            return None
        
        # 创建复合告警
        first_alert = list(sub_alerts.values())[0]
        metric = MetricPoint(
            device_id=first_alert.device_id,
            metric_name=first_alert.metric_name,
            value=first_alert.value,
            timestamp=now,
            unit=''
        )
        
        alert = self._create_alert(
            rule=rule,
            metric=metric,
            threshold_value=0,
            fingerprint=fingerprint,
            current_time=now
        )
        alert.message += f"\n满足 {triggered_count}/{len(rule.sub_rules)} 个子规则"
        
        self._update_active_alert(alert, now)
        return alert
    
    def suppress(self, rule_id: str, device_id: str) -> None:
        """手动抑制告警"""
        key = f"{rule_id}:{device_id}"
        self._suppression_cache[key] = datetime.now()
        
        # 更新活跃告警状态
        alert_key = f"{rule_id}:{device_id}"
        if alert_key in self._active_alerts:
            self._active_alerts[alert_key].state = AlertState.SUPPRESSED
    
    def unsuppress(self, rule_id: str, device_id: str) -> None:
        """取消抑制告警"""
        key = f"{rule_id}:{device_id}"
        if key in self._suppression_cache:
            del self._suppression_cache[key]
        
        # 恢复告警状态
        alert_key = f"{rule_id}:{device_id}"
        if alert_key in self._active_alerts:
            self._active_alerts[alert_key].state = AlertState.FIRING
    
    def get_active_alerts(
        self,
        rule_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        state: Optional[AlertState] = None
    ) -> List[AlertEvent]:
        """获取活跃告警"""
        alerts = list(self._active_alerts.values())
        
        if rule_id:
            alerts = [a for a in alerts if a.rule_id == rule_id]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if state:
            alerts = [a for a in alerts if a.state == state]
        
        return alerts
    
    def get_alert_history(
        self,
        rule_id: Optional[str] = None,
        device_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AlertEvent]:
        """获取告警历史（需要外部存储支持）"""
        # 这里只是一个接口定义，实际实现需要结合存储层
        return []
    
    def clear_expired_cache(self) -> int:
        """清理过期的缓存"""
        now = datetime.now()
        cleared = 0
        
        # 清理去重缓存
        expired_keys = [
            k for k, v in self._deduplication_cache.items()
            if (now - v).total_seconds() > self._deduplication_ttl
        ]
        for key in expired_keys:
            del self._deduplication_cache[key]
            cleared += 1
        
        return cleared
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_rules': len(self._rules),
            'enabled_rules': len(self.get_enabled_rules()),
            'active_alerts': len(self._active_alerts),
            'suppression_cache_size': len(self._suppression_cache),
            'deduplication_cache_size': len(self._deduplication_cache),
            'alerts_by_severity': {
                s.value: len([a for a in self._active_alerts.values() if a.severity == s])
                for s in AlertSeverity
            }
        }
    
    def export_rules(self) -> List[Dict[str, Any]]:
        """导出所有规则"""
        return [rule.to_dict() for rule in self._rules.values()]
    
    def import_rules(self, rules_data: List[Dict[str, Any]]) -> int:
        """导入规则"""
        imported = 0
        for data in rules_data:
            try:
                rule = AlertRule.from_dict(data)
                self.add_rule(rule)
                imported += 1
            except Exception as e:
                logger.error(f'Error importing rule: {e}')
        
        return imported
