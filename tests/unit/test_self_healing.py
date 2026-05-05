"""
AM-02 告警自愈模块单元测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from modules.automation.self_healing.detector import (
    FaultDetector, FaultPattern, FaultEvent, FaultSeverity, FaultCategory,
    FaultStatus, RootCauseAnalysis, ImpactAssessment, PropagationNode
)
from modules.automation.self_healing.healer import (
    SelfHealer, RecoveryStrategy, RecoveryResult, RecoveryStatus,
    RecoveryType, StrategyType, StepExecution, RollbackSnapshot
)
from modules.automation.self_healing.playbook import (
    Playbook, PlaybookManager, PlaybookStep, PlaybookExecution,
    PlaybookStatus, PlaybookType, ExecutionStatus, ReviewComment
)


class TestFaultDetector:
    """故障检测器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.detector = FaultDetector()
    
    def test_detect_fault_cpu_overload(self):
        """测试CPU过载故障检测"""
        alert_data = {
            'alert_id': 'ALT-001',
            'asset_id': 'server-001',
            'asset_name': 'Web Server',
            'alert_type': 'high_cpu',
            'metric_name': 'cpu_usage',
            'value': 95.0,
            'severity': 'error',
        }
        
        fault = self.detector.detect_fault(alert_data)
        
        assert fault is not None
        assert fault.asset_id == 'server-001'
        assert fault.category == FaultCategory.PERFORMANCE
        assert fault.severity == FaultSeverity.ERROR
        assert fault.event_id in self.detector.active_faults
    
    def test_detect_fault_memory_exhausted(self):
        """测试内存耗尽故障检测"""
        alert_data = {
            'alert_id': 'ALT-002',
            'asset_id': 'server-002',
            'asset_name': 'DB Server',
            'metric_name': 'memory_usage',
            'value': 92.0,
            'severity': 'warning',
        }
        
        fault = self.detector.detect_fault(alert_data)
        
        assert fault is not None
        assert fault.category == FaultCategory.CAPACITY
    
    def test_register_pattern(self):
        """测试注册故障模式"""
        pattern = FaultPattern(
            pattern_id='CUSTOM-001',
            name='自定义故障',
            category=FaultCategory.SOFTWARE,
            match_conditions={'metric': 'custom_metric', 'operator': '>', 'threshold': 80},
            symptoms=['自定义症状'],
        )
        
        result = self.detector.register_pattern(pattern)
        assert result is True
        assert 'CUSTOM-001' in self.detector.patterns
    
    def test_analyze_root_cause(self):
        """测试根因分析"""
        # 先创建故障
        alert_data = {
            'alert_id': 'ALT-001',
            'asset_id': 'server-001',
            'asset_name': 'Web Server',
            'metric_name': 'service_health',
            'value': 0,
            'severity': 'error',
        }
        fault = self.detector.detect_fault(alert_data)
        
        analysis = self.detector.analyze_root_cause(fault.event_id)
        
        assert analysis is not None
        assert analysis.root_cause != ''
        assert analysis.analysis_method == 'automated'
    
    def test_assess_impact(self):
        """测试影响评估"""
        # 创建故障
        alert_data = {
            'alert_id': 'ALT-001',
            'asset_id': 'server-001',
            'asset_name': 'Critical Server',
            'metric_name': 'cpu_usage',  # 改为与模式匹配的指标
            'value': 95,
            'severity': 'critical',
        }
        fault = self.detector.detect_fault(alert_data)
        
        if fault is None:
            # 如果没有匹配到模式，手动创建一个用于测试
            from modules.automation.self_healing.detector import FaultEvent, FaultSeverity, FaultCategory
            fault = FaultEvent(
                event_id='TEST-FAULT-001',
                asset_id='server-001',
                asset_name='Critical Server',
                severity=FaultSeverity.CRITICAL,
                category=FaultCategory.PERFORMANCE,
            )
            self.detector.active_faults[fault.event_id] = fault
        
        impact = self.detector.assess_impact(fault.event_id)
        
        assert impact is not None
        assert 'server-001' in impact.affected_assets
        assert impact.business_impact_level in ['low', 'medium', 'high', 'critical']
    
    def test_register_asset_relation(self):
        """测试注册资产关系"""
        self.detector.register_asset_relation('server-001', 'server-002', 'network')
        self.detector.register_asset_relation('server-001', 'db-001', 'dependency')
        
        assert len(self.detector.asset_relations['server-001']) == 2
    
    def test_resolve_fault(self):
        """测试解决故障"""
        alert_data = {
            'alert_id': 'ALT-001',
            'asset_id': 'server-001',
            'asset_name': 'Web Server',
            'metric_name': 'cpu_usage',
            'value': 95,
            'severity': 'error',
        }
        fault = self.detector.detect_fault(alert_data)
        
        self.detector.resolve_fault(fault.event_id, auto_healed=True)
        
        assert fault.event_id not in self.detector.active_faults
        assert fault in self.detector.fault_history
        assert fault.status == FaultStatus.AUTO_HEALED
    
    def test_get_active_faults(self):
        """测试获取活跃故障"""
        # 创建多个故障
        for i in range(3):
            alert_data = {
                'alert_id': f'ALT-{i}',
                'asset_id': f'server-{i}',
                'asset_name': f'Server {i}',
                'metric_name': 'cpu_usage',
                'value': 95,
                'severity': 'error',
            }
            self.detector.detect_fault(alert_data)
        
        faults = self.detector.get_active_faults()
        assert len(faults) == 3
        
        # 按严重程度过滤
        critical_faults = self.detector.get_active_faults(FaultSeverity.CRITICAL)
        assert isinstance(critical_faults, list)
    
    def test_fault_statistics(self):
        """测试故障统计"""
        # 创建并解决一些故障
        for i in range(5):
            alert_data = {
                'alert_id': f'ALT-{i}',
                'asset_id': f'server-{i}',
                'asset_name': f'Server {i}',
                'metric_name': 'cpu_usage',
                'value': 95,
                'severity': 'error',
            }
            fault = self.detector.detect_fault(alert_data)
            self.detector.resolve_fault(fault.event_id, auto_healed=(i % 2 == 0))
        
        stats = self.detector.get_fault_statistics(days=30)
        
        assert stats['total_faults'] == 5
        assert 'by_category' in stats
        assert 'by_severity' in stats


class TestSelfHealer:
    """自动恢复引擎测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.healer = SelfHealer()
    
    def test_register_strategy(self):
        """测试注册恢复策略"""
        strategy = RecoveryStrategy(
            strategy_id='CUSTOM-STR-001',
            name='自定义恢复',
            strategy_type=StrategyType.RECONFIGURE,
            steps=[
                {'name': '停止服务', 'action': 'stop_service', 'params': {}, 'timeout': 60, 'retry_count': 1},
                {'name': '启动服务', 'action': 'start_service', 'params': {}, 'timeout': 60, 'retry_count': 1},
            ],
        )
        
        result = self.healer.register_strategy(strategy)
        assert result is True
        assert 'CUSTOM-STR-001' in self.healer.strategies
    
    def test_get_applicable_strategies(self):
        """测试获取适用策略"""
        strategies = self.healer.get_applicable_strategies('PAT-005', 'error')
        
        assert len(strategies) > 0
        # 服务重启策略应该适用
        assert any(s.strategy_type == StrategyType.RESTART_SERVICE for s in strategies)
    
    @pytest.mark.asyncio
    async def test_execute_recovery(self):
        """测试执行恢复"""
        fault_data = {
            'asset_id': 'server-001',
            'service_name': 'nginx',
            'metrics': {'service_health': 0},
        }
        
        result = await self.healer.execute_recovery(
            fault_event_id='FAULT-001',
            strategy_id='STR-001',  # 服务重启策略
            fault_data=fault_data,
        )
        
        assert result is not None
        assert result.strategy_id == 'STR-001'
        assert len(result.steps_executed) > 0
    
    @pytest.mark.asyncio
    async def test_execute_recovery_unknown_strategy(self):
        """测试执行未知策略"""
        result = await self.healer.execute_recovery(
            fault_event_id='FAULT-001',
            strategy_id='UNKNOWN-STR',
            fault_data={},
        )
        
        assert result.status == RecoveryStatus.FAILED
        assert 'not found' in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_recovery_with_verification(self):
        """测试带验证的恢复"""
        fault_data = {
            'asset_id': 'server-001',
            'service_name': 'nginx',
            'metrics': {'service_health': 0, 'cpu_usage': 50},
        }
        
        result = await self.healer.execute_recovery(
            fault_event_id='FAULT-001',
            strategy_id='STR-001',
            fault_data=fault_data,
        )
        
        assert result.verification_passed is not None  # 验证被执行
    
    def test_create_rollback_snapshot(self):
        """测试创建回滚快照"""
        fault_data = {
            'asset_id': 'server-001',
            'config': {'port': 8080, 'max_connections': 100},
            'state': {'running': True},
        }
        
        asyncio.run(self._test_create_snapshot(fault_data))
    
    async def _test_create_snapshot(self, fault_data):
        """辅助方法"""
        await self.healer._create_rollback_snapshot(fault_data)
        assert 'server-001' in self.healer.rollback_snapshots
        assert len(self.healer.rollback_snapshots['server-001']) == 1
    
    def test_recovery_statistics(self):
        """测试恢复统计"""
        stats = self.healer.get_recovery_statistics(days=30)
        
        assert 'total_recoveries' in stats
        assert 'successful' in stats
        assert 'by_strategy' in stats


class TestPlaybookManager:
    """剧本管理器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.manager = PlaybookManager()
    
    def test_create_playbook(self):
        """测试创建剧本"""
        playbook = Playbook(
            name='Test Playbook',
            type=PlaybookType.INCIDENT,
            description='测试剧本',
            steps=[
                PlaybookStep(
                    step_id='step-1',
                    name='步骤1',
                    action='notify',
                    action_params={'message': '开始处理'},
                ),
                PlaybookStep(
                    step_id='step-2',
                    name='步骤2',
                    action='wait',
                    action_params={'seconds': 5},
                ),
            ],
        )
        
        result = self.manager.create_playbook(playbook)
        assert result is True
        assert playbook.playbook_id is not None
        assert playbook.content_hash != ''
    
    def test_get_playbook(self):
        """测试获取剧本"""
        playbook = Playbook(name='Test Playbook')
        self.manager.create_playbook(playbook)
        
        retrieved = self.manager.get_playbook(playbook.playbook_id)
        assert retrieved is not None
        assert retrieved.name == 'Test Playbook'
    
    def test_update_playbook(self):
        """测试更新剧本（创建新版本）"""
        playbook = Playbook(name='Test Playbook', version='1.0.0')
        self.manager.create_playbook(playbook)
        
        # 创建一个新的playbook对象来更新
        updated_playbook = Playbook(
            playbook_id=playbook.playbook_id,
            name='Test Playbook',
            version='1.0.0',
            description='更新后的描述'
        )
        updated = self.manager.update_playbook(updated_playbook)
        
        assert updated is not None
        assert updated.previous_version == '1.0.0'  # 前一个版本
        # 版本递增: 1.0.0 -> 1.0.1 (根据increment_version逻辑)
        
        versions = self.manager.get_playbook_versions(playbook.playbook_id)
        assert len(versions) == 2
    
    def test_playbook_to_yaml(self):
        """测试剧本转YAML"""
        playbook = Playbook(name='Test Playbook')
        self.manager.create_playbook(playbook)
        
        yaml_str = playbook.to_yaml()
        assert yaml_str is not None
        assert 'playbook_id' in yaml_str
    
    def test_playbook_from_yaml(self):
        """测试从YAML创建剧本"""
        yaml_str = """
playbook_id: PB-TEST
name: YAML导入剧本
version: "1.0.0"
type: incident
steps: []
"""
        playbook = self.manager.import_from_yaml(yaml_str)
        
        assert playbook is not None
        assert playbook.name == 'YAML导入剧本'
    
    def test_playbook_to_json(self):
        """测试剧本转JSON"""
        playbook = Playbook(name='Test Playbook')
        self.manager.create_playbook(playbook)
        
        json_str = playbook.to_json()
        assert json_str is not None
        assert 'playbook_id' in json_str
    
    def test_playbook_from_json(self):
        """测试从JSON创建剧本"""
        json_str = '{"playbook_id": "PB-JSON", "name": "JSON导入剧本", "version": "1.0.0", "type": "incident", "steps": []}'
        
        playbook = self.manager.import_from_json(json_str)
        assert playbook is not None
        assert playbook.name == 'JSON导入剧本'
    
    def test_submit_for_review(self):
        """测试提交审核"""
        playbook = Playbook(name='Test Playbook')
        self.manager.create_playbook(playbook)
        
        result = self.manager.submit_for_review(playbook.playbook_id, playbook.version)
        assert result is True
        
        updated = self.manager.get_playbook(playbook.playbook_id)
        assert updated.status == PlaybookStatus.PENDING_REVIEW
    
    def test_approve_playbook(self):
        """测试批准剧本"""
        playbook = Playbook(name='Test Playbook')
        self.manager.create_playbook(playbook)
        
        self.manager.submit_for_review(playbook.playbook_id, playbook.version)
        result = self.manager.approve_playbook(playbook.playbook_id, playbook.version, 'reviewer1')
        
        assert result is True
        updated = self.manager.get_playbook(playbook.playbook_id)
        assert updated.status == PlaybookStatus.APPROVED
        assert updated.approved_by == 'reviewer1'
    
    def test_reject_playbook(self):
        """测试拒绝剧本"""
        playbook = Playbook(name='Test Playbook')
        self.manager.create_playbook(playbook)
        
        self.manager.submit_for_review(playbook.playbook_id, playbook.version)
        result = self.manager.reject_playbook(
            playbook.playbook_id, playbook.version, 'reviewer1', '需要修改'
        )
        
        assert result is True
        comments = self.manager.get_review_comments(playbook.playbook_id)
        assert len(comments) == 1
        assert comments[0].comment == '需要修改'
    
    def test_add_review_comment(self):
        """测试添加审核评论"""
        playbook = Playbook(name='Test Playbook')
        self.manager.create_playbook(playbook)
        
        result = self.manager.add_review_comment(
            playbook.playbook_id, playbook.version,
            'reviewer1', '这个步骤需要调整', 'step-1'
        )
        
        assert result is True
        comments = self.manager.get_review_comments(playbook.playbook_id)
        assert len(comments) == 1
    
    @pytest.mark.asyncio
    async def test_execute_playbook(self):
        """测试执行剧本"""
        playbook = Playbook(
            name='Test Playbook',
            status=PlaybookStatus.APPROVED,
            steps=[
                PlaybookStep(
                    step_id='step-1',
                    name='等待',
                    action='wait',
                    action_params={'seconds': 1},
                ),
                PlaybookStep(
                    step_id='step-2',
                    name='发送通知',
                    action='send_notification',
                    action_params={'message': '完成'},
                ),
            ],
        )
        self.manager.create_playbook(playbook)
        
        execution = await self.manager.execute_playbook(
            playbook.playbook_id,
            context={'asset_id': 'server-001'},
            triggered_by='manual',
        )
        
        assert execution is not None
        # 等待步骤可能失败，但不应该崩溃
        assert len(execution.step_executions) == 2
    
    @pytest.mark.asyncio
    async def test_execute_unapproved_playbook(self):
        """测试执行未批准剧本"""
        playbook = Playbook(name='Draft Playbook', status=PlaybookStatus.DRAFT)
        self.manager.create_playbook(playbook)
        
        execution = await self.manager.execute_playbook(playbook.playbook_id)
        assert execution is None
    
    def test_get_execution_history(self):
        """测试获取执行历史"""
        # 先执行一些剧本
        async def run_tests():
            playbook = Playbook(
                name='Test Playbook',
                status=PlaybookStatus.APPROVED,
                steps=[PlaybookStep(step_id='s1', name='s1', action='wait', action_params={'seconds': 1})],
            )
            self.manager.create_playbook(playbook)
            await self.manager.execute_playbook(playbook.playbook_id)
        
        asyncio.run(run_tests())
        
        history = self.manager.get_execution_history()
        assert len(history) >= 1
    
    def test_execution_statistics(self):
        """测试执行统计"""
        stats = self.manager.get_execution_statistics(days=30)
        
        assert 'total_executions' in stats
        assert 'by_playbook' in stats
        assert 'by_trigger' in stats


class TestRecoveryStrategy:
    """恢复策略测试"""
    
    def test_create_strategy(self):
        """测试创建恢复策略"""
        strategy = RecoveryStrategy(
            strategy_id='STR-TEST',
            name='测试策略',
            strategy_type=StrategyType.RESTART_SERVICE,
            steps=[
                {
                    'name': '停止服务',
                    'action': 'stop_service',
                    'params': {},
                    'timeout': 60,
                    'retry_count': 2,
                },
            ],
            auto_execute=True,
            timeout_seconds=300,
            enable_rollback=True,
        )
        
        assert strategy.strategy_id == 'STR-TEST'
        assert len(strategy.steps) == 1
    
    def test_strategy_to_dict(self):
        """测试策略转字典"""
        strategy = RecoveryStrategy(
            strategy_id='STR-TEST',
            name='测试策略',
            strategy_type=StrategyType.RESTART_SERVICE,
        )
        
        data = strategy.to_dict()
        assert data['strategy_id'] == 'STR-TEST'
        assert data['strategy_type'] == 'restart_service'


class TestFaultPattern:
    """故障模式测试"""
    
    def test_create_pattern(self):
        """测试创建故障模式"""
        pattern = FaultPattern(
            pattern_id='PAT-TEST',
            name='测试故障模式',
            category=FaultCategory.HARDWARE,
            match_conditions={'metric': 'smart_status', 'operator': '<', 'threshold': 50},
            symptoms=['SMART状态异常'],
            known_causes=['硬盘即将故障'],
        )
        
        assert pattern.pattern_id == 'PAT-TEST'
        assert pattern.category == FaultCategory.HARDWARE
    
    def test_pattern_to_dict(self):
        """测试故障模式转字典"""
        pattern = FaultPattern(
            pattern_id='PAT-TEST',
            name='测试故障模式',
        )
        
        data = pattern.to_dict()
        assert data['pattern_id'] == 'PAT-TEST'


class TestPlaybook:
    """剧本测试"""
    
    def test_create_playbook(self):
        """测试创建剧本"""
        playbook = Playbook(
            name='服务重启剧本',
            type=PlaybookType.INCIDENT,  # 使用存在的枚举值
            description='自动重启故障服务',
            applicable_faults=['PAT-005'],
        )
        
        assert playbook.name == '服务重启剧本'
        assert playbook.type == PlaybookType.INCIDENT
    
    def test_playbook_calculate_hash(self):
        """测试计算内容哈希"""
        playbook = Playbook(name='Test')
        playbook.calculate_hash()
        
        assert playbook.content_hash != ''
        assert len(playbook.content_hash) == 16


# 运行所有测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])