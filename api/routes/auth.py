# -*- coding: utf-8 -*-
"""
认证管理API路由
提供用户登录、注册、Token管理等功能
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from api.dependencies import get_db, get_settings, Settings

router = APIRouter()

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT配置
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


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

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, username: str, password: str) -> Optional[dict]:
    """
    验证用户凭证
    
    这里应该从数据库查询真实用户，暂时使用内存模拟
    """
    # 模拟用户数据（实际应从数据库读取）
    mock_users = {
        "admin": {
            "user_id": "u001",
            "username": "admin",
            "password_hash": get_password_hash("admin123"),
            "email": "admin@example.com",
            "full_name": "系统管理员",
            "roles": ["admin", "operator"],
            "is_active": True,
        },
        "operator": {
            "user_id": "u002",
            "username": "operator",
            "password_hash": get_password_hash("operator123"),
            "email": "operator@example.com",
            "full_name": "运维人员",
            "roles": ["operator"],
            "is_active": True,
        },
        "viewer": {
            "user_id": "u003",
            "username": "viewer",
            "password_hash": get_password_hash("viewer123"),
            "email": "viewer@example.com",
            "full_name": "访客",
            "roles": ["viewer"],
            "is_active": True,
        },
    }
    
    user = mock_users.get(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    if not user["is_active"]:
        return None
    
    return user


# ============== API路由 ==============

@router.post("/login", response_model=Token, tags=["认证"])
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    """
    # 验证用户凭证（使用模拟数据，不依赖真实数据库）
    # db参数仍然需要以保持FastAPI依赖注入兼容
    user = authenticate_user(db, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "user_id": user["user_id"], "roles": user["roles"]},
        expires_delta=access_token_expires,
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=Token, include_in_schema=False)
async def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2兼容的登录表单"""
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "user_id": user["user_id"], "roles": user["roles"]},
        expires_delta=access_token_expires,
    )
    
    return Token(access_token=access_token, token_type="bearer", expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)


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
    # 检查用户名是否已存在
    # 实际应查询数据库
    
    # 创建新用户
    new_user = {
        "user_id": f"u{secrets.token_hex(4)}",
        "username": user_data.username,
        "password_hash": get_password_hash(user_data.password),
        "email": user_data.email,
        "full_name": user_data.full_name,
        "roles": ["viewer"],  # 默认角色
        "is_active": True,
        "created_at": datetime.now(),
    }
    
    return UserResponse(
        user_id=new_user["user_id"],
        username=new_user["username"],
        email=new_user.get("email"),
        full_name=new_user.get("full_name"),
        roles=new_user["roles"],
        is_active=new_user["is_active"],
        created_at=new_user["created_at"],
    )


@router.get("/userinfo", response_model=UserResponse, tags=["认证"])
async def get_user_info(db: Session = Depends(get_db)):
    """
    获取当前用户信息
    
    需要先登录获取token
    """
    # 实际应从token解析用户信息
    # 暂时返回模拟数据
    return UserResponse(
        user_id="u001",
        username="admin",
        email="admin@example.com",
        full_name="系统管理员",
        roles=["admin", "operator"],
        is_active=True,
        created_at=datetime.now(),
    )


@router.post("/refresh", response_model=Token, tags=["认证"])
async def refresh_token():
    """刷新Token"""
    # 实际应验证refresh_token并颁发新access_token
    return Token(
        access_token="refreshed_token",
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.put("/password", tags=["认证"])
async def change_password(
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db)
):
    """
    修改密码
    
    - **old_password**: 旧密码
    - **new_password**: 新密码
    """
    # 实际应验证旧密码并更新数据库
    return {"message": "密码修改成功"}
