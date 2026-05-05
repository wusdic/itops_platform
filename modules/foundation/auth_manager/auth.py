"""
FM-04 权限管理模块 - 用户认证模块
包含用户模型、密码加密、JWT Token、登录登出接口
"""

import hashlib
import hmac
from jose import jwt
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from functools import wraps

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


class UserStatus(Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING = "pending"


@dataclass
class User:
    """用户模型"""
    id: str
    username: str
    password_hash: str
    email: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含密码）"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "roles": self.roles,
            "metadata": self.metadata
        }


class PasswordHasher:
    """密码哈希工具类"""

    @staticmethod
    def hash_password(password: str) -> str:
        """使用bcrypt加密密码"""
        if BCRYPT_AVAILABLE:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        else:
            # 备用方案：使用PBKDF2
            salt = uuid.uuid4().hex
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return f"{salt}${hash_obj.hex()}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        if BCRYPT_AVAILABLE:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        else:
            # PBKDF2验证
            try:
                salt, stored_hash = password_hash.split('$')
                hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
                return hmac.compare_digest(hash_obj.hex(), stored_hash)
            except ValueError:
                return False

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """验证密码强度"""
        if len(password) < 8:
            return False, "密码长度至少8位"
        if not any(c.isupper() for c in password):
            return False, "密码必须包含大写字母"
        if not any(c.islower() for c in password):
            return False, "密码必须包含小写字母"
        if not any(c.isdigit() for c in password):
            return False, "密码必须包含数字"
        return True, "密码强度合格"


class JWTManager:
    """JWT Token管理器"""

    def __init__(self, secret_key: str, algorithm: str = "HS256", 
                 access_token_expire: int = 3600, refresh_token_expire: int = 604800):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire
        self.refresh_token_expire = refresh_token_expire

    def generate_access_token(self, user_id: str, username: str, 
                              roles: List[str], additional_claims: Dict[str, Any] = None) -> str:
        """生成访问令牌"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "username": username,
            "roles": roles,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=self.access_token_expire)
        }
        if additional_claims:
            payload.update(additional_claims)
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def generate_refresh_token(self, user_id: str) -> str:
        """生成刷新令牌"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(seconds=self.refresh_token_expire),
            "jti": str(uuid.uuid4())
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def generate_token_pair(self, user_id: str, username: str, 
                            roles: List[str]) -> Dict[str, str]:
        """生成令牌对"""
        return {
            "access_token": self.generate_access_token(user_id, username, roles),
            "refresh_token": self.generate_refresh_token(user_id),
            "token_type": "Bearer",
            "expires_in": self.access_token_expire
        }

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != token_type:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """使用刷新令牌获取新的访问令牌"""
        payload = self.verify_token(refresh_token, token_type="refresh")
        if not payload:
            return None
        return {
            "access_token": self.generate_access_token(
                payload["sub"], 
                payload.get("username", ""), 
                payload.get("roles", [])
            ),
            "token_type": "Bearer",
            "expires_in": self.access_token_expire
        }


class AuthManager:
    """认证管理器"""

    def __init__(self, jwt_manager: JWTManager):
        self.jwt_manager = jwt_manager
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, str] = {}  # token -> user_id
        self._init_default_admin()

    def _init_default_admin(self):
        """初始化默认管理员"""
        if "admin" not in self.users:
            admin = User(
                id=str(uuid.uuid4()),
                username="admin",
                password_hash=PasswordHasher.hash_password("Admin@123456"),
                email="admin@example.com",
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                roles=["admin"]
            )
            self.users["admin"] = admin

    def register(self, username: str, password: str, email: str, 
                 metadata: Dict[str, Any] = None) -> tuple[bool, str, Optional[User]]:
        """用户注册"""
        if username in self.users:
            return False, "用户名已存在", None

        is_valid, msg = PasswordHasher.validate_password_strength(password)
        if not is_valid:
            return False, msg, None

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=PasswordHasher.hash_password(password),
            email=email,
            status=UserStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        self.users[username] = user
        return True, "注册成功", user

    def login(self, username: str, password: str) -> tuple[bool, str, Optional[Dict[str, str]]]:
        """用户登录"""
        user = self.users.get(username)
        if not user:
            return False, "用户名或密码错误", None

        if user.status == UserStatus.LOCKED:
            return False, "账户已锁定", None

        if not PasswordHasher.verify_password(password, user.password_hash):
            return False, "用户名或密码错误", None

        user.status = UserStatus.ACTIVE
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()

        tokens = self.jwt_manager.generate_token_pair(user.id, user.username, user.roles)
        self.sessions[tokens["access_token"]] = user.id
        return True, "登录成功", tokens

    def logout(self, token: str) -> bool:
        """用户登出"""
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """通过ID获取用户"""
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        return self.users.get(username)

    def authenticate_token(self, token: str) -> Optional[User]:
        """验证Token并返回用户"""
        payload = self.jwt_manager.verify_token(token)
        if not payload:
            return None
        return self.get_user_by_id(payload["sub"])

    def update_user(self, user_id: str, **kwargs) -> tuple[bool, str]:
        """更新用户信息"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"

        if "password" in kwargs:
            is_valid, msg = PasswordHasher.validate_password_strength(kwargs["password"])
            if not is_valid:
                return False, msg
            kwargs["password_hash"] = PasswordHasher.hash_password(kwargs.pop("password"))

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = datetime.utcnow()
        return True, "更新成功"

    def change_password(self, user_id: str, old_password: str, 
                        new_password: str) -> tuple[bool, str]:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在"

        if not PasswordHasher.verify_password(old_password, user.password_hash):
            return False, "原密码错误"

        is_valid, msg = PasswordHasher.validate_password_strength(new_password)
        if not is_valid:
            return False, msg

        user.password_hash = PasswordHasher.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        return True, "密码修改成功"


def require_auth(func):
    """认证装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 从上下文中获取token
        token = kwargs.get('token')
        if not token:
            # 尝试从Authorization头获取
            auth_header = kwargs.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if not token:
            return {"success": False, "error": "未提供认证令牌"}, 401
        
        # 在实际应用中，这里会调用AuthManager.authenticate_token
        # 为了简化，直接传递验证逻辑
        return func(*args, **kwargs)
    return wrapper
