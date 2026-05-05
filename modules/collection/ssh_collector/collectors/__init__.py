"""
采集器初始化
"""

from .linux_collector import LinuxCollector
from .windows_collector import WindowsCollector
from .kylin_collector import KylinCollector


__all__ = [
    'LinuxCollector',
    'WindowsCollector',
    'KylinCollector'
]
