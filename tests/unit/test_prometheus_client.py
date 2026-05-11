"""
Prometheus客户端单元测试
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json


class TestPrometheusClient(unittest.TestCase):
    """Prometheus客户端测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        client = PrometheusClient(
            url='http://test:9090',
            timeout=60
        )
        
        self.assertEqual(client.url, 'http://test:9090')
        self.assertEqual(client.timeout, 60)
        self.assertEqual(client._api_url, 'http://test:9090/api/v1')
    
    @patch('urllib.request.urlopen')
    def test_query(self, mock_urlopen):
        """测试即时查询"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {
                        'metric': {'job': 'test', 'instance': 'localhost:9100'},
                        'value': [1234567890.123, '1.0']
                    }
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        result = client.query('up{job="test"}')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['data']['result']), 1)
    
    @patch('urllib.request.urlopen')
    def test_query_range(self, mock_urlopen):
        """测试范围查询"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'resultType': 'matrix',
                'result': [
                    {
                        'metric': {'job': 'test'},
                        'values': [
                            [1234567890.0, '100'],
                            [1234567900.0, '95']
                        ]
                    }
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        end = datetime.now()
        start = end - timedelta(hours=1)
        
        result = client.query_range(
            'up',
            start=start,
            end=end,
            step='1m'
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data']['resultType'], 'matrix')
    
    @patch('urllib.request.urlopen')
    def test_get_all_metrics(self, mock_urlopen):
        """测试获取所有指标"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': ['up', 'process_cpu_seconds_total', 'node_memory_MemTotal_bytes']
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        metrics = client.get_all_metrics()
        
        self.assertEqual(len(metrics), 3)
        self.assertIn('up', metrics)
    
    @patch('urllib.request.urlopen')
    def test_targets(self, mock_urlopen):
        """测试获取Targets"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'activeTargets': [
                    {
                        'job': 'node',
                        'instance': 'localhost:9100',
                        'health': 'up',
                        'lastError': ''
                    }
                ],
                'droppedTargets': []
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        result = client.targets()
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['data']['activeTargets']), 1)
    
    @patch('urllib.request.urlopen')
    def test_label_values(self, mock_urlopen):
        """测试获取标签值"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': ['prometheus', 'node', 'alertmanager']
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        values = client.label_values('job')
        
        self.assertEqual(len(values), 3)
        self.assertIn('prometheus', values)
    
    @patch('urllib.request.urlopen')
    def test_rules(self, mock_urlopen):
        """测试获取规则"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'groups': [
                    {
                        'name': 'node_rules',
                        'file': 'rules.yml',
                        'rules': [
                            {'name': 'HighMemory', 'type': 'alerting'}
                        ]
                    }
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        result = client.rules()
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['data']['groups']), 1)
    
    @patch('urllib.request.urlopen')
    def test_series(self, mock_urlopen):
        """测试查询序列"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': [
                {'__name__': 'up', 'job': 'node', 'instance': 'localhost:9100'}
            ]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        result = client.series(['up{job="node"}'])
        
        self.assertEqual(len(result), 1)
        self.assertIn('__name__', result[0])


class TestPrometheusHighLevelAPI(unittest.TestCase):
    """Prometheus高级API测试"""
    
    @patch('urllib.request.urlopen')
    def test_get_metric_values(self, mock_urlopen):
        """测试获取指标值"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {
                        'metric': {'job': 'test'},
                        'value': [1234567890.0, '100']
                    }
                ]
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = PrometheusClient()
        
        values = client.get_metric_values(
            'up',
            labels={'job': 'test'}
        )
        
        self.assertEqual(len(values), 1)
    
    def test_parse_results(self):
        """测试结果解析"""
        from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        client = PrometheusClient()
        
        # 测试即时查询解析
        instant_result = {
            'status': 'success',
            'data': {
                'resultType': 'vector',
                'result': [
                    {'metric': {'job': 'test'}, 'value': [1234567890.0, '100']}
                ]
            }
        }
        
        parsed = client._parse_instant_result(instant_result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['metric']['job'], 'test')
        
        # 测试范围查询解析
        range_result = {
            'status': 'success',
            'data': {
                'resultType': 'matrix',
                'result': [
                    {'metric': {'job': 'test'}, 'values': [[1234567890.0, '100']]}
                ]
            }
        }
        
        parsed = client._parse_range_result(range_result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(len(parsed[0]['values']), 1)


class TestPrometheusAPIError(unittest.TestCase):
    """Prometheus API错误测试"""
    
    def test_error_exception(self):
        """测试异常类"""
        from modules.collection.api_collector.prometheus_client import PrometheusAPIError
        
        error = PrometheusAPIError(
            type_='bad_data',
            message='invalid query'
        )
        
        self.assertEqual(error.type, 'bad_data')
        self.assertEqual(error.message, 'invalid query')
        self.assertIn('bad_data', str(error))


if __name__ == '__main__':
    unittest.main()
