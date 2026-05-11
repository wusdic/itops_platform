"""
InfluxDB客户端单元测试
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json


class TestInfluxDBClient(unittest.TestCase):
    """InfluxDB客户端测试"""
    
    @patch('urllib.request.urlopen')
    def test_client_initialization(self, mock_urlopen):
        """测试客户端初始化"""
        from modules.storage.influxdb.client import InfluxDBClient
        
        client = InfluxDBClient(
            url='http://test:8086',
            token='test-token',
            org='testorg',
            bucket='testbucket'
        )
        
        self.assertEqual(client.url, 'http://test:8086')
        self.assertEqual(client.token, 'test-token')
        self.assertEqual(client.org, 'testorg')
        self.assertEqual(client.bucket, 'testbucket')
    
    @patch('urllib.request.urlopen')
    def test_write_line_protocol(self, mock_urlopen):
        """测试行协议写入"""
        from modules.storage.influxdb.client import InfluxDBClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = InfluxDBClient()
        
        result = client.write_line_protocol(
            measurement='cpu',
            tags={'host': 'server1'},
            fields={'usage': 45.5}
        )
        
        self.assertTrue(result)
    
    def test_format_field_string(self):
        """测试字符串字段格式化"""
        from modules.storage.influxdb.client import InfluxDBClient
        
        client = InfluxDBClient()
        
        # 测试带特殊字符的字符串
        result = client._format_field('msg', 'hello, world')
        self.assertEqual(result, 'msg="hello, world"')
    
    def test_format_field_number(self):
        """测试数字字段格式化"""
        from modules.storage.influxdb.client import InfluxDBClient
        
        client = InfluxDBClient()
        
        result = client._format_field('value', 42.5)
        self.assertEqual(result, 'value=42.5')
    
    def test_format_time_datetime(self):
        """测试datetime格式化"""
        from modules.storage.influxdb.client import InfluxDBClient
        
        client = InfluxDBClient()
        
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = client._format_time(dt)
        
        self.assertEqual(result, '2024-01-15T10:30:00Z')
    
    def test_format_time_relative(self):
        """测试相对时间格式化"""
        from modules.storage.influxdb.client import InfluxDBClient
        
        client = InfluxDBClient()
        
        # 负数表示过去时间
        result = client._format_time(-3600)
        self.assertEqual(result, '3600s')
        
        # 字符串
        result = client._format_time('now()')
        self.assertEqual(result, 'now()')


class TestInfluxDBQuery(unittest.TestCase):
    """InfluxDB查询测试"""
    
    @patch('urllib.request.urlopen')
    def test_query_flux(self, mock_urlopen):
        """测试Flux查询"""
        from modules.storage.influxdb.client import InfluxDBClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps([
            {
                'table': 0,
                'records': [
                    {'_time': '2024-01-15T10:30:00Z', '_value': 45.5, '_field': 'cpu'}
                ]
            }
        ]).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = InfluxDBClient()
        
        result = client.query_flux('from(bucket: "test") |> range(start: -1h)')
        
        self.assertIsInstance(result, list)


if __name__ == '__main__':
    unittest.main()
