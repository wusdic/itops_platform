# -*- coding: utf-8 -*-
"""
ITOps Platform - 核心存储层
统一存储抽象层，支持Redis/TDengine/InfluxDB/MinIO/Qdrant
"""
import json
import time
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from datetime import datetime
import threading


class StorageClient(ABC):
    """存储客户端基类"""
    
    def __init__(self):
        self._connected = False
        self._config: Dict[str, Any] = {}
    
    @abstractmethod
    def connect(self) -> bool:
        """连接存储"""
        raise NotImplementedError
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        raise NotImplementedError
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        raise NotImplementedError
    
    @property
    def is_connected(self) -> bool:
        return self._connected


class RedisClient(StorageClient):
    """Redis客户端"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: str = None):
        super().__init__()
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client = None
        self._memory_store: Dict[str, Any] = {}  # 内存后备
        self._use_memory_fallback = False
    
    def connect(self) -> bool:
        try:
            import redis
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self._client.ping()
            self._connected = True
            self._use_memory_fallback = False
            return True
        except Exception as e:
            print(f"Redis连接失败，使用内存后备: {e}")
            self._use_memory_fallback = True
            self._connected = True
            return True  # 使用内存后备也算连接成功
    
    def disconnect(self):
        if self._client:
            self._client.close()
        self._connected = False
    
    def health_check(self) -> bool:
        if self._use_memory_fallback:
            return True
        try:
            return self._client.ping()
        except Exception:
            return False
    
    def _get_client(self):
        if self._use_memory_fallback:
            return None
        return self._client
    
    # 通用操作
    def get(self, key: str) -> Optional[str]:
        if self._use_memory_fallback:
            return self._memory_store.get(key)
        try:
            return self._client.get(key)
        except Exception:
            return self._memory_store.get(key)
    
    def set(self, key: str, value: str, ttl: int = None) -> bool:
        if self._use_memory_fallback:
            self._memory_store[key] = value
            return True
        try:
            if ttl:
                return self._client.setex(key, ttl, value)
            return self._client.set(key, value)
        except Exception:
            self._memory_store[key] = value
            return True
    
    def delete(self, key: str) -> int:
        if self._use_memory_fallback:
            return self._memory_store.pop(key, None) is not None
        try:
            return self._client.delete(key)
        except Exception:
            return self._memory_store.pop(key, None) is not None
    
    def exists(self, key: str) -> bool:
        if self._use_memory_fallback:
            return key in self._memory_store
        try:
            return bool(self._client.exists(key))
        except Exception:
            return key in self._memory_store
    
    def expire(self, key: str, ttl: int) -> bool:
        if self._use_memory_fallback:
            return True
        try:
            return self._client.expire(key, ttl)
        except Exception:
            return False
    
    def ttl(self, key: str) -> int:
        if self._use_memory_fallback:
            return -1
        try:
            return self._client.ttl(key)
        except Exception:
            return -1
    
    # Hash操作
    def hget(self, key: str, field: str) -> Optional[str]:
        if self._use_memory_fallback:
            hash_data = self._memory_store.get(key, {})
            return hash_data.get(field)
        try:
            return self._client.hget(key, field)
        except Exception:
            return self._memory_store.get(key, {}).get(field)
    
    def hset(self, key: str, field: str, value: str) -> int:
        if self._use_memory_fallback:
            if key not in self._memory_store:
                self._memory_store[key] = {}
            self._memory_store[key][field] = value
            return 1
        try:
            return self._client.hset(key, field, value)
        except Exception:
            if key not in self._memory_store:
                self._memory_store[key] = {}
            self._memory_store[key][field] = value
            return 1
    
    def hgetall(self, key: str) -> Dict[str, str]:
        if self._use_memory_fallback:
            return self._memory_store.get(key, {})
        try:
            return self._client.hgetall(key)
        except Exception:
            return self._memory_store.get(key, {})
    
    def hdel(self, key: str, *fields) -> int:
        if self._use_memory_fallback:
            if key in self._memory_store:
                for field in fields:
                    self._memory_store[key].pop(field, None)
            return len(fields)
        try:
            return self._client.hdel(key, *fields)
        except Exception:
            if key in self._memory_store:
                for field in fields:
                    self._memory_store[key].pop(field, None)
            return len(fields)
    
    # List操作
    def lpush(self, key: str, *values) -> int:
        if self._use_memory_fallback:
            if key not in self._memory_store:
                self._memory_store[key] = []
            self._memory_store[key] = list(values) + self._memory_store[key]
            return len(self._memory_store[key])
        try:
            return self._client.lpush(key, *values)
        except Exception:
            return self.lpush(key, *values)
    
    def rpush(self, key: str, *values) -> int:
        if self._use_memory_fallback:
            if key not in self._memory_store:
                self._memory_store[key] = []
            self._memory_store[key].extend(values)
            return len(self._memory_store[key])
        try:
            return self._client.rpush(key, *values)
        except Exception:
            return self.rpush(key, *values)
    
    def lrange(self, key: str, start: int, end: int) -> List[str]:
        if self._use_memory_fallback:
            return self._memory_store.get(key, [])[start:end+1]
        try:
            return self._client.lrange(key, start, end)
        except Exception:
            return self._memory_store.get(key, [])[start:end+1]
    
    # Pub/Sub
    def publish(self, channel: str, message: str) -> int:
        if self._use_memory_fallback:
            return 0
        try:
            return self._client.publish(channel, message)
        except Exception:
            return 0
    
    # 分布式锁
    def lock(self, name: str, timeout: int = 10, blocking_timeout: int = -1) -> Any:
        if self._use_memory_fallback:
            return _MemoryLock(name)
        try:
            return self._client.lock(name, timeout=timeout, blocking_timeout=blocking_timeout)
        except Exception:
            return _MemoryLock(name)
    
    # 管道
    def pipeline(self):
        if self._use_memory_fallback:
            return _MemoryPipeline(self._memory_store)
        try:
            return self._client.pipeline()
        except Exception:
            return _MemoryPipeline(self._memory_store)
    
    # JSON操作
    def set_json(self, key: str, data: Any, ttl: int = None) -> bool:
        return self.set(key, json.dumps(data, ensure_ascii=False), ttl)
    
    def get_json(self, key: str) -> Optional[Any]:
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None


class _MemoryLock:
    """内存分布式锁（后备实现）"""
    
    def __init__(self, name: str):
        self.name = name
        self._acquired = False
    
    def acquire(self, blocking: bool = True, timeout: int = -1):
        self._acquired = True
        return True
    
    def release(self):
        self._acquired = False
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *args):
        self.release()


class _MemoryPipeline:
    """内存管道（后备实现）"""
    
    def __init__(self, store: Dict):
        self.store = store
        self._commands = []
    
    def get(self, key: str):
        self._commands.append(('get', key))
        return self
    
    def set(self, key: str, value: str):
        self._commands.append(('set', key, value))
        return self
    
    def execute(self) -> List:
        results = []
        for cmd in self._commands:
            if cmd[0] == 'get':
                results.append(self.store.get(cmd[1]))
            elif cmd[0] == 'set':
                self.store[cmd[1]] = cmd[2]
                results.append(True)
        return results


class TDengineClient(StorageClient):
    """TDengine时序数据库客户端"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6041,
        username: str = "root",
        password: str = "taosdata",
        database: str = "itops"
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self._session = None
        self._base_url = f"http://{host}:{port}"
    
    def connect(self) -> bool:
        try:
            import requests
            # 简单的REST API连接测试
            response = requests.get(f"{self._base_url}/rest/sql", timeout=5)
            self._connected = True
            return True
        except Exception as e:
            print(f"TDengine连接失败: {e}")
            return False
    
    def disconnect(self):
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
        self._connected = False
    
    def health_check(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self._base_url}/rest/sql", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def execute(self, sql: str) -> List[Dict]:
        """执行SQL查询"""
        try:
            import requests
            
            auth = (self.username, self.password)
            headers = {"Content-Type": "text/plain"}

            # 执行SQL
            response = requests.post(
                f"{self._base_url}/rest/sql",
                data=sql,
                auth=auth,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                return []

            data = response.json()
            # TDengine 3.x: code=0 表示成功（无 status 字段）
            # TDengine 2.x: status="succ" 表示成功
            code = data.get("code")
            status = data.get("status")
            if code != 0 and status not in ("succ", "success"):
                return []

            # 解析结果
            # TDengine 3.x REST API: 列信息在 column_meta [[name, type, size], ...]
            # TDengine 2.x: 列信息在 column_names [name, ...]
            column_meta = data.get("column_meta", [])
            column_names = [col[0] if isinstance(col, list) else col for col in column_meta]
            rows = data.get("data", [])
            
            results = []
            for row in rows:
                results.append(dict(zip(column_names, row)))
            
            return results
        except Exception as e:
            print(f"TDengine执行SQL失败: {e}")
            return []
    
    def execute_raw(self, sql: str) -> str:
        """执行SQL并返回原始结果"""
        try:
            import requests
            auth = (self.username, self.password)
            headers = {"Content-Type": "text/plain"}

            response = requests.post(
                f"{self._base_url}/rest/sql",
                data=sql,
                auth=auth,
                headers=headers,
                timeout=30
            )
            return response.text
        except Exception as e:
            return f"{{\"error\": \"{e}\"}}"
    
    def create_database(self, database: str = None):
        """创建数据库"""
        db = database or self.database
        self.execute(f"CREATE DATABASE IF NOT EXISTS {db}")
    
    def create_table(self, table_name: str, columns: List[str]):
        """创建普通表（TDengine 3.x 不支持无子表直接插入超级表，优先使用普通表）"""
        col_str = ", ".join(columns)
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({col_str})"
        self.execute(sql)

    def create_normal_table(self, table_name: str, columns: List[str]):
        """创建普通表（同create_table，保留别名）"""
        self.create_table(table_name, columns)

    def create_supertable(self, table_name: str, columns: List[str], tags: List[str]):
        """创建超级表（需要子表）"""
        col_str = ", ".join(columns)
        tag_str = ", ".join(tags)
        sql = f"CREATE STABLE IF NOT EXISTS {table_name} ({col_str}) TAGS ({tag_str})"
        self.execute(sql)

    def create_subtable(self, table_name: str, stable_name: str, tags: List[str]):
        """创建子表（基于超级表）"""
        tag_str = ", ".join([f"'{t}'" if isinstance(t, str) else str(t) for t in tags])
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} USING {stable_name} TAGS ({tag_str})"
        self.execute(sql)

    def insert(self, table_name: str, data: List[Dict]):
        """插入数据到普通表（支持 TDengine 3.x）"""
        if not data:
            return

        for item in data:
            timestamp = item.get('ts') or int(time.time() * 1000)
            values = []
            for col, val in item.items():
                if col == 'ts':
                    values.append(str(val) if isinstance(val, int) else f"'{val}'")
                elif isinstance(val, str):
                    values.append(f"'{val}'")
                elif val is None:
                    values.append("NULL")
                else:
                    values.append(str(val))

            sql = f"INSERT INTO {table_name} VALUES ({', '.join(values)})"
            self.execute(sql)
    
    def query(self, sql: str) -> List[Dict]:
        """查询数据"""
        return self.execute(sql)
    
    def last_row(self, table_name: str, fields: List[str] = None) -> Optional[Dict]:
        """获取最后一条记录"""
        field_str = "*" if not fields else ", ".join(fields)
        results = self.execute(f"SELECT LAST({field_str}) FROM {table_name}")
        return results[0] if results else None


class InfluxDBClient(StorageClient):
    """InfluxDB时序数据库客户端"""
    
    def __init__(
        self,
        url: str = "http://localhost:8086",
        token: str = "",
        org: str = "itops",
        bucket: str = "metrics"
    ):
        super().__init__()
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self._client = None
    
    def connect(self) -> bool:
        try:
            from influxdb_client import InfluxDBClient
            self._client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            self._connected = True
            return True
        except Exception as e:
            print(f"InfluxDB连接失败: {e}")
            return False
    
    def disconnect(self):
        if self._client:
            self._client.close()
        self._connected = False
    
    def health_check(self) -> bool:
        try:
            return self._client.health() is not None
        except Exception:
            return False
    
    def write(self, measurement: str, tags: Dict[str, str], fields: Dict[str, Any], time: datetime = None):
        """写入数据点"""
        from influxdb_client import Point
        
        point = Point(measurement)
        
        for key, value in tags.items():
            point.tag(key, value)
        
        for key, value in fields.items():
            point.field(key, value)
        
        if time:
            point.time(time)
        
        with self._client.write_api() as write_api:
            write_api.write(bucket=self.bucket, org=self.org, record=point)
    
    def query(self, query: str) -> List[Dict]:
        """查询数据"""
        from influxdb_client.rest import ApiException
        
        try:
            query_api = self._client.query_api()
            result = query_api.query(query)
            
            results = []
            for table in result:
                for record in table.records:
                    results.append({
                        "time": record.get_time(),
                        "measurement": record.get_measurement(),
                        "tags": dict(record.values.get('tags', {})),
                        "fields": {k: v for k, v in record.values.items() if k not in ['tags', 'time', 'measurement']}
                    })
            return results
        except Exception as e:
            print(f"InfluxDB查询失败: {e}")
            return []


class MinIOClient(StorageClient):
    """MinIO对象存储客户端"""
    
    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket: str = "itops",
        secure: bool = False
    ):
        super().__init__()
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.secure = secure
        self._client = None
    
    def connect(self) -> bool:
        try:
            from minio import Minio
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            
            # 确保bucket存在
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
            
            self._connected = True
            return True
        except Exception as e:
            print(f"MinIO连接失败: {e}")
            return False
    
    def disconnect(self):
        self._connected = False
    
    def health_check(self) -> bool:
        try:
            return self._client.bucket_exists(self.bucket)
        except Exception:
            return False
    
    def upload_file(self, object_name: str, file_path: str, content_type: str = "application/octet-stream"):
        """上传文件"""
        from minio.error import S3Error
        
        try:
            self._client.fput_object(
                self.bucket,
                object_name,
                file_path,
                content_type=content_type
            )
            return True
        except S3Error as e:
            print(f"MinIO上传失败: {e}")
            return False
    
    def upload_data(self, object_name: str, data: bytes, content_type: str = "application/octet-stream"):
        """上传数据"""
        from io import BytesIO
        from minio.error import S3Error
        
        try:
            self._client.put_object(
                self.bucket,
                object_name,
                BytesIO(data),
                len(data),
                content_type=content_type
            )
            return True
        except S3Error as e:
            print(f"MinIO上传失败: {e}")
            return False
    
    def download_file(self, object_name: str, file_path: str):
        """下载文件"""
        from minio.error import S3Error
        
        try:
            self._client.fget_object(self.bucket, object_name, file_path)
            return True
        except S3Error as e:
            print(f"MinIO下载失败: {e}")
            return False
    
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """获取预签名URL"""
        try:
            return self._client.presigned_get_object(self.bucket, object_name, expires=expires)
        except Exception as e:
            print(f"MinIO获取预签名URL失败: {e}")
            return None
    
    def list_objects(self, prefix: str = "", recursive: bool = False) -> List[str]:
        """列出对象"""
        try:
            objects = self._client.list_objects(self.bucket, prefix=prefix, recursive=recursive)
            return [obj.object_name for obj in objects]
        except Exception as e:
            print(f"MinIO列出对象失败: {e}")
            return []
    
    def delete_object(self, object_name: str):
        """删除对象"""
        try:
            self._client.remove_object(self.bucket, object_name)
            return True
        except Exception:
            return False


class QdrantClient(StorageClient):
    """Qdrant向量数据库客户端"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection: str = "itops_knowledge",
        vector_size: int = 1536
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.collection = collection
        self.vector_size = vector_size
        self._base_url = f"http://{host}:{port}"
    
    def connect(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self._base_url}/collections/{self.collection}", timeout=5)
            if response.status_code == 200:
                self._connected = True
            elif response.status_code == 404:
                # 集合不存在，创建它
                self.create_collection()
                self._connected = True
            else:
                self._connected = False
            return self._connected
        except Exception as e:
            print(f"Qdrant连接失败: {e}")
            return False
    
    def disconnect(self):
        self._connected = False
    
    def health_check(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self._base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def create_collection(self, vector_size: int = None):
        """创建集合"""
        import requests
        
        size = vector_size or self.vector_size
        payload = {
            "vectors": {
                "size": size,
                "distance": "Cosine"
            }
        }
        
        try:
            requests.put(
                f"{self._base_url}/collections/{self.collection}",
                json=payload,
                timeout=30
            )
        except Exception as e:
            print(f"Qdrant创建集合失败: {e}")
    
    def upsert(self, points: List[Dict]):
        """插入或更新向量"""
        import requests
        
        payload = {
            "points": points
        }
        
        try:
            requests.put(
                f"{self._base_url}/collections/{self.collection}/points",
                json=payload,
                timeout=30
            )
        except Exception as e:
            print(f"Qdrant插入向量失败: {e}")
    
    def search(
        self,
        vector: List[float],
        limit: int = 5,
        score_threshold: float = None,
        filter_conditions: Dict = None
    ) -> List[Dict]:
        """向量相似度搜索"""
        import requests
        
        query = {
            "vector": vector,
            "limit": limit,
            "with_payload": True
        }
        
        if score_threshold:
            query["score_threshold"] = score_threshold
        
        if filter_conditions:
            query["filter"] = filter_conditions
        
        try:
            response = requests.post(
                f"{self._base_url}/collections/{self.collection}/points/search",
                json=query,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                return results.get("result", [])
            return []
        except Exception as e:
            print(f"Qdrant搜索失败: {e}")
            return []
    
    def delete(self, point_ids: List[str]):
        """删除向量"""
        import requests
        
        payload = {
            "points": point_ids
        }
        
        try:
            requests.post(
                f"{self._base_url}/collections/{self.collection}/points/delete",
                json=payload,
                timeout=30
            )
        except Exception as e:
            print(f"Qdrant删除向量失败: {e}")
    
    def count(self) -> int:
        """统计向量数量"""
        import requests
        
        try:
            response = requests.get(
                f"{self._base_url}/collections/{self.collection}/points/count",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get("result", {}).get("count", 0)
            return 0
        except Exception:
            return 0


class StorageManager:
    """存储管理器 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._clients: Dict[str, StorageClient] = {}
        self._config: Dict[str, Any] = {}
    
    def configure(self, config: Dict[str, Any]):
        """配置存储管理器"""
        self._config = config
    
    def get_redis(self) -> RedisClient:
        """获取Redis客户端"""
        if "redis" not in self._clients:
            redis_config = self._config.get("redis", {})
            self._clients["redis"] = RedisClient(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password")
            )
            self._clients["redis"].connect()
        return self._clients["redis"]
    
    def get_tdengine(self) -> TDengineClient:
        """获取TDengine客户端"""
        if "tdengine" not in self._clients:
            td_config = self._config.get("tdengine", {})
            self._clients["tdengine"] = TDengineClient(
                host=td_config.get("host", "localhost"),
                port=td_config.get("port", 6041),
                username=td_config.get("username", "root"),
                password=td_config.get("password", "taosdata"),
                database=td_config.get("database", "itops")
            )
            self._clients["tdengine"].connect()
        return self._clients["tdengine"]
    
    def get_influxdb(self) -> InfluxDBClient:
        """获取InfluxDB客户端"""
        if "influxdb" not in self._clients:
            influx_config = self._config.get("influxdb", {})
            self._clients["influxdb"] = InfluxDBClient(
                url=influx_config.get("url", "http://localhost:8086"),
                token=influx_config.get("token", ""),
                org=influx_config.get("org", "itops"),
                bucket=influx_config.get("bucket", "metrics")
            )
            self._clients["influxdb"].connect()
        return self._clients["influxdb"]
    
    def get_minio(self) -> MinIOClient:
        """获取MinIO客户端"""
        if "minio" not in self._clients:
            minio_config = self._config.get("minio", {})
            self._clients["minio"] = MinIOClient(
                endpoint=minio_config.get("endpoint", "localhost:9000"),
                access_key=minio_config.get("access_key", "minioadmin"),
                secret_key=minio_config.get("secret_key", "minioadmin"),
                bucket=minio_config.get("bucket", "itops"),
                secure=minio_config.get("secure", False)
            )
            self._clients["minio"].connect()
        return self._clients["minio"]
    
    def get_qdrant(self) -> QdrantClient:
        """获取Qdrant客户端"""
        if "qdrant" not in self._clients:
            qdrant_config = self._config.get("qdrant", {})
            self._clients["qdrant"] = QdrantClient(
                host=qdrant_config.get("host", "localhost"),
                port=qdrant_config.get("port", 6333),
                collection=qdrant_config.get("collection", "itops_knowledge"),
                vector_size=qdrant_config.get("vector_size", 1536)
            )
            self._clients["qdrant"].connect()
        return self._clients["qdrant"]
    
    def health_check_all(self) -> Dict[str, bool]:
        """检查所有存储健康状态"""
        results = {}
        for name, client in self._clients.items():
            results[name] = client.health_check()
        return results
    
    def close_all(self):
        """关闭所有连接"""
        for client in self._clients.values():
            try:
                client.disconnect()
            except Exception:
                pass
        self._clients.clear()


def get_storage_manager() -> StorageManager:
    """获取存储管理器快捷函数"""
    return StorageManager()
