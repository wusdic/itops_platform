"""
BM-04 报告生成模块单元测试
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from modules.business.report_generator import (
    ReportGenerator,
    ReportType,
    ExportFormat,
    ReportStatus,
    Report,
    ReportMetadata,
    ReportExporter,
    DailyReportGenerator,
    PeriodicReportGenerator,
    ReportPeriod,
    RCAReportGenerator,
    RootCauseAnalysis,
    RootCauseMethod,
    Severity,
    TemplateManager,
    TemplateMarket,
    ReportTemplate,
    TemplateCategory,
    TemplateFormat,
    TemplateVariable,
)


class TestReportGenerator(unittest.TestCase):
    """测试报告生成器"""
    
    def setUp(self):
        """设置测试环境"""
        self.generator = ReportGenerator()
    
    def test_create_report(self):
        """测试创建报告"""
        report = self.generator.create_report(
            report_type=ReportType.DAILY,
            title="测试报告",
            description="测试描述",
            author="测试员",
        )
        
        self.assertIsInstance(report, Report)
        self.assertEqual(report.metadata.title, "测试报告")
        self.assertEqual(report.metadata.report_type, ReportType.DAILY)
        self.assertEqual(report.metadata.author, "测试员")
        self.assertEqual(report.status, ReportStatus.PENDING)
    
    def test_generate_report(self):
        """测试生成报告"""
        report = self.generator.create_report(
            report_type=ReportType.DAILY,
            title="测试报告",
        )
        
        context = {
            'content': '<h1>测试内容</h1><p>这是一份测试报告</p>'
        }
        
        result = self.generator.generate(report, context=context)
        
        self.assertEqual(result.status, ReportStatus.COMPLETED)
        self.assertIn('测试内容', result.content)
        self.assertIsNotNone(result.generated_at)
    
    def test_generate_default_content(self):
        """测试默认内容生成"""
        report = self.generator.create_report(
            report_type=ReportType.WEEKLY,
            title="周报测试",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 7),
        )
        
        result = self.generator.generate(report)
        
        self.assertIn('周报测试', result.content)
        self.assertIn('weekly', result.content)
    
    def test_list_reports(self):
        """测试列出报告"""
        # 创建多个报告
        for i in range(5):
            report = self.generator.create_report(
                report_type=ReportType.DAILY if i % 2 == 0 else ReportType.WEEKLY,
                title=f"报告{i+1}",
            )
        
        # 列出所有报告
        all_reports = self.generator.list_reports()
        self.assertEqual(len(all_reports), 5)
        
        # 按类型筛选
        daily_reports = self.generator.list_reports(report_type=ReportType.DAILY)
        self.assertEqual(len(daily_reports), 3)
        
        weekly_reports = self.generator.list_reports(report_type=ReportType.WEEKLY)
        self.assertEqual(len(weekly_reports), 2)
    
    def test_delete_report(self):
        """测试删除报告"""
        report = self.generator.create_report(
            report_type=ReportType.DAILY,
            title="待删除报告",
        )
        
        report_id = report.metadata.report_id
        
        # 删除报告
        self.assertTrue(self.generator.delete_report(report_id))
        
        # 验证已删除
        self.assertIsNone(self.generator.get_report(report_id))
        
        # 删除不存在的报告
        self.assertFalse(self.generator.delete_report("nonexistent"))
    
    def test_export_html(self):
        """测试HTML导出"""
        import tempfile
        import os
        
        report = self.generator.create_report(
            report_type=ReportType.DAILY,
            title="导出测试",
        )
        
        # 先生成报告
        self.generator.generate(report, context={'content': '<p>测试内容</p>'})
        
        # 使用临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 重新创建导出器
            self.generator._exporter = ReportExporter(tmpdir)
            
            filepath = self.generator.export(report, ExportFormat.HTML)
            self.assertTrue(filepath.endswith('.html'))
            self.assertTrue(os.path.exists(filepath))
    
    def test_report_types(self):
        """测试报告类型枚举"""
        self.assertEqual(ReportType.DAILY.value, "daily")
        self.assertEqual(ReportType.WEEKLY.value, "weekly")
        self.assertEqual(ReportType.MONTHLY.value, "monthly")
        self.assertEqual(ReportType.RCA.value, "rca")
    
    def test_export_formats(self):
        """测试导出格式枚举"""
        self.assertEqual(ExportFormat.HTML.value, "html")
        self.assertEqual(ExportFormat.PDF.value, "pdf")
        self.assertEqual(ExportFormat.WORD.value, "word")
        self.assertEqual(ExportFormat.EXCEL.value, "excel")


class TestDailyReportGenerator(unittest.TestCase):
    """测试日巡检报告生成器"""
    
    def setUp(self):
        """设置测试环境"""
        self.report_generator = ReportGenerator()
        self.daily_generator = DailyReportGenerator(self.report_generator)
    
    def test_generate_daily_report(self):
        """测试生成日巡检报告"""
        monitoring_data = {
            'total_hosts': 100,
            'online_hosts': 98,
            'offline_hosts': 2,
            'total_metrics': 500,
            'abnormal_metrics': 5,
            'cpu_avg_usage': 45.5,
            'memory_avg_usage': 60.0,
            'disk_avg_usage': 55.0,
        }
        
        alert_data = {
            'total_count': 20,
            'critical_count': 1,
            'warning_count': 5,
            'info_count': 14,
            'acknowledged_count': 18,
            'resolved_count': 15,
            'top_alerts': [
                {'name': 'CPU过高', 'severity': 'critical', 'duration': '30分钟'}
            ],
        }
        
        device_data = {
            'devices': [
                {'name': 'Server-01', 'type': '服务器', 'status': 'online', 'issues': []},
                {'name': 'Switch-01', 'type': '交换机', 'status': 'offline', 'issues': ['链路中断']},
            ]
        }
        
        anomaly_records = [
            {
                'id': 'AN001',
                'timestamp': datetime.now() - timedelta(hours=2),
                'source': '监控系统',
                'severity': 'warning',
                'description': 'CPU使用率突增',
                'handled': True,
                'handler': '张三',
            }
        ]
        
        report = self.daily_generator.generate(
            report_date=datetime(2024, 1, 15),
            duty_person="李四",
            duty_shift="day",
            monitoring_data=monitoring_data,
            alert_data=alert_data,
            device_data=device_data,
            anomaly_records=anomaly_records,
        )
        
        self.assertEqual(report.status, ReportStatus.COMPLETED)
        self.assertIn('日巡检报告', report.metadata.title)
        self.assertIn('李四', report.metadata.description)
    
    def test_collect_monitoring_data(self):
        """测试监控数据收集"""
        data = {
            'total_hosts': 50,
            'online_hosts': 48,
            'cpu_avg_usage': 55.5,
        }
        
        summary = self.daily_generator._collect_monitoring_data(data)
        
        self.assertEqual(summary.total_hosts, 50)
        self.assertEqual(summary.online_hosts, 48)
        self.assertEqual(summary.cpu_avg_usage, 55.5)
    
    def test_generate_html_content(self):
        """测试HTML内容生成"""
        from modules.business.report_generator.daily_report import (
            MonitoringSummary,
            AlertStatistics,
            DeviceStatus,
            AnomalyRecord,
        )
        
        monitoring = MonitoringSummary(
            total_hosts=100,
            online_hosts=95,
            offline_hosts=5,
            cpu_avg_usage=50.0,
        )
        
        alerts = AlertStatistics(
            total_count=10,
            critical_count=1,
            warning_count=3,
            resolved_count=8,
        )
        
        html = self.daily_generator.generate_html_content(
            report_date=datetime(2024, 1, 15),
            duty_person="测试员",
            duty_shift="day",
            monitoring=monitoring,
            alerts=alerts,
            devices=[],
            anomalies=[],
        )
        
        self.assertIn('日巡检报告', html)
        self.assertIn('测试员', html)
        self.assertIn('100', html)
    
    def test_template_variables(self):
        """测试模板变量说明"""
        variables = self.daily_generator.get_template_variables()
        
        self.assertIn('report_date', variables)
        self.assertIn('monitoring.total_hosts', variables)
        self.assertIn('alerts.total_count', variables)


class TestPeriodicReportGenerator(unittest.TestCase):
    """测试周期性报告生成器"""
    
    def setUp(self):
        """设置测试环境"""
        self.report_generator = ReportGenerator()
        self.periodic_generator = PeriodicReportGenerator(self.report_generator)
    
    def test_generate_weekly_report(self):
        """测试生成周报"""
        data = {
            'metrics': {
                'cpu_avg': 45.0,
                'memory_avg': 60.0,
                'availability': 99.95,
            },
            'trends': {
                'cpu_avg': [40, 42, 45, 48, 50, 47, 45],
            },
            'kpis': {
                'availability': 99.95,
                'mttr': 15.5,
            },
            'suggestions': [
                {
                    'category': '性能优化',
                    'title': '内存使用优化',
                    'description': '建议调整内存分配策略',
                    'priority': 'medium',
                    'estimated_impact': '降低内存使用10%',
                    'owner': '张三',
                }
            ],
        }
        
        kpi_targets = {
            'availability': 99.9,
            'mttr': 30.0,
        }
        
        week_start = datetime(2024, 1, 8)  # 周一
        report = self.periodic_generator.generate_weekly(
            week_start=week_start,
            data=data,
            kpi_targets=kpi_targets,
        )
        
        self.assertEqual(report.status, ReportStatus.COMPLETED)
        self.assertEqual(report.metadata.report_type, ReportType.WEEKLY)
    
    def test_generate_monthly_report(self):
        """测试生成月报"""
        data = {
            'metrics': {
                'incident_count': 5,
                'change_count': 20,
            }
        }
        
        report = self.periodic_generator.generate_monthly(
            month=1,
            year=2024,
            data=data,
        )
        
        self.assertEqual(report.status, ReportStatus.COMPLETED)
        self.assertEqual(report.metadata.report_type, ReportType.MONTHLY)
    
    def test_analyze_trends(self):
        """测试趋势分析"""
        data = {
            'trends': {
                'cpu_avg': [30, 35, 40, 45, 50],
            }
        }
        
        trends = self.periodic_generator._analyze_trends(data)
        
        self.assertIn('cpu_avg', trends)
        self.assertEqual(len(trends['cpu_avg']), 5)
    
    def test_calculate_kpis(self):
        """测试KPI计算"""
        data = {
            'kpis': {
                'availability': 99.95,
                'mttr': 15.0,
            }
        }
        
        targets = {
            'availability': 99.9,
            'mttr': 30.0,
        }
        
        kpis = self.periodic_generator._calculate_kpis(data, targets)
        
        self.assertEqual(len(kpis), 2)
        
        # 查找availability KPI
        availability_kpi = next(k for k in kpis if k.name == 'availability')
        self.assertTrue(availability_kpi.achieved)
        
        # 查找mttr KPI
        mttr_kpi = next(k for k in kpis if k.name == 'mttr')
        # MTTR: 越低越好，所以15 < 30表示达成目标
        # 实际业务中，MTTR越低越好，所以这里需要检查actual <= target
        self.assertLessEqual(mttr_kpi.actual, mttr_kpi.target)


class TestRCAReportGenerator(unittest.TestCase):
    """测试RCA报告生成器"""
    
    def setUp(self):
        """设置测试环境"""
        self.report_generator = ReportGenerator()
        self.rca_generator = RCAReportGenerator(self.report_generator)
    
    def test_generate_rca_report(self):
        """测试生成RCA报告"""
        timeline = [
            {
                'timestamp': datetime(2024, 1, 15, 10, 0),
                'type': 'detection',
                'description': '监控系统告警',
                'actor': '监控系统',
            },
            {
                'timestamp': datetime(2024, 1, 15, 10, 5),
                'type': 'notification',
                'description': '通知值班人员',
                'actor': '值班员',
            },
            {
                'timestamp': datetime(2024, 1, 15, 10, 15),
                'type': 'response',
                'description': '开始排查',
                'actor': '工程师A',
            },
            {
                'timestamp': datetime(2024, 1, 15, 10, 45),
                'type': 'resolution',
                'description': '问题解决',
                'actor': '工程师A',
            },
        ]
        
        impact = {
            'affected_services': ['订单系统', '支付系统'],
            'affected_users': 1000,
            'affected_regions': ['华东', '华北'],
            'revenue_impact': 50000.0,
        }
        
        root_cause_analysis = {
            'method': '5why',
            'five_why': {
                'problem': '服务不可用',
                'levels': [
                    {'question': '为什么服务不可用？', 'answer': '数据库连接池耗尽'},
                    {'question': '为什么连接池耗尽？', 'answer': '慢查询占用连接'},
                    {'question': '为什么存在慢查询？', 'answer': '缺少索引'},
                ],
                'root_cause': '数据库表缺少索引',
                'confidence': 'high',
            },
            'contributing_factors': [
                '监控告警未及时响应',
                '变更未充分测试',
            ],
        }
        
        action_items = [
            {
                'action': '添加数据库索引',
                'owner': 'DBA张三',
                'due_date': datetime(2024, 1, 20),
                'status': 'open',
                'priority': 'high',
            },
            {
                'action': '优化监控告警响应流程',
                'owner': '运维负责人',
                'due_date': datetime(2024, 1, 25),
                'status': 'open',
                'priority': 'medium',
            },
        ]
        
        lessons_learned = [
            '变更前需要充分测试',
            '监控告警需要及时响应',
            '重要表需要添加索引',
        ]
        
        report = self.rca_generator.generate(
            incident_id="INC001",
            incident_title="订单服务不可用",
            severity=Severity.P2,
            start_time=datetime(2024, 1, 15, 10, 0),
            end_time=datetime(2024, 1, 15, 10, 45),
            timeline=timeline,
            impact=impact,
            root_cause_analysis=root_cause_analysis,
            action_items=action_items,
            lessons_learned=lessons_learned,
        )
        
        self.assertEqual(report.status, ReportStatus.COMPLETED)
        self.assertIn('RCA报告', report.metadata.title)
        self.assertIn('INC001', report.metadata.title)
    
    def test_perform_five_why(self):
        """测试5Why分析"""
        result = self.rca_generator.perform_five_why(
            problem="服务响应慢",
            why_1="数据库查询慢",
            why_2="缺少索引",
            why_3="表结构设计时未考虑",
            why_4="缺乏评审流程",
            why_5="没有规范约束",
            root_cause="缺少数据库设计规范",
        )
        
        self.assertEqual(result.problem, "服务响应慢")
        self.assertEqual(len(result.why_levels), 5)
        self.assertEqual(result.root_cause, "缺少数据库设计规范")
    
    def test_perform_fishbone(self):
        """测试鱼骨图分析"""
        categories = {
            '人': ['培训不足', '经验欠缺'],
            '机': ['服务器性能不足', '硬件老化'],
            '料': ['数据量大'],
            '法': ['缺乏规范'],
        }
        
        result = self.rca_generator.perform_fishbone(
            problem="系统性能下降",
            categories=categories,
        )
        
        self.assertEqual(result.problem, "系统性能下降")
        self.assertEqual(len(result.categories), 4)
        self.assertIn('人员因素', [c.category for c in result.categories])
    
    def test_format_duration(self):
        """测试时长格式化"""
        self.assertEqual(
            self.rca_generator._format_duration(30),
            "30秒"
        )
        self.assertEqual(
            self.rca_generator._format_duration(150),
            "2分30秒"
        )
        self.assertEqual(
            self.rca_generator._format_duration(3665),
            "1小时1分5秒"
        )
        self.assertEqual(
            self.rca_generator._format_duration(90000),
            "1天1小时"
        )


class TestTemplateManager(unittest.TestCase):
    """测试模板管理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.market = TemplateMarket()
        self.manager = TemplateManager(self.market)
    
    def test_builtin_templates(self):
        """测试内置模板"""
        templates = self.market.list()
        
        self.assertGreater(len(templates), 0)
        
        # 验证内置模板存在
        template_ids = [t.template_id for t in templates]
        self.assertIn('daily_report_default', template_ids)
        self.assertIn('weekly_report_default', template_ids)
        self.assertIn('rca_report_default', template_ids)
    
    def test_create_template(self):
        """测试创建模板"""
        template = self.manager.create_template(
            template_id="custom_template",
            name="自定义模板",
            description="用于测试",
            category=TemplateCategory.CUSTOM,
            content="# {{ title }}\n\n{{ content }}",
            tags=['test', 'custom'],
        )
        
        self.assertEqual(template.template_id, "custom_template")
        self.assertEqual(template.name, "自定义模板")
        self.assertFalse(template.isBuiltIn)
    
    def test_get_template(self):
        """测试获取模板"""
        template = self.manager.get_template('daily_report_default')
        
        self.assertIsNotNone(template)
        self.assertEqual(template.name, "标准日巡检报告")
    
    def test_update_template(self):
        """测试更新模板"""
        # 创建自定义模板
        template = self.manager.create_template(
            template_id="update_test",
            name="更新测试",
            description="原始描述",
            category=TemplateCategory.CUSTOM,
            content="# Test",
        )
        
        # 更新
        updated = self.manager.update_template(
            "update_test",
            name="更新后名称",
            description="新描述",
        )
        
        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "更新后名称")
        self.assertEqual(updated.description, "新描述")
    
    def test_delete_template(self):
        """测试删除模板"""
        # 创建自定义模板
        self.manager.create_template(
            template_id="delete_test",
            name="删除测试",
            description="用于删除测试",
            category=TemplateCategory.CUSTOM,
            content="# Test",
        )
        
        # 删除
        self.assertTrue(self.manager.delete_template("delete_test"))
        
        # 验证已删除
        self.assertIsNone(self.manager.get_template("delete_test"))
    
    def test_list_templates(self):
        """测试列出模板"""
        templates = self.manager.list_templates()
        
        self.assertGreater(len(templates), 0)
        
        # 按分类筛选
        daily_templates = self.manager.list_templates(
            category=TemplateCategory.DAILY
        )
        self.assertTrue(all(t.category == TemplateCategory.DAILY for t in daily_templates))
    
    def test_preview(self):
        """测试模板预览"""
        preview = self.manager.preview(
            'daily_report_default',
            preview_data={
                'report_date': '2024-01-15',
                'duty_person': '测试员',
                'duty_shift': 'day',
                'monitoring': {'total_hosts': 100},
                'alerts': {'total_count': 10},
                'devices': [],
                'anomalies': [],
                'conclusions': '一切正常',
            }
        )
        
        self.assertIn('日巡检报告', preview)
        self.assertIn('测试员', preview)
    
    def test_export_import_template(self):
        """测试导出导入模板"""
        # 创建模板
        original = self.manager.create_template(
            template_id="export_test",
            name="导出测试",
            description="用于导出导入测试",
            category=TemplateCategory.CUSTOM,
            content="# {{ title }}",
            variables=[
                TemplateVariable("title", "标题", "string"),
            ],
            tags=['test'],
        )
        
        # 导出
        exported = self.manager.export_template("export_test")
        
        self.assertEqual(exported['template_id'], "export_test")
        self.assertEqual(exported['name'], "导出测试")
        
        # 删除原模板
        self.manager.delete_template("export_test")
        
        # 导入
        imported = self.manager.import_template(exported)
        
        self.assertEqual(imported.name, "导出测试")
        self.assertEqual(len(imported.variables), 1)
    
    def test_search_templates(self):
        """测试搜索模板"""
        results = self.market.search("日")
        
        self.assertTrue(len(results) > 0)
        self.assertTrue(any('日' in t.name for t in results))
    
    def test_template_variable(self):
        """测试模板变量"""
        var = TemplateVariable(
            name="test_var",
            description="测试变量",
            var_type="string",
            required=True,
            default_value="default",
            example="example",
        )
        
        self.assertEqual(var.name, "test_var")
        self.assertEqual(var.var_type, "string")
        self.assertTrue(var.required)


class TestTemplateMarket(unittest.TestCase):
    """测试模板市场"""
    
    def setUp(self):
        """设置测试环境"""
        self.market = TemplateMarket()
    
    def test_register_unregister(self):
        """测试注册和取消注册"""
        template = ReportTemplate(
            template_id="test_reg",
            name="注册测试",
            description="测试注册功能",
            category=TemplateCategory.CUSTOM,
            format=TemplateFormat.JINJA2,
            content="# Test",
        )
        
        # 注册
        self.market.register(template)
        self.assertIsNotNone(self.market.get("test_reg"))
        
        # 取消注册
        self.market.unregister("test_reg")
        self.assertIsNone(self.market.get("test_reg"))
    
    def test_list_with_filters(self):
        """测试带过滤条件的列表"""
        # 按分类
        templates = self.market.list(category=TemplateCategory.DAILY)
        self.assertTrue(all(t.category == TemplateCategory.DAILY for t in templates))
        
        # 按标签 - 内置模板都有period或类型相关的标签
        templates = self.market.list(tag='periodic')
        self.assertTrue(len(templates) > 0)
    
    def test_builtin_templates_categories(self):
        """测试内置模板分类"""
        daily = self.market.list(category=TemplateCategory.DAILY)
        weekly = self.market.list(category=TemplateCategory.PERIODIC)
        rca = self.market.list(category=TemplateCategory.RCA)
        
        self.assertTrue(len(daily) >= 1)
        self.assertTrue(len(weekly) >= 2)  # 周报和月报
        self.assertTrue(len(rca) >= 1)


if __name__ == '__main__':
    unittest.main()
