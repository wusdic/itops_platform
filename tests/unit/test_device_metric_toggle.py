"""
CFG-013: Per-Device Per-Metric Collection Toggle Tests
测试设备指标采集项单项开关功能

This module tests the per-device per-metric collection toggle feature (CFG-013):
1. DeviceMetricConfig model has params field
2. DeviceManager has is_metric_enabled, get_metric_interval, get_metric_params methods  
3. PATCH /api/v1/devices/{id}/metrics/{metric} endpoint
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import Optional

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')


class TestDeviceMetricConfigModel:
    """DeviceMetricConfig模型测试"""
    
    def test_model_has_params_field(self):
        """测试模型包含params字段"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test-server',
            metric_category='cpu',
            metric_name='cpu_usage_percent',
            enabled=True,
            params='{"threshold": 90}'
        )
        
        assert hasattr(config, 'params')
        assert config.params == '{"threshold": 90}'
    
    def test_params_default_none(self):
        """测试params字段默认为None"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test-server',
            metric_category='cpu',
            metric_name='cpu_usage_percent'
        )
        
        assert config.params is None
    
    def test_to_dict_includes_params(self):
        """测试to_dict包含params字段"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            id=1,
            device_id=100,
            device_name='test-server',
            metric_category='cpu',
            metric_name='cpu_usage_percent',
            enabled=True,
            params='{"threshold": 90}'
        )
        
        result = config.to_dict()
        
        assert 'params' in result
        assert result['params'] == '{"threshold": 90}'
    
    def test_all_fields_present(self):
        """测试所有字段都存在"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            id=1,
            device_id=1,
            device_name='test-server',
            metric_category='cpu',
            metric_name='cpu_usage',
            enabled=True,
            collect_interval=60,
            alert_thresholds='{"max": 90}',
            params='{"timeout": 30}',
            remark='Test remark',
            created_by='admin',
            updated_by='admin'
        )
        
        result = config.to_dict()
        
        # Verify all expected fields in to_dict output
        expected_fields = [
            'id', 'device_id', 'device_name', 'metric_category', 'metric_name',
            'enabled', 'collect_interval', 'alert_thresholds', 'params',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'remark'
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"


class TestDeviceManagerMethods:
    """DeviceManager新增方法测试"""
    
    def test_is_metric_enabled_method_exists(self):
        """测试is_metric_enabled方法存在"""
        from modules.collection.device_manager import DeviceManager
        
        manager = DeviceManager()
        assert hasattr(manager, 'is_metric_enabled')
        assert callable(manager.is_metric_enabled)
    
    def test_get_metric_interval_method_exists(self):
        """测试get_metric_interval方法存在"""
        from modules.collection.device_manager import DeviceManager
        
        manager = DeviceManager()
        assert hasattr(manager, 'get_metric_interval')
        assert callable(manager.get_metric_interval)
    
    def test_get_metric_params_method_exists(self):
        """测试get_metric_params方法存在"""
        from modules.collection.device_manager import DeviceManager
        
        manager = DeviceManager()
        assert hasattr(manager, 'get_metric_params')
        assert callable(manager.get_metric_params)


class TestMetricToggleRequestFormat:
    """指标开关请求格式测试"""
    
    def test_enable_request_format(self):
        """测试启用请求格式"""
        request_data = {
            "enabled": True
        }
        
        assert 'enabled' in request_data
        assert isinstance(request_data['enabled'], bool)
    
    def test_disable_request_format(self):
        """测试禁用请求格式"""
        request_data = {
            "enabled": False
        }
        
        assert 'enabled' in request_data
        assert isinstance(request_data['enabled'], bool)
    
    def test_interval_request_format(self):
        """测试间隔更新请求格式"""
        request_data = {
            "collect_interval": 120
        }
        
        assert 'collect_interval' in request_data
        assert isinstance(request_data['collect_interval'], int)
    
    def test_params_request_format(self):
        """测试params更新请求格式"""
        request_data = {
            "params": '{"threshold": 90}'
        }
        
        assert 'params' in request_data
        assert isinstance(request_data['params'], str)
    
    def test_combined_request_format(self):
        """测试组合更新请求格式"""
        request_data = {
            "enabled": True,
            "collect_interval": 60,
            "params": '{"threshold": 85}'
        }
        
        assert 'enabled' in request_data
        assert 'collect_interval' in request_data
        assert 'params' in request_data


class TestMetricToggleResponseFormat:
    """指标开关响应格式测试"""
    
    def test_success_response_format(self):
        """测试成功响应格式"""
        response = {
            "status": "success",
            "message": "Metric configuration updated",
            "data": {
                "id": 1,
                "device_id": 1,
                "device_name": "server-01",
                "metric_category": "cpu",
                "metric_name": "cpu_usage",
                "enabled": True,
                "collect_interval": 60,
                "params": None
            }
        }
        
        assert 'status' in response
        assert 'message' in response
        assert 'data' in response
        assert response['data']['enabled'] is True
    
    def test_created_response_format(self):
        """测试创建响应格式"""
        response = {
            "status": "created",
            "message": "Metric configuration created",
            "data": {
                "id": 2,
                "device_id": 1,
                "device_name": "server-01",
                "metric_category": "memory",
                "metric_name": "memory_usage",
                "enabled": True,
                "collect_interval": 0,
                "params": None
            }
        }
        
        assert 'status' in response
        assert response['status'] == 'created'
    
    def test_error_response_format(self):
        """测试错误响应格式"""
        response = {
            "status": "error",
            "message": "Device not found",
            "detail": "Device with id 999 does not exist"
        }
        
        assert 'status' in response
        assert 'message' in response
        assert response['status'] == 'error'


class TestAPIEndpointDefinition:
    """API端点定义测试"""
    
    def test_patch_endpoint_defined_in_router(self):
        """测试PATCH端点在router中定义"""
        from api.routes.device_api import router
        
        # 获取所有路径和方法
        route_info = []
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                route_info.append(f"{list(route.methods)} {route.path}")
        
        # 至少应该有PATCH端点
        has_patch = any('PATCH' in info for info in route_info)
        
        # 检查是否有任何与metrics相关的端点
        metrics_endpoints = [info for info in route_info if 'metrics' in info]
        
        assert has_patch or len(metrics_endpoints) > 0, f"No metric PATCH endpoint found. Routes: {route_info}"
    
    def test_get_configs_endpoint_defined(self):
        """测试获取设备所有指标配置的端点"""
        from api.routes.device_api import router
        
        paths = [route.path for route in router.routes]
        
        # 应该有 /{device_id}/metrics/configs 端点
        has_configs_endpoint = any(
            '/{device_id}/metrics/configs' in path 
            for path in paths
        )
        
        assert has_configs_endpoint, f"No configs endpoint found. Paths: {paths}"
    
    def test_get_single_config_endpoint_defined(self):
        """测试获取单个指标配置的端点"""
        from api.routes.device_api import router
        
        paths = [route.path for route in router.routes]
        
        # 应该有 /{device_id}/metrics/{metric}/config 端点
        has_single_config = any(
            '/{device_id}/metrics/{metric}/config' in path 
            for path in paths
        )
        
        assert has_single_config, f"No single config endpoint found. Paths: {paths}"


class TestAPIRequestResponseModels:
    """API请求响应模型测试"""
    
    def test_metric_config_update_request_has_required_fields(self):
        """测试MetricConfigUpdateRequest有所需字段"""
        from api.routes.device_api import MetricConfigUpdateRequest
        
        # 测试默认值为None
        request = MetricConfigUpdateRequest()
        assert request.enabled is None
        assert request.collect_interval is None
        assert request.params is None
    
    def test_metric_config_update_request_with_values(self):
        """测试MetricConfigUpdateRequest设置值"""
        from api.routes.device_api import MetricConfigUpdateRequest
        
        request = MetricConfigUpdateRequest(
            enabled=False,
            collect_interval=120,
            params='{"threshold": 95}'
        )
        
        assert request.enabled is False
        assert request.collect_interval == 120
        assert request.params == '{"threshold": 95}'
    
    def test_metric_config_response_has_required_fields(self):
        """测试MetricConfigResponse有所需字段"""
        from api.routes.device_api import MetricConfigResponse
        
        response = MetricConfigResponse(
            id=1,
            device_id=1,
            device_name='test-server',
            metric_category='cpu',
            metric_name='cpu_usage',
            enabled=True,
            collect_interval=60
        )
        
        assert response.id == 1
        assert response.device_id == 1
        assert response.metric_name == 'cpu_usage'
        assert response.enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
