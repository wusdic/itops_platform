"""安全设备日志解析器"""
import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .generic_parser import GenericLogParser, ParsedLog

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """安全事件类型"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PASSWORD_CHANGED = "password_changed"
    PERMISSION_CHANGED = "permission_changed"
    
    FIREWALL_DROP = "firewall_drop"
    FIREWALL_ACCEPT = "firewall_accept"
    FIREWALL_ALERT = "firewall_alert"
    
    IDS_ALERT = "ids_alert"
    IDS_BLOCK = "ids_block"
    
    VIRUS_DETECTED = "virus_detected"
    MALWARE_BLOCKED = "malware_blocked"
    
    DATA_LEAK = "data_leak"
    SENSITIVE_ACCESS = "sensitive_access"
    
    NETWORK_SCAN = "network_scan"
    DOS_ATTACK = "dos_attack"
    BRUTE_FORCE = "brute_force"
    
    CONFIG_CHANGE = "config_change"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    
    UNKNOWN = "unknown"


@dataclass
class SecurityLogInfo:
    """安全日志信息"""
    event_type: SecurityEventType
    severity: str
    timestamp: datetime
    source_ip: Optional[str]
    source_port: Optional[int]
    dest_ip: Optional[str]
    dest_port: Optional[int]
    protocol: Optional[str]
    username: Optional[str]
    action: str
    message: str
    raw: str
    device_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityLogParser:
    """
    安全设备日志解析器
    支持防火墙、IDS/IPS、WAF等安全设备的日志格式
    """
    
    # 通用安全日志格式
    GENERIC_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<severity>\w+)\s+'
        r'(?P<action>\w+)\s+'
        r'(?:(?P<src_ip>\S+)\s*'
        r'(?::(?P<src_port>\d+))?\s+'
        r'(?P<direction>\w+)\s+'
        r'(?P<dest_ip>\S+)\s*'
        r'(?::(?P<dest_port>\d+))?\s+)?'
        r'(?:(?P<protocol>\w+)\s+)?'
        r'(?P<message>.*)$'
    )
    
    # FortiGate防火墙格式
    FORTIGATE_PATTERN = re.compile(
        r'date=(?P<date>\d{4}-\d{2}-\d{2})\s+'
        r'time=(?P<time>\d{2}:\d{2}:\d{2})\s+'
        r'devname=(?P<devname>\S+)\s+'
        r'devid=(?P<devid>\S+)\s+'
        r'logid=(?P<logid>\d+)\s+'
        r'type=(?P<type>\w+)\s+'
        r'subtype=(?P<subtype>\w+)\s+'
        r'level=(?P<level>\w+)\s+'
        r'(?:vd=(?P<vd>\S+)\s+)?'
        r'(?:srcip=(?P<srcip>\S+)\s+)?'
        r'(?:srcport=(?P<srcport>\d+)\s+)?'
        r'(?:srcintf=(?P<srcintf>\S+)\s+)?'
        r'(?:dstip=(?P<dstip>\S+)\s+)?'
        r'(?:dstport=(?P<dstport>\d+)\s+)?'
        r'(?:dstintf=(?P<dstintf>\S+)\s+)?'
        r'(?:sessionid=(?P<sessionid>\S+)\s+)?'
        r'(?:proto=(?P<proto>\d+)\s+)?'
        r'(?:action=(?P<action>\w+)\s+)?'
        r'(?:policyid=(?P<policyid>\S+)\s+)?'
        r'(?:user=(?P<user>\S+)\s+)?'
        r'(?:msg="(?P<msg>[^"]*)")?'
    )
    
    # Checkpoint格式
    CHECKPOINT_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<action>\w+)\s+'
        r'(?P<severity>\w+)\s+'
        r'(?P<src_ip>\S+)\s*'
        r'(?::(?P<src_port>\d+))?\s+'
        r'(?P<protocol>\w+)\s+'
        r'(?P<dest_ip>\S+)\s*'
        r'(?::(?P<dest_port>\d+))?\s+'
        r'(?P<message>.*)$'
    )
    
    # 华为防火墙格式
    HUAWEI_FW_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<action>\w+)\s+'
        r'(?P<protocol>\w+)\s+'
        r'(?P<src_ip>\S+):(?P<src_port>\d+)\s+'
        r'(?P<dest_ip>\S+):(?P<dest_port>\d+)\s+'
        r'(?P<message>.*)$'
    )
    
    # 天融信防火墙格式
    TOPSEC_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'\[(?P<severity>\w+)\]\s+'
        r'(?P<module>\S+)\s+'
        r'(?P<src_ip>\S+)\s*'
        r'(?::(?P<src_port>\d+))?\s+'
        r'(?P<dest_ip>\S+)\s*'
        r'(?::(?P<dest_port>\d+))?\s+'
        r'(?P<protocol>\S+)\s+'
        r'(?P<action>\w+)\s+'
        r'(?P<message>.*)$'
    )
    
    # 事件类型识别模式
    EVENT_PATTERNS = {
        SecurityEventType.LOGIN_SUCCESS: [
            r'login\s+success',
            r'authentication\s+success',
            r'auth\s+success',
            r'successfully\s+logged\s+in',
            r'user\s+login',
            r'登录成功',
            r'认证成功',
        ],
        SecurityEventType.LOGIN_FAILED: [
            r'login\s+fail',
            r'authentication\s+fail',
            r'auth\s+fail',
            r'invalid\s+password',
            r'login\s+denied',
            r'登录失败',
            r'认证失败',
        ],
        SecurityEventType.ACCOUNT_LOCKED: [
            r'account\s+lock',
            r'user\s+lock',
            r'lockout',
            r'账号锁定',
        ],
        SecurityEventType.FIREWALL_DROP: [
            r'drop',
            r'deny',
            r'reject',
            r'blocked',
            r'discarded',
        ],
        SecurityEventType.FIREWALL_ACCEPT: [
            r'accept',
            r'permit',
            r'allow',
        ],
        SecurityEventType.IDS_ALERT: [
            r'ids\s+alert',
            r'intrusion\s+detect',
            r'attack\s+detect',
            r'signature\s+match',
        ],
        SecurityEventType.VIRUS_DETECTED: [
            r'virus',
            r'malware',
            r'trojan',
            r'恶意代码',
        ],
        SecurityEventType.DOS_ATTACK: [
            r'dos',
            r'ddos',
            r'syn\s+flood',
            r'flood',
            r'distributed',
        ],
        SecurityEventType.BRUTE_FORCE: [
            r'brute\s+force',
            r'password\s+guess',
            r'repeated\s+fail',
        ],
        SecurityEventType.CONFIG_CHANGE: [
            r'config\s+change',
            r'configuration\s+modify',
            r'setting\s+change',
            r'配置变更',
        ],
    }
    
    # 级别映射
    SEVERITY_MAP = {
        'emergency': 'CRITICAL',
        'alert': 'CRITICAL',
        'critical': 'CRITICAL',
        'error': 'ERROR',
        'warning': 'WARNING',
        'notice': 'INFO',
        'info': 'INFO',
        'debug': 'DEBUG',
        'low': 'WARNING',
        'medium': 'WARNING',
        'high': 'ERROR',
        'critical': 'CRITICAL',
    }
    
    # 协议号映射
    PROTOCOL_MAP = {
        '1': 'ICMP',
        '6': 'TCP',
        '17': 'UDP',
        '47': 'GRE',
        '50': 'ESP',
        '51': 'AH',
        '89': 'OSPF',
    }
    
    def __init__(self):
        self.generic_parser = GenericLogParser()
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """解析时间戳"""
        try:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
        
        try:
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            pass
        
        return datetime.now()
    
    def _parse_protocol(self, proto: str) -> str:
        """解析协议"""
        if not proto:
            return 'UNKNOWN'
        
        proto_upper = proto.upper()
        if proto_upper.isdigit():
            return self.PROTOCOL_MAP.get(proto, f'PROTO-{proto}')
        
        return proto_upper
    
    def _identify_event_type(self, message: str) -> SecurityEventType:
        """识别事件类型"""
        message_lower = message.lower()
        
        for event_type, patterns in self.EVENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return event_type
        
        return SecurityEventType.UNKNOWN
    
    def _parse_severity(self, severity_str: str) -> str:
        """解析严重级别"""
        if not severity_str:
            return 'INFO'
        
        severity_lower = severity_str.lower()
        return self.SEVERITY_MAP.get(severity_lower, severity_str.upper())
    
    def _parse_fortigate(self, raw: str) -> Optional[SecurityLogInfo]:
        """解析FortiGate日志"""
        match = self.FORTIGATE_PATTERN.search(raw)
        
        if match:
            groups = match.groupdict()
            
            # 识别事件类型
            subtype = groups.get('subtype', '').lower()
            action = groups.get('action', '').lower()
            
            if 'utm' in subtype or 'virus' in subtype:
                event_type = SecurityEventType.VIRUS_DETECTED
            elif 'attack' in subtype:
                event_type = SecurityEventType.IDS_ALERT
            elif action == 'drop' or action == 'deny':
                event_type = SecurityEventType.FIREWALL_DROP
            elif action == 'accept' or action == 'allow':
                event_type = SecurityEventType.FIREWALL_ACCEPT
            else:
                event_type = SecurityEventType.UNKNOWN
            
            timestamp_str = f"{groups.get('date', '')} {groups.get('time', '')}"
            
            return SecurityLogInfo(
                event_type=event_type,
                severity=self._parse_severity(groups.get('level', '')),
                timestamp=self._parse_timestamp(timestamp_str),
                source_ip=groups.get('srcip'),
                source_port=int(groups.get('srcport')) if groups.get('srcport') else None,
                dest_ip=groups.get('dstip'),
                dest_port=int(groups.get('dstport')) if groups.get('dstport') else None,
                protocol=self._parse_protocol(groups.get('proto', '')),
                username=groups.get('user'),
                action=groups.get('action', ''),
                message=groups.get('msg', ''),
                raw=raw,
                device_type='FortiGate',
                metadata={
                    'devname': groups.get('devname'),
                    'devid': groups.get('devid'),
                    'logid': groups.get('logid'),
                    'vd': groups.get('vd'),
                    'sessionid': groups.get('sessionid'),
                }
            )
        
        return None
    
    def _parse_checkpoint(self, raw: str) -> Optional[SecurityLogInfo]:
        """解析Check Point日志"""
        match = self.CHECKPOINT_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return SecurityLogInfo(
                event_type=self._identify_event_type(groups.get('message', '')),
                severity=self._parse_severity(groups.get('severity', '')),
                timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                source_ip=groups.get('src_ip'),
                source_port=int(groups.get('src_port')) if groups.get('src_port') else None,
                dest_ip=groups.get('dest_ip'),
                dest_port=int(groups.get('dest_port')) if groups.get('dest_port') else None,
                protocol=groups.get('protocol'),
                username=None,
                action=groups.get('action', ''),
                message=groups.get('message', ''),
                raw=raw,
                device_type='CheckPoint',
            )
        
        return None
    
    def _parse_huawei_fw(self, raw: str) -> Optional[SecurityLogInfo]:
        """解析华为防火墙日志"""
        match = self.HUAWEI_FW_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return SecurityLogInfo(
                event_type=self._identify_event_type(groups.get('action', '') + ' ' + groups.get('message', '')),
                severity='INFO',
                timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                source_ip=groups.get('src_ip'),
                source_port=int(groups.get('src_port')) if groups.get('src_port') else None,
                dest_ip=groups.get('dest_ip'),
                dest_port=int(groups.get('dest_port')) if groups.get('dest_port') else None,
                protocol=groups.get('protocol'),
                username=None,
                action=groups.get('action', ''),
                message=groups.get('message', ''),
                raw=raw,
                device_type='HuaweiFW',
            )
        
        return None
    
    def _parse_topsec(self, raw: str) -> Optional[SecurityLogInfo]:
        """解析天融信日志"""
        match = self.TOPSEC_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return SecurityLogInfo(
                event_type=self._identify_event_type(groups.get('action', '') + ' ' + groups.get('message', '')),
                severity=self._parse_severity(groups.get('severity', '')),
                timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                source_ip=groups.get('src_ip'),
                source_port=int(groups.get('src_port')) if groups.get('src_port') else None,
                dest_ip=groups.get('dest_ip'),
                dest_port=int(groups.get('dest_port')) if groups.get('dest_port') else None,
                protocol=groups.get('protocol'),
                username=None,
                action=groups.get('action', ''),
                message=groups.get('message', ''),
                raw=raw,
                device_type='TopSec',
                metadata={
                    'module': groups.get('module'),
                }
            )
        
        return None
    
    def parse(self, raw: str) -> SecurityLogInfo:
        """
        解析安全设备日志
        
        Args:
            raw: 原始日志行
            
        Returns:
            SecurityLogInfo: 解析后的日志信息
        """
        raw = raw.strip()
        
        if not raw:
            return SecurityLogInfo(
                event_type=SecurityEventType.UNKNOWN,
                severity='INFO',
                timestamp=datetime.now(),
                source_ip=None,
                source_port=None,
                dest_ip=None,
                dest_port=None,
                protocol=None,
                username=None,
                action='',
                message='',
                raw=raw,
            )
        
        # 尝试特定厂商格式
        if 'devname=' in raw or 'FortiGate' in raw:
            parsed = self._parse_fortigate(raw)
            if parsed:
                return parsed
        
        parsed = self._parse_checkpoint(raw)
        if parsed:
            return parsed
        
        parsed = self._parse_huawei_fw(raw)
        if parsed:
            return parsed
        
        parsed = self._parse_topsec(raw)
        if parsed:
            return parsed
        
        # 尝试通用格式
        match = self.GENERIC_PATTERN.match(raw)
        if match:
            groups = match.groupdict()
            
            return SecurityLogInfo(
                event_type=self._identify_event_type(groups.get('message', '')),
                severity=self._parse_severity(groups.get('severity', '')),
                timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                source_ip=groups.get('src_ip'),
                source_port=int(groups.get('src_port')) if groups.get('src_port') else None,
                dest_ip=groups.get('dest_ip'),
                dest_port=int(groups.get('dest_port')) if groups.get('dest_port') else None,
                protocol=groups.get('protocol'),
                username=None,
                action=groups.get('action', ''),
                message=groups.get('message', ''),
                raw=raw,
                device_type='Generic',
            )
        
        # 无法识别
        return SecurityLogInfo(
            event_type=self._identify_event_type(raw),
            severity='INFO',
            timestamp=datetime.now(),
            source_ip=None,
            source_port=None,
            dest_ip=None,
            dest_port=None,
            protocol=None,
            username=None,
            action='',
            message=raw,
            raw=raw,
        )
    
    def parse_to_generic(self, raw: str) -> ParsedLog:
        """解析并转换为通用格式"""
        security_log = self.parse(raw)
        
        return ParsedLog(
            timestamp=security_log.timestamp,
            level=security_log.severity,
            logger_name=f"security/{security_log.device_type}",
            message=security_log.message,
            raw=security_log.raw,
            ip_address=security_log.source_ip,
            user_id=security_log.username,
            extra={
                'event_type': security_log.event_type.value,
                'action': security_log.action,
                'source_ip': security_log.source_ip,
                'source_port': security_log.source_port,
                'dest_ip': security_log.dest_ip,
                'dest_port': security_log.dest_port,
                'protocol': security_log.protocol,
                'metadata': security_log.metadata,
            }
        )
    
    def parse_batch(self, lines: List[str]) -> List[SecurityLogInfo]:
        """批量解析"""
        return [self.parse(line) for line in lines if line.strip()]
    
    def filter_by_event_type(
        self,
        logs: List[SecurityLogInfo],
        event_types: List[SecurityEventType],
    ) -> List[SecurityLogInfo]:
        """按事件类型过滤"""
        return [log for log in logs if log.event_type in event_types]
    
    def filter_by_severity(
        self,
        logs: List[SecurityLogInfo],
        min_severity: str = 'INFO',
    ) -> List[SecurityLogInfo]:
        """按严重级别过滤"""
        severity_order = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        try:
            min_index = severity_order.index(min_severity)
        except ValueError:
            min_index = 1
        
        return [
            log for log in logs
            if severity_order.index(log.severity) <= min_index
        ]
