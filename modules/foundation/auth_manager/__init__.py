"""
FM-04 权限管理模块
包含认证、RBAC、LDAP集成、操作审计功能
"""

from .auth import (
    User, UserStatus, PasswordHasher, JWTManager, AuthManager,
    require_auth
)
from .rbac import (
    Role, Permission, PermissionAction, RBACManager,
    Resource, ResourceManager, require_permission, require_role
)
from .ldap_client import (
    LDAPUser, LDAPGroup, LDAPConfig, LDAPClient, LDAPSyncManager,
    LDAPAuthMethod, LDAPScope
)
from .audit import (
    AuditLog, AuditLevel, AuditAction, AuditLogger, AuditQuery,
    AuditContext, AuditReport, audit_log
)

__all__ = [
    # Auth
    'User', 'UserStatus', 'PasswordHasher', 'JWTManager', 'AuthManager', 'require_auth',
    # RBAC
    'Role', 'Permission', 'PermissionAction', 'RBACManager',
    'Resource', 'ResourceManager', 'require_permission', 'require_role',
    # LDAP
    'LDAPUser', 'LDAPGroup', 'LDAPConfig', 'LDAPClient', 'LDAPSyncManager',
    'LDAPAuthMethod', 'LDAPScope',
    # Audit
    'AuditLog', 'AuditLevel', 'AuditAction', 'AuditLogger', 'AuditQuery',
    'AuditContext', 'AuditReport', 'audit_log',
]
