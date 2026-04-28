"""
SNMP客户端
支持SNMP v1/v2c/v3，用于采集网络设备和服务器的监控数据
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum

# 尝试导入pysnmp
try:
    from pysnmp.hlapi import *
    from pysnmp.entity.rfc3413.oneliner import cmdgen
    from pysnmp.proto import rfc1902
    from pysnmp.smi import builder, view
    _pysnmp_available = True
except ImportError:
    _pysnmp_available = False

# 尝试导入easysnmp
try:
    from easysnmp import Session, SNMPVariable
    _easysnmp_available = True
except ImportError:
    _easysnmp_available = False


logger = logging.getLogger(__name__)


class SNMPVersion(str, Enum):
    """SNMP版本枚举"""
    V1 = 'v1'
    V2C = 'v2c'
    V3 = 'v3'


class SNMPClient:
    """
    SNMP客户端
    
    功能特性：
    1. 支持SNMP v1/v2c/v3
    2. 支持Get、Set、Walk、GetNext操作
    3. 支持批量采集
    4. 支持超时和重试配置
    5. 自动重连
    
    使用示例：
    >>> client = SNMPClient(host='192.168.1.1', community='public')
    >>> result = client.get('1.3.6.1.2.1.1.1.0')  # sysDescr
    >>> results = client.walk('1.3.6.1.2.1.2.2.1')  # ifTable
    >>> client.close()
    """
    
    def __init__(self, config: 'SNMPConfig' = None, **kwargs):
        """
        初始化SNMP客户端
        
        Args:
            config: SNMP配置对象
            **kwargs: 直接传入的配置参数
        """
        self._config = config or SNMPConfig(**kwargs)
        self._session = None
        self._mib_view = None
        self._connected = False
        
        if _pysnmp_available:
            self._engine = cmdgen.CommandGenerator()
        elif _easysnmp_available:
            self._session = self._create_easysnmp_session()
        else:
            logger.warning("未安装pysnmp或easysnmp，SNMP功能将不可用")
    
    def _create_easysnmp_session(self):
        """创建easysnmp会话"""
        if self._config.version == SNMPVersion.V3:
            return Session(
                hostname=self._config.host,
                port=self._config.port,
                version=self._config.version.value,
                security_username=self._config.security_name,
                auth_protocol=self._config.auth_protocol,
                auth_password=self._config.auth_password,
                priv_protocol=self._config.priv_protocol,
                priv_password=self._config.priv_password,
                security_level='authPriv',
                timeout=self._config.timeout,
                retries=self._config.retries
            )
        else:
            return Session(
                hostname=self._config.host,
                port=self._config.port,
                version=self._config.version.value,
                community=self._config.community,
                timeout=self._config.timeout,
                retries=self._config.retries
            )
    
    def connect(self) -> bool:
        """
        建立SNMP连接
        
        Returns:
            连接是否成功
        """
        try:
            # 测试连接 - 获取sysDescr
            result = self.get('1.3.6.1.2.1.1.1.0')
            self._connected = result is not None
            if self._connected:
                logger.info(f"SNMP连接成功: {self._config.host}:{self._config.port}")
            return self._connected
        except Exception as e:
            logger.error(f"SNMP连接失败: {self._config.host}:{self._config.port} - {e}")
            self._connected = False
            return False
    
    def get(self, oid: str) -> Optional[Any]:
        """
        SNMP Get操作
        
        Args:
            oid: OID或MIB名称
        
        Returns:
            获取的值，失败返回None
        """
        if _easysnmp_available and self._session:
            return self._easysnmp_get(oid)
        elif _pysnmp_available:
            return self._pysnmp_get(oid)
        else:
            logger.error("无可用的SNMP库")
            return None
    
    def _easysnmp_get(self, oid: str) -> Optional[Any]:
        """使用easysnmp执行get"""
        try:
            result = self._session.get(oid)
            if result and result.value != 'NOSUCHOBJECT':
                return self._convert_value(result)
            return None
        except Exception as e:
            logger.debug(f"SNMP Get失败 [{oid}]: {e}")
            return None
    
    def _pysnmp_get(self, oid: str) -> Optional[Any]:
        """使用pysnmp执行get"""
        try:
            # 解析OID
            oid = self._resolve_oid(oid)
            
            if self._config.version == SNMPVersion.V3:
                auth = UsmUserData(
                    self._config.security_name,
                    self._config.auth_password,
                    self._config.priv_password,
                    authProtocol=self._get_auth_protocol(),
                    privProtocol=self._get_priv_protocol()
                )
            else:
                auth = CommunityData(self._config.community, mpModel=1)
            
            target = UdpTransportTarget(
                (self._config.host, self._config.port),
                timeout=self._config.timeout,
                retries=self._config.retries
            )
            
            error_indication, error_status, error_index, var_binds = next(
                getCmd(self._engine.snmpEngine, auth, target, ContextData(), ObjectType(ObjectIdentity(oid)))
            )
            
            if error_indication:
                logger.debug(f"SNMP Get错误: {error_indication}")
                return None
            
            if var_binds:
                return self._parse_snmp_value(var_binds[0][1])
            
            return None
        except Exception as e:
            logger.debug(f"SNMP Get失败 [{oid}]: {e}")
            return None
    
    def walk(self, oid: str = '1.3.6.1') -> List[Dict[str, Any]]:
        """
        SNMP Walk操作
        
        Args:
            oid: 起始OID
        
        Returns:
            [(oid, value), ...] 列表
        """
        if _easysnmp_available and self._session:
            return self._easysnmp_walk(oid)
        elif _pysnmp_available:
            return self._pysnmp_walk(oid)
        else:
            logger.error("无可用的SNMP库")
            return []
    
    def _easysnmp_walk(self, oid: str) -> List[Dict[str, Any]]:
        """使用easysnmp执行walk"""
        results = []
        try:
            for var in self._session.walk(oid):
                value = self._convert_value(var)
                if value is not None:
                    results.append({
                        'oid': var.oid,
                        'oid_text': var.oid_index,
                        'value': value
                    })
        except Exception as e:
            logger.debug(f"SNMP Walk失败 [{oid}]: {e}")
        return results
    
    def _pysnmp_walk(self, oid: str) -> List[Dict[str, Any]]:
        """使用pysnmp执行walk"""
        results = []
        try:
            oid = self._resolve_oid(oid)
            
            if self._config.version == SNMPVersion.V3:
                auth = UsmUserData(
                    self._config.security_name,
                    self._config.auth_password,
                    self._config.priv_password
                )
            else:
                auth = CommunityData(self._config.community, mpModel=1)
            
            target = UdpTransportTarget(
                (self._config.host, self._config.port),
                timeout=self._config.timeout,
                retries=self._config.retries
            )
            
            error_indication, error_status, error_index, var_bind_table = next(
                nextCmd(self._engine.snmpEngine, auth, target, ContextData(), ObjectType(ObjectIdentity(oid)), lexicographicMode=False)
            )
            
            if error_indication:
                logger.debug(f"SNMP Walk错误: {error_indication}")
                return results
            
            for var_bind in var_bind_table:
                oid_str = var_bind[0].prettyPrint()
                value = self._parse_snmp_value(var_bind[1])
                results.append({
                    'oid': oid_str,
                    'value': value
                })
            
        except Exception as e:
            logger.debug(f"SNMP Walk失败 [{oid}]: {e}")
        return results
    
    def get_bulk(self, oids: List[str], bulk_count: int = 10) -> Dict[str, Any]:
        """
        批量获取多个OID的值
        
        Args:
            oids: OID列表
            bulk_count: 每个OID获取的数量
        
        Returns:
            {oid: value} 字典
        """
        results = {}
        for oid in oids:
            value = self.get(oid)
            if value is not None:
                results[oid] = value
        return results
    
    def _resolve_oid(self, oid: str) -> str:
        """解析MIB名称为OID"""
        # 如果已经是OID格式，直接返回
        if oid.startswith('1.3.6.1') or oid.startswith('.'):
            return oid.lstrip('.')
        return oid
    
    def _convert_value(self, var) -> Any:
        """转换easysnmp值为Python类型"""
        try:
            if hasattr(var, 'value'):
                value = var.value
                if value in ('NOSUCHOBJECT', 'NOSUCHINSTANCE', 'ENDOFMIBVIEW', None):
                    return None
                # 尝试转换为适当类型
                if value.isdigit():
                    return int(value)
                try:
                    return float(value)
                except ValueError:
                    return value
            return None
        except Exception:
            return None
    
    def _parse_snmp_value(self, value) -> Any:
        """解析pysnmp值为Python类型"""
        try:
            if isinstance(value, rfc1902.Integer32):
                return int(value)
            elif isinstance(value, (rfc1902.Counter32, rfc1902.Counter64, rfc1902.Gauge32, rfc1902.Unsigned32)):
                return int(value)
            elif isinstance(value, rfc1902.OctetString):
                return str(value)
            else:
                return str(value)
        except Exception:
            return str(value)
    
    def _get_auth_protocol(self) -> Any:
        """获取认证协议"""
        auth_map = {
            'MD5': usmHMACMD5AuthProtocol,
            'SHA': usmHMACSHAAuthProtocol,
            'SHA256': usmHMAC128SHA224AuthProtocol,
            'SHA384': usmHMAC192SHA384AuthProtocol,
            'SHA512': usmHMAC256SHA384AuthProtocol
        }
        return auth_map.get(self._config.auth_protocol.upper(), usmHMACMD5AuthProtocol)
    
    def _get_priv_protocol(self) -> Any:
        """获取加密协议"""
        priv_map = {
            'DES': usmDESPrivProtocol,
            'AES': usmAESPrivProtocol,
            'AES128': usmAES128PrivProtocol,
            'AES192': usmAES192PrivProtocol,
            'AES256': usmAES256PrivProtocol
        }
        return priv_map.get(self._config.priv_protocol.upper(), usmAESPrivProtocol)
    
    def close(self):
        """关闭连接"""
        self._connected = False
        self._session = None
        logger.debug(f"SNMP连接已关闭: {self._config.host}")


@dataclass
class SNMPConfig:
    """SNMP配置类"""
    host: str = 'localhost'
    port: int = 161
    version: SNMPVersion = SNMPVersion.V2C
    community: str = 'public'
    
    # SNMP v3配置
    security_name: str = ''
    auth_protocol: str = 'MD5'  # MD5, SHA, SHA256, SHA384, SHA512
    auth_password: str = ''
    priv_protocol: str = 'AES'  # DES, AES, AES128, AES192, AES256
    priv_password: str = ''
    
    # 连接配置
    timeout: int = 5  # 秒
    retries: int = 3
    max_repetitions: int = 50
    
    def __post_init__(self):
        if isinstance(self.version, str):
            self.version = SNMPVersion(self.version)


class SNMPDevice:
    """
    SNMP设备采集器
    
    用于采集特定类型设备的标准MIB数据
    """
    
    # 常用MIB OID定义
    MIB_SYSTEM = '1.3.6.1.2.1.1'           # system组
    MIB_INTERFACES = '1.3.6.1.2.1.2'       # interfaces组
    MIB_IFXTABLE = '1.3.6.1.2.1.31'        # ifXTable (64位计数器)
    MIB_TCP = '1.3.6.1.2.1.6'              # TCP组
    MIB_UDP = '1.3.6.1.2.1.7'              # UDP组
    MIB_IP = '1.3.6.1.2.1.4'               # IP组
    MIB_HOST_RESOURCES = '1.3.6.1.2.1.25'  # Host Resources
    MIB_SNMP = '1.3.6.1.2.1.11'            # SNMP组
    
    # 常用OID
    OID_SYS_DESCR = '1.3.6.1.2.1.1.1.0'
    OID_SYS_UPTIME = '1.3.6.1.2.1.1.3.0'
    OID_SYS_CONTACT = '1.3.6.1.2.1.1.4.0'
    OID_SYS_NAME = '1.3.6.1.2.1.1.5.0'
    OID_SYS_LOCATION = '1.3.6.1.2.1.1.6.0'
    OID_SYS_SERVICES = '1.3.6.1.2.1.1.7.0'
    
    def __init__(self, config: SNMPConfig):
        self._config = config
        self._client = SNMPClient(config)
    
    def collect_all(self) -> Dict[str, Any]:
        """
        采集设备所有标准数据
        
        Returns:
            采集的指标数据字典
        """
        data = {
            'host': self._config.host,
            'timestamp': None,
            'system': self.collect_system(),
            'interfaces': self.collect_interfaces(),
            'cpu': self.collect_cpu(),
            'memory': self.collect_memory(),
            'disk': self.collect_disk()
        }
        return data
    
    def collect_system(self) -> Dict[str, Any]:
        """采集系统信息"""
        system_oids = {
            'sysDescr': self.OID_SYS_DESCR,
            'sysUptime': self.OID_SYS_UPTIME,
            'sysContact': self.OID_SYS_CONTACT,
            'sysName': self.OID_SYS_NAME,
            'sysLocation': self.OID_SYS_LOCATION,
            'sysServices': self.OID_SYS_SERVICES
        }
        
        results = {}
        for key, oid in system_oids.items():
            value = self._client.get(oid)
            results[key] = value
        
        return results
    
    def collect_interfaces(self) -> List[Dict[str, Any]]:
        """采集网络接口信息"""
        interfaces = []
        
        # 获取接口数量
        if_count = self._client.get('1.3.6.1.2.1.2.1.0')
        if not if_count:
            return interfaces
        
        # 遍历每个接口
        for i in range(1, int(if_count) + 1):
            interface = {
                'index': i,
                'ifDescr': self._client.get(f'1.3.6.1.2.1.2.2.1.2.{i}'),
                'ifType': self._client.get(f'1.3.6.1.2.1.2.2.1.3.{i}'),
                'ifSpeed': self._client.get(f'1.3.6.1.2.1.2.2.1.5.{i}'),
                'ifOperStatus': self._client.get(f'1.3.6.1.2.1.2.2.1.8.{i}'),
                'ifInOctets': self._client.get(f'1.3.6.1.2.1.2.2.1.10.{i}'),
                'ifOutOctets': self._client.get(f'1.3.6.1.2.1.2.2.1.16.{i}'),
                'ifInErrors': self._client.get(f'1.3.6.1.2.1.2.2.1.14.{i}'),
                'ifOutErrors': self._client.get(f'1.3.6.1.2.1.2.2.1.20.{i}')
            }
            interfaces.append(interface)
        
        return interfaces
    
    def collect_cpu(self) -> Optional[Dict[str, Any]]:
        """采集CPU信息"""
        # 尝试多个可能的CPU OID
        cpu_oids = [
            '1.3.6.1.4.1.2021.11.9.0',    # UCD-SNMP-MIB::ssCpuUser
            '1.3.6.1.4.1.9.2.1.58.0',     # Cisco CPU
            '1.3.6.1.4.1.231.2.10.2.2.1.5.0'  # Sun CPU
        ]
        
        for oid in cpu_oids:
            value = self._client.get(oid)
            if value is not None:
                return {'usage': value, 'oid': oid}
        
        return None
    
    def collect_memory(self) -> Optional[Dict[str, Any]]:
        """采集内存信息"""
        memory_oids = {
            'total': '1.3.6.1.4.1.2021.4.5.0',      # UCD-SNMP-MIB::memTotalReal
            'avail': '1.3.6.1.4.1.2021.4.6.0',      # UCD-SNMP-MIB::memAvailReal
            'used': '1.3.6.1.4.1.2021.4.11.0'       # UCD-SNMP-MIB::memTotalReal - memAvailReal
        }
        
        data = {}
        for key, oid in memory_oids.items():
            data[key] = self._client.get(oid)
        
        if data.get('total'):
            data['usage_percent'] = ((data.get('total', 0) - data.get('avail', 0)) / data.get('total', 1)) * 100
        
        return data if data.get('total') else None
    
    def collect_disk(self) -> List[Dict[str, Any]]:
        """采集磁盘信息"""
        disks = []
        
        # 获取磁盘数量
        disk_num = self._client.get('1.3.6.1.4.1.2021.9.1.1.0')
        if not disk_num:
            return disks
        
        for i in range(1, int(disk_num) + 1):
            disk = {
                'index': i,
                'path': self._client.get(f'1.3.6.1.4.1.2021.9.1.2.{i}'),
                'total': self._client.get(f'1.3.6.1.4.1.2021.9.1.9.{i}'),  # dskTotal
                'avail': self._client.get(f'1.3.6.1.4.1.2021.9.1.4.{i}'),  # dskAvail
                'used_percent': self._client.get(f'1.3.6.1.4.1.2021.9.1.10.{i}')  # dskPercent
            }
            disks.append(disk)
        
        return disks
    
    def close(self):
        """关闭"""
        self._client.close()