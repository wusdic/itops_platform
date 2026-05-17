"""
Elasticsearch Collector for IT Operations Platform
Collects cluster health, node stats, index stats, and performance metrics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class ElasticsearchConfig:
    """Configuration for Elasticsearch connection."""
    hosts: List[str] = field(default_factory=lambda: ["http://localhost:9200"])
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    retry_on_timeout: bool = True
    max_retries: int = 3
    verify_certs: bool = False
    index_pattern: str = "*"
    shard_stats_enabled: bool = True


class ElasticsearchCollector:
    """
    Collector for Elasticsearch metrics.
    Collects cluster health, node stats, index stats, and performance metrics.
    """

    def __init__(self, config: Optional[ElasticsearchConfig] = None):
        self.config = config or ElasticsearchConfig()
        self._client = None

    def _get_client(self):
        """Lazy initialization of Elasticsearch client."""
        if self._client is None:
            try:
                from elasticsearch import Elasticsearch
                self._client = Elasticsearch(
                    hosts=self.config.hosts,
                    basic_auth=(self.config.username, self.config.password) if self.config.username else None,
                    timeout=self.config.timeout,
                    retry_on_timeout=self.config.retry_on_timeout,
                    max_retries=self.config.max_retries,
                    verify_certs=self.config.verify_certs,
                )
            except ImportError:
                # Fallback for older elasticsearch-py versions
                from elasticsearch import Elasticsearch
                self._client = Elasticsearch(
                    hosts=self.config.hosts,
                    http_auth=(self.config.username, self.config.password) if self.config.username else None,
                    timeout=self.config.timeout,
                    retry_on_timeout=self.config.retry_on_timeout,
                    max_retries=self.config.max_retries,
                    verify_certs=self.config.verify_certs,
                )
        return self._client

    def collect_cluster_health(self) -> Dict[str, Any]:
        """
        Collect cluster health status.
        Returns: cluster_name, status, number_of_nodes, active_shards, etc.
        """
        try:
            client = self._get_client()
            health = client.cluster.health()
            return {
                "timestamp": datetime.now().isoformat(),
                "cluster_name": health.get("cluster_name"),
                "status": health.get("status"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_shards": health.get("active_shards"),
                "active_primary_shards": health.get("active_primary_shards"),
                "relocating_shards": health.get("relocating_shards"),
                "initializing_shards": health.get("initializing_shards"),
                "unassigned_shards": health.get("unassigned_shards"),
                "delayed_unassigned_shards": health.get("delayed_unassigned_shards"),
                "number_of_pending_tasks": health.get("number_of_pending_tasks"),
                "active_shards_percent_as_number": health.get("active_shards_percent_as_number"),
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def collect_cluster_stats(self) -> Dict[str, Any]:
        """
        Collect cluster-level statistics.
        Returns: indices count, shards, storage, memory usage.
        """
        try:
            client = self._get_client()
            stats = client.cluster.stats()
            
            nodes_stats = stats.get("nodes", {})
            indices_stats = stats.get("indices", {})
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cluster_name": stats.get("cluster_name"),
                "status": stats.get("status"),
                "number_of_nodes": stats.get("_nodes", {}).get("total"),
                "indices": {
                    "count": indices_stats.get("count", {}).get("total"),
                    "docs_count": indices_stats.get("docs", {}).get("count"),
                    "docs_deleted": indices_stats.get("docs", {}).get("deleted"),
                    "store_size_bytes": indices_stats.get("store", {}).get("size_in_bytes"),
                    "primary_store_size_bytes": indices_stats.get("store", {}).get("primary_size_in_bytes"),
                },
                "shards": {
                    "total": indices_stats.get("shards", {}).get("total"),
                    "primary": indices_stats.get("shards", {}).get("primaries"),
                    "replication": indices_stats.get("shards", {}).get("replication"),
                },
                "memory": {
                    "used_bytes": nodes_stats.get("jvm", {}).get("mem", {}).get("heap_used_in_bytes"),
                    "max_bytes": nodes_stats.get("jvm", {}).get("mem", {}).get("heap_max_in_bytes"),
                    "percent_used": nodes_stats.get("jvm", {}).get("mem", {}).get("heap_used_percent"),
                },
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def collect_node_stats(self) -> Dict[str, Any]:
        """
        Collect per-node statistics.
        Returns: node name, roles, CPU, memory, JVM, thread pools, FS.
        """
        try:
            client = self._get_client()
            stats = client.nodes.stats()
            
            nodes_data = {}
            for node_id, node_info in stats.get("nodes", {}).items():
                nodes_data[node_id] = {
                    "name": node_info.get("name"),
                    "roles": node_info.get("roles", []),
                    "ip": node_info.get("ip"),
                    "transport_address": node_info.get("transport_address"),
                    "cpu": {
                        "percent": node_info.get("cpu", {}).get("percent"),
                    },
                    "memory": {
                        "used_bytes": node_info.get("memory", {}).get("used_in_bytes"),
                        "max_bytes": node_info.get("memory", {}).get("max_in_bytes"),
                        "percent_used": node_info.get("memory", {}).get("percent"),
                    },
                    "jvm": {
                        "heap_used_bytes": node_info.get("jvm", {}).get("mem", {}).get("heap_used_in_bytes"),
                        "heap_max_bytes": node_info.get("jvm", {}).get("mem", {}).get("heap_max_in_bytes"),
                        "heap_percent": node_info.get("jvm", {}).get("mem", {}).get("heap_used_percent"),
                        "gc_collections": node_info.get("jvm", {}).get("gc", {}).get("collection_count"),
                        "gc_time_millis": node_info.get("jvm", {}).get("gc", {}).get("collection_time_in_millis"),
                    },
                    "thread_pools": {
                        name: {
                            "threads": info.get("threads"),
                            "queue": info.get("queue"),
                            "active": info.get("active"),
                            "rejected": info.get("rejected"),
                            "completed": info.get("completed"),
                        }
                        for name, info in node_info.get("thread_pool", {}).items()
                    },
                    "fs": {
                        "total_bytes": node_info.get("fs", {}).get("total", {}).get("total_in_bytes"),
                        "free_bytes": node_info.get("fs", {}).get("total", {}).get("free_in_bytes"),
                        "available_bytes": node_info.get("fs", {}).get("total", {}).get("available_in_bytes"),
                    },
                    "search_latency": self._get_node_search_latency(node_id),
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "nodes": nodes_data,
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _get_node_search_latency(self, node_id: str) -> Dict[str, float]:
        """Get search latency metrics for a specific node."""
        try:
            client = self._get_client()
            # Use indices stats with breakdown by node
            stats = client.indices.stats(level="shards")
            
            search_latency = {"avg_latency_ms": 0.0, "search_total": 0}
            for index_name, index_data in stats.get("indices", {}).items():
                primaries = index_data.get("primaries", {})
                search_stats = primaries.get("search", {})
                total_time = search_stats.get("query_time_in_millis", 0)
                total_count = search_stats.get("query_count", 1)
                if total_count > 0:
                    search_latency["avg_latency_ms"] += (total_time / total_count)
                search_latency["search_total"] += total_count
            
            return search_latency
        except Exception:
            return {"avg_latency_ms": 0.0, "search_total": 0}

    def collect_index_stats(self) -> Dict[str, Any]:
        """
        Collect index-level statistics.
        Returns: index name, docs, size, shards, health, search latency.
        """
        try:
            client = self._get_client()
            
            # Get index stats
            index_stats = client.indices.stats()
            
            # Get cluster health for index-level shard info
            health = client.cluster.health()
            
            indices_data = {}
            for index_name, index_info in index_stats.get("indices", {}).items():
                primaries = index_info.get("primaries", {})
                
                indices_data[index_name] = {
                    "docs_count": primaries.get("docs", {}).get("count"),
                    "docs_deleted": primaries.get("docs", {}).get("deleted"),
                    "store_size_bytes": primaries.get("store", {}).get("size_in_bytes"),
                    "index_creation_date": primaries.get("creation_date"),
                    "shards": {
                        "primary": primaries.get("shard_stats", {}).get("total_count", 0),
                    },
                    "search": {
                        "query_count": primaries.get("search", {}).get("query_count", 0),
                        "query_time_ms": primaries.get("search", {}).get("query_time_in_millis", 0),
                        "fetch_count": primaries.get("search", {}).get("fetch_count", 0),
                        "fetch_time_ms": primaries.get("search", {}).get("fetch_time_in_millis", 0),
                    },
                    "indexing": {
                        "index_count": primaries.get("indexing", {}).get("index_count", 0),
                        "index_time_ms": primaries.get("indexing", {}).get("index_time_in_millis", 0),
                        "delete_count": primaries.get("indexing", {}).get("delete_count", 0),
                    },
                    "merges": {
                        "current": primaries.get("merges", {}).get("current"),
                        "total_count": primaries.get("merges", {}).get("total"),
                        "total_time_ms": primaries.get("merges", {}).get("total_time_in_millis"),
                    },
                    "refresh": {
                        "total_count": primaries.get("refresh", {}).get("total"),
                        " total_time_ms": primaries.get("refresh", {}).get("total_time_in_millis"),
                    },
                    "flush": {
                        "total_count": primaries.get("flush", {}).get("total"),
                        "total_time_ms": primaries.get("flush", {}).get("total_time_in_millis"),
                    },
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "indices": indices_data,
                "total_indices": len(indices_data),
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all Elasticsearch metrics.
        Returns: combined cluster health, stats, node stats, and index stats.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "cluster_health": self.collect_cluster_health(),
            "cluster_stats": self.collect_cluster_stats(),
            "node_stats": self.collect_node_stats(),
            "index_stats": self.collect_index_stats(),
        }

    def close(self):
        """Close the Elasticsearch client connection."""
        if self._client:
            self._client.close()
            self._client = None
