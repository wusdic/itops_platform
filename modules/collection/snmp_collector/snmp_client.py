"""
SNMP客户端
支持SNMP v1/v2c/v3，用于采集网络设备和服务器的监控数据
增强版本：增加异步支持、更多厂商MIB OID、批量操作优化
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading

# 尝试导入pysnmp
try:
    from pysnmp.hlapi.v1arch.asyncio import *
    from pysnmp.proto import rfc1902
    from pysnmp.smi import builder, view
    # 注意: asyncio carrier需要asyncio.coroutine (Python 3.10及之前)
    # Python 3.11+已移除该特性，因此不导入asyncio相关模块
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
    
    # 异步配置
    use_async: bool = False
    
    def __post_init__(self):
        if isinstance(self.version, str):
            self.version = SNMPVersion(self.version)


class VendorMIBMapper:
    """
    厂商MIB OID映射器
    支持多厂商设备的特定MIB OID
    """
    
    # 厂商标识 - 用于自动识别设备厂商
    VENDOR_OIDS = {
        'cisco': '1.3.6.1.4.1.9',        # Cisco
        'juniper': '1.3.6.1.4.1.2636',   # Juniper
        'huawei': '1.3.6.1.4.1.2011',    # Huawei
        'h3c': '1.3.6.1.4.1.25506',      # H3C/HP
        'arista': '1.3.6.1.4.1.30065',   # Arista
        'dell': '1.3.6.1.4.1.674',       # Dell
        'hp': '1.3.6.1.4.1.11',          # HP/Aruba
        'lenovo': '1.3.6.1.4.1.2',       # Lenovo
        'inspur': '1.3.6.1.4.1.111',     # Inspur
        'neokylin': '1.3.6.1.4.1.489',   # 麒麟
        'topsec': '1.3.6.1.4.1.629',     # 天融信
        'nsfocus': '1.3.6.1.4.1.8013',   # 绿盟
        'venustech': '1.3.6.1.4.1.25582', # 启明星辰
        'sangfor': '1.3.6.1.4.1.20992',  # 深信服
        'fortinet': '1.3.6.1.4.1.12356', # Fortinet
        'checkpoint': '1.3.6.1.4.1.262',  # CheckPoint
        'ubiquiti': '1.3.6.1.4.1.41112', # Ubiquiti
        'mikrotik': '1.3.6.1.4.1.14988', # MikroTik
        'aruba': '1.3.6.1.4.1.14823',    # Aruba
        'raspberry': '1.3.6.1.4.1.8072', # Raspberry Pi
    }
    
    # Cisco MIB OID
    CISCO_OIDS = {
        # CPU
        'cisco_cpu_5min': '1.3.6.1.4.1.9.2.1.58.0',     # Cisco IOS CPU 5min
        'cisco_cpu_1min': '1.3.6.1.4.1.9.2.1.57.0',     # Cisco IOS CPU 1min
        'cisco_cpu_5sec': '1.3.6.1.4.1.9.2.1.56.0',     # Cisco IOS CPU 5sec
        'cisco_memory_used': '1.3.6.1.4.1.9.2.1.8.0',    # Cisco IOS Memory Used
        'cisco_memory_free': '1.3.6.1.4.1.9.2.1.9.0',    # Cisco IOS Memory Free
        # 接口
        'cisco_ifinoctets': '1.3.6.1.4.1.9.2.2.1.1.10',  # ifInOctets
        'cisco_ifoutoctets': '1.3.6.1.4.1.9.2.2.1.1.16', # ifOutOctets
        # VLAN
        'cisco_vlan_table': '1.3.6.1.4.1.9.9.46.1.3.1', # VTP VLAN
        # CDP
        'cisco_cdp_cache': '1.3.6.1.4.1.9.9.23.1.2.1',  # CDP Cache
    }
    
    # Huawei MIB OID
    HUAWEI_OIDS = {
        # CPU
        'hw_cpu_usage': '1.3.6.1.4.1.2011.2.23.1.15.0',  # Huawei CPU Usage
        'hw_cpu_5min': '1.3.6.1.4.1.2011.5.25.31.1.1.1.5', # Huawei CPU 5min
        # 内存
        'hw_mem_used': '1.3.6.1.4.1.2011.2.23.1.6.0',   # Huawei Memory Used
        'hw_mem_free': '1.3.6.1.4.1.2011.2.23.1.7.0',   # Huawei Memory Free
        # 接口
        'hw_ifinoctets': '1.3.6.1.4.1.2011.5.25.41.1.5', # ifInOctets
        'hw_ifoutoctets': '1.3.6.1.4.1.2011.5.25.41.1.6', # ifOutOctets
        # 电源/风扇
        'hw_power_status': '1.3.6.1.4.1.2011.5.25.47.1.1.1', # Power Status
        'hw_fan_status': '1.3.6.1.4.1.2011.5.25.47.1.2.1',  # Fan Status
        # VLAN
        'hw_vlan_table': '1.3.6.1.4.1.2011.5.25.123.1.3', # VLAN Table
    }
    
    # Juniper MIB OID
    JUNIPER_OIDS = {
        # CPU
        'jnx_cpu_usage': '1.3.6.1.4.1.2636.3.1.13.0',   # Juniper CPU Usage
        # 内存
        'jnx_mem_used': '1.3.6.1.4.1.2636.3.1.13.0',    # Juniper Memory
        # 接口
        'jnx_ifinoctets': '1.3.6.1.4.1.2636.3.1.7.1',   # ifInOctets
        'jnx_ifoutoctets': '1.3.6.1.4.1.2636.3.1.7.1',  # ifOutOctets
    }
    
    # HPE/Aruba MIB OID
    HPE_OIDS = {
        # CPU
        'hpe_cpu_usage': '1.3.6.1.4.1.11.2.14.11.5.1.1',  # HP CPU
        # 内存
        'hpe_mem_used': '1.3.6.1.4.1.11.2.14.11.5.1.2', # HP Memory
        # 电源
        'hpe_power_status': '1.3.6.1.4.1.11.2.14.11.5.2', # HP Power
        # 风扇
        'hpe_fan_status': '1.3.6.1.4.1.11.2.14.11.5.3',  # HP Fan
    }
    
    # Dell MIB OID
    DELL_OIDS = {
        # CPU
        'dell_cpu_status': '1.3.6.1.4.1.674.10892.1.200.10.1', # Dell CPU Status
        # 内存
        'dell_mem_status': '1.3.6.1.4.1.674.10892.1.200.20.1', # Dell Memory Status
        # 电源
        'dell_power_status': '1.3.6.1.4.1.674.10892.1.200.10.1', # Dell Power
        # 风扇
        'dell_fan_status': '1.3.6.1.4.1.674.10892.1.200.30.1', # Dell Fan
        # 温度
        'dell_temp_status': '1.3.6.1.4.1.674.10892.1.200.40.1', # Dell Temperature
        # 电压
        'dell_voltage_status': '1.3.6.1.4.1.674.10892.1.200.50.1', # Dell Voltage
        # 电池
        'dell_battery_status': '1.3.6.1.4.1.674.10892.1.200.60.1', # Dell Battery
    }
    
    # H3C MIB OID
    H3C_OIDS = {
        # CPU
        'h3c_cpu_usage': '1.3.6.1.4.1.25506.2.6.1.1',   # H3C CPU Usage
        # 内存
        'h3c_mem_used': '1.3.6.1.4.1.25506.2.6.1.2',    # H3C Memory Used
        'h3c_mem_free': '1.3.6.1.4.1.25506.2.6.1.3',    # H3C Memory Free
        # 接口
        'h3c_ifinoctets': '1.3.6.1.4.1.25506.4.3.1',   # H3C ifInOctets
        'h3c_ifoutoctets': '1.3.6.1.4.1.25506.4.3.2',   # H3C ifOutOctets
        # VLAN
        'h3c_vlan_table': '1.3.6.1.4.1.25506.2.23.1',   # H3C VLAN
    }
    
    # 通用主机资源 MIB
    HOST_RESOURCE_OIDS = {
        'hr_sw_run_index': '1.3.6.1.2.1.25.1.1',       # hrSWRunIndex
        'hr_sw_run_name': '1.3.6.1.2.1.25.1.2',        # hrSWRunName
        'hr_sw_run_type': '1.3.6.1.2.1.25.1.3',         # hrSWRunType
        'hr_sw_run_status': '1.3.6.1.2.1.25.1.4',      # hrSWRunStatus
        'hr_storage_index': '1.3.6.1.2.1.25.2.3.1.1',  # hrStorageIndex
        'hr_storage_type': '1.3.6.1.2.1.25.2.3.1.2',    # hrStorageType
        'hr_storage_descr': '1.3.6.1.2.1.25.2.3.1.3',   # hrStorageDescr
        'hr_storage_units': '1.3.6.1.2.1.25.2.3.1.4',   # hrStorageUnits
        'hr_storage_size': '1.3.6.1.2.1.25.2.3.1.5',    # hrStorageSize
        'hr_storage_used': '1.3.6.1.2.1.25.2.3.1.6',    # hrStorageUsed
    }
    
    # UCD-SNMP-MIB (Linux/Unix通用)
    UCD_SNMP_OIDS = {
        'ss_cpu_user': '1.3.6.1.4.1.2021.11.9.0',      # ssCpuUser
        'ss_cpu_system': '1.3.6.1.4.1.2021.11.10.0',    # ssCpuSystem
        'ss_cpu_idle': '1.3.6.1.4.1.2021.11.11.0',      # ssCpuIdle
        'ss_cpu_raw_user': '1.3.6.1.4.1.2021.11.50.0',  # ssCpuRawUser
        'ss_cpu_raw_system': '1.3.6.1.4.1.2021.11.52.0', # ssCpuRawSystem
        'ss_cpu_raw_idle': '1.3.6.1.4.1.2021.11.53.0',  # ssCpuRawIdle
        'mem_total_real': '1.3.6.1.4.1.2021.4.5.0',     # memTotalReal
        'mem_avail_real': '1.3.6.1.4.1.2021.4.6.0',     # memAvailReal
        'mem_total_swap': '1.3.6.1.4.1.2021.4.4.0',    # memTotalSwap
        'mem_avail_swap': '1.3.6.1.4.1.2021.4.5.0',    # memAvailSwap
        'dsk_total': '1.3.6.1.4.1.2021.9.1.9',          # dskTotal
        'dsk_avail': '1.3.6.1.4.1.2021.9.1.4',         # dskAvail
        'dsk_used': '1.3.6.1.4.1.2021.9.1.8',          # dskUsed
        'dsk_percent': '1.3.6.1.4.1.2021.9.1.10',       # dskPercent
        'load_1min': '1.3.6.1.4.1.2021.10.1.3.1',      # laLoad.1
        'load_5min': '1.3.6.1.4.1.2021.10.1.3.2',      # laLoad.2
        'load_15min': '1.3.6.1.4.1.2021.10.1.3.3',     # laLoad.3
    }
    
    # 网卡流量统计 MIB (64位计数器，ifXTable)
    IFX_OIDS = {
        'if_name': '1.3.6.1.2.1.31.1.1.1.1',            # ifName
        'if_in_multicast_pkts': '1.3.6.1.2.1.31.1.1.1.2', # ifInMulticastPkts
        'if_in_broadcast_pkts': '1.3.6.1.2.1.31.1.1.1.3', # ifInBroadcastPkts
        'if_out_multicast_pkts': '1.3.6.1.2.1.31.1.1.1.4', # ifOutMulticastPkts
        'if_out_broadcast_pkts': '1.3.6.1.2.1.31.1.1.1.5', # ifOutBroadcastPkts
        'if_inoctets': '1.3.6.1.2.1.31.1.1.1.6',       # ifInOctets (64-bit)
        'if_outoctets': '1.3.6.1.2.1.31.1.1.1.10',     # ifOutOctets (64-bit)
        'if_inucastpkts': '1.3.6.1.2.1.31.1.1.1.7',   # ifInUcastPkts (64-bit)
        'if_outucastpkts': '1.3.6.1.2.1.31.1.1.1.11', # ifOutUcastPkts (64-bit)
        'if_inerrors': '1.3.6.1.2.1.31.1.1.1.15',      # ifInErrors (64-bit)
        'if_outerrors': '1.3.6.1.2.1.31.1.1.1.17',     # ifOutErrors (64-bit)
        'if_speed': '1.3.6.1.2.1.31.1.1.1.15',         # ifSpeed
        'if_high_speed': '1.3.6.1.2.1.31.1.1.1.15',    # ifHighSpeed (Mbps)
    }
    
    @classmethod
    def detect_vendor(cls, sys_descr: str) -> Optional[str]:
        """
        根据sysDescr自动识别厂商
        
        Args:
            sys_descr: 系统描述字符串
            
        Returns:
            厂商标识符
        """
        if not sys_descr:
            return None
            
        sys_descr_lower = sys_descr.lower()
        
        vendor_keywords = {
            'cisco': ['cisco', 'ios-xe', 'nx-os', 'ios'],
            'juniper': ['juniper', 'junos', 'screenos'],
            'huawei': ['huawei', 'vrp', 'acoplus'],
            'h3c': ['h3c', 'comware', 'hp networking'],
            'arista': ['arista', 'eos'],
            'dell': ['dell', 'powerconnect', 'force10'],
            'hp': ['hp ', 'hewlett', 'procurve', 'aruba'],
            'lenovo': ['lenovo', 'thinkpad', 'thinkserver'],
            'inspur': ['inspur', 'haniya'],
            'neokylin': ['kylin', 'kylinos', 'neokylin'],
            'topsec': ['topsec', 'tos'],
            'nsfocus': ['nsfocus', '绿盟'],
            'venustech': ['venustech', '启明'],
            'sangfor': ['sangfor', '深信服', 'af'],
            'fortinet': ['fortinet', 'fortigate', 'fortios'],
            'checkpoint': ['checkpoint', 'gaia', 'snut'],
            'ubiquiti': ['ubiquiti', 'unifi', 'edgemax'],
            'mikrotik': ['mikrotik', 'routeros'],
            'aruba': ['aruba', 'instant'],
            'linux': ['linux', 'ubuntu', 'centos', 'red hat', 'debian', 'suse'],
            'windows': ['windows', 'microsoft'],
            'vmware': ['vmware', 'esxi', 'esx'],
        }
        
        for vendor, keywords in vendor_keywords.items():
            for keyword in keywords:
                if keyword in sys_descr_lower:
                    return vendor
        
        return None
    
    @classmethod
    def get_vendor_oids(cls, vendor: str) -> Dict[str, str]:
        """获取指定厂商的MIB OID映射"""
        vendor_map = {
            'cisco': cls.CISCO_OIDS,
            'juniper': cls.JUNIPER_OIDS,
            'huawei': cls.HUAWEI_OIDS,
            'h3c': cls.H3C_OIDS,
            'hp': cls.HPE_OIDS,
            'dell': cls.DELL_OIDS,
        }
        return vendor_map.get(vendor, {})


class AsyncSNMPClient:
    """
    异步SNMP客户端
    支持异步Get、Walk、批量操作
    """
    
    def __init__(self, config: SNMPConfig):
        self._config = config
        self._engine = None
        self._transport = None
        self._connected = False
        
    async def get(self, oid: str) -> Optional[Any]:
        """异步SNMP Get"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get, oid)
    
    def _sync_get(self, oid: str) -> Optional[Any]:
        """同步执行SNMP Get"""
        try:
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
            
            oid = self._resolve_oid(oid)
            
            async def _async_get():
                snmp_dispatcher = SnmpDispatcher()
                transport = await UdpTransportTarget.create(
                    (self._config.host, self._config.port),
                    timeout=self._config.timeout,
                    retries=self._config.retries
                )
                return await get_cmd(
                    snmp_dispatcher, auth, transport,
                    ObjectType(ObjectIdentity(oid))
                )
            
            error_indication, error_status, error_index, var_binds = asyncio.run(_async_get())
            
            if error_indication:
                logger.debug(f"SNMP Get错误: {error_indication}")
                return None
            
            if var_binds:
                return self._parse_snmp_value(var_binds[0][1])
            
            return None
        except Exception as e:
            logger.debug(f"SNMP Get失败 [{oid}]: {e}")
            return None
    
    async def walk(self, oid: str = '1.3.6.1') -> List[Dict[str, Any]]:
        """异步SNMP Walk"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_walk, oid)
    
    def _sync_walk(self, oid: str) -> List[Dict[str, Any]]:
        """同步执行SNMP Walk"""
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
            
            async def _async_walk():
                snmp_dispatcher = SnmpDispatcher()
                transport = await UdpTransportTarget.create(
                    (self._config.host, self._config.port),
                    timeout=self._config.timeout,
                    retries=self._config.retries
                )
                return await next_cmd(
                    snmp_dispatcher, auth, transport,
                    ObjectType(ObjectIdentity(oid)), lexicographicMode=False
                )
            
            error_indication, error_status, error_index, var_bind_table = asyncio.run(_async_walk())
            
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
    
    async def get_bulk(self, oids: List[str]) -> Dict[str, Any]:
        """
        异步批量获取多个OID
        
        Args:
            oids: OID列表
            
        Returns:
            {oid: value} 字典
        """
        tasks = [self.get(oid) for oid in oids]
        results = await asyncio.gather(*tasks)
        return {oid: val for oid, val in zip(oids, results) if val is not None}
    
    def _resolve_oid(self, oid: str) -> str:
        """解析MIB名称为OID"""
        if oid.startswith('1.3.6.1') or oid.startswith('.'):
            return oid.lstrip('.')
        return oid
    
    def _parse_snmp_value(self, value) -> Any:
        """解析pysnmp值为Python类型"""
        try:
            if isinstance(value, rfc1902.Integer32):
                return int(value)
            elif isinstance(value, (rfc1902.Counter32, rfc1902.Counter64, 
                                    rfc1902.Gauge32, rfc1902.Unsigned32)):
                return int(value)
            elif isinstance(value, rfc1902.OctetString):
                return str(value)
            else:
                return str(value)
        except Exception:
            return str(value)
    
    def _get_auth_protocol(self):
        """获取认证协议"""
        auth_map = {
            'MD5': usmHMACMD5AuthProtocol,
            'SHA': usmHMACSHAAuthProtocol,
            'SHA256': usmHMAC128SHA224AuthProtocol,
            'SHA384': usmHMAC192SHA384AuthProtocol,
            'SHA512': usmHMAC256SHA384AuthProtocol
        }
        return auth_map.get(self._config.auth_protocol.upper(), usmHMACMD5AuthProtocol)
    
    def _get_priv_protocol(self):
        """获取加密协议"""
        priv_map = {
            'DES': usmDESPrivProtocol,
            'AES': usmAESPrivProtocol,
            'AES128': usmAES128PrivProtocol,
            'AES192': usmAES192PrivProtocol,
            'AES256': usmAES256PrivProtocol
        }
        return priv_map.get(self._config.priv_protocol.upper(), usmAESPrivProtocol)


class SNMPClient:
    """
    SNMP客户端（同步版本）
    
    功能特性：
    1. 支持SNMP v1/v2c/v3
    2. 支持Get、Set、Walk、GetNext操作
    3. 支持批量采集
    4. 支持超时和重试配置
    5. 自动重连
    6. 厂商自动识别
    7. 异步操作支持
    
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
        self._vendor: Optional[str] = None
        self._mib_mapper = VendorMIBMapper()
        self._async_client: Optional[AsyncSNMPClient] = None
        
        if _easysnmp_available:
            self._session = self._create_easysnmp_session()
        elif not _pysnmp_available:
            logger.warning("未安装pysnmp或easysnmp，SNMP功能将不可用")
        
        # 如果启用异步，创建异步客户端
        if self._config.use_async and _pysnmp_available:
            self._async_client = AsyncSNMPClient(self._config)
    
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
                # 自动识别厂商
                self._vendor = self._mib_mapper.detect_vendor(str(result))
                if self._vendor:
                    logger.info(f"识别到厂商: {self._vendor}")
            return self._connected
        except Exception as e:
            logger.error(f"SNMP连接失败: {self._config.host}:{self._config.port} - {e}")
            self._connected = False
            return False
    
    @property
    def vendor(self) -> Optional[str]:
        """获取识别的厂商"""
        return self._vendor
    
    def get(self, oid: str) -> Optional[Any]:
        """
        SNMP Get操作
        
        Args:
            oid: OID或MIB名称
        
        Returns:
            获取的值，失败返回None
        """
        if self._async_client:
            return self._async_client._sync_get(oid)
        elif _easysnmp_available and self._session:
            return self._easysnmp_get(oid)
        elif _pysnmp_available:
            return self._pysnmp_get(oid)
        else:
            logger.error("无可用的SNMP库")
            return None
    
    async def async_get(self, oid: str) -> Optional[Any]:
        """
        异步SNMP Get操作
        
        Args:
            oid: OID或MIB名称
        
        Returns:
            获取的值，失败返回None
        """
        if self._async_client:
            return await self._async_client.get(oid)
        else:
            logger.warning("异步客户端未初始化")
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
            
            async def _async_get():
                snmp_dispatcher = SnmpDispatcher()
                transport = await UdpTransportTarget.create(
                    (self._config.host, self._config.port),
                    timeout=self._config.timeout,
                    retries=self._config.retries
                )
                return await get_cmd(
                    snmp_dispatcher, auth, transport,
                    ObjectType(ObjectIdentity(oid))
                )
            
            error_indication, error_status, error_index, var_binds = asyncio.run(_async_get())
            
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
        if self._async_client:
            return self._async_client._sync_walk(oid)
        elif _easysnmp_available and self._session:
            return self._easysnmp_walk(oid)
        elif _pysnmp_available:
            return self._pysnmp_walk(oid)
        else:
            logger.error("无可用的SNMP库")
            return []
    
    async def async_walk(self, oid: str = '1.3.6.1') -> List[Dict[str, Any]]:
        """
        异步SNMP Walk操作
        
        Args:
            oid: 起始OID
        
        Returns:
            [(oid, value), ...] 列表
        """
        if self._async_client:
            return await self._async_client.walk(oid)
        else:
            logger.warning("异步客户端未初始化")
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
            
            async def _async_walk():
                snmp_dispatcher = SnmpDispatcher()
                transport = await UdpTransportTarget.create(
                    (self._config.host, self._config.port),
                    timeout=self._config.timeout,
                    retries=self._config.retries
                )
                return await next_cmd(
                    snmp_dispatcher, auth, transport,
                    ObjectType(ObjectIdentity(oid)), lexicographicMode=False
                )
            
            error_indication, error_status, error_index, var_bind_table = asyncio.run(_async_walk())
            
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
    
    async def async_get_bulk(self, oids: List[str]) -> Dict[str, Any]:
        """
        异步批量获取多个OID的值
        
        Args:
            oids: OID列表
        
        Returns:
            {oid: value} 字典
        """
        if self._async_client:
            return await self._async_client.get_bulk(oids)
        else:
            return self.get_bulk(oids)
    
    def get_vendor_oid(self, oid_key: str) -> Optional[Any]:
        """
        获取厂商特定MIB OID的值
        
        Args:
            oid_key: MIB OID键名 (如 'cisco_cpu_5min', 'hw_mem_used')
        
        Returns:
            MIB值
        """
        if not self._vendor:
            logger.warning("厂商未识别，无法获取厂商特定MIB")
            return None
        
        vendor_oids = self._mib_mapper.get_vendor_oids(self._vendor)
        oid = vendor_oids.get(oid_key)
        
        if oid:
            return self.get(oid)
        
        # 尝试从各厂商MIB中查找
        all_vendor_oids = [
            VendorMIBMapper.CISCO_OIDS,
            VendorMIBMapper.HUAWEI_OIDS,
            VendorMIBMapper.JUNIPER_OIDS,
            VendorMIBMapper.HPE_OIDS,
            VendorMIBMapper.DELL_OIDS,
            VendorMIBMapper.H3C_OIDS,
        ]
        
        for vendor_oid_dict in all_vendor_oids:
            if oid_key in vendor_oid_dict:
                return self.get(vendor_oid_dict[oid_key])
        
        return None
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息（综合多个OID）
        
        Returns:
            系统信息字典
        """
        info = {
            'host': self._config.host,
            'vendor': self._vendor,
        }
        
        # 基础系统信息
        system_oids = {
            'sysDescr': '1.3.6.1.2.1.1.1.0',
            'sysUptime': '1.3.6.1.2.1.1.3.0',
            'sysContact': '1.3.6.1.2.1.1.4.0',
            'sysName': '1.3.6.1.2.1.1.5.0',
            'sysLocation': '1.3.6.1.2.1.1.6.0',
            'sysServices': '1.3.6.1.2.1.1.7.0'
        }
        
        for key, oid in system_oids.items():
            info[key] = self.get(oid)
        
        return info
    
    def get_interface_stats(self) -> List[Dict[str, Any]]:
        """
        获取网络接口统计信息（使用64位计数器）
        
        Returns:
            接口统计列表
        """
        interfaces = []
        
        # 获取接口数量
        if_count = self.get('1.3.6.1.2.1.2.1.0')
        if not if_count:
            return interfaces
        
        # 获取接口名称映射
        if_names = {}
        for i in range(1, int(if_count) + 1):
            if_name = self.get(f'1.3.6.1.2.1.31.1.1.1.1.{i}')
            if if_name:
                if_names[i] = if_name
        
        # 遍历每个接口
        for i in range(1, int(if_count) + 1):
            # 使用64位计数器(ifXTable)
            interface = {
                'index': i,
                'name': if_names.get(i, ''),
                'ifDescr': self.get(f'1.3.6.1.2.1.2.2.1.2.{i}'),
                'ifType': self.get(f'1.3.6.1.2.1.2.2.1.3.{i}'),
                'ifSpeed': self.get(f'1.3.6.1.2.1.2.2.1.5.{i}'),
                'ifOperStatus': self.get(f'1.3.6.1.2.1.2.2.1.8.{i}'),
                'ifAdminStatus': self.get(f'1.3.6.1.2.1.2.2.1.7.{i}'),
                # 64位计数器
                'ifInOctets': self.get(f'1.3.6.1.2.1.31.1.1.1.6.{i}'),
                'ifOutOctets': self.get(f'1.3.6.1.2.1.31.1.1.1.10.{i}'),
                'ifInUcastPkts': self.get(f'1.3.6.1.2.1.31.1.1.1.7.{i}'),
                'ifOutUcastPkts': self.get(f'1.3.6.1.2.1.31.1.1.1.11.{i}'),
                'ifInErrors': self.get(f'1.3.6.1.2.1.31.1.1.1.15.{i}'),
                'ifOutErrors': self.get(f'1.3.6.1.2.1.31.1.1.1.17.{i}'),
            }
            interfaces.append(interface)
        
        return interfaces
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """
        获取CPU信息（支持多厂商）
        
        Returns:
            CPU信息
        """
        info = {'source': 'unknown'}
        
        # 尝试UCD-SNMP-MIB (Linux)
        cpu_user = self.get('1.3.6.1.4.1.2021.11.9.0')
        if cpu_user is not None:
            info = {
                'source': 'ucd_snmp',
                'user': cpu_user,
                'system': self.get('1.3.6.1.4.1.2021.11.10.0'),
                'idle': self.get('1.3.6.1.4.1.2021.11.11.0'),
            }
            return info
        
        # 尝试Cisco
        cisco_cpu = self.get('1.3.6.1.4.1.9.2.1.58.0')
        if cisco_cpu is not None:
            info = {
                'source': 'cisco',
                'usage_5min': cisco_cpu,
            }
            return info
        
        # 尝试Huawei
        huawei_cpu = self.get('1.3.6.1.4.1.2011.2.23.1.15.0')
        if huawei_cpu is not None:
            info = {
                'source': 'huawei',
                'usage': huawei_cpu,
            }
            return info
        
        # 尝试Dell
        dell_cpu = self.get('1.3.6.1.4.1.674.10892.1.200.10.1.0')
        if dell_cpu is not None:
            info = {
                'source': 'dell',
                'status': dell_cpu,
            }
            return info
        
        return info
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        获取内存信息（支持多厂商）
        
        Returns:
            内存信息
        """
        info = {'source': 'unknown'}
        
        # 尝试UCD-SNMP-MIB (Linux)
        mem_total = self.get('1.3.6.1.4.1.2021.4.5.0')
        if mem_total is not None:
            mem_avail = self.get('1.3.6.1.4.1.2021.4.6.0')
            info = {
                'source': 'ucd_snmp',
                'total': mem_total,
                'avail': mem_avail,
                'used': mem_total - mem_avail if mem_avail else 0,
                'usage_percent': ((mem_total - mem_avail) / mem_total * 100) if mem_total else 0,
            }
            return info
        
        # 尝试Cisco
        cisco_mem = self.get('1.3.6.1.4.1.9.2.1.8.0')
        if cisco_mem is not None:
            cisco_mem_free = self.get('1.3.6.1.4.1.9.2.1.9.0')
            info = {
                'source': 'cisco',
                'used': cisco_mem,
                'free': cisco_mem_free,
            }
            return info
        
        # 尝试Huawei
        huawei_mem = self.get('1.3.6.1.4.1.2011.2.23.1.6.0')
        if huawei_mem is not None:
            huawei_mem_free = self.get('1.3.6.1.4.1.2011.2.23.1.7.0')
            info = {
                'source': 'huawei',
                'used': huawei_mem,
                'free': huawei_mem_free,
            }
            return info
        
        return info
    
    def _resolve_oid(self, oid: str) -> str:
        """解析MIB名称为OID"""
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
    
    def _get_auth_protocol(self):
        """获取认证协议"""
        auth_map = {
            'MD5': usmHMACMD5AuthProtocol,
            'SHA': usmHMACSHAAuthProtocol,
            'SHA256': usmHMAC128SHA224AuthProtocol,
            'SHA384': usmHMAC192SHA384AuthProtocol,
            'SHA512': usmHMAC256SHA384AuthProtocol
        }
        return auth_map.get(self._config.auth_protocol.upper(), usmHMACMD5AuthProtocol)
    
    def _get_priv_protocol(self):
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
        self._async_client = None
        logger.debug(f"SNMP连接已关闭: {self._config.host}")


class SNMPDevice:
    """
    SNMP设备采集器
    
    用于采集特定类型设备的标准MIB数据
    支持多厂商自动识别和厂商特定MIB采集
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
        self._mib_mapper = VendorMIBMapper()
        self._connected = False
    
    def connect(self) -> bool:
        """建立SNMP连接"""
        self._client.connect()
        self._connected = True
        return True
    
    def close(self):
        """关闭SNMP连接"""
        self._client.close()
        self._connected = False
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    def collect_all(self) -> Dict[str, Any]:
        """
        采集设备所有标准数据
        
        Returns:
            采集的指标数据字典
        """
        # 先连接以识别厂商
        self._client.connect()
        
        data = {
            'host': self._config.host,
            'timestamp': None,
            'vendor': self._client.vendor,
            'system': self.collect_system(),
            'interfaces': self.collect_interfaces(),
            'cpu': self.collect_cpu(),
            'memory': self.collect_memory(),
            'disk': self.collect_disk(),
            'network': self.collect_network_stats(),
        }
        
        # 采集厂商特定信息
        vendor_data = self.collect_vendor_specific()
        if vendor_data:
            data['vendor_data'] = vendor_data
        
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
        
        # 识别厂商
        results['detected_vendor'] = self._mib_mapper.detect_vendor(str(results.get('sysDescr', '')))
        
        return results
    
    def collect_interfaces(self) -> List[Dict[str, Any]]:
        """采集网络接口信息"""
        return self._client.get_interface_stats()
    
    def collect_cpu(self) -> Optional[Dict[str, Any]]:
        """采集CPU信息"""
        return self._client.get_cpu_info()
    
    def collect_memory(self) -> Optional[Dict[str, Any]]:
        """采集内存信息"""
        return self._client.get_memory_info()
    
    def collect_disk(self) -> List[Dict[str, Any]]:
        """采集磁盘信息"""
        disks = []
        
        # 尝试UCD-SNMP-MIB磁盘信息
        disk_num = self._client.get('1.3.6.1.4.1.2021.9.1.1.0')
        if not disk_num:
            # 尝试Host Resources MIB
            return self._collect_host_resources_disk()
        
        for i in range(1, int(disk_num) + 1):
            disk = {
                'index': i,
                'path': self._client.get(f'1.3.6.1.4.1.2021.9.1.2.{i}'),
                'total': self._client.get(f'1.3.6.1.4.1.2021.9.1.9.{i}'),
                'avail': self._client.get(f'1.3.6.1.4.1.2021.9.1.4.{i}'),
                'used_percent': self._client.get(f'1.3.6.1.4.1.2021.9.1.10.{i}')
            }
            disks.append(disk)
        
        return disks
    
    def _collect_host_resources_disk(self) -> List[Dict[str, Any]]:
        """使用Host Resources MIB采集磁盘信息"""
        disks = []
        
        # hrStorageTable索引
        storage_index = 1
        while True:
            storage_type = self._client.get(f'1.3.6.1.2.1.25.2.3.1.2.{storage_index}')
            if storage_type is None:
                break
            
            # 检查是否是磁盘类型 (.1.3.6.1.2.1.25.2.1.4 = hrStorageFixedDisk)
            if storage_type in ['1.3.6.1.2.1.25.2.1.4', '1.3.6.1.2.1.25.2.1.5']:  # FixedDisk or VirtualMemory
                storage_descr = self._client.get(f'1.3.6.1.2.1.25.2.3.1.3.{storage_index}')
                storage_units = self._client.get(f'1.3.6.1.2.1.25.2.3.1.4.{storage_index}')
                storage_size = self._client.get(f'1.3.6.1.2.1.25.2.3.1.5.{storage_index}')
                storage_used = self._client.get(f'1.3.6.1.2.1.25.2.3.1.6.{storage_index}')
                
                if storage_size and storage_units:
                    disk = {
                        'index': storage_index,
                        'path': storage_descr,
                        'type': 'fixed' if 'FixedDisk' in str(storage_type) else 'virtual',
                        'total': storage_size * storage_units if storage_size and storage_units else 0,
                        'used': storage_used * storage_units if storage_used and storage_units else 0,
                        'avail': (storage_size - storage_used) * storage_units if storage_size and storage_used and storage_units else 0,
                    }
                    disks.append(disk)
            
            storage_index += 1
            if storage_index > 100:  # 防止无限循环
                break
        
        return disks
    
    def collect_network_stats(self) -> Dict[str, Any]:
        """采集网络统计信息"""
        stats = {
            'ip_forwarding': self._client.get('1.3.6.1.2.1.4.1.0'),
            'tcp_rto_algorithm': self._client.get('1.3.6.1.2.1.6.1.0'),
            'tcp_rto_min': self._client.get('1.3.6.1.2.1.6.2.0'),
            'tcp_rto_max': self._client.get('1.3.6.1.2.1.6.5.0'),
            'tcp_active_opens': self._client.get('1.3.6.1.2.1.6.8.0'),
            'tcp_passive_opens': self._client.get('1.3.6.1.2.1.6.9.0'),
            'tcp_attempt_fails': self._client.get('1.3.6.1.2.1.6.10.0'),
            'tcp_estab_resets': self._client.get('1.3.6.1.2.1.6.11.0'),
            'tcp_curr_estab': self._client.get('1.3.6.1.2.1.6.15.0'),
            'udp_in_datagrams': self._client.get('1.3.6.1.2.1.7.1.0'),
            'udp_out_datagrams': self._client.get('1.3.6.1.2.1.7.4.0'),
            'udp_in_errors': self._client.get('1.3.6.1.2.1.7.3.0'),
            'udp_no_ports': self._client.get('1.3.6.1.2.1.7.2.0'),
        }
        return stats
    
    def collect_vendor_specific(self) -> Dict[str, Any]:
        """采集厂商特定信息"""
        vendor = self._client.vendor
        if not vendor:
            return {}
        
        vendor_data = {}
        
        if vendor == 'dell':
            # Dell服务器特定信息
            vendor_data['power_supply'] = self._collect_dell_power()
            vendor_data['fan'] = self._collect_dell_fan()
            vendor_data['temperature'] = self._collect_dell_temp()
        
        elif vendor == 'hp':
            # HPE服务器特定信息
            vendor_data['power_supply'] = self._collect_hpe_power()
            vendor_data['fan'] = self._collect_hpe_fan()
        
        elif vendor in ['huawei', 'cisco', 'juniper']:
            # 网络设备特定信息
            vendor_data['load_average'] = self._collect_load_average()
        
        return vendor_data
    
    def _collect_dell_power(self) -> List[Dict[str, Any]]:
        """采集Dell电源状态"""
        power_units = []
        index = 1
        while True:
            status = self._client.get(f'1.3.6.1.4.1.674.10892.1.200.10.1.{index}.0')
            if status is None:
                break
            power_units.append({
                'index': index,
                'status': status,
                'type': self._client.get(f'1.3.6.1.4.1.674.10892.1.200.10.1.{index}.1'),
                'reading': self._client.get(f'1.3.6.1.4.1.674.10892.1.200.10.1.{index}.3'),
            })
            index += 1
            if index > 10:
                break
        return power_units
    
    def _collect_dell_fan(self) -> List[Dict[str, Any]]:
        """采集Dell风扇状态"""
        fans = []
        index = 1
        while True:
            status = self._client.get(f'1.3.6.1.4.1.674.10892.1.200.30.1.{index}.0')
            if status is None:
                break
            fans.append({
                'index': index,
                'status': status,
                'speed': self._client.get(f'1.3.6.1.4.1.674.10892.1.200.30.1.{index}.3'),
            })
            index += 1
            if index > 20:
                break
        return fans
    
    def _collect_dell_temp(self) -> List[Dict[str, Any]]:
        """采集Dell温度状态"""
        temps = []
        index = 1
        while True:
            status = self._client.get(f'1.3.6.1.4.1.674.10892.1.200.40.1.{index}.0')
            if status is None:
                break
            temps.append({
                'index': index,
                'status': status,
                'reading': self._client.get(f'1.3.6.1.4.1.674.10892.1.200.40.1.{index}.3'),
            })
            index += 1
            if index > 20:
                break
        return temps
    
    def _collect_hpe_power(self) -> List[Dict[str, Any]]:
        """采集HPE电源状态"""
        power_units = []
        # HPE MIB索引可能不同，这里使用通用方法
        for i in range(1, 5):
            status = self._client.get(f'1.3.6.1.4.1.11.2.14.11.5.1.1.{i}')
            if status is not None:
                power_units.append({'index': i, 'status': status})
        return power_units
    
    def _collect_hpe_fan(self) -> List[Dict[str, Any]]:
        """采集HPE风扇状态"""
        fans = []
        for i in range(1, 10):
            status = self._client.get(f'1.3.6.1.4.1.11.2.14.11.5.2.{i}')
            if status is not None:
                fans.append({'index': i, 'status': status})
        return fans
    
    def _collect_load_average(self) -> Optional[Dict[str, Any]]:
        """采集负载信息"""
        load_1 = self._client.get('1.3.6.1.4.1.2021.10.1.3.1')
        load_5 = self._client.get('1.3.6.1.4.1.2021.10.1.3.2')
        load_15 = self._client.get('1.3.6.1.4.1.2021.10.1.3.3')
        
        if load_1 or load_5 or load_15:
            return {
                '1min': load_1,
                '5min': load_5,
                '15min': load_15,
            }
        return None
    
    def close(self):
        """关闭"""
        self._client.close()
