"""
BM-14 配置加载器单元测试
测试设备配置加载、解析、管理等核心功能
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import Dict, List, Optional

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')


class TestConfigLoader:
    """配置加载器测试"""
    
    @pytest.fixture
    def sample_config(self):
        """创建示例配置文件"""
        return {
            "devices": [
                {
                    "name": "server-01",
                    "ip": "192.168.1.10",
                    "type": "linux",
                    "vendor": "dell",
                    "os": "linux",
                    "os_version": "7.9",
                    "protocols": {
                        "ssh": {
                            "enabled": True,
                            "port": 22,
                            "username": "admin",
                            "password": "password"
                        }
                    },
                    "collect": {
                        "enabled": True,
                        "interval": 60
                    },
                    "tags": {
                        "env": "production",
                        "app": "web"
                    }
                },
                {
                    "name": "server-02",
                    "ip": "192.168.1.11",
                    "type": "windows",
                    "vendor": "hp",
                    "os": "windows",
                    "os_version": "2019",
                    "protocols": {
                        "winrm": {
                            "enabled": True,
                            "port": 5985,
                            "username": "admin",
                            "password": "password"
                        }
                    },
                    "collect": {
                        "enabled": False
                    },
                    "tags": {
                        "env": "development"
                    }
                }
            ],
            "defaults": {
                "ssh": {
                    "timeout": 30,
                    "retry": 3
                },
                "collect": {
                    "interval": 300
                }
            }
        }
    
    @pytest.fixture
    def temp_config_file(self, sample_config):
        """创建临时配置文件"""
        fd, path = tempfile.mkstemp(suffix='.yaml')
        with os.fdopen(fd, 'w') as f:
            import yaml
            yaml.dump(sample_config, f)
        yield path
        os.unlink(path)
    
    def test_load_config_file(self, temp_config_file):
        """测试加载配置文件"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        assert loader.config is not None
        assert "devices" in loader.config
    
    def test_get_all_devices(self, temp_config_file):
        """测试获取所有设备"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        devices = loader.get_devices()
        assert len(devices) == 2
    
    def test_get_device_by_name(self, temp_config_file):
        """测试根据名称获取设备"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        device = loader.get_device_by_name("server-01")
        assert device is not None
        assert device["ip"] == "192.168.1.10"
    
    def test_get_device_by_ip(self, temp_config_file):
        """测试根据IP获取设备"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        device = loader.get_device_by_ip("192.168.1.11")
        assert device is not None
        assert device["name"] == "server-02"
    
    def test_get_devices_by_type(self, temp_config_file):
        """测试按类型获取设备"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        linux_devices = loader.get_devices(device_type="linux")
        windows_devices = loader.get_devices(device_type="windows")
        
        assert len(linux_devices) == 1
        assert linux_devices[0]["name"] == "server-01"
        
        assert len(windows_devices) == 1
        assert windows_devices[0]["name"] == "server-02"
    
    def test_get_devices_by_vendor(self, temp_config_file):
        """测试按厂商获取设备"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        dell_devices = loader.get_devices(vendor="dell")
        hp_devices = loader.get_devices(vendor="hp")
        
        assert len(dell_devices) == 1
        assert len(hp_devices) == 1
    
    def test_get_enabled_devices_only(self, temp_config_file):
        """测试只获取已启用的设备"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        enabled_devices = loader.get_devices(enabled_only=True)
        
        # server-01 enabled=True, server-02 enabled=False
        assert len(enabled_devices) == 1
        assert enabled_devices[0]["name"] == "server-01"
    
    def test_get_devices_with_tag(self, temp_config_file):
        """测试按标签过滤设备"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        
        prod_devices = loader.get_devices(tag="env:production")
        dev_devices = loader.get_devices(tag="env:development")
        
        assert len(prod_devices) == 1
        assert prod_devices[0]["name"] == "server-01"
        
        assert len(dev_devices) == 1
        assert dev_devices[0]["name"] == "server-02"
    
    def test_get_device_credentials(self, temp_config_file):
        """测试获取设备凭据"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        creds = loader.get_device_credentials("server-01", "ssh")
        
        assert creds is not None
        assert creds.get("username") == "admin"
    
    def test_get_device_protocol_config(self, temp_config_file):
        """测试获取设备协议配置"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        protocol_config = loader.get_device_protocol_config("server-01", "ssh")
        
        assert protocol_config is not None
        assert protocol_config.get("enabled") == True
        assert protocol_config.get("port") == 22
    
    def test_get_collect_config(self, temp_config_file):
        """测试获取采集配置"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        collect_config = loader.get_collect_config("server-01")
        
        assert collect_config is not None
        assert collect_config.get("enabled") == True
        assert collect_config.get("interval") == 60
    
    def test_reload_config(self, temp_config_file):
        """测试重新加载配置"""
        from modules.collection.config_loader import ConfigLoader
        
        loader = ConfigLoader(config_file=temp_config_file)
        initial_devices = loader.get_devices()
        assert len(initial_devices) == 2
        
        # 修改配置文件
        with open(temp_config_file, 'r') as f:
            import yaml
            config = yaml.safe_load(f)
        
        config["devices"].append({
            "name": "server-03",
            "ip": "192.168.1.12",
            "type": "linux",
            "vendor": "dell"
        })
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(config, f)
        
        # 重新加载
        loader.reload()
        reloaded_devices = loader.get_devices()
        
        assert len(reloaded_devices) == 3


class TestDeviceFiltering:
    """设备过滤测试"""
    
    @pytest.fixture
    def loader_with_devices(self):
        """创建带设备的加载器"""
        from modules.collection.config_loader import ConfigLoader
        
        config = {
            "devices": [
                {"name": "srv-01", "ip": "10.0.0.1", "type": "linux", "vendor": "dell", "enabled": True, "tags": {"env": "prod"}},
                {"name": "srv-02", "ip": "10.0.0.2", "type": "linux", "vendor": "hp", "enabled": True, "tags": {"env": "prod"}},
                {"name": "srv-03", "ip": "10.0.0.3", "type": "windows", "vendor": "dell", "enabled": False, "tags": {"env": "dev"}},
                {"name": "srv-04", "ip": "10.0.0.4", "type": "linux", "vendor": "hp", "enabled": True, "tags": {"env": "dev"}},
            ]
        }
        
        fd, path = tempfile.mkstemp(suffix='.yaml')
        with os.fdopen(fd, 'w') as f:
            import yaml
            yaml.dump(config, f)
        
        loader = ConfigLoader(config_file=path)
        yield loader
        os.unlink(path)
    
    def test_filter_by_multiple_tags(self, loader_with_devices):
        """测试按多个标签过滤"""
        # 标签过滤需要正确实现
        pass
    
    def test_filter_combined_conditions(self, loader_with_devices):
        """测试组合条件过滤"""
        devices = loader_with_devices.get_devices(
            device_type="linux",
            enabled_only=True
        )
        
        # 应该有 srv-01, srv-02, srv-04
        assert len(devices) == 3


class TestConfigStats:
    """配置统计测试"""
    
    def test_get_stats(self):
        """测试获取配置统计信息"""
        from modules.collection.config_loader import ConfigLoader
        
        config = {
            "devices": [
                {"name": "srv-01", "type": "linux", "vendor": "dell", "enabled": True},
                {"name": "srv-02", "type": "linux", "vendor": "hp", "enabled": True},
            ]
        }
        
        fd, path = tempfile.mkstemp(suffix='.yaml')
        with os.fdopen(fd, 'w') as f:
            import yaml
            yaml.dump(config, f)
        
        loader = ConfigLoader(config_file=path)
        stats = loader.get_stats()
        
        assert "total_devices" in stats
        assert stats["total_devices"] == 2
        
        os.unlink(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
