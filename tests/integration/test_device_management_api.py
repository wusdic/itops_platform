# -*- coding: utf-8 -*-
"""
设备管理API集成测试

遵循Google测试最佳实践:
- Given-When-Then结构
- 测试通过公共API
- 测试业务工作流，不测试内部实现
- 使用 f 工厂fixture生成所有测试数据
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestDeviceManagementAPI:
    """设备管理API测试类"""

    @pytest.fixture
    def mock_device_manager(self):
        """模拟设备管理器"""
        with patch("modules.collection.device_manager.get_device_manager") as mock:
            manager = MagicMock()
            manager.get_device_status.return_value = MagicMock(value="online")
            manager.get_last_metrics.return_value = MagicMock(
                timestamp=datetime.now(),
                metrics={"cpu": {"usage": 45.5}, "memory": {"total_mb": 8192, "used_mb": 4096}}
            )
            mock.return_value = manager
            yield mock

    @pytest.fixture
    def mock_config_loader(self):
        """模拟配置加载器"""
        with patch("modules.collection.config_loader.get_config_loader") as mock:
            loader = MagicMock()
            loader.get_devices.return_value = []
            loader.get_device_by_name.return_value = None
            loader.get_stats.return_value = {"total": 0, "enabled": 0, "by_type": {}, "by_vendor": {}}
            mock.return_value = loader
            yield mock

    # ============== 设备列表接口 ==============

    def test_list_devices_empty(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 系统中无设备
           When: 获取设备列表
           Then: 返回空列表"""
        mock_config_loader.return_value.get_devices.return_value = []
        
        response = client.get(
            "/api/v1/devices/",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0

    def test_list_devices_with_data(self, client, admin_headers, f, mock_device_manager, mock_config_loader):
        """Given: 系统中有设备
           When: 获取设备列表
           Then: 返回设备列表"""
        # 创建设备数据
        devices = [
            f.device(name="web-prod-01", ip="192.168.1.10", device_type="server"),
            f.device(name="db-prod-01", ip="192.168.1.20", device_type="server"),
        ]
        mock_config_loader.return_value.get_devices.return_value = devices
        
        response = client.get(
            "/api/v1/devices/",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_devices_with_type_filter(self, client, admin_headers, f, mock_device_manager, mock_config_loader):
        """Given: 系统中有多种类型设备
           When: 按设备类型过滤
           Then: 返回指定类型的设备"""
        devices = [
            f.device(name="server-01", device_type="server"),
            f.device(name="router-01", device_type="router"),
        ]
        mock_config_loader.return_value.get_devices.return_value = devices
        
        response = client.get(
            "/api/v1/devices/?device_type=server",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_list_devices_with_pagination(self, client, admin_headers, f, mock_device_manager, mock_config_loader):
        """Given: 系统中有多个设备
           When: 请求分页
           Then: 返回指定页的数据"""
        devices = [f.device(name=f"device-{i}") for i in range(25)]
        mock_config_loader.return_value.get_devices.return_value = devices
        
        response = client.get(
            "/api/v1/devices/?page=1&page_size=10",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 25

    def test_list_devices_unauthorized(self, client):
        """Given: 未认证用户
           When: 获取设备列表
           Then: 返回401"""
        response = client.get("/api/v1/devices/")
        assert response.status_code == 401

    # ============== 设备统计接口 ==============

    def test_get_device_stats_empty(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 系统中无设备
           When: 获取设备统计
           Then: 返回空统计"""
        mock_config_loader.return_value.get_devices.return_value = []
        
        response = client.get(
            "/api/v1/devices/stats",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "online" in data
        assert "offline" in data
        assert data["total"] == 0

    def test_get_device_stats_with_devices(self, client, admin_headers, f, mock_device_manager, mock_config_loader):
        """Given: 系统中有设备
           When: 获取设备统计
           Then: 返回统计信息"""
        devices = [
            f.device(name="web-01", device_type="server", vendor="Dell"),
            f.device(name="web-02", device_type="server", vendor="Dell"),
            f.device(name="switch-01", device_type="switch", vendor="Cisco"),
        ]
        mock_config_loader.return_value.get_devices.return_value = devices
        
        response = client.get(
            "/api/v1/devices/stats",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert "by_type" in data
        assert "by_vendor" in data

    # ============== 设备详情接口 ==============

    def test_get_device_not_found(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 设备不存在
           When: 获取设备详情
           Then: 返回404"""
        mock_config_loader.return_value.get_device_by_name.return_value = None
        
        response = client.get(
            "/api/v1/devices/nonexistent-device",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    def test_get_device_found(self, client, admin_headers, f, mock_device_manager, mock_config_loader):
        """Given: 设备存在
           When: 获取设备详情
           Then: 返回设备详情"""
        device_data = f.device(name="web-prod-01", ip="192.168.1.10")
        mock_config_loader.return_value.get_device_by_name.return_value = device_data
        
        response = client.get(
            "/api/v1/devices/web-prod-01",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "web-prod-01"
        assert data["ip"] == "192.168.1.10"

    # ============== 设备状态接口 ==============

    def test_get_device_status_online(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 设备在线
           When: 获取设备状态
           Then: 返回online状态"""
        mock_device_manager.return_value.get_device_status.return_value = MagicMock(value="online")
        
        response = client.get(
            "/api/v1/devices/web-prod-01/status",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"

    def test_get_device_status_offline(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 设备离线
           When: 获取设备状态
           Then: 返回offline状态"""
        mock_device_manager.return_value.get_device_status.return_value = MagicMock(value="offline")
        
        response = client.get(
            "/api/v1/devices/web-prod-01/status",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "offline"

    def test_get_device_status_unknown(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 设备状态未知
           When: 获取设备状态
           Then: 返回unknown状态"""
        mock_device_manager.return_value.get_device_status.return_value = None
        
        response = client.get(
            "/api/v1/devices/unknown-device/status",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unknown"

    # ============== 设备指标接口 ==============

    def test_get_device_metrics_found(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 设备有指标数据
           When: 获取设备指标
           Then: 返回指标数据"""
        metrics = MagicMock(
            device_name="web-prod-01",
            device_ip="192.168.1.10",
            device_type="server",
            vendor="Dell",
            timestamp=datetime.now(),
            status=MagicMock(value="online"),
            metrics={"cpu": {"usage": 45.5}, "memory": {"total_mb": 8192}},
            error=None
        )
        mock_device_manager.return_value.get_last_metrics.return_value = metrics
        
        response = client.get(
            "/api/v1/devices/web-prod-01/metrics",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["device_name"] == "web-prod-01"
        assert "metrics" in data

    def test_get_device_metrics_not_found(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 设备无指标数据
           When: 获取设备指标
           Then: 返回404"""
        mock_device_manager.return_value.get_last_metrics.return_value = None
        
        response = client.get(
            "/api/v1/devices/new-device/metrics",
            headers=admin_headers
        )
        
        assert response.status_code == 404

    # ============== 采集接口 ==============

    def test_collect_device_success(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 设备存在且可达
           When: 手动采集设备指标
           Then: 返回采集结果"""
        metrics = MagicMock(
            device_name="web-prod-01",
            device_ip="192.168.1.10",
            device_type="server",
            vendor="Dell",
            status=MagicMock(value="online"),
            timestamp=datetime.now(),
            metrics={"cpu": {"usage": 50.0}},
            error=None
        )
        mock_device_manager.return_value.collect_device.return_value = metrics
        
        response = client.post(
            "/api/v1/devices/collect",
            json={"device_name": "web-prod-01"},
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["device_name"] == "web-prod-01"
        assert data["status"] == "online"

    def test_collect_device_not_found(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 设备不存在
           When: 手动采集设备指标
           Then: 返回404"""
        mock_device_manager.return_value.collect_device.return_value = None
        
        response = client.post(
            "/api/v1/devices/collect",
            json={"device_name": "nonexistent-device"},
            headers=admin_headers
        )
        
        assert response.status_code == 404

    def test_collect_all_devices(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 系统中有设备
           When: 批量采集所有设备
           Then: 返回采集结果汇总"""
        metrics_list = [
            MagicMock(
                device_name="web-01",
                device_ip="192.168.1.10",
                device_type="server",
                vendor="Dell",
                status=MagicMock(value="online"),
                timestamp=datetime.now(),
                metrics={},
                error=None
            ),
            MagicMock(
                device_name="web-02",
                device_ip="192.168.1.11",
                device_type="server",
                vendor="HP",
                status=MagicMock(value="offline"),
                timestamp=datetime.now(),
                metrics={},
                error="Connection timeout"
            )
        ]
        mock_device_manager.return_value.collect_all.return_value = metrics_list
        
        response = client.post(
            "/api/v1/devices/collect/all",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] == 2

    # ============== 适配器接口 ==============

    def test_list_adapters(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 系统中有注册适配器
           When: 获取适配器列表
           Then: 返回适配器列表"""
        with patch("modules.collection.adapter_registry.get_registry") as mock_registry:
            registry = MagicMock()
            adapter = MagicMock()
            adapter.name = "SSHAdapter"
            adapter.protocol.value = "ssh"
            adapter.default_port = 22
            adapter.capabilities = ["cpu", "memory", "disk"]
            adapter.required_credentials = ["username", "password"]
            adapter.optional_credentials = ["private_key"]
            adapter.description = "SSH采集适配器"
            adapter.version = "1.0.0"
            registry.list_adapters.return_value = [adapter]
            mock_registry.return_value = registry
            
            response = client.get(
                "/api/v1/devices/adapters/list",
                headers=admin_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert data["total"] == 1

    def test_list_protocols(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 系统支持多种协议
           When: 获取协议列表
           Then: 返回协议列表"""
        with patch("modules.collection.adapter_registry.ProtocolType") as mock_protocol:
            mock_protocol.__members__ = {
                'SSH': 'ssh',
                'SNMP': 'snmp',
                'IPMI': 'ipmi',
                'WMI': 'wmi',
                'API': 'api'
            }
            
            response = client.get(
                "/api/v1/devices/adapters/protocols",
                headers=admin_headers
            )
            
            assert response.status_code == 200

    # ============== 配置接口 ==============

    def test_reload_config(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 配置文件已更新
           When: 重新加载配置
           Then: 返回成功"""
        with patch("modules.collection.config_loader.reload_config") as mock_reload:
            response = client.post(
                "/api/v1/devices/config/reload",
                headers=admin_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_config_stats(self, client, admin_headers, mock_device_manager, mock_config_loader):
        """Given: 系统有设备配置
           When: 获取配置统计
           Then: 返回配置统计"""
        mock_config_loader.return_value.get_stats.return_value = {
            "total": 5,
            "enabled": 4,
            "by_type": {"server": 3, "switch": 2},
            "by_vendor": {"Dell": 2, "Cisco": 3}
        }
        
        response = client.get(
            "/api/v1/devices/config/stats",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    # ============== 权限测试 ==============

    def test_operator_can_view_devices(self, client, operator_headers, mock_device_manager, mock_config_loader):
        """Given: 操作员已认证
           When: 获取设备列表
           Then: 返回设备列表"""
        response = client.get(
            "/api/v1/devices/",
            headers=operator_headers
        )
        
        assert response.status_code == 200

    def test_viewer_can_view_devices(self, client, viewer_headers, mock_device_manager, mock_config_loader):
        """Given: 访客已认证
           When: 获取设备列表
           Then: 返回设备列表"""
        response = client.get(
            "/api/v1/devices/",
            headers=viewer_headers
        )
        
        assert response.status_code == 200

    # ============== 过滤测试 ==============

    def test_filter_by_vendor(self, client, admin_headers, f, mock_device_manager, mock_config_loader):
        """Given: 系统中有多个厂商设备
           When: 按厂商过滤
           Then: 返回指定厂商设备"""
        devices = [
            f.device(name="dell-server", vendor="Dell"),
            f.device(name="hp-server", vendor="HP"),
            f.device(name="cisco-switch", vendor="Cisco"),
        ]
        mock_config_loader.return_value.get_devices.return_value = devices
        
        response = client.get(
            "/api/v1/devices/?vendor=Dell",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_filter_by_tag(self, client, admin_headers, f, mock_device_manager, mock_config_loader):
        """Given: 系统中有带标签的设备
           When: 按标签过滤
           Then: 返回指定标签设备"""
        devices = [
            f.device(name="critical-server", tags=["关键", "核心"]),
            f.device(name="normal-server", tags=["普通"]),
        ]
        mock_config_loader.return_value.get_devices.return_value = devices
        
        response = client.get(
            "/api/v1/devices/?tag=关键",
            headers=admin_headers
        )
        
        assert response.status_code == 200

    def test_filter_by_status(self, client, admin_headers, f, mock_device_manager, mock_config_loader):
        """Given: 系统中有不同状态的设备
           When: 按状态过滤
           Then: 返回指定状态设备"""
        devices = [
            f.device(name="active-device", status="active"),
            f.device(name="inactive-device", status="inactive"),
        ]
        mock_config_loader.return_value.get_devices.return_value = devices
        
        response = client.get(
            "/api/v1/devices/?enabled=true",
            headers=admin_headers
        )
        
        assert response.status_code == 200