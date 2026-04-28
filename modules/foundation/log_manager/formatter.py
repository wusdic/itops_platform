"""
日志格式化器
支持Text、JSON等多种格式化方式
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional


class LogFormatter:
    """日志格式化器基类"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        raise NotImplementedError


class TextFormatter(logging.Formatter):
    """文本日志格式化器"""
    
    DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: str = '%Y-%m-%d %H:%M:%S'
    ):
        super().__init__(fmt or self.DEFAULT_FORMAT, datefmt)


class DetailedTextFormatter(TextFormatter):
    """详细文本日志格式化器"""
    
    def __init__(self, datefmt: str = '%Y-%m-%d %H:%M:%S'):
        super().__init__(self.DETAILED_FORMAT, datefmt)


class JSONFormatter(LogFormatter):
    """JSON日志格式化器"""
    
    def __init__(
        self,
        extra_fields: Optional[Dict[str, str]] = None,
        timestamp_field: str = 'timestamp',
        level_field: str = 'level',
        message_field: str = 'message',
        name_field: str = 'logger',
        include_extra: bool = True
    ):
        self._extra_fields = extra_fields or {}
        self._timestamp_field = timestamp_field
        self._level_field = level_field
        self._message_field = message_field
        self._name_field = name_field
        self._include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON"""
        data = {
            self._timestamp_field: datetime.fromtimestamp(record.created).isoformat(),
            self._level_field: record.levelname,
            self._message_field: record.getMessage(),
            self._name_field: record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process_id': record.process,
            'thread_id': record.thread,
        }
        
        # 添加extra字段
        if hasattr(record, 'extra_fields') and self._include_extra:
            data.update(record.extra_fields)
        
        # 添加任何额外的record属性
        for key, value in self._extra_fields.items():
            if hasattr(record, key):
                data[value] = getattr(record, key)
        
        return json.dumps(data, ensure_ascii=False, default=str)


class LogstashFormatter(JSONFormatter):
    """Logstash格式日志格式化器"""
    
    def __init__(self, app_name: str = 'itops'):
        super().__init__(
            extra_fields={'host': 'host'},
            timestamp_field='@timestamp'
        )
        self._app_name = app_name
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志为Logstash格式"""
        data = {
            '@timestamp': datetime.fromtimestamp(record.created).isoformat(),
            '@version': '1',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'host': getattr(record, 'host', 'unknown'),
            'app': self._app_name,
            'tags': ['itops', 'platform']
        }
        
        return json.dumps(data, ensure_ascii=False, default=str)


class CEFFormatter(LogFormatter):
    """
    CEF (Common Event Format) 日志格式化器
    用于与SIEM系统（如ArcSight）集成
    """
    
    def __init__(
        self,
        app_name: str = 'ITOps',
        app_vendor: str = 'ITOpsPlatform',
        app_version: str = '1.0.0'
    ):
        self._app_name = app_name
        self._app_vendor = app_vendor
        self._app_version = app_version
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志为CEF格式"""
        # CEF格式: CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        
        severity_map = {
            'DEBUG': 0,
            'INFO': 5,
            'WARNING': 7,
            'ERROR': 8,
            'CRITICAL': 10
        }
        
        severity = severity_map.get(record.levelname, 5)
        
        # 基本头信息
        header = f"CEF:0|{self._app_vendor}|{self._app_name}|{self._app_version}|{record.levelno}|{record.name}|{severity}"
        
        # 扩展字段
        extension = [
            f"rt={datetime.fromtimestamp(record.created).isoformat()}",
            f"msg={record.getMessage()}",
            f"suser={getattr(record, 'user', 'unknown')}",
            f"src={getattr(record, 'src_ip', 'unknown')}",
            f"dst={getattr(record, 'dst_ip', 'unknown')}"
        ]
        
        return header + '|' + ' '.join(extension)


class CustomFormatter(logging.Formatter):
    """自定义日志格式化器"""
    
    def __init__(
        self,
        fmt: str = '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt: str = '%Y-%m-%d %H:%M:%S',
        color: bool = True
    ):
        super().__init__(fmt, datefmt)
        self._color = color
        
        if color:
            self.COLORS = {
                'DEBUG': '\033[36m',
                'INFO': '\033[32m',
                'WARNING': '\033[33m',
                'ERROR': '\033[31m',
                'CRITICAL': '\033[35m\033[1m',
            }
            self.RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        if self._color and record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        return super().format(record)