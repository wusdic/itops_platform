"""
AM-02 告警自愈模块
提供故障检测、自动恢复、剧本管理等功能
"""

from .detector import FaultDetector, FaultPattern, RootCauseAnalysis
from .healer import SelfHealer, RecoveryStrategy, RecoveryResult
from .playbook import Playbook, PlaybookManager, PlaybookExecution

__all__ = [
    'FaultDetector', 'FaultPattern', 'RootCauseAnalysis',
    'SelfHealer', 'RecoveryStrategy', 'RecoveryResult',
    'Playbook', 'PlaybookManager', 'PlaybookExecution',
]
__version__ = '1.0.0'
