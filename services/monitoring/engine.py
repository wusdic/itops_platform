# -*- coding: utf-8 -*-
"""
ITOps Platform - Alert Engine
告警引擎
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


class AlertLevel(Enum):
    """告警级别"""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric: str
    condition: str  # >, <, >=, <=, ==, !=
    threshold: float
    level: AlertLevel = AlertLevel.WARNING
    duration: int = 0  # 持续时间（秒）
    enabled: bool = True
    description: str = ""
    
    def evaluate(self, value: float) -> bool:
        """评估告警条件"""
        if not self.enabled:
            return False
        
        try:
            if self.condition == ">":
                return value > self.threshold
            elif self.condition == "<":
                return value < self.threshold
            elif self.condition == ">=":
                return value >= self.threshold
            elif self.condition == "<=":
                return value <= self.threshold
            elif self.condition == "==":
                return value == self.threshold
            elif self.condition == "!=":
                return value != self.threshold
        except Exception:
            pass
        
        return False


@dataclass
class Alert:
    """告警"""
    id: Optional[int] = None
    rule_name: str = ""
    level: AlertLevel = AlertLevel.INFO
    metric: str = ""
    value: float = 0
    threshold: float = 0
    message: str = ""
    host: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class AlertEngine:
    """告警引擎"""
    
    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_callbacks: List[Callable] = []
        self._alert_history: List[Alert] = []
        self._max_history: int = 1000
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self._rules[rule.name] = rule
    
    def remove_rule(self, name: str):
        """移除告警规则"""
        self._rules.pop(name, None)
    
    def get_rules(self) -> List[AlertRule]:
        """获取所有规则"""
        return list(self._rules.values())
    
    def add_callback(self, callback: Callable):
        """添加告警回调"""
        self._alert_callbacks.append(callback)
    
    def evaluate(self, metric: str, value: float, host: str = "", tags: Dict = None) -> List[Alert]:
        """评估指标并生成告警"""
        alerts = []
        tags = tags or {}
        
        for rule in self._rules.values():
            if rule.metric != metric:
                continue
            
            if rule.evaluate(value):
                alert_key = f"{host}:{metric}:{rule.name}"
                
                alert = Alert(
                    rule_name=rule.name,
                    level=rule.level,
                    metric=metric,
                    value=value,
                    threshold=rule.threshold,
                    message=f"{rule.description or rule.name}: {value} {rule.condition} {rule.threshold}",
                    host=host,
                    tags=tags,
                )
                
                # 检查是否是新告警
                if alert_key not in self._active_alerts:
                    self._active_alerts[alert_key] = alert
                    alerts.append(alert)
                    
                    # 触发回调
                    for callback in self._alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            print(f"告警回调执行失败: {e}")
        
        return alerts
    
    def acknowledge(self, alert_id: int):
        """确认告警"""
        for alert in self._active_alerts.values():
            if alert.id == alert_id:
                alert.status = "acknowledged"
                alert.acknowledged_at = datetime.now()
                break
    
    def resolve(self, host: str, metric: str, rule_name: str = None):
        """解决告警"""
        if rule_name:
            alert_key = f"{host}:{metric}:{rule_name}"
            if alert_key in self._active_alerts:
                alert = self._active_alerts.pop(alert_key)
                alert.status = "resolved"
                alert.resolved_at = datetime.now()
                self._add_to_history(alert)
        else:
            # 解决所有匹配条件的所有告警
            keys_to_remove = [
                key for key, alert in self._active_alerts.items()
                if alert.host == host and alert.metric == metric
            ]
            for key in keys_to_remove:
                alert = self._active_alerts.pop(key)
                alert.status = "resolved"
                alert.resolved_at = datetime.now()
                self._add_to_history(alert)
    
    def _add_to_history(self, alert: Alert):
        """添加告警到历史"""
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]
    
    def get_active_alerts(self, level: AlertLevel = None) -> List[Alert]:
        """获取活跃告警"""
        alerts = list(self._active_alerts.values())
        if level:
            alerts = [a for a in alerts if a.level == level]
        return sorted(alerts, key=lambda x: x.level.value, reverse=True)
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self._alert_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        active = list(self._active_alerts.values())
        
        stats = {
            "total_active": len(active),
            "by_level": {
                "info": len([a for a in active if a.level == AlertLevel.INFO]),
                "warning": len([a for a in active if a.level == AlertLevel.WARNING]),
                "error": len([a for a in active if a.level == AlertLevel.ERROR]),
                "critical": len([a for a in active if a.level == AlertLevel.CRITICAL]),
            },
            "total_history": len(self._alert_history),
            "total_rules": len(self._rules),
        }
        
        return stats
