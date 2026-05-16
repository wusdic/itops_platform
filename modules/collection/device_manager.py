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
    
    def _get_device_config_from_db(self, device_name: str) -> Optional[Dict[str, Any]]:
        """
        从MySQL数据库获取设备配置（用于采集）
        
        从数据库读取设备信息，转换为采集所需的配置格式。
        如果设备在YAML配置中也有定义，YAML中的协议/凭据配置优先。
        
        Args:
            device_name: 设备名称
            
        Returns:
            设备配置字典，如果设备不存在则返回None
        """
        try:
            from modules.foundation.db_models.device import Device, DeviceType as DBDeviceType
            from modules.foundation.db_models.base import _db_manager
            
            with _db_manager.session_scope() as session:
                # 按名称或主机名查询设备
                device = session.query(Device).filter(
                    (Device.name == device_name) | (Device.hostname == device_name)
                ).first()
                
                if not device:
                    return None
                
                # 构建基础配置
                config = {
                    'name': device.name,
                    'ip': device.ip_address,
                    'type': self._map_db_device_type(device.device_type),
                    'vendor': device.vendor or device.manufacturer,
                    'os': device.os_type,
                    'os_version': device.os_version,
                    'monitor_enabled': device.monitor_enabled if device.monitor_enabled is not None else True,
                    'protocols': {},
                    'credentials': {},
                    'collect': {
                        'enabled': device.monitor_enabled if device.monitor_enabled is not None else True,
                    },
                    '_db_device_id': device.id,
                }
                
                # 添加SSH配置
                if device.ssh_port:
                    config['ssh_port'] = device.ssh_port
                if device.ssh_username:
                    config['credentials']['ssh_username'] = device.ssh_username
                if device.ssh_password_encrypted:
                    config['credentials']['ssh_password'] = device.ssh_password_encrypted
                if device.ssh_key_path:
                    config['credentials']['ssh_key_path'] = device.ssh_key_path
                
                # 添加SNMP配置
                if device.snmp_enabled:
                    config['protocols']['snmp'] = {
                        'enabled': True,
                        'community': device.snmp_community or 'public',
                        'version': device.snmp_version or 'v2c',
                    }
                
                # 检查YAML配置是否覆盖凭据/协议
                yaml_config = self._config_loader.get_device_by_name(device_name)
                if yaml_config:
                    # YAML中的protocols和credentials优先
                    if yaml_config.get('protocols'):
                        config['protocols'].update(yaml_config['protocols'])
                    if yaml_config.get('credentials'):
                        config['credentials'].update(yaml_config['credentials'])
                    # YAML中的采集配置
                    if yaml_config.get('collect'):
                        config['collect'].update(yaml_config['collect'])
                
                return config
                
        except Exception as e:
            logger.warning(f"从数据库获取设备配置失败: {e}")
            return None
    
    def _map_db_device_type(self, db_device_type) -> str:
        """将数据库设备类型映射为采集配置类型"""
        if db_device_type is None:
            return 'server'
        
        type_str = db_device_type.value if hasattr(db_device_type, 'value') else str(db_device_type)
        
        mapping = {
            'server_windows': 'server',
            'server_linux': 'server',
            'server_vmware': 'virtual',
            'server_hyperv': 'virtual',
            'server_kvm': 'virtual',
            'network_switch': 'network',
            'network_router': 'network',
            'network_firewall': 'security',
            'network_waf': 'security',
            'network_loadbalancer': 'network',
            'network_vpn': 'security',
            'network_ap': 'network',
            'network_ac': 'network',
            'security_ids': 'security',
            'security_ips': 'security',
            'security_antivirus': 'server',
            'storage_array': 'storage',
            'storage_nas': 'storage',
            'storage_tape': 'storage',
            'other': 'server',
        }
        return mapping.get(type_str, 'server')
    
    def get_devices_from_db(self) -> List[Dict[str, Any]]:
        """
        从MySQL数据库获取所有设备列表（用于采集）
        
        Returns:
            设备配置列表
        """
        try:
            from modules.foundation.db_models.device import Device
            from modules.foundation.db_models.base import _db_manager
            
            devices = []
            with _db_manager.session_scope() as session:
                db_devices = session.query(Device).all()
                for d in db_devices:
                    # 跳过退役设备
                    if hasattr(d, 'status') and d.status and d.status.value == 'decommissioned':
                        continue
                    # 跳过未启用监控的设备
                    if d.monitor_enabled is False:
                        continue
                    
                    config = {
                        'name': d.name,
                        'ip': d.ip_address,
                        'type': self._map_db_device_type(d.device_type),
                        'vendor': d.vendor or d.manufacturer,
                        'os': d.os_type,
                        'os_version': d.os_version,
                        'monitor_enabled': d.monitor_enabled if d.monitor_enabled is not None else True,
                    }
                    devices.append(config)
            
            return devices
            
        except Exception as e:
            logger.warning(f"从数据库获取设备列表失败: {e}")
            return []
    
    def _update_device_status_in_db(self, device_name: str, status: CollectionStatus) -> None:
        """更新数据库中的设备状态"""
        try:
            from modules.foundation.db_models.device import Device, DeviceStatus as DBDeviceStatus
            from modules.foundation.db_models.base import _db_manager

            # 映射状态
            status_mapping = {
                CollectionStatus.ONLINE: DBDeviceStatus.ONLINE,
                CollectionStatus.OFFLINE: DBDeviceStatus.OFFLINE,
                CollectionStatus.ERROR: DBDeviceStatus.WARNING,
                CollectionStatus.UNKNOWN: DBDeviceStatus.UNKNOWN,
            }
            db_status = status_mapping.get(status, DBDeviceStatus.OFFLINE)

            with _db_manager.session_scope() as session:
                device = session.query(Device).filter(Device.name == device_name).first()
                if device:
                    device.status = db_status.value  # 使用字符串值而非枚举对象
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
        # 优先使用MySQL设备数，回退到YAML配置设备数
        db_devices = self.get_devices_from_db()
        yaml_devices = self._config_loader.get_devices()
        stats['device_count'] = len(db_devices) if db_devices else len(yaml_devices)
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
        # 优先从MySQL数据库获取设备配置，失败时回退到YAML配置
        device_config = self._get_device_config_from_db(device_name)
        if not device_config:
            # 回退到YAML配置文件
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
                
                if metrics and metrics.status == CollectionStatus.ONLINE:
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
        device_name = device_config.get('name')
        device_ip = device_config.get('ip')
        try:
            # 先 ping 检测连通性（采集前验证）
            ping_ok = self._ping_device(device_ip)
            if not ping_ok:
                logger.warning(f"Ping检测失败: {device_ip}，标记为OFFLINE")
                collector.close()
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )

            collector.connect()
            metrics_data = {}
            try:
                # SNMPDevice 有 collect_all() 方法，直接调用
                if hasattr(collector, 'collect_all'):
                    metrics_data = collector.collect_all()
                else:
                    metrics_data = {}
            except Exception as e:
                logger.warning(f"SNMP采集异常: {e}")
                metrics_data = {}
            collector.close()

            # 采集结果判断：metrics_data 为空说明 SNMP 库不可用或连接失败 → OFFLINE
            if not metrics_data or not metrics_data.get('system'):
                logger.warning(f"SNMP采集无数据: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics=metrics_data,
                )

            return DeviceMetrics(
                device_name=device_name,
                device_ip=device_ip,
                device_type=device_config.get('type'),
                vendor=device_config.get('vendor'),
                timestamp=datetime.now(),
                status=CollectionStatus.ONLINE,
                metrics=metrics_data,
            )
        except Exception as e:
            logger.error(f"SNMP采集失败: {e}")
            raise

    def _ping_device(self, ip: str, timeout: int = 3) -> bool:
        """TCP 端口连通性检测（采集前验证，替代 ping）"""
        import socket
        # 常见端口优先尝试：SSH(22)、HTTP(80)、HTTPS(443)、MySQL(3306)
        ports = [22, 80, 443, 3306, 6379, 8080]
        for port in ports:
            try:
                with socket.create_connection((ip, port), timeout=timeout):
                    return True
            except (socket.timeout, socket.error, OSError):
                continue
        return False

    def _collect_ssh_based(self, collector, device_config: Dict) -> DeviceMetrics:
        """SSH/WinRM采集"""
        device_name = device_config.get('name')
        device_ip = device_config.get('ip')
        try:
            # Ping 检测连通性
            ping_ok = self._ping_device(device_ip)
            if not ping_ok:
                logger.warning(f"Ping检测失败: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )

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

            # 空数据判断
            if not metrics_data or not metrics_data.get('hostname'):
                logger.warning(f"SSH采集无数据: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics=metrics_data,
                )

            return DeviceMetrics(
                device_name=device_name,
                device_ip=device_ip,
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
        device_name = device_config.get('name')
        device_ip = device_config.get('ip')
        try:
            ping_ok = self._ping_device(device_ip)
            if not ping_ok:
                logger.warning(f"Ping检测失败: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )
            collector.connect()
            metrics_data = collector.collect_all_metrics()
            collector.close()

            if not metrics_data:
                logger.warning(f"IPMI采集无数据: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )

            return DeviceMetrics(
                device_name=device_name,
                device_ip=device_ip,
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
        device_name = device_config.get('name')
        device_ip = device_config.get('ip')
        try:
            ping_ok = self._ping_device(device_ip)
            if not ping_ok:
                logger.warning(f"Ping检测失败: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )

            collector_type = type(collector).__name__

            if 'Zabbix' in collector_type:
                auth_token = collector.login()
                metrics_data = {'auth_token': auth_token} if auth_token else {}
                collector.logout()
            elif 'Prometheus' in collector_type:
                metrics_data = collector.targets()
            elif 'Vendor' in collector_type:
                metrics_data = collector.collect_metrics()
            else:
                metrics_data = collector.get('/api/status') if hasattr(collector, 'get') else {}

            if not metrics_data:
                logger.warning(f"HTTP采集无数据: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )

            return DeviceMetrics(
                device_name=device_name,
                device_ip=device_ip,
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
        device_name = device_config.get('name')
        device_ip = device_config.get('ip')
        try:
            ping_ok = self._ping_device(device_ip)
            if not ping_ok:
                logger.warning(f"Ping检测失败: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )
            collector.connect()
            metrics_data = collector.collect_all_metrics()
            collector.close()

            if not metrics_data:
                logger.warning(f"API采集无数据: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )

            return DeviceMetrics(
                device_name=device_name,
                device_ip=device_ip,
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
        device_name = device_config.get('name')
        device_ip = device_config.get('ip')
        try:
            ping_ok = self._ping_device(device_ip)
            if not ping_ok:
                logger.warning(f"Ping检测失败: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )
            metrics_data = collector.collect() if hasattr(collector, 'collect') else {}

            if not metrics_data:
                logger.warning(f"通用采集无数据: {device_ip}，标记为OFFLINE")
                return DeviceMetrics(
                    device_name=device_name,
                    device_ip=device_ip,
                    device_type=device_config.get('type'),
                    vendor=device_config.get('vendor'),
                    timestamp=datetime.now(),
                    status=CollectionStatus.OFFLINE,
                    metrics={},
                )

            return DeviceMetrics(
                device_name=device_name,
                device_ip=device_ip,
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
        
        优先从MySQL数据库获取设备列表，失败时回退到YAML配置。
        
        Args:
            enabled_only: 只采集已启用的设备
            
        Returns:
            采集结果列表
        """
        # 优先从MySQL数据库获取设备列表
        devices = self.get_devices_from_db()
        
        if not devices:
            # 回退到YAML配置文件
            devices = self._config_loader.get_devices(enabled_only=enabled_only)
        
        if not devices:
            logger.warning("没有可采集的设备")
            return []
        
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
            from modules.foundation.db_models.base import _db_manager
            
            with _db_manager.session_scope() as session:
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
            from modules.foundation.db_models.base import _db_manager
            
            with _db_manager.session_scope() as session:
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
            from modules.foundation.db_models.base import _db_manager
            
            with _db_manager.session_scope() as session:
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
