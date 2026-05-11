"""
BM-13 采集适配器注册表单元测试
测试适配器注册、发现、创建等核心功能
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Optional

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

from core.protocols import ProtocolType


class TestAdapterInfo:
    """适配器信息测试"""
    
    def test_adapter_info_creation(self):
        """测试创建适配器信息"""
        from modules.collection.adapter_registry import AdapterInfo, AdapterRegistry
        
        info = AdapterInfo(
            name="test_adapter",
            protocol=ProtocolType.SSH,
            handler_class=MagicMock,
            required_credentials=["username"],
            optional_credentials=["password"],
            default_port=22,
            description="Test adapter",
            version="1.0",
            capabilities=["command"]
        )
        
        assert info.name == "test_adapter"
        assert info.protocol == ProtocolType.SSH
        assert info.default_port == 22
        assert "username" in info.required_credentials


class TestAdapterRegistry:
    """适配器注册表测试"""
    
    @pytest.fixture
    def registry(self):
        """创建空的注册表实例"""
        from modules.collection.adapter_registry import AdapterRegistry
        return AdapterRegistry()
    
    def test_register_adapter(self, registry):
        """测试注册适配器"""
        class TestAdapter:
            pass
        
        registry.register(
            name="test_adapter",
            protocol=ProtocolType.SSH,
            handler_class=TestAdapter,
            required_credentials=["username"],
            optional_credentials=["password"],
            default_port=2222,
            description="Test adapter",
            capabilities=["command"]
        )
        
        # 验证注册成功
        info = registry.get_adapter("test_adapter")
        assert info is not None
        assert info.name == "test_adapter"
        assert info.default_port == 2222
    
    def test_register_duplicate_adapter(self, registry):
        """测试重复注册适配器"""
        class TestAdapter:
            pass
        
        registry.register(
            name="duplicate_adapter",
            protocol=ProtocolType.SSH,
            handler_class=TestAdapter
        )
        
        # 重复注册应该覆盖
        class NewAdapter:
            pass
        
        registry.register(
            name="duplicate_adapter",
            protocol=ProtocolType.SSH,
            handler_class=NewAdapter
        )
        
        info = registry.get_adapter("duplicate_adapter")
        assert info.handler_class == NewAdapter
    
    def test_get_adapter_not_found(self, registry):
        """测试获取不存在的适配器"""
        info = registry.get_adapter("nonexistent")
        assert info is None
    
    def test_list_adapters_all(self, registry):
        """测试列出所有适配器"""
        class TestAdapter1:
            pass
        
        class TestAdapter2:
            pass
        
        registry.register(
            name="adapter1",
            protocol=ProtocolType.SSH,
            handler_class=TestAdapter1
        )
        registry.register(
            name="adapter2",
            protocol=ProtocolType.SNMP,
            handler_class=TestAdapter2
        )
        
        adapters = registry.list_adapters()
        assert len(adapters) >= 2
    
    def test_list_adapters_by_protocol(self, registry):
        """测试按协议列出适配器"""
        class SSHAdapter:
            pass
        
        class SNMPAdapter:
            pass
        
        registry.register(
            name="my_ssh",
            protocol=ProtocolType.SSH,
            handler_class=SSHAdapter
        )
        registry.register(
            name="my_snmp",
            protocol=ProtocolType.SNMP,
            handler_class=SNMPAdapter
        )
        
        ssh_adapters = registry.list_adapters(ProtocolType.SSH)
        snmp_adapters = registry.list_adapters(ProtocolType.SNMP)
        
        assert len(ssh_adapters) >= 1
        assert len(snmp_adapters) >= 1
        
        # 验证返回的是正确的适配器
        ssh_names = [a.name for a in ssh_adapters]
        assert "my_ssh" in ssh_names
    
    def test_create_adapter(self, registry):
        """测试创建适配器实例"""
        class MockAdapter:
            def __init__(self, config):
                self.config = config
        
        registry.register(
            name="factory_adapter",
            protocol=ProtocolType.SSH,
            handler_class=MockAdapter
        )
        
        config = {"host": "192.168.1.1", "port": 22}
        adapter = registry.create_adapter("factory_adapter", config)
        
        assert adapter is not None
        assert adapter.config == config
    
    def test_create_adapter_not_found(self, registry):
        """测试创建不存在的适配器"""
        adapter = registry.create_adapter("nonexistent", {})
        assert adapter is None
    
    def test_register_factory(self, registry):
        """测试注册工厂函数"""
        def factory_function(config):
            return MagicMock()
        
        registry.register_factory("factory_method", factory_function)
        
        factory = registry.get_factory("factory_method")
        assert factory is not None
    
    def test_get_factory_not_found(self, registry):
        """测试获取不存在的工厂函数"""
        factory = registry.get_factory("nonexistent")
        assert factory is None
    
    def test_get_protocol_handlers(self, registry):
        """测试获取协议处理器映射"""
        class SSHAdapter:
            pass
        
        registry.register(
            name="ssh_handler",
            protocol=ProtocolType.SSH,
            handler_class=SSHAdapter
        )
        
        handlers = registry.get_protocol_handlers(ProtocolType.SSH)
        assert len(handlers) >= 1


class TestProtocolType:
    """协议类型枚举测试"""
    
    def test_all_protocols_defined(self):
        """测试所有协议类型都已定义"""
        assert ProtocolType.SSH is not None
        assert ProtocolType.SNMP is not None
        assert ProtocolType.WINRM is not None
        assert ProtocolType.IPMI is not None
        assert ProtocolType.HTTP is not None
        assert ProtocolType.KUBERNETES is not None
        assert ProtocolType.DOCKER is not None
        assert ProtocolType.ZABBIX is not None
        assert ProtocolType.PROMETHEUS is not None
        assert ProtocolType.VMWARE is not None
        assert ProtocolType.SNMPTRAP is not None
        assert ProtocolType.SYSLOG is not None
        assert ProtocolType.LOG is not None
        assert ProtocolType.METRIC is not None
    
    def test_protocol_value(self):
        """测试协议类型值"""
        assert ProtocolType.SSH.value == "ssh"
        assert ProtocolType.SNMP.value == "snmp"
        assert ProtocolType.WINRM.value == "winrm"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
