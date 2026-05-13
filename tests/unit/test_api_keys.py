"""
B4: API Key认证 - 单元测试
测试API Key的创建、验证、使用和管理功能
"""

import pytest
import hashlib
import secrets
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Optional

# ============== API Key模型测试 ==============

from modules.foundation.db_models.system import APIKey


class TestAPIKeyModel:
    """API Key模型测试"""

    def test_api_key_is_valid(self):
        """测试API Key有效性检查"""
        api_key = APIKey(
            key_id="test_key",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Test Key",
            is_active=1,
            is_revoked=0,
        )
        assert api_key.is_valid() is True

    def test_api_key_is_invalid_when_revoked(self):
        """测试已撤销的Key无效"""
        api_key = APIKey(
            key_id="test_key",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Test Key",
            is_active=1,
            is_revoked=1,  # 已撤销
        )
        assert api_key.is_valid() is False

    def test_api_key_is_invalid_when_inactive(self):
        """测试禁用的Key无效"""
        api_key = APIKey(
            key_id="test_key",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Test Key",
            is_active=0,  # 已禁用
            is_revoked=0,
        )
        assert api_key.is_valid() is False

    def test_api_key_is_invalid_when_expired(self):
        """测试过期的Key无效"""
        api_key = APIKey(
            key_id="test_key",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Test Key",
            is_active=1,
            is_revoked=0,
            expires_at=datetime.now() - timedelta(days=1),  # 已过期
        )
        assert api_key.is_valid() is False

    def test_api_key_is_invalid_when_request_limit_reached(self):
        """测试请求次数超限的Key无效"""
        api_key = APIKey(
            key_id="test_key",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Test Key",
            is_active=1,
            is_revoked=0,
            max_requests=100,
            request_count=100,  # 已达上限
        )
        assert api_key.is_valid() is False

    def test_api_key_is_valid_with_no_request_limit(self):
        """测试无请求限制的Key"""
        api_key = APIKey(
            key_id="test_key",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Test Key",
            is_active=1,
            is_revoked=0,
            max_requests=-1,  # 无限制
            request_count=10000,
        )
        assert api_key.is_valid() is True

    def test_api_key_is_valid_with_no_expiry(self):
        """测试永不过期的Key"""
        api_key = APIKey(
            key_id="test_key",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Test Key",
            is_active=1,
            is_revoked=0,
            expires_at=None,  # 永不过期
        )
        assert api_key.is_valid() is True


# ============== API Key生成测试 ==============

class TestAPIKeyGeneration:
    """API Key生成测试"""

    def test_generate_api_key_uses_token_urlsafe(self):
        """测试使用secrets.token_urlsafe(32)生成Key"""
        random_part = secrets.token_urlsafe(32)
        full_key = f"sk-{random_part}"
        
        assert full_key.startswith("sk-")
        # token_urlsafe(32) produces 43 characters in base64
        assert len(random_part) == 43
        assert len(full_key) == 46  # "sk-" + 43 chars

    def test_generate_api_key_uniqueness(self):
        """测试生成的Key唯一性"""
        keys = set()
        for _ in range(100):
            random_part = secrets.token_urlsafe(32)
            full_key = f"sk-{random_part}"
            keys.add(full_key)
        
        assert len(keys) == 100  # 所有Key都唯一

    def test_key_hash_is_deterministic(self):
        """测试相同Key产生相同Hash"""
        test_key = "sk-test-api-key"
        hash1 = hashlib.sha256(test_key.encode()).hexdigest()
        hash2 = hashlib.sha256(test_key.encode()).hexdigest()
        
        assert hash1 == hash2

    def test_key_hash_is_different_for_different_keys(self):
        """测试不同Key产生不同Hash"""
        hash1 = hashlib.sha256("sk-key1".encode()).hexdigest()
        hash2 = hashlib.sha256("sk-key2".encode()).hexdigest()
        
        assert hash1 != hash2

    def test_key_hash_length(self):
        """测试Hash长度(sha256产生64字符hex)"""
        test_key = "sk-test-key"
        key_hash = hashlib.sha256(test_key.encode()).hexdigest()
        
        assert len(key_hash) == 64


# ============== API Key验证测试 ==============

from api.dependencies import verify_api_key, require_api_key, get_current_user_from_api_key


class TestVerifyAPIKey:
    """API Key验证测试"""

    @pytest.mark.asyncio
    async def test_verify_api_key_requires_key(self):
        """测试无Key时抛出异常"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key=None)
        
        assert exc_info.value.status_code == 401
        assert "API Key is required" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('modules.foundation.db_models.base._db_manager')
    async def test_verify_api_key_success(self, mock_db_manager):
        """测试有效Key验证成功"""
        # 创建模拟的API Key记录
        mock_key = MagicMock()
        mock_key.key_hash = hashlib.sha256("test-api-key".encode()).hexdigest()
        mock_key.is_active = 1
        mock_key.is_revoked = 0
        mock_key.expires_at = None
        mock_key.max_requests = -1
        mock_key.request_count = 0
        mock_key.last_used_at = None

        # 模拟session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_key
        mock_db_manager.session_scope.return_value.__enter__.return_value = mock_session

        result = await verify_api_key(api_key="test-api-key")
        assert result == "test-api-key"

    @pytest.mark.asyncio
    @patch('modules.foundation.db_models.base._db_manager')
    async def test_verify_api_key_not_found(self, mock_db_manager):
        """测试无效Key返回401"""
        from fastapi import HTTPException
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db_manager.session_scope.return_value.__enter__.return_value = mock_session

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key="invalid-key")
        
        assert exc_info.value.status_code == 401
        assert "Invalid API Key" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('modules.foundation.db_models.base._db_manager')
    async def test_verify_api_key_expired(self, mock_db_manager):
        """测试过期Key返回401"""
        from fastapi import HTTPException
        
        mock_key = MagicMock()
        mock_key.key_hash = hashlib.sha256("expired-key".encode()).hexdigest()
        mock_key.is_active = 1
        mock_key.is_revoked = 0
        mock_key.expires_at = datetime.now() - timedelta(days=1)  # 已过期
        mock_key.max_requests = -1
        mock_key.request_count = 0

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_key
        mock_db_manager.session_scope.return_value.__enter__.return_value = mock_session

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key="expired-key")
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch('modules.foundation.db_models.base._db_manager')
    async def test_verify_api_key_request_limit_exceeded(self, mock_db_manager):
        """测试请求次数超限返回429"""
        from fastapi import HTTPException
        
        mock_key = MagicMock()
        mock_key.key_hash = hashlib.sha256("limited-key".encode()).hexdigest()
        mock_key.is_active = 1
        mock_key.is_revoked = 0
        mock_key.expires_at = None
        mock_key.max_requests = 100
        mock_key.request_count = 100  # 已达上限

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_key
        mock_db_manager.session_scope.return_value.__enter__.return_value = mock_session

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key="limited-key")
        
        assert exc_info.value.status_code == 429
        assert "limit exceeded" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_api_key_development_mode_fallback(self):
        """测试开发环境下数据库查询失败时的fallback"""
        with patch('modules.foundation.db_models.base._db_manager') as mock_db:
            mock_db.session_scope.side_effect = Exception("DB not available")

            with patch('api.dependencies.get_settings') as mock_settings:
                mock_settings.return_value.DEBUG = True

                result = await verify_api_key(api_key="any-key")
                assert result == "any-key"


# ============== require_api_key装饰器测试 ==============

class TestRequireAPIKey:
    """require_api_key装饰器测试"""

    def test_require_api_key_returns_callable(self):
        """测试返回可调用对象"""
        result = require_api_key()
        assert callable(result)

    def test_require_api_key_with_scopes(self):
        """测试带scopes参数的装饰器"""
        result = require_api_key(scopes=["read", "write"])
        assert callable(result)

    def test_require_api_key_with_empty_scopes(self):
        """测试带空scopes参数的装饰器"""
        result = require_api_key(scopes=[])
        assert callable(result)


# ============== 从API Key获取用户测试 ==============

class TestGetCurrentUserFromAPIKey:
    """从API Key获取用户测试"""

    @pytest.mark.asyncio
    @patch('modules.foundation.db_models.base._db_manager')
    async def test_get_user_from_api_key_with_existing_user(self, mock_db_manager):
        """测试获取关联用户信息"""
        mock_key = MagicMock()
        mock_key.key_hash = hashlib.sha256("test-key".encode()).hexdigest()
        mock_key.username = "api_user_001"
        mock_key.user_id = "user_123"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_key
        mock_db_manager.session_scope.return_value.__enter__.return_value = mock_session

        user = await get_current_user_from_api_key(api_key="test-key")
        assert user.username == "api_user_001"
        assert user.user_id == "user_123"

    @pytest.mark.asyncio
    @patch('modules.foundation.db_models.base._db_manager')
    async def test_get_user_from_api_key_no_user_returns_default(self, mock_db_manager):
        """测试无关联用户时返回默认用户"""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db_manager.session_scope.return_value.__enter__.return_value = mock_session

        user = await get_current_user_from_api_key(api_key="test-key")
        assert user.username == "api_user"
        assert "api_user" in user.roles


# ============== API Key路由测试 ==============

class TestAPIKeyRoutes:
    """API Key路由测试"""

    @pytest.fixture
    def mock_db_session(self):
        """创建模拟数据库会话"""
        session = MagicMock()
        return session

    @pytest.fixture
    def mock_current_user(self):
        """创建模拟当前用户"""
        from api.dependencies import CurrentUser
        return CurrentUser(
            user_id="admin_user",
            username="admin",
            email="admin@example.com",
            roles=["admin"],
            permissions=["*"],
        )

    def test_generate_api_key_format(self):
        """测试生成的Key格式"""
        random_part = secrets.token_urlsafe(32)
        full_key = f"sk-{random_part}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        key_prefix = f"sk-{random_part[:8]}"

        assert full_key.startswith("sk-")
        assert key_prefix.startswith("sk-")
        assert len(key_hash) == 64
        assert len(key_prefix) == 11  # "sk-" + 8 chars

    def test_mask_api_key(self):
        """测试API Key掩码功能"""
        from api.routes.api_keys import _mask_api_key
        
        # 长Key应该掩码
        long_key = "sk-abcdefghijklmnopqrstuvwxyz123456"
        masked = _mask_api_key(long_key)
        assert masked.startswith("sk-abcde")
        assert "***" in masked
        assert len(masked) < len(long_key)
        
        # 短Key应该保持原样
        short_key = "sk-ab"
        masked = _mask_api_key(short_key)
        assert masked == short_key + "***"

    def test_api_key_create_request_model(self):
        """测试API Key创建请求模型"""
        from api.routes.api_keys import APIKeyCreate
        
        # 完整参数
        key_data = APIKeyCreate(
            name="Test API Key",
            user_id="user_123",
            username="testuser",
            scopes=["read", "write"],
            expires_days=30,
            max_requests=1000,
            rate_limit=100,
        )
        
        assert key_data.name == "Test API Key"
        assert key_data.scopes == ["read", "write"]
        assert key_data.expires_days == 30

    def test_api_key_create_request_model_optional_fields(self):
        """测试API Key创建请求模型的可选字段"""
        from api.routes.api_keys import APIKeyCreate
        
        # 最小参数
        key_data = APIKeyCreate(name="Minimal Key")
        
        assert key_data.name == "Minimal Key"
        assert key_data.user_id is None
        assert key_data.username is None
        assert key_data.scopes == []
        assert key_data.expires_days is None
        assert key_data.max_requests is None
        assert key_data.rate_limit == 100  # 默认值


# ============== API Key响应格式测试 ==============

class TestAPIKeyResponseFormat:
    """API Key响应格式测试"""

    def test_response_format_with_data_and_code(self):
        """测试响应格式包含 data 和 code 字段"""
        # 模拟响应结构
        response = {
            "data": {"id": 1, "key_id": "key_123", "name": "Test Key"},
            "code": 0,
            "message": "Success"
        }
        
        assert "data" in response
        assert "code" in response
        assert response["code"] == 0

    def test_list_response_format(self):
        """测试列表响应格式"""
        response = {
            "data": [
                {"id": 1, "key_id": "key_1", "name": "Key 1"},
                {"id": 2, "key_id": "key_2", "name": "Key 2"},
            ],
            "code": 0,
            "total": 2,
            "page": 1,
            "page_size": 20,
        }
        
        assert "data" in response
        assert isinstance(response["data"], list)
        assert len(response["data"]) == 2
        assert response["total"] == 2
        assert "code" in response

    def test_create_response_includes_api_key(self):
        """测试创建响应包含完整API Key"""
        response = {
            "data": {
                "id": 1,
                "key_id": "key_123",
                "api_key": "sk-abc123...",  # 只在创建时返回
                "name": "Test Key",
            },
            "code": 0,
            "message": "请妥善保管API Key，仅在创建时显示完整Key",
        }
        
        assert "api_key" in response["data"]
        assert response["data"]["api_key"].startswith("sk-")


# ============== 集成测试 ==============

class TestAPIKeyIntegration:
    """API Key集成测试"""

    def test_full_api_key_lifecycle(self):
        """测试API Key完整生命周期"""
        # 1. 生成Key
        random_part = secrets.token_urlsafe(32)
        full_key = f"sk-{random_part}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        # 2. 验证Key hash一致
        assert hashlib.sha256(full_key.encode()).hexdigest() == key_hash
        
        # 3. 创建模型实例
        api_key_record = APIKey(
            key_id="key_test123",
            key_hash=key_hash,
            key_prefix=f"sk-{random_part[:8]}",
            name="Integration Test Key",
            is_active=1,
            is_revoked=0,
            max_requests=-1,
            request_count=0,
        )
        
        # 4. 验证模型有效性
        assert api_key_record.is_valid() is True
        
        # 5. 模拟使用后计数增加
        api_key_record.request_count += 1
        assert api_key_record.request_count == 1
        
        # 6. 模拟撤销
        api_key_record.is_revoked = 1
        assert api_key_record.is_valid() is False

    def test_api_key_expiry_scenario(self):
        """测试API Key过期场景"""
        # 创建带过期时间的Key
        api_key = APIKey(
            key_id="key_expiry",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Expiry Test",
            is_active=1,
            is_revoked=0,
            expires_at=datetime.now() + timedelta(days=1),  # 1天后过期
            max_requests=-1,
            request_count=0,
        )
        
        assert api_key.is_valid() is True
        
        # 模拟时间流逝，Key过期
        api_key.expires_at = datetime.now() - timedelta(days=1)
        assert api_key.is_valid() is False

    def test_api_key_permission_scopes(self):
        """测试API Key权限范围"""
        import json
        
        api_key = APIKey(
            key_id="key_scopes",
            key_hash="test_hash",
            key_prefix="sk-test",
            name="Scopes Test",
            is_active=1,
            is_revoked=0,
            scopes=json.dumps(["monitoring:read", "workorder:write"]),
            max_requests=-1,
            request_count=0,
        )
        
        scopes = json.loads(api_key.scopes)
        assert "monitoring:read" in scopes
        assert "workorder:write" in scopes
        assert "admin:write" not in scopes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
