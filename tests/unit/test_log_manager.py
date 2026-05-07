# -*- coding: utf-8 -*-
"""
单元测试 - 核心日志管理器
"""
import os
import sys
import json
import logging
import threading
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.log.manager import (
    TextFormatter, JSONFormatter, CEFFormatter,
    StreamHandler, RotatingFileHandler, TimedRotatingFileHandler,
    SysLogHandler, BufferedHandler, ContextFilter,
    LoggerManager, StructuredLogger, get_logger, get_structured_logger
)


class TestTextFormatter:
    """测试文本格式化器"""

    def test_format_default(self):
        """测试默认格式"""
        formatter = TextFormatter()
        record = self._create_log_record('Test message', logging.INFO, 'test_logger')

        result = formatter.format(record)

        assert 'Test message' in result
        assert 'INFO' in result
        assert 'test_logger' in result

    def test_format_custom_fmt(self):
        """测试自定义格式"""
        custom_fmt = "%(levelname)s - %(message)s"
        formatter = TextFormatter(fmt=custom_fmt)
        record = self._create_log_record('Error occurred', logging.ERROR, 'custom')

        result = formatter.format(record)

        assert 'ERROR' in result
        assert 'Error occurred' in result

    def test_format_different_levels(self):
        """测试不同日志级别"""
        formatter = TextFormatter()

        for level, level_name in [(logging.DEBUG, 'DEBUG'), (logging.INFO, 'INFO'),
                                   (logging.WARNING, 'WARNING'), (logging.ERROR, 'ERROR')]:
            record = self._create_log_record('Test', level, 'test')
            result = formatter.format(record)
            assert level_name in result

    def _create_log_record(self, message, level, name):
        """创建LogRecord"""
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname='test.py',
            lineno=1,
            msg=message,
            args=(),
            exc_info=None
        )
        return record


class TestJSONFormatter:
    """测试JSON格式化器"""

    def test_format_basic(self):
        """测试基本格式"""
        formatter = JSONFormatter()
        record = self._create_log_record('Test message', logging.INFO, 'test_logger')

        result = formatter.format(record)
        data = json.loads(result)

        assert data['message'] == 'Test message'
        assert data['level'] == 'INFO'
        assert data['logger'] == 'test_logger'
        assert 'timestamp' in data
        assert 'module' in data
        assert 'function' in data
        assert 'line' in data
        assert 'process_id' in data
        assert 'thread_id' in data

    def test_format_with_extra_fields(self):
        """测试额外字段"""
        formatter = JSONFormatter()
        record = self._create_log_record('Test', logging.INFO, 'test')
        record.extra_fields = {'user_id': '123', 'action': 'login'}

        result = formatter.format(record)
        data = json.loads(result)

        assert data['user_id'] == '123'
        assert data['action'] == 'login'

    def test_format_exclude_extra(self):
        """测试不包含额外字段"""
        formatter = JSONFormatter(include_extra=False)
        record = self._create_log_record('Test', logging.INFO, 'test')
        record.extra_fields = {'user_id': '123'}

        result = formatter.format(record)
        data = json.loads(result)

        assert 'user_id' not in data

    def test_format_exception(self):
        """测试异常格式"""
        formatter = JSONFormatter()

        try:
            raise ValueError("test error")
        except:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='test.py',
            lineno=1,
            msg='Error occurred',
            args=(),
            exc_info=exc_info
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert 'exception' in data
        assert data['exception']['type'] == 'ValueError'
        assert data['exception']['message'] == 'test error'
        assert 'traceback' in data['exception']

    def test_format_exception_no_error(self):
        """测试无异常情况"""
        formatter = JSONFormatter()
        record = self._create_log_record('Test', logging.INFO, 'test')

        result = formatter.format(record)
        data = json.loads(result)

        assert 'exception' not in data

    def _create_log_record(self, message, level, name):
        """创建LogRecord"""
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname='test.py',
            lineno=1,
            msg=message,
            args=(),
            exc_info=None
        )
        return record


class TestCEFFormatter:
    """测试CEF格式化器"""

    def test_format_basic(self):
        """测试基本格式"""
        formatter = CEFFormatter()
        record = self._create_log_record('Test message', logging.INFO, 'test_module')

        result = formatter.format(record)

        assert 'CEF:1.0' in result
        assert 'ITOps' in result
        assert 'Platform' in result
        assert 'Test message' in result
        assert 'msg=' in result

    def test_map_severity_debug(self):
        """测试DEBUG级别映射"""
        formatter = CEFFormatter()
        assert formatter._map_severity('DEBUG') == 0

    def test_map_severity_info(self):
        """测试INFO级别映射"""
        formatter = CEFFormatter()
        assert formatter._map_severity('INFO') == 1

    def test_map_severity_warning(self):
        """测试WARNING级别映射"""
        formatter = CEFFormatter()
        assert formatter._map_severity('WARNING') == 4

    def test_map_severity_error(self):
        """测试ERROR级别映射"""
        formatter = CEFFormatter()
        assert formatter._map_severity('ERROR') == 7

    def test_map_severity_critical(self):
        """测试CRITICAL级别映射"""
        formatter = CEFFormatter()
        assert formatter._map_severity('CRITICAL') == 10

    def test_map_severity_unknown(self):
        """测试未知级别映射"""
        formatter = CEFFormatter()
        assert formatter._map_severity('UNKNOWN') == 1

    def test_get_cef_version(self):
        """测试CEF版本"""
        formatter = CEFFormatter()
        assert formatter._get_cef_version() == '1.0'

    def test_format_different_severity(self):
        """测试不同严重级别"""
        formatter = CEFFormatter()

        record_debug = self._create_log_record('Debug', logging.DEBUG, 'test')
        result_debug = formatter.format(record_debug)
        assert ' 0 ' in result_debug or result_debug.endswith(' 0')

        record_error = self._create_log_record('Error', logging.ERROR, 'test')
        result_error = formatter.format(record_error)
        assert ' 7 ' in result_error or result_error.endswith(' 7')

    def _create_log_record(self, message, level, name):
        """创建LogRecord"""
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname='test.py',
            lineno=1,
            msg=message,
            args=(),
            exc_info=None
        )
        return record


class TestStreamHandler:
    """测试控制台处理器"""

    def test_get_handler(self):
        """测试获取处理器"""
        handler = StreamHandler(level='DEBUG', formatter=TextFormatter())
        result = handler.get_handler()

        assert isinstance(result, logging.StreamHandler)
        assert result.level == logging.DEBUG

    def test_get_handler_default_level(self):
        """测试默认级别"""
        handler = StreamHandler()
        result = handler.get_handler()

        assert result.level == logging.INFO

    def test_get_handler_with_formatter(self):
        """测试设置格式化器"""
        formatter = JSONFormatter()
        handler = StreamHandler(formatter=formatter)
        result = handler.get_handler()

        assert result.formatter is formatter


class TestRotatingFileHandler:
    """测试轮转文件处理器"""

    @patch('core.log.manager.Path')
    @patch('core.log.manager.RotatingFileHandler')
    def test_get_handler(self, mock_rotating_handler, mock_path):
        """测试获取处理器"""
        mock_path.return_value.parent.mkdir.return_value = None
        mock_handler_instance = MagicMock()
        mock_rotating_handler.return_value = mock_handler_instance

        handler = RotatingFileHandler(
            filename='logs/test.log',
            max_bytes=1024,
            backup_count=3,
            level='DEBUG'
        )
        result = handler.get_handler()

        mock_rotating_handler.assert_called_once()
        assert result == mock_handler_instance
        assert result.setLevel.called

    @patch('core.log.manager.Path')
    @patch('core.log.manager.RotatingFileHandler')
    def test_get_handler_creates_directory(self, mock_rotating_handler, mock_path):
        """测试创建目录"""
        mock_path.return_value.parent.mkdir.return_value = None
        mock_rotating_handler.return_value = MagicMock()

        handler = RotatingFileHandler(filename='logs/test.log')
        handler.get_handler()

        mock_path.return_value.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestTimedRotatingFileHandler:
    """测试时间轮转文件处理器"""

    @patch('core.log.manager.Path')
    @patch('core.log.manager.TimedRotatingFileHandler')
    def test_get_handler(self, mock_timed_handler, mock_path):
        """测试获取处理器"""
        mock_path.return_value.parent.mkdir.return_value = None
        mock_handler_instance = MagicMock()
        mock_timed_handler.return_value = mock_handler_instance

        handler = TimedRotatingFileHandler(
            filename='logs/test.log',
            when='midnight',
            interval=1,
            backup_count=7,
            level='INFO'
        )
        result = handler.get_handler()

        mock_timed_handler.assert_called_once()
        assert result == mock_handler_instance

    @patch('core.log.manager.Path')
    @patch('core.log.manager.TimedRotatingFileHandler')
    def test_get_handler_default_params(self, mock_timed_handler, mock_path):
        """测试默认参数"""
        mock_path.return_value.parent.mkdir.return_value = None
        mock_timed_handler.return_value = MagicMock()

        handler = TimedRotatingFileHandler()
        handler.get_handler()

        call_args = mock_timed_handler.call_args
        assert call_args[1]['when'] == 'midnight'
        assert call_args[1]['interval'] == 1
        assert call_args[1]['backupCount'] == 7


class TestSysLogHandler:
    """测试Syslog处理器"""

    @patch('core.log.manager.logging.handlers.SysLogHandler')
    def test_get_handler(self, mock_syslog_handler):
        """测试获取处理器"""
        mock_handler_instance = MagicMock()
        mock_syslog_handler.return_value = mock_handler_instance

        handler = SysLogHandler(host='localhost', port=514, level='INFO')
        result = handler.get_handler()

        mock_syslog_handler.assert_called_once_with(address=('localhost', 514))
        assert result == mock_handler_instance
        assert result.setLevel.called

    @patch('core.log.manager.logging.handlers.SysLogHandler')
    def test_get_handler_custom_address(self, mock_syslog_handler):
        """测试自定义地址"""
        mock_syslog_handler.return_value = MagicMock()

        handler = SysLogHandler(host='syslog.example.com', port=1514)
        handler.get_handler()

        mock_syslog_handler.assert_called_once_with(address=('syslog.example.com', 1514))


class TestBufferedHandler:
    """测试缓冲处理器"""

    def test_buffer_size(self):
        """测试缓冲区大小"""
        handler = BufferedHandler(buffer_size=200)
        assert handler.buffer_size == 200

    def test_flush_level(self):
        """测试刷新级别"""
        handler = BufferedHandler(flush_level='WARNING')
        assert handler.flush_level == logging.WARNING

    def test_flush_interval(self):
        """测试刷新间隔"""
        handler = BufferedHandler(flush_interval=120)
        assert handler.flush_interval == 120

    def test_get_handler(self):
        """测试获取处理器"""
        handler = BufferedHandler(buffer_size=100)
        result = handler.get_handler()

        assert isinstance(result, logging.Handler)

    def test_default_values(self):
        """测试默认值"""
        handler = BufferedHandler()

        assert handler.buffer_size == 100
        assert handler.flush_level == logging.ERROR
        assert handler.flush_interval == 60


class TestContextFilter:
    """测试上下文过滤器"""

    def test_add_context(self):
        """测试添加上下文"""
        filter = ContextFilter()
        filter.add_context(user_id='123', action='login')

        assert filter._context['user_id'] == '123'
        assert filter._context['action'] == 'login'

    def test_add_context_multiple_calls(self):
        """测试多次添加上下文"""
        filter = ContextFilter()
        filter.add_context(user_id='123')
        filter.add_context(action='login')
        filter.add_context(ip='192.168.1.1')

        assert filter._context['user_id'] == '123'
        assert filter._context['action'] == 'login'
        assert filter._context['ip'] == '192.168.1.1'

    def test_clear_context(self):
        """测试清除上下文"""
        filter = ContextFilter()
        filter.add_context(user_id='123')
        filter.clear_context()

        assert len(filter._context) == 0

    def test_filter_with_context(self):
        """测试过滤时添加上下文"""
        filter = ContextFilter()
        filter.add_context(user_id='123')
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='test.py',
            lineno=1, msg='test', args=(), exc_info=None
        )

        result = filter.filter(record)

        assert result is True
        assert hasattr(record, 'extra_fields')
        assert record.extra_fields['user_id'] == '123'

    def test_filter_without_context(self):
        """测试无上下文时过滤"""
        filter = ContextFilter()
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='test.py',
            lineno=1, msg='test', args=(), exc_info=None
        )

        result = filter.filter(record)

        assert result is True

    def test_filter_thread_local(self):
        """测试线程本地上下文"""
        filter = ContextFilter()

        def add_thread_context():
            filter.add_context(thread_id='thread_1')

        thread = threading.Thread(target=add_thread_context)
        thread.start()
        thread.join()

        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='test.py',
            lineno=1, msg='test', args=(), exc_info=None
        )
        result = filter.filter(record)

        assert result is True


class TestLoggerManager:
    """测试日志管理器"""

    def setup_method(self):
        """每个测试前重置单例"""
        LoggerManager._instance = None

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = LoggerManager()
        manager2 = LoggerManager()

        assert manager1 is manager2

    @patch('core.log.manager.StreamHandler')
    def test_configure_console_only(self, mock_stream_handler):
        """测试仅配置控制台"""
        mock_handler_instance = MagicMock()
        mock_stream_handler_instance = MagicMock()
        mock_stream_handler.return_value.get_handler.return_value = mock_stream_handler_instance

        manager = LoggerManager()
        # 只开启console，不开启file rotation
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False, level='DEBUG')

        assert mock_stream_handler.called

    @patch('core.log.manager.RotatingFileHandler')
    @patch('core.log.manager.Path')
    def test_configure_file_rotation(self, mock_path, mock_rotating):
        """测试配置文件轮转"""
        mock_path.return_value.parent.mkdir.return_value = None
        mock_handler_instance = MagicMock()
        mock_rotating.return_value.get_handler.return_value = mock_handler_instance

        manager = LoggerManager()
        manager.configure(
            console=False,
            file_size_rotation=True,
            log_dir='logs',
            log_file='test.log'
        )

        assert mock_rotating.called

    @patch('core.log.manager.SysLogHandler')
    def test_configure_syslog_only(self, mock_syslog_handler):
        """测试仅配置syslog"""
        mock_handler_instance = MagicMock()
        mock_syslog_handler.return_value.get_handler.return_value = mock_handler_instance

        manager = LoggerManager()
        # 只开启syslog，不开启file rotation
        manager.configure(console=False, file_size_rotation=False, file_time_rotation=False, syslog=True, syslog_host='localhost')

        assert mock_syslog_handler.called

    @patch('core.log.manager.StreamHandler')
    @patch('core.log.manager.RotatingFileHandler')
    def test_configure_json_format(self, mock_rotating, mock_stream):
        """测试配置JSON格式"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance
        mock_path_instance = MagicMock()
        with patch('core.log.manager.Path', return_value=mock_path_instance):
            mock_rotating_instance = MagicMock()
            mock_rotating.return_value.get_handler.return_value = mock_rotating_instance

            manager = LoggerManager()
            manager.configure(console=True, file_size_rotation=True, json_format=True)

            # 验证不报错即可

    def test_add_handler(self):
        """测试添加处理器"""
        manager = LoggerManager()
        handler = logging.StreamHandler()

        manager.add_handler(handler)

        assert handler in manager._handlers

    @patch('core.log.manager.StreamHandler')
    def test_get_logger_creates_new(self, mock_stream):
        """测试创建新logger"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)

        logger = manager.get_logger('test_logger')

        assert isinstance(logger, logging.Logger)
        assert 'test_logger' in manager._loggers

    @patch('core.log.manager.StreamHandler')
    def test_get_logger_returns_existing(self, mock_stream):
        """测试返回已存在的logger"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)

        logger1 = manager.get_logger('test_logger')
        logger2 = manager.get_logger('test_logger')

        assert logger1 is logger2

    @patch('core.log.manager.StreamHandler')
    def test_add_context(self, mock_stream):
        """测试添加上下文"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        manager.add_context(user_id='123')

        assert manager._context_filter._context.get('user_id') == '123'

    @patch('core.log.manager.StreamHandler')
    def test_clear_context(self, mock_stream):
        """测试清除上下文"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        manager.add_context(user_id='123')

        manager.clear_context()

        assert len(manager._context_filter._context) == 0

    @patch('core.log.manager.StreamHandler')
    def test_set_level_named_logger(self, mock_stream):
        """测试设置指定logger级别"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)

        manager.set_level('DEBUG', 'test_logger')
        logger = manager.get_logger('test_logger')

        assert logger.level == logging.DEBUG

    @patch('core.log.manager.StreamHandler')
    def test_set_level_default(self, mock_stream):
        """测试设置默认级别"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)

        manager.set_level('WARNING')
        manager.get_logger('test_logger')

        assert manager._default_level == 'WARNING'

    @patch('core.log.manager.StreamHandler')
    def test_shutdown(self, mock_stream):
        """测试关闭"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        with patch('core.log.manager.logging.shutdown') as mock_shutdown:
            manager = LoggerManager()
            manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
            manager.get_logger('test_logger')

            manager.shutdown()

            mock_shutdown.assert_called_once()
            assert len(manager._loggers) == 0


class TestStructuredLogger:
    """测试结构化日志"""

    @patch('core.log.manager.StreamHandler')
    def test_add_context(self, mock_stream):
        """测试添加上下文"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        logger = manager.get_logger('test')
        structured = StructuredLogger(logger)

        structured.add_context(user_id='123', action='login')

        assert structured._context['user_id'] == '123'
        assert structured._context['action'] == 'login'

    @patch('core.log.manager.StreamHandler')
    def test_log_includes_context(self, mock_stream):
        """测试日志包含上下文"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        logger = manager.get_logger('test')
        structured = StructuredLogger(logger)
        structured.add_context(user_id='123')

        # 验证_log方法存在
        assert hasattr(structured, '_log')
        assert callable(structured._log)

    @patch('core.log.manager.StreamHandler')
    def test_debug_method(self, mock_stream):
        """测试debug方法"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        logger = manager.get_logger('test')
        structured = StructuredLogger(logger)

        assert callable(structured.debug)

    @patch('core.log.manager.StreamHandler')
    def test_info_method(self, mock_stream):
        """测试info方法"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        logger = manager.get_logger('test')
        structured = StructuredLogger(logger)

        assert callable(structured.info)

    @patch('core.log.manager.StreamHandler')
    def test_warning_method(self, mock_stream):
        """测试warning方法"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        logger = manager.get_logger('test')
        structured = StructuredLogger(logger)

        assert callable(structured.warning)

    @patch('core.log.manager.StreamHandler')
    def test_error_method(self, mock_stream):
        """测试error方法"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        logger = manager.get_logger('test')
        structured = StructuredLogger(logger)

        assert callable(structured.error)

    @patch('core.log.manager.StreamHandler')
    def test_critical_method(self, mock_stream):
        """测试critical方法"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value.get_handler.return_value = mock_stream_instance

        manager = LoggerManager()
        manager.configure(console=True, file_size_rotation=False, file_time_rotation=False)
        logger = manager.get_logger('test')
        structured = StructuredLogger(logger)

        assert callable(structured.critical)


class TestGetLogger:
    """测试get_logger函数"""

    def setup_method(self):
        """每个测试前重置单例"""
        LoggerManager._instance = None

    @patch('core.log.manager.StreamHandler')
    def test_get_logger_default(self, mock_stream):
        """测试默认获取logger"""
        mock_stream.return_value.get_handler.return_value = MagicMock()

        logger = get_logger()

        assert isinstance(logger, logging.Logger)

    @patch('core.log.manager.StreamHandler')
    def test_get_logger_named(self, mock_stream):
        """测试获取命名logger"""
        mock_stream.return_value.get_handler.return_value = MagicMock()

        logger = get_logger('my_logger')

        assert isinstance(logger, logging.Logger)


class TestGetStructuredLogger:
    """测试get_structured_logger函数"""

    def setup_method(self):
        """每个测试前重置单例"""
        LoggerManager._instance = None

    @patch('core.log.manager.StreamHandler')
    def test_get_structured_logger(self, mock_stream):
        """测试获取结构化logger"""
        mock_stream.return_value.get_handler.return_value = MagicMock()

        structured = get_structured_logger()

        assert isinstance(structured, StructuredLogger)

    @patch('core.log.manager.StreamHandler')
    def test_get_structured_logger_named(self, mock_stream):
        """测试获取命名结构化logger"""
        mock_stream.return_value.get_handler.return_value = MagicMock()

        structured = get_structured_logger('my_structured_logger')

        assert isinstance(structured, StructuredLogger)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
