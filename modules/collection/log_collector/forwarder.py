"""日志转发器 - 支持多种后端"""
import os
import json
import logging
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ForwarderType(Enum):
    """转发器类型"""
    ELASTICSEARCH = "elasticsearch"
    TDENGINE = "tdengine"
    KAFKA = "kafka"
    REDIS = "redis"
    FILE = "file"
    HTTP = "http"
    NULL = "null"


@dataclass
class LogRecord:
    """日志记录"""
    timestamp: datetime
    level: str
    message: str
    source: str
    hostname: str
    service: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class ForwarderBackend(ABC):
    """转发器后端基类"""
    
    @abstractmethod
    def connect(self):
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def send(self, record: LogRecord) -> bool:
        """发送单条记录"""
        pass
    
    @abstractmethod
    def send_batch(self, records: List[LogRecord]) -> bool:
        """批量发送"""
        pass
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return False


class ElasticsearchForwarder(ForwarderBackend):
    """
    Elasticsearch转发器
    可选功能，需要安装elasticsearch包
    """
    
    def __init__(
        self,
        hosts: List[str],
        index_prefix: str = "logs-",
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.hosts = hosts
        self.index_prefix = index_prefix
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None
        self._connected = False
    
    def connect(self):
        """建立连接"""
        try:
            from elasticsearch import Elasticsearch
            
            es_config = {
                'hosts': self.hosts,
                'timeout': self.timeout,
                'max_retries': self.max_retries,
            }
            
            if self.username and self.password:
                es_config['basic_auth'] = (self.username, self.password)
            
            self._client = Elasticsearch(**es_config)
            
            # 测试连接
            if self._client.ping():
                self._connected = True
                logger.info(f"Connected to Elasticsearch: {self.hosts}")
            else:
                logger.warning("Elasticsearch ping failed")
        
        except ImportError:
            logger.error("elasticsearch package not installed")
            raise ImportError("Install elasticsearch package: pip install elasticsearch")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
    
    def disconnect(self):
        """断开连接"""
        if self._client:
            self._client.close()
            self._connected = False
    
    def is_connected(self) -> bool:
        return self._connected
    
    def _get_index_name(self, timestamp: datetime) -> str:
        """获取索引名称"""
        return f"{self.index_prefix}{timestamp.strftime('%Y.%m.%d')}"
    
    def send(self, record: LogRecord) -> bool:
        """发送单条记录"""
        if not self._client:
            return False
        
        try:
            self._client.index(
                index=self._get_index_name(record.timestamp),
                document=record.to_dict(),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send log to Elasticsearch: {e}")
            return False
    
    def send_batch(self, records: List[LogRecord]) -> bool:
        """批量发送"""
        if not self._client or not records:
            return False
        
        try:
            from elasticsearch.helpers import bulk
            
            actions = [
                {
                    '_index': self._get_index_name(r.timestamp),
                    '_source': r.to_dict(),
                }
                for r in records
            ]
            
            success, failed = bulk(self._client, actions)
            
            if failed:
                logger.warning(f"Failed to send {len(failed)} logs")
            
            return success > 0
        except Exception as e:
            logger.error(f"Failed to bulk send to Elasticsearch: {e}")
            return False


class TDengineForwarder(ForwarderBackend):
    """
    TDengine转发器
    用于时序数据存储
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6030,
        username: str = "root",
        password: str = "taosdata",
        database: str = "logs",
        table_name: str = "logs",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.table_name = table_name
        self._conn = None
        self._connected = False
    
    def connect(self):
        """建立连接"""
        try:
            import taospy as taos
            
            self._conn = taos.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
            )
            
            # 创建数据库
            cursor = self._conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")
            
            # 创建表
            cursor.execute(f"""
                CREATE STABLE IF NOT EXISTS {self.table_name} (
                    ts TIMESTAMP,
                    level BINARY(20),
                    message BINARY(1024),
                    source BINARY(100),
                    hostname BINARY(100),
                    service BINARY(100)
                ) TAGS (tag1 BINARY(50))
            """)
            
            cursor.close()
            self._connected = True
            logger.info(f"Connected to TDengine: {self.host}:{self.port}")
        
        except ImportError:
            logger.error("taospy package not installed")
            raise ImportError("Install taospy package: pip install taospy")
        except Exception as e:
            logger.error(f"Failed to connect to TDengine: {e}")
            raise
    
    def disconnect(self):
        """断开连接"""
        if self._conn:
            self._conn.close()
            self._connected = False
    
    def is_connected(self) -> bool:
        return self._connected
    
    def send(self, record: LogRecord) -> bool:
        """发送单条记录"""
        if not self._conn:
            return False
        
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                f"INSERT INTO {self.table_name}_{record.hostname} "
                f"USING {self.table_name} TAGS ('{record.hostname}') "
                f"VALUES ('{record.timestamp.isoformat()}', '{record.level}', "
                f"'{record.message}', '{record.source}', '{record.hostname}', '{record.service}')"
            )
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to send log to TDengine: {e}")
            return False
    
    def send_batch(self, records: List[LogRecord]) -> bool:
        """批量发送"""
        if not self._conn or not records:
            return False
        
        try:
            cursor = self._conn.cursor()
            
            values = []
            for r in records:
                values.append(
                    f"('{r.timestamp.isoformat()}', '{r.level}', "
                    f"'{r.message}', '{r.source}', '{r.hostname}', '{r.service}')"
                )
            
            sql = f"INSERT INTO {self.table_name}_all VALUES {','.join(values)}"
            cursor.execute(sql)
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to batch send to TDengine: {e}")
            return False


class FileForwarder(ForwarderBackend):
    """
    文件转发器
    将日志写入本地文件
    """
    
    def __init__(
        self,
        file_path: str,
        append: bool = True,
        format: str = "json",  # json, text, syslog
        rotation: Optional[Dict[str, Any]] = None,
    ):
        self.file_path = file_path
        self.append = append
        self.format = format
        self.rotation = rotation or {}
        self._file = None
        self._lock = threading.Lock()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    
    def connect(self):
        """打开文件"""
        mode = 'a' if self.append else 'w'
        self._file = open(self.file_path, mode, encoding='utf-8')
        logger.info(f"Opened log file: {self.file_path}")
    
    def disconnect(self):
        """关闭文件"""
        if self._file:
            self._file.close()
            self._file = None
    
    def is_connected(self) -> bool:
        return self._file is not None
    
    def _format_text(self, record: LogRecord) -> str:
        """文本格式"""
        return f"{record.timestamp.isoformat()} {record.level} [{record.source}] {record.message}\n"
    
    def _format_syslog(self, record: LogRecord) -> str:
        """Syslog格式"""
        priority = self._get_syslog_priority(record.level)
        return f"<{priority}>{record.timestamp.strftime('%b %d %H:%M:%S')} {record.hostname} {record.service}: {record.message}\n"
    
    def _get_syslog_priority(self, level: str) -> int:
        """获取Syslog优先级"""
        level_map = {
            'CRITICAL': 2,  # (local0 + critical)
            'ERROR': 3,     # (local0 + error)
            'WARNING': 4,   # (local0 + warning)
            'INFO': 6,     # (local0 + info)
            'DEBUG': 7,    # (local0 + debug)
        }
        return level_map.get(level, 6) + 16 * 16  # local0 facility
    
    def _check_rotation(self):
        """检查日志轮转"""
        if not self.rotation:
            return
        
        max_size = self.rotation.get('max_size', 100 * 1024 * 1024)  # 100MB
        max_files = self.rotation.get('max_files', 10)
        
        if os.path.exists(self.file_path):
            size = os.path.getsize(self.file_path)
            
            if size >= max_size:
                # 轮转文件
                self._file.close()
                
                # 移动旧文件
                for i in range(max_files - 1, 0, -1):
                    src = f"{self.file_path}.{i}"
                    dst = f"{self.file_path}.{i + 1}"
                    if os.path.exists(src):
                        os.rename(src, dst)
                
                if os.path.exists(self.file_path):
                    os.rename(self.file_path, f"{self.file_path}.1")
                
                # 重新打开
                self._file = open(self.file_path, 'w', encoding='utf-8')
    
    def send(self, record: LogRecord) -> bool:
        """发送单条记录"""
        with self._lock:
            if not self._file:
                return False
            
            try:
                self._check_rotation()
                
                if self.format == "json":
                    line = record.to_json() + "\n"
                elif self.format == "syslog":
                    line = self._format_syslog(record)
                else:
                    line = self._format_text(record)
                
                self._file.write(line)
                self._file.flush()
                return True
            except Exception as e:
                logger.error(f"Failed to write log to file: {e}")
                return False
    
    def send_batch(self, records: List[LogRecord]) -> bool:
        """批量发送"""
        with self._lock:
            if not self._file:
                return False
            
            try:
                self._check_rotation()
                
                lines = []
                for record in records:
                    if self.format == "json":
                        lines.append(record.to_json() + "\n")
                    elif self.format == "syslog":
                        lines.append(self._format_syslog(record))
                    else:
                        lines.append(self._format_text(record))
                
                self._file.writelines(lines)
                self._file.flush()
                return True
            except Exception as e:
                logger.error(f"Failed to batch write logs to file: {e}")
                return False


class KafkaForwarder(ForwarderBackend):
    """
    Kafka转发器
    可选功能，需要安装kafka-python或confluent-kafka
    """
    
    def __init__(
        self,
        bootstrap_servers: List[str],
        topic: str,
        client_id: str = "log_forwarder",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.client_id = client_id
        self._producer = None
        self._connected = False
    
    def connect(self):
        """建立连接"""
        try:
            from kafka import KafkaProducer
            
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            )
            self._connected = True
            logger.info(f"Connected to Kafka: {self.bootstrap_servers}")
        except ImportError:
            logger.warning("kafka-python not installed, Kafka forwarding disabled")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
    
    def disconnect(self):
        """断开连接"""
        if self._producer:
            self._producer.close()
            self._connected = False
    
    def is_connected(self) -> bool:
        return self._connected
    
    def send(self, record: LogRecord) -> bool:
        """发送单条记录"""
        if not self._producer:
            return False
        
        try:
            future = self._producer.send(
                self.topic,
                value=record.to_dict(),
                key=record.hostname.encode('utf-8') if record.hostname else None,
            )
            future.get(timeout=10)
            return True
        except Exception as e:
            logger.error(f"Failed to send log to Kafka: {e}")
            return False
    
    def send_batch(self, records: List[LogRecord]) -> bool:
        """批量发送"""
        if not self._producer or not records:
            return False
        
        try:
            for record in records:
                self._producer.send(
                    self.topic,
                    value=record.to_dict(),
                    key=record.hostname.encode('utf-8') if record.hostname else None,
                )
            self._producer.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to batch send to Kafka: {e}")
            return False


class RedisForwarder(ForwarderBackend):
    """
    Redis转发器
    用于缓存或消息队列
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        key_prefix: str = "logs:",
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.key_prefix = key_prefix
        self._client = None
        self._connected = False
    
    def connect(self):
        """建立连接"""
        try:
            import redis
            
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True,
            )
            
            if self._client.ping():
                self._connected = True
                logger.info(f"Connected to Redis: {self.host}:{self.port}")
        except ImportError:
            logger.warning("redis package not installed, Redis forwarding disabled")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
    
    def disconnect(self):
        """断开连接"""
        if self._client:
            self._client.close()
            self._connected = False
    
    def is_connected(self) -> bool:
        return self._connected
    
    def send(self, record: LogRecord) -> bool:
        """发送单条记录"""
        if not self._client:
            return False
        
        try:
            key = f"{self.key_prefix}{record.timestamp.strftime('%Y%m%d%H%M%S')}"
            self._client.lpush(key, record.to_json())
            self._client.expire(key, 86400)  # 24小时过期
            return True
        except Exception as e:
            logger.error(f"Failed to send log to Redis: {e}")
            return False
    
    def send_batch(self, records: List[LogRecord]) -> bool:
        """批量发送"""
        if not self._client or not records:
            return False
        
        try:
            pipe = self._client.pipeline()
            
            for record in records:
                key = f"{self.key_prefix}{record.timestamp.strftime('%Y%m%d%H%M%S')}"
                pipe.lpush(key, record.to_json())
                pipe.expire(key, 86400)
            
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Failed to batch send to Redis: {e}")
            return False


class LogForwarder:
    """
    日志转发器
    支持多种后端转发
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        batch_size: int = 100,
        flush_interval: int = 5,
    ):
        """
        初始化日志转发器
        
        Args:
            config: 后端配置
            batch_size: 批处理大小
            flush_interval: 刷新间隔（秒）
        """
        self.config = config or {}
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._backends: Dict[ForwarderType, ForwarderBackend] = {}
        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def add_backend(self, backend_type: ForwarderType, backend: ForwarderBackend):
        """添加后端"""
        self._backends[backend_type] = backend
    
    def create_backend(self, backend_type: str, **kwargs) -> ForwarderBackend:
        """创建后端"""
        if backend_type == "elasticsearch":
            return ElasticsearchForwarder(**kwargs)
        elif backend_type == "tdengine":
            return TDengineForwarder(**kwargs)
        elif backend_type == "kafka":
            return KafkaForwarder(**kwargs)
        elif backend_type == "redis":
            return RedisForwarder(**kwargs)
        elif backend_type == "file":
            return FileForwarder(**kwargs)
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
    
    def connect_all(self):
        """连接所有后端"""
        for backend_type, backend in self._backends.items():
            try:
                backend.connect()
            except Exception as e:
                logger.error(f"Failed to connect {backend_type}: {e}")
    
    def disconnect_all(self):
        """断开所有后端"""
        for backend in self._backends.values():
            try:
                backend.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting backend: {e}")
    
    def send(self, record: LogRecord) -> bool:
        """发送日志记录"""
        if not self._backends:
            return False
        
        success = False
        
        for backend in self._backends.values():
            if backend.is_connected():
                try:
                    if backend.send(record):
                        success = True
                except Exception as e:
                    logger.error(f"Error sending to backend: {e}")
        
        return success
    
    def send_async(self, record: LogRecord, callback: Optional[Callable] = None):
        """异步发送"""
        self._queue.put((record, callback))
    
    def _flush_loop(self):
        """刷新循环"""
        import time
        
        while self._running:
            try:
                records = []
                
                # 收集记录
                while len(records) < self.batch_size:
                    try:
                        timeout = max(0.1, self.flush_interval)
                        record, callback = self._queue.get(timeout=timeout)
                        records.append((record, callback))
                    except queue.Empty:
                        break
                
                if records:
                    # 发送到所有后端
                    for backend in self._backends.values():
                        if backend.is_connected():
                            try:
                                backend.send_batch([r for r, _ in records])
                            except Exception as e:
                                logger.error(f"Error batch sending: {e}")
                    
                    # 执行回调
                    for record, callback in records:
                        if callback:
                            try:
                                callback(record)
                            except Exception as e:
                                logger.error(f"Error in callback: {e}")
            
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
            
            time.sleep(0.1)
    
    def start(self):
        """启动转发器"""
        if self._running:
            return
        
        self._running = True
        self.connect_all()
        
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()
        
        logger.info("Log forwarder started")
    
    def stop(self):
        """停止转发器"""
        self._running = False
        
        # 刷新剩余记录
        self.flush()
        
        self._thread.join(timeout=10)
        self.disconnect_all()
        
        logger.info("Log forwarder stopped")
    
    def flush(self):
        """刷新缓冲区"""
        records = []
        
        while not self._queue.empty():
            try:
                record, callback = self._queue.get_nowait()
                records.append((record, callback))
            except queue.Empty:
                break
        
        for backend in self._backends.values():
            if backend.is_connected() and records:
                try:
                    backend.send_batch([r for r, _ in records])
                except Exception as e:
                    logger.error(f"Error flushing: {e}")
