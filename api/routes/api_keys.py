"""
API Key管理路由
提供API Key的CRUD操作和管理功能
遵循 {"data": ..., "code": 0} 响应格式
"""

import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams, require_role


router = APIRouter()


# ============== 辅助函数 ==============

def _generate_api_key() -> tuple:
    """
    生成API Key
    使用 secrets.token_urlsafe(32) 生成安全的随机Key
    Returns: (full_key, key_hash, key_prefix)
    """
    # 生成32字节的随机字符串，URL-safe base64编码
    random_part = secrets.token_urlsafe(32)
    full_key = f"sk-{random_part}"  # sk- 前缀表示 secret key
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = f"sk-{random_part[:8]}"  # 显示前8位用于识别
    return full_key, key_hash, key_prefix


def _mask_api_key(key: str) -> str:
    """掩码API Key，只显示前8位"""
    if len(key) > 12:
        return f"{key[:12]}***"
    return f"{key[:4]}***"


# ============== 请求/响应模型 ==============

class APIKeyCreate(BaseModel):
    """创建API Key请求"""
    name: str = Field(..., description="API Key名称")
    user_id: Optional[str] = Field(None, description="关联用户ID")
    username: Optional[str] = Field(None, description="关联用户名")
    scopes: List[str] = Field(default_factory=list, description="权限范围")
    expires_days: Optional[int] = Field(None, description="过期天数，为空表示永不过期")
    max_requests: Optional[int] = Field(None, description="最大请求数，为空表示无限制")
    rate_limit: Optional[int] = Field(100, description="每分钟请求数限制")
    rate_limit_window: Optional[int] = Field(60, description="速率限制时间窗口(秒)")


class APIKeyUpdate(BaseModel):
    """更新API Key请求"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    scopes: Optional[List[str]] = None
    expires_days: Optional[int] = None
    max_requests: Optional[int] = None
    rate_limit: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API Key响应"""
    id: int
    key_id: str
    key_prefix: str
    name: str
    username: Optional[str] = None
    scopes: List[str] = []
    is_active: bool
    is_revoked: bool
    expires_at: Optional[str] = None
    max_requests: int
    request_count: int
    rate_limit: int
    rate_limit_window: int
    last_used_at: Optional[str] = None
    last_used_ip: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None


# ============== API Routes ==============

@router.get("", summary="获取API Key列表")
async def get_api_keys(
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    is_active: Optional[bool] = Query(None, description="启用状态过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """获取API Key列表"""
    from modules.foundation.db_models.system import APIKey

    query = db.query(APIKey)

    if keyword:
        query = query.filter(
            (APIKey.name.ilike(f"%{keyword}%")) |
            (APIKey.key_id.ilike(f"%{keyword}%")) |
            (APIKey.username.ilike(f"%{keyword}%"))
        )

    if is_active is not None:
        query = query.filter(APIKey.is_active == (1 if is_active else 0))

    total = query.count()
    keys = query.order_by(APIKey.created_at.desc()).offset(pagination.offset).limit(pagination.limit).all()

    items = [
        {
            "id": k.id,
            "key_id": k.key_id,
            "key_prefix": k.key_prefix,
            "name": k.name,
            "username": k.username,
            "scopes": json.loads(k.scopes) if k.scopes else [],
            "is_active": bool(k.is_active),
            "is_revoked": bool(k.is_revoked),
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "max_requests": k.max_requests,
            "request_count": k.request_count,
            "rate_limit": k.rate_limit,
            "rate_limit_window": k.rate_limit_window,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "created_by": k.created_by,
        }
        for k in keys
    ]

    return {
        "data": items,
        "code": 0,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("", summary="创建API Key")
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """创建新的API Key"""
    from modules.foundation.db_models.system import APIKey

    # 生成API Key
    full_key, key_hash, key_prefix = _generate_api_key()

    # 计算过期时间
    expires_at = None
    if api_key_data.expires_days:
        expires_at = datetime.now() + timedelta(days=api_key_data.expires_days)

    # 创建记录
    api_key_record = APIKey(
        key_id=f"key_{secrets.token_hex(8)}",
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=api_key_data.name,
        user_id=api_key_data.user_id,
        username=api_key_data.username,
        scopes=json.dumps(api_key_data.scopes) if api_key_data.scopes else None,
        is_active=1,
        is_revoked=0,
        expires_at=expires_at,
        max_requests=api_key_data.max_requests if api_key_data.max_requests else -1,
        rate_limit=api_key_data.rate_limit if api_key_data.rate_limit else 100,
        rate_limit_window=api_key_data.rate_limit_window if api_key_data.rate_limit_window else 60,
        created_by=current_user.username,
    )

    db.add(api_key_record)
    db.commit()
    db.refresh(api_key_record)

    return {
        "data": {
            "id": api_key_record.id,
            "key_id": api_key_record.key_id,
            "api_key": full_key,  # 只在创建时返回一次
            "key_prefix": key_prefix,
            "name": api_key_data.name,
            "username": api_key_data.username,
            "scopes": api_key_data.scopes,
            "is_active": True,
            "is_revoked": False,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "max_requests": api_key_data.max_requests,
            "rate_limit": api_key_data.rate_limit,
            "rate_limit_window": api_key_data.rate_limit_window,
            "created_at": api_key_record.created_at.isoformat() if api_key_record.created_at else None,
            "created_by": current_user.username,
        },
        "code": 0,
        "message": "API Key创建成功，请妥善保管，仅在创建时显示完整Key",
    }


@router.get("/{key_id}", summary="获取API Key详情")
async def get_api_key(
    key_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """获取指定API Key的详细信息"""
    from modules.foundation.db_models.system import APIKey

    api_key_record = db.query(APIKey).filter(APIKey.key_id == key_id).first()

    if not api_key_record:
        raise HTTPException(status_code=404, detail="API Key不存在")

    return {
        "data": {
            "id": api_key_record.id,
            "key_id": api_key_record.key_id,
            "key_prefix": api_key_record.key_prefix,
            "name": api_key_record.name,
            "user_id": api_key_record.user_id,
            "username": api_key_record.username,
            "scopes": json.loads(api_key_record.scopes) if api_key_record.scopes else [],
            "is_active": bool(api_key_record.is_active),
            "is_revoked": bool(api_key_record.is_revoked),
            "expires_at": api_key_record.expires_at.isoformat() if api_key_record.expires_at else None,
            "max_requests": api_key_record.max_requests,
            "request_count": api_key_record.request_count,
            "rate_limit": api_key_record.rate_limit,
            "rate_limit_window": api_key_record.rate_limit_window,
            "last_used_at": api_key_record.last_used_at.isoformat() if api_key_record.last_used_at else None,
            "last_used_ip": api_key_record.last_used_ip,
            "created_at": api_key_record.created_at.isoformat() if api_key_record.created_at else None,
            "created_by": api_key_record.created_by,
        },
        "code": 0,
    }


@router.put("/{key_id}", summary="更新API Key")
async def update_api_key(
    key_id: str,
    api_key_data: APIKeyUpdate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """更新API Key"""
    from modules.foundation.db_models.system import APIKey

    api_key_record = db.query(APIKey).filter(APIKey.key_id == key_id).first()

    if not api_key_record:
        raise HTTPException(status_code=404, detail="API Key不存在")

    # 更新字段
    if api_key_data.name is not None:
        api_key_record.name = api_key_data.name

    if api_key_data.enabled is not None:
        api_key_record.is_active = 1 if api_key_data.enabled else 0

    if api_key_data.scopes is not None:
        api_key_record.scopes = json.dumps(api_key_data.scopes)

    if api_key_data.expires_days is not None:
        if api_key_data.expires_days > 0:
            api_key_record.expires_at = datetime.now() + timedelta(days=api_key_data.expires_days)
        else:
            api_key_record.expires_at = None

    if api_key_data.max_requests is not None:
        api_key_record.max_requests = api_key_data.max_requests

    if api_key_data.rate_limit is not None:
        api_key_record.rate_limit = api_key_data.rate_limit

    api_key_record.updated_at = datetime.now()

    db.commit()

    return {
        "data": None,
        "code": 0,
        "message": "API Key更新成功",
    }


@router.delete("/{key_id}", summary="删除API Key")
async def delete_api_key(
    key_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """删除API Key"""
    from modules.foundation.db_models.system import APIKey

    api_key_record = db.query(APIKey).filter(APIKey.key_id == key_id).first()

    if not api_key_record:
        raise HTTPException(status_code=404, detail="API Key不存在")

    db.delete(api_key_record)
    db.commit()

    return {
        "data": None,
        "code": 0,
        "message": "API Key删除成功",
    }


@router.post("/{key_id}/revoke", summary="撤销API Key")
async def revoke_api_key(
    key_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """撤销API Key（软删除）"""
    from modules.foundation.db_models.system import APIKey

    api_key_record = db.query(APIKey).filter(APIKey.key_id == key_id).first()

    if not api_key_record:
        raise HTTPException(status_code=404, detail="API Key不存在")

    if api_key_record.is_revoked:
        raise HTTPException(status_code=400, detail="API Key已被撤销")

    api_key_record.is_revoked = 1
    api_key_record.is_active = 0
    api_key_record.updated_at = datetime.now()

    db.commit()

    return {
        "data": None,
        "code": 0,
        "message": "API Key已撤销",
    }


@router.post("/{key_id}/activate", summary="激活API Key")
async def activate_api_key(
    key_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """激活被禁用的API Key"""
    from modules.foundation.db_models.system import APIKey

    api_key_record = db.query(APIKey).filter(APIKey.key_id == key_id).first()

    if not api_key_record:
        raise HTTPException(status_code=404, detail="API Key不存在")

    if api_key_record.is_revoked:
        raise HTTPException(status_code=400, detail="已撤销的API Key无法激活，请重新创建")

    api_key_record.is_active = 1
    api_key_record.updated_at = datetime.now()

    db.commit()

    return {
        "data": None,
        "code": 0,
        "message": "API Key已激活",
    }


@router.post("/{key_id}/rotate", summary="轮换API Key")
async def rotate_api_key(
    key_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """轮换API Key（创建新的Key并禁用旧的）"""
    from modules.foundation.db_models.system import APIKey

    api_key_record = db.query(APIKey).filter(APIKey.key_id == key_id).first()

    if not api_key_record:
        raise HTTPException(status_code=404, detail="API Key不存在")

    # 生成新Key
    full_key, key_hash, key_prefix = _generate_api_key()

    # 更新旧Key为禁用
    api_key_record.is_active = 0
    api_key_record.is_revoked = 1
    api_key_record.updated_at = datetime.now()

    # 创建新Key（复制原Key的大部分属性）
    new_key_record = APIKey(
        key_id=f"key_{secrets.token_hex(8)}",
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=api_key_record.name + " (轮换)",
        user_id=api_key_record.user_id,
        username=api_key_record.username,
        scopes=api_key_record.scopes,
        is_active=1,
        is_revoked=0,
        expires_at=api_key_record.expires_at,
        max_requests=api_key_record.max_requests,
        rate_limit=api_key_record.rate_limit,
        rate_limit_window=api_key_record.rate_limit_window,
        created_by=current_user.username,
    )

    db.add(new_key_record)
    db.commit()
    db.refresh(new_key_record)

    return {
        "data": {
            "old_key_id": key_id,
            "new_key_id": new_key_record.key_id,
            "new_api_key": full_key,
            "key_prefix": key_prefix,
            "name": new_key_record.name,
        },
        "code": 0,
        "message": "API Key已轮换，旧Key已禁用，请妥善保管新Key",
    }
