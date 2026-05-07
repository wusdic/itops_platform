# -*- coding: utf-8 -*-
"""
存储客户端单元测试 - 专注于抽象基类和辅助方法
测试未在专门测试文件中覆盖的部分：
- StorageClient抽象基类接口
- _MemoryLock内存锁实现
- _MemoryPipeline内存管道实现
- 各存储客户端的扩展/辅助方法
"""

import unittest
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


class TestStorageClientAbstract(unittest.TestCase):
    """测试StorageClient抽象基类接口"""

    def test_storage_client_is_abc(self):
        """测试StorageClient是抽象基类"""
        from core.storage.client import StorageClient
        
        # 不能直接实例化抽象类
        with self.assertRaises(TypeError):
            StorageClient()

    def test_storage_client_abstract_methods(self):
        """测试抽象方法定义"""
        from core.storage.client import StorageClient
        from abc import ABC
        
        # StorageClient应该继承自ABC
        self.assertTrue(issubclass(StorageClient, ABC))
        
        # 应该有抽象方法
        self.assertTrue(hasattr(StorageClient, 'connect'))
        self.assertTrue(hasattr(StorageClient, 'disconnect'))
        self.assertTrue(hasattr(StorageClient, 'health_check'))

    def test_storage_client_concrete_implementations(self):
        """测试具体实现类都继承自StorageClient"""
        from core.storage.client import (
            StorageClient, RedisClient, TDengineClient, 
            InfluxDBClient, MinIOClient, QdrantClient
        )
        
        # 所有客户端都应该继承自StorageClient
        self.assertTrue(issubclass(RedisClient, StorageClient))
        self.assertTrue(issubclass(TDengineClient, StorageClient))
        self.assertTrue(issubclass(InfluxDBClient, StorageClient))
        self.assertTrue(issubclass(MinIOClient, StorageClient))
        self.assertTrue(issubclass(QdrantClient, StorageClient))

    def test_storage_client_base_properties(self):
        """测试StorageClient基类属性"""
        from core.storage.client import RedisClient
        
        client = RedisClient()
        # 初始状态未连接
        self.assertFalse(client._connected)
        self.assertIsInstance(client._config, dict)


class TestMemoryLock(unittest.TestCase):
    """测试_MemoryLock内存分布式锁实现"""

    def test_memory_lock_initialization(self):
        """测试锁初始化"""
        from core.storage.client import _MemoryLock
        
        lock = _MemoryLock("test_lock")
        self.assertEqual(lock.name, "test_lock")
        self.assertFalse(lock._acquired)

    def test_memory_lock_acquire(self):
        """测试获取锁"""
        from core.storage.client import _MemoryLock
        
        lock = _MemoryLock("test_lock")
        result = lock.acquire()
        
        self.assertTrue(result)
        self.assertTrue(lock._acquired)

    def test_memory_lock_acquire_with_parameters(self):
        """测试带参数的获取锁"""
        from core.storage.client import _MemoryLock
        
        lock = _MemoryLock("test_lock")
        
        # blocking=True
        result = lock.acquire(blocking=True, timeout=10)
        self.assertTrue(result)
        
        # blocking=False
        lock2 = _MemoryLock("test_lock2")
        result = lock2.acquire(blocking=False)
        self.assertTrue(result)

    def test_memory_lock_release(self):
        """测试释放锁"""
        from core.storage.client import _MemoryLock
        
        lock = _MemoryLock("test_lock")
        lock.acquire()
        self.assertTrue(lock._acquired)
        
        lock.release()
        self.assertFalse(lock._acquired)

    def test_memory_lock_context_manager(self):
        """测试作为上下文管理器使用"""
        from core.storage.client import _MemoryLock
        
        lock = _MemoryLock("test_lock")
        
        with lock:
            self.assertTrue(lock._acquired)
        
        # 退出后应该释放
        self.assertFalse(lock._acquired)

    def test_memory_lock_context_manager_nested(self):
        """测试嵌套上下文管理器"""
        from core.storage.client import _MemoryLock
        
        lock1 = _MemoryLock("lock1")
        lock2 = _MemoryLock("lock2")
        
        with lock1:
            self.assertTrue(lock1._acquired)
            with lock2:
                self.assertTrue(lock2._acquired)
            self.assertFalse(lock2._acquired)
        self.assertFalse(lock1._acquired)

    def test_memory_lock_reentrant(self):
        """测试锁的可重入性 - 内存锁总是返回True所以支持重入"""
        from core.storage.client import _MemoryLock
        
        lock = _MemoryLock("test_lock")
        
        # 第一次获取
        lock.acquire()
        self.assertTrue(lock._acquired)
        
        # 第二次获取（模拟重入）
        lock.acquire()
        self.assertTrue(lock._acquired)


class TestMemoryPipeline(unittest.TestCase):
    """测试_MemoryPipeline内存管道实现"""

    def test_memory_pipeline_initialization(self):
        """测试管道初始化"""
        from core.storage.client import _MemoryPipeline
        
        store = {}
        pipeline = _MemoryPipeline(store)
        
        self.assertIs(pipeline.store, store)
        self.assertEqual(pipeline._commands, [])

    def test_memory_pipeline_get_command(self):
        """测试GET命令"""
        from core.storage.client import _MemoryPipeline
        
        store = {"key1": "value1"}
        pipeline = _MemoryPipeline(store)
        
        result = pipeline.get("key1")
        
        # 应该返回self以支持链式调用
        self.assertIs(result, pipeline)
        self.assertEqual(len(pipeline._commands), 1)
        self.assertEqual(pipeline._commands[0], ('get', 'key1'))

    def test_memory_pipeline_set_command(self):
        """测试SET命令"""
        from core.storage.client import _MemoryPipeline
        
        store = {}
        pipeline = _MemoryPipeline(store)
        
        result = pipeline.set("key1", "value1")
        
        self.assertIs(result, pipeline)
        self.assertEqual(len(pipeline._commands), 1)
        self.assertEqual(pipeline._commands[0], ('set', 'key1', 'value1'))

    def test_memory_pipeline_chain_commands(self):
        """测试链式命令"""
        from core.storage.client import _MemoryPipeline
        
        store = {}
        pipeline = _MemoryPipeline(store)
        
        pipeline.get("key1").set("key2", "value2").get("key3")
        
        self.assertEqual(len(pipeline._commands), 3)
        self.assertEqual(pipeline._commands[0], ('get', 'key1'))
        self.assertEqual(pipeline._commands[1], ('set', 'key2', 'value2'))
        self.assertEqual(pipeline._commands[2], ('get', 'key3'))

    def test_memory_pipeline_execute_get(self):
        """测试执行GET命令"""
        from core.storage.client import _MemoryPipeline
        
        store = {"key1": "value1", "key2": "value2"}
        pipeline = _MemoryPipeline(store)
        
        pipeline.get("key1")
        results = pipeline.execute()
        
        self.assertEqual(results, ["value1"])

    def test_memory_pipeline_execute_set(self):
        """测试执行SET命令"""
        from core.storage.client import _MemoryPipeline
        
        store = {}
        pipeline = _MemoryPipeline(store)
        
        pipeline.set("key1", "value1")
        results = pipeline.execute()
        
        self.assertEqual(results, [True])
        self.assertEqual(store["key1"], "value1")

    def test_memory_pipeline_execute_mixed(self):
        """测试执行混合命令"""
        from core.storage.client import _MemoryPipeline
        
        store = {"existing_key": "existing_value"}
        pipeline = _MemoryPipeline(store)
        
        pipeline.get("existing_key")
        pipeline.set("new_key", "new_value")
        pipeline.get("new_key")
        
        results = pipeline.execute()
        
        self.assertEqual(results[0], "existing_value")
        self.assertEqual(results[1], True)
        self.assertEqual(results[2], "new_value")
        self.assertEqual(store["new_key"], "new_value")

    def test_memory_pipeline_execute_empty(self):
        """测试执行空管道"""
        from core.storage.client import _MemoryPipeline
        
        store = {}
        pipeline = _MemoryPipeline(store)
        
        results = pipeline.execute()
        
        self.assertEqual(results, [])

    def test_memory_pipeline_multiple_execute(self):
        """测试多次执行"""
        from core.storage.client import _MemoryPipeline
        
        store = {}
        pipeline = _MemoryPipeline(store)
        
        pipeline.get("key1")
        results1 = pipeline.execute()
        results2 = pipeline.execute()  # 第二次执行应该再次执行同样命令
        
        # 命令没有被清空，所以两次执行结果相同
        self.assertEqual(results1, results2)


class TestRedisClientExtensions(unittest.TestCase):
    """测试RedisClient扩展方法"""

    def setUp(self):
        """测试前准备"""
        from core.storage.client import RedisClient
        # 使用内存后备模式以便隔离测试
        self.client = RedisClient()
        self.client._use_memory_fallback = True
        self.client._connected = True

    def test_set_json(self):
        """测试JSON序列化存储"""
        data = {"name": "test", "items": [1, 2, 3], "nested": {"key": "value"}}
        
        result = self.client.set_json("json_key", data)
        
        self.assertTrue(result)
        stored = self.client._memory_store["json_key"]
        self.assertEqual(json.loads(stored), data)

    def test_set_json_with_ttl(self):
        """测试带TTL的JSON存储"""
        data = {"key": "value"}
        
        result = self.client.set_json("json_key", data, ttl=60)
        
        self.assertTrue(result)

    def test_get_json(self):
        """测试JSON反序列化读取"""
        # 先存储JSON数据
        self.client._memory_store["json_key"] = json.dumps({"name": "test"})
        
        result = self.client.get_json("json_key")
        
        self.assertEqual(result, {"name": "test"})

    def test_get_json_invalid_json(self):
        """测试读取无效JSON"""
        self.client._memory_store["invalid_key"] = "not valid json {"
        
        result = self.client.get_json("invalid_key")
        
        self.assertIsNone(result)

    def test_get_json_nonexistent(self):
        """测试读取不存在的键"""
        result = self.client.get_json("nonexistent")
        
        self.assertIsNone(result)

    def test_lock_returns_memory_lock(self):
        """测试在内存后备模式下返回_MemoryLock"""
        lock = self.client.lock("test_lock")
        
        from core.storage.client import _MemoryLock
        self.assertIsInstance(lock, _MemoryLock)
        self.assertEqual(lock.name, "test_lock")

    def test_lock_with_timeout(self):
        """测试带超时参数的锁"""
        lock = self.client.lock("test_lock", timeout=30)
        
        self.assertEqual(lock.name, "test_lock")

    def test_pipeline_returns_memory_pipeline(self):
        """测试在内存后备模式下返回_MemoryPipeline"""
        pipeline = self.client.pipeline()
        
        from core.storage.client import _MemoryPipeline
        self.assertIsInstance(pipeline, _MemoryPipeline)

    def test_pipeline_execute(self):
        """测试管道执行"""
        self.client.set("key1", "value1")
        
        pipeline = self.client.pipeline()
        pipeline.get("key1")
        results = pipeline.execute()
        
        self.assertEqual(results, ["value1"])

    def test_set_json_unicode(self):
        """测试Unicode字符处理"""
        data = {"name": "中文测试", "emoji": "😀"}
        
        self.client.set_json("unicode_key", data)
        result = self.client.get_json("unicode_key")
        
        self.assertEqual(result, data)


class TestTDengineClientExtensions(unittest.TestCase):
    """测试TDengineClient扩展方法"""

    @patch('requests.post')
    @patch('requests.get')
    def test_execute_raw(self, mock_get, mock_post):
        """测试执行原始SQL"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "succ"}'
        mock_post.return_value = mock_response
        
        client = TDengineClient()
        result = client.execute_raw("SELECT * FROM test")
        
        self.assertEqual(result, '{"status": "succ"}')
        mock_post.assert_called_once()

    @patch('requests.post')
    @patch('requests.get')
    def test_execute_raw_error(self, mock_get, mock_post):
        """测试execute_raw异常处理"""
        from core.storage.client import TDengineClient
        
        mock_post.side_effect = Exception("Network error")
        
        client = TDengineClient()
        result = client.execute_raw("SELECT * FROM test")
        
        # 应该返回错误JSON
        self.assertIn("error", result)

    @patch('requests.post')
    @patch('requests.get')
    def test_create_database(self, mock_get, mock_post):
        """测试创建数据库"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "succ"}
        mock_post.return_value = mock_response
        
        client = TDengineClient(database="testdb")
        client.create_database()
        
        # 验证调用
        mock_post.assert_called()
        call_args = mock_post.call_args
        self.assertIn("CREATE DATABASE", call_args[1]["data"])

    @patch('requests.post')
    @patch('requests.get')
    def test_create_database_custom(self, mock_get, mock_post):
        """测试创建自定义名称的数据库"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "succ"}
        mock_post.return_value = mock_response
        
        client = TDengineClient()
        client.create_database("custom_db")
        
        call_args = mock_post.call_args
        self.assertIn("custom_db", call_args[1]["data"])

    @patch('requests.post')
    @patch('requests.get')
    def test_create_table(self, mock_get, mock_post):
        """测试创建超级表"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "succ"}
        mock_post.return_value = mock_response
        
        client = TDengineClient()
        client.create_table(
            table_name="test_table",
            tags=["device_id INT", "location VARCHAR(100)"],
            columns=["ts TIMESTAMP", "temperature FLOAT"]
        )
        
        call_args = mock_post.call_args
        sql = call_args[1]["data"]
        self.assertIn("CREATE TABLE", sql)
        self.assertIn("test_table", sql)
        self.assertIn("TAGS", sql)

    @patch('requests.post')
    @patch('requests.get')
    def test_insert(self, mock_get, mock_post):
        """测试数据插入"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "succ", "rows_affected": 1}
        mock_post.return_value = mock_response
        
        client = TDengineClient()
        data = [{"temperature": 25.5, "humidity": 60}]
        client.insert("sensor_data", data)
        
        mock_post.assert_called()

    @patch('requests.post')
    @patch('requests.get')
    def test_insert_empty_data(self, mock_get, mock_post):
        """测试插入空数据"""
        from core.storage.client import TDengineClient
        
        client = TDengineClient()
        client.insert("sensor_data", [])
        
        # 不应该调用post
        mock_post.assert_not_called()

    @patch('requests.post')
    @patch('requests.get')
    def test_insert_multiple_records(self, mock_get, mock_post):
        """测试插入多条记录"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "succ"}
        mock_post.return_value = mock_response
        
        client = TDengineClient()
        data = [
            {"temperature": 25.5},
            {"temperature": 26.0},
            {"temperature": 24.5}
        ]
        client.insert("sensor_data", data)
        
        # 应该为每条记录调用一次
        self.assertEqual(mock_post.call_count, 3)

    @patch('requests.post')
    @patch('requests.get')
    def test_last_row(self, mock_get, mock_post):
        """测试获取最后一条记录"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "succ",
            "column_names": ["ts", "temperature"],
            "data": [[1234567890, 25.5]]
        }
        mock_post.return_value = mock_response
        
        client = TDengineClient()
        result = client.last_row("sensor_data")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["temperature"], 25.5)

    @patch('requests.post')
    @patch('requests.get')
    def test_last_row_with_fields(self, mock_get, mock_post):
        """测试获取指定字段的最后一条记录"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "succ",
            "column_names": ["ts", "temperature"],
            "data": [[1234567890, 25.5]]
        }
        mock_post.return_value = mock_response
        
        client = TDengineClient()
        result = client.last_row("sensor_data", fields=["temperature"])
        
        self.assertIsNotNone(result)
        # 验证使用了LAST()函数
        call_args = mock_post.call_args
        self.assertIn("LAST(temperature)", call_args[1]["data"])

    @patch('requests.post')
    @patch('requests.get')
    def test_last_row_empty(self, mock_get, mock_post):
        """测试表为空时last_row返回None"""
        from core.storage.client import TDengineClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "succ",
            "column_names": [],
            "data": []
        }
        mock_post.return_value = mock_response
        
        client = TDengineClient()
        result = client.last_row("sensor_data")
        
        self.assertIsNone(result)


class TestInfluxDBClientExtensions(unittest.TestCase):
    """测试InfluxDBClient扩展方法"""

    def test_write_point_creates_point(self):
        """测试write_point方法存在且参数正确"""
        from core.storage.client import InfluxDBClient
        
        client = InfluxDBClient()
        # InfluxDBClient.write is the actual method (write_point alias)
        self.assertTrue(hasattr(client, 'write'))

    def test_influxdb_client_has_query_method(self):
        """测试InfluxDBClient有query方法"""
        from core.storage.client import InfluxDBClient
        
        client = InfluxDBClient()
        self.assertTrue(hasattr(client, 'query'))
        self.assertTrue(callable(client.query))

    def test_influxdb_client_has_write_method(self):
        """测试InfluxDBClient有write方法"""
        from core.storage.client import InfluxDBClient
        
        client = InfluxDBClient()
        self.assertTrue(hasattr(client, 'write'))
        self.assertTrue(callable(client.write))

    def test_influxdb_client_initialization(self):
        """测试InfluxDBClient初始化参数"""
        from core.storage.client import InfluxDBClient
        
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

    def test_influxdb_client_write_method_signature(self):
        """测试write方法签名"""
        from core.storage.client import InfluxDBClient
        import inspect
        
        client = InfluxDBClient()
        sig = inspect.signature(client.write)
        params = list(sig.parameters.keys())
        
        # write(measurement, tags, fields, time=None)
        self.assertIn('measurement', params)
        self.assertIn('tags', params)
        self.assertIn('fields', params)
        self.assertIn('time', params)

    def test_influxdb_client_query_method_signature(self):
        """测试query方法签名"""
        from core.storage.client import InfluxDBClient
        import inspect
        
        client = InfluxDBClient()
        sig = inspect.signature(client.query)
        params = list(sig.parameters.keys())
        
        # query(query)
        self.assertIn('query', params)


class TestStorageManagerSingleton(unittest.TestCase):
    """测试StorageManager单例模式"""

    def test_storage_manager_is_singleton(self):
        """测试StorageManager是单例"""
        from core.storage.client import StorageManager, get_storage_manager
        
        # 重置单例以进行测试
        StorageManager._instance = None
        
        manager1 = StorageManager()
        manager2 = StorageManager()
        
        self.assertIs(manager1, manager2)

    def test_get_storage_manager_function(self):
        """测试快捷函数"""
        from core.storage.client import StorageManager, get_storage_manager
        
        # 重置单例
        StorageManager._instance = None
        
        manager = get_storage_manager()
        
        self.assertIsInstance(manager, StorageManager)

    def test_storage_manager_configure(self):
        """测试配置方法"""
        from core.storage.client import StorageManager
        
        StorageManager._instance = None
        manager = StorageManager()
        
        config = {"redis": {"host": "localhost"}}
        manager.configure(config)
        
        self.assertEqual(manager._config, config)


if __name__ == '__main__':
    unittest.main()
