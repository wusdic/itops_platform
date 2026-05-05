"""
设备适配器工厂类
根据设备类型自动创建对应的适配器实例
"""

import logging
from typing import Dict, List, Optional, Type, Any

from .base_adapter import BaseDeviceAdapter, DeviceCredential
from .huawei_adapter import HuaweiDeviceAdapter
from .topsec_adapter import TopsecDeviceAdapter, TopSecAdapter
from .nsfocus_adapter import NSFOCUSDeviceAdapter, NSFOCUSAdapter
from .venustech_adapter import VenustechDeviceAdapter, VenustechAdapter
from .sangfor_adapter import SangforDeviceAdapter, SangforAdapter
from .generic_adapter import GenericDeviceAdapter

logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    设备适配器工厂
    
    支持根据设备类型自动创建对应的适配器实例
    """
    
    # 支持的设备类型
    DEVICE_TYPES = {
        # 华为网络设备
        'huawei': {
            'class': HuaweiDeviceAdapter,
            'name': '华为网络设备',
            'description': '华为交换机、路由器、AC控制器等',
            'vendor': 'Huawei'
        },
        # 天融信安全设备
        'topsec': {
            'class': TopSecAdapter,
            'name': '天融信安全设备',
            'description': '天融信防火墙、UTM、WAF等',
            'vendor': 'TopSec'
        },
        'ngfw': {
            'class': TopSecAdapter,
            'name': '天融信NGFW',
            'description': '天融信下一代防火墙',
            'vendor': 'TopSec'
        },
        # 绿盟安全设备
        'nsfocus': {
            'class': NSFOCUSDeviceAdapter,
            'name': '绿盟安全设备',
            'description': '绿盟防火墙、IDS、IPS、WAF等',
            'vendor': 'NSFOCUS'
        },
        'nsfocus_ngfw': {
            'class': NSFOCUSDeviceAdapter,
            'name': '绿盟NGFW',
            'description': '绿盟下一代防火墙',
            'vendor': 'NSFOCUS'
        },
        'green': {
            'class': NSFOCUSDeviceAdapter,
            'name': '绿盟安全设备',
            'description': '绿盟安全设备',
            'vendor': 'NSFOCUS'
        },
        # 启明星辰安全设备
        'venustech': {
            'class': VenustechDeviceAdapter,
            'name': '启明星辰安全设备',
            'description': '启明星辰防火墙、IDS、IPS、UTM等',
            'vendor': 'Venustech'
        },
        'watchguard': {
            'class': VenustechDeviceAdapter,
            'name': '启明星辰安全设备',
            'description': '启明星辰安全设备',
            'vendor': 'Venustech'
        },
        # 深信服设备
        'sangfor': {
            'class': SangforDeviceAdapter,
            'name': '深信服设备',
            'description': '深信服AD、DC、AF、SSL VPN等',
            'vendor': 'Sangfor'
        },
        'ad': {
            'class': SangforDeviceAdapter,
            'name': '深信服AD',
            'description': '深信服应用交付',
            'vendor': 'Sangfor'
        },
        'dc': {
            'class': SangforDeviceAdapter,
            'name': '深信服DC',
            'description': '深信服统一运维管理',
            'vendor': 'Sangfor'
        },
        'af': {
            'class': SangforDeviceAdapter,
            'name': '深信服AF',
            'description': '深信服防火墙',
            'vendor': 'Sangfor'
        },
        # 通用设备
        'generic': {
            'class': GenericDeviceAdapter,
            'name': '通用Web设备',
            'description': '通用Web管理界面设备',
            'vendor': 'Generic'
        }
    }
    
    # 厂商映射
    VENDOR_MAP = {
        'huawei': 'huawei',
        'topsec': 'topsec',
        'nsfocus': 'nsfocus',
        'green': 'nsfocus',
        '绿盟': 'nsfocus',
        'venustech': 'venustech',
        '启明': 'venustech',
        'sangfor': 'sangfor',
        '深信服': 'sangfor',
        'generic': 'generic'
    }
    
    @classmethod
    def create(cls, device_type: str, credential: DeviceCredential, **kwargs) -> BaseDeviceAdapter:
        """
        创建设备适配器
        
        Args:
            device_type: 设备类型 (huawei, topsec, nsfocus, venustech, sangfor, generic)
            credential: 设备凭证
            **kwargs: 额外参数
        
        Returns:
            设备适配器实例
        
        Raises:
            ValueError: 不支持的设备类型
        """
        # 标准化设备类型
        device_type_lower = device_type.lower().strip()
        
        # 查找适配器
        adapter_info = cls.DEVICE_TYPES.get(device_type_lower)
        if not adapter_info:
            # 尝试通过厂商名称匹配
            vendor_key = cls.VENDOR_MAP.get(device_type)
            if vendor_key:
                adapter_info = cls.DEVICE_TYPES.get(vendor_key)
            
            if not adapter_info:
                raise ValueError(
                    f"不支持的设备类型: {device_type}\n"
                    f"支持的设备类型: {', '.join(cls.DEVICE_TYPES.keys())}"
                )
        
        logger.info(f"创建适配器: {device_type} -> {adapter_info['name']}")
        return adapter_info['class'](credential, **kwargs)
    
    @classmethod
    def create_by_vendor(cls, vendor: str, credential: DeviceCredential, **kwargs) -> BaseDeviceAdapter:
        """
        根据厂商名称创建设备适配器
        
        Args:
            vendor: 厂商名称
            credential: 设备凭证
            **kwargs: 额外参数
        
        Returns:
            设备适配器实例
        """
        device_type = cls.VENDOR_MAP.get(vendor)
        if not device_type:
            raise ValueError(f"不支持的厂商: {vendor}")
        
        return cls.create(device_type, credential, **kwargs)
    
    @classmethod
    def get_supported_types(cls) -> List[Dict[str, str]]:
        """
        获取支持的设备类型列表
        
        Returns:
            设备类型信息列表
        """
        return [
            {
                'type': device_type,
                'name': info['name'],
                'description': info['description'],
                'vendor': info['vendor']
            }
            for device_type, info in cls.DEVICE_TYPES.items()
        ]
    
    @classmethod
    def get_type_info(cls, device_type: str) -> Optional[Dict[str, str]]:
        """
        获取设备类型信息
        
        Args:
            device_type: 设备类型
        
        Returns:
            设备类型信息，如果不存在返回None
        """
        info = cls.DEVICE_TYPES.get(device_type.lower())
        if info:
            return {
                'type': device_type,
                'name': info['name'],
                'description': info['description'],
                'vendor': info['vendor']
            }
        return None
    
    @classmethod
    def is_supported(cls, device_type: str) -> bool:
        """
        检查是否支持该设备类型
        
        Args:
            device_type: 设备类型
        
        Returns:
            是否支持
        """
        return device_type.lower() in cls.DEVICE_TYPES


class AdapterRegistry:
    """
    设备适配器注册表
    
    管理多个设备的适配器实例
    """
    
    def __init__(self):
        self._adapters: Dict[str, BaseDeviceAdapter] = {}
        self._device_info: Dict[str, Dict[str, Any]] = {}
    
    def register(self, device_id: str, adapter: BaseDeviceAdapter, info: Dict[str, Any] = None):
        """
        注册设备适配器
        
        Args:
            device_id: 设备ID
            adapter: 适配器实例
            info: 设备信息
        """
        self._adapters[device_id] = adapter
        if info:
            self._device_info[device_id] = info
        logger.info(f"注册设备适配器: {device_id} ({adapter.__class__.__name__})")
    
    def unregister(self, device_id: str):
        """
        注销设备适配器
        
        Args:
            device_id: 设备ID
        """
        if device_id in self._adapters:
            del self._adapters[device_id]
        if device_id in self._device_info:
            del self._device_info[device_id]
        logger.info(f"注销设备适配器: {device_id}")
    
    def get(self, device_id: str) -> Optional[BaseDeviceAdapter]:
        """
        获取设备适配器
        
        Args:
            device_id: 设备ID
        
        Returns:
            适配器实例，如果不存在返回None
        """
        return self._adapters.get(device_id)
    
    def get_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        获取设备信息
        
        Args:
            device_id: 设备ID
        
        Returns:
            设备信息
        """
        return self._device_info.get(device_id)
    
    def list_devices(self) -> List[str]:
        """
        列出所有注册的设备ID
        
        Returns:
            设备ID列表
        """
        return list(self._adapters.keys())
    
    def clear(self):
        """清空所有注册的设备"""
        self._adapters.clear()
        self._device_info.clear()
        logger.info("清空设备适配器注册表")
    
    @property
    def count(self) -> int:
        """获取注册设备数量"""
        return len(self._adapters)


# 全局适配器注册表
_adapter_registry = AdapterRegistry()


def get_adapter_registry() -> AdapterRegistry:
    """获取全局适配器注册表"""
    return _adapter_registry


def auto_create_adapter(device_type: str, host: str, port: int = 443,
                        username: str = None, password: str = None,
                        protocol: str = 'https', **kwargs) -> BaseDeviceAdapter:
    """
    自动创建设备适配器（便捷函数）
    
    Args:
        device_type: 设备类型
        host: 主机地址
        port: 端口
        username: 用户名
        password: 密码
        protocol: 协议 (http/https)
        **kwargs: 额外参数
    
    Returns:
        设备适配器实例
    """
    credential = DeviceCredential(
        host=host,
        port=port,
        protocol=protocol,
        username=username or '',
        password=password or ''
    )
    
    return AdapterFactory.create(device_type, credential, **kwargs)
