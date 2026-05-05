"""
设备管理服务

提供设备采集的统一入口，协调配置加载器、适配器注册器和采集客户端
支持定时采集、批量采集、故障转移等高级功能
"""

import os
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceStatus(str, Enum):
    """设备状态"""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    COLLECTING = "collecting"


@dataclass
class DeviceMetrics:
    """设备指标数据"""
    device_name: str
    device_ip: str
    device_type: str
    vendor: str
    timestamp: datetime
    status: DeviceStatus
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class DeviceManager:
    """
    设备管理服务
    
    统一管理所有设备的采集，提供：
    - 配置驱动的设备加载
    - 协议自动适配
    - 定时/批量采集
    - 故障转移 (主协议失败自动切换fallback)
    - 指标数据回调
    
    使用示例:
    >>> manager = DeviceManager()
    >>> manager.register_callback(lambda metrics: print(metrics))
    >>> manager.start()
    >>> 
    >>> # 手动采集单个设备
    >>> result = await manager.collect_device('Web服务器-01')
    """
    
    def __init__(self, config_dir: str = None):
        """
        初始化设备管理服务
        
        Args:
            config_dir: 配置目录路径
        """
        # 导入并初始化配置加载器
        from .config_loader import get_config_loader
        
        self._config_loader = get_config_loader(config_dir)
        self._registry = self._load_registry()
        
        # 设备状态缓存
        self._device_status: Dict[str, DeviceStatus] = {}
        self._last_collect_time: Dict[str, datetime] = {}
        self._last_metrics: Dict[str, DeviceMetrics] = {}
        
        # 采集回调
        self._collect_callbacks: List[Callable[[DeviceMetrics], None]] = []
        
        # 异步支持
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._running = False
        self._collect_tasks: List[asyncio.Task] = []
        
        # 统计信息
        self._stats = {
            'total_collects': 0,
            'successful_collects': 0,
            'failed_collects': 0,
            'protocol_fallbacks': 0,
        }
    
    def _load_registry(self):
        """加载适配器注册表"""
        from .adapter_registry import get_registry
        return get_registry()
    
    def register_callback(self, callback: Callable[[DeviceMetrics], None]) -> None:
        """
        注册指标采集回调
        
        Args:
            callback: 回调函数，接收DeviceMetrics参数
        """
        self._collect_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[DeviceMetrics], None]) -> None:
        """注销回调"""
        if callback in self._collect_callbacks:
            self._collect_callbacks.remove(callback)
    
    def _notify_callbacks(self, metrics: DeviceMetrics) -> None:
        """触发回调"""
        for callback in self._collect_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
    
    def get_device_status(self, device_name: str) -> DeviceStatus:
        """获取设备状态"""
        return self._device_status.get(device_name, DeviceStatus.UNKNOWN)
    
    def get_last_metrics(self, device_name: str) -> Optional[DeviceMetrics]:
        """获取设备最近一次指标"""
        return self._last_metrics.get(device_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取采集统计"""
        stats = self._stats.copy()
        stats['device_count'] = len(self._config_loader.get_devices())
        stats['running'] = self._running
        return stats
    
    async def collect_device(self, device_name: str, force_protocol: str = None) -> Optional[DeviceMetrics]:
        """
        采集单个设备指标
        
        Args:
            device_name: 设备名称
            force_protocol: 强制使用的协议 (不适用fallback)
            
        Returns:
            设备指标数据
        """
        device_config = self._config_loader.get_device_by_name(device_name)
        if not device_config:
            logger.error(f"设备未找到: {device_name}")
            return None
        
        # 更新状态
        self._device_status[device_name] = DeviceStatus.COLLECTING
        
        # 确定使用的协议
        if force_protocol:
            protocols = [force_protocol]
        else:
            protocols = self._get_device_protocols(device_config)
        
        # 尝试各协议
        last_error = None
        for protocol in protocols:
            try:
                metrics = await self._collect_with_protocol(device_config, protocol)
                
                if metrics:
                    metrics.status = DeviceStatus.ONLINE
                    self._device_status[device_name] = DeviceStatus.ONLINE
                    self._last_collect_time[device_name] = datetime.now()
                    self._last_metrics[device_name] = metrics
                    self._notify_callbacks(metrics)
                    
                    self._stats['total_collects'] += 1
                    self._stats['successful_collects'] += 1
                    
                    return metrics
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"设备{device_name}使用{protocol}协议采集失败: {e}")
                continue
        
        # 所有协议都失败
        metrics = DeviceMetrics(
            device_name=device_name,
            device_ip=device_config.get('ip', ''),
            device_type=device_config.get('type', ''),
            vendor=device_config.get('vendor', ''),
            timestamp=datetime.now(),
            status=DeviceStatus.OFFLINE,
            error=last_error,
        )
        
        self._device_status[device_name] = DeviceStatus.OFFLINE
        self._last_metrics[device_name] = metrics
        self._notify_callbacks(metrics)
        
        self._stats['total_collects'] += 1
        self._stats['failed_collects'] += 1
        
        return metrics
    
    async def _collect_with_protocol(self, device_config: Dict, protocol: str) -> Optional[DeviceMetrics]:
        """使用指定协议采集"""
        loop = asyncio.get_event_loop()
        
        if protocol == 'snmp':
            return await loop.run_in_executor(
                self._executor, 
                self._collect_snmp, 
                device_config
            )
        elif protocol == 'ssh':
            return await loop.run_in_executor(
                self._executor,
                self._collect_ssh,
                device_config
            )
        elif protocol == 'winrm':
            return await loop.run_in_executor(
                self._executor,
                self._collect_winrm,
                device_config
            )
        elif protocol == 'ipmi':
            return await loop.run_in_executor(
                self._executor,
                self._collect_ipmi,
                device_config
            )
        elif protocol == 'http':
            return await loop.run_in_executor(
                self._executor,
                self._collect_http,
                device_config
            )
        elif protocol == 'kubernetes':
            return await loop.run_in_executor(
                self._executor,
                self._collect_kubernetes,
                device_config
            )
        elif protocol == 'docker':
            return await loop.run_in_executor(
                self._executor,
                self._collect_docker,
                device_config
            )
        elif protocol == 'zabbix':
            return await loop.run_in_executor(
                self._executor,
                self._collect_zabbix,
                device_config
            )
        elif protocol == 'prometheus':
            return await loop.run_in_executor(
                self._executor,
                self._collect_prometheus,
                device_config
            )
        else:
            logger.error(f"不支持的协议: {protocol}")
            return None
    
    def _get_device_protocols(self, device_config: Dict) -> List[str]:
        """获取设备的可用协议列表 (按优先级)"""
        protocols_config = device_config.get('protocols', {})
        
        primary = protocols_config.get('primary')
        fallback = protocols_config.get('fallback')
        
        protocols = []
        if primary:
            protocols.append(primary)
        if fallback and fallback != primary:
            protocols.append(fallback)
        
        # 如果没有配置，默认使用SNMP
        if not protocols:
            protocols = ['snmp']
        
        return protocols
    
    def _collect_snmp(self, device_config: Dict) -> DeviceMetrics:
        """SNMP采集"""
        from .snmp_collector.snmp_client import SNMPClient, SNMPConfig, SNMPVersion
        
        credentials = device_config.get('credentials', {}).get('snmp', {})
        
        config = SNMPConfig(
            host=device_config.get('ip'),
            port=device_config.get('port', 161),
            version=SNMPVersion(credentials.get('version', 'v2c')),
            community=credentials.get('community', 'public'),
            timeout=30,
        )
        
        client = SNMPClient(config)
        client.connect()
        
        # 采集系统信息
        metrics_data = client.collect_all_metrics()
        
        client.close()
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type=device_config.get('type'),
            vendor=device_config.get('vendor'),
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    def _collect_ssh(self, device_config: Dict) -> DeviceMetrics:
        """SSH采集"""
        from .ssh_collector.ssh_client import SSHClient, SSHConfig
        
        credentials = device_config.get('credentials', {}).get('ssh', {})
        
        config = SSHConfig(
            host=device_config.get('ip'),
            port=credentials.get('port', 22),
            username=credentials.get('username', 'root'),
            password=credentials.get('password', ''),
            key_file=credentials.get('key_file'),
        )
        
        client = SSHClient(config)
        
        if not client.connect():
            raise Exception("SSH连接失败")
        
        # 采集系统信息
        metrics_data = {
            'uptime': client.execute_command('uptime'),
            'cpu': client.execute_command('cat /proc/cpuinfo | grep processor | wc -l'),
            'memory': client.execute_command('free -m'),
        }
        
        client.close()
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type=device_config.get('type'),
            vendor=device_config.get('vendor'),
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    def _collect_winrm(self, device_config: Dict) -> DeviceMetrics:
        """WinRM采集"""
        from .ssh_collector.winrm_client import WinRMClient, WinRMConfig
        
        credentials = device_config.get('credentials', {}).get('winrm', {})
        
        config = WinRMConfig(
            host=device_config.get('ip'),
            port=credentials.get('port', 5985),
            username=credentials.get('username', 'Administrator'),
            password=credentials.get('password', ''),
            ssl=credentials.get('ssl', False),
        )
        
        client = WinRMClient(config)
        
        if not client.connect():
            raise Exception("WinRM连接失败")
        
        # 采集WMI数据
        metrics_data = client.collect_all_metrics()
        
        client.close()
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type=device_config.get('type'),
            vendor=device_config.get('vendor'),
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    def _collect_ipmi(self, device_config: Dict) -> DeviceMetrics:
        """IPMI采集"""
        from .ipmi_collector.ipmi_client import IPMIClient, IPMIConfig, IPMIVersion
        
        credentials = device_config.get('credentials', {}).get('ipmi', {})
        
        config = IPMIConfig(
            host=device_config.get('ipmi_ip', device_config.get('ip')),
            port=credentials.get('port', 623),
            username=credentials.get('username', 'admin'),
            password=credentials.get('password', ''),
            version=IPMIVersion(credentials.get('version', '2.0')),
        )
        
        client = IPMIClient(config)
        
        if not client.connect():
            raise Exception("IPMI连接失败")
        
        # 采集传感器数据
        metrics_data = client.collect_all_metrics()
        
        client.close()
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type=device_config.get('type'),
            vendor=device_config.get('vendor'),
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    def _collect_http(self, device_config: Dict) -> DeviceMetrics:
        """HTTP API采集"""
        from .api_collector.http_client import HTTPClient, VendorAPIClient
        
        api_config = device_config.get('api', {})
        vendor = device_config.get('vendor', '')
        
        if vendor in ['zabbix', 'prometheus', 'topsec', 'nsfocus', 'sangfor', 'venustech']:
            # 使用厂商特定适配器
            adapter = VendorAPIClient(vendor=vendor)
            adapter.configure(
                base_url=api_config.get('base_url'),
                auth_type=api_config.get('auth_type'),
                username=api_config.get('username'),
                password=api_config.get('password'),
                api_key=api_config.get('api_key'),
            )
            metrics_data = adapter.collect_metrics()
        else:
            # 使用通用HTTP客户端
            client = HTTPClient(base_url=api_config.get('base_url', f"http://{device_config.get('ip')}"))
            
            if api_config.get('username'):
                client.set_basic_auth(api_config['username'], api_config.get('password', ''))
            
            metrics_data = client.get('/api/status') if client.health_check() else {}
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type=device_config.get('type'),
            vendor=vendor,
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    def _collect_kubernetes(self, device_config: Dict) -> DeviceMetrics:
        """Kubernetes采集"""
        from .api_collector.kubernetes_client import K8sClient
        
        k8s_config = device_config.get('kubernetes', {})
        
        client = K8sClient(
            host=k8s_config.get('api_server', device_config.get('ip')),
            port=6443,
            token=k8s_config.get('token', ''),
        )
        
        if not client.connect():
            raise Exception("K8s API连接失败")
        
        # 采集集群指标
        metrics_data = client.collect_all_metrics()
        
        client.close()
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type='container',
            vendor='kubernetes',
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    def _collect_docker(self, device_config: Dict) -> DeviceMetrics:
        """Docker采集"""
        from .api_collector.docker_client import DockerClient, DockerConfig
        
        credentials = device_config.get('credentials', {}).get('docker', {})
        
        config = DockerConfig(
            host=credentials.get('host', f"tcp://{device_config.get('ip')}:2375"),
        )
        
        client = DockerClient(config)
        
        if not client.connect():
            raise Exception("Docker连接失败")
        
        # 采集容器指标
        metrics_data = client.collect_all_metrics()
        
        client.close()
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type='container',
            vendor='docker',
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    def _collect_zabbix(self, device_config: Dict) -> DeviceMetrics:
        """Zabbix采集"""
        from .api_collector.zabbix_client import ZabbixClient
        
        api_config = device_config.get('api', {})
        
        client = ZabbixClient(
            url=api_config.get('base_url'),
            username=api_config.get('username', 'Admin'),
            password=api_config.get('password', 'zabbix'),
        )
        
        if not client.login():
            raise Exception("Zabbix登录失败")
        
        # 采集Zabbix数据
        metrics_data = client.get_all_metrics()
        
        client.logout()
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type='monitor',
            vendor='zabbix',
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    def _collect_prometheus(self, device_config: Dict) -> DeviceMetrics:
        """Prometheus采集"""
        from .api_collector.prometheus_client import PrometheusClient
        
        api_config = device_config.get('api', {})
        
        client = PrometheusClient(
            url=api_config.get('base_url', f"http://{device_config.get('ip')}:9090"),
        )
        
        # 采集Prometheus数据
        metrics_data = {
            'targets': client.get_targets(),
        }
        
        return DeviceMetrics(
            device_name=device_config.get('name'),
            device_ip=device_config.get('ip'),
            device_type='monitor',
            vendor='prometheus',
            timestamp=datetime.now(),
            status=DeviceStatus.ONLINE,
            metrics=metrics_data,
        )
    
    async def collect_all(self, enabled_only: bool = True) -> List[DeviceMetrics]:
        """
        批量采集所有设备
        
        Args:
            enabled_only: 只采集已启用的设备
            
        Returns:
            采集结果列表
        """
        devices = self._config_loader.get_devices(enabled_only=enabled_only)
        
        tasks = [self.collect_device(d.get('name')) for d in devices]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤异常
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"采集异常: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def start_periodic_collect(self, interval: int = 60) -> None:
        """
        启动定时采集任务
        
        Args:
            interval: 采集间隔 (秒)
        """
        self._running = True
        
        while self._running:
            try:
                await self.collect_all()
            except Exception as e:
                logger.error(f"定时采集失败: {e}")
            
            await asyncio.sleep(interval)
    
    def stop(self) -> None:
        """停止定时采集"""
        self._running = False
        for task in self._collect_tasks:
            task.cancel()
        self._executor.shutdown(wait=False)


# 全局设备管理器实例
_device_manager: Optional[DeviceManager] = None


def get_device_manager(config_dir: str = None) -> DeviceManager:
    """获取全局设备管理器"""
    global _device_manager
    
    if _device_manager is None:
        _device_manager = DeviceManager(config_dir)
    
    return _device_manager


# 便捷函数
async def collect_device(name: str, protocol: str = None) -> Optional[DeviceMetrics]:
    """采集单个设备"""
    return await get_device_manager().collect_device(name, protocol)


async def collect_all_devices(enabled_only: bool = True) -> List[DeviceMetrics]:
    """批量采集所有设备"""
    return await get_device_manager().collect_all(enabled_only)


def get_device_status(name: str) -> DeviceStatus:
    """获取设备状态"""
    return get_device_manager().get_device_status(name)


def register_collect_callback(callback: Callable[[DeviceMetrics], None]) -> None:
    """注册采集回调"""
    get_device_manager().register_callback(callback)
