"""
告警触发自动化测试
BM-01 告警触发规则引擎单元测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from importlib import util

import sys
import os

# 直接从模块文件导入，避免通过 modules.business.__init__.py 触发所有依赖
def import_from_path(module_name, file_path):
    spec = util.spec_from_file_location(module_name, file_path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

alert_trigger_path = '/home/zcxx/.hermes/projects/itops_platform/modules/business/monitoring/alert_trigger.py'
at = import_from_path('alert_trigger', alert_trigger_path)
AlertTriggerEngine = at.AlertTriggerEngine
TriggerRule = at.TriggerRule
TriggerCondition = at.TriggerCondition
TriggerStatus = at.TriggerStatus
TriggerEvent = at.TriggerEvent


class TestAlertTriggerEngine:
    """告警触发引擎测试"""
    
    def setup_method(self):
        """每个测试方法前 setup"""
        self.engine = AlertTriggerEngine()
        self.TriggerRule = TriggerRule
        self.TriggerCondition = TriggerCondition
        self.TriggerStatus = TriggerStatus
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        assert self.engine is not None
        assert len(self.engine._rules) == 0
        assert len(self.engine._events) == 0
    
    def test_add_rule(self):
        """测试添加规则"""
        rule = self.TriggerRule(
            id='test-rule-1',
            name='CPU告警规则',
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={'metric': 'cpu_usage', 'operator': '>', 'value': 80},
            alert_level='warning',
        )
        
        rule_id = self.engine.add_rule(rule)
        assert rule_id == 'test-rule-1'
        assert len(self.engine.list_rules()) == 1
        
        added_rule = self.engine.get_rule('test-rule-1')
        assert added_rule is not None
        assert added_rule.name == 'CPU告警规则'
    
    def test_update_rule(self):
        """测试更新规则"""
        rule = self.TriggerRule(
            id='test-rule-2',
            name='原始名称',
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={'metric': 'cpu_usage', 'operator': '>', 'value': 80},
        )
        self.engine.add_rule(rule)
        
        # 更新规则
        rule.name = '新名称'
        rule.match_conditions = {'metric': 'memory_usage', 'operator': '>', 'value': 90}
        self.engine.update_rule(rule)
        
        updated_rule = self.engine.get_rule('test-rule-2')
        assert updated_rule.name == '新名称'
        assert updated_rule.match_conditions['metric'] == 'memory_usage'
    
    def test_delete_rule(self):
        """测试删除规则"""
        rule = self.TriggerRule(
            id='test-rule-3',
            name='待删除规则',
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={'metric': 'cpu_usage', 'operator': '>', 'value': 80},
        )
        self.engine.add_rule(rule)
        assert len(self.engine.list_rules()) == 1
        
        # 删除
        result = self.engine.delete_rule('test-rule-3')
        assert result is True
        assert len(self.engine.list_rules()) == 0
        
        # 删除不存在的规则
        result = self.engine.delete_rule('non-existent')
        assert result is False
    
    def test_list_rules_enabled_only(self):
        """测试只获取启用的规则"""
        rule1 = self.TriggerRule(
            id='enabled-rule',
            name='启用规则',
            enabled=True,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={},
        )
        rule2 = self.TriggerRule(
            id='disabled-rule',
            name='禁用规则',
            enabled=False,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={},
        )
        
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        
        all_rules = self.engine.list_rules(enabled_only=False)
        assert len(all_rules) == 2
        
        enabled_rules = self.engine.list_rules(enabled_only=True)
        assert len(enabled_rules) == 1
        assert enabled_rules[0].id == 'enabled-rule'
    
    def test_evaluate_threshold(self):
        """测试阈值评估"""
        # 测试大于
        assert self.engine.evaluate_threshold('cpu', 85, '>', 80) is True
        assert self.engine.evaluate_threshold('cpu', 75, '>', 80) is False
        
        # 测试小于
        assert self.engine.evaluate_threshold('cpu', 75, '<', 80) is True
        assert self.engine.evaluate_threshold('cpu', 85, '<', 80) is False
        
        # 测试大于等于
        assert self.engine.evaluate_threshold('cpu', 80, '>=', 80) is True
        assert self.engine.evaluate_threshold('cpu', 85, '>=', 80) is True
        assert self.engine.evaluate_threshold('cpu', 75, '>=', 80) is False
        
        # 测试小于等于
        assert self.engine.evaluate_threshold('cpu', 80, '<=', 80) is True
        assert self.engine.evaluate_threshold('cpu', 75, '<=', 80) is True
        assert self.engine.evaluate_threshold('cpu', 85, '<=', 80) is False
        
        # 测试等于
        assert self.engine.evaluate_threshold('cpu', 80, '==', 80) is True
        assert self.engine.evaluate_threshold('cpu', 85, '==', 80) is False
    
    def test_evaluate_change(self):
        """测试变化评估"""
        # 上升50%
        assert self.engine.evaluate_change(150, 100, 50) is True
        # 下降50%
        assert self.engine.evaluate_change(50, 100, 50) is True
        # 变化30%但阈值为50%
        assert self.engine.evaluate_change(130, 100, 50) is False
        # 零变化
        assert self.engine.evaluate_change(100, 100, 50) is False
        # 从零上升
        assert self.engine.evaluate_change(10, 0, 50) is True
    
    def test_evaluate_rate(self):
        """测试速率评估"""
        assert self.engine.evaluate_rate(110, 100, 10) is True
        assert self.engine.evaluate_rate(105, 100, 10) is False
        assert self.engine.evaluate_rate(90, 100, 10) is True  # 负速率也触发
        assert self.engine.evaluate_rate(100, 100, 10) is False
    
    def test_evaluate_constant(self):
        """测试持续条件评估"""
        start_time = datetime.now() - timedelta(seconds=300)
        assert self.engine.evaluate_constant(300, start_time) is True
        assert self.engine.evaluate_constant(600, start_time) is False
        
        start_time = datetime.now() - timedelta(seconds=60)
        assert self.engine.evaluate_constant(300, start_time) is False
    
    def test_evaluate_expression(self):
        """测试表达式评估"""
        context = {'value': 85, 'previous_value': 75, 'metric': 'cpu_usage'}
        
        # 简单表达式
        assert self.engine.evaluate_expression('value > 80', context) is True
        assert self.engine.evaluate_expression('value < 80', context) is True
        assert self.engine.evaluate_expression('value == 85', context) is True
        
        # 复合表达式
        assert self.engine.evaluate_expression('value > 80 and previous_value > 70', context) is True
        assert self.engine.evaluate_expression('value > 90 or previous_value > 70', context) is True
        assert self.engine.evaluate_expression('value > 90 and previous_value > 70', context) is False
    
    def test_should_trigger_with_enabled(self):
        """测试启用状态的触发检查"""
        rule = self.TriggerRule(
            id='test-rule',
            name='测试规则',
            enabled=True,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={'metric': 'cpu_usage', 'operator': '>', 'value': 80},
            trigger_interval=60,
        )
        self.engine.add_rule(rule)
        
        # 未触发过，应该可以触发
        assert self.engine._should_trigger(rule, 1, 'cpu_usage') is True
    
    def test_should_trigger_with_interval(self):
        """测试触发间隔检查"""
        rule = self.TriggerRule(
            id='test-rule-interval',
            name='间隔规则',
            enabled=True,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={},
            trigger_interval=300,  # 5分钟
        )
        self.engine.add_rule(rule)
        
        # 第一次触发
        assert self.engine._should_trigger(rule, 1, 'cpu_usage') is True
        
        # 刚触发过，不应该再次触发
        self.engine._last_trigger_time[rule.id] = datetime.now()
        assert self.engine._should_trigger(rule, 1, 'cpu_usage') is False
        
        # 超过间隔后可以再次触发
        self.engine._last_trigger_time[rule.id] = datetime.now() - timedelta(seconds=400)
        assert self.engine._should_trigger(rule, 1, 'cpu_usage') is True
    
    def test_should_trigger_with_suppress(self):
        """测试抑制检查"""
        rule = self.TriggerRule(
            id='test-rule-suppress',
            name='抑制规则',
            enabled=True,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={},
            suppress_enabled=True,
            suppress_duration=300,
            suppress_key='test-suppress-key',
        )
        self.engine.add_rule(rule)
        
        # 未被抑制，应该可以触发
        assert self.engine._should_trigger(rule, 1, 'cpu_usage') is True
        
        # 添加抑制
        self.engine._add_suppress(rule, 1, 'cpu_usage')
        assert self.engine._should_trigger(rule, 1, 'cpu_usage') is False
        
        # 抑制过期后可以再次触发
        self.engine._suppressed_keys['test-suppress-key'] = datetime.now() - timedelta(seconds=400)
        assert self.engine._should_trigger(rule, 1, 'cpu_usage') is True
    
    def test_should_trigger_with_time_window(self):
        """测试时间窗口检查"""
        # 设置只在工作时间触发
        now = datetime.now()
        work_start = (now - timedelta(hours=now.hour)).hour if now.hour >= 9 else 9
        work_end = 18
        
        rule = self.TriggerRule(
            id='test-rule-window',
            name='时间窗口规则',
            enabled=True,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={},
            time_windows=[{
                'days': [0, 1, 2, 3, 4, 5, 6],  # 每天
                'start_hour': 0,
                'end_hour': 23,
            }],
        )
        
        # 只要在规则范围内就可以触发
        assert self.engine._should_trigger(rule, 1, 'cpu_usage') is True
    
    @pytest.mark.asyncio
    async def test_evaluate_and_trigger_threshold(self):
        """测试阈值条件触发"""
        rule = self.TriggerRule(
            id='trigger-test-rule',
            name='阈值触发测试',
            enabled=True,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={
                'metric': 'cpu_usage',
                'operator': '>',
                'value': 80
            },
            alert_level='warning',
            alert_title_template='CPU告警',
            alert_message_template='CPU使用率超过阈值',
        )
        self.engine.add_rule(rule)
        
        # 触发条件：值85 > 阈值80
        events = await self.engine.evaluate_and_trigger(
            metric_name='cpu_usage',
            value=85,
            device_id=1,
            device_name='test-server',
            device_ip='192.168.1.1',
        )
        
        assert len(events) == 1
        assert events[0].rule_id == 'trigger-test-rule'
        assert events[0].metric_value == 85
        assert events[0].threshold_value == 80
        assert events[0].alert_level == 'warning'
    
    @pytest.mark.asyncio
    async def test_evaluate_and_trigger_no_match(self):
        """测试不满足条件时不触发"""
        rule = self.TriggerRule(
            id='no-trigger-rule',
            name='不触发规则',
            enabled=True,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={
                'metric': 'cpu_usage',
                'operator': '>',
                'value': 80
            },
            alert_level='warning',
        )
        self.engine.add_rule(rule)
        
        # 不触发条件：值75 < 阈值80
        events = await self.engine.evaluate_and_trigger(
            metric_name='cpu_usage',
            value=75,
            device_id=1,
            device_name='test-server',
            device_ip='192.168.1.1',
        )
        
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_evaluate_and_trigger_device_filter(self):
        """测试设备过滤"""
        rule = self.TriggerRule(
            id='device-filter-rule',
            name='设备过滤规则',
            enabled=True,
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={
                'metric': 'cpu_usage',
                'operator': '>',
                'value': 80
            },
            device_ids=[1, 2, 3],  # 只监控设备1,2,3
            alert_level='warning',
        )
        self.engine.add_rule(rule)
        
        # 设备1应该触发
        events = await self.engine.evaluate_and_trigger(
            metric_name='cpu_usage',
            value=85,
            device_id=1,
            device_name='server-1',
            device_ip='192.168.1.1',
        )
        assert len(events) == 1
        
        # 设备10不应该触发
        events = await self.engine.evaluate_and_trigger(
            metric_name='cpu_usage',
            value=85,
            device_id=10,
            device_name='server-10',
            device_ip='192.168.1.10',
        )
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_evaluate_and_trigger_disabled_rule(self):
        """测试禁用规则不触发"""
        rule = self.TriggerRule(
            id='disabled-trigger-rule',
            name='已禁用规则',
            enabled=False,  # 禁用
            condition_type=self.TriggerCondition.THRESHOLD,
            match_conditions={
                'metric': 'cpu_usage',
                'operator': '>',
                'value': 80
            },
            alert_level='warning',
        )
        self.engine.add_rule(rule)
        
        events = await self.engine.evaluate_and_trigger(
            metric_name='cpu_usage',
            value=85,
            device_id=1,
            device_name='test-server',
            device_ip='192.168.1.1',
        )
        
        assert len(events) == 0
    
    def test_list_events(self):
        """测试列出触发事件"""
        from modules.business.monitoring.alert_trigger import TriggerEvent, TriggerStatus
        
        # 添加一些测试事件
        event1 = TriggerEvent(
            id='event-1',
            rule_id='rule-1',
            rule_name='规则1',
            status=TriggerStatus.TRIGGERED,
            trigger_time=datetime.now(),
            metric_name='cpu_usage',
            metric_value=85,
            threshold_value=80,
            device_id=1,
            device_name='server-1',
            device_ip='192.168.1.1',
        )
        self.engine._events['event-1'] = event1
        
        events = self.engine.list_events()
        assert len(events) == 1
        
        events = self.engine.list_events(rule_id='rule-1')
        assert len(events) == 1
        
        events = self.engine.list_events(rule_id='non-existent')
        assert len(events) == 0
    
    def test_clear_old_events(self):
        """测试清理旧事件"""
        from modules.business.monitoring.alert_trigger import TriggerEvent, TriggerStatus
        
        # 添加旧事件
        old_event = TriggerEvent(
            id='old-event',
            rule_id='rule-1',
            rule_name='规则1',
            status=TriggerStatus.TRIGGERED,
            trigger_time=datetime.now() - timedelta(hours=48),
            metric_name='cpu_usage',
            metric_value=85,
            threshold_value=80,
            device_id=1,
            device_name='server-1',
            device_ip='192.168.1.1',
        )
        old_event.created_at = datetime.now() - timedelta(hours=48)
        self.engine._events['old-event'] = old_event
        
        # 添加新事件
        new_event = TriggerEvent(
            id='new-event',
            rule_id='rule-1',
            rule_name='规则1',
            status=TriggerStatus.TRIGGERED,
            trigger_time=datetime.now(),
            metric_name='cpu_usage',
            metric_value=85,
            threshold_value=80,
            device_id=1,
            device_name='server-1',
            device_ip='192.168.1.1',
        )
        self.engine._events['new-event'] = new_event
        
        # 清理24小时前的事件
        self.engine.clear_old_events(hours=24)
        
        assert 'old-event' not in self.engine._events
        assert 'new-event' in self.engine._events


class TestTriggerRule:
    """触发规则数据类测试"""
    
    def test_trigger_rule_creation(self):
        """测试触发规则创建"""
        from modules.business.monitoring.alert_trigger import (
            TriggerRule, TriggerCondition
        )
        
        rule = TriggerRule(
            id='test-id',
            name='测试规则',
            description='测试描述',
            enabled=True,
            condition_type=TriggerCondition.THRESHOLD,
            match_conditions={'metric': 'cpu', 'operator': '>', 'value': 80},
            alert_level='warning',
            device_ids=[1, 2, 3],
            priority=50,
        )
        
        assert rule.id == 'test-id'
        assert rule.name == '测试规则'
        assert rule.enabled is True
        assert rule.condition_type == TriggerCondition.THRESHOLD
        assert rule.alert_level == 'warning'
        assert len(rule.device_ids) == 3
        assert rule.priority == 50
    
    def test_trigger_rule_to_dict(self):
        """测试触发规则转字典"""
        from modules.business.monitoring.alert_trigger import (
            TriggerRule, TriggerCondition
        )
        
        rule = TriggerRule(
            id='test-id',
            name='测试规则',
            condition_type=TriggerCondition.THRESHOLD,
            match_conditions={'metric': 'cpu'},
        )
        
        rule_dict = rule.to_dict()
        
        assert rule_dict['id'] == 'test-id'
        assert rule_dict['name'] == '测试规则'
        assert rule_dict['condition_type'] == 'threshold'
        assert rule_dict['match_conditions']['metric'] == 'cpu'


class TestTriggerEvent:
    """触发事件数据类测试"""
    
    def test_trigger_event_creation(self):
        """测试触发事件创建"""
        from modules.business.monitoring.alert_trigger import (
            TriggerEvent, TriggerStatus
        )
        
        event = TriggerEvent(
            id='event-1',
            rule_id='rule-1',
            rule_name='规则1',
            status=TriggerStatus.TRIGGERED,
            trigger_time=datetime.now(),
            metric_name='cpu_usage',
            metric_value=85,
            threshold_value=80,
            device_id=1,
            device_name='server-1',
            device_ip='192.168.1.1',
        )
        
        assert event.id == 'event-1'
        assert event.rule_id == 'rule-1'
        assert event.status == TriggerStatus.TRIGGERED
        assert event.metric_value == 85
    
    def test_trigger_event_to_dict(self):
        """测试触发事件转字典"""
        from modules.business.monitoring.alert_trigger import (
            TriggerEvent, TriggerStatus
        )
        
        event = TriggerEvent(
            id='event-1',
            rule_id='rule-1',
            rule_name='规则1',
            status=TriggerStatus.TRIGGERED,
            trigger_time=datetime(2024, 1, 1, 12, 0, 0),
            metric_name='cpu_usage',
            metric_value=85,
            threshold_value=80,
            device_id=1,
            device_name='server-1',
            device_ip='192.168.1.1',
        )
        
        event_dict = event.to_dict()
        
        assert event_dict['id'] == 'event-1'
        assert event_dict['status'] == 'triggered'
        assert event_dict['metric_value'] == 85
        assert event_dict['threshold_value'] == 80


class TestTriggerStatus:
    """触发状态枚举测试"""
    
    def test_trigger_status_values(self):
        """测试触发状态枚举值"""
        from modules.business.monitoring.alert_trigger import TriggerStatus
        
        assert TriggerStatus.PENDING.value == 'pending'
        assert TriggerStatus.TRIGGERED.value == 'triggered'
        assert TriggerStatus.SUPPRESSED.value == 'suppressed'
        assert TriggerStatus.EXPIRED.value == 'expired'


class TestTriggerCondition:
    """触发条件枚举测试"""
    
    def test_trigger_condition_values(self):
        """测试触发条件枚举值"""
        from modules.business.monitoring.alert_trigger import TriggerCondition
        
        assert TriggerCondition.THRESHOLD.value == 'threshold'
        assert TriggerCondition.CHANGE.value == 'change'
        assert TriggerCondition.RATE.value == 'rate'
        assert TriggerCondition.CONSTANT.value == 'constant'
        assert TriggerCondition.EXPRESSION.value == 'expression'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
