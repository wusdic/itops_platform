"""
操作日志数据库模型
用于记录系统操作日志
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func

from .base import Base


class OperationLog(Base):
    """
    操作日志模型
    记录用户在系统中的操作行为
    """
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 操作信息
    username = Column(String(64), index=True, nullable=False)
    action = Column(String(64), index=True)  # create, update, delete, login, etc.
    resource = Column(String(64), index=True)  # device, workorder, alert, etc.
    resource_id = Column(String(64))  # 操作资源的ID

    # 操作详情
    method = Column(String(16))  # GET, POST, PUT, DELETE
    path = Column(String(256))
    ip_address = Column(String(64))
    user_agent = Column(String(256))

    # 请求和响应
    request_body = Column(Text)  # 请求参数（脱敏）
    response_status = Column(Integer)  # 响应状态码
    error_message = Column(Text)

    # 执行信息
    duration_ms = Column(Integer)  # 执行时长（毫秒）

    # 时间戳
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 索引
    __table_args__ = (
        Index('idx_user_action_time', 'username', 'action', 'timestamp'),
        Index('idx_resource_time', 'resource', 'resource_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<OperationLog(user={self.username}, action={self.action}, resource={self.resource})>"


class BackupRecord(Base):
    """
    备份记录模型
    记录数据库备份信息
    """
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 备份信息
    backup_type = Column(String(32))  # full, incremental, config
    file_name = Column(String(256))
    file_path = Column(String(512))
    file_size = Column(Integer)  # bytes

    # 备份状态
    status = Column(String(32))  # pending, running, completed, failed
    error_message = Column(Text)

    # 备份位置
    storage_type = Column(String(32))  # local, remote
    storage_path = Column(String(512))

    # 操作信息
    created_by = Column(String(64))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<BackupRecord(id={self.id}, type={self.backup_type}, status={self.status})>"


class APIKey(Base):
    """
    API Key模型
    用于API接口认证
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Key信息
    key_id = Column(String(64), unique=True, index=True, nullable=False)  # key标识符
    key_hash = Column(String(256), nullable=False)  # key的hash值
    key_prefix = Column(String(16), nullable=False)  # key的前缀（用于显示）

    # 使用者信息
    name = Column(String(128), nullable=False)  # key名称/描述
    user_id = Column(String(64), index=True)  # 关联用户ID
    username = Column(String(64))  # 用户名

    # 权限范围
    scopes = Column(Text)  # JSON数组，可访问的scope列表

    # 状态
    is_active = Column(Integer, default=1)  # 1=激活, 0=禁用
    is_revoked = Column(Integer, default=0)  # 1=已撤销, 0=正常

    # 有效期
    expires_at = Column(DateTime)  # 过期时间，为空表示永不过期

    # 使用限制
    max_requests = Column(Integer)  # 最大请求数，-1表示无限制
    request_count = Column(Integer, default=0)  # 当前请求计数

    # 速率限制
    rate_limit = Column(Integer, default=100)  # 每分钟请求数限制
    rate_limit_window = Column(Integer, default=60)  # 速率限制时间窗口(秒)

    # 使用记录
    last_used_at = Column(DateTime)  # 最后使用时间
    last_used_ip = Column(String(64))  # 最后使用的IP

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(64))  # 创建者

    # 索引
    __table_args__ = (
        Index('idx_api_key_active', 'is_active', 'is_revoked'),
        Index('idx_api_key_user', 'user_id', 'is_active'),
    )

    def __repr__(self):
        return f"<APIKey(id={self.id}, key_id='{self.key_id}', name='{self.name}')>"

    def is_valid(self) -> bool:
        """检查key是否有效"""
        if self.is_revoked or not self.is_active:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        if self.max_requests > 0 and self.request_count >= self.max_requests:
            return False
        return True
