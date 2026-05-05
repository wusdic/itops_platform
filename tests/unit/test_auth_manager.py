"""
FM-04 权限管理模块 - 单元测试
包含认证测试、权限测试、JWT测试
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from modules.foundation.auth_manager.auth import (
    User, UserStatus, PasswordHasher, JWTManager, AuthManager
)
from modules.foundation.auth_manager.rbac import (
    Role, Permission, PermissionAction, RBACManager,
    require_permission, require_role
)
from modules.foundation.auth_manager.ldap_client import (
    LDAPUser, LDAPGroup, LDAPConfig, LDAPClient
)
from modules.foundation.auth_manager.audit import (
    AuditLog, AuditLevel, AuditAction, AuditLogger, AuditQuery, AuditContext
)


class TestPasswordHasher:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "Test@123456"
        hashed = PasswordHasher.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert "$" in hashed or hashed.startswith("pbkdf2")

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "Test@123456"
        hashed = PasswordHasher.hash_password(password)
        
        assert PasswordHasher.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "Test@123456"
        hashed = PasswordHasher.hash_password(password)
        
        assert PasswordHasher.verify_password("WrongPassword", hashed) is False

    def test_password_strength_valid(self):
        """测试密码强度验证 - 有效密码"""
        valid_passwords = [
            "Admin@123456",
            "MyP@ssw0rd",
            "Str0ng#Pass"
        ]
        
        for pwd in valid_passwords:
            is_valid, msg = PasswordHasher.validate_password_strength(pwd)
            assert is_valid, f"密码应该有效: {pwd}, 错误: {msg}"

    def test_password_strength_invalid(self):
        """测试密码强度验证 - 无效密码"""
        invalid_passwords = [
            ("short", "密码长度至少8位"),
            ("nouppercase123", "密码必须包含大写字母"),
            ("NOLOWERCASE123", "密码必须包含小写字母"),
            ("NoDigitsHere", "密码必须包含数字"),
        ]
        
        for pwd, expected_msg in invalid_passwords:
            is_valid, msg = PasswordHasher.validate_password_strength(pwd)
            assert not is_valid, f"密码应该无效: {pwd}"
            assert expected_msg in msg


class TestJWTManager:
    """JWT Token测试"""

    def setup_method(self):
        """测试前准备"""
        self.jwt_manager = JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire=3600,
            refresh_token_expire=604800
        )

    def test_generate_access_token(self):
        """测试生成访问令牌"""
        token = self.jwt_manager.generate_access_token(
            user_id="user123",
            username="testuser",
            roles=["admin", "viewer"]
        )
        
        assert token is not None
        assert len(token) > 0
        assert token.count('.') == 2  # JWT格式: header.payload.signature

    def test_generate_refresh_token(self):
        """测试生成刷新令牌"""
        token = self.jwt_manager.generate_refresh_token(user_id="user123")
        
        assert token is not None
        assert len(token) > 0

    def test_generate_token_pair(self):
        """测试生成令牌对"""
        tokens = self.jwt_manager.generate_token_pair(
            user_id="user123",
            username="testuser",
            roles=["admin"]
        )
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "Bearer"

    def test_verify_token_valid(self):
        """测试验证有效令牌"""
        token = self.jwt_manager.generate_access_token(
            user_id="user123",
            username="testuser",
            roles=["admin"]
        )
        
        payload = self.jwt_manager.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert "admin" in payload["roles"]

    def test_verify_token_invalid(self):
        """测试验证无效令牌"""
        payload = self.jwt_manager.verify_token("invalid.token.here")
        assert payload is None

    def test_refresh_access_token(self):
        """测试刷新访问令牌"""
        refresh_token = self.jwt_manager.generate_refresh_token(user_id="user123")
        new_token = self.jwt_manager.refresh_access_token(refresh_token)
        
        assert new_token is not None
        assert "access_token" in new_token
        assert "token_type" in new_token


class TestAuthManager:
    """认证管理器测试"""

    def setup_method(self):
        """测试前准备"""
        self.jwt_manager = JWTManager(secret_key="test-secret-key")
        self.auth_manager = AuthManager(self.jwt_manager)

    def test_register_user(self):
        """测试用户注册"""
        success, msg, user = self.auth_manager.register(
            username="newuser",
            password="NewUser@123456",
            email="newuser@example.com"
        )
        
        assert success is True
        assert msg == "注册成功"
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"

    def test_register_duplicate_username(self):
        """测试重复用户名注册"""
        self.auth_manager.register(
            username="testuser",
            password="TestUser@123456",
            email="test1@example.com"
        )
        
        success, msg, user = self.auth_manager.register(
            username="testuser",
            password="TestUser@123456",
            email="test2@example.com"
        )
        
        assert success is False
        assert "已存在" in msg

    def test_register_weak_password(self):
        """测试弱密码注册"""
        success, msg, user = self.auth_manager.register(
            username="testuser",
            password="weak",
            email="test@example.com"
        )
        
        assert success is False
        assert "长度至少8位" in msg

    def test_login_success(self):
        """测试成功登录"""
        self.auth_manager.register(
            username="logintest",
            password="LoginTest@123",
            email="login@example.com"
        )
        
        success, msg, tokens = self.auth_manager.login(
            username="logintest",
            password="LoginTest@123"
        )
        
        assert success is True
        assert msg == "登录成功"
        assert tokens is not None
        assert "access_token" in tokens

    def test_login_wrong_password(self):
        """测试错误密码登录"""
        self.auth_manager.register(
            username="logintest2",
            password="LoginTest@123",
            email="login2@example.com"
        )
        
        success, msg, tokens = self.auth_manager.login(
            username="logintest2",
            password="WrongPassword"
        )
        
        assert success is False
        assert "错误" in msg

    def test_login_nonexistent_user(self):
        """测试不存在的用户登录"""
        success, msg, tokens = self.auth_manager.login(
            username="nonexistent",
            password="Password@123"
        )
        
        assert success is False

    def test_logout(self):
        """测试登出"""
        self.auth_manager.register(
            username="logouttest",
            password="LogoutTest@123",
            email="logout@example.com"
        )
        
        success, _, tokens = self.auth_manager.login(
            username="logouttest",
            password="LogoutTest@123"
        )
        
        token = tokens["access_token"]
        assert self.auth_manager.logout(token) is True

    def test_change_password(self):
        """测试修改密码"""
        self.auth_manager.register(
            username="pwdtest",
            password="OldPass@123",
            email="pwd@example.com"
        )
        
        user = self.auth_manager.get_user_by_username("pwdtest")
        success, msg = self.auth_manager.change_password(
            user_id=user.id,
            old_password="OldPass@123",
            new_password="NewPass@456"
        )
        
        assert success is True
        
        # 验证新密码可以登录
        success, _, tokens = self.auth_manager.login(
            username="pwdtest",
            password="NewPass@456"
        )
        assert success is True


class TestRBACManager:
    """RBAC权限管理测试"""

    def setup_method(self):
        """测试前准备"""
        self.rbac_manager = RBACManager()

    def test_default_roles_exist(self):
        """测试默认角色存在"""
        roles = self.rbac_manager.list_roles()
        role_names = [r.name for r in roles]
        
        assert "admin" in role_names
        assert "operator" in role_names
        assert "viewer" in role_names

    def test_create_role(self):
        """测试创建角色"""
        success, msg, role = self.rbac_manager.create_role(
            name="custom_role",
            description="自定义角色"
        )
        
        assert success is True
        assert role is not None
        assert role.name == "custom_role"

    def test_assign_role_to_user(self):
        """测试为用户分配角色"""
        success, msg = self.rbac_manager.assign_role_to_user(
            user_id="user123",
            role_name="admin"
        )
        
        assert success is True
        
        roles = self.rbac_manager.get_user_roles("user123")
        assert len(roles) == 1
        assert roles[0].name == "admin"

    def test_check_permission(self):
        """测试权限检查"""
        # 为用户分配admin角色
        self.rbac_manager.assign_role_to_user("user123", "admin")
        
        # admin应该拥有人事管理权限
        has_permission = self.rbac_manager.check_permission(
            user_id="user123",
            resource="user",
            action=PermissionAction.MANAGE
        )
        assert has_permission is True
        
        # viewer不应该拥有人事管理权限
        self.rbac_manager.assign_role_to_user("user456", "viewer")
        has_permission = self.rbac_manager.check_permission(
            user_id="user456",
            resource="user",
            action=PermissionAction.MANAGE
        )
        assert has_permission is False

    def test_check_any_permission(self):
        """测试检查任一权限"""
        self.rbac_manager.assign_role_to_user("user123", "viewer")
        
        # viewer拥有人事读取权限
        has_any = self.rbac_manager.check_any_permission(
            user_id="user123",
            required_permissions=[
                ("user", PermissionAction.MANAGE),
                ("user", PermissionAction.READ)
            ]
        )
        assert has_any is True

    def test_delete_system_role(self):
        """测试删除系统角色失败"""
        success, msg = self.rbac_manager.delete_role("admin")
        
        assert success is False
        assert "不可删除" in msg


class TestAuditLogger:
    """审计日志测试"""

    def setup_method(self):
        """测试前准备"""
        self.audit_logger = AuditLogger(retention_days=30)

    def test_log_audit(self):
        """测试记录审计日志"""
        log = self.audit_logger.log(
            user_id="user123",
            username="testuser",
            action=AuditAction.LOGIN.value,
            resource_type="session",
            status="success",
            level=AuditLevel.INFO,
            ip_address="192.168.1.1"
        )
        
        assert log is not None
        assert log.user_id == "user123"
        assert log.action == "login"

    def test_query_by_user(self):
        """测试按用户查询"""
        self.audit_logger.log(
            user_id="user123",
            username="user1",
            action=AuditAction.LOGIN.value,
            status="success"
        )
        self.audit_logger.log(
            user_id="user456",
            username="user2",
            action=AuditAction.LOGIN.value,
            status="success"
        )
        
        query = AuditQuery().by_user("user123")
        results = self.audit_logger.query(query)
        
        assert len(results) == 1
        assert results[0].user_id == "user123"

    def test_query_by_action(self):
        """测试按操作查询"""
        self.audit_logger.log(
            user_id="user123",
            username="testuser",
            action=AuditAction.LOGIN.value,
            status="success"
        )
        self.audit_logger.log(
            user_id="user123",
            username="testuser",
            action=AuditAction.USER_CREATE.value,
            status="success"
        )
        
        query = AuditQuery().by_action(AuditAction.USER_CREATE.value)
        results = self.audit_logger.query(query)
        
        assert len(results) == 1
        assert results[0].action == "user_create"

    def test_query_by_time_range(self):
        """测试按时间范围查询"""
        # 记录一个参考时间点
        self.audit_logger.log(
            user_id="user123",
            username="testuser",
            action=AuditAction.LOGIN.value,
            status="success"
        )
        
        # 使用一个较大的时间范围确保能查到
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow() + timedelta(days=1)
        query = AuditQuery().by_time_range(start_time, end_time)
        results = self.audit_logger.query(query)
        
        assert len(results) >= 1

    def test_get_failed_logins(self):
        """测试获取失败登录"""
        self.audit_logger.log(
            user_id="user123",
            username="testuser",
            action=AuditAction.LOGIN.value,
            status="failed"
        )
        
        failed_logins = self.audit_logger.get_failed_logins(hours=24)
        assert len(failed_logins) >= 1

    def test_export_logs(self):
        """测试导出日志"""
        self.audit_logger.log(
            user_id="user123",
            username="testuser",
            action=AuditAction.LOGIN.value,
            status="success"
        )
        
        query = AuditQuery().paginate(limit=100)
        exported = self.audit_logger.export_logs(query, format="json")
        
        assert exported is not None
        assert '"user_id": "user123"' in exported


class TestAuditContext:
    """审计上下文测试"""

    def test_set_and_get_context(self):
        """测试设置和获取上下文"""
        AuditContext.set_context(
            user_id="user123",
            username="testuser",
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0"
        )
        
        context = AuditContext.get_context()
        
        assert context["user_id"] == "user123"
        assert context["username"] == "testuser"
        assert context["ip_address"] == "192.168.1.1"

    def test_clear_context(self):
        """测试清除上下文"""
        AuditContext.set_context(
            user_id="user123",
            username="testuser"
        )
        
        AuditContext.clear_context()
        context = AuditContext.get_context()
        
        assert context["user_id"] == "system"


class TestLDAPConfig:
    """LDAP配置测试"""

    def test_ldap_config_creation(self):
        """测试LDAP配置创建"""
        config = LDAPConfig(
            server="ldap.example.com",
            port=389,
            use_ssl=False,
            base_dn="dc=example,dc=com",
            username_attr="sAMAccountName"
        )
        
        assert config.server == "ldap.example.com"
        assert config.port == 389
        assert config.base_dn == "dc=example,dc=com"


class TestLDAPUser:
    """LDAP用户测试"""

    def test_ldap_user_creation(self):
        """测试LDAP用户创建"""
        ldap_user = LDAPUser(
            dn="cn=test,dc=example,dc=com",
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            groups=["Domain Users", "IT Dept"]
        )
        
        assert ldap_user.username == "testuser"
        assert len(ldap_user.groups) == 2
        assert ldap_user.enabled is True

    def test_ldap_user_to_dict(self):
        """测试LDAP用户转字典"""
        ldap_user = LDAPUser(
            dn="cn=test,dc=example,dc=com",
            username="testuser",
            email="test@example.com",
            display_name="Test User"
        )
        
        user_dict = ldap_user.to_dict()
        
        assert user_dict["username"] == "testuser"
        assert user_dict["email"] == "test@example.com"


class TestIntegration:
    """集成测试"""

    def setup_method(self):
        """测试前准备"""
        self.jwt_manager = JWTManager(secret_key="integration-test-key")
        self.auth_manager = AuthManager(self.jwt_manager)
        self.rbac_manager = RBACManager()
        self.audit_logger = AuditLogger()

    def test_full_auth_flow(self):
        """测试完整认证流程"""
        # 1. 注册用户
        success, msg, user = self.auth_manager.register(
            username="flowtest",
            password="FlowTest@123",
            email="flow@example.com"
        )
        assert success is True
        
        # 2. 分配角色
        self.rbac_manager.assign_role_to_user(user.id, "viewer")
        
        # 3. 登录获取token
        success, msg, tokens = self.auth_manager.login(
            username="flowtest",
            password="FlowTest@123"
        )
        assert success is True
        assert "access_token" in tokens
        
        # 4. 验证token
        payload = self.jwt_manager.verify_token(tokens["access_token"])
        assert payload is not None
        assert payload["username"] == "flowtest"
        
        # 5. 检查权限
        has_read = self.rbac_manager.check_permission(
            user_id=user.id,
            resource="user",
            action=PermissionAction.READ
        )
        assert has_read is True
        
        # 6. 记录审计
        self.audit_logger.log(
            user_id=user.id,
            username="flowtest",
            action=AuditAction.LOGIN.value,
            status="success"
        )
        
        # 7. 查询审计日志
        query = AuditQuery().by_user(user.id)
        logs = self.audit_logger.query(query)
        assert len(logs) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
