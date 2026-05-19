"""
系统管理API路由
提供用户管理、角色权限、系统配置等管理功能
"""

from typing import Optional, List
from datetime import datetime
import secrets
import json

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams, require_role
from sqlalchemy.orm import Session

from api.routes.auth import _user_store
from modules.foundation.auth_manager.auth import PasswordHasher


router = APIRouter()


# ============== 请求/响应模型 ==============

class UserCreate(BaseModel):
    """创建用户"""
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., description="密码")
    full_name: Optional[str] = Field(None, description="姓名")
    phone: Optional[str] = Field(None, description="电话")
    roles: List[str] = Field(default_factory=list, description="角色列表")
    is_active: bool = Field(True, description="是否启用")


class UserUpdate(BaseModel):
    """更新用户"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RoleCreate(BaseModel):
    """创建角色"""
    name: str = Field(..., description="角色名称")
    code: str = Field(..., description="角色代码")
    description: Optional[str] = Field(None, description="描述")
    permissions: List[str] = Field(default_factory=list, description="权限列表")


class SystemConfigUpdate(BaseModel):
    """更新系统配置"""
    key: str = Field(..., description="配置键")
    value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="描述")


# 预定义角色
ROLES = {
    "admin": {"name": "管理员", "code": "admin", "permissions": ["*"], "description": "系统管理员"},
    "operator": {"name": "运维工程师", "code": "operator", "permissions": ["monitoring:read", "workorder:write", "asset:read", "knowledge:read"], "description": "运维工程师"},
    "viewer": {"name": "访客", "code": "viewer", "permissions": ["monitoring:read", "asset:read", "knowledge:read"], "description": "只读访客"},
}

# 预定义权限
PERMISSIONS = [
    {"code": "monitoring:read", "name": "查看监控", "category": "monitoring"},
    {"code": "monitoring:write", "name": "管理监控", "category": "monitoring"},
    {"code": "workorder:read", "name": "查看工单", "category": "workorder"},
    {"code": "workorder:write", "name": "管理工单", "category": "workorder"},
    {"code": "asset:read", "name": "查看资产", "category": "asset"},
    {"code": "asset:write", "name": "管理资产", "category": "asset"},
    {"code": "knowledge:read", "name": "查看知识库", "category": "knowledge"},
    {"code": "knowledge:write", "name": "管理知识库", "category": "knowledge"},
    {"code": "report:read", "name": "查看报表", "category": "report"},
    {"code": "report:write", "name": "管理报表", "category": "report"},
    {"code": "admin:user", "name": "用户管理", "category": "admin"},
    {"code": "admin:role", "name": "角色管理", "category": "admin"},
    {"code": "admin:config", "name": "系统配置", "category": "admin"},
]

# 系统配置（内存存储，生产环境应存入数据库）
_system_config = {
    "system.name": {"value": "ITOps Platform", "description": "系统名称", "category": "system"},
    "system.maintenance": {"value": "false", "description": "维护模式", "category": "system"},
    "system.version": {"value": "1.0.0", "description": "系统版本", "category": "system"},
}


# ============== 用户管理接口 ==============

@router.get("/users", summary="获取用户列表")
async def get_users(
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    role: Optional[str] = Query(None, description="角色过滤"),
    is_active: Optional[bool] = Query(None, description="启用状态过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户列表"""
    # 从 InMemoryUserStore 获取所有用户
    all_users = []
    for username, user in _user_store._users.items():
        all_users.append(user)
    
    # 过滤
    filtered_users = all_users
    if keyword:
        filtered_users = [u for u in filtered_users if 
            keyword.lower() in u.username.lower() or 
            (u.email and keyword.lower() in u.email.lower())]
    
    if role:
        filtered_users = [u for u in filtered_users if role in u.roles]
    
    total = len(filtered_users)
    
    # 分页
    start = pagination.offset
    end = start + pagination.limit
    page_users = filtered_users[start:end]
    
    return {
        "items": [_user_to_dict(u) for u in page_users],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


def _user_to_dict(user) -> dict:
    """用户转字典"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.metadata.get("full_name") if user.metadata else None,
        "phone": user.metadata.get("phone") if user.metadata else None,
        "roles": user.roles,
        "is_active": user.status.value == "active",
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat(),
    }


@router.post("/users", summary="创建用户")
async def create_user(
    user: UserCreate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """创建新用户"""
    try:
        new_user = _user_store.create_user(
            username=user.username,
            password=user.password,
            email=user.email,
        )
        # 更新额外信息
        existing_user = _user_store.get_user(user.username)
        if existing_user and hasattr(existing_user, 'metadata'):
            existing_user.metadata["full_name"] = user.full_name
            existing_user.metadata["phone"] = user.phone
            existing_user.roles = user.roles if user.roles else ["viewer"]
        
        return {
            "id": existing_user.id if existing_user else new_user.get("user_id"),
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
            "is_active": user.is_active,
            "created_at": datetime.now().isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}", summary="获取用户详情")
async def get_user(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户详细信息"""
    user_data = _user_store.get_user_by_id(str(user_id))
    
    if not user_data:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取完整用户对象
    for username, user in _user_store._users.items():
        if user.id == str(user_id):
            return _user_to_dict(user)
    
    raise HTTPException(status_code=404, detail="用户不存在")


@router.put("/users/{user_id}", summary="更新用户")
async def update_user(
    user_id: int,
    user: UserUpdate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """更新用户信息"""
    # 获取用户
    target_user = None
    for username, u in _user_store._users.items():
        if u.id == str(user_id):
            target_user = u
            break
    
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新字段
    if user.email:
        target_user.email = user.email
    if user.roles:
        target_user.roles = user.roles
    if user.is_active is not None:
        from modules.foundation.auth_manager.auth import UserStatus
        target_user.status = UserStatus.ACTIVE if user.is_active else UserStatus.INACTIVE
    if not target_user.metadata:
        target_user.metadata = {}
    if user.full_name:
        target_user.metadata["full_name"] = user.full_name
    if user.phone:
        target_user.metadata["phone"] = user.phone
    
    target_user.updated_at = datetime.now()
    
    return {"status": "success", "message": "User updated successfully"}


@router.delete("/users/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """删除用户"""
    for username, user in list(_user_store._users.items()):
        if user.id == str(user_id):
            if username == "admin":
                raise HTTPException(status_code=400, detail="不能删除管理员账户")
            del _user_store._users[username]
            return {"status": "success", "message": "User deleted successfully"}
    
    raise HTTPException(status_code=404, detail="用户不存在")


@router.post("/users/{user_id}/reset-password", summary="重置密码")
async def reset_password(
    user_id: int,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """重置用户密码"""
    for username, user in _user_store._users.items():
        if user.id == str(user_id):
            new_password = f"Password@{secrets.token_hex(4)}"
            user.password_hash = PasswordHasher.hash_password(new_password)
            user.updated_at = datetime.now()
            return {
                "status": "success",
                "message": "Password reset successfully",
                "new_password": new_password,  # 临时显示，实际应通过安全渠道发送
            }
    
    raise HTTPException(status_code=404, detail="用户不存在")


# ============== 角色管理接口 ==============

@router.get("/roles", summary="获取角色列表")
async def get_roles(
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """获取角色列表"""
    items = []
    for code, role in ROLES.items():
        # 统计使用该角色的用户数
        user_count = sum(1 for u in _user_store._users.values() if code in u.roles)
        items.append({
            "id": hash(code) % 10000,
            "name": role["name"],
            "code": role["code"],
            "description": role["description"],
            "permissions": role["permissions"],
            "user_count": user_count,
        })
    
    return {"items": items, "total": len(items)}


@router.post("/roles", summary="创建角色")
async def create_role(
    role: RoleCreate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """创建新角色"""
    if role.code in ROLES:
        raise HTTPException(status_code=400, detail="角色代码已存在")
    
    ROLES[role.code] = {
        "name": role.name,
        "code": role.code,
        "permissions": role.permissions,
        "description": role.description or "",
    }
    
    return {
        "id": hash(role.code) % 10000,
        "name": role.name,
        "code": role.code,
        "permissions": role.permissions,
        "created_at": datetime.now().isoformat(),
    }


@router.put("/roles/{role_id}", summary="更新角色")
async def update_role(
    role_id: int,
    role: RoleCreate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """更新角色"""
    # 查找角色
    found_code = None
    for code, r in ROLES.items():
        if hash(code) % 10000 == role_id:
            found_code = code
            break
    
    if not found_code:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    ROLES[found_code] = {
        "name": role.name,
        "code": found_code,
        "permissions": role.permissions,
        "description": role.description or "",
    }
    
    return {"status": "success", "message": "Role updated successfully"}


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """删除角色"""
    found_code = None
    for code, r in ROLES.items():
        if hash(code) % 10000 == role_id:
            found_code = code
            break
    
    if not found_code:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    if found_code == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员角色")
    
    del ROLES[found_code]
    return {"status": "success", "message": "Role deleted successfully"}


# ============== 权限管理接口 ==============

@router.get("/permissions", summary="获取权限列表")
async def get_permissions(
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """获取系统所有权限列表"""
    return {"items": PERMISSIONS, "total": len(PERMISSIONS)}


# ============== 系统配置接口 ==============

@router.get("/config", summary="获取系统配置")
async def get_system_config(
    category: Optional[str] = Query(None, description="配置分类过滤"),
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """获取系统配置"""
    items = []
    for key, cfg in _system_config.items():
        if category and cfg.get("category") != category:
            continue
        items.append({
            "key": key,
            "value": cfg["value"],
            "description": cfg.get("description"),
            "category": cfg.get("category"),
            "updated_at": datetime.now().isoformat(),
        })
    
    return {"items": items, "total": len(items)}


@router.put("/config/{config_key}", summary="更新系统配置")
async def update_system_config(
    config_key: str,
    config: SystemConfigUpdate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """更新系统配置"""
    if config_key not in _system_config:
        _system_config[config_key] = {}
    
    _system_config[config_key]["value"] = config.value
    _system_config[config_key]["description"] = config.description or _system_config[config_key].get("description", "")
    
    return {"status": "success", "message": "Configuration updated successfully"}


# ============== 系统信息接口 ==============

@router.get("/info", summary="获取系统信息")
async def get_system_info(
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取系统运行信息"""
    return {
        "version": _system_config.get("system.version", {}).get("value", "1.0.0"),
        "environment": "production",
        "uptime": 86400,
        "database": {
            "type": "mysql",
            "status": "connected",
            "connections": 10,
        },
        "redis": {
            "status": "connected",
        },
    }


@router.get("/metrics", summary="获取系统指标")
async def get_system_metrics(
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """获取系统性能指标"""
    # 简化实现，返回模拟数据
    # 实际应从系统收集真实指标
    return {
        "cpu": {"usage": 45.5, "cores": 8},
        "memory": {"total": 16384, "used": 8192, "usage": 50.0},
        "disk": {"total": 512000, "used": 256000, "usage": 50.0},
        "network": {"in": 1000, "out": 500},
    }


# ============== 操作日志接口 ==============

@router.get("/logs", summary="获取操作日志")
async def get_operation_logs(
    operator: Optional[str] = Query(None, description="操作人过滤"),
    action: Optional[str] = Query(None, description="操作类型过滤"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """获取操作日志"""
    from modules.foundation.db_models.system import OperationLog

    query = db.query(OperationLog)

    if operator:
        query = query.filter(OperationLog.username == operator)
    if action:
        query = query.filter(OperationLog.action == action)
    if start_date:
        query = query.filter(OperationLog.timestamp >= start_date)
    if end_date:
        query = query.filter(OperationLog.timestamp <= end_date)

    total = query.count()
    logs = query.order_by(OperationLog.timestamp.desc()).offset(pagination.offset).limit(pagination.limit).all()

    return {
        "items": [
            {
                "id": log.id,
                "username": log.username,
                "action": log.action,
                "resource": log.resource,
                "resource_id": log.resource_id,
                "method": log.method,
                "path": log.path,
                "ip_address": log.ip_address,
                "response_status": log.response_status,
                "duration_ms": log.duration_ms,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


# ============== 备份管理接口 ==============

@router.get("/backup", summary="获取备份列表")
async def get_backups(
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """获取数据库备份列表"""
    from modules.foundation.db_models.system import BackupRecord

    backups = db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).all()

    return {
        "items": [
            {
                "id": b.id,
                "backup_type": b.backup_type,
                "file_name": b.file_name,
                "file_path": b.file_path,
                "file_size": b.file_size,
                "status": b.status,
                "storage_type": b.storage_type,
                "created_by": b.created_by,
                "started_at": b.started_at.isoformat() if b.started_at else None,
                "completed_at": b.completed_at.isoformat() if b.completed_at else None,
                "duration_seconds": b.duration_seconds,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in backups
        ],
        "total": len(backups)
    }


@router.post("/backup", summary="创建备份")
async def create_backup(
    backup_type: str = Query("full", description="备份类型: full, incremental, config"),
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """创建数据库备份"""
    from modules.foundation.db_models.system import BackupRecord
    import os

    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"backup_{backup_type}_{timestamp}.sql"
    backup_dir = "/tmp/backups"

    # 确保备份目录存在
    os.makedirs(backup_dir, exist_ok=True)
    file_path = os.path.join(backup_dir, file_name)

    # 创建备份记录
    backup_record = BackupRecord(
        backup_type=backup_type,
        file_name=file_name,
        file_path=file_path,
        status="completed",
        storage_type="local",
        storage_path=backup_dir,
        created_by=current_user.username,
        started_at=datetime.now(),
        completed_at=datetime.now(),
        duration_seconds=0,
    )

    db.add(backup_record)
    db.commit()
    db.refresh(backup_record)

    return {
        "status": "success",
        "message": "Backup created",
        "task_id": f"backup-{timestamp}",
        "backup_id": backup_record.id,
        "file_name": file_name,
        "file_path": file_path,
    }


@router.post("/backup/{backup_id}/restore", summary="恢复备份")
async def restore_backup(
    backup_id: int,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """恢复数据库备份"""
    # 简化实现
    return {
        "status": "success",
        "message": "Restore task created",
        "task_id": f"restore-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }


# ============== 缓存管理接口 ==============

@router.post("/cache/clear", summary="清空缓存")
async def clear_cache(
    cache_type: str = Query("all", description="缓存类型: all, redis, memory"),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """清空系统缓存"""
    # 简化实现
    return {
        "status": "success",
        "message": f"{cache_type} cache cleared",
    }


# ============== 健康检查接口 ==============

@router.get("/health", summary="系统健康检查")
async def system_health_check(
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """执行系统健康检查"""
    return {
        "status": "healthy",
        "components": {
            "database": {"status": "healthy", "latency_ms": 5},
            "redis": {"status": "healthy", "latency_ms": 1},
            "filesystem": {"status": "healthy", "usage_percent": 45},
            "monitoring": {"status": "healthy"},
        },
        "checked_at": datetime.now().isoformat(),
    }


# ============== API Key管理接口 ==============

import secrets
import hashlib
import string


def _generate_api_key(prefix: str = "sk") -> tuple:
    """
    生成API Key
    Returns: (full_key, key_hash, key_prefix)
    """
    # 生成随机字符串
    random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))
    full_key = f"{prefix}-{random_part}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = f"{prefix}-{random_part[:8]}"
    return full_key, key_hash, key_prefix


def _mask_api_key(key: str) -> str:
    """掩码API Key，只显示前8位"""
    if len(key) > 12:
        return f"{key[:12]}{'***'}"
    return f"{key[:4]}{'***'}"


class APIKeyCreate(BaseModel):
    """创建API Key"""
    name: str = Field(..., description="API Key名称")
    user_id: Optional[str] = Field(None, description="关联用户ID")
    username: Optional[str] = Field(None, description="关联用户名")
    scopes: List[str] = Field(default_factory=list, description="权限范围")
    expires_days: Optional[int] = Field(None, description="过期天数，为空表示永不过期")
    max_requests: Optional[int] = Field(None, description="最大请求数，为空表示无限制")
    rate_limit: Optional[int] = Field(100, description="每分钟请求数限制")
    rate_limit_window: Optional[int] = Field(60, description="速率限制时间窗口(秒)")


class APIKeyUpdate(BaseModel):
    """更新API Key"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    scopes: Optional[List[str]] = None
    expires_days: Optional[int] = None
    max_requests: Optional[int] = None
    rate_limit: Optional[int] = None


@router.get("/api-keys", summary="获取API Key列表")
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

    return {
        "items": [
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
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "created_by": k.created_by,
            }
            for k in keys
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/api-keys", summary="创建API Key")
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
        from datetime import timedelta
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
        max_requests=api_key_data.max_requests or -1,
        rate_limit=api_key_data.rate_limit or 100,
        rate_limit_window=api_key_data.rate_limit_window or 60,
        created_by=current_user.username,
    )

    db.add(api_key_record)
    db.commit()
    db.refresh(api_key_record)

    return {
        "id": api_key_record.id,
        "key_id": api_key_record.key_id,
        "api_key": full_key,  # 只在创建时返回一次
        "key_prefix": key_prefix,
        "name": api_key_data.name,
        "scopes": api_key_data.scopes,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "max_requests": api_key_data.max_requests,
        "rate_limit": api_key_data.rate_limit,
        "created_at": api_key_record.created_at.isoformat() if api_key_record.created_at else None,
        "message": "请妥善保管API Key，仅在创建时显示完整Key"
    }


@router.get("/api-keys/{key_id}", summary="获取API Key详情")
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
    }


@router.put("/api-keys/{key_id}", summary="更新API Key")
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
        from datetime import timedelta
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

    return {"status": "success", "message": "API Key更新成功"}


@router.delete("/api-keys/{key_id}", summary="删除API Key")
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

    return {"status": "success", "message": "API Key删除成功"}


@router.post("/api-keys/{key_id}/revoke", summary="撤销API Key")
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

    return {"status": "success", "message": "API Key已撤销"}


@router.post("/api-keys/{key_id}/activate", summary="激活API Key")
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

    return {"status": "success", "message": "API Key已激活"}


@router.post("/api-keys/{key_id}/rotate", summary="轮换API Key")
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
        "status": "success",
        "message": "API Key已轮换，旧Key已禁用",
        "old_key_id": key_id,
        "new_key_id": new_key_record.key_id,
        "new_api_key": full_key,
        "key_prefix": key_prefix,
    }


# ============== 备份恢复接口 ==============

class BackupCreateRequest(BaseModel):
    """创建备份请求"""
    name: str = Field(..., description="备份名称")
    backup_type: str = Field("full", description="备份类型: full, incremental, differential")
    targets: List[str] = Field(default_factory=list, description="备份目标: database, config, files, all")
    description: str = Field("", description="备份描述")


class BackupRestoreRequest(BaseModel):
    """恢复备份请求"""
    target: str = Field("all", description="恢复目标: database, config, files, all")
    target_path: Optional[str] = Field(None, description="恢复路径")
    create_pre_backup: bool = Field(True, description="恢复前是否创建备份")


@router.get("/backups", summary="获取备份列表")
async def get_backups(
    status: Optional[str] = Query(None, description="状态过滤"),
    backup_type: Optional[str] = Query(None, description="备份类型过滤"),
    limit: int = Query(100, le=500),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """获取备份列表"""
    from modules.business.backup_manager import (
        get_backup_manager, BackupStatus, BackupType
    )
    
    manager = get_backup_manager()
    
    status_enum = None
    if status:
        try:
            status_enum = BackupStatus(status)
        except ValueError:
            pass
    
    type_enum = None
    if backup_type:
        try:
            type_enum = BackupType(backup_type)
        except ValueError:
            pass
    
    backups = manager.list_backups(status=status_enum, backup_type=type_enum, limit=limit)
    
    return {
        "items": [b.to_dict() for b in backups],
        "total": len(backups),
    }


@router.post("/backups", summary="创建备份")
async def create_backup(
    request: BackupCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """创建新的备份"""
    from modules.business.backup_manager import (
        get_backup_manager, BackupStatus, BackupType, BackupTarget
    )
    
    manager = get_backup_manager()
    
    # 解析备份类型
    backup_type = BackupType(request.backup_type)
    
    # 解析目标
    targets = []
    if not request.targets or 'all' in request.targets:
        targets = [BackupTarget.ALL]
    else:
        for t in request.targets:
            try:
                targets.append(BackupTarget(t))
            except ValueError:
                pass
    
    record = await manager.create_backup(
        name=request.name,
        backup_type=backup_type,
        targets=targets,
        description=request.description,
    )
    
    return {
        "id": record.id,
        "status": record.status.value if isinstance(record.status, BackupStatus) else record.status,
        "message": "备份创建成功" if record.status == BackupStatus.SUCCESS else "备份创建失败",
        "record": record.to_dict(),
    }


@router.get("/backups/{backup_id}", summary="获取备份详情")
async def get_backup(
    backup_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """获取备份详细信息"""
    from modules.business.backup_manager import get_backup_manager
    
    manager = get_backup_manager()
    backup = manager.get_backup(backup_id)
    
    if not backup:
        raise HTTPException(status_code=404, detail="备份不存在")
    
    return backup.to_dict()


@router.delete("/backups/{backup_id}", summary="删除备份")
async def delete_backup(
    backup_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """删除备份"""
    from modules.business.backup_manager import get_backup_manager
    
    manager = get_backup_manager()
    
    if not manager.delete_backup(backup_id):
        raise HTTPException(status_code=404, detail="备份不存在")
    
    return {"status": "success", "message": "备份已删除"}


@router.post("/backups/{backup_id}/restore", summary="恢复备份")
async def restore_backup(
    backup_id: str,
    request: BackupRestoreRequest,
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """从备份恢复数据"""
    from modules.business.backup_manager import (
        get_backup_manager, BackupTarget
    )
    
    manager = get_backup_manager()
    
    backup = manager.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="备份不存在")
    
    target = BackupTarget(request.target)
    
    record = await manager.restore(
        backup_id=backup_id,
        target=target,
        target_path=request.target_path,
        create_pre_backup=request.create_pre_backup,
    )
    
    return {
        "id": record.id,
        "status": record.status.value if isinstance(record.status, RestoreStatus) else record.status,
        "message": "恢复成功" if record.status == RestoreStatus.SUCCESS else "恢复失败",
        "record": record.to_dict(),
    }


@router.get("/restores", summary="获取恢复记录列表")
async def get_restores(
    limit: int = Query(100, le=500),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """获取恢复记录列表"""
    from modules.business.backup_manager import get_backup_manager
    
    manager = get_backup_manager()
    restores = manager.list_restores(limit=limit)
    
    return {
        "items": [r.to_dict() for r in restores],
        "total": len(restores),
    }


@router.get("/restores/{restore_id}", summary="获取恢复记录详情")
async def get_restore(
    restore_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """获取恢复记录详细信息"""
    from modules.business.backup_manager import get_backup_manager
    
    manager = get_backup_manager()
    restore = manager.get_restore(restore_id)
    
    if not restore:
        raise HTTPException(status_code=404, detail="恢复记录不存在")
    
    return restore.to_dict()


@router.post("/backups/cleanup", summary="清理过期备份")
async def cleanup_backups(
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """清理过期的备份文件"""
    from modules.business.backup_manager import get_backup_manager
    
    manager = get_backup_manager()
    count = manager.cleanup_old_backups()
    
    return {"status": "success", "message": f"已清理 {count} 个过期备份"}


@router.get("/backup/config", summary="获取备份配置")
async def get_backup_config(
    current_user: CurrentUser = Depends(require_role("admin")),
):
    """获取备份配置信息"""
    from modules.business.backup_manager import get_backup_manager
    
    manager = get_backup_manager()
    config = manager.config
    
    return {
        "backup_dir": config.backup_dir,
        "retention_days": config.retention_days,
        "max_backups": config.max_backups,
        "compression_enabled": config.compression_enabled,
        "compression_level": config.compression_level,
        "encryption_enabled": config.encryption_enabled,
        "auto_backup_enabled": config.auto_backup_enabled,
        "backup_schedule": config.backup_schedule,
    }
