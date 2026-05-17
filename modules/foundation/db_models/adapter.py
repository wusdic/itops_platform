"""协议适配器数据模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON

from .base import Base


class AdapterTemplate(Base):
    """协议适配器模板"""
    __tablename__ = 'adapter_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    protocol_type = Column(String(32), nullable=False, unique=True, index=True, comment='协议类型 snmp/ssh/mysql...')
    name = Column(String(128), nullable=False, comment='模板名称')
    description = Column(String(512), comment='描述')
    # 默认配置JSON: {host, port, username, password, timeout, ...}
    default_config = Column(JSON, nullable=False, default=dict, comment='默认配置')
    enabled = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'protocol_type': self.protocol_type,
            'name': self.name,
            'description': self.description,
            'default_config': self.default_config or {},
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DeviceProtocolConfig(Base):
    """设备协议配置 - 设备使用的适配器及覆盖参数"""
    __tablename__ = 'device_protocol_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, nullable=False, index=True, comment='设备ID')
    protocol_type = Column(String(32), nullable=False, index=True, comment='协议类型')
    # 使用的适配器模板ID，null表示直接配置不用模板
    adapter_template_id = Column(Integer, comment='适配器模板ID')
    # 覆盖参数，合并到适配器配置上
    overrides = Column(JSON, nullable=False, default=dict, comment='覆盖参数')
    enabled = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        # 同一设备的同一协议类型只能有一条配置
        {'sqlite_autoincrement': True},
    )

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'protocol_type': self.protocol_type,
            'adapter_template_id': self.adapter_template_id,
            'overrides': self.overrides or {},
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
