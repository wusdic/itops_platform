"""
BM-11 设备管理API路由单元测试
测试设备采集、设备状态、设备配置等API端点
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Optional

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient


@pytest.fixture
def mock_user():
    """创建模拟用户"""
    from modules.foundation.auth_manager.auth import UserStatus
    user = MagicMock()
    user.id = "u001"
    user.username = "testuser"
    user.email = "test@example.com"
    user.roles = ["admin"]
    user.status = UserStatus.ACTIVE
    user.metadata = {}
    user.last_login = datetime.now()
    user.created_at = datetime.now()
    user.updated_at = datetime.now()
    return user


@pytest.fixture
def app(mock_user):
    """创建测试FastAPI应用"""
    from api.routes.device_api import router
    from api.dependencies import get_db, get_current_user, CurrentUser
    
    app = FastAPI()
    app.include_router(router)
    
    # 覆盖依赖
    def override_get_current_user():
        return CurrentUser(
            user_id=mock_user.id,
            username=mock_user.username,
            email=mock_user.email,
            roles=mock_user.roles
        )
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


class TestDeviceListAPI:
    """设备列表接口测试"""
    
    @patch('modules.collection.device_manager.get_device_manager')
    @patch('modules.collection.config_loader.get_config_loader')
    def test_get_devices(self, mock_loader, mock_manager, client):
        """测试获取设备列表"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_device_status.return_value = MagicMock(value="online")
        mock_manager_instance.get_last_metrics.return_value = MagicMock(
            timestamp=datetime.now(),
            metrics={}
        )
        mock_manager.return_value = mock_manager_instance
        
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_devices.return_value = []
        mock_loader.return_value = mock_loader_instance
        
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @patch('modules.collection.device_manager.get_device_manager')
    @patch('modules.collection.config_loader.get_config_loader')
    def test_get_devices_with_filters(self, mock_loader, mock_manager, client):
        """测试带过滤条件的设备列表"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_device_status.return_value = MagicMock(value="online")
        mock_manager_instance.get_last_metrics.return_value = None
        mock_manager.return_value = mock_manager_instance
        
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_devices.return_value = [
            {"name": "server-01", "ip": "192.168.1.10", "type": "linux", "vendor": "dell"}
        ]
        mock_loader.return_value = mock_loader_instance
        
        response = client.get("/?device_type=linux&vendor=dell&enabled=true")
        assert response.status_code == 200


class TestDeviceStatsAPI:
    """设备统计接口测试"""
    
    @patch('modules.collection.device_manager.get_device_manager')
    @patch('modules.collection.config_loader.get_config_loader')
    def test_get_device_stats(self, mock_loader, mock_manager, client):
        """测试获取设备统计"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_device_status.return_value = MagicMock(value="online")
        mock_manager.return_value = mock_manager_instance
        
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_devices.return_value = [
            {"name": "server-01", "type": "linux", "vendor": "dell"},
            {"name": "server-02", "type": "linux", "vendor": "hp"},
        ]
        mock_loader.return_value = mock_loader_instance
        
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "online" in data
        assert "offline" in data
        assert "unknown" in data


class TestDeviceDetailAPI:
    """设备详情接口测试"""
    
    @patch('modules.collection.device_manager.get_device_manager')
    @patch('modules.collection.config_loader.get_config_loader')
    def test_get_device(self, mock_loader, mock_manager, client):
        """测试获取设备详情"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_device_status.return_value = MagicMock(value="online")
        mock_manager_instance.get_last_metrics.return_value = MagicMock(
            timestamp=datetime.now(),
            metrics={"cpu": 50}
        )
        mock_manager.return_value = mock_manager_instance
        
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_device_by_name.return_value = {
            "name": "server-01",
            "ip": "192.168.1.10",
            "type": "linux",
            "vendor": "dell",
            "os": "linux",
            "os_version": "7.9",
            "protocols": {"ssh": {}},
            "collect": {"enabled": True, "interval": 60},
            "tags": {}
        }
        mock_loader.return_value = mock_loader_instance
        
        response = client.get("/server-01")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "server-01"
    
    @patch('modules.collection.config_loader.get_config_loader')
    def test_get_device_not_found(self, mock_loader, client):
        """测试获取不存在的设备"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_device_by_name.return_value = None
        mock_loader.return_value = mock_loader_instance
        
        response = client.get("/nonexistent")
        assert response.status_code == 404


class TestDeviceCollectAPI:
    """设备采集接口测试"""
    
    @patch('modules.collection.device_manager.get_device_manager')
    def test_collect_device(self, mock_manager, client):
        """测试手动采集设备指标"""
        mock_manager_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.device_name = "server-01"
        mock_result.device_ip = "192.168.1.10"
        mock_result.device_type = "linux"
        mock_result.vendor = "dell"
        mock_result.status = MagicMock(value="online")
        mock_result.timestamp = datetime.now()
        mock_result.metrics = {"cpu": 50, "memory": 60}
        mock_result.error = None
        
        mock_manager_instance.collect_device = AsyncMock(return_value=mock_result)
        mock_manager.return_value = mock_manager_instance
        
        request_data = {"device_name": "server-01"}
        response = client.post("/collect", json=request_data)
        assert response.status_code == 200
    
    @patch('modules.collection.device_manager.get_device_manager')
    def test_collect_all_devices(self, mock_manager, client):
        """测试批量采集所有设备"""
        mock_manager_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.device_name = "server-01"
        mock_result.device_ip = "192.168.1.10"
        mock_result.device_type = "linux"
        mock_result.vendor = "dell"
        mock_result.status = MagicMock(value="online")
        mock_result.timestamp = datetime.now()
        mock_result.metrics = {"cpu": 50}
        mock_result.error = None
        
        mock_manager_instance.collect_all = AsyncMock(return_value=[mock_result])
        mock_manager.return_value = mock_manager_instance
        
        response = client.post("/collect/all")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestDeviceStatusAPI:
    """设备状态接口测试"""
    
    @patch('modules.collection.device_manager.get_device_manager')
    def test_get_device_status(self, mock_manager, client):
        """测试获取设备状态"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_device_status.return_value = MagicMock(value="online")
        mock_manager.return_value = mock_manager_instance
        
        response = client.get("/server-01/status")
        assert response.status_code == 200
        data = response.json()
        assert "device_name" in data
        assert "status" in data


class TestDeviceMetricsAPI:
    """设备指标接口测试"""
    
    @patch('modules.collection.device_manager.get_device_manager')
    def test_get_device_metrics(self, mock_manager, client):
        """测试获取设备指标"""
        mock_manager_instance = MagicMock()
        mock_metrics = MagicMock()
        mock_metrics.device_name = "server-01"
        mock_metrics.device_ip = "192.168.1.10"
        mock_metrics.device_type = "linux"
        mock_metrics.vendor = "dell"
        mock_metrics.timestamp = datetime.now()
        mock_metrics.status = MagicMock(value="online")
        mock_metrics.metrics = {"cpu": 50, "memory": 60}
        mock_metrics.error = None
        
        mock_manager_instance.get_last_metrics.return_value = mock_metrics
        mock_manager.return_value = mock_manager_instance
        
        response = client.get("/server-01/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["device_name"] == "server-01"
        assert "metrics" in data
    
    @patch('modules.collection.device_manager.get_device_manager')
    def test_get_device_metrics_not_found(self, mock_manager, client):
        """测试获取不存在的设备指标"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_last_metrics.return_value = None
        mock_manager.return_value = mock_manager_instance
        
        response = client.get("/nonexistent/metrics")
        assert response.status_code == 404


class TestAdapterAPI:
    """适配器接口测试"""
    
    @patch('modules.collection.adapter_registry.get_registry')
    def test_list_adapters(self, mock_registry, client):
        """测试获取适配器列表"""
        mock_registry_instance = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.name = "ssh"
        mock_adapter.protocol = MagicMock(value="ssh")
        mock_adapter.default_port = 22
        mock_adapter.capabilities = ["command", "script"]
        mock_adapter.required_credentials = ["username"]
        mock_adapter.optional_credentials = ["password", "key_file"]
        mock_adapter.description = "SSH采集适配器"
        mock_adapter.version = "1.0"
        
        mock_registry_instance.list_adapters.return_value = [mock_adapter]
        mock_registry.return_value = mock_registry_instance
        
        response = client.get("/adapters/list")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @patch('modules.collection.adapter_registry.get_registry')
    def test_list_adapters_with_protocol_filter(self, mock_registry, client):
        """测试按协议过滤适配器"""
        mock_registry_instance = MagicMock()
        mock_registry_instance.list_adapters.return_value = []
        mock_registry.return_value = mock_registry_instance
        
        response = client.get("/adapters/list?protocol=ssh")
        assert response.status_code == 200
    
    def test_list_protocols(self, client):
        """测试获取协议列表"""
        response = client.get("/adapters/protocols")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestConfigAPI:
    """配置接口测试"""
    
    @patch('modules.collection.config_loader.reload_config')
    def test_reload_config(self, mock_reload, client):
        """测试重新加载配置"""
        mock_reload.return_value = None
        
        response = client.post("/config/reload")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('modules.collection.config_loader.get_config_loader')
    def test_get_config_stats(self, mock_loader, client):
        """测试获取配置统计"""
        mock_loader_instance = MagicMock()
        mock_loader_instance.get_stats.return_value = {
            "total_devices": 10,
            "enabled_devices": 8,
            "by_type": {"linux": 5, "windows": 3},
            "by_vendor": {"dell": 4, "hp": 4}
        }
        mock_loader.return_value = mock_loader_instance
        
        response = client.get("/config/stats")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
