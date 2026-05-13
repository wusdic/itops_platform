"""
巡检任务和结果数据模型
包含设备巡检任务、检查项和巡检结果
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, Enum as SQLEnum, ForeignKey, Float
from sqlalchemy.orm import relationship

from .base import Base


class InspectionStatus(str):
    """巡检状态"""
    PENDING = "pending"           # 待执行
    RUNNING = "running"          # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"      # 已取消


class InspectionTask(Base):
    """巡检任务模型"""
    __tablename__ = "inspection_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_no = Column(String(50), unique=True, nullable=False, comment="巡检任务编号")
    name = Column(String(200), nullable=False, comment="巡检任务名称")
    description = Column(Text, nullable=True, comment="任务描述")
    
    # 巡检类型
    inspection_type = Column(String(50), default="routine", comment="巡检类型: routine常规/maintenance维护/emergency应急")
    
    # 巡检范围
    target_type = Column(String(50), default="device", comment="巡检对象类型: device设备/group分组/all全部")
    target_ids = Column(JSON, nullable=True, comment="巡检对象ID列表")
    
    # 巡检配置
    config = Column(JSON, nullable=True, comment="巡检配置项")
    
    # 巡检项模板
    check_items = Column(JSON, nullable=True, comment="巡检项定义(JSON)")
    
    # 执行配置
    schedule_type = Column(String(20), default="manual", comment="调度类型: manual手动/scheduled定时/auto自动")
    cron_expression = Column(String(100), nullable=True, comment="Cron表达式(定时任务)")
    
    # 状态和进度
    status = Column(String(20), default=InspectionStatus.PENDING, comment="任务状态")
    progress = Column(Float, default=0.0, comment="完成进度(0-100)")
    total_items = Column(Integer, default=0, comment="总检查项数")
    completed_items = Column(Integer, default=0, comment="已完成检查项数")
    
    # 执行信息
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    executor = Column(String(100), nullable=True, comment="执行人")
    
    # 结果摘要
    total_devices = Column(Integer, default=0, comment="巡检设备数")
    healthy_devices = Column(Integer, default=0, comment="健康设备数")
    warning_devices = Column(Integer, default=0, comment="警告设备数")
    critical_devices = Column(Integer, default=0, comment="危险设备数")
    offline_devices = Column(Integer, default=0, comment="离线设备数")
    
    # 健康度评分 (0-100)
    health_score = Column(Float, nullable=True, comment="整体健康度评分")
    
    # 报告信息
    report_id = Column(Integer, nullable=True, comment="生成的报告ID")
    report_path = Column(String(500), nullable=True, comment="报告文件路径")
    
    # 审计字段
    created_by = Column(String(100), nullable=True, comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(100), nullable=True, comment="更新人")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<InspectionTask(id={self.id}, task_no='{self.task_no}', status='{self.status}')>"


class InspectionResult(Base):
    """巡检结果模型"""
    __tablename__ = "inspection_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("inspection_tasks.id"), nullable=False, comment="所属任务ID")
    
    # 设备信息
    device_id = Column(Integer, nullable=True, comment="设备ID")
    device_name = Column(String(128), nullable=True, comment="设备名称")
    device_ip = Column(String(64), nullable=True, comment="设备IP")
    device_type = Column(String(50), nullable=True, comment="设备类型")
    
    # 巡检项结果
    check_item_id = Column(String(100), nullable=True, comment="检查项ID")
    check_item_name = Column(String(200), nullable=True, comment="检查项名称")
    check_category = Column(String(100), nullable=True, comment="检查项分类")
    
    # 检查结果
    status = Column(String(20), default="pending", comment="检查状态: pending/running/ok/warning/critical/error")
    result_value = Column(String(500), nullable=True, comment="检查结果值")
    result_message = Column(Text, nullable=True, comment="检查结果消息")
    expected_value = Column(String(200), nullable=True, comment="期望值")
    
    # 严重程度
    severity = Column(String(20), default="info", comment="严重程度: info/warning/critical")
    
    # 建议措施
    suggestion = Column(Text, nullable=True, comment="建议措施")
    
    # 时间戳
    checked_at = Column(DateTime, nullable=True, comment="检查时间")
    
    # 附加数据
    raw_data = Column(JSON, nullable=True, comment="原始检查数据")
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    def __repr__(self):
        return f"<InspectionResult(id={self.id}, task_id={self.task_id}, device='{self.device_name}', status='{self.status}')>"


class InspectionCheckItem(Base):
    """巡检检查项模板"""
    __tablename__ = "inspection_check_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="检查项名称")
    category = Column(String(100), nullable=True, comment="检查项分类")
    description = Column(Text, nullable=True, comment="检查项描述")
    
    # 检查配置
    check_type = Column(String(50), nullable=False, comment="检查类型: snmp/ssh/api/metric/log")
    check_script = Column(Text, nullable=True, comment="检查脚本")
    check_command = Column(String(500), nullable=True, comment="检查命令")
    check_params = Column(JSON, nullable=True, comment="检查参数")
    
    # 阈值配置
    warning_threshold = Column(String(200), nullable=True, comment="警告阈值")
    critical_threshold = Column(String(200), nullable=True, comment="严重阈值")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    isbuiltin = Column(Boolean, default=False, comment="是否内置")
    
    # 排序
    order = Column(Integer, default=0, comment="排序顺序")
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<InspectionCheckItem(id={self.id}, name='{self.name}', category='{self.category}')>"
