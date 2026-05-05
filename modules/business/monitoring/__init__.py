"""
BM-01 监控告警模块
提供指标采集、告警规则、告警触发、通知服务、仪表盘数据等功能
"""

from .monitor import MonitorCore
from .rules import AlertRulesEngine
from .alerter import AlertTrigger
from .notification import NotificationService
from .dashboard import DashboardData

__all__ = [
    'MonitorCore',
    'AlertRulesEngine',
    'AlertTrigger',
    'NotificationService',
    'DashboardData',
]
__version__ = '1.0.0'
