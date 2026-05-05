"""
FM-04 权限管理模块 - RBAC权限模块
包含角色模型、权限模型、用户-角色关联、权限检查装饰器
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from functools import wraps


class PermissionAction(Enum):
    """权限操作枚举"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"


@dataclass
class Permission:
    """权限模型 - 资源+操作"""
    id: str
    resource: str          # 资源名称，如 "user", "role", "audit"
    action: PermissionAction  # 操作类型
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.resource}:{self.action.value}"

    def __hash__(self) -> int:
        return hash((self.resource, self.action.value))

    def __eq__(self, other) -> bool:
        if isinstance(other, Permission):
            return self.resource == other.resource and self.action == other.action
        return False


@dataclass
class Role:
    """角色模型"""
    id: str
    name: str
    description: str = ""
    permissions: Set[Permission] = field(default_factory=set)
    is_system: bool = False  # 系统内置角色不可删除
    parent_role: Optional[str] = None  # 继承的角色
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """检查角色是否拥有某权限"""
        if permission in self.permissions:
            return True
        # 检查继承角色的权限
        return False

    def add_permission(self, permission: Permission):
        """添加权限"""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission):
        """移除权限"""
        self.permissions.discard(permission)


class RBACManager:
    """RBAC权限管理器"""

    # 默认系统角色
    DEFAULT_ROLES = {
        "admin": {
            "description": "系统管理员，拥有所有权限",
            "is_system": True,
            "permissions": [
                ("user", "manage"),
                ("role", "manage"),
                ("permission", "manage"),
                ("audit", "read"),
                ("system", "manage"),
            ]
        },
        "operator": {
            "description": "运维操作员，拥有资源管理权限",
            "is_system": True,
            "permissions": [
                ("user", "read"),
                ("system", "execute"),
                ("config", "read"),
                ("config", "update"),
            ]
        },
        "viewer": {
            "description": "只读用户，仅能查看资源",
            "is_system": True,
            "permissions": [
                ("user", "read"),
                ("system", "read"),
                ("config", "read"),
                ("audit", "read"),
            ]
        }
    }

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, Set[str]] = {}  # user_id -> set of role names
        self.resource_permissions: Dict[str, List[Permission]] = {}  # resource -> permissions
        self._init_default_roles()

    def _init_default_roles(self):
        """初始化默认角色"""
        for role_name, role_config in self.DEFAULT_ROLES.items():
            role = Role(
                id=f"role_{role_name}",
                name=role_name,
                description=role_config["description"],
                is_system=role_config["is_system"]
            )
            for resource, action in role_config["permissions"]:
                permission = Permission(
                    id=f"perm_{resource}_{action}",
                    resource=resource,
                    action=PermissionAction(action),
                    description=f"{action} {resource}"
                )
                role.add_permission(permission)
                if resource not in self.resource_permissions:
                    self.resource_permissions[resource] = []
                if permission not in self.resource_permissions[resource]:
                    self.resource_permissions[resource].append(permission)
            self.roles[role_name] = role

    def create_role(self, name: str, description: str = "", 
                    permissions: List[Permission] = None,
                    parent_role: str = None) -> tuple[bool, str, Optional[Role]]:
        """创建角色"""
        if name in self.roles:
            return False, "角色已存在", None

        role = Role(
            id=f"role_{name}",
            name=name,
            description=description,
            permissions=set(permissions) if permissions else set(),
            parent_role=parent_role
        )
        self.roles[name] = role
        return True, "角色创建成功", role

    def update_role(self, name: str, **kwargs) -> tuple[bool, str]:
        """更新角色"""
        if name not in self.roles:
            return False, "角色不存在"
        
        role = self.roles[name]
        if role.is_system:
            return False, "系统内置角色不可修改"

        for key, value in kwargs.items():
            if key == "permissions":
                role.permissions = set(value)
            elif hasattr(role, key):
                setattr(role, key, value)
        return True, "角色更新成功"

    def delete_role(self, name: str) -> tuple[bool, str]:
        """删除角色"""
        if name not in self.roles:
            return False, "角色不存在"
        
        role = self.roles[name]
        if role.is_system:
            return False, "系统内置角色不可删除"

        # 移除所有用户的相关角色
        for user_id, roles in self.user_roles.items():
            roles.discard(name)

        del self.roles[name]
        return True, "角色删除成功"

    def get_role(self, name: str) -> Optional[Role]:
        """获取角色"""
        return self.roles.get(name)

    def list_roles(self) -> List[Role]:
        """列出所有角色"""
        return list(self.roles.values())

    def create_permission(self, resource: str, action: PermissionAction,
                          description: str = "") -> Permission:
        """创建权限"""
        perm_id = f"perm_{resource}_{action.value}"
        permission = Permission(
            id=perm_id,
            resource=resource,
            action=action,
            description=description or f"{action.value} {resource}"
        )
        if resource not in self.resource_permissions:
            self.resource_permissions[resource] = []
        if permission not in self.resource_permissions[resource]:
            self.resource_permissions[resource].append(permission)
        return permission

    def get_permissions_by_resource(self, resource: str) -> List[Permission]:
        """获取资源的权限列表"""
        return self.resource_permissions.get(resource, [])

    def assign_role_to_user(self, user_id: str, role_name: str) -> tuple[bool, str]:
        """为用户分配角色"""
        if role_name not in self.roles:
            return False, "角色不存在"
        
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        
        self.user_roles[user_id].add(role_name)
        return True, "角色分配成功"

    def revoke_role_from_user(self, user_id: str, role_name: str) -> tuple[bool, str]:
        """撤销用户角色"""
        if user_id not in self.user_roles:
            return False, "用户没有分配过角色"
        
        self.user_roles[user_id].discard(role_name)
        return True, "角色撤销成功"

    def get_user_roles(self, user_id: str) -> List[Role]:
        """获取用户的所有角色"""
        role_names = self.user_roles.get(user_id, set())
        return [self.roles[name] for name in role_names if name in self.roles]

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """获取用户的所有权限（合并所有角色的权限）"""
        permissions = set()
        roles = self.get_user_roles(user_id)
        for role in roles:
            permissions.update(role.permissions)
        return permissions

    def check_permission(self, user_id: str, resource: str, 
                        action: PermissionAction) -> bool:
        """检查用户是否拥有特定权限"""
        permissions = self.get_user_permissions(user_id)
        required_permission = Permission(
            id=f"perm_{resource}_{action.value}",
            resource=resource,
            action=action
        )
        return required_permission in permissions

    def check_any_permission(self, user_id: str, 
                             required_permissions: List[tuple[str, PermissionAction]]) -> bool:
        """检查用户是否拥有任一权限"""
        for resource, action in required_permissions:
            if self.check_permission(user_id, resource, action):
                return True
        return False

    def check_all_permissions(self, user_id: str,
                              required_permissions: List[tuple[str, PermissionAction]]) -> bool:
        """检查用户是否拥有所有权限"""
        for resource, action in required_permissions:
            if not self.check_permission(user_id, resource, action):
                return False
        return True


def require_permission(resource: str, action: PermissionAction):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从kwargs获取user_id和rbac_manager
            user_id = kwargs.get('user_id')
            rbac_manager = kwargs.get('rbac_manager')
            
            if not user_id or not rbac_manager:
                return {"success": False, "error": "缺少认证信息"}, 401
            
            if not rbac_manager.check_permission(user_id, resource, action):
                return {"success": False, "error": "权限不足"}, 403
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*required_roles: str):
    """角色检查装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id')
            rbac_manager = kwargs.get('rbac_manager')
            
            if not user_id or not rbac_manager:
                return {"success": False, "error": "缺少认证信息"}, 401
            
            user_roles = {r.name for r in rbac_manager.get_user_roles(user_id)}
            if not any(role in user_roles for role in required_roles):
                return {"success": False, "error": "角色不匹配"}, 403
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class Resource:
    """资源基类"""
    def __init__(self, name: str, owner_id: str):
        self.name = name
        self.owner_id = owner_id
        self.acl: Dict[str, List[PermissionAction]] = {}

    def add_access(self, user_id: str, actions: List[PermissionAction]):
        """添加访问权限"""
        self.acl[user_id] = actions

    def remove_access(self, user_id: str):
        """移除访问权限"""
        if user_id in self.acl:
            del self.acl[user_id]

    def check_access(self, user_id: str, action: PermissionAction) -> bool:
        """检查访问权限"""
        if self.owner_id == user_id:
            return True
        return action in self.acl.get(user_id, [])


class ResourceManager:
    """资源访问控制管理器"""

    def __init__(self, rbac_manager: RBACManager):
        self.rbac_manager = rbac_manager
        self.resources: Dict[str, Resource] = {}

    def register_resource(self, resource_name: str, resource: Resource):
        """注册资源"""
        self.resources[resource_name] = resource

    def grant_resource_access(self, resource_name: str, user_id: str,
                              actions: List[PermissionAction]) -> tuple[bool, str]:
        """授予资源访问权限"""
        if resource_name not in self.resources:
            return False, "资源不存在"
        
        self.resources[resource_name].add_access(user_id, actions)
        return True, "权限授予成功"

    def revoke_resource_access(self, resource_name: str, 
                               user_id: str) -> tuple[bool, str]:
        """撤销资源访问权限"""
        if resource_name not in self.resources:
            return False, "资源不存在"
        
        self.resources[resource_name].remove_access(user_id)
        return True, "权限撤销成功"

    def check_resource_access(self, resource_name: str, user_id: str,
                              action: PermissionAction) -> bool:
        """检查资源访问权限"""
        if resource_name not in self.resources:
            return False
        
        return self.resources[resource_name].check_access(user_id, action)
