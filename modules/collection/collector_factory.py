# -*- coding: utf-8 -*-
"""
采集适配器工厂

统一管理多种采集协议和厂商设备，提供统一的采集接口
设备配置从 config/devices/*.yaml 加载，不硬编码敏感信息
"""

import logging
from typing import Any, Dict, List, Optional

from core.protocols import ProtocolType

logger = logging.getLogger(__name__)


class CollectorFactory:
    """
    采集适配器工厂
    
    根据设备配置自动选择合适的采集协议和客户端。
    设备配置从配置文件加载，支持热更新。
    
    使用示例:
    >>> factory = CollectorFactory()
    >>> # 创建设备采集器
    >>> collector = factory.create_collector(device_config)
    >>> # 执行采集
    >>> data = collector.collect()
    """
    
    def __init__(self):
        self._collectors: Dict[str, Any] = {}
    
    def create_collector(self, device_config: Dict[str, Any]):
        """
        根据设备配置创建采集器
        
        Args:
            device_config: 设备配置字典
            
        Returns:
            采集器实例
        """
        device_type = device_config.get('type', 'unknown')
        protocol = device_config.get('protocols', {}).get('primary', 'snmp')
        
        protocol_lower = protocol.lower()
        
        # 根据协议类型创建采集器
        if protocol_lower == 'snmp':
            return self._create_snmp_collector(device_config)
        elif protocol_lower == 'ssh':
            return self._create_ssh_collector(device_config)
        elif protocol_lower == 'winrm':
            return self._create_winrm_collector(device_config)
        elif protocol_lower == 'ipmi':
            return self._create_ipmi_collector(device_config)
        elif protocol_lower == 'http':
            return self._create_http_collector(device_config)
        elif protocol_lower == 'kubernetes':
            return self._create_kubernetes_collector(device_config)
        elif protocol_lower == 'docker':
            return self._create_docker_collector(device_config)
        elif protocol_lower == 'zabbix':
            return self._create_zabbix_collector(device_config)
        elif protocol_lower == 'prometheus':
            return self._create_prometheus_collector(device_config)
        else:
            raise ValueError(f"不支持的协议: {protocol}")
    
    def _create_snmp_collector(self, device_config: Dict[str, Any]):
        """创建SNMP采集器"""
        from .snmp_collector.snmp_client import SNMPClient, SNMPConfig, SNMPVersion
        
        credentials = device_config.get('credentials', {}).get('snmp', {})
        ip = device_config.get('ip', '')
        port = device_config.get('port', 161)
        
        version_str = credentials.get('version', 'v2c')
        version = SNMPVersion(version_str) if version_str else SNMPVersion.V2C
        
        config = SNMPConfig(
            host=ip,
            port=credentials.get('port', port),
            version=version,
            community=credentials.get('community', 'public'),
            timeout=credentials.get('timeout', 10),
        )
        
        return SNMPClient(config)
    
    def _create_ssh_collector(self, device_config: Dict[str, Any]):
        """创建SSH采集器"""
        from .ssh_collector.ssh_client import SSHClient, SSHConfig
        
        credentials = device_config.get('credentials', {}).get('ssh', {})
        ip = device_config.get('ip', '')
        
        config = SSHConfig(
            host=ip,
            port=credentials.get('port', 22),
            username=credentials.get('username', 'root'),
            password=credentials.get('password', ''),
            key_file=credentials.get('key_file'),
            timeout=credentials.get('timeout', 30),
        )
        
        return SSHClient(config)
    
    def _create_winrm_collector(self, device_config: Dict[str, Any]):
        """创建WinRM采集器"""
        from .ssh_collector.winrm_client import WinRMClient, WinRMConfig
        
        credentials = device_config.get('credentials', {}).get('winrm', {})
        ip = device_config.get('ip', '')
        
        config = WinRMConfig(
            host=ip,
            port=credentials.get('port', 5985),
            username=credentials.get('username', 'Administrator'),
            password=credentials.get('password', ''),
            ssl=credentials.get('ssl', False),
        )
        
        return WinRMClient(config)
    
    def _create_ipmi_collector(self, device_config: Dict[str, Any]):
        """创建IPMI采集器"""
        from .ipmi_collector.ipmi_client import IPMIClient, IPMIConfig, IPMIVersion
        
        credentials = device_config.get('credentials', {}).get('ipmi', {})
        ip = device_config.get('ipmi_ip', device_config.get('ip', ''))
        
        config = IPMIConfig(
            host=ip,
            port=credentials.get('port', 623),
            username=credentials.get('username', 'admin'),
            password=credentials.get('password', ''),
            version=IPMIVersion(credentials.get('version', '2.0')),
        )
        
        return IPMIClient(config)
    
    def _create_http_collector(self, device_config: Dict[str, Any]):
        """创建HTTP API采集器"""
        from .api_collector.http_client import HTTPClient, VendorAPIClient
        
        api_config = device_config.get('api', {})
        vendor = device_config.get('vendor', '')
        
        if vendor in ['zabbix', 'prometheus', 'topsec', 'nsfocus', 'sangfor', 'venustech', 'fortinet']:
            adapter = VendorAPIClient(vendor=vendor)
            adapter.configure(
                base_url=api_config.get('base_url'),
                auth_type=api_config.get('auth_type'),
                username=api_config.get('username'),
                password=api_config.get('password'),
                api_key=api_config.get('api_key'),
            )
            return adapter
        else:
            base_url = api_config.get('base_url', f"http://{device_config.get('ip')}")
            client = HTTPClient(base_url=base_url)
            
            if api_config.get('username'):
                client.set_basic_auth(api_config['username'], api_config.get('password', ''))
            
            return client
    
    def _create_kubernetes_collector(self, device_config: Dict[str, Any]):
        """创建Kubernetes采集器"""
        from .api_collector.kubernetes_client import K8sClient
        
        k8s_config = device_config.get('kubernetes', {})
        
        return K8sClient(
            host=k8s_config.get('api_server', device_config.get('ip')),
            port=k8s_config.get('port', 6443),
            token=k8s_config.get('token', ''),
        )
    
    def _create_docker_collector(self, device_config: Dict[str, Any]):
        """创建Docker采集器"""
        from .api_collector.docker_client import DockerClient, DockerConfig
        
        credentials = device_config.get('credentials', {}).get('docker', {})
        
        config = DockerConfig(
            host=credentials.get('host', f"tcp://{device_config.get('ip')}:2375"),
        )
        
        return DockerClient(config)
    
    def _create_zabbix_collector(self, device_config: Dict[str, Any]):
        """创建Zabbix采集器"""
        from .api_collector.zabbix_client import ZabbixClient
        
        api_config = device_config.get('api', {})
        
        client = ZabbixClient(
            url=api_config.get('base_url'),
            username=api_config.get('username', 'Admin'),
            password=api_config.get('password', 'zabbix'),
        )
        
        return client
    
    def _create_prometheus_collector(self, device_config: Dict[str, Any]):
        """创建Prometheus采集器"""
        from .api_collector.prometheus_client import PrometheusClient
        
        api_config = device_config.get('api', {})
        
        return PrometheusClient(
            url=api_config.get('base_url', f"http://{device_config.get('ip')}:9090"),
        )
    
    def register_collector(self, name: str, collector: Any) -> None:
        """注册采集器实例"""
        self._collectors[name] = collector
    
    def get_collector(self, name: str) -> Optional[Any]:
        """获取已注册的采集器"""
        return self._collectors.get(name)
    
    def remove_collector(self, name: str) -> None:
        """移除采集器"""
        if name in self._collectors:
            del self._collectors[name]


# 全局工厂实例
_factory: Optional[CollectorFactory] = None


def get_factory() -> CollectorFactory:
    """获取全局采集器工厂"""
    global _factory
    if _factory is None:
        _factory = CollectorFactory()
    return _factory
