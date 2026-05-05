"""通用日志解析器"""
import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """日志级别"""
    CRITICAL = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5
    UNKNOWN = 99


@dataclass
class ParsedLog:
    """解析后的日志"""
    timestamp: Optional[datetime]
    level: str
    logger_name: str
    message: str
    raw: str
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    thread: Optional[str] = None
    process: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class GenericLogParser:
    """
    通用日志解析器
    支持多种日志格式的正则匹配
    """
    
    # 常用时间格式
    TIMESTAMP_PATTERNS = [
        # ISO格式
        (r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?', 'iso'),
        # Python标准格式
        (r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d+)?', 'python'),
        # 常用格式
        (r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}', 'apache'),
        # 简短格式
        (r'\d{4}\d{2}\d{2}_\d{2}\d{2}\d{2}', 'short'),
        # Syslog格式
        (r'\w{3}\s+\d{1,2} \d{2}:\d{2}:\d{2}', 'syslog'),
    ]
    
    # 日志级别模式
    LEVEL_PATTERNS = [
        (r'\bCRITICAL\b|\bFATAL\b', LogLevel.CRITICAL),
        (r'\bERROR\b|\bERR\b', LogLevel.ERROR),
        (r'\bWARNING\b|\bWARN\b', LogLevel.WARNING),
        (r'\bINFO\b|\bINFORMATION\b', LogLevel.INFO),
        (r'\bDEBUG\b|\bDBG\b', LogLevel.DEBUG),
        (r'\bTRACE\b|\bVERBOSE\b', LogLevel.TRACE),
    ]
    
    # 通用日志格式
    # 格式: TIMESTAMP LEVEL MESSAGE
    STANDARD_PATTERN = re.compile(
        r'^(?P<timestamp>'
        + r'|'.join([p[0] for p in TIMESTAMP_PATTERNS])
        + r')\s+'
        r'(?P<level>'
        + r'|'.join([p[0] for p in LEVEL_PATTERNS])
        + r')\s+'
        r'(?P<message>.*)$'
    )
    
    # Python logging格式
    PYTHON_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d+)?)\s+'
        r'-(?P<level>\w+)\s+-(?P<logger>\S+)\s+-(?P<message>.*)'
        r'(?:\n(?P<trace>.*))?$'
    )
    
    # JSON格式
    JSON_PATTERN = re.compile(r'^\s*\{.*\}\s*$')
    
    # Apache/Nginx访问日志
    APACHE_PATTERN = re.compile(
        r'^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<request>[^"]*)"\s+'
        r'(?P<status>\d+)\s+'
        r'(?P<size>\S+)'
        r'(?:\s+"(?P<referrer>[^"]*)"\s+"(?P<ua>[^"]*)")?'
    )
    
    # JSON解析
    def _parse_json(self, raw: str) -> Optional[Dict[str, Any]]:
        """解析JSON"""
        try:
            import json
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    
    # 时间戳解析
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """解析时间戳"""
        # ISO格式
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        
        # Python格式
        try:
            if ',' in timestamp_str:
                timestamp_str = timestamp_str.replace(',', '.')
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            pass
        
        try:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
        
        # Apache格式
        try:
            return datetime.strptime(timestamp_str, '%d/%b/%Y:%H:%M:%S %z')
        except ValueError:
            pass
        
        # 简短格式
        try:
            return datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
        except ValueError:
            pass
        
        return None
    
    # 级别解析
    def _parse_level(self, level_str: str) -> str:
        """解析日志级别"""
        level_upper = level_str.upper()
        
        level_map = {
            'CRITICAL': 'CRITICAL',
            'FATAL': 'CRITICAL',
            'ERROR': 'ERROR',
            'ERR': 'ERROR',
            'WARNING': 'WARNING',
            'WARN': 'WARNING',
            'INFO': 'INFO',
            'INFORMATION': 'INFO',
            'DEBUG': 'DEBUG',
            'DBG': 'DEBUG',
            'TRACE': 'TRACE',
            'VERBOSE': 'TRACE',
        }
        
        return level_map.get(level_upper, 'INFO')
    
    # 标准格式解析
    def _parse_standard(self, raw: str) -> Optional[ParsedLog]:
        """解析标准格式日志"""
        match = self.STANDARD_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return ParsedLog(
                timestamp=self._parse_timestamp(groups['timestamp']),
                level=self._parse_level(groups['level']),
                logger_name='',
                message=groups['message'],
                raw=raw,
            )
        
        return None
    
    # Python格式解析
    def _parse_python(self, raw: str) -> Optional[ParsedLog]:
        """解析Python logging格式"""
        match = self.PYTHON_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return ParsedLog(
                timestamp=self._parse_timestamp(groups['timestamp']),
                level=self._parse_level(groups['level']),
                logger_name=groups['logger'],
                message=groups['message'],
                raw=raw,
                trace_id=groups.get('trace'),
            )
        
        return None
    
    # Apache格式解析
    def _parse_apache(self, raw: str) -> Optional[ParsedLog]:
        """解析Apache/Nginx日志"""
        match = self.APACHE_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return ParsedLog(
                timestamp=self._parse_timestamp(groups['timestamp'].replace(':', ' ', 1)),
                level='INFO',
                logger_name='access',
                message=groups['request'],
                raw=raw,
                ip_address=groups['ip'],
                user_id=groups.get('user'),
                extra={
                    'status': groups.get('status'),
                    'size': groups.get('size'),
                    'referrer': groups.get('referrer'),
                    'user_agent': groups.get('ua'),
                }
            )
        
        return None
    
    def parse(self, raw: str) -> ParsedLog:
        """
        解析日志行
        
        Args:
            raw: 原始日志行
            
        Returns:
            ParsedLog: 解析后的日志对象
        """
        raw = raw.strip()
        
        if not raw:
            return ParsedLog(
                timestamp=None,
                level='INFO',
                logger_name='',
                message='',
                raw=raw,
            )
        
        # 尝试JSON格式
        if self.JSON_PATTERN.match(raw):
            data = self._parse_json(raw)
            if data:
                return ParsedLog(
                    timestamp=self._parse_timestamp(data.get('timestamp', data.get('time', ''))),
                    level=self._parse_level(data.get('level', data.get('severity', 'INFO'))),
                    logger_name=data.get('logger', data.get('name', '')),
                    message=data.get('message', data.get('msg', '')),
                    raw=raw,
                    source_file=data.get('file'),
                    line_number=data.get('line'),
                    trace_id=data.get('trace_id', data.get('traceId')),
                    span_id=data.get('span_id', data.get('spanId')),
                    user_id=data.get('user_id', data.get('userId')),
                    extra={k: v for k, v in data.items() if k not in ['timestamp', 'level', 'logger', 'message', 'time', 'severity', 'name', 'msg', 'file', 'line', 'trace_id', 'traceId', 'span_id', 'spanId', 'user_id', 'userId']}
                )
        
        # 尝试Python格式
        parsed = self._parse_python(raw)
        if parsed:
            return parsed
        
        # 尝试Apache格式
        parsed = self._parse_apache(raw)
        if parsed:
            return parsed
        
        # 尝试标准格式
        parsed = self._parse_standard(raw)
        if parsed:
            return parsed
        
        # 无法解析，返回原始
        return ParsedLog(
            timestamp=datetime.now(),
            level='INFO',
            logger_name='',
            message=raw,
            raw=raw,
        )
    
    def parse_batch(self, lines: List[str]) -> List[ParsedLog]:
        """批量解析"""
        return [self.parse(line) for line in lines]
    
    def add_pattern(self, name: str, pattern: str, priority: int = 0):
        """
        添加自定义解析模式
        
        Args:
            name: 模式名称
            pattern: 正则表达式（包含捕获组）
            priority: 优先级
        """
        # 保存模式以便后续使用
        setattr(self, f'_custom_pattern_{name}', re.compile(pattern))


class StructuredLogParser:
    """
    结构化日志解析器
    专门处理JSON格式的结构化日志
    """
    
    def __init__(self, json_path_mapping: Optional[Dict[str, str]] = None):
        """
        初始化结构化日志解析器
        
        Args:
            json_path_mapping: JSON路径映射
        """
        self.json_path_mapping = json_path_mapping or {}
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """获取嵌套值"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    def parse(self, raw: str) -> Dict[str, Any]:
        """解析结构化日志"""
        import json
        
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        
        # 应用路径映射
        result = {}
        
        for target_key, json_path in self.json_path_mapping.items():
            result[target_key] = self._get_nested_value(data, json_path)
        
        # 保留原始字段
        for key, value in data.items():
            if key not in result:
                result[key] = value
        
        return result
