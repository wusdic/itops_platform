"""
SNMP采集模块 (CM-01)
ITOps Intelligence Platform - Collection Layer

功能：
- SNMP v1/v2c/v3 支持
- 设备自动发现
- MIB解析和转换
- Trap接收和处理

依赖：FM-01 配置管理模块, FM-02 日志管理模块

作者：ITOps Platform Team
版本：1.0.0
"""

from .snmp_client import SNMPClient, SNMPConfig
from .mib_parser import MIBParser, MIBRegistry, OIDResolver
from .trap_receiver import TrapReceiver, TrapHandler

__all__ = [
    'SNMPClient',
    'SNMPConfig',
    'MIBParser',
    'MIBRegistry',
    'OIDResolver',
    'TrapReceiver',
    'TrapHandler'
]

__version__ = '1.0.0'