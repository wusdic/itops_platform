"""
SM-02: Qdrant向量数据库客户端

Qdrant是一个高性能的向量相似度搜索引擎，支持：
- 向量存储和检索
- 近似最近邻搜索(ANN)
- 多种距离度量（余弦/欧氏/点积）
- 分组和过滤查询
- 负载均衡和分布式部署

配置参数：
    host: Qdrant服务地址
    port: 端口号（默认6333）
    api_key: API密钥（可选）
    timeout: 超时时间
    https: 是否使用HTTPS
"""

from .client import QdrantClient

__all__ = ['QdrantClient']
__version__ = '1.0.0'
