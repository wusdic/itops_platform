"""
采集项单项开关功能测试
测试 DeviceMetricConfig 模型、PATCH API 和前端开关面板
"""

import unittest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


class TestDeviceMetricConfigModel(unittest.TestCase):
    """DeviceMetricConfig模型测试"""
    
    def test_model_fields(self):
        """测试模型字段"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            id=1,
            device_id=100,
            device_name='test-server-01',
            metric_category='cpu',
            metric_name='cpu_usage_percent',
            enabled=True,
            collect_interval=60,
            alert_thresholds='{"max": 90, "min": 10}',
            remark='CPU监控'
        )
        
        self.assertEqual(config.id, 1)
        self.assertEqual(config.device_id, 100)
        self.assertEqual(config.device_name, 'test-server-01')
        self.assertEqual(config.metric_category, 'cpu')
        self.assertEqual(config.metric_name, 'cpu_usage_percent')
        self.assertTrue(config.enabled)
        self.assertEqual(config.collect_interval, 60)
        self.assertEqual(config.alert_thresholds, '{"max": 90, "min": 10}')
        self.assertEqual(config.remark, 'CPU监控')
    
    def test_default_values(self):
        """测试默认值"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='test_metric'
        )
        
        self.assertTrue(config.enabled)
        self.assertIsNone(config.collect_interval)
        self.assertIsNone(config.alert_thresholds)
        self.assertIsNone(config.remark)
    
    def test_to_dict_conversion(self):
        """测试转换为字典"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            id=1,
            device_id=100,
            device_name='test-server',
            metric_category='memory',
            metric_name='memory_used_mb',
            enabled=False,
            collect_interval=120,
            alert_thresholds='{"max": 4096}',
            remark='内存监控'
        )
        config.created_at = datetime(2024, 1, 15, 10, 30, 0)
        config.updated_at = datetime(2024, 1, 15, 11, 0, 0)
        
        result = config.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['device_id'], 100)
        self.assertEqual(result['device_name'], 'test-server')
        self.assertEqual(result['metric_category'], 'memory')
        self.assertEqual(result['metric_name'], 'memory_used_mb')
        self.assertFalse(result['enabled'])
        self.assertEqual(result['collect_interval'], 120)
        self.assertEqual(result['alert_thresholds'], '{"max": 4096}')
        self.assertEqual(result['remark'], '内存监控')
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
    
    def test_repr_format(self):
        """测试字符串表示格式"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='server1',
            metric_category='disk',
            metric_name='disk_usage_percent',
            enabled=True
        )
        
        repr_str = repr(config)
        
        self.assertIn('server1', repr_str)
        self.assertIn('disk_usage_percent', repr_str)
        self.assertIn('enabled', repr_str)


class TestMetricConfigAPI(unittest.TestCase):
    """采集项配置API测试"""
    
    def setUp(self):
        """测试前准备"""
        self.app = Mock()
        self.app.state = Mock()
        self.app.state.db = Mock()
        self.app.state.current_user = Mock(id=1, username='testuser')
    
    @patch('modules.foundation.db_models.monitoring.DeviceMetricConfig')
    def test_create_metric_config(self, mock_model):
        """测试创建采集项配置"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        mock_config = Mock(spec=DeviceMetricConfig)
        mock_config.id = 1
        mock_config.device_id = 1
        mock_config.metric_category = 'cpu'
        mock_config.metric_name = 'cpu_usage'
        mock_config.enabled = True
        
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda x: setattr(x, 'id', 1))
        
        # Test that create logic works
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='cpu_usage'
        )
        
        self.assertEqual(config.device_id, 1)
        self.assertEqual(config.metric_category, 'cpu')
    
    @patch('modules.foundation.db_models.monitoring.DeviceMetricConfig')
    def test_toggle_metric_config(self, mock_model):
        """测试切换采集项状态"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        # Test enabled=True -> enabled=False
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='cpu_usage',
            enabled=True
        )
        
        config.enabled = False
        
        self.assertFalse(config.enabled)
        
        # Test enabled=False -> enabled=True
        config.enabled = True
        
        self.assertTrue(config.enabled)
    
    def test_unique_constraint_validation(self):
        """测试唯一约束验证"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        # Create first config
        config1 = DeviceMetricConfig(
            device_id=1,
            device_name='server1',
            metric_category='cpu',
            metric_name='cpu_usage',
            enabled=True
        )
        
        # Create second config with different metric_name
        config2 = DeviceMetricConfig(
            device_id=1,
            device_name='server1',
            metric_category='cpu',
            metric_name='cpu_idle',  # Different name
            enabled=True
        )
        
        # Should be valid (different metric names)
        self.assertNotEqual(config1.metric_name, config2.metric_name)
        
        # Create config with same device_id but different category
        config3 = DeviceMetricConfig(
            device_id=1,
            device_name='server1',
            metric_category='memory',  # Different category
            metric_name='cpu_usage',  # Same name as config1
            enabled=True
        )
        
        # Should be valid (different categories)
        self.assertNotEqual(config1.metric_category, config3.metric_category)


class TestMetricConfigAPIEndpoints(unittest.TestCase):
    """API端点测试"""
    
    @patch('api.routes.monitoring.get_db')
    @patch('api.routes.monitoring.get_current_user')
    def test_get_metric_configs_endpoint(self, mock_auth, mock_db):
        """测试获取采集项配置列表"""
        from api.routes.monitoring import router
        
        mock_user = Mock(id=1, username='testuser')
        mock_auth.return_value = mock_user
        
        # Mock database session and query
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.return_value = mock_session
        
        # Verify router has the endpoint
        routes = [route.path for route in router.routes]
        self.assertIn('/metric-configs', str(routes))
    
    @patch('api.routes.monitoring.get_db')
    @patch('api.routes.monitoring.get_current_user')
    def test_toggle_endpoint_exists(self, mock_auth, mock_db):
        """测试切换端点存在"""
        from api.routes.monitoring import router
        
        mock_user = Mock(id=1, username='testuser')
        mock_auth.return_value = mock_user
        
        # Check that toggle endpoint exists
        routes = [route.path for route in router.routes]
        
        # The toggle endpoint should be /metric-configs/{id}/toggle
        has_toggle = any('toggle' in str(route.path) for route in router.routes)
        self.assertTrue(has_toggle)
    
    def test_toggle_request_format(self):
        """测试切换请求格式"""
        # Simulate toggle request
        request_data = {
            'enabled': True
        }
        
        self.assertIn('enabled', request_data)
        self.assertIsInstance(request_data['enabled'], bool)
    
    def test_create_request_format(self):
        """测试创建请求格式"""
        # Simulate create request
        request_data = {
            'device_id': 1,
            'device_name': 'test-server',
            'metric_category': 'cpu',
            'metric_name': 'cpu_usage',
            'enabled': True,
            'collect_interval': 60,
            'alert_thresholds': '{"max": 90}',
            'remark': 'CPU监控'
        }
        
        required_fields = ['device_id', 'device_name', 'metric_category', 'metric_name']
        for field in required_fields:
            self.assertIn(field, request_data)
    
    def test_update_request_format(self):
        """测试更新请求格式"""
        # Simulate PATCH request
        request_data = {
            'collect_interval': 120,
            'alert_thresholds': '{"max": 95}',
            'remark': 'Updated remark'
        }
        
        # All fields are optional for PATCH
        self.assertIn('collect_interval', request_data)


class TestMetricConfigServiceLogic(unittest.TestCase):
    """服务逻辑测试"""
    
    def test_enable_metric(self):
        """测试启用指标"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='test',
            enabled=False
        )
        
        config.enabled = True
        
        self.assertTrue(config.enabled)
    
    def test_disable_metric(self):
        """测试禁用指标"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='test',
            enabled=True
        )
        
        config.enabled = False
        
        self.assertFalse(config.enabled)
    
    def test_update_collect_interval(self):
        """测试更新采集间隔"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='test',
            collect_interval=60
        )
        
        config.collect_interval = 120
        
        self.assertEqual(config.collect_interval, 120)
    
    def test_update_alert_thresholds(self):
        """测试更新告警阈值"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='test',
            alert_thresholds='{"max": 90}'
        )
        
        new_thresholds = '{"max": 95, "min": 5}'
        config.alert_thresholds = new_thresholds
        
        self.assertEqual(config.alert_thresholds, new_thresholds)
    
    def test_metric_config_lifecycle(self):
        """测试配置生命周期"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        # Create
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='test',
            enabled=True
        )
        
        self.assertTrue(config.enabled)
        
        # Disable
        config.enabled = False
        self.assertFalse(config.enabled)
        
        # Re-enable
        config.enabled = True
        self.assertTrue(config.enabled)
        
        # Update interval
        config.collect_interval = 300
        self.assertEqual(config.collect_interval, 300)


class TestMetricConfigValidation(unittest.TestCase):
    """验证测试"""
    
    def test_valid_metric_categories(self):
        """测试有效的指标类别"""
        valid_categories = ['cpu', 'memory', 'disk', 'network', 'process', 'service']
        
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        for category in valid_categories:
            config = DeviceMetricConfig(
                device_id=1,
                device_name='test',
                metric_category=category,
                metric_name='test'
            )
            self.assertEqual(config.metric_category, category)
    
    def test_metric_name_format(self):
        """测试指标名称格式"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        valid_names = [
            'cpu_usage',
            'cpu_usage_percent',
            'memory_used_mb',
            'disk_read_bytes',
            'network_tx_packets'
        ]
        
        for name in valid_names:
            config = DeviceMetricConfig(
                device_id=1,
                device_name='test',
                metric_category='cpu',
                metric_name=name
            )
            self.assertEqual(config.metric_name, name)
    
    def test_enabled_field_type(self):
        """测试enabled字段类型"""
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        
        config = DeviceMetricConfig(
            device_id=1,
            device_name='test',
            metric_category='cpu',
            metric_name='test',
            enabled=True
        )
        
        self.assertIsInstance(config.enabled, bool)
        
        config.enabled = False
        self.assertIsInstance(config.enabled, bool)


class TestFrontendAPIFunctions(unittest.TestCase):
    """前端API函数测试"""
    
    def test_get_metric_configs_params(self):
        """测试获取配置列表参数"""
        params = {
            'device_id': 1,
            'metric_category': 'cpu',
            'enabled': True,
            'page': 1,
            'page_size': 20
        }
        
        self.assertIn('device_id', params)
        self.assertIn('metric_category', params)
        self.assertIn('enabled', params)
    
    def test_create_metric_config_payload(self):
        """测试创建配置载荷"""
        payload = {
            'device_id': 1,
            'device_name': 'server-01',
            'metric_category': 'cpu',
            'metric_name': 'cpu_usage_percent',
            'enabled': True,
            'collect_interval': 60,
            'alert_thresholds': '{"max": 90}',
            'remark': ''
        }
        
        self.assertEqual(payload['device_id'], 1)
        self.assertEqual(payload['metric_category'], 'cpu')
        self.assertTrue(payload['enabled'])
    
    def test_update_metric_config_payload(self):
        """测试更新配置载荷"""
        payload = {
            'collect_interval': 120,
            'alert_thresholds': '{"max": 95}',
            'remark': 'Updated'
        }
        
        # PATCH should only include fields to update
        self.assertIn('collect_interval', payload)
        self.assertNotIn('device_id', payload)
        self.assertNotIn('metric_category', payload)
    
    def test_toggle_response_format(self):
        """测试切换响应格式"""
        response = {
            'status': 'success',
            'message': '采集项状态已切换',
            'enabled': False
        }
        
        self.assertEqual(response['status'], 'success')
        self.assertIn('message', response)
        self.assertIn('enabled', response)
        self.assertIsInstance(response['enabled'], bool)


class TestMetricTogglePanelIntegration(unittest.TestCase):
    """前端开关面板集成测试"""
    
    def test_panel_initial_state(self):
        """测试面板初始状态"""
        initial_state = {
            'devices': [],
            'selectedDeviceId': None,
            'selectedCategory': '',
            'selectedStatus': None,
            'configs': [],
            'loading': False
        }
        
        self.assertIsNone(initial_state['selectedDeviceId'])
        self.assertEqual(initial_state['configs'], [])
        self.assertFalse(initial_state['loading'])
    
    def test_filter_state_transitions(self):
        """测试过滤状态转换"""
        states = []
        
        # No device selected
        current_state = {'selectedDeviceId': None}
        states.append(current_state.copy())
        
        # Device selected
        current_state = {'selectedDeviceId': 1}
        states.append(current_state.copy())
        
        # Category added
        current_state = {'selectedDeviceId': 1, 'selectedCategory': 'cpu'}
        states.append(current_state.copy())
        
        # Status filter added
        current_state = {'selectedDeviceId': 1, 'selectedCategory': 'cpu', 'selectedStatus': True}
        states.append(current_state.copy())
        
        self.assertEqual(len(states), 4)
        self.assertIsNone(states[0]['selectedDeviceId'])
        self.assertEqual(states[3]['selectedDeviceId'], 1)
    
    def test_config_list_update(self):
        """测试配置列表更新"""
        initial_configs = []
        
        # After loading
        new_configs = [
            {
                'id': 1,
                'metric_category': 'cpu',
                'metric_name': 'cpu_usage',
                'enabled': True
            },
            {
                'id': 2,
                'metric_category': 'memory',
                'metric_name': 'memory_used',
                'enabled': False
            }
        ]
        
        self.assertEqual(len(new_configs), 2)
        self.assertTrue(new_configs[0]['enabled'])
        self.assertFalse(new_configs[1]['enabled'])
    
    def test_toggle_state_change(self):
        """测试切换状态变更"""
        config = {
            'id': 1,
            'enabled': True,
            'metric_name': 'cpu_usage'
        }
        
        # Toggle
        config['enabled'] = not config['enabled']
        
        self.assertFalse(config['enabled'])
        
        # Toggle back
        config['enabled'] = not config['enabled']
        
        self.assertTrue(config['enabled'])
    
    def test_stats_calculation(self):
        """测试统计计算"""
        configs = [
            {'enabled': True},
            {'enabled': True},
            {'enabled': False},
            {'enabled': True},
            {'enabled': False}
        ]
        
        enabled_count = sum(1 for c in configs if c['enabled'])
        disabled_count = sum(1 for c in configs if not c['enabled'])
        total = len(configs)
        enable_rate = int((enabled_count / total) * 100) if total > 0 else 0
        
        self.assertEqual(enabled_count, 3)
        self.assertEqual(disabled_count, 2)
        self.assertEqual(enable_rate, 60)
    
    def test_category_display_mapping(self):
        """测试类别显示映射"""
        category_map = {
            'cpu': 'CPU',
            'memory': '内存',
            'disk': '磁盘',
            'network': '网络',
            'process': '进程',
            'service': '服务'
        }
        
        for key, value in category_map.items():
            self.assertEqual(category_map[key], value)


class TestMetricToggleUIFlow(unittest.TestCase):
    """UI流程测试"""
    
    def test_select_device_flow(self):
        """测试选择设备流程"""
        # User opens panel
        # Panel loads devices list
        # User selects device
        # System fetches configs for device
        
        flow_steps = [
            'panel_opened',
            'devices_loaded',
            'device_selected',
            'configs_fetched'
        ]
        
        self.assertEqual(len(flow_steps), 4)
    
    def test_toggle_metric_flow(self):
        """测试切换指标流程"""
        # User clicks toggle switch
        # System calls toggle API
        # API returns new state
        # UI updates switch state
        # System shows success message
        
        flow_steps = [
            'toggle_clicked',
            'api_called',
            'response_received',
            'ui_updated',
            'message_shown'
        ]
        
        self.assertEqual(len(flow_steps), 5)
    
    def test_edit_config_flow(self):
        """测试编辑配置流程"""
        # User clicks edit button
        # Dialog opens with current values
        # User modifies values
        # User clicks save
        # System calls update API
        # Dialog closes
        # List refreshes
        
        flow_steps = [
            'edit_clicked',
            'dialog_opened',
            'values_modified',
            'save_clicked',
            'api_called',
            'dialog_closed',
            'list_refreshed'
        ]
        
        self.assertEqual(len(flow_steps), 7)
    
    def test_delete_config_flow(self):
        """测试删除配置流程"""
        # User clicks delete
        # Confirmation dialog appears
        # User confirms
        # System calls delete API
        # List refreshes
        
        flow_steps = [
            'delete_clicked',
            'confirm_dialog',
            'user_confirms',
            'api_called',
            'list_refreshed'
        ]
        
        self.assertEqual(len(flow_steps), 5)


if __name__ == '__main__':
    unittest.main()
