# -*- coding: utf-8 -*-
"""Redis Collector for monitoring Redis instances."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import redis
except ImportError:
    redis = None


@dataclass
class RedisConfig:
    """Configuration for Redis collector."""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    connection_pool_max_connections: int = 10

    def build_client(self) -> "redis.Redis":
        if redis is None:
            raise ImportError("redis package is required: pip install redis")
        pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            max_connections=self.connection_pool_max_connections,
        )
        return redis.Redis(connection_pool=pool)


class RedisCollector:
    """Collector for Redis metrics."""

    def __init__(self, config: Optional[RedisConfig] = None) -> None:
        self.config = config or RedisConfig()
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = self.config.build_client()
        return self._client

    def collect_info(self) -> Dict[str, Any]:
        """Collect Redis INFO output."""
        return self.client.info()

    def collect_commandstats(self) -> Dict[str, Any]:
        """Collect Redis command statistics."""
        return self.client.info("commandstats")

    def collect_slowlog(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Collect Redis slowlog entries."""
        return self.client.slowlog_get(limit)

    def collect_replication(self) -> Dict[str, Any]:
        """Collect Redis replication info."""
        return self.client.info("replication")

    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all available Redis metrics."""
        metrics = {
            "timestamp": int(time.time()),
            "host": self.config.host,
            "port": self.config.port,
        }

        try:
            info = self.collect_info()
            metrics["memory_used"] = info.get("used_memory_human", "0")
            metrics["memory_peak"] = info.get("used_memory_peak_human", "0")
            metrics["connected_clients"] = info.get("connected_clients", 0)
            metrics["blocked_clients"] = info.get("blocked_clients", 0)
            metrics["total_connections_received"] = info.get("total_connections_received", 0)
            metrics["total_commands_processed"] = info.get("total_commands_processed", 0)
            metrics["instantaneous_ops_per_sec"] = info.get("instantaneous_ops_per_sec", 0)
            metrics["keyspace_hits"] = info.get("keyspace_hits", 0)
            metrics["keyspace_misses"] = info.get("keyspace_misses", 0)
            metrics["uptime_seconds"] = info.get("uptime_in_seconds", 0)
            metrics["redis_version"] = info.get("redis_version", "unknown")
        except Exception as e:
            metrics["info_error"] = str(e)

        try:
            metrics["commandstats"] = self.collect_commandstats()
        except Exception as e:
            metrics["commandstats_error"] = str(e)

        try:
            metrics["slowlog"] = self.collect_slowlog()
        except Exception as e:
            metrics["slowlog_error"] = str(e)

        try:
            replication = self.collect_replication()
            metrics["replication"] = replication
            metrics["role"] = replication.get("role", "unknown")
            metrics["connected_slaves"] = replication.get("connected_slaves", 0)
        except Exception as e:
            metrics["replication_error"] = str(e)

        return metrics
