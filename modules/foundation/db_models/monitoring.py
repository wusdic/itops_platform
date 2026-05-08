"""
监控指标数据库模型
用于存储设备监控采集的性能指标数据
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Index
from sqlalchemy.sql import func

from .base import Base


class PerformanceMetric(Base):
    """
    设备性能指标模型
    存储设备采集的性能指标数据，支持时序查询
    """
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 设备标识
    device_id = Column(Integer, nullable=False, index=True)
    device_name = Column(String(128), index=True)
    device_ip = Column(String(64), index=True)
    device_type = Column(String(64))

    # 指标类型
    metric_category = Column(String(32), index=True)  # cpu, memory, disk, network, process, service
    metric_name = Column(String(64), index=True)       # cpu_usage, memory_usage, etc.
    metric_unit = Column(String(16))                     # %, MB, GB, B/s

    # 指标值
    value = Column(Float, nullable=False)
    value_str = Column(String(256))                     # 字符串形式的值，用于特殊格式

    # 标签/维度 (JSON格式)
    tags = Column(Text)  # JSON: {"interface": "eth0", "mount_point": "/"}

    # 元数据
    timestamp = Column(DateTime, nullable=False, index=True)
    collected_by = Column(String(64))
    source = Column(String(32))  # ssh, snmp, api, agent

    # 索引
    __table_args__ = (
        Index('idx_device_metric_time', 'device_id', 'metric_name', 'timestamp'),
        Index('idx_metric_time', 'metric_category', 'metric_name', 'timestamp'),
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PerformanceMetric(device={self.device_name}, metric={self.metric_name}, value={self.value})>"
