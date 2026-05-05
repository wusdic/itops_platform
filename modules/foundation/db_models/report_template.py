"""
报告模板数据模型
支持多种报告类型和Jinja2模板语法
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, Enum as SQLEnum
import enum

from modules.foundation.db_models.base import Base


class ReportTemplateType(str, enum.Enum):
    """报告模板类型"""
    DEVICE_STATUS = "device_status"      # 设备状态报告
    ALERT_SUMMARY = "alert_summary"      # 告警汇总报告
    PERFORMANCE_TREND = "performance_trend"  # 性能趋势报告
    CUSTOM = "custom"                    # 自定义报告


class ReportFormat(str, enum.Enum):
    """报告格式"""
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


class ReportTemplate(Base):
    """报告模板模型"""
    __tablename__ = "report_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="模板名称")
    template_type = Column(
        SQLEnum(ReportTemplateType),
        nullable=False,
        comment="模板类型"
    )
    description = Column(Text, nullable=True, comment="模板描述")
    
    # Jinja2模板内容
    content = Column(Text, nullable=False, comment="模板内容(Jinja2)")
    
    # 配置信息
    config = Column(JSON, nullable=True, comment="模板配置")
    
    # 内置模板标志
    is_builtin = Column(Boolean, default=False, comment="是否内置模板")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 审计字段
    created_by = Column(String(100), nullable=True, comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(100), nullable=True, comment="更新人")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<ReportTemplate(id={self.id}, name='{self.name}', type='{self.template_type}')>"


class Report(Base):
    """生成的报告记录"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_no = Column(String(50), unique=True, nullable=False, comment="报告编号")
    name = Column(String(200), nullable=False, comment="报告名称")
    
    # 关联的模板
    template_id = Column(Integer, nullable=True, comment="模板ID")
    template_type = Column(SQLEnum(ReportTemplateType), nullable=False, comment="报告类型")
    
    # 报告参数
    start_date = Column(DateTime, nullable=False, comment="开始日期")
    end_date = Column(DateTime, nullable=False, comment="结束日期")
    format = Column(SQLEnum(ReportFormat), default=ReportFormat.PDF, comment="输出格式")
    filters = Column(JSON, nullable=True, comment="筛选条件")
    params = Column(JSON, nullable=True, comment="额外参数")
    
    # 生成状态
    status = Column(String(20), default="pending", comment="状态: pending/generating/completed/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 文件信息
    file_path = Column(String(500), nullable=True, comment="文件路径")
    file_name = Column(String(200), nullable=True, comment="文件名")
    file_size = Column(Integer, nullable=True, comment="文件大小(字节)")
    
    # 报告数据(JSON格式存储完整报告数据)
    report_data = Column(JSON, nullable=True, comment="报告数据")
    
    # 审计字段
    created_by = Column(String(100), nullable=True, comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    
    def __repr__(self):
        return f"<Report(id={self.id}, report_no='{self.report_no}', status='{self.status}')>"


class ReportSchedule(Base):
    """定时报告调度配置"""
    __tablename__ = "report_schedules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="调度名称")
    
    # 关联的模板
    template_id = Column(Integer, nullable=False, comment="模板ID")
    
    # 调度配置
    cron_expression = Column(String(100), nullable=False, comment="Cron表达式")
    timezone = Column(String(50), default="Asia/Shanghai", comment="时区")
    
    # 输出配置
    format = Column(SQLEnum(ReportFormat), default=ReportFormat.PDF, comment="输出格式")
    recipients = Column(JSON, nullable=False, comment="接收人邮箱列表")
    
    # 报告参数
    date_range_type = Column(String(20), default="daily", comment="日期范围类型: daily/weekly/monthly")
    params = Column(JSON, nullable=True, comment="额外参数")
    
    # 状态
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    
    # 上次执行信息
    last_run_at = Column(DateTime, nullable=True, comment="上次执行时间")
    last_run_status = Column(String(20), nullable=True, comment="上次执行状态")
    next_run_at = Column(DateTime, nullable=True, comment="下次执行时间")
    
    # 审计字段
    created_by = Column(String(100), nullable=True, comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_by = Column(String(100), nullable=True, comment="更新人")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<ReportSchedule(id={self.id}, name='{self.name}', cron='{self.cron_expression}')>"