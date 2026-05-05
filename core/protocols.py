# -*- coding: utf-8 -*-
"""
核心协议类型定义

统一管理所有支持的采集协议类型
被 modules/collection/adapter_registry.py 和 modules/collection/collector_factory.py 共用
"""

from enum import Enum


class ProtocolType(str, Enum):
    """
    支持的采集协议类型
    
    统一枚举定义，避免在多个模块中重复定义
    """
    SNMP = "snmp"
    SSH = "ssh"
    HTTP = "http"
    WINRM = "winrm"
    IPMI = "ipmi"
    KUBERNETES = "kubernetes"
    DOCKER = "docker"
    ZABBIX = "zabbix"
    PROMETHEUS = "prometheus"
    REDFISH = "redfish"
    WBEM = "wbem"
    SNMP_V1 = "snmp_v1"
    SNMP_V2C = "snmp_v2c"
    SNMP_V3 = "snmp_v3"
    TELNET = "telnet"
    JMX = "jmx"


class DeviceCategory(str, Enum):
    """设备分类"""
    SERVER = "server"
    NETWORK = "network"
    SECURITY = "security"
    STORAGE = "storage"
    VIRTUAL = "virtual"
    CONTAINER = "container"
    MONITOR = "monitor"
    CLOUD = "cloud"


class MetricType(str, Enum):
    """指标类型"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    TEMPERATURE = "temperature"
    POWER = "power"
    FAN = "fan"
    VOLTAGE = "voltage"
    SESSION = "session"
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"


# 协议默认端口映射
PROTOCOL_DEFAULT_PORTS = {
    ProtocolType.SNMP: 161,
    ProtocolType.SNMP_V1: 161,
    ProtocolType.SNMP_V2C: 161,
    ProtocolType.SNMP_V3: 161,
    ProtocolType.SSH: 22,
    ProtocolType.TELNET: 23,
    ProtocolType.HTTP: 80,
    ProtocolType.WINRM: 5985,
    ProtocolType.IPMI: 623,
    ProtocolType.KUBERNETES: 6443,
    ProtocolType.DOCKER: 2375,
    ProtocolType.ZABBIX: 80,
    ProtocolType.PROMETHEUS: 9090,
    ProtocolType.REDFISH: 443,
    ProtocolType.WBEM: 5988,
    ProtocolType.JMX: 9999,
}


def get_protocol_default_port(protocol: ProtocolType) -> int:
    """获取协议的默认端口"""
    return PROTOCOL_DEFAULT_PORTS.get(protocol, 0)


def parse_protocol(protocol_str: str) -> ProtocolType:
    """
    将字符串解析为ProtocolType
    
    Args:
        protocol_str: 协议字符串 (如 'snmp', 'snmp_v2c', 'SSH')
        
    Returns:
        ProtocolType枚举
        
    Raises:
        ValueError: 未知协议类型
    """
    protocol_str = protocol_str.lower().strip()
    
    # 尝试直接匹配
    for pt in ProtocolType:
        if pt.value == protocol_str:
            return pt
    
    # 处理别名
    aliases = {
        'snmpv1': ProtocolType.SNMP_V1,
        'snmpv2': ProtocolType.SNMP_V2C,
        'snmpv2c': ProtocolType.SNMP_V2C,
        'snmpv3': ProtocolType.SNMP_V3,
        'winrm': ProtocolType.WINRM,
        'k8s': ProtocolType.KUBERNETES,
    }
    
    if protocol_str in aliases:
        return aliases[protocol_str]
    
    raise ValueError(f"未知协议类型: {protocol_str}")
