# -*- coding: utf-8 -*-
"""
ITOps Platform - 核心日志管理器
基于GitHub版本架构设计，支持结构化日志、多输出、日志轮转
"""
import os
import sys
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from logging import Formatter, LogRecord
import socket
import struct
import time


class LogFormatter:
    """日志格式化器基类"""
    
    def format(self, record: LogRecord) -> str:
        raise NotImplementedError


class TextFormatter(LogFormatter):
    """文本格式化器"""
    
    def __init__(self, fmt: str = None):
        self.fmt = fmt or "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        self.datefmt = "%Y-%m-%d %H:%M:%S"
    
    def format(self, record: LogRecord) -> str:
        formatter = Formatter(self.fmt, self.datefmt)
        return formatter.format(record)


class JSONFormatter(LogFormatter):
    """JSON结构化日志格式化器"""
    
    def __init__(self, include_extra: bool = True):
        self.include_extra = include_extra
    
    def format(self, record: LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }
        
        # 添加额外字段
        if self.include_extra and hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self._format_exception(record)
        
        return json.dumps(log_data, ensure_ascii=False)
    
    def _format_exception(self, record: LogRecord) -> Dict:
        """格式化异常信息"""
        if record.exc_info:
            import traceback
            return {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info else []
            }
        return {}


class CEFFormatter(LogFormatter):
    """CEF格式化器 (Common Event Format)"""
    
    def __init__(self, device_vendor: str = "ITOps", device_product: str = "Platform"):
        self.device_vendor = device_vendor
        self.device_product = device_product
        self.device_version = "1.0"
    
    def format(self, record: LogRecord) -> str:
        severity = self._map_severity(record.levelname)
        cef_header = f"CEF:{self._get_cef_version()} {self.device_vendor} {self.device_product} {self.device_version} "
        
        extension = {
            "msg": record.getMessage(),
            "rt": datetime.fromtimestamp(record.created).strftime("%b %d %Y %H:%M:%S"),
            "src": f"{socket.gethostname()}/{record.module}",
        }
        
        extension_str = " ".join([f"{k}={v}" for k, v in extension.items()])
        return f"{cef_header}{severity} {extension_str}"
    
    def _map_severity(self, level: str) -> int:
        """映射日志级别到CEF严重性"""
        mapping = {"DEBUG": 0, "INFO": 1, "WARNING": 4, "ERROR": 7, "CRITICAL": 10}
        return mapping.get(level, 1)
    
    def _get_cef_version(self) -> str:
        return "1.0"


class LogHandler:
    """日志处理器基类"""
    
    def __init__(self):
        self._handler: logging.Handler = None
    
    def get_handler(self) -> logging.Handler:
        raise NotImplementedError


class StreamHandler(LogHandler):
    """控制台日志处理器"""
    
    def __init__(self, level: str = "INFO", formatter: LogFormatter = None):
        super().__init__()
        self.level = level
        self.formatter = formatter or TextFormatter()
    
    def get_handler(self) -> logging.Handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, self.level))
        handler.setFormatter(self.formatter)
        return handler


class RotatingFileHandler(LogHandler):
    """轮转文件日志处理器 (按大小)"""
    
    def __init__(
        self,
        filename: str = "logs/itops.log",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        level: str = "DEBUG",
        formatter: LogFormatter = None
    ):
        super().__init__()
        self.filename = filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.level = level
        self.formatter = formatter or TextFormatter()
    
    def get_handler(self) -> logging.Handler:
        # 确保目录存在
        Path(self.filename).parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            self.filename,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        handler.setLevel(getattr(logging, self.level))
        handler.setFormatter(self.formatter)
        return handler


class TimedRotatingFileHandler(LogHandler):
    """轮转文件日志处理器 (按时间)"""
    
    def __init__(
        self,
        filename: str = "logs/itops.log",
        when: str = "midnight",
        interval: int = 1,
        backup_count: int = 7,
        level: str = "DEBUG",
        formatter: LogFormatter = None
    ):
        super().__init__()
        self.filename = filename
        self.when = when
        self.interval = interval
        self.backup_count = backup_count
        self.level = level
        self.formatter = formatter or TextFormatter()
    
    def get_handler(self) -> logging.Handler:
        Path(self.filename).parent.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            self.filename,
            when=self.when,
            interval=self.interval,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        handler.setLevel(getattr(logging, self.level))
        handler.setFormatter(self.formatter)
        return handler


class SysLogHandler(LogHandler):
    """Syslog日志处理器"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 514,
        level: str = "INFO",
        formatter: LogFormatter = None
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.level = level
        self.formatter = formatter or TextFormatter()
    
    def get_handler(self) -> logging.Handler:
        handler = logging.handlers.SysLogHandler(address=(self.host, self.port))
        handler.setLevel(getattr(logging, self.level))
        handler.setFormatter(self.formatter)
        return handler


class BufferedHandler(LogHandler):
    """缓冲日志处理器"""
    
    def __init__(
        self,
        buffer_size: int = 100,
        flush_level: str = "ERROR",
        flush_interval: int = 60
    ):
        super().__init__()
        self.buffer_size = buffer_size
        self.flush_level = getattr(logging, flush_level)
        self.flush_interval = flush_interval
        self._buffer: List[Dict] = []
        self._last_flush = datetime.now()
        self._lock = threading.Lock()
    
    def get_handler(self) -> logging.Handler:
        return _BufferedLoggingHandler(self)


class _BufferedLoggingHandler(logging.Handler):
    """内部缓冲处理实现"""
    
    def __init__(self, buffered_handler: 'BufferedHandler'):
        super().__init__()
        self._buffered_handler = buffered_handler
    
    def emit(self, record: LogRecord):
        self._buffered_handler._emit(record)


class ContextFilter(logging.Filter):
    """日志上下文过滤器"""
    
    def __init__(self):
        super().__init__()
        self._context: Dict[str, Any] = {}
        self._local = threading.local()
    
    def add_context(self, **kwargs):
        """添加上下文信息"""
        self._context.update(kwargs)
        if not hasattr(self._local, 'extra_fields'):
            self._local.extra_fields = {}
        self._local.extra_fields.update(kwargs)
    
    def clear_context(self):
        """清除上下文"""
        self._context.clear()
        if hasattr(self._local, 'extra_fields'):
            self._local.extra_fields = {}
    
    def filter(self, record: LogRecord) -> bool:
        # 合并全局上下文和线程本地上下文
        extra_fields = {}
        extra_fields.update(self._context)
        if hasattr(self._local, 'extra_fields'):
            extra_fields.update(self._local.extra_fields)
        
        if extra_fields:
            record.extra_fields = extra_fields
        return True


class LoggerManager:
    """
    日志管理器 - 单例模式
    支持多输出、结构化日志、日志上下文
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: List[logging.Handler] = []
        self._context_filter = ContextFilter()
        self._default_level = "INFO"
        self._default_formatter = JSONFormatter()
        self._log_dir = "logs"
        self._log_file = "itops.log"
    
    def configure(
        self,
        level: str = "INFO",
        log_dir: str = "logs",
        log_file: str = "itops.log",
        console: bool = True,
        file_size_rotation: bool = True,
        file_time_rotation: bool = False,
        syslog: bool = False,
        syslog_host: str = "localhost",
        syslog_port: int = 514,
        json_format: bool = False,
        max_file_size: int = 10 * 1024 * 1024,
        backup_count: int = 5
    ):
        """配置日志管理器"""
        self._default_level = level
        self._log_dir = log_dir
        self._log_file = log_file
        
        # 选择格式化器
        if json_format:
            formatter = JSONFormatter()
        else:
            formatter = TextFormatter()
        
        # 添加控制台处理器
        if console:
            console_handler = StreamHandler(level, formatter)
            self.add_handler(console_handler.get_handler())
        
        # 添加文件处理器
        if file_size_rotation or file_time_rotation:
            if file_size_rotation:
                file_handler = RotatingFileHandler(
                    filename=f"{log_dir}/{log_file}",
                    max_bytes=max_file_size,
                    backup_count=backup_count,
                    level=level,
                    formatter=formatter
                )
            else:
                file_handler = TimedRotatingFileHandler(
                    filename=f"{log_dir}/{log_file}",
                    when="midnight",
                    interval=1,
                    backup_count=7,
                    level=level,
                    formatter=formatter
                )
            self.add_handler(file_handler)
        
        # 添加Syslog处理器
        if syslog:
            try:
                syslog_handler = SysLogHandler(syslog_host, syslog_port, level, formatter)
                self.add_handler(syslog_handler.get_handler())
            except Exception as e:
                print(f"无法连接Syslog服务器: {e}")
        
        # 添加上下文过滤器
        for handler in self._handlers:
            handler.addFilter(self._context_filter)
    
    def add_handler(self, handler: logging.Handler):
        """添加处理器"""
        self._handlers.append(handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        if name in self._loggers:
            return self._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self._default_level))
        logger.propagate = False
        
        # 添加所有配置的处理器
        for handler in self._handlers:
            # 避免重复添加
            if handler not in logger.handlers:
                logger.addHandler(handler)
        
        self._loggers[name] = logger
        return logger
    
    def add_context(self, **kwargs):
        """添加日志上下文"""
        self._context_filter.add_context(**kwargs)
    
    def clear_context(self):
        """清除日志上下文"""
        self._context_filter.clear_context()
    
    def set_level(self, level: str, logger_name: str = None):
        """设置日志级别"""
        log_level = getattr(logging, level.upper())
        if logger_name:
            logger = self.get_logger(logger_name)
            logger.setLevel(log_level)
        else:
            self._default_level = level
            for logger in self._loggers.values():
                logger.setLevel(log_level)
    
    def shutdown(self):
        """关闭日志管理器"""
        logging.shutdown()
        self._loggers.clear()


class StructuredLogger:
    """结构化日志包装器"""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._context: Dict[str, Any] = {}
    
    def add_context(self, **kwargs):
        """添加上下文"""
        self._context.update(kwargs)
    
    def _log(self, level: str, message: str, **kwargs):
        """带上下文的日志记录"""
        extra_fields = self._context.copy()
        extra_fields.update(kwargs)
        
        logger_method = getattr(self._logger, level.lower())
        
        # 创建带有extra_fields的record
        extra = {"extra_fields": extra_fields}
        logger_method(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("CRITICAL", message, **kwargs)


def get_logger(name: str = __name__) -> logging.Logger:
    """获取日志记录器快捷函数"""
    return LoggerManager().get_logger(name)


def get_structured_logger(name: str = __name__) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(get_logger(name))
