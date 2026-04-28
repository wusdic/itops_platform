"""
Qdrant向量数据库客户端单元测试
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json


class TestQdrantClient(unittest.TestCase):
    """Qdrant客户端测试"""
    
    @patch('urllib.request.urlopen')
    def test_client_initialization(self, mock_urlopen):
        """测试客户端初始化"""
        from modules.storage.qdrant.client import QdrantClient
        
        client = QdrantClient(
            host='test-host',
            port=6333,
            api_key='test-key',
            collection_prefix='test_'
        )
        
        self.assertEqual(client.host, 'test-host')
        self.assertEqual(client.port, 6333)
        self.assertEqual(client.api_key, 'test-key')
        self.assertEqual(client.prefix, 'test_')
    
    @patch('urllib.request.urlopen')
    def test_create_collection(self, mock_urlopen):
        """测试创建集合"""
        from modules.storage.qdrant.client import QdrantClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'result': True,
            'status': 'ok'
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = QdrantClient()
        result = client.create_collection('test', vector_size=128, distance='Cosine')
        
        self.assertTrue(result.get('result') or result.get('status') == 'ok')
    
    @patch('urllib.request.urlopen')
    def test_upsert_points(self, mock_urlopen):
        """测试插入向量"""
        from modules.storage.qdrant.client import QdrantClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'result': {
                'operation_id': 1,
                'status': 'acknowledged'
            }
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = QdrantClient()
        
        points = [
            {
                'id': 'test-1',
                'vector': [0.1] * 128,
                'payload': {'name': 'test1'}
            }
        ]
        
        result = client.upsert('test_collection', points)
        
        self.assertIn('result', result)
    
    @patch('urllib.request.urlopen')
    def test_search(self, mock_urlopen):
        """测试向量搜索"""
        from modules.storage.qdrant.client import QdrantClient
        
        # Mock响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'result': [
                {'id': 'test-1', 'score': 0.95, 'payload': {'name': 'test1'}}
            ]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = QdrantClient()
        
        query_vector = [0.1] * 128
        results = client.search('test_collection', query_vector, limit=5)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['score'], 0.95)


class TestQdrantFilter(unittest.TestCase):
    """Qdrant过滤条件测试"""
    
    def test_filter_match(self):
        """测试精确匹配"""
        from modules.storage.qdrant.client import QdrantClient
        
        result = QdrantClient.filter_match('device_type', 'server')
        
        self.assertEqual(result['key'], 'device_type')
        self.assertEqual(result['match']['value'], 'server')
    
    def test_filter_range(self):
        """测试范围过滤"""
        from modules.storage.qdrant.client import QdrantClient
        
        result = QdrantClient.filter_range('age', gte=18, lte=65)
        
        self.assertEqual(result['key'], 'age')
        self.assertEqual(result['range']['gte'], 18)
        self.assertEqual(result['range']['lte'], 65)
    
    def test_filter_must(self):
        """测试Must条件"""
        from modules.storage.qdrant.client import QdrantClient
        
        cond1 = QdrantClient.filter_match('type', 'server')
        cond2 = QdrantClient.filter_range('age', gte=18)
        
        result = QdrantClient.filter_must(cond1, cond2)
        
        self.assertIn('must', result)
        self.assertEqual(len(result['must']), 2)
    
    def test_filter_should(self):
        """测试Should条件"""
        from modules.storage.qdrant.client import QdrantClient
        
        cond1 = QdrantClient.filter_match('type', 'server')
        cond2 = QdrantClient.filter_match('type', 'router')
        
        result = QdrantClient.filter_should(cond1, cond2)
        
        self.assertIn('should', result)
        self.assertEqual(len(result['should']), 2)
    
    def test_filter_must_not(self):
        """测试Must Not条件"""
        from modules.storage.qdrant.client import QdrantClient
        
        cond = QdrantClient.filter_match('status', 'deleted')
        result = QdrantClient.filter_must_not(cond)
        
        self.assertIn('must_not', result)


if __name__ == '__main__':
    unittest.main()
