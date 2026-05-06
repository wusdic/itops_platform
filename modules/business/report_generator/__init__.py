"""
报告生成模块
"""

from .generator import ReportExporter, ReportDataCollector, BUILTIN_TEMPLATES
from .reporter import (
    ReportGenerator,
    ReportType,
    ExportFormat,
    ReportStatus,
    Report,
    ReportMetadata,
    TemplateRenderer,
)
from .scheduler import ReportScheduler, get_scheduler, start_scheduler, stop_scheduler
from .periodic_report import ReportPeriod, PeriodicReportGenerator
from .daily_report import DailyReportGenerator
from .rca_report import RootCauseAnalysis, RootCauseMethod, Severity, RCAReportGenerator
from .templates import (
    TemplateFormat, TemplateCategory, TemplateVariable,
    ReportTemplate, TemplateMarket, TemplateManager
)

__all__ = [
    # 核心类
    'ReportGenerator',
    'BUILTIN_TEMPLATES',
    'ReportExporter',
    'ReportDataCollector',
    'ReportScheduler',
    'get_scheduler',
    'start_scheduler',
    'stop_scheduler',
    # 枚举类型
    'ReportType',
    'ExportFormat',
    'ReportStatus',
    'ReportPeriod',
    'TemplateFormat',
    'TemplateCategory',
    'Severity',
    # 数据类
    'Report',
    'ReportMetadata',
    'TemplateVariable',
    'ReportTemplate',
    # 生成器
    'TemplateRenderer',
    'PeriodicReportGenerator',
    'DailyReportGenerator',
    'RCAReportGenerator',
    # RCA
    'RootCauseAnalysis',
    'RootCauseMethod',
    # 模板
    'TemplateMarket',
    'TemplateManager'
]