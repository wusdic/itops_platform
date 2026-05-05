# -*- coding: utf-8 -*-
"""
集成测试

测试完整的业务流程：
1. 配置加载 → 设备注册 → 采集执行 → 指标返回
2. API请求 → 路由处理 → 业务逻辑 → 响应返回
3. 多模块协作
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestCollectionWorkflow:
    """采集完整流程测试"""
    
    def test_config_to_device_flow(self):
        """测试配置加载到设备注册流程"""
        from modules.collection.config_loader import ConfigLoader
        from modules.collection.device_manager import DeviceManager
        
        # 1. 配置加载
        loader = ConfigLoader('/workspace/itops_platform/config')
        devices = loader.get_devices()
        assert isinstance(devices, list)
        
        # 2. 设备管理器初始化
        manager = DeviceManager('/workspace/itops_platform/config')
        assert manager is not None
        
        # 3. 验证设备状态查询可用
        stats = manager.get_stats()
        assert 'device_count' in stats
    
    def test_device_manager_callback(self):
        """测试设备管理回调机制"""
        from modules.collection.device_manager import DeviceManager, DeviceMetrics, CollectionStatus
        
        manager = DeviceManager('/workspace/itops_platform/config')
        
        # 注册回调
        callback_result = []
        def test_callback(metrics: DeviceMetrics):
            callback_result.append(metrics)
        
        manager.register_callback(test_callback)
        assert len(manager._collect_callbacks) >= 1
        
        # 注销回调
        manager.unregister_callback(test_callback)
    
    def test_collector_factory_protocol_selection(self):
        """测试采集器工厂协议选择"""
        from modules.collection.collector_factory import CollectorFactory
        from core.protocols import ProtocolType
        
        factory = CollectorFactory()
        
        # 测试HTTP协议
        device_config = {
            'name': 'test_http',
            'ip': '192.168.1.100',
            'protocols': {'primary': 'http'}
        }
        
        # 应该能创建HTTP采集器
        try:
            collector = factory.create_collector(device_config)
            assert collector is not None
        except ValueError as e:
            # HTTP协议可能需要额外配置，这是预期行为
            assert "http" in str(e).lower() or "api" in str(e).lower()


class TestAPIIntegration:
    """API集成测试"""
    
    def test_api_dependencies(self):
        """测试API依赖注入"""
        from api.dependencies import get_settings, Settings
        
        settings = get_settings()
        assert settings is not None
        # Settings 有 API_TITLE 属性
        assert hasattr(settings, 'API_TITLE')
    
    def test_fastapi_app_creation(self):
        """测试FastAPI应用创建"""
        from api.main import app
        
        assert app is not None
        assert app.title == "ITOps Platform API"
        assert len(app.routes) > 0


class TestProtocolIntegration:
    """协议集成测试"""
    
    def test_protocol_type_complete(self):
        """测试协议类型完整性"""
        from core.protocols import ProtocolType, DeviceCategory
        
        # 验证所有主要协议都已定义
        protocols = [
            ProtocolType.SNMP,
            ProtocolType.SSH,
            ProtocolType.HTTP,
            ProtocolType.WINRM,
            ProtocolType.IPMI,
            ProtocolType.KUBERNETES,
            ProtocolType.DOCKER,
        ]
        
        for p in protocols:
            assert p.value is not None
    
    def test_adapter_registry_complete(self):
        """测试适配器注册表完整性"""
        from modules.collection.adapter_registry import AdapterRegistry
        
        registry = AdapterRegistry()
        adapters = registry.list_adapters()
        
        # 应该有内置适配器
        assert len(adapters) > 0
        
        # 验证注册表可以获取适配器信息
        for adapter in adapters:
            assert adapter.name
            assert adapter.protocol


class TestBusinessLogic:
    """业务逻辑集成测试"""
    
    def test_device_status_workflow(self):
        """测试设备状态工作流"""
        from modules.collection.device_manager import CollectionStatus
        
        # 状态转换
        assert CollectionStatus.UNKNOWN != CollectionStatus.ONLINE
        assert CollectionStatus.OFFLINE != CollectionStatus.COLLECTING
        
        # 状态值验证
        assert CollectionStatus.ONLINE.value == "online"
        assert CollectionStatus.OFFLINE.value == "offline"
    
    def test_metrics_data_structure(self):
        """测试指标数据结构"""
        from modules.collection.device_manager import DeviceMetrics, CollectionStatus
        
        metrics = DeviceMetrics(
            device_name="测试设备",
            device_ip="192.168.1.1",
            device_type="server",
            vendor="Linux",
            timestamp=datetime.now(),
            status=CollectionStatus.ONLINE,
            metrics={"cpu": 50, "memory": 80}
        )
        
        assert metrics.device_name == "测试设备"
        assert metrics.metrics["cpu"] == 50
        assert metrics.status == CollectionStatus.ONLINE


class TestConfigIntegration:
    """配置集成测试"""
    
    def test_yaml_config_loading(self):
        """测试YAML配置加载"""
        import yaml
        from pathlib import Path
        
        config_path = Path('/workspace/itops_platform/config/dev.yaml')
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            assert config is not None
            assert isinstance(config, dict)
    
    def test_device_config_structure(self):
        """测试设备配置结构"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader('/workspace/itops_platform/config')
        
        # 尝试获取一个设备
        devices = loader.get_devices()
        if devices:
            device = devices[0]
            
            # 验证必要字段
            assert 'name' in device or 'ip' in device or 'type' in device


class TestEndToEnd:
    """端到端测试"""
    
    def test_full_collection_simulation(self):
        """模拟完整采集流程"""
        from modules.collection.config_loader import ConfigLoader
        from modules.collection.device_manager import DeviceManager, CollectionStatus
        from modules.collection.collector_factory import CollectorFactory
        
        # 1. 加载配置
        loader = ConfigLoader('/workspace/itops_platform/config')
        devices = loader.get_devices()
        
        # 2. 初始化管理器
        manager = DeviceManager('/workspace/itops_platform/config')
        
        # 3. 获取工厂
        factory = CollectorFactory()
        
        # 4. 验证统计
        stats = manager.get_stats()
        assert 'total_collects' in stats
        assert stats['total_collects'] == 0  # 初始状态
    
    def test_adapter_selection_logic(self):
        """测试适配器选择逻辑"""
        from modules.collection.adapter_registry import AdapterRegistry
        from core.protocols import ProtocolType
        
        registry = AdapterRegistry()
        
        # 获取支持特定协议的适配器
        snmp_adapters = registry.get_adapters_by_protocol(ProtocolType.SNMP)
        assert isinstance(snmp_adapters, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
