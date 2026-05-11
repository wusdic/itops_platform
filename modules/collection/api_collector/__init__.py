"""
CM-02: API采集模块

提供通用的API数据采集能力，包括：
- 基础HTTP客户端（支持认证、重试、超时）
- Zabbix API集成
- Prometheus API集成
- Kubernetes API集成

配置参数化设计，支持多种认证方式和数据格式。
"""

from .http_client import HTTPClient
from .zabbix_client import ZabbixClient
from .prometheus_client import PrometheusClient
from .kubernetes_client import K8sClient

__all__ = ['HTTPClient', 'ZabbixClient', 'PrometheusClient', 'K8sClient']
__version__ = '1.1.0'
