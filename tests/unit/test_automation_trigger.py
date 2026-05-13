"""
告警触发自动化测试 (D1)
测试 modules.automation.alert_trigger 模块的数据模型
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from importlib import util
import sys


# 导入 models 模块
models_path = '/home/zcxx/.hermes/projects/itops_platform/modules/automation/alert_trigger/models.py'

models_spec = util.spec_from_file_location('trigger_models', models_path)
models_module = util.module_from_spec(models_spec)
sys.modules['modules.automation.alert_trigger.models'] = models_module
models_spec.loader.exec_module(models_module)

AlertTriggerRule = models_module.AlertTriggerRule
TriggerEvent = models_module.TriggerEvent
ActionConfig = models_module.ActionConfig
ActionType = models_module.ActionType
ConditionConfig = models_module.ConditionConfig
AlertLevel = models_module.AlertLevel


class TestAlertTriggerRule:
    """告警触发规则数据模型测试"""
    
    def test_rule_creation(self):
        """测试规则创建"""
        rule = AlertTriggerRule(
            id="test-rule-1",
            name="CPU告警规则",
            description="CPU使用率超过80%时触发",
            enabled=True,
            condition=ConditionConfig(
                condition_type="threshold",
                metric_name="cpu_usage",
                operator=">",
                threshold_value=80.0,
            ),
            alert_level="high",
            device_ids=[1, 2, 3],
            device_tags=["production", "web"],
            trigger_interval=300,
            suppress_enabled=True,
            suppress_duration=600,
            actions=[
                ActionConfig(
                    action_type=ActionType.SCRIPT,
                    enabled=True,
                    script_name="restart_service.sh",
                    script_params={"service": "nginx"},
                )
            ],
        )
        
        assert rule.id == "test-rule-1"
        assert rule.name == "CPU告警规则"
        assert rule.enabled is True
        assert rule.condition.metric_name == "cpu_usage"
        assert rule.condition.operator == ">"
        assert rule.condition.threshold_value == 80.0
        assert len(rule.actions) == 1
        assert rule.actions[0].script_name == "restart_service.sh"
    
    def test_rule_to_dict(self):
        """测试规则转换为字典"""
        rule = AlertTriggerRule(
            id="test-rule-2",
            name="Memory告警规则",
            alert_level="critical",
            condition=ConditionConfig(
                condition_type="threshold",
                metric_name="memory_usage",
                operator=">=",
                threshold_value=90.0,
            ),
        )
        
        rule_dict = rule.to_dict()
        assert rule_dict["id"] == "test-rule-2"
        assert rule_dict["condition"]["metric_name"] == "memory_usage"
        assert rule_dict["alert_level"] == "critical"


class TestConditionConfig:
    """触发条件配置测试"""
    
    def test_threshold_condition(self):
        """测试阈值条件"""
        cond = ConditionConfig(
            condition_type="threshold",
            metric_name="cpu_usage",
            operator=">",
            threshold_value=80.0,
        )
        
        assert cond.condition_type == "threshold"
        assert cond.operator == ">"
        assert cond.threshold_value == 80.0
    
    def test_change_condition(self):
        """测试变化条件"""
        cond = ConditionConfig(
            condition_type="change",
            metric_name="cpu_usage",
            change_percent=10.0,
        )
        
        assert cond.condition_type == "change"
        assert cond.change_percent == 10.0
    
    def test_rate_condition(self):
        """测试速率条件"""
        cond = ConditionConfig(
            condition_type="rate",
            metric_name="request_count",
            rate_percent=50.0,
        )
        
        assert cond.condition_type == "rate"
        assert cond.rate_percent == 50.0
    
    def test_expression_condition(self):
        """测试表达式条件"""
        cond = ConditionConfig(
            condition_type="expression",
            expression="{cpu} > 80 and {memory} < 90",
        )
        
        assert cond.condition_type == "expression"
        assert "cpu" in cond.expression


class TestActionConfig:
    """动作配置测试"""
    
    def test_script_action(self):
        """测试脚本动作配置"""
        action = ActionConfig(
            action_type=ActionType.SCRIPT,
            enabled=True,
            script_name="restart.sh",
            script_params={"service": "nginx"},
        )
        
        assert action.action_type == ActionType.SCRIPT
        assert action.script_name == "restart.sh"
        assert action.script_params["service"] == "nginx"
    
    def test_workorder_action(self):
        """测试工单动作配置"""
        action = ActionConfig(
            action_type=ActionType.WORKORDER,
            enabled=True,
            workorder_title_template="服务器 {device_name} 告警",
            workorder_description_template="指标 {metric_name} 超过阈值",
            workorder_priority="P1",
        )
        
        assert action.action_type == ActionType.WORKORDER
        assert "nginx" not in action.workorder_title_template  # 模板未被替换
    
    def test_notification_action(self):
        """测试通知动作配置"""
        action = ActionConfig(
            action_type=ActionType.NOTIFICATION,
            enabled=True,
            notification_channels=["email", "sms"],
            notification_receivers=["ops-team"],
            notification_template="告警: {alert_message}",
        )
        
        assert action.action_type == ActionType.NOTIFICATION
        assert "email" in action.notification_channels
        assert "sms" in action.notification_channels
    
    def test_action_enabled_disabled(self):
        """测试动作启用/禁用"""
        action_enabled = ActionConfig(
            action_type=ActionType.SCRIPT,
            enabled=True,
        )
        action_disabled = ActionConfig(
            action_type=ActionType.SCRIPT,
            enabled=False,
        )
        
        assert action_enabled.enabled is True
        assert action_disabled.enabled is False


class TestTriggerEvent:
    """触发事件测试"""
    
    def test_event_creation(self):
        """测试事件创建"""
        event = TriggerEvent(
            id="evt-001",
            rule_id="test-rule-1",
            rule_name="测试规则",
            trigger_time=datetime.now(),
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold_value=80.0,
            device_id=1,
            device_name="web-server-01",
            device_ip="192.168.1.100",
        )
        
        assert event.id == "evt-001"
        assert event.rule_name == "测试规则"
        assert event.metric_value == 85.0
        assert event.status == "pending"
        assert len(event.actions_executed) == 0
    
    def test_event_to_dict(self):
        """测试事件转换为字典"""
        event = TriggerEvent(
            id="evt-002",
            rule_id="test-rule-1",
            rule_name="测试规则",
            trigger_time=datetime.now(),
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold_value=80.0,
        )
        
        event_dict = event.to_dict()
        assert event_dict["id"] == "evt-002"
        assert event_dict["metric_value"] == 85.0
        assert event_dict["status"] == "pending"
    
    def test_event_with_execution_results(self):
        """测试带执行结果的事件"""
        event = TriggerEvent(
            id="evt-003",
            rule_id="test-rule-1",
            rule_name="测试规则",
            trigger_time=datetime.now(),
            metric_name="cpu_usage",
            metric_value=85.0,
            threshold_value=80.0,
            actions_executed=["script:restart.sh"],
            execution_results=[
                {"action_type": "script", "status": "success", "return_code": 0}
            ],
        )
        
        assert len(event.actions_executed) == 1
        assert event.actions_executed[0] == "script:restart.sh"
        assert len(event.execution_results) == 1
        assert event.execution_results[0]["status"] == "success"


class TestAlertLevel:
    """告警级别枚举测试"""
    
    def test_alert_level_values(self):
        """测试告警级别枚举值"""
        assert AlertLevel.CRITICAL.value == "critical"
        assert AlertLevel.HIGH.value == "high"
        assert AlertLevel.MEDIUM.value == "medium"
        assert AlertLevel.LOW.value == "low"
        assert AlertLevel.INFO.value == "info"


class TestActionType:
    """动作类型枚举测试"""
    
    def test_action_type_values(self):
        """测试动作类型枚举值"""
        assert ActionType.SCRIPT.value == "script"
        assert ActionType.WORKORDER.value == "workorder"
        assert ActionType.NOTIFICATION.value == "notification"


class TestRuleWithMultipleActions:
    """多动作规则测试"""
    
    def test_rule_with_multiple_actions(self):
        """测试带多个动作的规则"""
        rule = AlertTriggerRule(
            id="multi-action-rule",
            name="多动作规则",
            enabled=True,
            condition=ConditionConfig(
                condition_type="threshold",
                metric_name="cpu_usage",
                operator=">",
                threshold_value=80.0,
            ),
            actions=[
                ActionConfig(
                    action_type=ActionType.SCRIPT,
                    enabled=True,
                    script_name="auto_scale.sh",
                ),
                ActionConfig(
                    action_type=ActionType.NOTIFICATION,
                    enabled=True,
                    notification_channels=["email"],
                    notification_receivers=["ops@example.com"],
                ),
                ActionConfig(
                    action_type=ActionType.WORKORDER,
                    enabled=True,
                    workorder_title_template="CPU告警自动化工单",
                ),
            ],
        )
        
        assert len(rule.actions) == 3
        assert rule.actions[0].action_type == ActionType.SCRIPT
        assert rule.actions[1].action_type == ActionType.NOTIFICATION
        assert rule.actions[2].action_type == ActionType.WORKORDER


class TestSuppressConfig:
    """抑制配置测试"""
    
    def test_suppress_config(self):
        """测试抑制配置"""
        rule = AlertTriggerRule(
            id="suppress-test",
            name="抑制测试规则",
            condition=ConditionConfig(
                condition_type="threshold",
                metric_name="cpu_usage",
                operator=">",
                threshold_value=80.0,
            ),
            suppress_enabled=True,
            suppress_duration=600,
            suppress_key="cpu_high_{device_id}",
        )
        
        assert rule.suppress_enabled is True
        assert rule.suppress_duration == 600
        assert "device_id" in rule.suppress_key


class TestTimeWindows:
    """时间窗口测试"""
    
    def test_time_windows_config(self):
        """测试时间窗口配置"""
        rule = AlertTriggerRule(
            id="timewindow-test",
            name="时间窗口测试规则",
            condition=ConditionConfig(
                condition_type="threshold",
                metric_name="cpu_usage",
                operator=">",
                threshold_value=80.0,
            ),
            time_windows=[
                {"start": "09:00", "end": "18:00", "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]},
                {"start": "10:00", "end": "16:00", "days": ["Saturday", "Sunday"]},
            ],
        )
        
        assert len(rule.time_windows) == 2
        assert rule.time_windows[0]["start"] == "09:00"
        assert "Monday" in rule.time_windows[0]["days"]


class TestDeviceFiltering:
    """设备过滤测试"""
    
    def test_device_ids_filter(self):
        """测试设备ID过滤"""
        rule = AlertTriggerRule(
            id="device-filter-test",
            name="设备过滤测试",
            condition=ConditionConfig(
                condition_type="threshold",
                metric_name="cpu_usage",
                operator=">",
                threshold_value=80.0,
            ),
            device_ids=[101, 102, 103],
        )
        
        assert len(rule.device_ids) == 3
        assert 101 in rule.device_ids
        assert 102 in rule.device_ids
        assert 103 in rule.device_ids
    
    def test_device_tags_filter(self):
        """测试设备标签过滤"""
        rule = AlertTriggerRule(
            id="tags-filter-test",
            name="标签过滤测试",
            condition=ConditionConfig(
                condition_type="threshold",
                metric_name="cpu_usage",
                operator=">",
                threshold_value=80.0,
            ),
            device_tags=["production", "web", "database"],
        )
        
        assert len(rule.device_tags) == 3
        assert "production" in rule.device_tags
        assert "web" in rule.device_tags
    
    def test_empty_device_filter_means_all(self):
        """测试空的设备过滤意味着所有设备"""
        rule = AlertTriggerRule(
            id="no-filter-test",
            name="无过滤测试",
            condition=ConditionConfig(
                condition_type="threshold",
                metric_name="cpu_usage",
                operator=">",
                threshold_value=80.0,
            ),
            device_ids=[],  # 空列表表示所有设备
            device_tags=[],  # 空列表表示所有标签
        )
        
        assert len(rule.device_ids) == 0
        assert len(rule.device_tags) == 0


class TestTriggerInterval:
    """触发间隔测试"""
    
    def test_trigger_interval_default(self):
        """测试默认触发间隔"""
        rule = AlertTriggerRule(
            id="interval-test",
            name="间隔测试",
            condition=ConditionConfig(metric_name="cpu_usage", threshold_value=80),
        )
        
        assert rule.trigger_interval == 300  # 默认5分钟
    
    def test_trigger_interval_custom(self):
        """测试自定义触发间隔"""
        rule = AlertTriggerRule(
            id="interval-test-2",
            name="间隔测试2",
            condition=ConditionConfig(metric_name="cpu_usage", threshold_value=80),
            trigger_interval=600,  # 10分钟
        )
        
        assert rule.trigger_interval == 600


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
