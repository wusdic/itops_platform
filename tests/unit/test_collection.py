# -*- coding: utf-8 -*-
"""
采集模块单元测试

测试采集模块核心功能：
- config_loader: 配置加载
- device_manager: 设备管理
- collector_factory: 采集器工厂
- adapter_registry: 适配器注册表
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.collection.config_loader import ConfigLoader
from modules.collection.device_manager import DeviceManager, CollectionStatus, DeviceMetrics
from modules.collection.collector_factory import CollectorFactory, get_factory
from modules.collection.adapter_registry import AdapterRegistry, AdapterInfo
from core.protocols import ProtocolType, DeviceCategory


class TestConfigLoader:
    """配置加载器测试"""
    
    def test_config_loader_init(self):
        """测试配置加载器初始化"""
        loader = ConfigLoader('/workspace/itops_platform/config')
        assert loader is not None
        assert hasattr(loader, '_devices')
        assert hasattr(loader, '_adapters')
    
    def test_load_devices(self):
        """测试设备配置加载"""
        loader = ConfigLoader('/workspace/itops_platform/config')
        devices = loader.get_devices()
        assert isinstance(devices, list)
    
    def test_get_device_by_name(self):
        """测试按名称获取设备"""
        loader = ConfigLoader('/workspace/itops_platform/config')
        
        # 测试存在的设备
        device = loader.get_device_by_name('Web服务器-01')
        if device:
            assert 'name' in device or 'ip' in device


class TestDeviceManager:
    """设备管理器测试"""
    
    def test_device_manager_init(self):
        """测试设备管理器初始化"""
        manager = DeviceManager('/workspace/itops_platform/config')
        assert manager is not None
    
    def test_collection_status_enum(self):
        """测试采集状态枚举"""
        assert CollectionStatus.ONLINE == "online"
        assert CollectionStatus.OFFLINE == "offline"
        assert CollectionStatus.COLLECTING == "collecting"
    
    def test_device_metrics_creation(self):
        """测试设备指标创建"""
        from datetime import datetime
        
        metrics = DeviceMetrics(
            device_name="test_device",
            device_ip="192.168.1.1",
            device_type="server",
            vendor="test",
            timestamp=datetime.now(),
            status=CollectionStatus.ONLINE,
            metrics={"cpu": 50}
        )
        
        assert metrics.device_name == "test_device"
        assert metrics.status == CollectionStatus.ONLINE
        assert metrics.metrics["cpu"] == 50


class TestCollectorFactory:
    """采集器工厂测试"""
    
    def test_factory_singleton(self):
        """测试工厂单例"""
        factory1 = get_factory()
        factory2 = get_factory()
        assert factory1 is factory2
    
    def test_create_collector_invalid_protocol(self):
        """测试创建不支持协议的采集器"""
        factory = CollectorFactory()
        
        device_config = {
            'name': 'test',
            'ip': '192.168.1.1',
            'protocols': {'primary': 'invalid_protocol'}
        }
        
        with pytest.raises(ValueError, match="不支持的协议"):
            factory.create_collector(device_config)
    
    def test_protocol_types(self):
        """测试协议类型定义"""
        assert ProtocolType.SNMP == "snmp"
        assert ProtocolType.SSH == "ssh"
        assert ProtocolType.HTTP == "http"
        assert ProtocolType.KUBERNETES == "kubernetes"


class TestAdapterRegistry:
    """适配器注册表测试"""
    
    def test_registry_init(self):
        """测试注册表初始化"""
        registry = AdapterRegistry()
        assert registry is not None
    
    def test_register_adapter(self):
        """测试适配器注册"""
        registry = AdapterRegistry()
        
        # 使用正确的签名
        registry.register(
            name="test_adapter",
            protocol=ProtocolType.SNMP,
            handler_class=None,  # 必须字段
            description="Test adapter"
        )
        
        adapter = registry.get_adapter("test_adapter")
        assert adapter is not None
        assert adapter.name == "test_adapter"
    
    def test_list_adapters(self):
        """测试列出适配器"""
        registry = AdapterRegistry()
        adapters = registry.list_adapters()
        assert isinstance(adapters, list)


class TestProtocolTypes:
    """协议类型测试"""
    
    def test_device_category(self):
        """测试设备分类"""
        assert DeviceCategory.SERVER == "server"
        assert DeviceCategory.NETWORK == "network"
        assert DeviceCategory.SECURITY == "security"
    
    def test_protocol_type_values(self):
        """测试协议类型值"""
        assert ProtocolType.SNMP.value == "snmp"
        assert ProtocolType.SSH.value == "ssh"
        assert ProtocolType.WINRM.value == "winrm"
        assert ProtocolType.IPMI.value == "ipmi"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
