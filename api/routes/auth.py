# -*- coding: utf-8 -*-
"""
认证管理API路由
提供用户登录、注册、Token管理等功能
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from api.dependencies import get_db, get_settings, Settings, CurrentUser, get_current_user

router = APIRouter()

# JWT配置
ALGORITHM = "HS256"


# ============== 数据模型 ==============

class Token(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token数据"""
    username: Optional[str] = None


class UserBase(BaseModel):
    """用户基础信息"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserResponse(UserBase):
    """用户响应"""
    user_id: str
    roles: list[str] = []
    is_active: bool = True
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    """创建用户"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=6)


# ============== 工具函数 ==============

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, settings: Settings) -> Optional[dict]:
    """验证JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ============== 内存用户存储（开发环境使用，生产环境应使用数据库）==============

class InMemoryUserStore:
    """内存用户存储（开发环境使用）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        from modules.foundation.auth_manager.auth import PasswordHasher, UserStatus
        self._users = {}
        self._password_hasher = PasswordHasher
        # 初始化默认管理员
        self._init_default_users()
    
    def _init_default_users(self):
        """初始化默认用户"""
        from modules.foundation.auth_manager.auth import UserStatus, User
        admin = User(
            id="u001",
            username="admin",
            password_hash=self._password_hasher.hash_password("Admin@123456"),
            email="admin@example.com",
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            roles=["admin"]
        )
        self._users["admin"] = admin
        
        operator = User(
            id="u002",
            username="operator",
            password_hash=self._password_hasher.hash_password("Operator@123456"),
            email="operator@example.com",
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            roles=["operator"]
        )
        self._users["operator"] = operator
    
    def get_user(self, username: str):
        """获取用户"""
        return self._users.get(username)
    
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """验证用户凭证"""
        user = self._users.get(username)
        if not user:
            return None
        
        from modules.foundation.auth_manager.auth import UserStatus
        if user.status == UserStatus.LOCKED:
            return None
        
        if not self._password_hasher.verify_password(password, user.password_hash):
            return None
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
        }
    
    def create_user(self, username: str, password: str, email: str = None, full_name: str = None) -> dict:
        """创建用户"""
        if username in self._users:
            raise ValueError("用户名已存在")
        
        from modules.foundation.auth_manager.auth import UserStatus, User
        user = User(
            id=f"u{secrets.token_hex(4)}",
            username=username,
            password_hash=self._password_hasher.hash_password(password),
            email=email,
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            roles=["viewer"]  # 默认角色
        )
        self._users[username] = user
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
        }
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """根据ID获取用户"""
        for user in self._users.values():
            if user.id == user_id:
                from modules.foundation.auth_manager.auth import UserStatus
                return {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "roles": user.roles,
                    "is_active": user.status == UserStatus.ACTIVE,
                }
        return None


# 获取用户存储实例
_user_store = InMemoryUserStore()


# ============== API路由 ==============

@router.post("/login", response_model=Token, tags=["认证"])
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    """
    settings = get_settings()
    
    # 验证用户凭证
    user = _user_store.authenticate(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["username"],
            "user_id": user["user_id"],
            "roles": user["roles"]
        },
        expires_delta=access_token_expires,
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=Token, include_in_schema=False)
async def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2兼容的登录表单"""
    settings = get_settings()
    
    user = _user_store.authenticate(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "user_id": user["user_id"], "roles": user["roles"]},
        expires_delta=access_token_expires,
    )
    
    return Token(access_token=access_token, token_type="bearer", expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/logout", tags=["认证"])
async def logout():
    """用户登出"""
    return {"message": "登出成功"}


@router.post("/register", response_model=UserResponse, tags=["认证"])
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册
    
    - **username**: 用户名 (3-50字符)
    - **password**: 密码 (至少6字符)
    - **email**: 邮箱 (可选)
    - **full_name**: 姓名 (可选)
    """
    try:
        user = _user_store.create_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            full_name=user_data.full_name
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return UserResponse(
        user_id=user["user_id"],
        username=user["username"],
        email=user.get("email"),
        roles=user["roles"],
        is_active=True,
        created_at=datetime.utcnow(),
    )


@router.get("/userinfo", response_model=UserResponse, tags=["认证"])
async def get_user_info(
    credentials: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取当前用户信息
    
    需要先登录获取token
    """
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=None,
        roles=current_user.roles,
        is_active=True,
        created_at=None,
    )


@router.post("/refresh", response_model=Token, tags=["认证"])
async def refresh_token(current_user: CurrentUser = Depends(get_current_user)):
    """刷新Token"""
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": current_user.username,
            "user_id": current_user.user_id,
            "roles": current_user.roles
        },
        expires_delta=access_token_expires,
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.put("/password", tags=["认证"])
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    修改密码
    
    - **old_password**: 旧密码
    - **new_password**: 新密码
    """
    # 验证旧密码
    user = _user_store.get_user(current_user.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 验证旧密码正确
    if not _user_store._password_hasher.verify_password(password_data.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 验证新密码强度
    from modules.foundation.auth_manager.auth import PasswordHasher
    is_valid, msg = PasswordHasher.validate_password_strength(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    
    # 更新密码
    user.password_hash = _user_store._password_hasher.hash_password(password_data.new_password)
    
    return {"message": "密码修改成功"}
