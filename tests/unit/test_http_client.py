"""
HTTP客户端单元测试
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json


class TestHTTPClient(unittest.TestCase):
    """HTTP客户端测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient(
            base_url='https://api.example.com',
            timeout=30,
            max_retries=3
        )
        
        self.assertEqual(client.base_url, 'https://api.example.com')
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.max_retries, 3)
    
    def test_build_url(self):
        """测试URL构建"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient(base_url='https://api.example.com')
        
        # 简单端点
        url = client._build_url('/users', None)
        self.assertEqual(url, 'https://api.example.com/users')
        
        # 带参数
        url = client._build_url('/users', {'page': 1, 'limit': 10})
        self.assertIn('page=1', url)
        self.assertIn('limit=10', url)
    
    def test_add_interceptors(self):
        """测试拦截器"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        client = HTTPClient()
        
        def mock_interceptor(request):
            return request
        
        client.add_request_interceptor(mock_interceptor)
        client.add_response_interceptor(mock_interceptor)
        
        self.assertEqual(len(client._request_interceptors), 1)
        self.assertEqual(len(client._response_interceptors), 1)


class TestHTTPClientRequest(unittest.TestCase):
    """HTTP请求测试"""
    
    @patch('urllib.request.urlopen')
    def test_get_request(self, mock_urlopen):
        """测试GET请求"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = json.dumps({'data': 'test'}).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = HTTPClient(base_url='https://api.example.com')
        
        result = client.get('/test')
        
        self.assertEqual(result['status_code'], 200)
        self.assertEqual(result['data']['data'], 'test')
    
    @patch('urllib.request.urlopen')
    def test_post_request(self, mock_urlopen):
        """测试POST请求"""
        from modules.collection.api_collector.http_client import HTTPClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.status = 201
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = json.dumps({'id': 1}).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = HTTPClient(base_url='https://api.example.com')
        
        result = client.post('/users', json_data={'name': 'Alice'})
        
        self.assertEqual(result['status_code'], 201)
        self.assertEqual(result['data']['id'], 1)
    
    @patch('urllib.request.urlopen')
    def test_authentication(self, mock_urlopen):
        """测试认证"""
        from modules.collection.api_collector.http_client import HTTPClient
        import base64
        
        # Mock响应
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = json.dumps({'success': True}).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = HTTPClient(base_url='https://api.example.com')
        
        # Basic认证
        client.get('/protected', auth=('user', 'pass'))
        
        # Bearer Token
        client.get('/protected', bearer_token='token123')
        
        # API Key
        client.get('/api', api_key='key123')
    
    @patch('urllib.request.urlopen')
    def test_error_response(self, mock_urlopen):
        """测试错误响应"""
        from modules.collection.api_collector.http_client import HTTPClient
        from urllib.error import HTTPError
        
        # Mock HTTPError
        mock_error = HTTPError(
            'https://api.example.com/nonexistent',
            404,
            'Not Found',
            {},
            json.dumps({'error': 'Not found'}).encode()
        )
        mock_urlopen.side_effect = mock_error
        
        client = HTTPClient(base_url='https://api.example.com')
        
        # 捕获错误
        try:
            client.get('/nonexistent')
        except HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == '__main__':
    unittest.main()
