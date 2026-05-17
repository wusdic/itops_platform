# -*- coding: utf-8 -*-
"""RabbitMQ Collector for monitoring RabbitMQ instances via HTTP API."""

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None


@dataclass
class RabbitMQConfig:
    """Configuration for RabbitMQ collector."""
    host: str = "localhost"
    port: int = 15672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    timeout: int = 10

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/api"

    @property
    def auth(self) -> tuple:
        return (self.username, self.password)


class RabbitMQCollector:
    """Collector for RabbitMQ metrics via Management HTTP API."""

    def __init__(self, config: Optional[RabbitMQConfig] = None) -> None:
        self.config = config or RabbitMQConfig()
        self._session: Optional["requests.Session"] = None

    @property
    def session(self) -> "requests.Session":
        if requests is None:
            raise ImportError("requests package is required: pip install requests")
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = self.config.auth
            self._session.headers.update({"Content-Type": "application/json"})
        return self._session

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.config.base_url}{path}"
        resp = self.session.get(url, timeout=self.config.timeout)
        resp.raise_for_status()
        return resp.json()

    def collect_overview(self) -> Dict[str, Any]:
        """Collect RabbitMQ overview/messaging metrics."""
        return self._get("/overview")

    def collect_queues(self) -> List[Dict[str, Any]]:
        """Collect queue statistics."""
        return self._get("/queues")

    def collect_nodes(self) -> List[Dict[str, Any]]:
        """Collect node statistics."""
        return self._get("/nodes")

    def collect_connections(self) -> List[Dict[str, Any]]:
        """Collect connection statistics."""
        return self._get("/connections")

    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all available RabbitMQ metrics."""
        metrics = {
            "timestamp": int(time.time()),
            "host": self.config.host,
            "port": self.config.port,
        }

        try:
            overview = self.collect_overview()
            metrics["rabbitmq_version"] = overview.get("rabbitmq_version", "unknown")
            metrics["erlang_version"] = overview.get("erlang_version", "unknown")
            mq_overview = overview.get("message_stats", {})
            metrics["messages_ready"] = overview.get("queue_totals", {}).get("messages_ready", 0)
            metrics["messages_unacked"] = overview.get("queue_totals", {}).get("messages_unacked", 0)
            metrics["message_stats"] = mq_overview
        except Exception as e:
            metrics["overview_error"] = str(e)

        try:
            queues = self.collect_queues()
            metrics["queue_count"] = len(queues)
            queue_summaries = []
            for q in queues:
                queue_summaries.append({
                    "name": q.get("name"),
                    "vhost": q.get("vhost"),
                    "messages": q.get("messages", 0),
                    "consumers": q.get("consumers", 0),
                    "memory": q.get("memory", 0),
                })
            metrics["queues"] = queue_summaries
        except Exception as e:
            metrics["queues_error"] = str(e)

        try:
            nodes = self.collect_nodes()
            metrics["node_count"] = len(nodes)
            node_summaries = []
            for n in nodes:
                node_summaries.append({
                    "name": n.get("name"),
                    "type": n.get("type"),
                    "running": n.get("running", False),
                    "mem_used": n.get("mem_used", 0),
                    "mem_limit": n.get("mem_limit", 0),
                    "fd_used": n.get("fd_used", 0),
                    "fd_limit": n.get("fd_limit", 0),
                    "sockets_used": n.get("sockets_used", 0),
                    "sockets_limit": n.get("sockets_limit", 0),
                })
            metrics["nodes"] = node_summaries
        except Exception as e:
            metrics["nodes_error"] = str(e)

        try:
            connections = self.collect_connections()
            metrics["connection_count"] = len(connections)
            conn_summaries = []
            for c in connections:
                conn_summaries.append({
                    "name": c.get("name"),
                    "host": c.get("peer_host"),
                    "port": c.get("peer_port"),
                    "channels": c.get("channels", 0),
                    "frame_size": c.get("frame_max", 0),
                })
            metrics["connections"] = conn_summaries
        except Exception as e:
            metrics["connections_error"] = str(e)

        return metrics
