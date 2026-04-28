"""
Redis缓存管理客户端核心实现

支持Redis/String/Hash/List/Set/ZSet等数据结构的完整操作。
"""

import json
import pickle
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class RedisClient:
    """
    Redis缓存客户端
    
    支持多种数据结构和丰富的缓存操作。
    
    Attributes:
        host: Redis服务器地址
        port: 端口
        password: 密码
        db: 数据库编号
        socket_timeout: 套接字超时
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        socket_timeout: int = 30,
        ssl: bool = False,
        decode_responses: bool = True
    ):
        """
        初始化Redis客户端
        
        Args:
            host: Redis主机地址
            port: 端口号
            password: 密码
            db: 数据库编号
            socket_timeout: 超时时间
            ssl: 是否使用SSL
            decode_responses: 是否自动解码响应
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self._decode_responses = decode_responses
        
        # 尝试导入redis库
        self._redis = None
        self._available = False
        
        try:
            import redis
            self._redis = redis
            self._available = True
            self._client = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                socket_timeout=socket_timeout,
                ssl=ssl,
                decode_responses=decode_responses
            )
        except ImportError:
            # 使用内存模拟作为后备
            self._client = self._MemoryStore()
    
    # ========== String Operations ==========
    
    def set(
        self,
        key: str,
        value: Union[str, int, float, bytes, Any],
        ex: Optional[int] = None,
        px: Optional[int] = None,
        exat: Optional[int] = None,
        pxat: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        设置键值对
        
        Args:
            key: 键名
            value: 值
            ex: 过期秒数
            px: 过期毫秒数
            exat: 过期时间戳（秒）
            pxat: 过期时间戳（毫秒）
            nx: 仅在键不存在时设置
            xx: 仅在键存在时设置
            
        Returns:
            设置是否成功
        """
        if self._available:
            return self._client.set(key, value, ex=ex, px=px, exat=exat, pxat=pxat, nx=nx, xx=xx)
        else:
            return self._client.set(key, value, ex=ex)
    
    def get(self, key: str) -> Optional[str]:
        """获取值"""
        if self._available:
            return self._client.get(key)
        else:
            return self._client.get(key)
    
    def mset(self, mapping: Dict[str, Any]) -> bool:
        """批量设置"""
        if self._available:
            return self._client.mset(mapping)
        else:
            for k, v in mapping.items():
                self._client.set(k, v)
            return True
    
    def mget(self, keys: List[str]) -> List[Optional[str]]:
        """批量获取"""
        if self._available:
            return self._client.mget(keys)
        else:
            return [self._client.get(k) for k in keys]
    
    def setnx(self, key: str, value: Any) -> bool:
        """仅键不存在时设置"""
        if self._available:
            return self._client.setnx(key, value)
        else:
            if not self._client.exists(key):
                self._client.set(key, value)
                return True
            return False
    
    def setex(self, key: str, time: Union[int, timedelta], value: Any) -> bool:
        """设置带过期时间"""
        if self._available:
            return self._client.setex(key, time, value)
        else:
            return self._client.set(key, value, ex=int(time) if isinstance(time, timedelta) else time)
    
    def incr(self, key: str, amount: int = 1) -> int:
        """递增"""
        if self._available:
            return self._client.incrby(key, amount)
        else:
            val = int(self._client.get(key) or 0) + amount
            self._client.set(key, val)
            return val
    
    def decr(self, key: str, amount: int = 1) -> int:
        """递减"""
        if self._available:
            return self._client.decrby(key, amount)
        else:
            val = int(self._client.get(key) or 0) - amount
            self._client.set(key, val)
            return val
    
    def append(self, key: str, value: str) -> int:
        """追加字符串"""
        if self._available:
            return self._client.append(key, value)
        else:
            val = (self._client.get(key) or '') + value
            self._client.set(key, val)
            return len(val)
    
    # ========== Hash Operations ==========
    
    def hset(
        self,
        name: str,
        key: Optional[str] = None,
        value: Optional[Any] = None,
        mapping: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        设置哈希字段
        
        Args:
            name: 哈希键名
            key: 字段名
            value: 字段值
            mapping: 字段字典
            
        Returns:
            设置的字段数
        """
        if self._available:
            if mapping:
                return self._client.hset(name, mapping=mapping)
            else:
                return self._client.hset(name, key, value)
        else:
            if mapping:
                for k, v in mapping.items():
                    self._client.hset(name, k, v)
                return len(mapping)
            else:
                self._client.hset(name, key, value)
                return 1
    
    def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希字段"""
        if self._available:
            return self._client.hget(name, key)
        else:
            return self._client.hget(name, key)
    
    def hgetall(self, name: str) -> Dict[str, str]:
        """获取所有哈希字段"""
        if self._available:
            return self._client.hgetall(name)
        else:
            return self._client.hgetall(name)
    
    def hmset(self, name: str, mapping: Dict[str, Any]) -> bool:
        """批量设置哈希字段"""
        if self._available:
            return self._client.hmset(name, mapping)
        else:
            return self._client.hset(name, mapping=mapping)
    
    def hmget(self, name: str, keys: List[str]) -> List[Optional[str]]:
        """批量获取哈希字段"""
        if self._available:
            return self._client.hmget(name, keys)
        else:
            return self._client.hmget(name, keys)
    
    def hkeys(self, name: str) -> List[str]:
        """获取所有字段名"""
        if self._available:
            return self._client.hkeys(name)
        else:
            return self._client.hkeys(name)
    
    def hvals(self, name: str) -> List[str]:
        """获取所有字段值"""
        if self._available:
            return self._client.hvals(name)
        else:
            return self._client.hvals(name)
    
    def hlen(self, name: str) -> int:
        """获取字段数量"""
        if self._available:
            return self._client.hlen(name)
        else:
            return self._client.hlen(name)
    
    def hexists(self, name: str, key: str) -> bool:
        """检查字段是否存在"""
        if self._available:
            return self._client.hexists(name, key)
        else:
            return self._client.hexists(name, key)
    
    def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """哈希字段递增"""
        if self._available:
            return self._client.hincrby(name, key, amount)
        else:
            val = int(self._client.hget(name, key) or 0) + amount
            self._client.hset(name, key, val)
            return val
    
    def hdel(self, name: str, *keys: str) -> int:
        """删除哈希字段"""
        if self._available:
            return self._client.hdel(name, *keys)
        else:
            return self._client.hdel(name, *keys)
    
    # ========== List Operations ==========
    
    def lpush(self, name: str, *values: Any) -> int:
        """从左侧插入"""
        if self._available:
            return self._client.lpush(name, *values)
        else:
            return self._client.lpush(name, *values)
    
    def rpush(self, name: str, *values: Any) -> int:
        """从右侧插入"""
        if self._available:
            return self._client.rpush(name, *values)
        else:
            return self._client.rpush(name, *values)
    
    def lpop(self, name: str) -> Optional[str]:
        """从左侧弹出"""
        if self._available:
            return self._client.lpop(name)
        else:
            return self._client.lpop(name)
    
    def rpop(self, name: str) -> Optional[str]:
        """从右侧弹出"""
        if self._available:
            return self._client.rpop(name)
        else:
            return self._client.rpop(name)
    
    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[str]:
        """获取列表范围"""
        if self._available:
            return self._client.lrange(name, start, end)
        else:
            return self._client.lrange(name, start, end)
    
    def llen(self, name: str) -> int:
        """获取列表长度"""
        if self._available:
            return self._client.llen(name)
        else:
            return self._client.llen(name)
    
    def ltrim(self, name: str, start: int, end: int) -> bool:
        """修剪列表"""
        if self._available:
            return self._client.ltrim(name, start, end)
        else:
            return self._client.ltrim(name, start, end)
    
    # ========== Set Operations ==========
    
    def sadd(self, name: str, *values: Any) -> int:
        """添加集合成员"""
        if self._available:
            return self._client.sadd(name, *values)
        else:
            return self._client.sadd(name, *values)
    
    def smembers(self, name: str) -> Set[str]:
        """获取所有成员"""
        if self._available:
            return self._client.smembers(name)
        else:
            return self._client.smembers(name)
    
    def sismember(self, name: str, value: Any) -> bool:
        """检查是否为成员"""
        if self._available:
            return self._client.sismember(name, value)
        else:
            return self._client.sismember(name, value)
    
    def scard(self, name: str) -> int:
        """获取成员数量"""
        if self._available:
            return self._client.scard(name)
        else:
            return self._client.scard(name)
    
    def srem(self, name: str, *values: Any) -> int:
        """移除成员"""
        if self._available:
            return self._client.srem(name, *values)
        else:
            return self._client.srem(name, *values)
    
    # ========== Sorted Set Operations ==========
    
    def zadd(
        self,
        name: str,
        mapping: Dict[Any, float],
        nx: bool = False,
        xx: bool = False,
        ch: bool = False
    ) -> int:
        """添加有序集合成员"""
        if self._available:
            return self._client.zadd(name, mapping, nx=nx, xx=xx, ch=ch)
        else:
            return self._client.zadd(name, mapping)
    
    def zrange(
        self,
        name: str,
        start: int = 0,
        end: int = -1,
        desc: bool = False,
        withscores: bool = False
    ) -> List[Any]:
        """获取有序集合范围"""
        if self._available:
            return self._client.zrange(name, start, end, desc=desc, withscores=withscores)
        else:
            return self._client.zrange(name, start, end, desc=desc, withscores=withscores)
    
    def zrevrange(
        self,
        name: str,
        start: int = 0,
        end: int = -1,
        withscores: bool = False
    ) -> List[Any]:
        """逆序获取范围"""
        if self._available:
            return self._client.zrevrange(name, start, end, withscores=withscores)
        else:
            return self._client.zrevrange(name, start, end, withscores=withscores)
    
    def zrangebyscore(
        self,
        name: str,
        min: Union[int, str],
        max: Union[int, str],
        withscores: bool = False,
        offset: Optional[int] = None,
        num: Optional[int] = None
    ) -> List[Any]:
        """按分数范围获取"""
        if self._available:
            return self._client.zrangebyscore(
                name, min, max, withscores=withscores, offset=offset, num=num
            )
        else:
            return self._client.zrangebyscore(name, min, max, withscores=withscores)
    
    def zscore(self, name: str, member: Any) -> Optional[float]:
        """获取成员分数"""
        if self._available:
            return self._client.zscore(name, member)
        else:
            return self._client.zscore(name, member)
    
    def zcard(self, name: str) -> int:
        """获取成员数量"""
        if self._available:
            return self._client.zcard(name)
        else:
            return self._client.zcard(name)
    
    def zrem(self, name: str, *members: Any) -> int:
        """移除成员"""
        if self._available:
            return self._client.zrem(name, *members)
        else:
            return self._client.zrem(name, *members)
    
    # ========== Key Operations ==========
    
    def delete(self, *keys: str) -> int:
        """删除键"""
        if self._available:
            return self._client.delete(*keys)
        else:
            return self._client.delete(*keys)
    
    def exists(self, *keys: str) -> int:
        """检查键是否存在"""
        if self._available:
            return self._client.exists(*keys)
        else:
            return self._client.exists(*keys)
    
    def expire(self, name: str, time: Union[int, timedelta]) -> bool:
        """设置过期时间"""
        if self._available:
            return self._client.expire(name, time)
        else:
            return self._client.expire(name, time)
    
    def ttl(self, name: str) -> int:
        """获取剩余生存时间"""
        if self._available:
            return self._client.ttl(name)
        else:
            return self._client.ttl(name)
    
    def persist(self, name: str) -> bool:
        """移除过期时间"""
        if self._available:
            return self._client.persist(name)
        else:
            return self._client.persist(name)
    
    def keys(self, pattern: str = '*') -> List[str]:
        """获取匹配的键"""
        if self._available:
            return self._client.keys(pattern)
        else:
            return self._client.keys(pattern)
    
    def rename(self, src: str, dst: str) -> bool:
        """重命名键"""
        if self._available:
            return self._client.rename(src, dst)
        else:
            return self._client.rename(src, dst)
    
    # ========== JSON/Serialization ==========
    
    def set_json(self, key: str, value: Any, **kwargs) -> bool:
        """设置JSON值"""
        return self.set(key, json.dumps(value), **kwargs)
    
    def get_json(self, key: str) -> Optional[Any]:
        """获取JSON值"""
        value = self.get(key)
        if value:
            return json.loads(value)
        return None
    
    def set_pickle(self, key: str, value: Any, **kwargs) -> bool:
        """设置Pickle值"""
        return self.set(key, pickle.dumps(value), **kwargs)
    
    def get_pickle(self, key: str) -> Optional[Any]:
        """获取Pickle值"""
        value = self.get(key)
        if value:
            return pickle.loads(value)
        return None
    
    # ========== Cache Utilities ==========
    
    def cache_set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """缓存设置（带默认TTL）"""
        return self.set(key, json.dumps(value), ex=ttl)
    
    def cache_get(self, key: str) -> Optional[Any]:
        """缓存获取"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    # ========== Distributed Lock ==========
    
    def lock(
        self,
        name: str,
        timeout: int = 10,
        blocking_timeout: int = 3,
        blocking: bool = True
    ) -> bool:
        """
        获取分布式锁
        
        Args:
            name: 锁名称
            timeout: 锁超时时间
            blocking_timeout: 阻塞等待时间
            blocking: 是否阻塞等待
            
        Returns:
            是否成功获取锁
        """
        if self._available:
            try:
                lock = self._client.lock(
                    name,
                    timeout=timeout,
                    blocking_timeout=blocking_timeout,
                    blocking=blocking
                )
                return lock.acquire()
            except Exception:
                return False
        else:
            return self._client.lock(name, timeout, blocking_timeout, blocking)
    
    def unlock(self, name: str) -> bool:
        """释放分布式锁"""
        if self._available:
            try:
                lock = self._client.lock(name)
                return lock.release()
            except Exception:
                return False
        else:
            return self._client.unlock(name)
    
    # ========== Health & Info ==========
    
    def ping(self) -> bool:
        """健康检查"""
        try:
            if self._available:
                return self._client.ping()
            else:
                return self._client.ping()
        except Exception:
            return False
    
    def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """获取Redis信息"""
        if self._available:
            return self._client.info(section)
        else:
            return {
                'version': 'memory_mock',
                'used_memory': 0,
                'connected_clients': 1
            }
    
    def dbsize(self) -> int:
        """获取键数量"""
        if self._available:
            return self._client.dbsize()
        else:
            return self._client.dbsize()
    
    def flushdb(self) -> bool:
        """清空当前数据库"""
        if self._available:
            return self._client.flushdb()
        else:
            return self._client.flushdb()
    
    def close(self):
        """关闭连接"""
        if self._available:
            self._client.close()
    
    # ========== Memory Store (Fallback) ==========
    
    class _MemoryStore:
        """内存存储后备实现"""
        
        def __init__(self):
            self._data: Dict[str, Any] = {}
            self._hashes: Dict[str, Dict[str, Any]] = {}
            self._lists: Dict[str, List] = {}
            self._sets: Dict[str, Set] = {}
            self._zsets: Dict[str, Dict] = {}
            self._expiry: Dict[str, float] = {}
        
        def _check_expiry(self, key: str) -> bool:
            """检查并清理过期键"""
            if key in self._expiry:
                if time.time() > self._expiry[key]:
                    self._cleanup_key(key)
                    return False
            return True
        
        def _cleanup_key(self, key: str):
            """清理键"""
            for store in [self._data, self._hashes, self._lists, self._sets, self._zsets]:
                if key in store:
                    del store[key]
            if key in self._expiry:
                del self._expiry[key]
        
        def set(self, key, value, ex=None, px=None, exat=None, pxat=None, nx=False, xx=False):
            if nx and key in self._data:
                return False
            if xx and key not in self._data:
                return False
            
            self._data[key] = value
            if ex:
                self._expiry[key] = time.time() + ex
            elif px:
                self._expiry[key] = time.time() + px / 1000
            elif exat:
                self._expiry[key] = exat
            elif pxat:
                self._expiry[key] = pxat / 1000
            return True
        
        def get(self, key):
            if not self._check_expiry(key):
                return None
            return self._data.get(key)
        
        def mset(self, mapping):
            self._data.update(mapping)
            return True
        
        def mget(self, keys):
            return [self.get(k) for k in keys]
        
        def delete(self, *keys):
            count = 0
            for key in keys:
                if self._check_expiry(key):
                    self._cleanup_key(key)
                    count += 1
            return count
        
        def exists(self, *keys):
            return sum(1 for k in keys if self._check_expiry(k) and k in self._data)
        
        def expire(self, name, time):
            if name in self._data:
                self._expiry[name] = time.time() + (int(time) if isinstance(time, int) else 0)
                return True
            return False
        
        def ttl(self, name):
            if name not in self._expiry:
                return -1 if name in self._data else -2
            return max(0, int(self._expiry[name] - time.time()))
        
        def persist(self, name):
            if name in self._expiry:
                del self._expiry[name]
                return True
            return False
        
        def keys(self, pattern='*'):
            result = []
            for key in self._data:
                if self._check_expiry(key):
                    if pattern == '*' or self._match_pattern(key, pattern):
                        result.append(key)
            return result
        
        def _match_pattern(self, key, pattern):
            import fnmatch
            return fnmatch.fnmatch(key, pattern)
        
        def ping(self):
            return True
        
        def dbsize(self):
            return len([k for k in self._data if self._check_expiry(k)])
        
        def flushdb(self):
            self._data.clear()
            self._hashes.clear()
            self._lists.clear()
            self._sets.clear()
            self._zsets.clear()
            self._expiry.clear()
            return True
        
        # Hash operations
        def hset(self, name, key=None, value=None, mapping=None):
            if name not in self._hashes:
                self._hashes[name] = {}
            if mapping:
                self._hashes[name].update(mapping)
                return len(mapping)
            else:
                self._hashes[name][key] = value
                return 1
        
        def hget(self, name, key):
            return self._hashes.get(name, {}).get(key)
        
        def hgetall(self, name):
            return self._hashes.get(name, {}).copy()
        
        def hmget(self, name, keys):
            return [self._hashes.get(name, {}).get(k) for k in keys]
        
        def hkeys(self, name):
            return list(self._hashes.get(name, {}).keys())
        
        def hvals(self, name):
            return list(self._hashes.get(name, {}).values())
        
        def hlen(self, name):
            return len(self._hashes.get(name, {}))
        
        def hexists(self, name, key):
            return key in self._hashes.get(name, {})
        
        def hincrby(self, name, key, amount):
            if name not in self._hashes:
                self._hashes[name] = {}
            val = int(self._hashes[name].get(key, 0)) + amount
            self._hashes[name][key] = val
            return val
        
        def hdel(self, name, *keys):
            if name in self._hashes:
                count = 0
                for k in keys:
                    if k in self._hashes[name]:
                        del self._hashes[name][k]
                        count += 1
                return count
            return 0
        
        # List operations
        def lpush(self, name, *values):
            if name not in self._lists:
                self._lists[name] = []
            self._lists[name] = list(values) + self._lists[name]
            return len(self._lists[name])
        
        def rpush(self, name, *values):
            if name not in self._lists:
                self._lists[name] = []
            self._lists[name].extend(values)
            return len(self._lists[name])
        
        def lpop(self, name):
            if name in self._lists and self._lists[name]:
                return self._lists[name].pop(0)
            return None
        
        def rpop(self, name):
            if name in self._lists and self._lists[name]:
                return self._lists[name].pop()
            return None
        
        def lrange(self, name, start, end):
            if name not in self._lists:
                return []
            if end == -1:
                return self._lists[name][start:]
            return self._lists[name][start:end+1]
        
        def llen(self, name):
            return len(self._lists.get(name, []))
        
        def ltrim(self, name, start, end):
            if name in self._lists:
                self._lists[name] = self.lrange(name, start, end)
            return True
        
        # Set operations
        def sadd(self, name, *values):
            if name not in self._sets:
                self._sets[name] = set()
            self._sets[name].update(values)
            return len(self._sets[name])
        
        def smembers(self, name):
            return self._sets.get(name, set()).copy()
        
        def sismember(self, name, value):
            return value in self._sets.get(name, set())
        
        def scard(self, name):
            return len(self._sets.get(name, set()))
        
        def srem(self, name, *values):
            if name in self._sets:
                removed = len(self._sets[name] & set(values))
                self._sets[name] -= set(values)
                return removed
            return 0
        
        # Sorted Set operations
        def zadd(self, name, mapping, nx=False, xx=False, ch=False):
            if name not in self._zsets:
                self._zsets[name] = {}
            count = 0
            for member, score in mapping.items():
                if nx and member in self._zsets[name]:
                    continue
                if xx and member not in self._zsets[name]:
                    continue
                self._zsets[name][member] = score
                count += 1
            return count
        
        def zrange(self, name, start, end, desc=False, withscores=False):
            if name not in self._zsets:
                return []
            items = sorted(self._zsets[name].items(), key=lambda x: x[1])
            if desc:
                items = items[::-1]
            items = items[start:end+1] if end != -1 else items[start:]
            if withscores:
                return items
            return [k for k, v in items]
        
        def zrevrange(self, name, start, end, withscores=False):
            return self.zrange(name, start, end, desc=True, withscores=withscores)
        
        def zrangebyscore(self, name, min, max, withscores=False):
            if name not in self._zsets:
                return []
            items = [(k, v) for k, v in self._zsets[name].items() 
                    if (min in ['-inf', '-inf'] or v >= (float(min) if isinstance(min, str) and min != '-inf' else min)) and
                       (max in ['+inf', '+inf'] or v <= (float(max) if isinstance(max, str) and max != '+inf' else max))]
            if withscores:
                return items
            return [k for k, v in items]
        
        def zscore(self, name, member):
            return self._zsets.get(name, {}).get(member)
        
        def zcard(self, name):
            return len(self._zsets.get(name, {}))
        
        def zrem(self, name, *members):
            if name in self._zsets:
                count = len(self._zsets[name] & set(members))
                self._zsets[name] = {k: v for k, v in self._zsets[name].items() if k not in members}
                return count
            return 0
        
        def rename(self, src, dst):
            if src in self._data:
                self._data[dst] = self._data.pop(src)
            return True
        
        def close(self):
            pass
        
        def lock(self, name, timeout, blocking_timeout, blocking):
            """简化的锁实现"""
            return _SimpleLock(name, self)
        
        def info(self, section=None):
            return {'version': 'memory_mock'}


class _SimpleLock:
    """简化的内存锁实现"""
    
    def __init__(self, name, store):
        self.name = name
        self.store = store
        self.lock_key = f'_lock:{name}'
    
    def acquire(self):
        if self.lock_key not in self.store._data:
            self.store._data[self.lock_key] = '1'
            return True
        return False
    
    def release(self):
        if self.lock_key in self.store._data:
            del self.store._data[self.lock_key]
            return True
        return False


if __name__ == '__main__':
    # 配置连接参数
    config = {
        'host': 'localhost',
        'port': 6379,
        'password': None,
        'db': 0
    }
    
    # 创建客户端
    client = RedisClient(**config)
    
    # String操作
    client.set('key1', 'value1', ex=60)
    print(f"GET key1: {client.get('key1')}")
    
    # Hash操作
    client.hset('user:1', mapping={'name': 'Alice', 'email': 'alice@example.com'})
    print(f"HGETALL user:1: {client.hgetall('user:1')}")
    
    # List操作
    client.lpush('tasks', 'task1', 'task2', 'task3')
    print(f"LRANGE tasks: {client.lrange('tasks', 0, -1)}")
    
    # Set操作
    client.sadd('tags', 'python', 'redis', 'cache')
    print(f"SMEMBERS tags: {client.smembers('tags')}")
    
    # Sorted Set操作
    client.zadd('leaderboard', {'alice': 100, 'bob': 90, 'charlie': 110})
    print(f"ZRANGE leaderboard: {client.zrange('leaderboard', 0, -1, withscores=True)}")
    
    # 计数器
    client.set('counter', 0)
    client.incr('counter')
    client.incr('counter')
    print(f"Counter: {client.get('counter')}")
    
    # 缓存示例
    cache_data = {'items': [1, 2, 3], 'total': 100}
    client.cache_set('api:data', cache_data, ttl=300)
    print(f"Cache get: {client.cache_get('api:data')}")
    
    # JSON缓存
    client.set_json('config', {'debug': True, 'level': 'info'})
    print(f"JSON get: {client.get_json('config')}")
    
    # 分布式锁
    if client.lock('resource:1', timeout=10):
        print("Lock acquired")
        # 执行业务逻辑
        client.unlock('resource:1')
        print("Lock released")
    
    # 健康检查
    print(f"Ping: {client.ping()}")
    print(f"DB size: {client.dbsize()}")
    
    # 清理
    client.flushdb()
    print("DB flushed")
    
    client.close()
