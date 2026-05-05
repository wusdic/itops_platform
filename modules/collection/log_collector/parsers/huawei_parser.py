"""华为设备日志解析器"""
import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .generic_parser import GenericLogParser, ParsedLog, LogLevel

logger = logging.getLogger(__name__)


class HuaweiLogLevel(Enum):
    """华为设备日志级别"""
    EMERGENCY = 0   # 紧急
    ALERT = 1       # 警戒
    CRITICAL = 2    # 严重
    ERROR = 3       # 错误
    WARNING = 4     # 警告
    NOTICE = 5      # 通知
    INFO = 6        # 信息
    DEBUG = 7       # 调试


@dataclass
class HuaweiLogInfo:
    """华为日志信息"""
    device_type: str       # 设备类型
    module: str            # 模块
    sn: str                # 序列号/会话ID
    vpn_instance: str      # VPN实例
    level: str             # 级别
    message: str           # 消息
    timestamp: datetime    # 时间戳
    raw: str                # 原始消息


class HuaweiLogParser:
    """
    华为设备日志解析器
    支持华为交换机、路由器、防火墙等设备的日志格式
    """
    
    # 华为标准日志格式
    # %@%...%@%device_time %%07ModuleID/SN/Level/Info
    STANDARD_PATTERN = re.compile(
        r'^%(?P<mark>\S+)'
        r'(?P<timestamp>\w{3}\s+\d{1,2},?\s+\d{4}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+'
        r'%%(?P<module>\w+)'
        r'(?:/(?P<sn>\S+))?'
        r'(?:/(?P<vpn>\S+))?'
        r'(?:/(?P<level>\w+))?'
        r'(?::\s*)?(?P<message>.*)$'
    )
    
    # 华为简化格式
    SIMPLE_PATTERN = re.compile(
        r'^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<module>\S+)\s+\d+\s+'
        r'\[(?P<level>\w+)\]\s*'
        r'(?P<message>.*)$'
    )
    
    # 华为信息卡日志格式
    INFO_CARD_PATTERN = re.compile(
        r'^%@'
        r'(?P<device_info>.*?)'
        r'@%(?P<timestamp>\S+\s+\S+\s+\d+:\d+:\d+)\s+'
        r'(?P<module>\w+)'
        r'(?:/(?P<level>\w+))?'
        r'(?::\s*)(?P<message>.*)$'
    )
    
    # VRP系统日志格式
    VRP_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<module>\S+)\s+'
        r'\[(?P<level>\w+)\]\s*'
        r'(?P<sn>\d+)\s+'
        r'(?P<message>.*)$'
    )
    
    # 华为防火墙日志格式
    FIREWALL_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<action>\w+)\s+'
        r'(?P<protocol>\w+)\s+'
        r'(?P<src_ip>\S+)\s*:\s*(?P<src_port>\d+)\s+'
        r'(?P<dst_ip>\S+)\s*:\s*(?P<dst_port>\d+)\s+'
        r'(?P<message>.*)$'
    )
    
    # 级别映射
    LEVEL_MAP = {
        'emerg': HuaweiLogLevel.EMERGENCY,
        'alert': HuaweiLogLevel.ALERT,
        'crit': HuaweiLogLevel.CRITICAL,
        'critical': HuaweiLogLevel.CRITICAL,
        'error': HuaweiLogLevel.ERROR,
        'err': HuaweiLogLevel.ERROR,
        'warning': HuaweiLogLevel.WARNING,
        'warn': HuaweiLogLevel.WARNING,
        'notice': HuaweiLogLevel.NOTICE,
        'info': HuaweiLogLevel.INFO,
        'debug': HuaweiLogLevel.DEBUG,
        'dbg': HuaweiLogLevel.DEBUG,
    }
    
    # 华为设备型号特征
    DEVICE_SIGNATURES = {
        'CE': r'CE\d+',                           # 华为云引擎交换机
        'S5700': r'S5700',                        # 交换机
        'S3700': r'S3700',
        'S2700': r'S2700',
        'AR': r'AR\d+',                            # 路由器
        'NE': r'NE\d+',                            # 运营商路由器
        'USG': r'USG\d+',                         # 防火墙
        'NGFW': r'NGFW\d+',                       # 防火墙
        'AC': r'AC\d+',                            # 无线控制器
        'AP': r'AP\d+',                            # 无线AP
    }
    
    # 模块名称映射
    MODULE_NAMES = {
        'SHELL': '用户界面模块',
        'SNMP': 'SNMP模块',
        'SSH': 'SSH模块',
        'TELNET': 'Telnet模块',
        'FTP': 'FTP模块',
        'TFTP': 'TFTP模块',
        'OSPF': 'OSPF路由协议',
        'BGP': 'BGP路由协议',
        'ISIS': 'ISIS路由协议',
        'RIP': 'RIP路由协议',
        'STP': '生成树协议',
        'VLAN': 'VLAN模块',
        'IFNET': '接口模块',
        'ACL': '访问控制列表',
        'QOS': '服务质量',
        'SEC': '安全模块',
        'IPSEC': 'IPSec模块',
        'SSL': 'SSL模块',
        'SYS': '系统模块',
        'DEV': '设备模块',
        'BOARD': '单板模块',
        'CARD': '卡模块',
        'PFC': '协议转发模块',
    }
    
    def __init__(self):
        self.generic_parser = GenericLogParser()
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """解析时间戳"""
        # 格式: "Jan  1, 2024 12:00:00" 或 "Jan 1, 2024 12:00:00"
        timestamp_str = re.sub(r'\s+', ' ', timestamp_str)
        
        try:
            return datetime.strptime(timestamp_str, '%b %d, %Y %H:%M:%S')
        except ValueError:
            pass
        
        # 格式: "Jan  1 12:00:00"
        try:
            parts = timestamp_str.split()
            if len(parts) >= 3:
                month = parts[0]
                day = parts[1].rstrip(',')
                time_part = parts[2]
                year = datetime.now().year
                
                return datetime.strptime(f"{month} {day} {year} {time_part}", '%b %d %Y %H:%M:%S')
        except ValueError:
            pass
        
        # 格式: "2024-01-01 12:00:00"
        try:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
        
        return datetime.now()
    
    def _parse_level(self, level_str: str) -> str:
        """解析日志级别"""
        if not level_str:
            return 'INFO'
        
        level_lower = level_str.lower()
        
        level_map = {
            'emergency': 'CRITICAL',
            'alert': 'CRITICAL',
            'critical': 'CRITICAL',
            'error': 'ERROR',
            'err': 'ERROR',
            'warning': 'WARNING',
            'warn': 'WARNING',
            'notice': 'INFO',
            'info': 'INFO',
            'debug': 'DEBUG',
            'dbg': 'DEBUG',
        }
        
        return level_map.get(level_lower, 'INFO')
    
    def _identify_device_type(self, raw: str) -> Optional[str]:
        """识别设备类型"""
        for device_type, pattern in self.DEVICE_SIGNATURES.items():
            if re.search(pattern, raw, re.IGNORECASE):
                return device_type
        return None
    
    def _parse_module_name(self, module_code: str) -> str:
        """解析模块名称"""
        return self.MODULE_NAMES.get(module_code.upper(), module_code)
    
    def _parse_standard(self, raw: str) -> Optional[HuaweiLogInfo]:
        """解析华为标准格式"""
        match = self.STANDARD_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return HuaweiLogInfo(
                device_type=self._identify_device_type(raw) or 'Unknown',
                module=self._parse_module_name(groups.get('module', '')),
                sn=groups.get('sn', ''),
                vpn_instance=groups.get('vpn', ''),
                level=self._parse_level(groups.get('level', '')),
                message=groups.get('message', ''),
                timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                raw=raw,
            )
        
        return None
    
    def _parse_simple(self, raw: str) -> Optional[HuaweiLogInfo]:
        """解析华为简化格式"""
        match = self.SIMPLE_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return HuaweiLogInfo(
                device_type=self._identify_device_type(raw) or 'Unknown',
                module=groups.get('module', ''),
                sn='',
                vpn_instance='',
                level=self._parse_level(groups.get('level', '')),
                message=groups.get('message', ''),
                timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                raw=raw,
            )
        
        return None
    
    def _parse_vrp(self, raw: str) -> Optional[HuaweiLogInfo]:
        """解析VRP格式"""
        match = self.VRP_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return HuaweiLogInfo(
                device_type=self._identify_device_type(raw) or 'Unknown',
                module=groups.get('module', ''),
                sn=groups.get('sn', ''),
                vpn_instance='',
                level=self._parse_level(groups.get('level', '')),
                message=groups.get('message', ''),
                timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                raw=raw,
            )
        
        return None
    
    def _parse_firewall(self, raw: str) -> Optional[HuaweiLogInfo]:
        """解析防火墙日志"""
        match = self.FIREWALL_PATTERN.match(raw)
        
        if match:
            groups = match.groupdict()
            
            return HuaweiLogInfo(
                device_type='USG',
                module='FIREWALL',
                sn='',
                vpn_instance='',
                level='INFO',
                message=groups.get('message', ''),
                timestamp=self._parse_timestamp(groups.get('timestamp', '')),
                raw=raw,
            )
        
        return None
    
    def parse(self, raw: str) -> HuaweiLogInfo:
        """
        解析华为设备日志
        
        Args:
            raw: 原始日志行
            
        Returns:
            HuaweiLogInfo: 解析后的日志信息
        """
        raw = raw.strip()
        
        if not raw:
            return HuaweiLogInfo(
                device_type='Unknown',
                module='',
                sn='',
                vpn_instance='',
                level='INFO',
                message='',
                timestamp=datetime.now(),
                raw=raw,
            )
        
        # 按优先级尝试不同格式
        parsed = self._parse_standard(raw)
        if parsed:
            return parsed
        
        parsed = self._parse_simple(raw)
        if parsed:
            return parsed
        
        parsed = self._parse_vrp(raw)
        if parsed:
            return parsed
        
        parsed = self._parse_firewall(raw)
        if parsed:
            return parsed
        
        # 无法识别格式，返回通用解析
        return HuaweiLogInfo(
            device_type=self._identify_device_type(raw) or 'Unknown',
            module='Unknown',
            sn='',
            vpn_instance='',
            level='INFO',
            message=raw,
            timestamp=datetime.now(),
            raw=raw,
        )
    
    def parse_to_generic(self, raw: str) -> ParsedLog:
        """解析并转换为通用格式"""
        huawei_log = self.parse(raw)
        
        return ParsedLog(
            timestamp=huawei_log.timestamp,
            level=huawei_log.level,
            logger_name=f"{huawei_log.device_type}/{huawei_log.module}",
            message=huawei_log.message,
            raw=huawei_log.raw,
            extra={
                'device_type': huawei_log.device_type,
                'module': huawei_log.module,
                'sn': huawei_log.sn,
                'vpn_instance': huawei_log.vpn_instance,
            }
        )
    
    def parse_batch(self, lines: List[str]) -> List[HuaweiLogInfo]:
        """批量解析"""
        return [self.parse(line) for line in lines if line.strip()]
