"""Syslog接收器 - 支持UDP/TCP接收、RFC3164/RFC5424解析"""
import socket
import threading
import logging
import struct
import re
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class SyslogProtocol(Enum):
    """Syslog协议版本"""
    RFC3164 = "RFC3164"
    RFC5424 = "RFC5424"
    UNKNOWN = "UNKNOWN"


class Facility(Enum):
    """Syslog设施"""
    KERNEL = 0
    USER = 1
    MAIL = 2
    SYSTEM = 3
    SECURITY1 = 4
    INTERNAL = 5
    PRINTER = 6
    NEWS = 7
    UUCP = 8
    CLOCK1 = 9
    AUTH2 = 10
    FTP = 11
    NTP = 12
    LOG_AUDIT = 13
    LOG_ALERT = 14
    CLOCK2 = 15
    LOCAL0 = 16
    LOCAL1 = 17
    LOCAL2 = 18
    LOCAL3 = 19
    LOCAL4 = 20
    LOCAL5 = 21
    LOCAL6 = 22
    LOCAL7 = 23


class Severity(Enum):
    """Syslog严重级别"""
    EMERGENCY = 0  # 系统不可用
    ALERT = 1      # 需要立即动作
    CRITICAL = 2  # 严重状态
    ERROR = 3      # 错误状态
    WARNING = 4    # 警告状态
    NOTICE = 5     # 正常但重要
    INFO = 6       # 信息
    DEBUG = 7      # 调试


@dataclass
class SyslogMessage:
    """Syslog消息"""
    timestamp: Optional[datetime]
    hostname: str
    app_name: str
    proc_id: Optional[str]
    msg_id: Optional[str]
    structured_data: Dict[str, Any]
    message: str
    facility: int
    severity: int
    protocol: SyslogProtocol
    raw: str
    source_ip: str
    source_port: int
    
    @property
    def facility_name(self) -> str:
        """获取设施名称"""
        try:
            return Facility(self.facility).name
        except ValueError:
            return f"UNKNOWN({self.facility})"
    
    @property
    def severity_name(self) -> str:
        """获取严重级别名称"""
        try:
            return Severity(self.severity).name
        except ValueError:
            return f"UNKNOWN({self.severity})"
    
    @property
    def level(self) -> str:
        """获取日志级别（统一格式）"""
        level_map = {
            Severity.EMERGENCY: "CRITICAL",
            Severity.ALERT: "CRITICAL",
            Severity.CRITICAL: "CRITICAL",
            Severity.ERROR: "ERROR",
            Severity.WARNING: "WARNING",
            Severity.NOTICE: "INFO",
            Severity.INFO: "INFO",
            Severity.DEBUG: "DEBUG",
        }
        try:
            return level_map[Severity(self.severity)]
        except ValueError:
            return "INFO"


class SyslogParser:
    """Syslog消息解析器"""
    
    # RFC3164 模式
    RFC3164_PATTERN = re.compile(
        r'^<(?P<pri>\d+)>'
        r'(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<tag>[^:\[]+)(?:\[(?P<pid>\d+)\])?(?::\s*)?'
        r'(?P<message>.*)$'
    )
    
    # RFC5424 模式 (非完整带结构化数据版本)
    RFC5424_PATTERN = re.compile(
        r'^<(?P<pri>\d+)>'
        r'(?P<version>\d+)\s+'
        r'(?P<timestamp>\S+)\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<app_name>\S+)\s+'
        r'(?P<proc_id>\S+)\s+'
        r'(?P<msg_id>\S+)\s+'
        r'(?P<structured_data>\[.*?\]|-)\s*'
        r'(?P<message>.*)$'
    )
    
    # 简化模式（无优先级）
    NO_PRI_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<message>.*)$'
    )
    
    # RFC3164 月份映射
    MONTH_MAP = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    def __init__(self):
        self.device_patterns: Dict[str, re.Pattern] = {}
        self._load_device_patterns()
    
    def _load_device_patterns(self):
        """加载设备特定模式"""
        # 华为设备模式
        self.device_patterns['huawei'] = re.compile(
            r'^(?P<timestamp>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+'
            r'(?P<hostname>\S+)\s+'
            r'(?P<module>\S+)\s+\d+\s+\[\s*(?P<level>\w+)\s*\]\s*'
            r'(?P<message>.*)$'
        )
        
        # 思科设备模式
        self.device_patterns['cisco'] = re.compile(
            r'^%(?P<facility>\w+):(?P<level>\w+):\s*'
            r'(?P<hostname>\S+),\s*'
            r'(?P<timestamp>\w+\s+\d+\s+\d{2}:\d{2}:\d{2})\s*'
            r'(?P<message>.*)$'
        )
        
        # 安全设备模式
        self.device_patterns['security'] = re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'(?P<level>\w+)\s+'
            r'(?P<hostname>\S+)\s+'
            r'(?P<module>\S+)\s+'
            r'(?P<message>.*)$'
        )
    
    def _parse_priority(self, pri: int) -> Tuple[int, int]:
        """解析优先级"""
        facility = pri // 8
        severity = pri % 8
        return facility, severity
    
    def _parse_rfc3164_timestamp(self, timestamp: str) -> Optional[datetime]:
        """解析RFC3164时间戳"""
        try:
            # 格式: "Jan  1 12:00:00" (注意空格)
            parts = timestamp.split()
            if len(parts) == 3:
                month = self.MONTH_MAP.get(parts[0], 1)
                day = int(parts[1])
                time_parts = parts[2].split(':')
                
                now = datetime.now()
                return datetime(
                    year=now.year,
                    month=month,
                    day=day,
                    hour=int(time_parts[0]),
                    minute=int(time_parts[1]),
                    second=int(time_parts[2])
                )
        except Exception as e:
            logger.warning(f"Failed to parse RFC3164 timestamp: {timestamp}, {e}")
        return None
    
    def _parse_rfc5424_timestamp(self, timestamp: str) -> Optional[datetime]:
        """解析RFC5424时间戳"""
        try:
            # 格式: "2024-01-01T12:00:00.000Z" 或 "2024-01-01 12:00:00"
            timestamp = timestamp.replace('T', ' ').replace('Z', '')
            if '.' in timestamp:
                timestamp = timestamp.split('.')[0]
            return datetime.fromisoformat(timestamp)
        except Exception as e:
            logger.warning(f"Failed to parse RFC5424 timestamp: {timestamp}, {e}")
        return None
    
    def _parse_structured_data(self, sd: str) -> Dict[str, Any]:
        """解析结构化数据"""
        result = {}
        
        if sd == '-' or not sd:
            return result
        
        # 匹配 [id key="value" key="value"]
        sd_pattern = re.compile(r'\[(?P<id>\S+)\s+(?P<params>[^\]]+)\]')
        
        for match in sd_pattern.finditer(sd):
            sd_id = match.group('id')
            params_str = match.group('params')
            
            params = {}
            param_pattern = re.compile(r'(\S+)="([^"]*)"')
            
            for param_match in param_pattern.finditer(params_str):
                key = param_match.group(1)
                value = param_match.group(2)
                params[key] = value
            
            result[sd_id] = params
        
        return result
    
    def parse(self, data: str, source_ip: str = "", source_port: int = 0) -> Optional[SyslogMessage]:
        """解析Syslog消息"""
        raw = data.strip()
        
        if not raw:
            return None
        
        # 尝试RFC5424格式
        rfc5424_match = self.RFC5424_PATTERN.match(raw)
        if rfc5424_match:
            groups = rfc5424_match.groupdict()
            pri = int(groups['pri'])
            facility, severity = self._parse_priority(pri)
            
            return SyslogMessage(
                timestamp=self._parse_rfc5424_timestamp(groups['timestamp']),
                hostname=groups['hostname'],
                app_name=groups['app_name'],
                proc_id=groups['proc_id'],
                msg_id=groups['msg_id'],
                structured_data=self._parse_structured_data(groups['structured_data']),
                message=groups['message'],
                facility=facility,
                severity=severity,
                protocol=SyslogProtocol.RFC5424,
                raw=raw,
                source_ip=source_ip,
                source_port=source_port,
            )
        
        # 尝试RFC3164格式
        rfc3164_match = self.RFC3164_PATTERN.match(raw)
        if rfc3164_match:
            groups = rfc3164_match.groupdict()
            pri = int(groups['pri'])
            facility, severity = self._parse_priority(pri)
            
            return SyslogMessage(
                timestamp=self._parse_rfc3164_timestamp(groups['timestamp']),
                hostname=groups['hostname'],
                app_name=groups['tag'] if 'tag' in groups else '',
                proc_id=groups.get('pid'),
                msg_id=None,
                structured_data={},
                message=groups['message'],
                facility=facility,
                severity=severity,
                protocol=SyslogProtocol.RFC3164,
                raw=raw,
                source_ip=source_ip,
                source_port=source_port,
            )
        
        # 尝试无优先级格式
        no_pri_match = self.NO_PRI_PATTERN.match(raw)
        if no_pri_match:
            groups = no_pri_match.groupdict()
            return SyslogMessage(
                timestamp=datetime.fromisoformat(groups['timestamp']),
                hostname=groups['hostname'],
                app_name='',
                proc_id=None,
                msg_id=None,
                structured_data={},
                message=groups['message'],
                facility=Facility.USER.value,
                severity=Severity.INFO.value,
                protocol=SyslogProtocol.UNKNOWN,
                raw=raw,
                source_ip=source_ip,
                source_port=source_port,
            )
        
        # 无法解析，返回原始消息
        return SyslogMessage(
            timestamp=datetime.now(),
            hostname=source_ip,
            app_name='unknown',
            proc_id=None,
            msg_id=None,
            structured_data={},
            message=raw,
            facility=Facility.USER.value,
            severity=Severity.INFO.value,
            protocol=SyslogProtocol.UNKNOWN,
            raw=raw,
            source_ip=source_ip,
            source_port=source_port,
        )
    
    def parse_device(self, data: str, device_type: str) -> Optional[SyslogMessage]:
        """使用设备特定模式解析"""
        if device_type not in self.device_patterns:
            return self.parse(data)
        
        pattern = self.device_patterns[device_type]
        match = pattern.match(data)
        
        if match:
            groups = match.groupdict()
            level = groups.get('level', 'INFO').upper()
            
            severity_map = {
                'EMERG': 0, 'ALERT': 1, 'CRIT': 2, 'CRITICAL': 2,
                'ERR': 3, 'ERROR': 3,
                'WARNING': 4, 'WARN': 4,
                'NOTICE': 5,
                'INFO': 6,
                'DEBUG': 7,
            }
            severity = severity_map.get(level, 6)
            
            return SyslogMessage(
                timestamp=self._parse_rfc3164_timestamp(groups.get('timestamp', '')),
                hostname=groups.get('hostname', ''),
                app_name=groups.get('module', ''),
                proc_id=None,
                msg_id=None,
                structured_data={'device_type': device_type},
                message=groups.get('message', ''),
                facility=Facility.USER.value,
                severity=severity,
                protocol=SyslogProtocol.UNKNOWN,
                raw=data,
                source_ip='',
                source_port=0,
            )
        
        return self.parse(data)


class SyslogReceiver:
    """
    Syslog接收器
    支持功能:
    - UDP/TCP Syslog接收
    - RFC3164/RFC5424解析
    - 设备识别
    - 日志过滤与转发
    """
    
    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 514,
        protocol: str = 'udp',
        max_packet_size: int = 65535,
        callback: Optional[Callable[[SyslogMessage], None]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化Syslog接收器
        
        Args:
            host: 绑定地址
            port: 绑定端口
            protocol: 协议 ('udp' 或 'tcp')
            max_packet_size: 最大数据包大小
            callback: 消息回调函数
            filters: 过滤器配置
        """
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.max_packet_size = max_packet_size
        self.callback = callback
        self.filters = filters or {}
        
        self.parser = SyslogParser()
        self._running = False
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        
        # 设备识别
        self.device_registry: Dict[str, Dict[str, Any]] = {}
        self._load_device_registry()
    
    def _load_device_registry(self):
        """加载设备注册表"""
        # 常用设备信息
        self.device_registry = {
            'huawei': {
                'patterns': [r' Huawei ', r'%%Huawei', r'SNTP', r'VRP'],
                'default_port': 514,
                'parser': 'huawei',
            },
            'cisco': {
                'patterns': [r'%[A-Z]+-'],  # Cisco style %FACILITY-SEVERITY
                'default_port': 514,
                'parser': 'cisco',
            },
            'juniper': {
                'patterns': [r'Juniper', r'%%Juniper'],
                'default_port': 514,
                'parser': 'generic',
            },
            'fortinet': {
                'patterns': [r'FortiGate', r'date=', r'devname='],
                'default_port': 514,
                'parser': 'security',
            },
            'zabbix': {
                'patterns': [r'<[0-9]+>'],
                'default_port': 10051,
                'parser': 'generic',
            },
        }
    
    def _identify_device(self, message: SyslogMessage) -> Optional[str]:
        """识别设备类型"""
        raw_lower = message.raw.lower()
        
        for device_type, info in self.device_registry.items():
            for pattern in info['patterns']:
                if re.search(pattern, raw_lower, re.IGNORECASE):
                    return device_type
        
        return None
    
    def _match_filter(self, message: SyslogMessage) -> bool:
        """匹配过滤器"""
        if not self.filters:
            return True
        
        # 级别过滤
        if 'levels' in self.filters:
            if message.level not in self.filters['levels']:
                return False
        
        # 设施过滤
        if 'facilities' in self.filters:
            if message.facility_name not in self.filters['facilities']:
                return False
        
        # 主机过滤
        if 'hosts' in self.filters:
            if message.hostname not in self.filters['hosts']:
                return False
        
        # 关键词过滤
        if 'keywords' in self.filters:
            include = True
            if self.filters.get('exclude', False):
                include = False
            
            for keyword in self.filters['keywords']:
                if keyword.lower() in message.message.lower():
                    return include
            
            return not include
        
        return True
    
    def _handle_udp_message(self, data: bytes, addr: Tuple[str, int]):
        """处理UDP消息"""
        try:
            message_str = data.decode('utf-8', errors='replace')
            message = self.parser.parse(message_str, addr[0], addr[1])
            
            if message and self._match_filter(message):
                if self.callback:
                    self.callback(message)
        except Exception as e:
            logger.error(f"Error handling UDP message from {addr}: {e}")
    
    def _handle_tcp_connection(self, client_socket: socket.socket, addr: Tuple[str, int]):
        """处理TCP连接"""
        try:
            # 设置超时
            client_socket.settimeout(60)
            
            buffer = b''
            
            while True:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    
                    buffer += chunk
                    
                    # 处理完整消息（以换行符分隔）
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        message_str = line.decode('utf-8', errors='replace').strip()
                        
                        if message_str:
                            message = self.parser.parse(message_str, addr[0], addr[1])
                            
                            if message and self._match_filter(message):
                                if self.callback:
                                    self.callback(message)
                except socket.timeout:
                    break
        except Exception as e:
            logger.error(f"Error handling TCP connection from {addr}: {e}")
        finally:
            client_socket.close()
    
    def _udp_server(self):
        """UDP服务器"""
        while self._running:
            try:
                self._socket.settimeout(1.0)
                data, addr = self._socket.recvfrom(self.max_packet_size)
                self._handle_udp_message(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.error(f"UDP server error: {e}")
    
    def _tcp_server(self):
        """TCP服务器"""
        while self._running:
            try:
                self._socket.settimeout(1.0)
                client_socket, addr = self._socket.accept()
                
                thread = threading.Thread(
                    target=self._handle_tcp_connection,
                    args=(client_socket, addr),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.error(f"TCP server error: {e}")
    
    def start(self):
        """启动接收器"""
        if self._running:
            return
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM if self.protocol == 'tcp' else socket.SOCK_DGRAM)
        
        # 设置socket选项
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if self.protocol == 'udp':
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
        
        try:
            self._socket.bind((self.host, self.port))
            
            if self.protocol == 'tcp':
                self._socket.listen(128)
            
            self._running = True
            
            self._thread = threading.Thread(
                target=self._udp_server if self.protocol == 'udp' else self._tcp_server,
                daemon=True
            )
            self._thread.start()
            
            logger.info(f"Syslog receiver started on {self.host}:{self.port} ({self.protocol.upper()})")
        except Exception as e:
            self._socket.close()
            raise RuntimeError(f"Failed to start Syslog receiver: {e}")
    
    def stop(self):
        """停止接收器"""
        self._running = False
        
        if self._socket:
            self._socket.close()
        
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info(f"Syslog receiver stopped")
    
    def register_device(self, device_id: str, info: Dict[str, Any]):
        """注册设备"""
        self.device_registry[device_id] = info
    
    def add_filter(self, filter_type: str, value: Any):
        """添加过滤器"""
        self.filters[filter_type] = value
