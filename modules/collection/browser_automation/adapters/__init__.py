"""
浏览器自动化适配器
"""

from .base_adapter import BaseDeviceAdapter, DeviceCredential
from .huawei_adapter import HuaweiDeviceAdapter
from .topsec_adapter import TopsecDeviceAdapter, TopSecAdapter
from .nsfocus_adapter import NSFOCUSDeviceAdapter
from .venustech_adapter import VenustechDeviceAdapter
from .sangfor_adapter import SangforDeviceAdapter
from .generic_adapter import (
    GenericDeviceAdapter,
    TopSecAdapter,
    NSFOCUSAdapter,
    HillstoneAdapter
)

# 向后兼容别名
NSFOCUSAdapter = NSFOCUSDeviceAdapter
VenustechAdapter = VenustechDeviceAdapter
SangforAdapter = SangforDeviceAdapter


def create_adapter(device_type: str, credential: DeviceCredential, **kwargs):
    """
    创建设备适配器
    
    Args:
        device_type: 设备类型 (huawei, topsec, nsfocus, venustech, sangfor, generic)
        credential: 设备凭证
        **kwargs: 额外参数
    
    Returns:
        设备适配器实例
    """
    from .adapter_factory import AdapterFactory
    return AdapterFactory.create(device_type, credential, **kwargs)


__all__ = [
    # 基础类
    'BaseDeviceAdapter',
    'DeviceCredential',
    # 设备适配器
    'HuaweiDeviceAdapter',
    'TopsecDeviceAdapter',
    'TopSecAdapter',
    'NSFOCUSDeviceAdapter',
    'NSFOCUSAdapter',
    'VenustechDeviceAdapter',
    'VenustechAdapter',
    'SangforDeviceAdapter',
    'SangforAdapter',
    'GenericDeviceAdapter',
    'HillstoneAdapter',
    # 工厂类
    'AdapterFactory',
    'AdapterRegistry',
    'get_adapter_registry',
    'auto_create_adapter',
    'create_adapter'
]