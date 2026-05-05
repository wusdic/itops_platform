"""
采集适配器工厂

统一管理多种采集协议和厂商设备，提供统一的采集接口
"""

import logging
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass
from enum import Enum

from snmp_collector.snmp_client import SNMPClient, SNMPConfig, SNMPVersion, VendorMIBMapper
from ssh_collector.ssh_client import SSHClient, SSHConfig
from api_collector.http_client import HTTPClient, VendorAPIClient, AuthType
from api_collector.zabbix_client import ZabbixClient
from api_collector.prometheus_client import PrometheusClient
from api_collector.kubernetes_client import K8sClient
from api_collector.docker_client import DockerClient, DockerConfig
from ssh_collector.winrm_client import WinRMClient, WinRMConfig
from ipmi_collector.ipmi_client import IPMIClient, IPMIConfig, IPMIVersion

logger = logging.getLogger(__name__)


class DeviceType(str, Enum):
    """设备类型枚举"""
    UNKNOWN = 'unknown'
    SERVER = 'server'
    NETWORK = 'network'
    SECURITY = 'security'
    STORAGE = 'storage'
    VIRTUAL = 'virtual'
    CONTAINER = 'container'
    CLOUD = 'cloud'


class ProtocolType(str, Enum):
    """协议类型枚举"""
    SNMP = 'snmp'
    SSH = 'ssh'
    HTTP = 'http'
    WINRM = 'winrm'
    IPMI = 'ipmi'
    ZABBIX = 'zabbix'
    PROMETHEUS = 'prometheus'
    KUBERNETES = 'kubernetes'
    DOCKER = 'docker'
    REDFISH = 'redfish'
    WBEM = 'wbem'


class CollectorFactory:
    """
    采集适配器工厂
    
    根据设备类型和配置自动选择合适的采集协议和客户端。
    
    使用示例:
    >>> factory = CollectorFactory()
    >>> factory.register_device('linux_server', DeviceType.SERVER, ProtocolType.SSH)
    >>> collector = factory.create_collector('linux_server', host='192.168.1.1')
    >>> data = collector.collect()
    """
    
    def __init__(self):
        self._device_registry: Dict[str, Dict[str, Any]] = {}
        self._vendor_mappers: Dict[str, VendorMIBMapper] = {}
        self._active_collectors: Dict[str, Any] = {}
        
        # 注册默认设备类型
        self._register_default_devices()
    
    def _register_default_devices(self) -> None:
        """注册默认设备类型"""
        
        # Linux/Unix服务器
        self.register_device(
            name='linux_server',
            device_type=DeviceType.SERVER,
            protocols=[ProtocolType.SSH, ProtocolType.SNMP],
            default_protocol=ProtocolType.SSH,
            vendor_patterns=['linux', 'ubuntu', 'centos', 'red hat', 'debian', 'suse', 'oracle'],
            credentials={'ssh': {'username': 'root', 'password': '', 'key_file': '/root/.ssh/id_rsa'}},
        )
        
        # Windows服务器
        self.register_device(
            name='windows_server',
            device_type=DeviceType.SERVER,
            protocols=[ProtocolType.WINRM, ProtocolType.SSH],
            default_protocol=ProtocolType.WINRM,
            vendor_patterns=['windows', 'microsoft'],
            credentials={'winrm': {'username': 'administrator', 'password': ''}},
        )
        
        # Cisco网络设备
        self.register_device(
            name='cisco_router',
            device_type=DeviceType.NETWORK,
            protocols=[ProtocolType.SNMP, ProtocolType.SSH, ProtocolType.HTTP],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['cisco', 'ios-xe', 'nx-os', 'ios'],
            credentials={'snmp': {'community': 'public', 'version': 'v2c'}},
        )
        
        # Huawei网络设备
        self.register_device(
            name='huawei_switch',
            device_type=DeviceType.NETWORK,
            protocols=[ProtocolType.SNMP, ProtocolType.SSH, ProtocolType.HTTP],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['huawei', 'vrp'],
            credentials={'snmp': {'community': 'public', 'version': 'v2c'}},
        )
        
        # Juniper网络设备
        self.register_device(
            name='juniper_firewall',
            device_type=DeviceType.NETWORK,
            protocols=[ProtocolType.SNMP, ProtocolType.SSH],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['juniper', 'junos', 'screenos'],
            credentials={'snmp': {'community': 'public', 'version': 'v2c'}},
        )
        
        # H3C网络设备
        self.register_device(
            name='h3c_switch',
            device_type=DeviceType.NETWORK,
            protocols=[ProtocolType.SNMP, ProtocolType.SSH],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['h3c', 'comware', 'hp networking'],
            credentials={'snmp': {'community': 'public', 'version': 'v2c'}},
        )
        
        # 天融信安全设备
        self.register_device(
            name='topsec_firewall',
            device_type=DeviceType.SECURITY,
            protocols=[ProtocolType.SNMP, ProtocolType.HTTP],
            default_protocol=ProtocolType.HTTP,
            vendor_patterns=['topsec', 'tos'],
            credentials={'http': {'username': 'admin', 'password': 'admin'}},
        )
        
        # 绿盟安全设备
        self.register_device(
            name='nsfocus_ids',
            device_type=DeviceType.SECURITY,
            protocols=[ProtocolType.SNMP, ProtocolType.HTTP],
            default_protocol=ProtocolType.HTTP,
            vendor_patterns=['nsfocus', '绿盟'],
            credentials={'http': {'username': 'admin', 'password': 'admin'}},
        )
        
        # 启明星辰安全设备
        self.register_device(
            name='venustech_utm',
            device_type=DeviceType.SECURITY,
            protocols=[ProtocolType.SNMP, ProtocolType.HTTP],
            default_protocol=ProtocolType.HTTP,
            vendor_patterns=['venustech', '启明'],
            credentials={'http': {'username': 'admin', 'password': 'admin'}},
        )
        
        # 深信服安全设备
        self.register_device(
            name='sangfor_fw',
            device_type=DeviceType.SECURITY,
            protocols=[ProtocolType.SNMP, ProtocolType.HTTP],
            default_protocol=ProtocolType.HTTP,
            vendor_patterns=['sangfor', '深信服', 'af'],
            credentials={'http': {'username': 'admin', 'password': 'admin'}},
        )
        
        # Fortinet防火墙
        self.register_device(
            name='fortinet_fortigate',
            device_type=DeviceType.SECURITY,
            protocols=[ProtocolType.SNMP, ProtocolType.HTTP],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['fortinet', 'fortigate', 'fortios'],
            credentials={'snmp': {'community': 'public', 'version': 'v2c'}},
        )
        
        # Dell服务器
        self.register_device(
            name='dell_server',
            device_type=DeviceType.SERVER,
            protocols=[ProtocolType.SNMP, ProtocolType.SSH, ProtocolType.IPMI, ProtocolType.WINRM],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['dell', 'poweredge'],
            credentials={
                'snmp': {'community': 'public', 'version': 'v2c'},
                'ipmi': {'username': 'root', 'password': 'calvin'},
            },
        )
        
        # HPE服务器
        self.register_device(
            name='hpe_server',
            device_type=DeviceType.SERVER,
            protocols=[ProtocolType.SNMP, ProtocolType.SSH, ProtocolType.IPMI],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['hp ', 'hewlett', 'procurve', 'hpe'],
            credentials={
                'snmp': {'community': 'public', 'version': 'v2c'},
                'ipmi': {'username': 'Administrator', 'password': ''},
            },
        )
        
        # 华为服务器
        self.register_device(
            name='huawei_server',
            device_type=DeviceType.SERVER,
            protocols=[ProtocolType.SNMP, ProtocolType.SSH, ProtocolType.IPMI],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['huawei'],
            credentials={
                'snmp': {'community': 'public', 'version': 'v2c'},
                'ipmi': {'username': 'root', 'password': 'Huawei12#$'},
            },
        )
        
        # 浪潮服务器
        self.register_device(
            name='inspur_server',
            device_type=DeviceType.SERVER,
            protocols=[ProtocolType.SNMP, ProtocolType.SSH, ProtocolType.IPMI],
            default_protocol=ProtocolType.SNMP,
            vendor_patterns=['inspur', 'haniya'],
            credentials={
                'snmp': {'community': 'public', 'version': 'v2c'},
                'ipmi': {'username': 'admin', 'password': 'admin'},
            },
        )
        
        # VMware虚拟化
        self.register_device(
            name='vmware_esxi',
            device_type=DeviceType.VIRTUAL,
            protocols=[ProtocolType.SNMP, ProtocolType.HTTP],
            default_protocol=ProtocolType.HTTP,
            vendor_patterns=['vmware', 'esxi', 'esx'],
            credentials={'http': {'username': 'root', 'password': ''}},
        )
        
        # Kubernetes集群
        self.register_device(
            name='kubernetes_cluster',
            device_type=DeviceType.CONTAINER,
            protocols=[ProtocolType.KUBERNETES],
            default_protocol=ProtocolType.KUBERNETES,
            vendor_patterns=['kubernetes', 'k8s'],
            credentials={'k8s': {'token': ''}},
        )
        
        # Docker主机
        self.register_device(
            name='docker_host',
            device_type=DeviceType.CONTAINER,
            protocols=[ProtocolType.DOCKER, ProtocolType.SSH],
            default_protocol=ProtocolType.DOCKER,
            vendor_patterns=['docker'],
            credentials={'docker': {'host': 'tcp://localhost:2375'}},
        )
    
    def register_device(
        self,
        name: str,
        device_type: DeviceType,
        protocols: List[ProtocolType],
        default_protocol: ProtocolType = None,
        vendor_patterns: List[str] = None,
        credentials: Dict[str, Dict] = None,
        config: Dict[str, Any] = None,
    ) -> None:
        """
        注册设备类型
        
        Args:
            name: 设备类型名称
            device_type: 设备大类
            protocols: 支持的协议列表
            default_protocol: 默认协议
            vendor_patterns: 厂商识别关键词
            credentials: 默认凭据
            config: 其他配置
        """
        self._device_registry[name] = {
            'device_type': device_type,
            'protocols': protocols,
            'default_protocol': default_protocol or protocols[0],
            'vendor_patterns': vendor_patterns or [],
            'credentials': credentials or {},
            'config': config or {},
        }
        
        logger.debug(f"注册设备类型: {name} ({device_type})")
    
    def detect_device_type(self, sys_info: Dict[str, Any]) -> Optional[str]:
        """
        根据系统信息检测设备类型
        
        Args:
            sys_info: 系统信息 (如 sysDescr)
            
        Returns:
            设备类型名称
        """
        sys_descr = str(sys_info.get('sysDescr', '')).lower()
        
        best_match = None
        best_score = 0
        
        for name, device_info in self._device_registry.items():
            score = 0
            for pattern in device_info.get('vendor_patterns', []):
                if pattern.lower() in sys_descr:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = name
        
        return best_match
    
    def create_collector(
        self,
        device_type: str = None,
        protocol: ProtocolType = None,
        host: str = '',
        port: int = None,
        credentials: Dict[str, Any] = None,
        **kwargs
    ) -> Optional['BaseCollector']:
        """
        创建采集器
        
        Args:
            device_type: 设备类型名称
            protocol: 指定协议
            host: 主机地址
            port: 端口
            credentials: 连接凭据
            **kwargs: 其他参数
            
        Returns:
            采集器实例
        """
        if not device_type and not protocol:
            logger.error("必须指定device_type或protocol")
            return None
        
        # 获取设备注册信息
        device_info = self._device_registry.get(device_type, {})
        
        # 确定使用的协议
        if not protocol:
            protocol = device_info.get('default_protocol') or ProtocolType.SNMP
        
        # 合并凭据
        merged_credentials = {**(device_info.get('credentials', {})), **(credentials or {})}
        
        # 创建采集器
        collector = self._create_collector_by_protocol(
            protocol, host, port, merged_credentials, **kwargs
        )
        
        if collector:
            collector_id = f"{protocol.value}_{host}_{port or 'default'}"
            self._active_collectors[collector_id] = collector
        
        return collector
    
    def _create_collector_by_protocol(
        self,
        protocol: ProtocolType,
        host: str,
        port: int,
        credentials: Dict[str, Any],
        **kwargs
    ) -> Optional['BaseCollector']:
        """根据协议类型创建采集器"""
        
        try:
            if protocol == ProtocolType.SNMP:
                snmp_creds = credentials.get('snmp', {})
                config = SNMPConfig(
                    host=host,
                    port=port or snmp_creds.get('port', 161),
                    version=SNMPVersion(snmp_creds.get('version', 'v2c')),
                    community=snmp_creds.get('community', 'public'),
                    security_name=snmp_creds.get('username', ''),
                    auth_password=snmp_creds.get('auth_password', ''),
                    priv_password=snmp_creds.get('priv_password', ''),
                    timeout=snmp_creds.get('timeout', 5),
                )
                return SNMPCollector(config)
            
            elif protocol == ProtocolType.SSH:
                ssh_creds = credentials.get('ssh', {})
                config = SSHConfig(
                    host=host,
                    port=port or ssh_creds.get('port', 22),
                    username=ssh_creds.get('username', 'root'),
                    password=ssh_creds.get('password', ''),
                    key_file=ssh_creds.get('key_file'),
                )
                return SSHCollector(config)
            
            elif protocol == ProtocolType.HTTP:
                http_creds = credentials.get('http', {})
                client = HTTPClient(
                    base_url=f"http://{host}:{port or 80}",
                    timeout=http_creds.get('timeout', 30),
                )
                if http_creds.get('username'):
                    client.set_auth(AuthType.BASIC, 
                                  username=http_creds['username'], 
                                  password=http_creds.get('password', ''))
                return HTTPAgent(client, vendor=http_creds.get('vendor'))
            
            elif protocol == ProtocolType.WINRM:
                winrm_creds = credentials.get('winrm', {})
                config = WinRMConfig(
                    host=host,
                    port=port or winrm_creds.get('port', 5985),
                    username=winrm_creds.get('username', 'administrator'),
                    password=winrm_creds.get('password', ''),
                    ssl=winrm_creds.get('ssl', False),
                )
                return WinRMCollector(config)
            
            elif protocol == ProtocolType.IPMI:
                ipmi_creds = credentials.get('ipmi', {})
                config = IPMIConfig(
                    host=host,
                    port=port or 623,
                    username=ipmi_creds.get('username', 'admin'),
                    password=ipmi_creds.get('password', ''),
                    version=IPMIVersion(ipmi_creds.get('version', 'v2.0')),
                )
                return IPMICollector(config)
            
            elif protocol == ProtocolType.KUBERNETES:
                k8s_creds = credentials.get('k8s', {})
                return K8sCollector(
                    host=host or 'localhost',
                    port=port or 6443,
                    token=k8s_creds.get('token', ''),
                    **kwargs
                )
            
            elif protocol == ProtocolType.DOCKER:
                docker_creds = credentials.get('docker', {})
                config = DockerConfig(
                    host=docker_creds.get('host', f'tcp://{host}:{port or 2375}'),
                )
                return DockerCollector(config)
            
            elif protocol == ProtocolType.ZABBIX:
                zabbix_creds = credentials.get('zabbix', {})
                return ZabbixCollector(
                    url=zabbix_creds.get('url', f'http://{host}/zabbix/api_jsonrpc.php'),
                    username=zabbix_creds.get('username', 'Admin'),
                    password=zabbix_creds.get('password', 'zabbix'),
                )
            
            elif protocol == ProtocolType.PROMETHEUS:
                prom_creds = credentials.get('prometheus', {})
                return PrometheusCollector(
                    url=prom_creds.get('url', f'http://{host}:{port or 9090}'),
                )
            
            else:
                logger.warning(f"不支持的协议类型: {protocol}")
                return None
                
        except Exception as e:
            logger.error(f"创建{protocol}采集器失败: {e}")
            return None
    
    def get_active_collector(self, collector_id: str) -> Optional['BaseCollector']:
        """获取活跃采集器"""
        return self._active_collectors.get(collector_id)
    
    def remove_collector(self, collector_id: str) -> None:
        """移除采集器"""
        if collector_id in self._active_collectors:
            self._active_collectors[collector_id].close()
            del self._active_collectors[collector_id]
    
    def close_all(self) -> None:
        """关闭所有采集器"""
        for collector in self._active_collectors.values():
            try:
                collector.close()
            except Exception:
                pass
        self._active_collectors.clear()


class BaseCollector:
    """采集器基类"""
    
    def __init__(self, protocol: ProtocolType):
        self._protocol = protocol
        self._connected = False
    
    def collect(self) -> Dict[str, Any]:
        """采集数据"""
        raise NotImplementedError
    
    def connect(self) -> bool:
        """建立连接"""
        raise NotImplementedError
    
    def close(self) -> None:
        """关闭连接"""
        pass


class SNMPCollector(BaseCollector):
    """SNMP采集器"""
    
    def __init__(self, config: SNMPConfig):
        super().__init__(ProtocolType.SNMP)
        self._config = config
        self._client = SNMPClient(config)
    
    def connect(self) -> bool:
        return self._client.connect()
    
    def collect(self) -> Dict[str, Any]:
        device = SNMPDevice(self._config)
        return device.collect_all()
    
    def close(self) -> None:
        self._client.close()


class SSHCollector(BaseCollector):
    """SSH采集器"""
    
    def __init__(self, config: SSHConfig):
        super().__init__(ProtocolType.SSH)
        self._config = config
        self._client = SSHClient(config)
    
    def connect(self) -> bool:
        return self._client.connect()
    
    def collect(self) -> Dict[str, Any]:
        return self._client.execute_command('uptime')
    
    def close(self) -> None:
        self._client.close()


class HTTPAgent(BaseCollector):
    """HTTP API采集器"""
    
    def __init__(self, client: HTTPClient, vendor: str = None):
        super().__init__(ProtocolType.HTTP)
        self._client = client
        self._vendor = vendor
    
    def connect(self) -> bool:
        return self._client.health_check()
    
    def collect(self) -> Dict[str, Any]:
        return {'status': 'connected', 'vendor': self._vendor}
    
    def close(self) -> None:
        self._client.close()


class WinRMCollector(BaseCollector):
    """WinRM采集器"""
    
    def __init__(self, config: WinRMConfig):
        super().__init__(ProtocolType.WINRM)
        self._config = config
        self._client = WinRMClient(config)
    
    def connect(self) -> bool:
        return self._client.connect()
    
    def collect(self) -> Dict[str, Any]:
        return self._client.collect_all_metrics()
    
    def close(self) -> None:
        self._client.close()


class IPMICollector(BaseCollector):
    """IPMI采集器"""
    
    def __init__(self, config: IPMIConfig):
        super().__init__(ProtocolType.IPMI)
        self._config = config
        self._client = IPMIClient(config)
    
    def connect(self) -> bool:
        return self._client.connect()
    
    def collect(self) -> Dict[str, Any]:
        return self._client.collect_all_metrics()
    
    def close(self) -> None:
        self._client.close()


class K8sCollector(BaseCollector):
    """Kubernetes采集器"""
    
    def __init__(self, host: str, port: int, token: str = '', **kwargs):
        super().__init__(ProtocolType.KUBERNETES)
        self._client = K8sClient(host, port, token, **kwargs)
    
    def connect(self) -> bool:
        return self._client.connect()
    
    def collect(self) -> Dict[str, Any]:
        return self._client.collect_all_metrics()
    
    def close(self) -> None:
        self._client.close()


class DockerCollector(BaseCollector):
    """Docker采集器"""
    
    def __init__(self, config: DockerConfig):
        super().__init__(ProtocolType.DOCKER)
        self._config = config
        self._client = DockerClient(config)
    
    def connect(self) -> bool:
        return self._client.connect()
    
    def collect(self) -> Dict[str, Any]:
        return self._client.collect_all_metrics()
    
    def close(self) -> None:
        self._client.close()


class ZabbixCollector(BaseCollector):
    """Zabbix采集器"""
    
    def __init__(self, url: str, username: str, password: str):
        super().__init__(ProtocolType.ZABBIX)
        self._client = ZabbixClient(url, username, password)
    
    def connect(self) -> bool:
        return self._client.login()
    
    def collect(self) -> Dict[str, Any]:
        return self._client.get_all_metrics()
    
    def close(self) -> None:
        self._client.logout()


class PrometheusCollector(BaseCollector):
    """Prometheus采集器"""
    
    def __init__(self, url: str):
        super().__init__(ProtocolType.PROMETHEUS)
        self._client = PrometheusClient(url)
    
    def connect(self) -> bool:
        return self._client.health_check()
    
    def collect(self) -> Dict[str, Any]:
        return self._client.get_targets()
    
    def close(self) -> None:
        pass


# 全局工厂实例
_factory_instance: Optional[CollectorFactory] = None


def get_factory() -> CollectorFactory:
    """获取全局工厂实例"""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = CollectorFactory()
    return _factory_instance


def create_collector(
    device_type: str = None,
    protocol: str = None,
    host: str = '',
    port: int = None,
    **credentials
) -> Optional[BaseCollector]:
    """快捷创建采集器"""
    factory = get_factory()
    
    protocol_enum = None
    if protocol:
        try:
            protocol_enum = ProtocolType(protocol.lower())
        except ValueError:
            logger.error(f"未知协议: {protocol}")
            return None
    
    return factory.create_collector(
        device_type=device_type,
        protocol=protocol_enum,
        host=host,
        port=port,
        credentials=credentials,
    )
