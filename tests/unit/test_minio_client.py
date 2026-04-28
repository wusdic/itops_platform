"""
MinIO客户端单元测试
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestLocalStorageClient(unittest.TestCase):
    """本地存储客户端测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        from modules.storage.minio.client import LocalStorageClient
        
        client = LocalStorageClient(base_path=self.temp_dir)
        
        self.assertTrue(os.path.exists(self.temp_dir))
        self.assertEqual(client.base_path, Path(self.temp_dir))
    
    def test_upload_file(self):
        """测试文件上传"""
        from modules.storage.minio.client import LocalStorageClient
        
        client = LocalStorageClient(base_path=self.temp_dir)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('test content')
            temp_path = f.name
        
        try:
            result = client.upload_file(temp_path, 'test/file.txt')
            
            self.assertEqual(result['object_name'], 'test/file.txt')
            self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'test/file.txt')))
        finally:
            os.unlink(temp_path)
    
    def test_upload_data(self):
        """测试数据上传"""
        from modules.storage.minio.client import LocalStorageClient
        
        client = LocalStorageClient(base_path=self.temp_dir)
        
        data = b'test data content'
        result = client.upload_data(data, 'test/data.bin', metadata={'type': 'binary'})
        
        self.assertEqual(result['object_name'], 'test/data.bin')
        self.assertEqual(result['size'], len(data))
        self.assertIn('etag', result)
    
    def test_download_data(self):
        """测试数据下载"""
        from modules.storage.minio.client import LocalStorageClient
        
        client = LocalStorageClient(base_path=self.temp_dir)
        
        # 先上传
        data = b'test data for download'
        client.upload_data(data, 'test/download.txt')
        
        # 再下载
        downloaded = client.download_data('test/download.txt')
        
        self.assertEqual(downloaded, data)
    
    def test_delete(self):
        """测试删除"""
        from modules.storage.minio.client import LocalStorageClient
        
        client = LocalStorageClient(base_path=self.temp_dir)
        
        # 先上传
        client.upload_data(b'test', 'test/delete.txt')
        self.assertTrue(client.exists('test/delete.txt'))
        
        # 再删除
        result = client.delete('test/delete.txt')
        self.assertTrue(result)
        self.assertFalse(client.exists('test/delete.txt'))
    
    def test_list_objects(self):
        """测试列出对象"""
        from modules.storage.minio.client import LocalStorageClient
        
        client = LocalStorageClient(base_path=self.temp_dir)
        
        # 上传多个文件
        client.upload_data(b'data1', 'prefix/file1.txt')
        client.upload_data(b'data2', 'prefix/file2.txt')
        client.upload_data(b'data3', 'other/file3.txt')
        
        # 列出prefix下的文件
        objects = client.list_objects('prefix/')
        
        self.assertEqual(len(objects), 2)
        names = [o['object_name'] for o in objects]
        self.assertIn('prefix/file1.txt', names)
        self.assertIn('prefix/file2.txt', names)
    
    def test_get_metadata(self):
        """测试获取元数据"""
        from modules.storage.minio.client import LocalStorageClient
        
        client = LocalStorageClient(base_path=self.temp_dir)
        
        # 上传带元数据
        client.upload_data(b'test', 'test/meta.txt', metadata={'key': 'value'})
        
        # 获取元数据
        meta = client.get_metadata('test/meta.txt')
        
        self.assertIn('size', meta)
        self.assertIn('last_modified', meta)
        self.assertIn('metadata', meta)


class TestMinIOClient(unittest.TestCase):
    """MinIO客户端测试"""
    
    @patch('urllib.request.urlopen')
    def test_client_initialization(self, mock_urlopen):
        """测试客户端初始化"""
        from modules.storage.minio.client import MinIOClient
        
        client = MinIOClient(
            endpoint='localhost:9000',
            access_key='test',
            secret_key='test123',
            bucket='testbucket'
        )
        
        self.assertEqual(client.endpoint, 'localhost:9000')
        self.assertEqual(client.access_key, 'test')
        self.assertEqual(client.bucket, 'testbucket')


class TestMinIOOperations(unittest.TestCase):
    """MinIO操作测试（使用本地存储后备）"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_fallback_to_local(self):
        """测试回退到本地存储"""
        from modules.storage.minio.client import MinIOClient
        
        # 创建客户端（不安装minio库时使用本地存储）
        client = MinIOClient.__new__(MinIOClient)
        client._minio_available = False
        client._client = client._LocalStorage__init__(
            MinIOClient._LocalStorageClient.__new__(MinIOClient._LocalStorageClient),
            self.temp_dir
        )
        
        # 测试基本操作
        client._client.upload_data(b'test', 'test.txt')
        data = client._client.download_data('test.txt')
        
        self.assertEqual(data, b'test')


if __name__ == '__main__':
    unittest.main()
