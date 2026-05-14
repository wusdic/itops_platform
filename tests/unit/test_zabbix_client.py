"""
Zabbix客户端单元测试
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import json


class TestZabbixClient(unittest.TestCase):
    """Zabbix客户端测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        client = ZabbixClient(
            url='http://test/zabbix/api_jsonrpc.php',
            user='admin',
            password='password'
        )
        
        self.assertEqual(client.url, 'http://test/zabbix/api_jsonrpc.php')
        self.assertEqual(client.user, 'admin')
        self.assertIsNone(client.auth_token)
    
    @patch('modules.collection.api_collector.zabbix_client.urlopen')
    def test_login(self, mock_urlopen):
        """测试登录"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'jsonrpc': '2.0',
            'result': 'test-auth-token-123',
            'id': 1
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        result = client.login()
        
        self.assertTrue(result)
        self.assertEqual(client.auth_token, 'test-auth-token-123')
    
    @patch('modules.collection.api_collector.zabbix_client.urlopen')
    def test_get_hosts(self, mock_urlopen):
        """测试获取主机"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'result': [
                {'hostid': '1', 'host': 'server1', 'name': 'Server 1'},
                {'hostid': '2', 'host': 'server2', 'name': 'Server 2'}
            ]
        }).encode()
        
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'  # 跳过登录
        
        hosts = client.host_get(output=['hostid', 'host', 'name'])
        
        self.assertEqual(len(hosts), 2)
        self.assertEqual(hosts[0]['host'], 'server1')
    
    @patch('modules.collection.api_collector.zabbix_client.urlopen')
    def test_get_items(self, mock_urlopen):
        """测试获取监控项"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'result': [
                {
                    'itemid': '1',
                    'name': 'CPU Usage',
                    'key_': 'system.cpu.util',
                    'lastvalue': '45.5'
                }
            ]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'
        
        items = client.item_get(search={'key_': 'system.cpu.util'})
        
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'CPU Usage')
    
    @patch('modules.collection.api_collector.zabbix_client.urlopen')
    def test_get_triggers(self, mock_urlopen):
        """测试获取触发器"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'result': [
                {
                    'triggerid': '1',
                    'description': 'High CPU Usage',
                    'priority': '3',
                    'status': '0',
                    'value': '1'
                }
            ]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = ZabbixClient()
        client.auth_token = 'test-token'
        
        triggers = client.trigger_get(only_true=True)
        
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]['description'], 'High CPU Usage')


class TestZabbixContextManager(unittest.TestCase):
    """Zabbix上下文管理器测试"""
    
    @patch('modules.collection.api_collector.zabbix_client.urlopen')
    def test_context_manager(self, mock_urlopen):
        """测试上下文管理器"""
        from modules.collection.api_collector.zabbix_client import ZabbixClient
        
        # Mock响应
        mock_login_response = Mock()
        mock_login_response.read.return_value = json.dumps({
            'result': 'test-token'
        }).encode()
        mock_login_response.__enter__ = Mock(return_value=mock_login_response)
        mock_login_response.__exit__ = Mock(return_value=False)
        
        mock_logout_response = Mock()
        mock_logout_response.read.return_value = json.dumps({
            'result': True
        }).encode()
        mock_logout_response.__enter__ = Mock(return_value=mock_logout_response)
        mock_logout_response.__exit__ = Mock(return_value=False)
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'result': [{'hostid': '1', 'host': 'server1'}]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        
        mock_urlopen.side_effect = [mock_login_response, mock_response, mock_logout_response]
        
        with ZabbixClient() as client:
            hosts = client.host_get(output=['hostid', 'host'])
            self.assertEqual(len(hosts), 1)
        
        self.assertIsNone(client.auth_token)


class TestZabbixAPIError(unittest.TestCase):
    """Zabbix API错误测试"""
    
    def test_error_exception(self):
        """测试异常类"""
        from modules.collection.api_collector.zabbix_client import ZabbixAPIError
        
        error = ZabbixAPIError(
            code=-32600,
            message='Invalid Request',
            data='Method not found'
        )
        
        self.assertEqual(error.code, -32600)
        self.assertEqual(error.message, 'Invalid Request')
        self.assertIn('Invalid Request', str(error))


if __name__ == '__main__':
    unittest.main()
