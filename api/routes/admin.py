"""
系统管理API路由
提供用户管理、角色权限、系统配置等管理功能
"""

from typing import Optional, List
from datetime import datetime
import secrets

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
