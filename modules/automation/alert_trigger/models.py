"""
告警触发自动化 - 数据模型
定义告警触发规则的数据结构
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


class ActionType(str, Enum):
    """动作类型枚举"""
    SCRIPT = "script"           # 执行脚本
    WORKORDER = "workorder"     # 创建工单
    NOTIFICATION = "notification"  # 发送通知


class AlertLevel(str, Enum):
    """告警级别枚举"""
    CRITICAL = "critical"   # 紧急 - P1
    HIGH = "high"          # 严重 - P2
    MEDIUM = "medium"      # 中等 - P3
    LOW = "low"            # 低 - P4
    INFO = "info"          # 信息


@dataclass
class ActionConfig:
    """动作配置"""
    action_type: ActionType
    enabled: bool = True
    # 脚本配置
    script_name: Optional[str] = None
    script_content: Optional[str] = None
    script_params: Dict[str, Any] = field(default_factory=dict)
    # 工单配置
    workorder_title_template: Optional[str] = None
    workorder_description_template: Optional[str] = None
    workorder_type: str = "fault"
    workorder_priority: str = "P2"
    # 通知配置
    notification_channels: List[str] = field(default_factory=list)
    notification_receivers: List[str] = field(default_factory=list)
    notification_template: Optional[str] = None


@dataclass
class ConditionConfig:
    """触发条件配置"""
    condition_type: str = "threshold"  # threshold, change, rate, constant, expression
    metric_name: str = ""
    operator: str = ">"  # >, <, >=, <=, ==, !=
    threshold_value: float = 0
    duration_seconds: int = 0  # 持续时间
    change_percent: float = 0  # 变化百分比
    rate_percent: float = 0   # 速率百分比
    expression: str = ""      # 自定义表达式


@dataclass
class AlertTriggerRule:
    """
    告警触发规则
    
    定义当满足特定条件时自动执行相应动作
    """
    id: str
    name: str
    description: str = ""
    enabled: bool = True
    
    # 触发条件
    condition: ConditionConfig = field(default_factory=ConditionConfig)
    
    # 告警级别
    alert_level: str = "medium"
    
    # 设备过滤
    device_ids: List[int] = field(default_factory=list)  # 空列表表示所有设备
    device_tags: List[str] = field(default_factory=list)
    
    # 触发间隔(秒)，避免重复触发
    trigger_interval: int = 300
    
    # 抑制配置
    suppress_enabled: bool = False
    suppress_duration: int = 300
    suppress_key: str = ""
    
    # 时间窗口
    time_windows: List[Dict[str, Any]] = field(default_factory=list)
    
    # 动作列表
    actions: List[ActionConfig] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    updated_by: str = ""
    
    # 统计
    trigger_count: int = 0
    last_triggered_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "condition": {
                "condition_type": self.condition.condition_type,
                "metric_name": self.condition.metric_name,
                "operator": self.condition.operator,
                "threshold_value": self.condition.threshold_value,
                "duration_seconds": self.condition.duration_seconds,
                "change_percent": self.condition.change_percent,
                "rate_percent": self.condition.rate_percent,
                "expression": self.condition.expression,
            },
            "alert_level": self.alert_level,
            "device_ids": self.device_ids,
            "device_tags": self.device_tags,
            "trigger_interval": self.trigger_interval,
            "suppress_enabled": self.suppress_enabled,
            "suppress_duration": self.suppress_duration,
            "suppress_key": self.suppress_key,
            "time_windows": self.time_windows,
            "actions": [
                {
                    "action_type": a.action_type.value if isinstance(a.action_type, ActionType) else a.action_type,
                    "enabled": a.enabled,
                    "script_name": a.script_name,
                    "script_params": a.script_params,
                    "workorder_title_template": a.workorder_title_template,
                    "workorder_description_template": a.workorder_description_template,
                    "workorder_type": a.workorder_type,
                    "workorder_priority": a.workorder_priority,
                    "notification_channels": a.notification_channels,
                    "notification_receivers": a.notification_receivers,
                    "notification_template": a.notification_template,
                }
                for a in self.actions
            ],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "trigger_count": self.trigger_count,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertTriggerRule":
        """从字典创建"""
        condition_data = data.get("condition", {})
        condition = ConditionConfig(
            condition_type=condition_data.get("condition_type", "threshold"),
            metric_name=condition_data.get("metric_name", ""),
            operator=condition_data.get("operator", ">"),
            threshold_value=condition_data.get("threshold_value", 0),
            duration_seconds=condition_data.get("duration_seconds", 0),
            change_percent=condition_data.get("change_percent", 0),
            rate_percent=condition_data.get("rate_percent", 0),
            expression=condition_data.get("expression", ""),
        )
        
        actions = []
        for a in data.get("actions", []):
            action_type = a.get("action_type", "script")
            if isinstance(action_type, str):
                action_type = ActionType(action_type)
            actions.append(ActionConfig(
                action_type=action_type,
                enabled=a.get("enabled", True),
                script_name=a.get("script_name"),
                script_content=a.get("script_content"),
                script_params=a.get("script_params", {}),
                workorder_title_template=a.get("workorder_title_template"),
                workorder_description_template=a.get("workorder_description_template"),
                workorder_type=a.get("workorder_type", "fault"),
                workorder_priority=a.get("workorder_priority", "P2"),
                notification_channels=a.get("notification_channels", []),
                notification_receivers=a.get("notification_receivers", []),
                notification_template=a.get("notification_template"),
            ))
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            condition=condition,
            alert_level=data.get("alert_level", "medium"),
            device_ids=data.get("device_ids", []),
            device_tags=data.get("device_tags", []),
            trigger_interval=data.get("trigger_interval", 300),
            suppress_enabled=data.get("suppress_enabled", False),
            suppress_duration=data.get("suppress_duration", 300),
            suppress_key=data.get("suppress_key", ""),
            time_windows=data.get("time_windows", []),
            actions=actions,
            created_by=data.get("created_by", ""),
            updated_by=data.get("updated_by", ""),
            trigger_count=data.get("trigger_count", 0),
        )


@dataclass
class TriggerEvent:
    """触发事件记录"""
    id: str
    rule_id: str
    rule_name: str
    trigger_time: datetime
    metric_name: str
    metric_value: float
    threshold_value: float
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    device_ip: Optional[str] = None
    actions_executed: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, success, failed, partial
    error_message: str = ""
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_ip": self.device_ip,
            "actions_executed": self.actions_executed,
            "status": self.status,
            "error_message": self.error_message,
            "execution_results": self.execution_results,
        }