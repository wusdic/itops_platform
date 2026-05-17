# -*- coding: utf-8 -*-
"""Kafka Collector for monitoring Kafka brokers via kafka-python."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from kafka import KafkaConsumer, KafkaProducer, KafkaAdminClient
    from kafka.protocol.admin import DescribeGroupsRequest, ListGroupsRequest
    from kafka.protocol.offset import OffsetRequest, OffsetResetStrategy
    from kafka.cluster import KafkaCluster
except ImportError:
    KafkaConsumer = None
    KafkaProducer = None
    KafkaAdminClient = None


@dataclass
class KafkaConfig:
    """Configuration for Kafka collector."""
    bootstrap_servers: str = "localhost:9092"
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_plain_username: Optional[str] = None
    sasl_plain_password: Optional[str] = None
    ssl_check_hostname: bool = False
    request_timeout_ms: int = 10000
    consumer_group: Optional[str] = None

    def build_admin_client(self) -> "KafkaAdminClient":
        if KafkaAdminClient is None:
            raise ImportError("kafka-python package is required: pip install kafka-python")
        return KafkaAdminClient(
            bootstrap_servers=self.bootstrap_servers,
            security_protocol=self.security_protocol,
            sasl_mechanism=self.sasl_mechanism,
            sasl_plain_username=self.sasl_plain_username,
            sasl_plain_password=self.sasl_plain_password,
            ssl_check_hostname=self.ssl_check_hostname,
            request_timeout_ms=self.request_timeout_ms,
        )


class KafkaCollector:
    """Collector for Kafka metrics."""

    def __init__(self, config: Optional[KafkaConfig] = None) -> None:
        self.config = config or KafkaConfig()
        self._admin_client: Optional["KafkaAdminClient"] = None

    @property
    def admin_client(self) -> "KafkaAdminClient":
        if self._admin_client is None:
            self._admin_client = self.config.build_admin_client()
        return self._admin_client

    def collect_brokers(self) -> List[Dict[str, Any]]:
        """Collect broker information."""
        cluster = self.admin_client._client
        brokers = []
        for broker_id, node in cluster._brokers.items():
            brokers.append({
                "broker_id": broker_id,
                "host": node.host,
                "port": node.port,
                "rack": getattr(node, "rack", None),
            })
        return brokers

    def collect_topics(self) -> List[Dict[str, Any]]:
        """Collect topic and partition information."""
        topics_metadata = self.admin_client._client.cluster.topics()
        topic_summaries = []
        for topic in topics_metadata:
            try:
                partitions = self.admin_client._client.cluster.partitions_for_topic(topic)
                topic_summaries.append({
                    "topic": topic,
                    "partition_count": len(partitions) if partitions else 0,
                    "partitions": partitions,
                })
            except Exception:
                topic_summaries.append({
                    "topic": topic,
                    "partition_count": 0,
                    "partitions": [],
                })
        return topic_summaries

    def collect_consumer_groups(self) -> List[Dict[str, Any]]:
        """Collect consumer group lag and offsets."""
        groups = []
        try:
            for group in self.admin_client._client.cluster.consumer_groups.keys():
                try:
                    group_info = self.admin_client.describe_consumer_groups([group])
                    groups.append({
                        "group": group,
                        "state": group_info[0].state if group_info else "unknown",
                    })
                except Exception:
                    groups.append({"group": group, "state": "unknown"})
        except Exception:
            pass
        return groups

    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all available Kafka metrics."""
        metrics = {
            "timestamp": int(time.time()),
            "bootstrap_servers": self.config.bootstrap_servers,
        }

        try:
            metrics["brokers"] = self.collect_brokers()
            metrics["broker_count"] = len(metrics["brokers"])
        except Exception as e:
            metrics["brokers_error"] = str(e)

        try:
            metrics["topics"] = self.collect_topics()
            metrics["topic_count"] = len(metrics["topics"])
        except Exception as e:
            metrics["topics_error"] = str(e)

        try:
            metrics["consumer_groups"] = self.collect_consumer_groups()
            metrics["consumer_group_count"] = len(metrics["consumer_groups"])
        except Exception as e:
            metrics["consumer_groups_error"] = str(e)

        return metrics

    def close(self):
        """关闭 Kafka 连接"""
        if self._client:
            self._client.close()
            self._client = None
