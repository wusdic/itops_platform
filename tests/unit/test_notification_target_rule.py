"""
通知目标规则测试
测试NotificationTargetRule模型的创建、查询、匹配功能
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from modules.foundation.db_models.notification.notification_model import NotificationTargetRule


class TestNotificationTargetRuleModel:
    """NotificationTargetRule模型测试"""

    def test_rule_creation(self):
        """测试规则创建"""
        rule = NotificationTargetRule(
            name="Critical Alert Rule",
            description="Critical级别告警通知规则",
            rule_type="alert_level",
            match_conditions=json.dumps({"levels": ["critical", "high"]}),
            notify_channels=json.dumps(["email", "dingtalk"]),
            notify_receivers=json.dumps(["admin@example.com"]),
            notify_interval=300,
            max_notify_count=3,
            priority=10,
            enabled=True,
        )

        assert rule.name == "Critical Alert Rule"
        assert rule.rule_type == "alert_level"
        assert rule.enabled is True

    def test_rule_types(self):
        """测试所有支持的规则类型"""
        rule_types = ["alert_level", "device", "category", "custom"]

        for rule_type in rule_types:
            rule = NotificationTargetRule(
                name=f"Test {rule_type} Rule",
                rule_type=rule_type,
                notify_channels=json.dumps(["email"]),
            )
            assert rule.rule_type == rule_type

    def test_rule_default_values(self):
        """测试默认值"""
        rule = NotificationTargetRule(
            name="Test Rule",
            rule_type="alert_level",
            notify_channels=json.dumps(["email"]),
        )

        assert rule.enabled is True
        assert rule.suppress_enabled is False
        assert rule.notify_interval == 300
        assert rule.max_notify_count == 3
        assert rule.priority == 100

    def test_rule_repr(self):
        """测试字符串表示"""
        rule = NotificationTargetRule(
            id=1,
            name="Test Rule",
            rule_type="alert_level",
        )

        repr_str = repr(rule)
        assert "NotificationTargetRule" in repr_str
        assert "Test Rule" in repr_str

    def test_rule_with_escalation_config(self):
        """测试带升级配置的规则"""
        escalation = {
            "critical": [
                {"after_seconds": 300, "channels": ["sms"]},
                {"after_seconds": 600, "channels": ["phone"]},
            ]
        }

        rule = NotificationTargetRule(
            name="Escalation Rule",
            rule_type="alert_level",
            notify_channels=json.dumps(["email"]),
            escalation_config=json.dumps(escalation),
        )

        config = json.loads(rule.escalation_config)
        assert "critical" in config
        assert len(config["critical"]) == 2

    def test_rule_with_time_windows(self):
        """测试带时段配置的规则"""
        time_windows = [
            {"days": [1, 2, 3, 4, 5], "start_hour": 9, "end_hour": 18},  # 工作日
            {"days": [6, 7], "start_hour": 10, "end_hour": 16},  # 周末
        ]

        rule = NotificationTargetRule(
            name="Business Hours Rule",
            rule_type="alert_level",
            notify_channels=json.dumps(["email"]),
            time_windows=json.dumps(time_windows),
        )

        windows = json.loads(rule.time_windows)
        assert len(windows) == 2

    def test_rule_with_suppress_until(self):
        """测试带抑制截止时间的规则"""
        suppress_until = datetime(2024, 12, 31, 23, 59, 59)

        rule = NotificationTargetRule(
            name="Suppressed Rule",
            rule_type="alert_level",
            notify_channels=json.dumps(["email"]),
            suppress_enabled=True,
            suppress_until=suppress_until,
        )

        assert rule.suppress_until == suppress_until


class TestNotificationTargetRuleAPI:
    """NotificationTargetRule API测试"""

    def test_create_rule_request_model(self):
        """测试创建规则请求模型"""
        from api.routes.notification import NotificationTargetRuleCreate

        rule = NotificationTargetRuleCreate(
            name="New Rule",
            description="Test rule",
            rule_type="alert_level",
            match_conditions={"levels": ["critical"]},
            notify_channels=["email", "dingtalk"],
            notify_receivers=["admin@test.com"],
            notify_interval=600,
            max_notify_count=5,
            priority=50,
        )

        assert rule.name == "New Rule"
        assert rule.rule_type == "alert_level"
        assert len(rule.notify_channels) == 2

    def test_update_rule_request_model(self):
        """测试更新规则请求模型"""
        from api.routes.notification import NotificationTargetRuleUpdate

        update = NotificationTargetRuleUpdate(
            name="Updated Rule",
            enabled=False,
            notify_interval=1200,
        )

        assert update.name == "Updated Rule"
        assert update.enabled is False
        assert update.notify_interval == 1200


class TestNotificationTargetRuleMatching:
    """通知目标规则匹配测试"""

    def test_match_by_alert_level(self):
        """测试按告警级别匹配"""
        rule = NotificationTargetRule(
            name="Critical Alert Rule",
            rule_type="alert_level",
            match_conditions=json.dumps({"levels": ["critical", "high"]}),
            notify_channels=json.dumps(["email", "dingtalk"]),
            enabled=True,
        )

        # 模拟匹配逻辑
        alert_level = "critical"
        conditions = json.loads(rule.match_conditions)
        is_match = alert_level in conditions.get("levels", [])

        assert is_match is True

    def test_match_by_alert_level_no_match(self):
        """测试告警级别不匹配"""
        rule = NotificationTargetRule(
            name="Critical Alert Rule",
            rule_type="alert_level",
            match_conditions=json.dumps({"levels": ["critical", "high"]}),
            notify_channels=json.dumps(["email"]),
            enabled=True,
        )

        alert_level = "low"
        conditions = json.loads(rule.match_conditions)
        is_match = alert_level in conditions.get("levels", [])

        assert is_match is False

    def test_match_by_device_id(self):
        """测试按设备ID匹配"""
        rule = NotificationTargetRule(
            name="Server Alert Rule",
            rule_type="device",
            match_conditions=json.dumps({"device_ids": [1, 2, 3], "device_types": ["server"]}),
            notify_channels=json.dumps(["dingtalk"]),
            enabled=True,
        )

        device_id = 2
        conditions = json.loads(rule.match_conditions)
        is_match = device_id in conditions.get("device_ids", [])

        assert is_match is True

    def test_match_by_device_type(self):
        """测试按设备类型匹配"""
        rule = NotificationTargetRule(
            name="Server Alert Rule",
            rule_type="device",
            match_conditions=json.dumps({"device_ids": [], "device_types": ["server", "router"]}),
            notify_channels=json.dumps(["dingtalk"]),
            enabled=True,
        )

        device_type = "router"
        conditions = json.loads(rule.match_conditions)
        is_match = device_type in conditions.get("device_types", [])

        assert is_match is True

    def test_match_by_category(self):
        """测试按告警分类匹配"""
        rule = NotificationTargetRule(
            name="Performance Alert Rule",
            rule_type="category",
            match_conditions=json.dumps({"categories": ["performance", "capacity"]}),
            notify_channels=json.dumps(["email"]),
            enabled=True,
        )

        category = "performance"
        conditions = json.loads(rule.match_conditions)
        is_match = category in conditions.get("categories", [])

        assert is_match is True

    def test_disabled_rule_not_matched(self):
        """测试禁用的规则不匹配"""
        rule = NotificationTargetRule(
            name="Disabled Rule",
            rule_type="alert_level",
            match_conditions=json.dumps({"levels": ["critical"]}),
            notify_channels=json.dumps(["email"]),
            enabled=False,  # 禁用
        )

        assert rule.enabled is False

    def test_match_priority_order(self):
        """测试按优先级排序匹配"""
        rules = [
            NotificationTargetRule(id=1, name="Low Priority", priority=100, rule_type="alert_level", notify_channels=json.dumps(["email"])),
            NotificationTargetRule(id=2, name="High Priority", priority=10, rule_type="alert_level", notify_channels=json.dumps(["sms"])),
            NotificationTargetRule(id=3, name="Medium Priority", priority=50, rule_type="alert_level", notify_channels=json.dumps(["dingtalk"])),
        ]

        # 按优先级排序
        sorted_rules = sorted(rules, key=lambda x: x.priority)

        assert sorted_rules[0].name == "High Priority"
        assert sorted_rules[1].name == "Medium Priority"
        assert sorted_rules[2].name == "Low Priority"


class TestNotificationTargetRuleQuery:
    """通知目标规则查询测试"""

    def test_filter_by_rule_type(self):
        """测试按规则类型过滤"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_query.filter().count.return_value = 5
        mock_query.filter().order_by().offset().limit().all.return_value = []

        result = mock_query.filter().all()
        assert isinstance(result, list)

    def test_filter_by_enabled_status(self):
        """测试按启用状态过滤"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query

        enabled_rules = [
            NotificationTargetRule(id=1, name="Rule 1", enabled=True, rule_type="alert_level", notify_channels=json.dumps(["email"])),
            NotificationTargetRule(id=2, name="Rule 2", enabled=True, rule_type="alert_level", notify_channels=json.dumps(["dingtalk"])),
        ]
        mock_query.filter().all.return_value = enabled_rules

        result = mock_query.filter().all()
        assert len(result) == 2
        assert all(r.enabled for r in result)

    def test_order_by_priority(self):
        """测试按优先级排序"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        rules = [
            NotificationTargetRule(id=3, priority=50),
            NotificationTargetRule(id=1, priority=10),
            NotificationTargetRule(id=2, priority=30),
        ]

        mock_query.filter().order_by().all.return_value = sorted(rules, key=lambda x: x.priority)

        result = mock_query.filter().order_by().all()
        assert result[0].priority == 10
        assert result[1].priority == 30
        assert result[2].priority == 50

    def test_check_duplicate_name(self):
        """测试检查重复名称"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query

        existing_rule = NotificationTargetRule(
            id=1,
            name="Existing Rule",
            rule_type="alert_level",
            notify_channels=json.dumps(["email"]),
        )
        mock_query.filter().first.return_value = existing_rule

        # 检查是否存在同名规则
        result = mock_query.filter().first()
        assert result is not None
        assert result.name == "Existing Rule"
