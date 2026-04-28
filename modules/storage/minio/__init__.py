"""
SM-03: MinIO对象存储客户端

MinIO是一个高性能的分布式对象存储系统，兼容S3协议。本模块提供：
- 存储桶管理
- 文件上传/下载/删除
- 预签名URL生成
- 批量操作

配置参数：
    endpoint: MinIO服务地址
    access_key: 访问密钥
    secret_key: 秘密密钥
    secure: 是否使用HTTPS
    bucket: 默认存储桶
"""

from .client import MinIOClient

__all__ = ['MinIOClient']
__version__ = '1.0.0'
