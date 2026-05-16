# -*- coding: utf-8 -*-
"""
设备管理服务

提供设备采集的统一入口，协调配置加载器、适配器注册器和采集客户端
支持定时采集、批量采集、故障转移等高级功能
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

logger = logging.getLogger(__name__)


class CollectionStatus(str, Enum):
    """采集状态"""
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
    status: 'CollectionStatus'
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# 别名，保持向后兼容
DeviceStatus = CollectionStatus


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
    
    def get_device_status(self, device_name: str) -> CollectionStatus:
        """获取设备状态"""
        return self._device_status.get(device_name, CollectionStatus.UNKNOWN)
    
    def _update_device_status_in_db(self, device_name: str, status: CollectionStatus) -> None:
        """更新数据库中的设备状态"""
        try:
            from modules.foundation.db_models.device import Device, DeviceStatus as DBDeviceStatus
            from modules.foundation.db.client import get_db_session
            
            # 映射状态
            status_mapping = {
                CollectionStatus.ONLINE: DBDeviceStatus.ONLINE,
                CollectionStatus.OFFLINE: DBDeviceStatus.OFFLINE,
                CollectionStatus.WARNING: DBDeviceStatus.WARNING,
                CollectionStatus.UNKNOWN: DBDeviceStatus.UNKNOWN,
            }
            db_status = status_mapping.get(status, DBDeviceStatus.OFFLINE)
            
            with get_db_session() as session:
                device = session.query(Device).filter(Device.name == device_name).first()
                if device:
                    device.status = db_status
                    session.commit()
                    logger.debug(f"更新设备 {device_name} 状态为 {status.value}")
        except Exception as e:
            logger.warning(f"更新设备状态到数据库失败: {e}")
    
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
        self._device_status[device_name] = CollectionStatus.COLLECTING
        
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
                    metrics.status = CollectionStatus.ONLINE
                    self._device_status[device_name] = CollectionStatus.ONLINE
                    self._last_collect_time[device_name] = datetime.now()
                    self._last_metrics[device_name] = metrics
                    self._notify_callbacks(metrics)
                    
                    self._stats['total_collects'] += 1
                    self._stats['successful_collects'] += 1
                    
                    # 更新数据库中的设备状态
                    self._update_device_status_in_db(device_name, CollectionStatus.ONLINE)
                    
                    return metrics
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"设备{device_name}使用{protocol}协议采集失败: {e}")
                self._stats['protocol_fallbacks'] += 1
                continue
        
        # 所有协议都失败
        metrics = DeviceMetrics(
            device_name=device_name,
            device_ip=device_config.get('ip', ''),
            device_type=device_config.get('type', ''),
            vendor=device_config.get('vendor', ''),
            timestamp=datetime.now(),
            status=CollectionStatus.OFFLINE,
            error=last_error,
        )
        
        self._device_status[device_name] = CollectionStatus.OFFLINE
        self._last_metrics[device_name] = metrics
        self._notify_callbacks(metrics)
        
        self._stats['total_collects'] += 1
        self._stats['failed_collects'] += 1
        
        # 更新数据库中的设备状态
        self._update_device_status_in_db(device_name, CollectionStatus.OFFLINE)
        
        return metrics
    
    async def _collect_with_protocol(self, device_config: Dict, protocol: str) -> Optional[DeviceMetrics]:
        """
        使用指定协议采集
        
        委托给 CollectorFactory 创建采集器执行采集
        """
        loop = asyncio.get_event_loop()
        
        # 使用工厂模式创建采集器
        from .collector_factory import get_factory
        factory = get_factory()
        
        try:
            collector = factory.create_collector(device_config)
        except Exception as e:
            logger.error(f"创建采集器失败: {e}")
            return None
        
        # 根据不同采集器类型执行采集
        collector_type = type(collector).__name__
        
        try:
            if 'SNMP' in collector_type:
                return await loop.run_in_executor(
                    self._executor, 
                    self._collect_snmp, 
                    collector, 
                    device_config
                )
            elif 'SSH' in collector_type or 'WinRM' in collector_type:
                return await loop.run_in_executor(
                    self._executor,
                    self._collect_ssh_based,
                    collector,
                    device_config
                )
            elif 'IPMI' in collector_type:
                return await loop.run_in_executor(
                    self._executor,
                    self._collect_ipmi,
                    collector,
                    device_config
                )
            elif 'HTTP' in collector_type or 'Zabbix' in collector_type or 'Prometheus' in collector_type:
                return await loop.run_in_executor(
                    self._executor,
                    self._collect_http_based,
                    collector,
                    device_config
                )
            elif 'K8s' in collector_type or 'Docker' in collector_type:
                return await loop.run_in_executor(
                    self._executor,
                    self._collect_api_based,
                    collector,
                    device_config
                )
            else:
                # 通用采集
                return await loop.run_in_executor(
                    self._executor,
                    self._collect_generic,
                    collector,
                    device_config
                )
        except Exception as e:
            logger.error(f"采集执行失败: {e}")
            raise
    
    def _collect_snmp(self, collector, device_config: Dict) -> DeviceMetrics:
        """SNMP采集"""
        try:
            collector.connect()
            metrics_data = collector.collect_all()
            collector.close()
            
            return DeviceMetrics(
                device_name=device_config.get('name'),
                device_ip=device_config.get('ip'),
                device_type=device_config.get('type'),
                vendor=device_config.get('vendor'),
                timestamp=datetime.now(),
                status=CollectionStatus.ONLINE,
                metrics=metrics_data,
            )
        except Exception as e:
            logger.error(f"SNMP采集失败: {e}")
            raise
    
    def _collect_ssh_based(self, collector, device_config: Dict) -> DeviceMetrics:
        """SSH/WinRM采集"""
        try:
            collector.connect()
            
            # 根据类型调用不同方法
            collector_type = type(collector).__name__
            if 'WinRM' in collector_type:
                metrics_data = collector.collect_all_metrics()
            else:
                metrics_data = {
                    'uptime': collector.execute('uptime'),
                    'hostname': collector.execute('hostname'),
                    'cpu_idle': collector.execute("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"),
                    'mem_info': collector.execute('free -m | grep Mem | awk "{print $3\",\"$2}"'),
                    'disk_usage': collector.execute('df -h | grep -E "^/dev" | awk "{print $1\":\"$5}"'),
                    'load_avg': collector.execute('uptime | awk -F"load average:" "{print $2}"'),
                }
            
            collector.close()
            
            return DeviceMetrics(
                device_name=device_config.get('name'),
                device_ip=device_config.get('ip'),
                device_type=device_config.get('type'),
                vendor=device_config.get('vendor'),
                timestamp=datetime.now(),
                status=CollectionStatus.ONLINE,
                metrics=metrics_data,
            )
        except Exception as e:
            logger.error(f"SSH采集失败: {e}")
            raise
    
    def _collect_ipmi(self, collector, device_config: Dict) -> DeviceMetrics:
        """IPMI采集"""
        try:
            collector.connect()
            metrics_data = collector.collect_all()
            collector.close()
            
            return DeviceMetrics(
                device_name=device_config.get('name'),
                device_ip=device_config.get('ip'),
                device_type=device_config.get('type'),
                vendor=device_config.get('vendor'),
                timestamp=datetime.now(),
                status=CollectionStatus.ONLINE,
                metrics=metrics_data,
            )
        except Exception as e:
            logger.error(f"IPMI采集失败: {e}")
            raise
    
    def _collect_http_based(self, collector, device_config: Dict) -> DeviceMetrics:
        """HTTP API采集"""
        try:
            collector_type = type(collector).__name__
            
            if 'Zabbix' in collector_type:
                collector.login()
                metrics_data = collector.get_all_metrics()
                collector.logout()
            elif 'Prometheus' in collector_type:
                metrics_data = collector.get_targets()
            elif 'Vendor' in collector_type:
                metrics_data = collector.collect_metrics()
            else:
                metrics_data = collector.get('/api/status') if hasattr(collector, 'get') else {}
            
            return DeviceMetrics(
                device_name=device_config.get('name'),
                device_ip=device_config.get('ip'),
                device_type=device_config.get('type'),
                vendor=device_config.get('vendor'),
                timestamp=datetime.now(),
                status=CollectionStatus.ONLINE,
                metrics=metrics_data,
            )
        except Exception as e:
            logger.error(f"HTTP采集失败: {e}")
            raise
    
    def _collect_api_based(self, collector, device_config: Dict) -> DeviceMetrics:
        """K8s/Docker采集"""
        try:
            collector.connect()
            metrics_data = collector.collect_all()
            collector.close()
            
            return DeviceMetrics(
                device_name=device_config.get('name'),
                device_ip=device_config.get('ip'),
                device_type=device_config.get('type'),
                vendor=device_config.get('vendor'),
                timestamp=datetime.now(),
                status=CollectionStatus.ONLINE,
                metrics=metrics_data,
            )
        except Exception as e:
            logger.error(f"API采集失败: {e}")
            raise
    
    def _collect_generic(self, collector, device_config: Dict) -> DeviceMetrics:
        """通用采集"""
        try:
            metrics_data = collector.collect() if hasattr(collector, 'collect') else {}
            
            return DeviceMetrics(
                device_name=device_config.get('name'),
                device_ip=device_config.get('ip'),
                device_type=device_config.get('type'),
                vendor=device_config.get('vendor'),
                timestamp=datetime.now(),
                status=CollectionStatus.ONLINE,
                metrics=metrics_data,
            )
        except Exception as e:
            logger.error(f"通用采集失败: {e}")
            raise
    
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

    def is_metric_enabled(self, device_id: int, metric_name: str) -> bool:
        """
        检查设备指标是否启用采集
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            
        Returns:
            是否启用采集，未配置则默认启用
        """
        try:
            from modules.foundation.db_models.monitoring import DeviceMetricConfig
            from modules.foundation.db.client import get_db_session
            
            with get_db_session() as session:
                config = session.query(DeviceMetricConfig).filter(
                    DeviceMetricConfig.device_id == device_id,
                    DeviceMetricConfig.metric_name == metric_name
                ).first()
                
                if config is None:
                    # 未配置则默认启用
                    return True
                return config.enabled
        except Exception as e:
            logger.warning(f"检查指标启用状态失败: {e}")
            return True  # 出错时默认启用
    
    def get_metric_interval(self, device_id: int, metric_name: str) -> Optional[int]:
        """
        获取设备指标采集间隔
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            
        Returns:
            采集间隔(秒)，未配置返回None
        """
        try:
            from modules.foundation.db_models.monitoring import DeviceMetricConfig
            from modules.foundation.db.client import get_db_session
            
            with get_db_session() as session:
                config = session.query(DeviceMetricConfig).filter(
                    DeviceMetricConfig.device_id == device_id,
                    DeviceMetricConfig.metric_name == metric_name
                ).first()
                
                if config is None:
                    return None
                return config.collect_interval if config.collect_interval > 0 else None
        except Exception as e:
            logger.warning(f"获取指标采集间隔失败: {e}")
            return None
    
    def get_metric_params(self, device_id: int, metric_name: str) -> Optional[str]:
        """
        获取设备指标自定义参数
        
        Args:
            device_id: 设备ID
            metric_name: 指标名称
            
        Returns:
            自定义参数字符串，未配置返回None
        """
        try:
            from modules.foundation.db_models.monitoring import DeviceMetricConfig
            from modules.foundation.db.client import get_db_session
            
            with get_db_session() as session:
                config = session.query(DeviceMetricConfig).filter(
                    DeviceMetricConfig.device_id == device_id,
                    DeviceMetricConfig.metric_name == metric_name
                ).first()
                
                if config is None:
                    return None
                return config.params
        except Exception as e:
            logger.warning(f"获取指标自定义参数失败: {e}")
            return None


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
