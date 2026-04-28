"""
日志管理模块 (FM-02)
ITOps Intelligence Platform - Foundation Layer

功能：
- 结构化日志记录
- 多级别日志输出
- 多输出目标支持
- 日志聚合和查询

依赖：FM-01 配置管理模块

作者：ITOps Platform Team
版本：1.0.0
"""

from .logger import LoggerManager, get_logger
from .handlers import LogHandler, FileHandler, RotatingHandler, SyslogHandler
from .formatter import LogFormatter, JSONFormatter, TextFormatter

__all__ = [
    'LoggerManager',
    'get_logger',
    'LogHandler',
    'FileHandler',
    'RotatingHandler',
    'SyslogHandler',
    'LogFormatter',
    'JSONFormatter',
    'TextFormatter'
]

__version__ = '1.0.0'