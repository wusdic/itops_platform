"""
API Key认证测试
测试API Key的创建、验证、使用和撤销功能
"""

import pytest
import hashlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import secrets
import string

from modules.foundation.db_models.system import APIKey
from api.dependencies import verify_api_key, require_api_key, get_current_user_from_api_key


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


class TestAPIKeyGeneration:
    """API Key生成测试"""

    def test_generate_api_key_format(self):
        """测试生成的Key格式"""
        # 模拟生成函数
        prefix = "sk"
        random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))
        full_key = f"{prefix}-{random_part}"

        assert full_key.startswith("sk-")
        assert len(full_key) == 52  # "sk-" + 48 chars

    def test_generate_api_key_uniqueness(self):
        """测试生成的Key唯一性"""
        keys = set()
        for _ in range(100):
            random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))
            full_key = f"sk-{random_part}"
            keys.add(full_key)

        assert len(keys) == 100  # 所有Key都唯一

    def test_key_hash_is_deterministic(self):
        """测试相同Key产生相同Hash"""
        test_key = "sk-test_key_12345"
        hash1 = hashlib.sha256(test_key.encode()).hexdigest()
        hash2 = hashlib.sha256(test_key.encode()).hexdigest()

        assert hash1 == hash2

    def test_key_hash_is_different_for_different_keys(self):
        """测试不同Key产生不同Hash"""
        hash1 = hashlib.sha256("sk-key1".encode()).hexdigest()
        hash2 = hashlib.sha256("sk-key2".encode()).hexdigest()

        assert hash1 != hash2


class TestVerifyAPIKey:
    """API Key验证测试"""

    @pytest.mark.asyncio
    async def test_verify_api_key_requires_key(self):
        """测试无Key时抛出异常"""
        with pytest.raises(Exception) as exc_info:
            await verify_api_key(api_key=None)
        assert "API Key is required" in str(exc_info.value.detail)

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
    async def test_verify_api_key_development_mode_fallback(self):
        """测试开发环境下数据库查询失败时的fallback"""
        with patch('modules.foundation.db_models.base._db_manager') as mock_db:
            mock_db.session_scope.side_effect = Exception("DB not available")

            with patch('api.dependencies.get_settings') as mock_settings:
                mock_settings.return_value.DEBUG = True

                result = await verify_api_key(api_key="any-key")
                assert result == "any-key"


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
