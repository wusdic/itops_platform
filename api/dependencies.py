"""
依赖注入模块
提供数据库会话、认证、权限检查、分页参数等依赖
"""

import os
import logging
from functools import lru_cache
from typing import Optional, Generator, List, Any
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from modules.foundation.db_models.base import get_engine, db_session


# ============== 配置相关 ==============

@dataclass
class Settings:
    """应用配置"""
    # 环境
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API配置
    API_V1_PREFIX: str = "/api/v1"
    API_TITLE: str = "ITOps Platform API"
    API_VERSION: str = "1.0.0"
    
    # CORS配置
    CORS_ORIGINS: List[str] = None
    
    # 认证配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库配置
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # 分页默认值
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    def __post_init__(self):
        if self.CORS_ORIGINS is None:
            self.CORS_ORIGINS = ["*"]


@lru_cache()
def get_settings() -> Settings:
    """
    获取应用配置
    使用lru_cache缓存配置实例
    """
    return Settings(
        ENVIRONMENT=os.getenv("ENVIRONMENT", "development"),
        DEBUG=os.getenv("DEBUG", "true").lower() == "true",
        SECRET_KEY=os.getenv("SECRET_KEY", "your-secret-key-change-in-production"),
        REDIS_HOST=os.getenv("REDIS_HOST", "localhost"),
        REDIS_PORT=int(os.getenv("REDIS_PORT", "6379")),
    )


# ============== 数据库依赖 ==============

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    使用上下文管理器确保会话正确关闭
    如果数据库未初始化，抛出503错误
    """
    from fastapi import HTTPException

    try:
        from modules.foundation.db_models.base import _db_manager
        session = _db_manager.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Database not available: {e}")
        raise HTTPException(status_code=503, detail="数据库服务不可用，请检查数据库连接")


# ============== 认证相关 ==============

# Bearer Token认证
security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """当前登录用户"""
    user_id: str
    username: str
    email: Optional[str] = None
    roles: List[str] = None
    permissions: List[str] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
    
    def has_role(self, role: str) -> bool:
        """检查用户是否具有指定角色"""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """检查用户是否具有指定权限"""
        return permission in self.permissions
    
    def is_admin(self) -> bool:
        """检查用户是否为管理员"""
        return "admin" in self.roles or "super_admin" in self.roles


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """
    获取当前登录用户
    从JWT Token中解析用户信息
    """
    settings = get_settings()
    
    # 如果没有提供凭证
    if not credentials:
        if settings.DEBUG:
            # 开发环境返回默认用户
            return CurrentUser(
                user_id="dev_user",
                username="developer",
                email="dev@example.com",
                roles=["admin"],
                permissions=["*"],
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证JWT Token
    try:
        from jose import jwt, JWTError
        
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        roles = payload.get("roles", [])
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return CurrentUser(
            user_id=user_id or username,
            username=username,
            email=None,
            roles=roles,
            permissions=[],
        )
        
    except JWTError as e:
        if settings.DEBUG:
            # 开发环境允许无有效token访问
            return CurrentUser(
                user_id="dev_user",
                username="developer",
                email="dev@example.com",
                roles=["admin"],
                permissions=["*"],
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """
    获取当前登录用户（可选）
    不强制要求认证
    """
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ============== 权限检查 ==============

def require_permission(permission: str):
    """
    权限检查依赖装饰器
    使用示例:
        @router.get("/items", dependencies=[Depends(require_permission("item:read"))])
    """
    async def check_permission(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user
    return check_permission


def require_role(role: str):
    """
    角色检查依赖装饰器
    使用示例:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    async def check_role(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}",
            )
        return current_user
    return check_role


# ============== 分页相关 ==============

@dataclass
class PaginationParams:
    """分页参数"""
    page: int = Query(1, ge=1, description="页码")
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """返回限制数量"""
        return self.page_size


def get_pagination_params(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> PaginationParams:
    """获取分页参数"""
    return PaginationParams(page=page, page_size=page_size)


@dataclass
class PaginatedResponse:
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(
        cls,
        items: List[Any],
        total: int,
        params: PaginationParams,
    ) -> "PaginatedResponse":
        """创建分页响应"""
        total_pages = (total + params.page_size - 1) // params.page_size
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )


# ============== 通用依赖 ==============

async def get_request_id(
    request: Any = None,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
) -> Optional[str]:
    """获取请求ID"""
    return x_request_id


async def verify_api_key(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """验证API Key"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is required",
        )
    # TODO: 实现API Key验证逻辑
    return api_key
