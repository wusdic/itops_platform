"""
日志处理器
支持文件、控制台、Syslog等多种输出方式
"""

import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional, Union


class LogHandler:
    """日志处理器基类"""
    
    def __init__(self, level: str = 'INFO'):
        self._level = getattr(logging, level.upper(), logging.INFO)
    
    def get_handler(self) -> logging.Handler:
        """获取Handler实例"""
        raise NotImplementedError


class FileHandler(LogHandler):
    """文件日志处理器"""
    
    def __init__(
        self,
        file_path: Union[str, Path],
        level: str = 'INFO',
        encoding: str = 'utf-8'
    ):
        super().__init__(level)
        self._file_path = Path(file_path)
        self._encoding = encoding
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_handler(self) -> logging.Handler:
        """获取文件Handler"""
        handler = logging.FileHandler(
            self._file_path,
            encoding=self._encoding
        )
        handler.setLevel(self._level)
        return handler


class RotatingHandler(LogHandler):
    """轮转日志处理器（按大小）"""
    
    def __init__(
        self,
        file_path: Union[str, Path],
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 10,
        level: str = 'INFO',
        encoding: str = 'utf-8'
    ):
        super().__init__(level)
        self._file_path = Path(file_path)
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._encoding = encoding
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_handler(self) -> RotatingFileHandler:
        """获取轮转文件Handler"""
        handler = RotatingFileHandler(
            self._file_path,
            maxBytes=self._max_bytes,
            backupCount=self._backup_count,
            encoding=self._encoding
        )
        handler.setLevel(self._level)
        return handler


class TimeRotatingHandler(LogHandler):
    """时间轮转日志处理器"""
    
    def __init__(
        self,
        file_path: Union[str, Path],
        when: str = 'midnight',
        interval: int = 1,
        backup_count: int = 30,
        level: str = 'INFO',
        encoding: str = 'utf-8'
    ):
        super().__init__(level)
        self._file_path = Path(file_path)
        self._when = when
        self._interval = interval
        self._backup_count = backup_count
        self._encoding = encoding
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_handler(self) -> TimedRotatingFileHandler:
        """获取时间轮转Handler"""
        handler = TimedRotatingFileHandler(
            self._file_path,
            when=self._when,
            interval=self._interval,
            backupCount=self._backup_count,
            encoding=self._encoding
        )
        handler.setLevel(self._level)
        return handler


class SyslogHandler(LogHandler):
    """Syslog日志处理器"""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 514,
        facility: int = logging.handlers.SysLogHandler.LOG_USER,
        level: str = 'INFO'
    ):
        super().__init__(level)
        self._host = host
        self._port = port
        self._facility = facility
    
    def get_handler(self) -> logging.handlers.SysLogHandler:
        """获取Syslog Handler"""
        try:
            from logging.handlers.SysLogHandler import SysLogHandler
            handler = SysLogHandler(
                address=(self._host, self._port),
                facility=self._facility
            )
            handler.setLevel(self._level)
            return handler
        except Exception as e:
            # 如果Syslog不可用，返回空Handler
            return logging.NullHandler()


class ConsoleHandler(LogHandler):
    """控制台日志处理器"""
    
    def __init__(
        self,
        level: str = 'INFO',
        color: bool = True
    ):
        super().__init__(level)
        self._color = color
    
    def get_handler(self) -> logging.StreamHandler:
        """获取控制台Handler"""
        import sys
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self._level)
        
        if self._color:
            handler.setFormatter(ColorFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        return handler


class ColorFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class BufferedHandler(LogHandler):
    """缓冲日志处理器（用于批量处理）"""
    
    def __init__(
        self,
        buffer_size: int = 100,
        flush_level: str = 'ERROR',
        level: str = 'DEBUG'
    ):
        super().__init__(level)
        self._buffer_size = buffer_size
        self._flush_level = getattr(logging, flush_level.upper(), logging.ERROR)
        self._buffer: list = []
    
    def get_handler(self) -> 'BufferedLogHandler':
        """获取缓冲Handler"""
        handler = BufferedLogHandler(
            buffer_size=self._buffer_size,
            flush_level=self._flush_level
        )
        handler.setLevel(self._level)
        return handler


class BufferedLogHandler(logging.Handler):
    """缓冲日志处理器实现"""
    
    def __init__(self, buffer_size: int = 100, flush_level: int = logging.ERROR):
        super().__init__()
        self._buffer_size = buffer_size
        self._flush_level = flush_level
        self._buffer = []
        self._callbacks: list = []
    
    def emit(self, record: logging.LogRecord):
        """记录日志"""
        self._buffer.append(record)
        
        if record.levelno >= self._flush_level or len(self._buffer) >= self._buffer_size:
            self.flush()
    
    def flush(self):
        """刷新缓冲区"""
        if not self._buffer:
            return
        
        for callback in self._callbacks:
            try:
                callback(self._buffer)
            except Exception:
                pass
        
        self._buffer = []
    
    def add_callback(self, callback):
        """添加缓冲区满时的回调"""
        self._callbacks.append(callback)
    
    def close(self):
        """关闭处理器"""
        self.flush()
        super().close()