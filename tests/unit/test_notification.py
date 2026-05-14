"""
B3: 通知对象配置单元测试
测试 NotificationTarget DB模型和 /api/v1/notifications/targets API接口
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from typing import Optional

import sys
import os
sys.path.insert(0, '/home/zcxx/.hermes/projects/itops_platform')

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from modules.foundation.db_models.base import Base
from modules.foundation.db_models.notification.notification_model import NotificationChannel, NotificationTarget, NotificationChannelModel, NotificationLog, NotificationTargetRule


# 测试数据库配置
TEST_DB_URL = 'sqlite:///:memory:'


@pytest.fixture
def db_engine():
    """创建测试数据库引擎"""
    engine = create_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """创建测试数据库会话"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_user():
    """创建模拟用户"""
    from modules.foundation.auth_manager.auth import UserStatus
    user = MagicMock()
    user.id = "u001"
    user.username = "testuser"
    user.email = "test@example.com"
    user.roles = ["admin"]
    user.status = UserStatus.ACTIVE
    user.metadata = {}
    user.last_login = datetime.now()
    user.created_at = datetime.now()
    user.updated_at = datetime.now()
    return user


@pytest.fixture
def test_app(db_session, mock_user):
    """创建测试FastAPI应用"""
    # 确保db_session被使用，这样db_engine(Base.metadata.create_all)会在app创建前执行
    _ = db_session
    
    from api.routes.notification import router
    from api.dependencies import get_db, get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(router, prefix="")

    # 覆盖依赖
    def override_get_db():
        yield db_session

    def override_get_current_user():
        return CurrentUser(
            user_id=mock_user.id,
            username=mock_user.username,
            email=mock_user.email,
            roles=mock_user.roles
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
def client(test_app):
    """创建测试客户端"""
    return TestClient(test_app)


class TestNotificationChannelEnum:
    """NotificationChannel枚举测试"""

    def test_email_channel(self):
        """测试邮件渠道枚举"""
        assert NotificationChannel.EMAIL.value == "email"

    def test_sms_channel(self):
        """测试短信渠道枚举"""
        assert NotificationChannel.SMS.value == "sms"

    def test_webhook_channel(self):
        """测试Webhook渠道枚举"""
        assert NotificationChannel.WEBHOOK.value == "webhook"

    def test_all_channels_defined(self):
        """测试所有渠道都已定义"""
        channels = [c.value for c in NotificationChannel]
        assert "email" in channels
        assert "sms" in channels
        assert "webhook" in channels


class TestNotificationTargetModel:
    """NotificationTarget模型测试"""

    def test_create_email_target(self, db_session):
        """测试创建邮件通知对象"""
        target = NotificationTarget(
            name="Critical Alert Email",
            description="Critical级别告警邮件通知",
            channel="email",
            channel_config=json.dumps({
                "recipients": ["admin@example.com", "ops@example.com"],
                "smtp_config": {"host": "smtp.example.com", "port": 587}
            }),
            match_conditions=json.dumps({"alert_levels": ["critical", "high"]}),
            enabled=True,
            priority=10,
        )
        db_session.add(target)
        db_session.commit()

        assert target.id is not None
        assert target.name == "Critical Alert Email"
        assert target.channel == "email"
        assert target.enabled is True
        assert target.priority == 10

    def test_create_sms_target(self, db_session):
        """测试创建短信通知对象"""
        target = NotificationTarget(
            name="Emergency SMS",
            description="紧急告警短信通知",
            channel="sms",
            channel_config=json.dumps({
                "phone_numbers": ["13800138000", "13900139000"],
                "provider": "aliyun"
            }),
            match_conditions=json.dumps({"alert_levels": ["critical"]}),
            enabled=True,
            priority=5,
        )
        db_session.add(target)
        db_session.commit()

        assert target.channel == "sms"
        config = json.loads(target.channel_config)
        assert "13800138000" in config["phone_numbers"]

    def test_create_webhook_target(self, db_session):
        """测试创建Webhook通知对象"""
        target = NotificationTarget(
            name="Alert Webhook",
            description="告警Webhook回调",
            channel="webhook",
            channel_config=json.dumps({
                "url": "https://hooks.example.com/alerts",
                "method": "POST",
                "headers": {"Authorization": "Bearer token123"}
            }),
            match_conditions=json.dumps({
                "alert_levels": ["critical", "high", "medium"],
                "device_groups": ["server-group-1"],
                "metric_names": ["cpu_usage", "memory_usage"]
            }),
            enabled=True,
            priority=20,
        )
        db_session.add(target)
        db_session.commit()

        assert target.channel == "webhook"
        conditions = json.loads(target.match_conditions)
        assert "critical" in conditions["alert_levels"]
        assert "server-group-1" in conditions["device_groups"]

    def test_target_with_time_windows(self, db_session):
        """测试带时段配置的告警对象"""
        target = NotificationTarget(
            name="Business Hours Alert",
            description="工作时间告警通知",
            channel="email",
            time_windows=json.dumps([
                {"days": [1, 2, 3, 4, 5], "start_hour": 9, "end_hour": 18}
            ]),
            enabled=True,
        )
        db_session.add(target)
        db_session.commit()

        windows = json.loads(target.time_windows)
        assert windows[0]["start_hour"] == 9
        assert windows[0]["end_hour"] == 18

    def test_target_with_escalation(self, db_session):
        """测试带升级配置的告警对象"""
        target = NotificationTarget(
            name="Escalation Alert",
            description="带升级策略的告警",
            channel="email",
            escalation_config=json.dumps({
                "critical": [
                    {"after_seconds": 300, "channels": ["sms"]},
                    {"after_seconds": 900, "channels": ["phone"]}
                ]
            }),
            enabled=True,
        )
        db_session.add(target)
        db_session.commit()

        escalation = json.loads(target.escalation_config)
        assert "critical" in escalation
        assert escalation["critical"][0]["after_seconds"] == 300

    def test_target_to_dict(self, db_session):
        """测试模型转字典方法"""
        target = NotificationTarget(
            name="Test Target",
            description="测试目标",
            channel="email",
            channel_config=json.dumps({"recipients": ["test@example.com"]}),
            match_conditions=json.dumps({"alert_levels": ["high"]}),
            enabled=True,
            priority=50,
            notify_interval=600,
            max_notify_count=5,
        )
        db_session.add(target)
        db_session.commit()

        target_dict = target.to_dict()

        assert target_dict["name"] == "Test Target"
        assert target_dict["channel"] == "email"
        assert target_dict["enabled"] is True
        assert target_dict["priority"] == 50
        assert "recipients" in target_dict["channel_config"]
        assert "critical" not in target_dict["match_conditions"]["alert_levels"]  # Only "high"

    def test_unique_name_constraint(self, db_session):
        """测试名称唯一性约束"""
        target1 = NotificationTarget(
            name="Unique Name",
            channel="email",
        )
        db_session.add(target1)
        db_session.commit()

        target2 = NotificationTarget(
            name="Unique Name",
            channel="sms",
        )
        db_session.add(target2)
        with pytest.raises(Exception):  # SQLite会抛出IntegrityError
            db_session.commit()


class TestNotificationTargetAPI:
    """通知对象配置API接口测试"""

    def test_get_targets_empty(self, client, mock_user):
        """测试获取空的通知对象列表"""
        response = client.get("/targets")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"] == []
        assert data["total"] == 0

    def test_get_targets_with_data(self, client, mock_user, db_session):
        """测试获取有数据的通知对象列表"""
        # 创建测试数据
        target = NotificationTarget(
            name="API Test Target",
            description="API测试目标",
            channel="email",
            channel_config=json.dumps({"recipients": ["test@example.com"]}),
            enabled=True,
            priority=100,
        )
        db_session.add(target)
        db_session.commit()

        response = client.get("/targets")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "API Test Target"

    def test_get_targets_filter_by_channel(self, client, mock_user, db_session):
        """测试按渠道过滤获取通知对象"""
        # 创建email和sms目标
        email_target = NotificationTarget(
            name="Email Target",
            channel="email",
            enabled=True,
        )
        sms_target = NotificationTarget(
            name="SMS Target",
            channel="sms",
            enabled=True,
        )
        db_session.add_all([email_target, sms_target])
        db_session.commit()

        response = client.get("/targets?channel=email")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 1
        assert data["data"][0]["channel"] == "email"

    def test_get_targets_filter_by_enabled(self, client, mock_user, db_session):
        """测试按启用状态过滤获取通知对象"""
        enabled_target = NotificationTarget(
            name="Enabled Target",
            channel="email",
            enabled=True,
        )
        disabled_target = NotificationTarget(
            name="Disabled Target",
            channel="email",
            enabled=False,
        )
        db_session.add_all([enabled_target, disabled_target])
        db_session.commit()

        response = client.get("/targets?enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 1
        assert data["data"][0]["enabled"] is True

    def test_create_target_success(self, client, mock_user, db_session):
        """测试成功创建通知对象"""
        request_data = {
            "name": "New Email Target",
            "description": "新建邮件通知对象",
            "channel": "email",
            "channel_config": {
                "recipients": ["new@example.com"]
            },
            "match_conditions": {
                "alert_levels": ["critical", "high"]
            },
            "enabled": True,
            "priority": 50,
        }

        response = client.post("/targets", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "通知对象创建成功"
        assert "id" in data["data"]

        # 验证数据库中的记录
        saved_target = db_session.query(NotificationTarget).filter(
            NotificationTarget.name == "New Email Target"
        ).first()
        assert saved_target is not None
        assert saved_target.channel == "email"
        assert saved_target.priority == 50

    def test_create_target_with_webhook(self, client, mock_user, db_session):
        """测试创建Webhook通知对象"""
        request_data = {
            "name": "Webhook Alert",
            "description": "Webhook告警对象",
            "channel": "webhook",
            "channel_config": {
                "url": "https://hooks.example.com/alert",
                "method": "POST",
                "headers": {"X-API-Key": "secret123"}
            },
            "match_conditions": {
                "alert_levels": ["critical"],
                "device_groups": ["core-servers"],
                "metric_names": ["cpu_usage", "disk_usage"]
            },
            "enabled": True,
        }

        response = client.post("/targets", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        saved_target = db_session.query(NotificationTarget).filter(
            NotificationTarget.name == "Webhook Alert"
        ).first()
        assert saved_target.channel == "webhook"
        config = json.loads(saved_target.channel_config)
        assert config["url"] == "https://hooks.example.com/alert"

    def test_create_target_duplicate_name(self, client, mock_user, db_session):
        """测试创建重复名称的通知对象"""
        # 先创建一个
        existing = NotificationTarget(
            name="Existing Target",
            channel="email",
        )
        db_session.add(existing)
        db_session.commit()

        request_data = {
            "name": "Existing Target",
            "channel": "sms",
        }

        response = client.post("/targets", json=request_data)
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]

    def test_create_target_invalid_channel(self, client, mock_user):
        """测试创建无效渠道的通知对象"""
        request_data = {
            "name": "Invalid Channel Target",
            "channel": "fax",  # 无效渠道
        }

        response = client.post("/targets", json=request_data)
        assert response.status_code == 400
        assert "无效的渠道类型" in response.json()["detail"]

    def test_get_target_by_id(self, client, mock_user, db_session):
        """测试获取指定ID的通知对象"""
        target = NotificationTarget(
            name="Get By ID Test",
            description="测试获取详情",
            channel="sms",
            channel_config=json.dumps({"phone_numbers": ["13800138000"]}),
            match_conditions=json.dumps({"alert_levels": ["high"]}),
            enabled=True,
        )
        db_session.add(target)
        db_session.commit()
        target_id = target.id

        response = client.get(f"/targets/{target_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "Get By ID Test"
        assert data["data"]["channel"] == "sms"

    def test_get_target_not_found(self, client, mock_user):
        """测试获取不存在的通知对象"""
        response = client.get("/targets/99999")
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    def test_delete_target_success(self, client, mock_user, db_session):
        """测试成功删除通知对象"""
        target = NotificationTarget(
            name="To Be Deleted",
            channel="email",
        )
        db_session.add(target)
        db_session.commit()
        target_id = target.id

        response = client.delete(f"/targets/{target_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "通知对象删除成功"

        # 验证已删除
        deleted = db_session.query(NotificationTarget).filter(
            NotificationTarget.id == target_id
        ).first()
        assert deleted is None

    def test_delete_target_not_found(self, client, mock_user):
        """测试删除不存在的通知对象"""
        response = client.delete("/targets/99999")
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]


class TestNotificationTargetMatchConditions:
    """通知对象匹配条件测试"""

    def test_match_by_alert_levels(self, db_session):
        """测试按告警级别匹配"""
        target = NotificationTarget(
            name="Alert Level Match",
            channel="email",
            match_conditions=json.dumps({
                "alert_levels": ["critical", "high"]
            }),
            enabled=True,
        )
        db_session.add(target)
        db_session.commit()

        conditions = json.loads(target.match_conditions)
        assert "critical" in conditions["alert_levels"]
        assert "low" not in conditions["alert_levels"]

    def test_match_by_device_groups(self, db_session):
        """测试按设备分组匹配"""
        target = NotificationTarget(
            name="Device Group Match",
            channel="webhook",
            match_conditions=json.dumps({
                "device_groups": ["server-group-1", "network-devices", "db-servers"]
            }),
            enabled=True,
        )
        db_session.add(target)
        db_session.commit()

        conditions = json.loads(target.match_conditions)
        assert "server-group-1" in conditions["device_groups"]
        assert "mobile-devices" not in conditions["device_groups"]

    def test_match_by_metric_names(self, db_session):
        """测试按指标名称匹配"""
        target = NotificationTarget(
            name="Metric Name Match",
            channel="email",
            match_conditions=json.dumps({
                "metric_names": ["cpu_usage", "memory_usage", "disk_usage"]
            }),
            enabled=True,
        )
        db_session.add(target)
        db_session.commit()

        conditions = json.loads(target.match_conditions)
        assert "cpu_usage" in conditions["metric_names"]
        assert "network_in" not in conditions["metric_names"]

    def test_match_combined_conditions(self, db_session):
        """测试组合条件匹配 (AND关系)"""
        target = NotificationTarget(
            name="Combined Match",
            channel="email",
            match_conditions=json.dumps({
                "alert_levels": ["critical"],
                "device_groups": ["core-servers"],
                "metric_names": ["cpu_usage"]
            }),
            enabled=True,
        )
        db_session.add(target)
        db_session.commit()

        conditions = json.loads(target.match_conditions)
        assert len(conditions) == 3
        assert "critical" in conditions["alert_levels"]
        assert "core-servers" in conditions["device_groups"]
        assert "cpu_usage" in conditions["metric_names"]


class TestNotificationTargetPriority:
    """通知对象优先级测试"""

    def test_priority_ordering(self, db_session):
        """测试优先级排序"""
        targets = [
            NotificationTarget(name="Low Priority", channel="email", priority=100),
            NotificationTarget(name="High Priority", channel="email", priority=10),
            NotificationTarget(name="Medium Priority", channel="email", priority=50),
        ]
        for t in targets:
            db_session.add(t)
        db_session.commit()

        # 按优先级排序查询
        results = db_session.query(NotificationTarget).order_by(
            NotificationTarget.priority.asc()
        ).all()

        assert results[0].name == "High Priority"
        assert results[1].name == "Medium Priority"
        assert results[2].name == "Low Priority"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
