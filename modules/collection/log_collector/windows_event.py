"""Windows事件采集器和麒麟系统日志采集"""
import os
import logging
import re
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import subprocess

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """日志级别"""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


@dataclass
class WindowsEvent:
    """Windows事件"""
    event_id: int
    level: str
    timestamp: datetime
    source: str
    computer: str
    message: str
    channel: str
    record_id: Optional[int] = None
    task: Optional[str] = None
    keywords: Optional[List[str]] = None
    user: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KylinLogEntry:
    """麒麟系统日志条目"""
    timestamp: datetime
    hostname: str
    service: str
    level: str
    message: str
    pid: Optional[int] = None
    source_file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WindowsEventCollector:
    """
    Windows事件采集器
    支持功能:
    - Windows Event Log读取
    - 麒麟系统日志采集
    - 告警级别识别
    """
    
    # Windows事件级别映射
    LEVEL_MAP = {
        1: LogLevel.CRITICAL,
        2: LogLevel.ERROR,
        3: LogLevel.WARNING,  # 通常不存在
        4: LogLevel.INFO,
        5: LogLevel.DEBUG,
    }
    
    # 常用日志通道
    DEFAULT_CHANNELS = [
        'Application',
        'System',
        'Security',
        'Setup',
    ]
    
    def __init__(
        self,
        channels: Optional[List[str]] = None,
        level_filter: Optional[int] = None,
        callback: Optional[Callable[[WindowsEvent], None]] = None,
        poll_interval: int = 5,
    ):
        """
        初始化Windows事件采集器
        
        Args:
            channels: 要采集的日志通道
            level_filter: 最低日志级别过滤
            callback: 事件回调函数
            poll_interval: 轮询间隔（秒）
        """
        self.channels = channels or self.DEFAULT_CHANNELS
        self.level_filter = level_filter
        self.callback = callback
        self.poll_interval = poll_interval
        
        self._last_record_ids: Dict[str, int] = {}
        self._running = False
        self._thread: Optional[object] = None
    
    def _is_windows(self) -> bool:
        """检查是否为Windows系统"""
        return os.name == 'nt'
    
    def _parse_windows_event_level(self, level: int) -> LogLevel:
        """解析Windows事件级别"""
        return self.LEVEL_MAP.get(level, LogLevel.INFO)
    
    def _parse_wevtutil_output(self, output: str, channel: str) -> List[WindowsEvent]:
        """解析wevtutil输出"""
        events = []
        
        # 分割事件记录
        # 格式: Event[0]: ...
        event_pattern = re.compile(r'Event\[\d+\]:\s*(.*?)(?=Event\[\d+\]:|$)', re.DOTALL)
        
        for event_match in event_pattern.finditer(output):
            event_text = event_match.group(1)
            
            try:
                event_id = 0
                level = LogLevel.INFO
                timestamp = datetime.now()
                source = ''
                computer = ''
                message = ''
                record_id = None
                task = None
                user = None
                
                # 解析各字段
                lines = event_text.split('\n')
                for line in lines:
                    line = line.strip()
                    
                    if line.startswith('EventID:'):
                        event_id = int(line.split(':', 1)[1].strip())
                    elif line.startswith('Level:'):
                        level_val = int(line.split(':', 1)[1].strip())
                        level = self._parse_windows_event_level(level_val)
                    elif line.startswith('TimeCreated:'):
                        time_str = line.split(':', 1)[1].strip().replace('SystemTime=', '')
                        try:
                            timestamp = datetime.fromisoformat(time_str)
                        except ValueError:
                            pass
                    elif line.startswith('Source Name:'):
                        source = line.split(':', 1)[1].strip()
                    elif line.startswith('Computer:'):
                        computer = line.split(':', 1)[1].strip()
                    elif line.startswith('Message:'):
                        message = line.split(':', 1)[1].strip()
                    elif line.startswith('EventRecordID:'):
                        record_id = int(line.split(':', 1)[1].strip())
                    elif line.startswith('Task:'):
                        task = line.split(':', 1)[1].strip()
                    elif line.startswith('User:'):
                        user = line.split(':', 1)[1].strip()
                
                # 应用级别过滤
                if self.level_filter is not None:
                    if level.value == LogLevel.DEBUG.value and self.level_filter > 4:
                        continue
                    if level.value == LogLevel.INFO.value and self.level_filter > 5:
                        continue
                
                event = WindowsEvent(
                    event_id=event_id,
                    level=level.value,
                    timestamp=timestamp,
                    source=source,
                    computer=computer,
                    message=message,
                    channel=channel,
                    record_id=record_id,
                    task=task,
                    user=user,
                )
                
                events.append(event)
                
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")
                continue
        
        return events
    
    def _read_channel(self, channel: str, start_record: int = 0) -> List[WindowsEvent]:
        """读取指定通道的事件"""
        if not self._is_windows():
            return []
        
        try:
            # 使用wevtutil读取事件
            cmd = [
                'wevtutil',
                'qe', channel,
                '/c', '100',  # 最多100条
                '/f', 'text',
                '/rd', 'true',  # 正向读取
            ]
            
            if start_record > 0:
                cmd.extend(['/Forward', '/StartRecord', str(start_record)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                return self._parse_wevtutil_output(result.stdout, channel)
            else:
                logger.warning(f"Failed to read channel {channel}: {result.stderr}")
        
        except FileNotFoundError:
            logger.error("wevtutil not found - not running on Windows?")
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout reading channel {channel}")
        except Exception as e:
            logger.error(f"Error reading channel {channel}: {e}")
        
        return []
    
    def collect(self, channel: Optional[str] = None) -> List[WindowsEvent]:
        """
        采集事件
        
        Args:
            channel: 指定通道，None表示所有通道
        """
        events = []
        channels = [channel] if channel else self.channels
        
        for ch in channels:
            start_record = self._last_record_ids.get(ch, 0)
            channel_events = self._read_channel(ch, start_record)
            
            for event in channel_events:
                if event.record_id and event.record_id > self._last_record_ids.get(ch, 0):
                    self._last_record_ids[ch] = event.record_id
                
                events.append(event)
                
                if self.callback:
                    self.callback(event)
        
        return events
    
    def start_collection(self):
        """启动循环采集"""
        if self._running:
            return
        
        self._running = True
        
        import threading
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        
        logger.info("Windows event collection started")
    
    def stop_collection(self):
        """停止循环采集"""
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=10)
        
        logger.info("Windows event collection stopped")
    
    def _collection_loop(self):
        """采集循环"""
        import time
        
        while self._running:
            try:
                self.collect()
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
            
            time.sleep(self.poll_interval)


class KylinLogCollector:
    """
    麒麟系统日志采集器
    支持银河麒麟、星光麒麟等国产操作系统
    """
    
    # 麒麟系统日志文件位置
    LOG_PATHS = {
        'system': [
            '/var/log/messages',
            '/var/log/syslog',
            '/var/log/kylin.log',
        ],
        'secure': [
            '/var/log/secure',
            '/var/log/auth.log',
        ],
        'kernel': [
            '/var/log/kmsg',
            '/var/log/dmesg',
        ],
        'boot': [
            '/var/log/boot.log',
            '/var/log/boot',
        ],
        'application': [
            '/var/log/app.log',
        ],
    }
    
    # 日志级别模式
    LEVEL_PATTERNS = {
        r'\b(emerg|emergency)\b': LogLevel.CRITICAL,
        r'\b(crit|critical)\b': LogLevel.CRITICAL,
        r'\b(err|error)\b': LogLevel.ERROR,
        r'\b(warn|warning)\b': LogLevel.WARNING,
        r'\b(notice)\b': LogLevel.INFO,
        r'\b(info)\b': LogLevel.INFO,
        r'\b(debug)\b': LogLevel.DEBUG,
    }
    
    # 标准日志格式
    SYSLOG_PATTERN = re.compile(
        r'^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<service>\S+?)'
        r'(?:\[(?P<pid>\d+)\])?\s*:?\s*'
        r'(?P<message>.*)$'
    )
    
    JOURNAL_PATTERN = re.compile(
        r'^(?P<timestamp>\w{3}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<service>\S+)\s+:?\s*'
        r'(?P<pid>\[\d+\])?\s*:?\s*'
        r'(?P<message>.*)$'
    )
    
    def __init__(
        self,
        log_paths: Optional[Dict[str, List[str]]] = None,
        callback: Optional[Callable[[KylinLogEntry], None]] = None,
    ):
        """
        初始化麒麟日志采集器
        
        Args:
            log_paths: 日志路径配置
            callback: 日志回调函数
        """
        self.log_paths = log_paths or self.LOG_PATHS
        self.callback = callback
        
        self._read_positions: Dict[str, int] = {}
        self._running = False
        self._thread = None
    
    def _parse_level(self, message: str) -> str:
        """解析日志级别"""
        message_lower = message.lower()
        
        for pattern, level in self.LEVEL_PATTERNS.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                return level.value
        
        return LogLevel.INFO.value
    
    def _parse_syslog_line(self, line: str, hostname: str = '') -> Optional[KylinLogEntry]:
        """解析标准syslog行"""
        match = self.SYSLOG_PATTERN.match(line)
        
        if match:
            groups = match.groupdict()
            
            # 解析时间戳
            timestamp_str = groups.get('timestamp', '')
            try:
                timestamp = datetime.strptime(timestamp_str, '%b %d %H:%M:%S')
                timestamp = timestamp.replace(year=datetime.now().year)
            except ValueError:
                timestamp = datetime.now()
            
            return KylinLogEntry(
                timestamp=timestamp,
                hostname=groups.get('hostname', hostname),
                service=groups.get('service', 'unknown'),
                pid=int(groups.get('pid', 0)) if groups.get('pid') else None,
                level=self._parse_level(groups.get('message', '')),
                message=groups.get('message', ''),
            )
        
        return None
    
    def _parse_journal_line(self, line: str, hostname: str = '') -> Optional[KylinLogEntry]:
        """解析journald行"""
        match = self.JOURNAL_PATTERN.match(line)
        
        if match:
            groups = match.groupdict()
            
            timestamp_str = groups.get('timestamp', '')
            try:
                timestamp = datetime.strptime(timestamp_str, '%b %d %H:%M:%S')
                timestamp = timestamp.replace(year=datetime.now().year)
            except ValueError:
                timestamp = datetime.now()
            
            return KylinLogEntry(
                timestamp=timestamp,
                hostname=groups.get('hostname', hostname),
                service=groups.get('service', 'unknown'),
                pid=int(groups.get('pid', '[0]')[1:-1]) if groups.get('pid') else None,
                level=self._parse_level(groups.get('message', '')),
                message=groups.get('message', ''),
            )
        
        return None
    
    def parse_line(self, line: str, log_type: str = 'system') -> Optional[KylinLogEntry]:
        """解析日志行"""
        line = line.strip()
        
        if not line:
            return None
        
        # 尝试syslog格式
        entry = self._parse_syslog_line(line)
        if entry:
            return entry
        
        # 尝试journal格式
        entry = self._parse_journal_line(line)
        if entry:
            return entry
        
        # 无法解析，返回原始
        return KylinLogEntry(
            timestamp=datetime.now(),
            hostname=socket.gethostname() if hasattr(socket, 'gethostname') else 'unknown',
            service=log_type,
            level=self._parse_level(line),
            message=line,
        )
    
    def _read_log_file(
        self,
        file_path: str,
        start_position: int = 0,
        log_type: str = 'system',
    ) -> List[KylinLogEntry]:
        """读取日志文件"""
        entries = []
        
        try:
            import socket
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(start_position)
                
                for line in f:
                    entry = self.parse_line(line, log_type)
                    if entry:
                        entry.source_file = file_path
                        entries.append(entry)
                        
                        if self.callback:
                            self.callback(entry)
                
                # 更新位置
                self._read_positions[file_path] = f.tell()
        
        except FileNotFoundError:
            logger.debug(f"Log file not found: {file_path}")
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {e}")
        
        return entries
    
    def collect(self, log_type: Optional[str] = None) -> List[KylinLogEntry]:
        """采集日志"""
        entries = []
        types = [log_type] if log_type else self.log_paths.keys()
        
        for log_type in types:
            paths = self.log_paths.get(log_type, [])
            
            for path in paths:
                start_pos = self._read_positions.get(path, 0)
                type_entries = self._read_log_file(path, start_pos, log_type)
                entries.extend(type_entries)
        
        return entries
    
    def collect_from_journal(self, lines: int = 100) -> List[KylinLogEntry]:
        """从systemd journal采集"""
        entries = []
        
        try:
            result = subprocess.run(
                ['journalctl', '-n', str(lines), '--no-pager', '-o', 'short-iso'],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    entry = self.parse_line(line)
                    if entry:
                        entries.append(entry)
                        
                        if self.callback:
                            self.callback(entry)
        
        except FileNotFoundError:
            logger.warning("journalctl not found - systemd may not be available")
        except Exception as e:
            logger.error(f"Error reading journal: {e}")
        
        return entries
    
    def start_collection(self, interval: int = 5):
        """启动循环采集"""
        if self._running:
            return
        
        self._running = True
        
        import threading
        
        def collection_loop():
            import time
            
            while self._running:
                try:
                    self.collect()
                    self.collect_from_journal(50)
                except Exception as e:
                    logger.error(f"Error in collection loop: {e}")
                
                time.sleep(interval)
        
        self._thread = threading.Thread(target=collection_loop, daemon=True)
        self._thread.start()
        
        logger.info("Kylin log collection started")
    
    def stop_collection(self):
        """停止循环采集"""
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=10)
        
        logger.info("Kylin log collection stopped")


# 平台选择器
def create_log_collector(
    platform: str = 'auto',
    **kwargs,
) -> Any:
    """
    创建日志采集器
    
    Args:
        platform: 平台类型 ('windows', 'kylin', 'linux', 'auto')
        **kwargs: 其他参数
    """
    if platform == 'auto':
        if os.name == 'nt':
            platform = 'windows'
        elif os.path.exists('/etc/kylin-release') or os.path.exists('/etc/星光麒麟'):
            platform = 'kylin'
        else:
            platform = 'linux'
    
    if platform == 'windows':
        return WindowsEventCollector(**kwargs)
    elif platform == 'kylin' or platform == 'linux':
        return KylinLogCollector(**kwargs)
    else:
        raise ValueError(f"Unsupported platform: {platform}")
