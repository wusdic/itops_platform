# -*- coding: utf-8 -*-
"""
HTTP客户端扩展单元测试
测试未在专门测试文件中覆盖的部分：
- AsyncHTTPClient 异步客户端
- WebSocketClient WebSocket客户端
- VendorAPIClient 厂商API客户端
- HTTP方法扩展 (PUT, PATCH, DELETE, HEAD)
- 重试机制
- SSL配置
"""

import unittest
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestHTTPMethodEnums(unittest.TestCase):
    """测试HTTP方法枚举"""

    def test_http_method_enum_values(self):
        """测试HTTP方法枚举值"""
        from modules.collection.api_collector.http_client import HTTPMethod
        
        self.assertEqual(HTTPMethod.GET.value, 'GET')
        self.assertEqual(HTTPMethod.POST.value, 'POST')
        self.assertEqual(HTTPMethod.PUT.value, 'PUT')
        self.assertEqual(HTTPMethod.PATCH.value, 'PATCH')
        self.assertEqual(HTTPMethod.DELETE.value, 'DELETE')
        self.assertEqual(HTTPMethod.HEAD.value, 'HEAD')
        self.assertEqual(HTTPMethod.OPTIONS.value, 'OPTIONS')


class TestAuthTypeEnums(unittest.TestCase):
    """测试认证类型枚举"""

    def test_auth_type_enum_values(self):
        """测试认证类型枚举值"""
        from modules.collection.api_collector.http_client import AuthType
        
        self.assertEqual(AuthType.NONE.value, 'none')
        self.assertEqual(AuthType.BASIC.value, 'basic')
        self.assertEqual(AuthType.BEARER.value, 'bearer')
        # API_KEY and OAUTH2 are marked as '***' in source to hide in logs
        self.assertEqual(AuthType.CUSTOM.value, 'custom')


class TestHTTPClientExtensions(unittest.TestCase):
    """测试HTTPClient扩展方法"""

    def test_client_initialization_defaults(self):
        """测试客户端默认初始化"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient()
        
        self.assertEqual(client.base_url, '')
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.max_retries, 3)
        self.assertEqual(client.retry_delay, 1.0)
        self.assertTrue(client.ssl_verify)

    def test_set_auth_basic(self):
        """测试设置Basic认证"""
        from modules.collection.api_collector.http_client import HTTPClient, AuthType
        
        client = HTTPClient()
        result = client.set_auth(AuthType.BASIC, username='admin', password='secret')
        
        # 应该返回self以支持链式调用
        self.assertIs(result, client)
        self.assertEqual(client._auth_type, AuthType.BASIC)

    def test_set_auth_bearer(self):
        """测试设置Bearer认证"""
        from modules.collection.api_collector.http_client import HTTPClient, AuthType
        
        client = HTTPClient()
        result = client.set_auth(AuthType.BEARER, token='jwt-token-here')
        
        self.assertIs(result, client)
        self.assertEqual(client._auth_type, AuthType.BEARER)

    def test_set_auth_api_key(self):
        """测试设置API Key认证"""
        from modules.collection.api_collector.http_client import HTTPClient, AuthType
        
        client = HTTPClient()
        result = client.set_auth(AuthType.API_KEY, key='my-api-key', header='X-Custom-Key')
        
        self.assertIs(result, client)
        self.assertEqual(client._auth_credentials.get('header'), 'X-Custom-Key')

    @patch('modules.collection.api_collector.http_client.urlopen')
    def test_delete_request(self, mock_urlopen):
        """测试DELETE请求"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        mock_response = Mock()
        mock_response.status = 204
        mock_response.headers = {}
        mock_response.read.return_value = b''
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = HTTPClient(base_url='https://api.example.com')
        result = client.delete('/users/1')
        
        self.assertEqual(result['status_code'], 204)

    @patch('modules.collection.api_collector.http_client.urlopen')
    def test_head_request(self, mock_urlopen):
        """测试HEAD请求"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'Content-Length': '100'}  # HEAD has no body
        mock_response.read.return_value = b''
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = HTTPClient(base_url='https://api.example.com')
        result = client.request('HEAD', '/users')
        
        self.assertEqual(result['status_code'], 200)
        self.assertIsNone(result['data'])

    @patch('modules.collection.api_collector.http_client.urlopen')
    def test_put_request(self, mock_urlopen):
        """测试PUT请求"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = json.dumps({'updated': True}).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = HTTPClient(base_url='https://api.example.com')
        result = client.put('/users/1', json_data={'name': 'updated'})
        
        self.assertEqual(result['status_code'], 200)

    @patch('modules.collection.api_collector.http_client.urlopen')
    def test_patch_request(self, mock_urlopen):
        """测试PATCH请求"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = json.dumps({'patched': True}).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = HTTPClient(base_url='https://api.example.com')
        result = client.patch('/users/1', json_data={'field': 'value'})
        
        self.assertEqual(result['status_code'], 200)

    def test_build_url_no_params(self):
        """测试无参数的URL构建"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient(base_url='https://api.example.com')
        url = client._build_url('/users', None)
        
        self.assertEqual(url, 'https://api.example.com/users')

    def test_build_url_with_params(self):
        """测试带参数的URL构建"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient(base_url='https://api.example.com')
        url = client._build_url('/users', {'page': 1, 'limit': 10})
        
        self.assertIn('page=1', url)
        self.assertIn('limit=10', url)

    def test_build_url_empty_endpoint(self):
        """测试空端点的URL构建"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient(base_url='https://api.example.com')
        url = client._build_url('', {'key': 'value'})
        
        self.assertEqual(url, 'https://api.example.com?key=value')

    def test_apply_auth_none(self):
        """测试无认证"""
        from modules.collection.api_collector.http_client import HTTPClient, AuthType
        
        client = HTTPClient()
        client._auth_type = AuthType.NONE
        
        headers = {}
        result = client._apply_auth(headers)
        
        self.assertNotIn('Authorization', result)

    def test_apply_auth_basic(self):
        """测试Basic认证应用"""
        from modules.collection.api_collector.http_client import HTTPClient, AuthType
        
        client = HTTPClient()
        client.set_auth(AuthType.BASIC, username='admin', password='secret')
        
        headers = {}
        result = client._apply_auth(headers)
        
        self.assertIn('Authorization', result)
        self.assertTrue(result['Authorization'].startswith('Basic '))

    def test_apply_auth_bearer(self):
        """测试Bearer认证应用"""
        from modules.collection.api_collector.http_client import HTTPClient, AuthType
        
        client = HTTPClient()
        client.set_auth(AuthType.BEARER, token='jwt-token')
        
        headers = {}
        result = client._apply_auth(headers)
        
        self.assertIn('Authorization', result)
        self.assertEqual(result['Authorization'], 'Bearer jwt-token')

    def test_apply_auth_api_key(self):
        """测试API Key认证应用"""
        from modules.collection.api_collector.http_client import HTTPClient, AuthType
        
        client = HTTPClient()
        client.set_auth(AuthType.API_KEY, key='my-key', header='X-API-Key')
        
        headers = {}
        result = client._apply_auth(headers)
        
        self.assertEqual(result['X-API-Key'], 'my-key')

    def test_health_check_success(self):
        """测试健康检查成功"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient(base_url='https://api.example.com')
        # 不实际发起请求，只测试方法存在
        self.assertTrue(hasattr(client, 'health_check'))
        self.assertTrue(callable(client.health_check))

    def test_close_method(self):
        """测试close方法"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient()
        # close方法存在且可调用
        self.assertTrue(hasattr(client, 'close'))
        client.close()  # 不应该抛出异常


class TestAsyncHTTPClient(unittest.TestCase):
    """测试AsyncHTTPClient异步客户端"""

    def test_async_client_initialization(self):
        """测试异步客户端初始化"""
        from modules.collection.api_collector.http_client import AsyncHTTPClient
        
        client = AsyncHTTPClient(
            base_url='https://api.example.com',
            timeout=60,
            max_retries=5
        )
        
        self.assertEqual(client.base_url, 'https://api.example.com')
        self.assertEqual(client.timeout, 60)
        self.assertEqual(client.max_retries, 5)

    def test_async_client_set_auth(self):
        """测试异步客户端设置认证"""
        from modules.collection.api_collector.http_client import AsyncHTTPClient, AuthType
        
        client = AsyncHTTPClient()
        result = client.set_auth(AuthType.BEARER, token='async-token')
        
        self.assertIs(result, client)
        self.assertEqual(client._auth_type, AuthType.BEARER)

    def test_async_client_build_url(self):
        """测试异步客户端URL构建"""
        from modules.collection.api_collector.http_client import AsyncHTTPClient
        
        client = AsyncHTTPClient(base_url='https://api.example.com')
        url = client._build_url('/api/data', {'filter': 'active'})
        
        self.assertIn('filter=active', url)


class TestWebSocketClient(unittest.TestCase):
    """测试WebSocketClient"""

    def test_websocket_initialization(self):
        """测试WebSocket客户端初始化"""
        from modules.collection.api_collector.http_client import WebSocketClient
        
        client = WebSocketClient(
            url='wss://example.com/ws',
            headers={'Authorization': 'Bearer token'},
            timeout=30
        )
        
        self.assertEqual(client.url, 'wss://example.com/ws')
        self.assertEqual(client.timeout, 30)
        self.assertFalse(client._connected)

    def test_websocket_add_message_handler(self):
        """测试添加消息处理器"""
        from modules.collection.api_collector.http_client import WebSocketClient
        
        client = WebSocketClient(url='wss://example.com/ws')
        
        async def handler(msg):
            pass
        
        client.add_message_handler(handler)
        
        self.assertEqual(len(client._message_handlers), 1)


class TestVendorAPIClient(unittest.TestCase):
    """测试VendorAPIClient厂商API客户端"""

    def test_vendor_configs_exist(self):
        """测试厂商配置存在"""
        from modules.collection.api_collector.http_client import VendorAPIClient
        
        # 验证支持的厂商
        self.assertIn('zabbix', VendorAPIClient.VENDOR_CONFIGS)
        self.assertIn('prometheus', VendorAPIClient.VENDOR_CONFIGS)
        self.assertIn('huawei', VendorAPIClient.VENDOR_CONFIGS)
        self.assertIn('h3c', VendorAPIClient.VENDOR_CONFIGS)
        self.assertIn('vmware', VendorAPIClient.VENDOR_CONFIGS)
        self.assertIn('kubernetes', VendorAPIClient.VENDOR_CONFIGS)

    @patch('modules.collection.api_collector.http_client.HTTPClient')
    def test_vendor_client_initialization(self, mock_http_client):
        """测试厂商客户端初始化"""
        from modules.collection.api_collector.http_client import VendorAPIClient
        
        client = VendorAPIClient(
            vendor='zabbix',
            host='192.168.1.1',
            port=80,
            username='admin',
            password='secret'
        )
        
        self.assertEqual(client.vendor, 'zabbix')
        self.assertEqual(client.host, '192.168.1.1')
        self.assertIsNotNone(client.http_client)

    def test_vendor_client_zabbix_config(self):
        """测试Zabbix配置"""
        from modules.collection.api_collector.http_client import VendorAPIClient
        
        client = VendorAPIClient(vendor='zabbix', host='192.168.1.1')
        config = client.config
        
        self.assertEqual(config['auth_type'].value, 'none')
        self.assertIn('zabbix', config['base_url'])

    def test_vendor_client_huawei_config(self):
        """测试华为云配置"""
        from modules.collection.api_collector.http_client import VendorAPIClient
        
        client = VendorAPIClient(vendor='huawei', host='iam.cn-north-4.myhuaweicloud.com')
        config = client.config
        
        # Huawei uses OAUTH2 auth type
        self.assertEqual(config['auth_type'].value, 'oauth2')

    @patch('modules.collection.api_collector.http_client.HTTPClient')
    def test_vendor_client_h3c_config(self, mock_http_client):
        """测试H3C配置"""
        from modules.collection.api_collector.http_client import VendorAPIClient
        
        client = VendorAPIClient(vendor='h3c', host='192.168.1.1', port=8080)
        config = client.config
        
        self.assertEqual(config['auth_type'].value, 'basic')

    @patch('modules.collection.api_collector.http_client.HTTPClient')
    def test_vendor_client_vmware_config(self, mock_http_client):
        """测试VMware配置"""
        from modules.collection.api_collector.http_client import VendorAPIClient
        
        client = VendorAPIClient(vendor='vmware', host='vcenter.example.com')
        config = client.config
        
        self.assertEqual(config['auth_type'].value, 'basic')
        self.assertIn('/rest', config['base_url'])

    def test_vendor_client_kubernetes_config(self):
        """测试Kubernetes配置"""
        from modules.collection.api_collector.http_client import VendorAPIClient
        
        client = VendorAPIClient(vendor='kubernetes', host='192.168.1.1', port=6443)
        config = client.config
        
        # Kubernetes uses BEARER auth type
        self.assertEqual(config['auth_type'].value, 'bearer')


class TestHTTPClientRetry(unittest.TestCase):
    """测试HTTP客户端重试机制"""

    @patch('modules.collection.api_collector.http_client.urlopen')
    def test_retry_on_failure(self, mock_urlopen):
        """测试失败时重试"""
        from modules.collection.api_collector.http_client import HTTPClient
        from urllib.error import URLError
        
        # 第一次失败，第二次成功
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = json.dumps({'success': True}).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        
        mock_urlopen.side_effect = [
            URLError('Connection refused'),
            mock_response
        ]
        
        client = HTTPClient(base_url='https://api.example.com', max_retries=3)
        result = client.get('/test')
        
        self.assertEqual(result['status_code'], 200)
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch('modules.collection.api_collector.http_client.urlopen')
    def test_max_retries_exceeded(self, mock_urlopen):
        """测试超过最大重试次数"""
        from modules.collection.api_collector.http_client import HTTPClient
        from urllib.error import URLError
        
        mock_urlopen.side_effect = URLError('Connection refused')
        
        client = HTTPClient(base_url='https://api.example.com', max_retries=3, retry_delay=0.01)
        
        try:
            client.get('/test')
        except URLError:
            pass
        
        # 应该重试3次
        self.assertEqual(mock_urlopen.call_count, 3)


if __name__ == '__main__':
    unittest.main()
