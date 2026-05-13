"""
告警触发自动化模块

提供告警触发规则的定义、评估和自动执行功能
支持脚本执行、工单创建、通知发送等动作类型
"""

from .models import (
    AlertTriggerRule,
    TriggerEvent,
    ActionConfig,
    ConditionConfig,
    ActionType,
    AlertLevel,
)
from .trigger import (
    AlertTriggerEngine,
    get_trigger_engine,
    set_trigger_engine,
)

__all__ = [
    "AlertTriggerRule",
    "TriggerEvent",
    "ActionConfig",
    "ConditionConfig",
    "ActionType",
    "AlertLevel",
    "AlertTriggerEngine",
    "get_trigger_engine",
    "set_trigger_engine",
]