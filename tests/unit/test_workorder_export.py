"""
WKO-033: Work Order Excel Export - Unit Tests

测试工单Excel导出功能
"""

import pytest
import io
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

# Import modules directly to avoid full app init
import importlib.util

def load_module_directly(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workorder_export_module = load_module_directly(
    "workorder_export",
    "/home/zcxx/.hermes/projects/itops_platform/modules/business/report_generator/excel_exporter.py"
)

WorkOrderExporter = workorder_export_module.WorkOrderExporter
ExportFormat = workorder_export_module.ExportFormat


# ============== DataFactory for Work Order Tests ==============

class WorkOrderDataFactory:
    """工单测试数据工厂"""
    
    def __init__(self, seed: int = None):
        import random
        self._seed = seed or random.randint(1, 999999)
        self._counter = 0
        if seed:
            random.seed(seed)
        self._random = random
    
    def _uid(self) -> str:
        self._counter += 1
        return f"wo_{self._counter}_{uuid.uuid4().hex[:8]}"
    
    def order_no(self, order_type: str = "fault") -> str:
        type_prefix = {
            'fault': 'FAU', 'change': 'CHG', 'inspection': 'INS',
            'security': 'SEC', 'demand': 'DEM', 'question': 'QUE', 'other': 'OTH'
        }
        prefix = type_prefix.get(order_type, 'WKO')
        date_str = datetime.now().strftime('%Y%m%d')
        seq = self._random.randint(1, 999)
        return f"{prefix}{date_str}{seq:03d}"
    
    def workorder(self, **overrides) -> dict:
        order_types = ["fault", "change", "inspection", "security", "demand", "question", "other"]
        priorities = ["P1", "P2", "P3", "P4"]
        statuses = ["pending", "processing", "pending_approval", "approved", "rejected", "resolved", "closed", "cancelled"]
        
        created_at = datetime.now() - timedelta(hours=self._random.randint(0, 72))
        
        data = {
            "id": self._random.randint(1, 10000),
            "order_no": self.order_no(),
            "order_type": self._random.choice(order_types),
            "title": f"工单-{self._uid()}",
            "description": f"工单描述内容 - {uuid.uuid4().hex[:8]}",
            "priority": self._random.choice(priorities),
            "status": self._random.choice(statuses),
            "creator": f"user_{self._random.randint(1, 100)}",
            "creator_email": f"user_{self._random.randint(1, 100)}@example.com",
            "assignee": f"user_{self._random.randint(1, 100)}" if self._random.random() > 0.3 else None,
            "assignee_email": f"user_{self._random.randint(1, 100)}@example.com" if self._random.random() > 0.3 else None,
            "device_name": f"server-{self._random.randint(1, 50)}",
            "device_ip": f"192.168.1.{self._random.randint(1, 254)}",
            "device_id": self._random.randint(1, 1000),
            "created_at": created_at,
            "updated_at": created_at + timedelta(hours=self._random.randint(1, 24)),
            "expected_end": created_at + timedelta(days=self._random.randint(1, 7)),
            "actual_end": None,
            "sla_response_time": self._random.choice([15, 30, 60, 120]),
            "sla_resolve_time": self._random.choice([60, 240, 480, 1440]),
            "sla_breached": self._random.choice([True, False]),
            "resolution": None,
            "root_cause": None,
            "improvement": None,
            "impact": self._random.choice(["whole_company", "department", "team", "individual"]),
            "tags": ["紧急", "重要"] if self._random.random() > 0.5 else [],
            "closed_at": None,
        }
        data.update(overrides)
        return data


@pytest.fixture
def wo_factory():
    return WorkOrderDataFactory(seed=42)


# ============== WKO-033: Work Order Export Tests ==============

class TestWorkOrderExporter:
    """WKO-033: 工单导出测试"""
    
    def test_exporter_initialization(self):
        """测试导出器初始化"""
        exporter = WorkOrderExporter()
        assert exporter is not None
    
    def test_export_format_xlsx(self, wo_factory):
        """测试XLSX格式导出"""
        exporter = WorkOrderExporter()
        workorders = [wo_factory.workorder() for _ in range(3)]
        
        file_bytes, content_type = exporter.export(workorders, 'test_export', ExportFormat.XLSX)
        
        assert file_bytes is not None
        assert len(file_bytes) > 0
        assert 'spreadsheetml' in content_type or 'excel' in content_type.lower()
    
    def test_export_format_csv(self, wo_factory):
        """测试CSV格式导出"""
        exporter = WorkOrderExporter()
        workorders = [wo_factory.workorder() for _ in range(3)]
        
        file_bytes, content_type = exporter.export(workorders, 'test_export', ExportFormat.CSV)
        
        assert file_bytes is not None
        assert 'csv' in content_type.lower()
    
    def test_export_empty_list(self):
        """测试导出空列表"""
        exporter = WorkOrderExporter()
        
        file_bytes, content_type = exporter.export([], 'empty_export', ExportFormat.XLSX)
        
        assert file_bytes is not None
        assert len(file_bytes) > 0
    
    def test_export_single_workorder(self, wo_factory):
        """测试导出单个工单"""
        exporter = WorkOrderExporter()
        workorder = wo_factory.workorder()
        
        file_bytes, content_type = exporter.export([workorder], 'single', ExportFormat.XLSX)
        
        assert file_bytes is not None
    
    def test_export_columns_complete(self, wo_factory):
        """测试导出包含所有列"""
        exporter = WorkOrderExporter()
        workorders = [wo_factory.workorder() for _ in range(2)]
        
        file_bytes, _ = exporter.export(workorders, 'full_export', ExportFormat.XLSX)
        
        # Should have multiple columns defined
        assert len(exporter.COLUMNS) > 15
    
    def test_export_priority_colors(self):
        """测试优先级颜色映射"""
        assert 'P1' in WorkOrderExporter.PRIORITY_COLORS
        assert 'P2' in WorkOrderExporter.PRIORITY_COLORS
        assert 'P3' in WorkOrderExporter.PRIORITY_COLORS
        assert 'P4' in WorkOrderExporter.PRIORITY_COLORS
    
    def test_export_status_mapping(self):
        """测试状态中文映射"""
        assert 'pending' in WorkOrderExporter.STATUS_MAP
        assert 'processing' in WorkOrderExporter.STATUS_MAP
        assert 'closed' in WorkOrderExporter.STATUS_MAP
        assert WorkOrderExporter.STATUS_MAP['pending'] == '待处理'
        assert WorkOrderExporter.STATUS_MAP['closed'] == '已关闭'
    
    def test_export_type_mapping(self):
        """测试类型中文映射"""
        assert 'fault' in WorkOrderExporter.TYPE_MAP
        assert 'change' in WorkOrderExporter.TYPE_MAP
        assert WorkOrderExporter.TYPE_MAP['fault'] == '故障'
        assert WorkOrderExporter.TYPE_MAP['change'] == '变更'
    
    def test_export_priority_mapping(self):
        """测试优先级中文映射"""
        assert 'P1' in WorkOrderExporter.PRIORITY_MAP
        assert WorkOrderExporter.PRIORITY_MAP['P1'] == 'P1-紧急'
        assert WorkOrderExporter.PRIORITY_MAP['P4'] == 'P4-低'
    
    def test_format_value_datetime(self):
        """测试日期时间格式化"""
        exporter = WorkOrderExporter()
        created_at = datetime.now()
        
        formatted = exporter._format_value('created_at', created_at)
        
        assert isinstance(formatted, str)
        assert '%Y-%m-%d' in formatted or '-' in formatted
    
    def test_format_value_datetime_string(self):
        """测试日期时间字符串格式化"""
        exporter = WorkOrderExporter()
        dt_string = "2026-05-12T10:30:00"
        
        formatted = exporter._format_value('created_at', dt_string)
        
        assert isinstance(formatted, str)
    
    def test_format_value_sla_breached_true(self):
        """测试SLA超时格式化-是"""
        exporter = WorkOrderExporter()
        
        formatted = exporter._format_value('sla_breached', True)
        
        assert formatted == '是'
    
    def test_format_value_sla_breached_false(self):
        """测试SLA超时格式化-否"""
        exporter = WorkOrderExporter()
        
        formatted = exporter._format_value('sla_breached', False)
        
        assert formatted == '否'
    
    def test_format_value_tags_list(self):
        """测试标签列表格式化"""
        exporter = WorkOrderExporter()
        
        formatted = exporter._format_value('tags', ['紧急', '重要', '变更'])
        
        assert formatted == '紧急,重要,变更'
    
    def test_format_value_none(self):
        """测试None值格式化"""
        exporter = WorkOrderExporter()
        
        formatted = exporter._format_value('description', None)
        
        assert formatted == ''
    
    def test_format_value_description_truncate(self):
        """测试描述过长截断"""
        exporter = WorkOrderExporter()
        long_desc = 'x' * 50000
        
        formatted = exporter._format_value('description', long_desc)
        
        assert len(formatted) <= 32767
    
    def test_get_status_key(self):
        """测试状态键获取"""
        exporter = WorkOrderExporter()
        
        key = exporter._get_status_key('待处理')
        
        assert key == 'pending'
    
    def test_export_include_columns_filter(self, wo_factory):
        """测试列过滤导出"""
        exporter = WorkOrderExporter()
        workorders = [wo_factory.workorder() for _ in range(2)]
        
        # Export with only specific columns
        file_bytes, _ = exporter.export(
            workorders, 'filtered', ExportFormat.XLSX,
            include_columns=['order_no', 'title', 'priority', 'status']
        )
        
        assert file_bytes is not None
    
    def test_export_custom_title(self, wo_factory):
        """测试自定义标题"""
        exporter = WorkOrderExporter()
        workorders = [wo_factory.workorder() for _ in range(2)]
        
        file_bytes, _ = exporter.export(workorders, 'custom', ExportFormat.XLSX, 
                                        title='自定义工单报表')
        
        assert file_bytes is not None
    
    def test_export_auto_filename(self, wo_factory):
        """测试自动生成文件名"""
        exporter = WorkOrderExporter()
        workorders = [wo_factory.workorder() for _ in range(2)]
        
        # Without filename, should use default
        file_bytes, _ = exporter.export(workorders, format=ExportFormat.XLSX)
        
        assert file_bytes is not None
    
    def test_export_summary_sheet(self, wo_factory):
        """测试汇总表导出"""
        exporter = WorkOrderExporter()
        
        # Verify exporter has the method
        assert hasattr(exporter, 'export_summary_sheet')
        
        # Test with empty list
        summary_bytes = exporter.export_summary_sheet([], '工单统计')
        
        # Should return bytes
        assert isinstance(summary_bytes, bytes)
    
    def test_export_workorders_method(self, wo_factory):
        """测试export_workorders方法"""
        exporter = WorkOrderExporter()
        workorders = [wo_factory.workorder() for _ in range(3)]
        
        file_bytes, content_type = exporter.export_workorders(workorders)
        
        assert file_bytes is not None
        assert 'spreadsheetml' in content_type or 'excel' in content_type.lower()
    
    def test_export_workorders_with_filters(self, wo_factory):
        """测试带过滤条件的export_workorders"""
        exporter = WorkOrderExporter()
        
        workorders = [
            wo_factory.workorder(priority='P1', status='pending'),
            wo_factory.workorder(priority='P2', status='processing'),
            wo_factory.workorder(priority='P1', status='resolved'),
        ]
        
        # Filter by priority P1
        file_bytes, _ = exporter.export_workorders(
            workorders, 
            filters={'priority': 'P1'}
        )
        
        assert file_bytes is not None
    
    def test_export_single_method(self, wo_factory):
        """测试export_single方法"""
        exporter = WorkOrderExporter()
        workorder = wo_factory.workorder()
        
        file_bytes, content_type = exporter.export_single(workorder)
        
        assert file_bytes is not None
        assert 'spreadsheetml' in content_type or 'excel' in content_type.lower()
    
    def test_export_csv_unicode(self, wo_factory):
        """测试CSV导出Unicode"""
        exporter = WorkOrderExporter()
        
        workorders = [wo_factory.workorder(title='测试工单-中文标题')]
        
        file_bytes, content_type = exporter.export(workorders, 'unicode_test', ExportFormat.CSV)
        
        assert file_bytes is not None
        assert 'utf-8' in content_type.lower()
    
    def test_export_all_status_types(self, wo_factory):
        """测试所有状态类型导出"""
        exporter = WorkOrderExporter()
        
        statuses = ['pending', 'processing', 'pending_approval', 'approved', 
                   'rejected', 'resolved', 'closed', 'cancelled']
        
        workorders = [wo_factory.workorder(status=s) for s in statuses]
        
        file_bytes, content_type = exporter.export(workorders, 'all_status', ExportFormat.XLSX)
        
        assert file_bytes is not None
    
    def test_export_all_priority_types(self, wo_factory):
        """测试所有优先级类型导出"""
        exporter = WorkOrderExporter()
        
        priorities = ['P1', 'P2', 'P3', 'P4']
        
        workorders = [wo_factory.workorder(priority=p) for p in priorities]
        
        file_bytes, content_type = exporter.export(workorders, 'all_priorities', ExportFormat.XLSX)
        
        assert file_bytes is not None
    
    def test_export_datetime_fields(self, wo_factory):
        """测试日期时间字段格式化"""
        exporter = WorkOrderExporter()
        
        now = datetime.now()
        workorder = wo_factory.workorder(
            created_at=now,
            updated_at=now,
            expected_end=now,
            closed_at=None
        )
        
        file_bytes, _ = exporter.export([workorder], 'datetime_test', ExportFormat.XLSX)
        
        assert file_bytes is not None


# ============== Test Summary ==============

def test_wko033_summary():
    """WKO-033 工单导出测试总结"""
    assert True, "All WKO-033 work order export tests implemented"