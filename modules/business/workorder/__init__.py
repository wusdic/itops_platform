"""
BM-02 工单管理模块
提供工单管理、流程引擎、审批处理、统计分析、变更管理等功能
"""

from .workorder import WorkOrderCore
from .flow import FlowEngine
from .approval import ApprovalHandler
from .stats import WorkOrderStats
from .change import ChangeManager

__all__ = [
    'WorkOrderCore',
    'FlowEngine',
    'ApprovalHandler',
    'WorkOrderStats',
    'ChangeManager',
]
__version__ = '1.0.0'
