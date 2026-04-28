"""
日志管理器
统一日志管理，支持多输出、格式化、日志级别控制
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json

from .formatter import JSONFormatter, TextFormatter, LogFormatter


class LoggerManager:
    """
    统一日志管理器
    
    功能特性：
    1. 支持控制台、文件、Syslog等多种输出
    2. 支持日志轮转（按大小、按时间）
    3. 支持JSON格式日志
    4. 支持结构化日志
    5. 支持日志上下文（request_id, user_id等）
    
    使用示例：
    >>> logger_manager = LoggerManager()
    >>> logger_manager.setup(
    ...     level='INFO',
    ...     format='json',
    ...     file_path='/var/log/itops/app.log'
    ... )
    >>> logger = logger_manager.get_logger('monitoring')
    >>> logger.info('Starting monitoring', extra={'host': 'server1'})
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._loggers: Dict[str, logging.Logger] = {}
        self._root_logger: Optional[logging.Logger] = None
        self._handlers: List[logging.Handler] = []
        self._context: Dict[str, Any] = {}
        self._default_level = logging.INFO
        self._default_format = 'text'
    
    def setup(
        self,
        level: str = 'INFO',
        format_type: str = 'text',
        file_path: Optional[str] = None,
        file_rotation: str = 'size',  # size, time
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 10,
        when: str = 'midnight',  # for time rotation
        interval: int = 1,
        console: bool = True,
        syslog_host: Optional[str] = None,
        syslog_port: int = 514,
        json_fields: Optional[Dict[str, str]] = None
    ) -> 'LoggerManager':
        """
        设置日志管理器
        
        Args:
            level: 日志级别 DEBUG, INFO, WARNING, ERROR, CRITICAL
            format_type: 格式化类型 text, json
            file_path: 日志文件路径
            file_rotation: 轮转方式 size, time
            max_bytes: 最大文件大小（字节）
            backup_count: 保留的备份数量
            when: 时间轮转单位 midnight, H, D, W0-W6
            interval: 时间轮转间隔
            console: 是否输出到控制台
            syslog_host: Syslog服务器地址
            syslog_port: Syslog服务器端口
            json_fields: JSON格式额外字段映射
        """
        # 设置根日志级别
        self._default_level = getattr(logging, level.upper(), logging.INFO)
        self._default_format = format_type
        
        # 创建根logger
        self._root_logger = logging.getLogger('itops')
        self._root_logger.setLevel(self._default_level)
        self._root_logger.handlers.clear()
        
        # 创建格式化器
        if format_type == 'json':
            formatter = JSONFormatter(json_fields or {})
        else:
            formatter = TextFormatter()
        
        # 添加控制台处理器
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(self._default_level)
            self._root_logger.addHandler(console_handler)
            self._handlers.append(console_handler)
        
        # 添加文件处理器
        if file_path:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if file_rotation == 'size':
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
            else:
                file_handler = TimedRotatingFileHandler(
                    file_path,
                    when=when,
                    interval=interval,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
            
            file_handler.setFormatter(formatter)
            file_handler.setLevel(self._default_level)
            self._root_logger.addHandler(file_handler)
            self._handlers.append(file_handler)
        
        # 添加Syslog处理器
        if syslog_host:
            try:
                from logging.handlers.SysLogHandler import SysLogHandler
                syslog_handler = SysLogHandler(
                    address=(syslog_host, syslog_port)
                )
                syslog_handler.setFormatter(formatter)
                syslog_handler.setLevel(self._default_level)
                self._root_logger.addHandler(syslog_handler)
                self._handlers.append(syslog_handler)
            except Exception as e:
                print(f"Failed to setup syslog handler: {e}")
        
        return self
    
    def setup_from_config(self, config: Dict[str, Any]) -> 'LoggerManager':
        """
        从配置设置日志管理器
        
        Args:
            config: 配置字典
        """
        log_config = config.get('logging', {})
        
        return self.setup(
            level=log_config.get('level', 'INFO'),
            format_type=log_config.get('format', 'text'),
            file_path=log_config.get('file_path'),
            file_rotation=log_config.get('rotation', 'size'),
            max_bytes=log_config.get('max_bytes', 10 * 1024 * 1024),
            backup_count=log_config.get('backup_count', 10),
            console=log_config.get('console', True),
            syslog_host=log_config.get('syslog_host'),
            syslog_port=log_config.get('syslog_port', 514)
        )
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取命名logger
        
        Args:
            name: logger名称
        
        Returns:
            Logger实例
        """
        if name in self._loggers:
            return self._loggers[name]
        
        # 创建子logger，继承根logger的handlers
        logger = logging.getLogger(f'itops.{name}')
        logger.setLevel(self._default_level)
        
        self._loggers[name] = logger
        return logger
    
    def set_context(self, **kwargs):
        """
        设置日志上下文
        
        Args:
            **kwargs: 上下文键值对
        """
        self._context.update(kwargs)
    
    def clear_context(self):
        """清除日志上下文"""
        self._context = {}
    
    def add_context_filter(self, logger: logging.Logger) -> 'ContextFilter':
        """
        为logger添加上下文过滤器
        
        Args:
            logger: Logger实例
        
        Returns:
            ContextFilter实例
        """
        context_filter = ContextFilter(self._context)
        logger.addFilter(context_filter)
        return context_filter
    
    def set_level(self, level: str, logger_name: Optional[str] = None):
        """
        设置日志级别
        
        Args:
            level: 日志级别
            logger_name: logger名称，None表示设置根logger
        """
        level_value = getattr(logging, level.upper(), logging.INFO)
        
        if logger_name:
            logger = self.get_logger(logger_name)
            logger.setLevel(level_value)
        else:
            self._default_level = level_value
            if self._root_logger:
                self._root_logger.setLevel(level_value)
    
    def close(self):
        """关闭所有处理器"""
        for handler in self._handlers:
            handler.close()
            self._root_logger.removeHandler(handler)
        self._handlers = []


class ContextFilter(logging.Filter):
    """日志上下文过滤器"""
    
    def __init__(self, context: Dict[str, Any]):
        super().__init__()
        self._context = context
    
    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录，添加上下文"""
        for key, value in self._context.items():
            setattr(record, key, value)
        
        # 添加时间戳
        record.iso_timestamp = datetime.now().isoformat()
        
        return True


def get_logger(name: str) -> logging.Logger:
    """
    获取logger的快捷方法
    
    Args:
        name: logger名称
    
    Returns:
        Logger实例
    """
    manager = LoggerManager()
    return manager.get_logger(name)


def setup_logging(
    level: str = 'INFO',
    format_type: str = 'json',
    log_dir: str = '/var/log/itops'
) -> LoggerManager:
    """
    快速设置日志的便捷函数
    
    Args:
        level: 日志级别
        format_type: 格式化类型
        log_dir: 日志目录
    
    Returns:
        LoggerManager实例
    """
    log_file = Path(log_dir) / 'itops.log'
    
    manager = LoggerManager()
    manager.setup(
        level=level,
        format_type=format_type,
        file_path=str(log_file),
        file_rotation='size'
    )
    
    return manager


# 结构化日志支持
class StructuredLogger:
    """
    结构化日志包装器
    
    使用示例：
    >>> logger = StructuredLogger(get_logger('test'))
    >>> logger.log(
    ...     level='INFO',
    ...     message='Server started',
    ...     server='web-01',
    ...     port=8080,
    ...     env='production'
    ... )
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def log(
        self,
        level: str,
        message: str,
        **kwargs
    ):
        """
        记录结构化日志
        
        Args:
            level: 日志级别
            message: 日志消息
            **kwargs: 结构化数据
        """
        logger_method = getattr(self._logger, level.lower(), self._logger.info)
        logger_method(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Debug级别结构化日志"""
        self.log('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Info级别结构化日志"""
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning级别结构化日志"""
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Error级别结构化日志"""
        self.log('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Critical级别结构化日志"""
        self.log('CRITICAL', message, **kwargs)