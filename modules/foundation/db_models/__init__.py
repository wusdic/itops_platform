"""
数据库模型模块 (FM-03)
ITOps Intelligence Platform - Foundation Layer

功能：
- SQLAlchemy ORM模型定义
- 数据迁移支持
- 统一的数据库操作接口

依赖：FM-01 配置管理模块, FM-02 日志管理模块

作者：ITOps Platform Team
版本：1.0.0
"""

from .base import Base, db_session, init_db, close_db, get_engine
from .device import Device, DeviceType, DeviceStatus
from .alert import Alert, AlertLevel, AlertStatus, AlertCategory, AlertRule
from .monitoring import PerformanceMetric
from .system import OperationLog, BackupRecord
from .workorder import WorkOrder, WorkOrderType, WorkOrderStatus
from .report_template import ReportTemplate, ReportTemplateType, ReportFormat, Report, ReportSchedule
from .ai import AIConversation
from .notification.notification_model import (
    NotificationChannelModel, NotificationLog, NotificationTargetRule
)

__all__ = [
    'Base',
    'db_session',
    'init_db',
    'close_db',
    'get_engine',
    'Device',
    'DeviceType',
    'DeviceStatus',
    'Alert',
    'AlertLevel',
    'AlertStatus',
    'AlertCategory',
    'AlertRule',
    'PerformanceMetric',
    'OperationLog',
    'BackupRecord',
    'WorkOrder',
    'WorkOrderType',
    'WorkOrderStatus',
    'ReportTemplate',
    'ReportTemplateType',
    'ReportFormat',
    'Report',
    'ReportSchedule',
    'AIConversation',
    'NotificationChannelModel',
    'NotificationLog',
    'NotificationTargetRule',
]

__version__ = '1.0.0'