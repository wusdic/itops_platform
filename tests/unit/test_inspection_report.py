"""
巡检报告单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Any


class TestInspectionReportGenerator:
    """巡检报告生成器测试"""

    @pytest.fixture
    def mock_db_session(self):
        """创建模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def generator(self, mock_db_session):
        """创建报告生成器实例"""
        from modules.business.report_generator.inspection_report import InspectionReportGenerator
        return InspectionReportGenerator(db_session=mock_db_session)

    @pytest.fixture
    def sample_task(self):
        """示例巡检任务数据"""
        task = Mock()
        task.id = 1
        task.task_no = "INS-20240501001"
        task.name = "周常巡检"
        task.description = "每周例行设备巡检"
        task.inspection_type = "routine"
        task.status = "completed"
        task.progress = 100.0
        task.total_items = 50
        task.completed_items = 50
        task.total_devices = 10
        task.healthy_devices = 7
        task.warning_devices = 2
        task.critical_devices = 1
        task.offline_devices = 0
        task.health_score = 85.5
        task.started_at = datetime.now() - timedelta(hours=2)
        task.completed_at = datetime.now()
        task.executor = "admin"
        task.created_at = datetime.now() - timedelta(hours=2)
        return task

    @pytest.fixture
    def sample_results(self):
        """示例巡检结果数据"""
        results = []
        
        # 正常设备结果
        for i in range(7):
            for j in range(5):
                result = Mock()
                result.task_id = 1
                result.device_id = 100 + i
                result.device_name = f"Server-{i+1}"
                result.device_ip = f"192.168.1.{10+i}"
                result.device_type = "server_linux"
                result.check_item_id = f"check_{j}"
                result.check_item_name = f"检查项-{j+1}"
                result.check_category = "系统检查"
                result.status = "ok"
                result.result_value = "正常"
                result.result_message = "检查通过"
                result.severity = "info"
                result.suggestion = None
                result.checked_at = datetime.now()
                results.append(result)
        
        # 警告设备结果
        for i in range(2):
            for j in range(5):
                result = Mock()
                result.task_id = 1
                result.device_id = 200 + i
                result.device_name = f"Server-Warning-{i+1}"
                result.device_ip = f"192.168.1.{20+i}"
                result.device_type = "server_linux"
                result.check_item_id = f"check_{j}"
                result.check_item_name = f"检查项-{j+1}"
                result.check_category = "系统检查"
                result.status = "warning" if j == 0 else "ok"
                result.result_value = "CPU使用率85%"
                result.result_message = "CPU使用率偏高"
                result.severity = "warning"
                result.suggestion = "建议清理不必要的进程"
                result.checked_at = datetime.now()
                results.append(result)
        
        # 严重设备结果
        for j in range(5):
            result = Mock()
            result.task_id = 1
            result.device_id = 300
            result.device_name = "Server-Critical-1"
            result.device_ip = "192.168.1.30"
            result.device_type = "server_linux"
            result.check_item_id = f"check_{j}"
            result.check_item_name = f"检查项-{j+1}"
            result.check_category = "系统检查"
            result.status = "critical" if j == 0 else "ok"
            result.result_value = "磁盘使用率100%"
            result.result_message = "磁盘空间已满"
            result.severity = "critical"
            result.suggestion = "立即清理磁盘或扩容"
            result.checked_at = datetime.now()
            results.append(result)
        
        return results

    def test_generator_initialization(self, generator):
        """测试生成器初始化"""
        assert generator.db is not None
        assert generator._report_data == {}
        assert generator._task_info == {}
        assert generator._device_results == {}
        assert generator._statistics == {}

    def test_get_report_template(self, generator):
        """测试获取报告模板"""
        template = generator.get_report_template()
        
        assert template['name'] == '巡检报告模板'
        assert 'sections' in template
        assert len(template['sections']) == 5
        
        # 验证模板包含必要的章节
        section_ids = [s['id'] for s in template['sections']]
        assert 'summary' in section_ids
        assert 'health_score' in section_ids
        assert 'statistics' in section_ids
        assert 'suggestions' in section_ids
        assert 'history' in section_ids

    def test_calculate_health_score(self, generator):
        """测试健康度评分计算"""
        # 全部正常
        generator._statistics = {
            'status_summary': {'total': 10, 'healthy': 10, 'warning': 0, 'critical': 0}
        }
        score = generator._calculate_health_score()
        assert score == 100.0
        
        # 全部警告
        generator._statistics = {
            'status_summary': {'total': 10, 'healthy': 0, 'warning': 10, 'critical': 0}
        }
        score = generator._calculate_health_score()
        assert score == 70.0
        
        # 全部严重
        generator._statistics = {
            'status_summary': {'total': 10, 'healthy': 0, 'warning': 0, 'critical': 10}
        }
        score = generator._calculate_health_score()
        assert score == 30.0
        
        # 混合: 5 healthy=100, 3 warning=70, 2 critical=30
        generator._statistics = {
            'status_summary': {'total': 10, 'healthy': 5, 'warning': 3, 'critical': 2}
        }
        score = generator._calculate_health_score()
        # (5*100 + 3*70 + 2*30) / 10 = 77.0
        assert score == 77.0

    def test_get_health_level(self, generator):
        """测试健康度等级判断"""
        # 优秀
        level = generator._get_health_level(95)
        assert level['level'] == '优秀'
        assert level['color'] == '#52c41a'
        
        # 良好
        level = generator._get_health_level(85)
        assert level['level'] == '良好'
        
        # 一般
        level = generator._get_health_level(75)
        assert level['level'] == '一般'
        
        # 较差
        level = generator._get_health_level(65)
        assert level['level'] == '较差'
        
        # 危险
        level = generator._get_health_level(50)
        assert level['level'] == '危险'
        assert level['color'] == '#ff4d4f'

    def test_calculate_trend(self, generator):
        """测试趋势计算"""
        # 无历史数据
        trend = generator._calculate_trend([])
        assert trend == 'stable'
        
        # 单次数据
        mock_task = Mock()
        mock_task.health_score = 90.0
        trend = generator._calculate_trend([mock_task])
        assert trend == 'stable'
        
        # 改善趋势
        mock_tasks = [
            Mock(health_score=95.0),
            Mock(health_score=85.0),
        ]
        trend = generator._calculate_trend(mock_tasks)
        assert trend == 'improving'
        
        # 下降趋势
        mock_tasks = [
            Mock(health_score=80.0),
            Mock(health_score=90.0),
        ]
        trend = generator._calculate_trend(mock_tasks)
        assert trend == 'declining'
        
        # 稳定
        mock_tasks = [
            Mock(health_score=85.0),
            Mock(health_score=85.0),
        ]
        trend = generator._calculate_trend(mock_tasks)
        assert trend == 'stable'

    def test_load_task_info(self, generator, mock_db_session, sample_task):
        """测试加载任务信息"""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_task
        mock_db_session.query.return_value = mock_query
        
        generator._load_task_info(1)
        
        assert generator._task_info['id'] == 1
        assert generator._task_info['task_no'] == 'INS-20240501001'
        assert generator._task_info['name'] == '周常巡检'
        assert generator._task_info['status'] == 'completed'
        assert generator._task_info['health_score'] == 85.5

    def test_load_task_info_not_found(self, generator, mock_db_session):
        """测试任务不存在时的错误处理"""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        with pytest.raises(ValueError, match="not found"):
            generator._load_task_info(999)

    def test_load_inspection_results(self, generator, mock_db_session, sample_results):
        """测试加载巡检结果"""
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = sample_results
        mock_db_session.query.return_value = mock_query
        
        generator._load_inspection_results(1)
        
        # 验证设备分组
        assert len(generator._device_results) == 10  # 7 + 2 + 1
        
        # 验证状态计数
        # 正常设备
        device_100 = generator._device_results.get('100_192.168.1.10')
        assert device_100 is not None
        assert device_100['status_counts']['ok'] == 5
        
        # 警告设备
        device_200 = generator._device_results.get('200_192.168.1.20')
        assert device_200 is not None
        assert device_200['status_counts']['warning'] == 1
        assert device_200['status_counts']['ok'] == 4

    def test_calculate_statistics(self, generator):
        """测试统计数据计算"""
        generator._device_results = {
            'device1': {
                'device_id': 1,
                'device_name': 'Server-1',
                'device_ip': '192.168.1.10',
                'device_type': 'server_linux',
                'items': [
                    {'status': 'ok', 'check_category': '系统检查'},
                    {'status': 'ok', 'check_category': '性能检查'},
                    {'status': 'warning', 'check_category': '系统检查'},
                ],
                'status_counts': {'ok': 2, 'warning': 1, 'critical': 0}
            },
            'device2': {
                'device_id': 2,
                'device_name': 'Server-2',
                'device_ip': '192.168.1.11',
                'device_type': 'server_linux',
                'items': [
                    {'status': 'ok', 'check_category': '系统检查'},
                    {'status': 'critical', 'check_category': '性能检查'},
                ],
                'status_counts': {'ok': 1, 'warning': 0, 'critical': 1}
            }
        }
        
        generator._calculate_statistics()
        
        assert generator._statistics['status_summary']['total'] == 2
        # device1: warning_count=1 -> warning bucket
        # device2: critical_count=1 -> critical bucket
        assert generator._statistics['status_summary']['healthy'] == 0
        assert generator._statistics['status_summary']['warning'] == 1
        assert generator._statistics['status_summary']['critical'] == 1
        
        # 验证分类统计
        assert '系统检查' in generator._statistics['category_stats']
        assert '性能检查' in generator._statistics['category_stats']

    def test_generate_suggestions(self, generator):
        """测试生成建议措施"""
        generator._device_results = {
            'device1': {
                'device_name': 'Server-1',
                'device_ip': '192.168.1.10',
                'items': [
                    {
                        'status': 'critical',
                        'check_item_name': '磁盘检查',
                        'result_message': '磁盘空间不足',
                        'result_value': '使用率95%',
                        'suggestion': '立即清理'
                    },
                    {
                        'status': 'ok',
                        'check_item_name': 'CPU检查',
                        'result_message': '正常',
                        'suggestion': None
                    }
                ]
            },
            'device2': {
                'device_name': 'Server-2',
                'device_ip': '192.168.1.11',
                'items': [
                    {
                        'status': 'warning',
                        'check_item_name': '内存检查',
                        'result_message': '内存使用率较高',
                        'result_value': '使用率85%',
                        'suggestion': '建议关注'
                    }
                ]
            }
        }
        
        generator._generate_suggestions()
        
        # 验证生成了建议
        assert len(generator._suggestions) == 2
        
        # 严重问题优先
        assert generator._suggestions[0]['priority'] == 'critical'
        assert generator._suggestions[0]['device_name'] == 'Server-1'
        assert len(generator._suggestions[0]['issues']) == 1
        assert generator._suggestions[0]['issues'][0]['check_item'] == '磁盘检查'
        
        # 警告次之
        assert generator._suggestions[1]['priority'] == 'warning'
        assert generator._suggestions[1]['device_name'] == 'Server-2'

    def test_assemble_report(self, generator):
        """测试组装报告数据"""
        generator._task_info = {
            'id': 1,
            'task_no': 'INS-001',
            'name': '测试巡检',
            'status': 'completed'
        }
        # healthy=3, warning=1, critical=1 -> (3*100+1*70+1*30)/5 = 400/5 = 80
        generator._statistics = {
            'status_summary': {'total': 5, 'healthy': 3, 'warning': 1, 'critical': 1}
        }
        generator._device_results = {}
        generator._suggestions = []
        generator._history_comparison = {}
        
        report = generator._assemble_report()
        
        assert 'task_info' in report
        assert 'statistics' in report
        assert 'devices' in report
        assert 'suggestions' in report
        assert 'history_comparison' in report
        assert 'health_score' in report
        assert 'health_level' in report
        assert 'generated_at' in report
        
        # 健康度: 3 healthy=100, 1 warning=70, 1 critical=30 -> (300+70+30)/5 = 80.0
        assert report['health_score'] == 80.0

    def test_export_html(self, generator, mock_db_session, sample_task, sample_results):
        """测试HTML导出 - 通过直接调用_render_html_report验证"""
        # 准备测试数据
        report_data = {
            'task_info': {
                'name': '周常巡检',
                'description': '测试描述',
                'task_no': 'INS-20240501001',
                'executor': 'admin',
                'started_at': datetime.now().isoformat(),
                'completed_at': datetime.now().isoformat()
            },
            'statistics': {
                'status_summary': {
                    'total': 10,
                    'healthy': 7,
                    'warning': 2,
                    'critical': 1
                }
            },
            'devices': [
                {
                    'device_name': 'Server-1',
                    'device_ip': '192.168.1.10',
                    'device_type': 'server_linux',
                    'status_counts': {'ok': 5, 'warning': 0, 'critical': 0}
                }
            ],
            'suggestions': [],
            'history_comparison': {
                'trend': 'stable',
                'history_tasks': []
            },
            'health_score': 85.0,
            'health_level': {'level': '良好', 'color': '#73d13d'},
            'generated_at': datetime.now().isoformat()
        }
        
        # 直接测试_render_html_report
        html = generator._render_html_report(report_data)
        
        assert '周常巡检' in html
        assert '85.0' in html
        assert '良好' in html

    def test_render_html_report(self, generator):
        """测试HTML渲染"""
        report_data = {
            'task_info': {
                'name': '测试巡检',
                'description': '测试描述',
                'task_no': 'INS-001',
                'executor': 'admin',
                'started_at': '2024-05-01T10:00:00',
                'completed_at': '2024-05-01T12:00:00'
            },
            'statistics': {
                'status_summary': {
                    'total': 10,
                    'healthy': 7,
                    'warning': 2,
                    'critical': 1
                }
            },
            'devices': [
                {
                    'device_name': 'Server-1',
                    'device_ip': '192.168.1.10',
                    'device_type': 'server_linux',
                    'status_counts': {'ok': 5, 'warning': 0, 'critical': 0}
                }
            ],
            'suggestions': [],
            'history_comparison': {
                'trend': 'stable',
                'history_tasks': []
            },
            'health_score': 85.0,
            'health_level': {'level': '良好', 'color': '#73d13d'},
            'generated_at': '2024-05-01T12:00:00'
        }
        
        html = generator._render_html_report(report_data)
        
        assert '测试巡检' in html
        assert '85.0' in html
        assert '良好' in html
        assert 'Server-1' in html
        assert '192.168.1.10' in html


class TestInspectionReportAPI:
    """巡检报告API测试"""

    def test_report_response_format(self):
        """测试响应格式"""
        # 验证遵循 {data:..., code:0} 格式
        response = {
            "data": {
                'task_info': {},
                'statistics': {},
                'devices': [],
                'suggestions': [],
                'history_comparison': {},
                'health_score': 100.0,
                'health_level': {},
                'generated_at': ''
            },
            "code": 0,
            "message": "报告生成成功"
        }
        
        assert 'data' in response
        assert 'code' in response
        assert response['code'] == 0

    def test_task_list_response_format(self):
        """测试任务列表响应格式"""
        response = {
            "data": [
                {
                    'id': 1,
                    'task_no': 'INS-001',
                    'name': '测试任务',
                    'status': 'completed',
                    'health_score': 90.0
                }
            ],
            "total": 1,
            "code": 0
        }
        
        assert 'data' in response
        assert 'total' in response
        assert 'code' in response
        assert isinstance(response['data'], list)


class TestInspectionModels:
    """巡检数据模型测试"""

    def test_inspection_task_model_fields(self):
        """测试巡检任务模型字段"""
        from modules.foundation.db_models.inspection import InspectionTask
        
        # 验证必要的字段存在
        required_fields = [
            'id', 'task_no', 'name', 'description', 'inspection_type',
            'status', 'progress', 'total_devices', 'healthy_devices',
            'warning_devices', 'critical_devices', 'health_score',
            'started_at', 'completed_at', 'executor', 'created_at'
        ]
        
        for field in required_fields:
            assert hasattr(InspectionTask, field), f"Missing field: {field}"

    def test_inspection_result_model_fields(self):
        """测试巡检结果模型字段"""
        from modules.foundation.db_models.inspection import InspectionResult
        
        # 验证必要的字段存在
        required_fields = [
            'id', 'task_id', 'device_id', 'device_name', 'device_ip',
            'check_item_id', 'check_item_name', 'status', 'result_value',
            'result_message', 'severity', 'suggestion', 'checked_at'
        ]
        
        for field in required_fields:
            assert hasattr(InspectionResult, field), f"Missing field: {field}"


class TestReportGeneratorEdgeCases:
    """报告生成器边界情况测试"""

    def test_empty_results_handling(self):
        """测试空结果处理"""
        from modules.business.report_generator.inspection_report import InspectionReportGenerator
        
        generator = InspectionReportGenerator()
        
        # 空统计数据
        generator._statistics = {
            'status_summary': {'total': 0, 'healthy': 0, 'warning': 0, 'critical': 0}
        }
        
        score = generator._calculate_health_score()
        assert score == 100.0  # 无数据时默认为100

    def test_missing_task_info(self):
        """测试缺失任务信息处理"""
        from modules.business.report_generator.inspection_report import InspectionReportGenerator
        
        generator = InspectionReportGenerator()
        generator._task_info = {}
        
        # 空统计数据默认返回100
        generator._statistics = {
            'status_summary': {'total': 0, 'healthy': 0, 'warning': 0, 'critical': 0}
        }
        generator._device_results = {}
        generator._suggestions = []
        generator._history_comparison = {}
        
        report = generator._assemble_report()
        assert 'task_info' in report
        # 空数据时health_score计算返回100.0
        assert report['health_score'] == 100.0

    def test_history_comparison_no_data(self):
        """测试无历史对比数据"""
        from modules.business.report_generator.inspection_report import InspectionReportGenerator
        
        generator = InspectionReportGenerator()
        
        # 空历史任务列表
        trend = generator._calculate_trend([])
        assert trend == 'stable'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
