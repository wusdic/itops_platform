"""
设备模型定义
包含服务器、网络设备、安全设备、存储设备等
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, Float, Boolean
from sqlalchemy.orm import relationship

from .base import Base


class DeviceType(str, Enum):
    """设备类型枚举"""
    # 服务器类
    SERVER_WINDOWS = 'server_windows'    # Windows服务器
    SERVER_LINUX = 'server_linux'        # Linux服务器
    SERVER_VMWARE = 'server_vmware'      # VMware虚拟机
    SERVER_HYPERV = 'server_hyperv'      # Hyper-V虚拟机
    SERVER_KVM = 'server_kvm'            # KVM虚拟机
    
    # 网络设备类
    NETWORK_SWITCH = 'network_switch'    # 交换机
    NETWORK_ROUTER = 'network_router'    # 路由器
    NETWORK_FIREWALL = 'network_firewall'# 防火墙
    NETWORK_WAF = 'network_waf'          # WAF
    NETWORK_LB = 'network_loadbalancer'  # 负载均衡
    NETWORK_VPN = 'network_vpn'          # VPN网关
    NETWORK_AP = 'network_ap'            # 无线AP
    NETWORK_AC = 'network_ac'            # 无线控制器
    
    # 安全设备类
    SECURITY_IDS = 'security_ids'        # 入侵检测
    SECURITY_IPS = 'security_ips'        # 入侵防御
    SECURITY_AMS = 'security_antivirus'  # 杀毒软件服务器
    
    # 存储设备类
    STORAGE_ARRAY = 'storage_array'      # 存储阵列
    STORAGE_NAS = 'storage_nas'          # NAS存储
    STORAGE_TAPE = 'storage_tape'        # 磁带库
    
    # 其他
    OTHER = 'other'                      # 其他设备


class DeviceStatus(str, Enum):
    """设备状态枚举"""
    ONLINE = 'online'          # 正常
    OFFLINE = 'offline'        # 离线
    WARNING = 'warning'        # 警告
    CRITICAL = 'critical'      # 严重
    MAINTENANCE = 'maintenance'# 维护中
    UNKNOWN = 'unknown'        # 未知


class Device(Base):
    """
    设备模型
    
    包含所有IT资产的基类，包括服务器、网络设备、安全设备、存储设备等
    """
    __tablename__ = 'devices'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基本信息
    name = Column(String(128), nullable=False, index=True, comment='设备名称')
    hostname = Column(String(128), unique=True, comment='主机名')
    ip_address = Column(String(64), index=True, comment='IP地址')
    mac_address = Column(String(64), comment='MAC地址')
    device_type = Column(SQLEnum(DeviceType), nullable=False, index=True, comment='设备类型')
    
    # 位置信息
    location = Column(String(256), comment='位置')
    idc = Column(String(128), comment='机房')
    rack = Column(String(64), comment='机柜')
    rack_position = Column(String(32), comment='机柜位置')
    
    # 厂商信息
    vendor = Column(String(128), comment='厂商')
    model = Column(String(128), comment='型号')
    serial_number = Column(String(128), comment='序列号')
    
    # 采购信息
    purchase_date = Column(DateTime, comment='采购日期')
    warranty_end = Column(DateTime, comment='保修结束日期')
    cost = Column(Float, comment='成本')
    
    # 状态
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.UNKNOWN, comment='状态')
    
    # 监控配置
    snmp_enabled = Column(Boolean, default=True, comment='是否启用SNMP')
    snmp_community = Column(String(64), comment='SNMP Community')
    snmp_version = Column(String(16), default='v2c', comment='SNMP版本')
    monitor_enabled = Column(Boolean, default=True, comment='是否启用监控')
    
    # 管理信息
    ssh_port = Column(Integer, default=22, comment='SSH端口')
    ssh_username = Column(String(64), comment='SSH用户名')
    ssh_password_encrypted = Column(String(256), comment='SSH密码(加密)')
    ssh_key_path = Column(String(256), comment='SSH密钥路径')
    
    # Web管理界面
    web_url = Column(String(256), comment='Web管理URL')
    web_username = Column(String(64), comment='Web用户名')
    web_password_encrypted = Column(String(256), comment='Web密码(加密)')
    
    # 配置信息（JSON格式）
    config = Column(Text, comment='配置信息JSON')
    
    # 标签/分组
    tags = Column(String(256), comment='标签，逗号分隔')
    group_id = Column(Integer, comment='设备组ID')
    
    # 业务关联
    business_id = Column(Integer, comment='业务系统ID')
    business_name = Column(String(128), comment='业务系统名称')
    
    # 责任人
    owner = Column(String(64), comment='责任人')
    owner_email = Column(String(128), comment='责任人邮箱')
    
    # 备注
    remark = Column(Text, comment='备注')
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    created_by = Column(String(64), comment='创建人')
    updated_by = Column(String(64), comment='更新人')
    
    # 关系
    # metrics = relationship('DeviceMetric', back_populates='device', lazy='dynamic')
    # alerts = relationship('Alert', back_populates='device', lazy='dynamic')
    
    def __repr__(self):
        return f"<Device(id={self.id}, name='{self.name}', ip='{self.ip_address}', type='{self.device_type.value}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'device_type': self.device_type.value if self.device_type else None,
            'location': self.location,
            'idc': self.idc,
            'rack': self.rack,
            'rack_position': self.rack_position,
            'vendor': self.vendor,
            'model': self.model,
            'serial_number': self.serial_number,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'warranty_end': self.warranty_end.isoformat() if self.warranty_end else None,
            'status': self.status.value if self.status else None,
            'owner': self.owner,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DeviceGroup(Base):
    """设备分组模型"""
    __tablename__ = 'device_groups'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True, comment='分组名称')
    parent_id = Column(Integer, comment='父分组ID')
    description = Column(String(256), comment='描述')
    
    # 权限控制
    is_public = Column(Boolean, default=True, comment='是否公开')
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<DeviceGroup(id={self.id}, name='{self.name}')>"


class BusinessSystem(Base):
    """业务系统模型"""
    __tablename__ = 'business_systems'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True, comment='系统名称')
    code = Column(String(64), unique=True, comment='系统代码')
    description = Column(String(512), comment='描述')
    
    # SLA配置
    sla_level = Column(String(32), comment='SLA级别')
    availability_target = Column(Float, default=99.9, comment='可用性目标(%)')
    
    # 负责人
    owner = Column(String(64), comment='负责人')
    owner_email = Column(String(128), comment='负责人邮箱')
    
    # 状态
    status = Column(String(32), default='active', comment='状态')
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<BusinessSystem(id={self.id}, name='{self.name}')>"