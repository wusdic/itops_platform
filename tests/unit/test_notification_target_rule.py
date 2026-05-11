"""
通知目标规则服务层测试 (TDD)
测试 target_config.py 中的 NotificationTargetRuleService
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Optional, List

from modules.foundation.db_models.notification.notification_model import NotificationTargetRule


class TestNotificationTargetRuleService:
    """NotificationTargetRule 服务层测试"""

    @pytest.fixture
    def mock_db_session(self):
        """创建模拟的数据库会话"""
        session = MagicMock()
        session.query.return_value = session
        session.filter.return_value = session
        session.order_by.return_value = session
        session.offset.return_value = session
        session.limit.return_value = session
        session.first.return_value = None
        session.all.return_value = []
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        session.delete.return_value = None
        return session

    @pytest.fixture
    def sample_rule_data(self):
        """示例规则数据"""
        return {
            "name": "Critical Alert Rule",
            "description": "Critical级别告警通知规则",
            "rule_type": "alert_level",
            "match_conditions": {"levels": ["critical", "high"]},
            "notify_channels": ["email", "dingtalk"],
            "notify_receivers": ["admin@example.com"],
            "notify_interval": 300,
            "max_notify_count": 3,
            "priority": 10,
            "enabled": True,
        }

    @pytest.fixture
    def sample_rule(self, sample_rule_data):
        """创建示例规则对象"""
        rule = NotificationTargetRule(
            id=1,
            name=sample_rule_data["name"],
            description=sample_rule_data["description"],
            rule_type=sample_rule_data["rule_type"],
            match_conditions=json.dumps(sample_rule_data["match_conditions"]),
            notify_channels=json.dumps(sample_rule_data["notify_channels"]),
            notify_receivers=json.dumps(sample_rule_data["notify_receivers"]),
            notify_interval=sample_rule_data["notify_interval"],
            max_notify_count=sample_rule_data["max_notify_count"],
            priority=sample_rule_data["priority"],
            enabled=sample_rule_data["enabled"],
            created_at=datetime.now(),
        )
        return rule

    def test_service_can_be_instantiated(self, mock_db_session):
        """测试服务可以实例化"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        service = NotificationTargetRuleService(mock_db_session)
        assert service is not None
        assert service.db == mock_db_session

    def test_create_rule(self, mock_db_session, sample_rule_data):
        """测试创建规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        # Mock query to return no existing rule
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.create_rule(sample_rule_data)
        
        # 验证规则创建成功
        assert result is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_create_rule_with_duplicate_name(self, mock_db_session, sample_rule_data, sample_rule):
        """测试创建重复名称规则应抛出异常"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        # Mock existing rule
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_rule
        
        service = NotificationTargetRuleService(mock_db_session)
        
        with pytest.raises(ValueError, match="规则名称已存在"):
            service.create_rule(sample_rule_data)

    def test_get_rule_by_id(self, mock_db_session, sample_rule):
        """测试通过ID获取规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_rule
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.get_rule_by_id(1)
        
        assert result is not None
        assert result.id == 1
        assert result.name == sample_rule.name

    def test_get_rule_by_id_not_found(self, mock_db_session):
        """测试获取不存在的规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.get_rule_by_id(999)
        
        assert result is None

    def test_list_rules(self, mock_db_session, sample_rule):
        """测试列出规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = [sample_rule]
        mock_db_session.query.return_value.count.return_value = 1
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.list_rules()
        
        assert len(result) == 1
        assert result[0].name == sample_rule.name

    def test_list_rules_with_filters(self, mock_db_session, sample_rule):
        """测试带过滤条件的列表查询"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.filter.return_value.all.return_value = [sample_rule]
        mock_db_session.query.return_value.filter.return_value.count.return_value = 1
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.list_rules(rule_type="alert_level", enabled=True)
        
        assert len(result) == 1
        mock_db_session.query.return_value.filter.assert_called()

    def test_update_rule(self, mock_db_session, sample_rule):
        """测试更新规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        service = NotificationTargetRuleService(mock_db_session)
        update_data = {"name": "Updated Rule", "notify_interval": 600}
        
        # Need to return sample_rule for id lookup, then None for name uniqueness check
        # First call: query.filter(id==1).first() -> sample_rule
        # Second call: query.filter(name==new_name, id!=1).first() -> None
        call_results = [sample_rule, None]
        mock_query = MagicMock()
        mock_query.filter.return_value.first.side_effect = call_results
        mock_db_session.query.return_value = mock_query
        
        result = service.update_rule(1, update_data)
        
        assert result is not None
        assert sample_rule.name == "Updated Rule"
        mock_db_session.commit.assert_called()

    def test_update_rule_not_found(self, mock_db_session):
        """测试更新不存在的规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        service = NotificationTargetRuleService(mock_db_session)
        
        with pytest.raises(ValueError, match="规则不存在"):
            service.update_rule(999, {"name": "Test"})

    def test_delete_rule(self, mock_db_session, sample_rule):
        """测试删除规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_rule
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.delete_rule(1)
        
        assert result is True
        mock_db_session.delete.assert_called_with(sample_rule)
        mock_db_session.commit.assert_called()

    def test_delete_rule_not_found(self, mock_db_session):
        """测试删除不存在的规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        service = NotificationTargetRuleService(mock_db_session)
        
        with pytest.raises(ValueError, match="规则不存在"):
            service.delete_rule(999)

    def test_toggle_rule(self, mock_db_session, sample_rule):
        """测试启用/禁用规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_rule
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.toggle_rule(1, enabled=False)
        
        assert result is not None
        assert sample_rule.enabled is False
        mock_db_session.commit.assert_called()

    def test_match_rules_by_alert_level(self, mock_db_session, sample_rule):
        """测试按告警级别匹配规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [sample_rule]
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.match_rules(alert_level="critical")
        
        assert len(result) == 1
        assert result[0]["id"] == sample_rule.id

    def test_match_rules_by_device_id(self, mock_db_session):
        """测试按设备ID匹配规则"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        device_rule = NotificationTargetRule(
            id=2,
            name="Device Rule",
            rule_type="device",
            match_conditions=json.dumps({"device_ids": [10, 20, 30]}),
            notify_channels=json.dumps(["dingtalk"]),
            enabled=True,
        )
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [device_rule]
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.match_rules(alert_level="critical", device_id=20)
        
        assert len(result) == 1

    def test_match_rules_disabled_rule_not_matched(self, mock_db_session):
        """测试禁用的规则不会被匹配"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        disabled_rule = NotificationTargetRule(
            id=3,
            name="Disabled Rule",
            rule_type="alert_level",
            match_conditions=json.dumps({"levels": ["critical"]}),
            notify_channels=json.dumps(["email"]),
            enabled=False,  # 禁用
        )
        
        # 当filter(enabled==True)调用时返回空列表
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        # 单独处理filter().filter()的情况（用于名称唯一性检查）
        mock_db_session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.match_rules(alert_level="critical")
        
        # 禁用的规则不应该匹配
        assert len(result) == 0

    def test_match_rules_priority_order(self, mock_db_session):
        """测试规则按优先级排序匹配"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        # Rules in sorted order by priority (SQL order_by will sort by priority asc)
        rule1 = NotificationTargetRule(id=1, name="Low Priority", priority=100, rule_type="alert_level", 
                                   match_conditions=json.dumps({"levels": ["critical"]}), 
                                   notify_channels=json.dumps(["email"]), enabled=True)
        rule2 = NotificationTargetRule(id=2, name="High Priority", priority=10, rule_type="alert_level",
                                   match_conditions=json.dumps({"levels": ["critical"]}),
                                   notify_channels=json.dumps(["sms"]), enabled=True)
        rule3 = NotificationTargetRule(id=3, name="Medium Priority", priority=50, rule_type="alert_level",
                                   match_conditions=json.dumps({"levels": ["critical"]}),
                                   notify_channels=json.dumps(["dingtalk"]), enabled=True)
        
        # SQL order_by(priority.asc) returns: rule2(10), rule3(50), rule1(100)
        sorted_rules = [rule2, rule3, rule1]
        
        # match_rules uses query.filter(enabled==True).order_by().all()
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = sorted_rules
        mock_db_session.query.return_value = mock_query
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.match_rules(alert_level="critical")
        
        # 结果应该按优先级排序
        assert result[0]["id"] == 2  # High Priority (priority=10)
        assert result[1]["id"] == 3  # Medium Priority (priority=50)
        assert result[2]["id"] == 1  # Low Priority (priority=100)

    def test_validate_rule_type(self, mock_db_session):
        """测试规则类型验证"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        valid_types = ["alert_level", "device", "category", "custom"]
        
        service = NotificationTargetRuleService(mock_db_session)
        for rule_type in valid_types:
            assert service._validate_rule_type(rule_type) is True

    def test_validate_rule_type_invalid(self, mock_db_session):
        """测试无效规则类型验证"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        service = NotificationTargetRuleService(mock_db_session)
        
        with pytest.raises(ValueError, match="无效的规则类型"):
            service._validate_rule_type("invalid_type")

    def test_validate_notify_channels(self, mock_db_session):
        """测试通知渠道验证"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        valid_channels = ["email", "dingtalk", "feishu", "wechat_work", "webhook", "sms"]
        
        service = NotificationTargetRuleService(mock_db_session)
        for channel in valid_channels:
            assert service._validate_notify_channel(channel) is True

    def test_validate_notify_channels_invalid(self, mock_db_session):
        """测试无效通知渠道验证"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        service = NotificationTargetRuleService(mock_db_session)
        
        with pytest.raises(ValueError, match="无效的通知渠道"):
            service._validate_notify_channel("invalid_channel")


class TestNotificationTargetRuleServiceEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def mock_db_session(self):
        session = MagicMock()
        session.query.return_value = session
        session.filter.return_value = session
        session.order_by.return_value = session
        session.commit.return_value = None
        return session

    def test_create_rule_with_empty_name(self, mock_db_session):
        """测试空名称验证"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        service = NotificationTargetRuleService(mock_db_session)
        
        with pytest.raises(ValueError, match="规则名称不能为空"):
            service.create_rule({"name": "", "rule_type": "alert_level", "notify_channels": ["email"]})

    def test_create_rule_with_special_characters_in_name(self, mock_db_session):
        """测试带特殊字符的名称"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.create_rule({
            "name": "Rule <test> & 'special'",
            "rule_type": "alert_level",
            "notify_channels": ["email"]
        })
        
        assert result is not None

    def test_match_rules_with_multiple_conditions(self, mock_db_session):
        """测试多条件匹配"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        rule = NotificationTargetRule(
            id=1,
            name="Multi Match Rule",
            rule_type="device",
            match_conditions=json.dumps({"device_ids": [1, 2], "device_types": ["server", "router"]}),
            notify_channels=json.dumps(["dingtalk"]),
            enabled=True,
        )
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [rule]
        
        service = NotificationTargetRuleService(mock_db_session)
        
        # 按device_id匹配
        result = service.match_rules(alert_level="warning", device_id=1)
        assert len(result) == 1
        
        # 按device_type匹配
        result = service.match_rules(alert_level="warning", device_type="router")
        assert len(result) == 1

    def test_match_rules_no_conditions(self, mock_db_session):
        """测试无匹配条件"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        rule = NotificationTargetRule(
            id=1,
            name="No Match Rule",
            rule_type="alert_level",
            match_conditions=json.dumps({"levels": ["low"]}),
            notify_channels=json.dumps(["email"]),
            enabled=True,
        )
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [rule]
        
        service = NotificationTargetRuleService(mock_db_session)
        result = service.match_rules(alert_level="critical")  # 不匹配任何规则
        
        assert len(result) == 0


class TestNotificationTargetRuleServiceIntegration:
    """集成测试（模拟真实数据库操作）"""

    def test_full_crud_cycle(self):
        """测试完整的CRUD周期"""
        from modules.business.notification.target_config import NotificationTargetRuleService
        
        # 创建一个模拟的DB session
        mock_session = MagicMock()
        
        # 存储创建的对象
        created_rule = None
        
        def mock_add(obj):
            nonlocal created_rule
            created_rule = obj
        
        mock_session.add = mock_add
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        service = NotificationTargetRuleService(mock_session)
        
        # Create
        rule_data = {
            "name": "Integration Test Rule",
            "rule_type": "alert_level",
            "match_conditions": {"levels": ["critical"]},
            "notify_channels": ["email", "dingtalk"],
            "priority": 50,
        }
        
        result = service.create_rule(rule_data)
        
        # 验证创建
        assert created_rule is not None
        assert created_rule.name == "Integration Test Rule"
        
        # 模拟更新后的查询
        mock_session.query.return_value.filter.return_value.first.return_value = created_rule
        
        # Read
        fetched = service.get_rule_by_id(1)
        assert fetched is not None
        
        # Update
        service.update_rule(1, {"priority": 30})
        assert created_rule.priority == 30
        
        # Delete
        mock_session.query.return_value.filter.return_value.first.return_value = created_rule
        service.delete_rule(1)
        mock_session.delete.assert_called()


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])