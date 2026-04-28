"""
SM-01: InfluxDB时序数据库客户端

InfluxDB是一个高性能的时序数据库，支持InfluxQL和Flux查询语言，本模块提供：
- 连接管理
- 行协议数据写入
- Flux/InfluxQL查询
- 数据管理

配置参数：
    url: InfluxDB服务地址
    token: 认证令牌
    org: 组织名称
    bucket: 存储桶
    timeout: 超时时间
"""

from .client import InfluxDBClient

__all__ = ['InfluxDBClient']
__version__ = '1.0.0'
