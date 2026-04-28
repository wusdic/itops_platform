"""
SM-04: Redis缓存管理客户端

Redis是一个高性能的键值存储系统，支持多种数据结构。本模块提供：
- 字符串/哈希/列表/集合/有序集合操作
- 键管理
- 过期时间设置
- 发布订阅
- 分布式锁

配置参数：
    host: Redis服务地址
    port: 端口号（默认6379）
    password: 密码（可选）
    db: 数据库编号
    ssl: 是否使用SSL
"""

from .client import RedisClient

__all__ = ['RedisClient']
__version__ = '1.0.0'
