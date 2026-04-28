"""
SM-01: TDengine时序数据库客户端

TDengine是一个专为物联网场景设计的时序数据库，本模块提供：
- 连接管理（REST API和原生连接）
- 超级表操作
- 数据写入（insert/update）
- 数据查询（时间范围查询/降采样聚合）
- 数据订阅

配置参数：
    host: TDengine服务地址
    port: 端口号（默认6041）
    username: 用户名
    password: 密码
    database: 默认数据库
    timezone: 时区设置
"""

from .client import TDengineClient

__all__ = ['TDengineClient']
__version__ = '1.0.0'
