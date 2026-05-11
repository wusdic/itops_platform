"""
监控指标数据库模型
用于存储设备监控采集的性能指标数据
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Index, Boolean
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


class DeviceMetricConfig(Base):
    """
    设备采集项单项开关配置模型
    
    用于控制设备各监控指标采集项的启用/禁用状态，
    实现精细化的采集控制。
    """
    __tablename__ = "device_metric_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 设备标识
    device_id = Column(Integer, nullable=False, index=True)
    device_name = Column(String(128), index=True)
    
    # 指标类型
    metric_category = Column(String(32), index=True)  # cpu, memory, disk, network, process, service
    metric_name = Column(String(64), index=True)       # cpu_usage, memory_usage, etc.
    
    # 采集开关
    enabled = Column(Boolean, default=True, nullable=False)
    
    # 采集间隔（秒），0表示使用默认间隔
    collect_interval = Column(Integer, default=0)
    
    # 告警阈值配置（JSON格式）
    alert_thresholds = Column(Text)  # JSON: {"max": 90, "min": 10}
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(64))
    updated_by = Column(String(64))
    
    # 备注
    remark = Column(Text)
    
    # 索引
    __table_args__ = (
        Index('idx_device_metric_config', 'device_id', 'metric_category', 'metric_name', unique=True),
    )
    
    def __repr__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"<DeviceMetricConfig(device={self.device_name}, metric={self.metric_name}, status={status})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'metric_category': self.metric_category,
            'metric_name': self.metric_name,
            'enabled': self.enabled,
            'collect_interval': self.collect_interval,
            'alert_thresholds': self.alert_thresholds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'remark': self.remark,
        }
