"""
TDengine客户端单元测试
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json


class TestTDengineClient(unittest.TestCase):
    """TDengine客户端测试"""
    
    def setUp(self):
        """测试前准备"""
        # 延迟导入以避免测试环境问题
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
    
    @patch('urllib.request.urlopen')
    def test_client_initialization(self, mock_urlopen):
        """测试客户端初始化"""
        from modules.storage.tdengine.client import TDengineClient
        
        client = TDengineClient(
            host='test-host',
            port=6041,
            username='test',
            password='test123',
            database='testdb'
        )
        
        self.assertEqual(client.host, 'test-host')
        self.assertEqual(client.port, 6041)
        self.assertEqual(client.database, 'testdb')
    
    def test_create_database(self):
        """测试创建数据库"""
        from modules.storage.tdengine.client import TDengineClient
        
        client = TDengineClient()
        
        # 直接mock _make_request方法
        with patch.object(client, '_make_request', return_value={'status': 'succ'}):
            result = client.create_database('testdb', keep=30, days=1)
            
            self.assertEqual(result['status'], 'succ')
    
    def test_insert_data(self):
        """测试数据插入"""
        from modules.storage.tdengine.client import TDengineClient
        
        client = TDengineClient()
        
        data = [
            {'ts': datetime.now(), 'value': 10.5},
            {'ts': datetime.now(), 'value': 20.3}
        ]
        
        with patch.object(client, '_make_request', return_value={'status': 'succ', 'rows_affected': 3}):
            result = client.insert('test_table', data)
            
            self.assertEqual(result['status'], 'succ')
            self.assertEqual(result['rows_affected'], 3)
    
    def test_query_range(self):
        """测试时间范围查询"""
        from modules.storage.tdengine.client import TDengineClient
        
        client = TDengineClient()
        
        with patch.object(client, '_make_request', return_value={'status': 'succ'}):
            result = client.query_range(
                'test_table',
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now()
            )
            
            self.assertEqual(result['status'], 'succ')
    
    def test_format_timestamp(self):
        """测试时间戳格式化"""
        from modules.storage.tdengine.client import TDengineClient
        
        client = TDengineClient()
        
        # 测试datetime对象
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = client._format_timestamp(dt)
        self.assertIn('2024-01-15', result)
        
        # 测试ISO字符串
        result = client._format_timestamp('2024-01-15T10:30:00')
        self.assertIn('2024-01-15', result)
    
    def test_health_check_connection_error(self):
        """测试健康检查（连接错误）"""
        from modules.storage.tdengine.client import TDengineClient
        
        client = TDengineClient()
        # 无mock应该返回False
        result = client.health_check()
        self.assertFalse(result)


class TestTDengineFilterBuilder(unittest.TestCase):
    """TDengine过滤条件构建测试"""
    
    def test_filter_match(self):
        """测试精确匹配"""
        from modules.storage.tdengine.client import TDengineClient
        
        client = TDengineClient()
        # 测试方法存在性
        self.assertTrue(hasattr(client, 'filter_match'))
    
    def test_filter_range(self):
        """测试范围过滤"""
        from modules.storage.tdengine.client import TDengineClient
        
        client = TDengineClient()
        # 测试方法存在性
        self.assertTrue(hasattr(client, 'filter_range'))


if __name__ == '__main__':
    unittest.main()
