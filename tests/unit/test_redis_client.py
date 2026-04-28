"""
Redis客户端单元测试
"""

import unittest
import time
from datetime import timedelta
from unittest.mock import Mock, patch, MagicMock
import json


class TestRedisClient(unittest.TestCase):
    """Redis客户端测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        from modules.storage.redis_client.client import RedisClient
        
        client = RedisClient(
            host='test-host',
            port=6379,
            password='test123',
            db=1
        )
        
        self.assertEqual(client.host, 'test-host')
        self.assertEqual(client.port, 6379)
        self.assertEqual(client.db, 1)


class TestRedisMemoryStore(unittest.TestCase):
    """Redis内存存储测试（后备实现）"""
    
    def setUp(self):
        """测试前准备"""
        from modules.storage.redis_client.client import RedisClient
        self.client = RedisClient()
    
    def test_string_operations(self):
        """测试字符串操作"""
        # 设置
        result = self.client.set('key1', 'value1')
        self.assertTrue(result)
        
        # 获取
        value = self.client.get('key1')
        self.assertEqual(value, 'value1')
        
        # 不存在
        value = self.client.get('nonexistent')
        self.assertIsNone(value)
    
    def test_string_with_expiry(self):
        """测试带过期时间的字符串"""
        # 设置带过期时间
        self.client.set('expire_key', 'value', ex=10)
        
        # 获取
        value = self.client.get('expire_key')
        self.assertEqual(value, 'value')
        
        # 检查TTL
        ttl = self.client.ttl('expire_key')
        self.assertGreater(ttl, 0)
    
    def test_incr_decr(self):
        """测试递增递减"""
        self.client.set('counter', '0')
        
        # 递增
        result = self.client.incr('counter')
        self.assertEqual(result, 1)
        
        result = self.client.incr('counter', 5)
        self.assertEqual(result, 6)
        
        # 递减
        result = self.client.decr('counter', 2)
        self.assertEqual(result, 4)
    
    def test_hash_operations(self):
        """测试哈希操作"""
        # 设置哈希
        self.client.hset('user:1', mapping={'name': 'Alice', 'email': 'alice@test.com'})
        
        # 获取单个字段
        name = self.client.hget('user:1', 'name')
        self.assertEqual(name, 'Alice')
        
        # 获取所有字段
        data = self.client.hgetall('user:1')
        self.assertEqual(data['name'], 'Alice')
        self.assertEqual(data['email'], 'alice@test.com')
        
        # 字段数量
        length = self.client.hlen('user:1')
        self.assertEqual(length, 2)
        
        # 字段是否存在
        exists = self.client.hexists('user:1', 'name')
        self.assertTrue(exists)
        
        # 递增
        self.client.hset('stats', 'count', '10')
        result = self.client.hincrby('stats', 'count', 5)
        self.assertEqual(result, 15)
    
    def test_list_operations(self):
        """测试列表操作"""
        # 从右侧插入
        self.client.rpush('tasks', 'task1', 'task2')
        self.assertEqual(self.client.llen('tasks'), 2)
        
        # 从左侧插入
        self.client.lpush('tasks', 'task0')
        self.assertEqual(self.client.llen('tasks'), 3)
        
        # 获取范围
        items = self.client.lrange('tasks', 0, -1)
        self.assertEqual(items[0], 'task0')
        self.assertEqual(items[-1], 'task2')
        
        # 弹出
        item = self.client.lpop('tasks')
        self.assertEqual(item, 'task0')
    
    def test_set_operations(self):
        """测试集合操作"""
        # 添加成员
        self.client.sadd('tags', 'python', 'redis', 'cache')
        
        # 获取所有成员
        members = self.client.smembers('tags')
        self.assertIn('python', members)
        self.assertIn('redis', members)
        
        # 成员数量
        count = self.client.scard('tags')
        self.assertEqual(count, 3)
        
        # 是否为成员
        is_member = self.client.sismember('tags', 'python')
        self.assertTrue(is_member)
        
        # 移除成员
        self.client.srem('tags', 'cache')
        members = self.client.smembers('tags')
        self.assertNotIn('cache', members)
    
    def test_sorted_set_operations(self):
        """测试有序集合操作"""
        # 添加成员
        self.client.zadd('leaderboard', {'alice': 100, 'bob': 90, 'charlie': 110})
        
        # 获取范围
        items = self.client.zrange('leaderboard', 0, -1, withscores=True)
        self.assertEqual(len(items), 3)
        
        # 获取成员分数
        score = self.client.zscore('leaderboard', 'alice')
        self.assertEqual(score, 100)
        
        # 成员数量
        count = self.client.zcard('leaderboard')
        self.assertEqual(count, 3)
    
    def test_key_operations(self):
        """测试键操作"""
        # 设置键
        self.client.set('test_key', 'value')
        
        # 存在检查
        exists = self.client.exists('test_key')
        self.assertEqual(exists, 1)
        
        # 重命名
        self.client.rename('test_key', 'new_key')
        exists = self.client.exists('test_key')
        self.assertEqual(exists, 0)
        exists = self.client.exists('new_key')
        self.assertEqual(exists, 1)
        
        # 删除
        deleted = self.client.delete('new_key')
        self.assertEqual(deleted, 1)
    
    def test_json_operations(self):
        """测试JSON序列化"""
        data = {'name': 'test', 'items': [1, 2, 3], 'nested': {'key': 'value'}}
        
        # 设置JSON
        self.client.set_json('json_key', data)
        
        # 获取JSON
        retrieved = self.client.get_json('json_key')
        self.assertEqual(retrieved, data)
    
    def test_cache_operations(self):
        """测试缓存操作"""
        data = {'result': [1, 2, 3]}
        
        # 设置缓存
        self.client.cache_set('cache_key', data, ttl=60)
        
        # 获取缓存
        retrieved = self.client.cache_get('cache_key')
        self.assertEqual(retrieved, data)
    
    def test_mget_mset(self):
        """测试批量操作"""
        # 批量设置
        self.client.mset({'key1': 'value1', 'key2': 'value2', 'key3': 'value3'})
        
        # 批量获取
        values = self.client.mget(['key1', 'key2', 'key3'])
        self.assertEqual(values[0], 'value1')
        self.assertEqual(values[1], 'value2')
        self.assertEqual(values[2], 'value3')
    
    def test_pattern_matching(self):
        """测试模式匹配"""
        # 设置多个键
        self.client.set('user:1:name', 'Alice')
        self.client.set('user:1:email', 'alice@test.com')
        self.client.set('user:2:name', 'Bob')
        self.client.set('product:1', 'item1')
        
        # 模式匹配
        keys = self.client.keys('user:*')
        self.assertEqual(len(keys), 3)
    
    def test_flushdb(self):
        """测试清空数据库"""
        # 添加数据
        self.client.set('key1', 'value1')
        self.client.set('key2', 'value2')
        
        # 清空
        result = self.client.flushdb()
        self.assertTrue(result)
        
        # 检查
        size = self.client.dbsize()
        self.assertEqual(size, 0)
    
    def test_lock(self):
        """测试分布式锁"""
        # 获取锁
        acquired = self.client.lock('resource:1', timeout=10)
        self.assertTrue(acquired)
        
        # 尝试获取已持有的锁（应该失败）
        acquired_again = self.client.lock('resource:1', timeout=1, blocking=False)
        self.assertFalse(bool(acquired_again))
        
        # 释放锁
        released = self.client.unlock('resource:1')
        self.assertTrue(released)
        
        # 再次获取应该成功
        acquired = self.client.lock('resource:1', timeout=10)
        self.assertTrue(acquired)
        self.client.unlock('resource:1')


class TestRedisHealthCheck(unittest.TestCase):
    """Redis健康检查测试"""
    
    def test_ping(self):
        """测试ping"""
        from modules.storage.redis_client.client import RedisClient
        
        client = RedisClient()
        self.assertTrue(client.ping())


if __name__ == '__main__':
    unittest.main()
