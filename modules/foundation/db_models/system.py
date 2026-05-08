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
