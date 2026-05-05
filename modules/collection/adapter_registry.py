"""
采集适配器注册器

提供适配器的注册、发现和管理机制
所有采集协议通过注册表统一管理，支持运行时动态注册
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field

# 从core层导入协议类型定义
from core.protocols import ProtocolType

logger = logging.getLogger(__name__)


@dataclass
class AdapterInfo:
    """适配器信息"""
    name: str
    protocol: ProtocolType
    handler_class: Type
    required_credentials: List[str] = field(default_factory=list)
    optional_credentials: List[str] = field(default_factory=list)
    default_port: int = 0
    description: str = ""
    version: str = "1.0"
    capabilities: List[str] = field(default_factory=list)


class AdapterRegistry:
    """
    适配器注册表
    
    管理所有采集协议的适配器，提供统一的适配器发现和创建接口
    
    使用示例:
    >>> registry = AdapterRegistry()
    >>> @registry.register(protocol=ProtocolType.SNMP, name='snmp_v2c')
    ... class MySNMPAdapter:
    ...     pass
    >>> adapter_info = registry.get_adapter('snmp_v2c')
    >>> adapter = registry.create_adapter('snmp_v2c', config)
    """
    
    def __init__(self):
        self._adapters: Dict[str, AdapterInfo] = {}
        self._protocol_handlers: Dict[ProtocolType, Dict[str, Type]] = {}
        self._factories: Dict[str, Callable] = {}
        
        # 初始化内置适配器
        self._register_builtin_adapters()
    
    def _register_builtin_adapters(self) -> None:
        """注册内置适配器"""
        from .snmp_collector.snmp_client import SNMPClient
        from .ssh_collector.ssh_client import SSHClient
        from .ssh_collector.winrm_client import WinRMClient
        from .ipmi_collector.ipmi_client import IPMIClient
        from .api_collector.kubernetes_client import K8sClient
        from .api_collector.docker_client import DockerClient
        from .api_collector.http_client import HTTPClient, VendorAPIClient
        from .api_collector.zabbix_client import ZabbixClient
        from .api_collector.prometheus_client import PrometheusClient
        
        # SNMP适配器
        self.register(
            name='snmp_v2c',
            protocol=ProtocolType.SNMP,
            handler_class=SNMPClient,
            required_credentials=['community'],
            optional_credentials=['security_name', 'auth_password', 'priv_password'],
            default_port=161,
            description='SNMP v2c 采集适配器',
            capabilities=['get', 'walk', 'bulk', 'trap']
        )
        
        # SSH适配器
        self.register(
            name='ssh',
            protocol=ProtocolType.SSH,
            handler_class=SSHClient,
            required_credentials=['username'],
            optional_credentials=['password', 'key_file'],
            default_port=22,
            description='SSH 采集适配器',
            capabilities=['command', 'script', 'sftp']
        )
        
        # WinRM适配器
        self.register(
            name='winrm',
            protocol=ProtocolType.WINRM,
            handler_class=WinRMClient,
            required_credentials=['username'],
            optional_credentials=['password'],
            default_port=5985,
            description='WinRM 采集适配器 (Windows)',
            capabilities=['powershell', 'wmi', 'wql']
        )
        
        # IPMI适配器
        self.register(
            name='ipmi_v2',
            protocol=ProtocolType.IPMI,
            handler_class=IPMIClient,
            required_credentials=['username', 'password'],
            optional_credentials=[],
            default_port=623,
            description='IPMI v2.0 采集适配器',
            capabilities=['sensor', 'sel', 'fru', 'sdr', 'power']
        )
        
        # Kubernetes适配器
        self.register(
            name='kubernetes',
            protocol=ProtocolType.KUBERNETES,
            handler_class=K8sClient,
            required_credentials=['api_server'],
            optional_credentials=['token', 'tls_ca_cert'],
            default_port=6443,
            description='Kubernetes API 采集适配器',
            capabilities=['node', 'pod', 'service', 'deployment', 'event']
        )
        
        # Docker适配器
        self.register(
            name='docker',
            protocol=ProtocolType.DOCKER,
            handler_class=DockerClient,
            required_credentials=['host'],
            optional_credentials=['tls_cert', 'tls_key'],
            default_port=2375,
            description='Docker Engine API 采集适配器',
            capabilities=['container', 'image', 'network', 'volume', 'stats']
        )
        
        # HTTP适配器
        self.register(
            name='http',
            protocol=ProtocolType.HTTP,
            handler_class=HTTPClient,
            required_credentials=['base_url'],
            optional_credentials=['username', 'password', 'api_key', 'token'],
            default_port=443,
            description='HTTP REST API 采集适配器',
            capabilities=['get', 'post', 'put', 'delete', 'websocket']
        )
        
        # Zabbix适配器
        self.register(
            name='zabbix',
            protocol=ProtocolType.ZABBIX,
            handler_class=ZabbixClient,
            required_credentials=['url', 'username'],
            optional_credentials=['password', 'token'],
            default_port=80,
            description='Zabbix API 采集适配器',
            capabilities=['host', 'item', 'history', 'trigger']
        )
        
        # Prometheus适配器
        self.register(
            name='prometheus',
            protocol=ProtocolType.PROMETHEUS,
            handler_class=PrometheusClient,
            required_credentials=['url'],
            optional_credentials=['token'],
            default_port=9090,
            description='Prometheus API 采集适配器',
            capabilities=['query', 'range', 'target', 'rule']
        )
        
        logger.info(f"已注册{len(self._adapters)}个内置适配器")
    
    def register(
        self,
        name: str,
        protocol: ProtocolType,
        handler_class: Type,
        required_credentials: List[str] = None,
        optional_credentials: List[str] = None,
        default_port: int = 0,
        description: str = "",
        version: str = "1.0",
        capabilities: List[str] = None,
    ) -> None:
        """
        注册适配器
        
        Args:
            name: 适配器名称 (唯一标识)
            protocol: 协议类型
            handler_class: 处理器类
            required_credentials: 必需凭据列表
            optional_credentials: 可选凭据列表
            default_port: 默认端口
            description: 描述
            version: 版本
            capabilities: 支持的能力列表
        """
        info = AdapterInfo(
            name=name,
            protocol=protocol,
            handler_class=handler_class,
            required_credentials=required_credentials or [],
            optional_credentials=optional_credentials or [],
            default_port=default_port,
            description=description,
            version=version,
            capabilities=capabilities or [],
        )
        
        self._adapters[name] = info
        
        if protocol not in self._protocol_handlers:
            self._protocol_handlers[protocol] = {}
        self._protocol_handlers[protocol][name] = handler_class
        
        logger.debug(f"注册适配器: {name} ({protocol.value})")
    
    def unregister(self, name: str) -> bool:
        """
        注销适配器
        
        Args:
            name: 适配器名称
            
        Returns:
            是否成功
        """
        if name in self._adapters:
            info = self._adapters[name]
            del self._adapters[name]
            
            if info.protocol in self._protocol_handlers:
                del self._protocol_handlers[info.protocol][name]
            
            logger.debug(f"注销适配器: {name}")
            return True
        
        return False
    
    def get_adapter(self, name: str) -> Optional[AdapterInfo]:
        """
        获取适配器信息
        
        Args:
            name: 适配器名称
            
        Returns:
            适配器信息
        """
        return self._adapters.get(name)
    
    def get_adapters_by_protocol(self, protocol: ProtocolType) -> List[AdapterInfo]:
        """
        获取指定协议的所有适配器
        
        Args:
            protocol: 协议类型
            
        Returns:
            适配器信息列表
        """
        return [info for name, info in self._adapters.items() 
                if info.protocol == protocol]
    
    def list_adapters(self, protocol: ProtocolType = None) -> List[AdapterInfo]:
        """
        列出适配器
        
        Args:
            protocol: 可选的协议过滤
            
        Returns:
            适配器列表
        """
        if protocol:
            return self.get_adapters_by_protocol(protocol)
        return list(self._adapters.values())
    
    def create_adapter(self, name: str, config: Dict[str, Any]) -> Optional[Any]:
        """
        创建适配器实例
        
        Args:
            name: 适配器名称
            config: 适配器配置
            
        Returns:
            适配器实例
        """
        info = self._adapters.get(name)
        if not info:
            logger.error(f"适配器未注册: {name}")
            return None
        
        try:
            handler = info.handler_class(config)
            logger.debug(f"创建适配器实例: {name}")
            return handler
        except Exception as e:
            logger.error(f"创建适配器{name}失败: {e}")
            return None
    
    def has_capability(self, name: str, capability: str) -> bool:
        """
        检查适配器是否具有指定能力
        
        Args:
            name: 适配器名称
            capability: 能力名称
            
        Returns:
            是否具有该能力
        """
        info = self._adapters.get(name)
        if not info:
            return False
        return capability in info.capabilities
    
    def register_factory(self, name: str, factory: Callable) -> None:
        """
        注册适配器工厂函数
        
        Args:
            name: 工厂名称
            factory: 工厂函数
        """
        self._factories[name] = factory
        logger.debug(f"注册适配器工厂: {name}")
    
    def get_factory(self, name: str) -> Optional[Callable]:
        """获取适配器工厂"""
        return self._factories.get(name)


# 全局适配器注册表
_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    """获取全局适配器注册表"""
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry


def register_adapter(**kwargs) -> Callable:
    """
    装饰器: 注册适配器
    
    使用示例:
    >>> @register_adapter(name='my_adapter', protocol=ProtocolType.SNMP)
    ... class MySNMPAdapter:
    ...     pass
    """
    def decorator(cls):
        registry = get_registry()
        registry.register(name=kwargs['name'], 
                        protocol=kwargs['protocol'],
                        handler_class=cls,
                        required_credentials=kwargs.get('required_credentials', []),
                        optional_credentials=kwargs.get('optional_credentials', []),
                        default_port=kwargs.get('default_port', 0),
                        description=kwargs.get('description', ''),
                        capabilities=kwargs.get('capabilities', []))
        return cls
    return decorator


# 便捷函数
def list_protocol_adapters() -> Dict[ProtocolType, List[str]]:
    """列出所有协议及其适配器"""
    registry = get_registry()
    result = {}
    for protocol in ProtocolType:
        adapters = registry.get_adapters_by_protocol(protocol)
        if adapters:
            result[protocol] = [a.name for a in adapters]
    return result


def create_protocol_adapter(protocol: ProtocolType, config: Dict[str, Any]) -> Optional[Any]:
    """根据协议类型创建适配器"""
    registry = get_registry()
    adapters = registry.get_adapters_by_protocol(protocol)
    
    if not adapters:
        logger.error(f"没有找到{protocol.value}协议的适配器")
        return None
    
    # 使用第一个注册的适配器
    return registry.create_adapter(adapters[0].name, config)
