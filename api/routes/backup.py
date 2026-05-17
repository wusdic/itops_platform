"""
备份管理API路由
提供备份记录、备份创建、恢复、统计等接口
"""

import os
import shutil
import tempfile
from datetime import datetime
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.system import BackupRecord
from modules.storage.minio.client import MinIOClient


router = APIRouter(prefix="", tags=["备份管理"])


# ============== 枚举定义 ==============

class BackupType(str, Enum):
    """备份类型"""
    FULL = "full"           # 全量备份
    INCREMENTAL = "incremental"  # 增量备份
    CONFIG = "config"       # 配置备份


class BackupStatus(str, Enum):
    """备份状态"""
    PENDING = "pending"     # 待处理
    RUNNING = "running"     # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败


class StorageType(str, Enum):
    """存储类型"""
    LOCAL = "local"         # 本地存储
    REMOTE = "remote"       # 远程存储(MinIO/S3)


# ============== 请求/响应模型 ==============

class BackupCreateRequest(BaseModel):
    """创建备份请求"""
    name: str = Field(..., description="备份名称")
    backup_type: BackupType = Field(BackupType.FULL, description="备份类型")
    description: Optional[str] = Field(None, description="备份描述")
    storage_type: StorageType = Field(StorageType.LOCAL, description="存储类型")


class BackupResponse(BaseModel):
    """备份记录响应"""
    id: int
    name: str
    backup_type: str
    status: str
    file_name: Optional[str]
    file_path: Optional[str]
    file_size: Optional[int]
    storage_type: str
    storage_path: Optional[str]
    created_by: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    description: Optional[str]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BackupListResponse(BaseModel):
    """备份列表响应"""
    items: List[BackupResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BackupStatsResponse(BaseModel):
    """备份统计响应"""
    total_backups: int
    total_size: int  # bytes
    by_status: dict
    by_type: dict
    last_backup_time: Optional[datetime]
    last_successful_backup: Optional[datetime]


class RestoreRequest(BaseModel):
    """恢复备份请求"""
    confirm: bool = Field(..., description="确认恢复操作")


# ============== 存储客户端 ==============

def get_storage_client() -> MinIOClient:
    """获取存储客户端"""
    settings = get_minio_settings()
    return MinIOClient(
        endpoint=settings.get("endpoint", "localhost:9000"),
        access_key=settings.get("access_key", "minioadmin"),
        secret_key=settings.get("secret_key", "minioadmin"),
        secure=False,
        bucket=settings.get("bucket", "itops-backups")
    )


def get_minio_settings() -> dict:
    """获取MinIO配置"""
    try:
        from api.dependencies import get_settings
        settings = get_settings()
        # 可以从环境变量或配置获取MinIO设置
        return {
            "endpoint": os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            "bucket": os.getenv("MINIO_BUCKET", "itops-backups"),
        }
    except Exception:
        return {
            "endpoint": "localhost:9000",
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "bucket": "itops-backups",
        }


# ============== 备份数据源路径 ==============

def get_backup_source_path() -> str:
    """获取备份源数据路径"""
    # 默认数据目录
    data_path = os.getenv("ITOPS_DATA_PATH", "/tmp/itops_data")
    return data_path


def perform_backup(
    db: Session,
    backup_id: int,
    backup_type: str,
    storage_type: str,
    description: Optional[str] = None
) -> bool:
    """
    执行备份操作
    
    将数据复制到备份存储位置
    """
    try:
        # 获取备份记录
        backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
        if not backup:
            return False
        
        # 更新状态为运行中
        backup.status = BackupStatus.RUNNING.value
        backup.started_at = datetime.now()
        db.commit()
        
        # 创建临时目录用于打包数据
        with tempfile.TemporaryDirectory() as temp_dir:
            # 源数据路径
            source_path = get_backup_source_path()
            
            # 备份文件名称
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{backup_type}_{timestamp}.tar.gz"
            
            if storage_type == StorageType.REMOTE.value:
                # 远程存储 - 上传到MinIO
                temp_backup_path = os.path.join(temp_dir, backup_filename)
                
                # 如果源路径存在，则创建备份
                if os.path.exists(source_path):
                    # 使用tar打包
                    import tarfile
                    with tarfile.open(temp_backup_path, "w:gz") as tar:
                        tar.add(source_path, arcname="data")
                
                # 上传到MinIO
                storage_client = get_storage_client()
                result = storage_client.upload_file(
                    local_path=temp_backup_path,
                    object_name=f"backups/{backup_filename}",
                    metadata={
                        "backup_id": str(backup_id),
                        "backup_type": backup_type,
                        "created_at": datetime.now().isoformat(),
                    }
                )
                
                # 更新备份记录
                backup.file_name = backup_filename
                backup.file_path = result.get("object_name", f"backups/{backup_filename}")
                backup.file_size = result.get("size", os.path.getsize(temp_backup_path) if os.path.exists(temp_backup_path) else 0)
                backup.storage_path = result.get("object_name", f"backups/{backup_filename}")
                
            else:
                # 本地存储
                backup_dir = os.getenv("ITOPS_BACKUP_PATH", "/tmp/itops_backups")
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, backup_filename)
                
                if os.path.exists(source_path):
                    import tarfile
                    with tarfile.open(backup_path, "w:gz") as tar:
                        tar.add(source_path, arcname="data")
                
                backup.file_name = backup_filename
                backup.file_path = backup_path
                backup.file_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
                backup.storage_path = backup_path
            
            # 计算耗时
            backup.completed_at = datetime.now()
            if backup.started_at:
                backup.duration_seconds = int((backup.completed_at - backup.started_at).total_seconds())
            
            # 更新状态为完成
            backup.status = BackupStatus.COMPLETED.value
            db.commit()
            
            return True
            
    except Exception as e:
        # 更新状态为失败
        try:
            backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
            if backup:
                backup.status = BackupStatus.FAILED.value
                backup.error_message = str(e)
                backup.completed_at = datetime.now()
                db.commit()
        except Exception:
            pass
        return False


def perform_restore(
    db: Session,
    backup_id: int
) -> bool:
    """
    执行恢复操作
    
    从备份文件恢复数据
    """
    try:
        # 获取备份记录
        backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
        if not backup:
            return False
        
        if backup.status != BackupStatus.COMPLETED.value:
            raise ValueError(f"备份状态不是已完成，无法恢复: {backup.status}")
        
        # 备份当前数据
        source_path = get_backup_source_path()
        if os.path.exists(source_path):
            # 创建预恢复备份
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = f"{source_path}_pre_restore_{timestamp}"
            shutil.move(source_path, pre_restore_backup)
        
        # 临时目录用于解压
        with tempfile.TemporaryDirectory() as temp_dir:
            if backup.storage_type == StorageType.REMOTE.value:
                # 从远程存储下载
                storage_client = get_storage_client()
                local_temp_path = os.path.join(temp_dir, backup.file_name or "backup.tar.gz")
                storage_client.download_file(
                    object_name=backup.storage_path,
                    local_path=local_temp_path
                )
                backup_file_path = local_temp_path
            else:
                # 本地存储
                backup_file_path = backup.storage_path
            
            # 解压恢复
            if os.path.exists(backup_file_path):
                import tarfile
                with tarfile.open(backup_file_path, "r:gz") as tar:
                    tar.extractall(path=os.path.dirname(source_path) or "/tmp")
            
            # 如果原数据路径存在但为空，创建data目录
            if not os.path.exists(source_path):
                os.makedirs(source_path, exist_ok=True)
        
        return True
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")


# ============== API接口 ==============

@router.get("/list", response_model=BackupListResponse, summary="获取备份列表")
async def list_backups(
    keyword: Optional[str] = Query(None, description="关键词搜索(名称)"),
    type: Optional[str] = Query(None, description="备份类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取备份记录列表
    
    支持分页、关键词搜索、类型和状态过滤
    """
    query = db.query(BackupRecord)
    
    # 关键词搜索
    if keyword:
        query = query.filter(BackupRecord.file_name.ilike(f"%{keyword}%"))
    
    # 类型过滤
    if type:
        query = query.filter(BackupRecord.backup_type == type)
    
    # 状态过滤
    if status:
        query = query.filter(BackupRecord.status == status)
    
    # 统计总数
    total = query.count()
    
    # 分页查询
    backups = query.order_by(desc(BackupRecord.created_at)).offset(pagination.offset).limit(pagination.limit).all()
    
    # 转换为响应格式
    items = []
    for backup in backups:
        items.append(BackupResponse(
            id=backup.id,
            name=backup.file_name or f"Backup-{backup.id}",
            backup_type=backup.backup_type,
            status=backup.status,
            file_name=backup.file_name,
            file_path=backup.file_path,
            file_size=backup.file_size,
            storage_type=backup.storage_type,
            storage_path=backup.storage_path,
            created_by=backup.created_by,
            started_at=backup.started_at,
            completed_at=backup.completed_at,
            duration_seconds=backup.duration_seconds,
            description=None,
            error_message=backup.error_message,
            created_at=backup.created_at,
        ))
    
    # 计算总页数
    total_pages = (total + pagination.page_size - 1) // pagination.page_size if total > 0 else 0
    
    return BackupListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=BackupStatsResponse, summary="获取备份统计")
async def get_backup_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取备份统计数据
    
    包括总数、总大小、各状态/类型数量、最近备份时间等
    """
    # 统计总数
    total_backups = db.query(func.count(BackupRecord.id)).scalar() or 0
    
    # 统计总大小
    total_size = db.query(func.sum(BackupRecord.file_size)).scalar() or 0
    
    # 按状态统计
    status_stats = db.query(
        BackupRecord.status,
        func.count(BackupRecord.id)
    ).group_by(BackupRecord.status).all()
    by_status = {status: count for status, count in status_stats}
    
    # 按类型统计
    type_stats = db.query(
        BackupRecord.backup_type,
        func.count(BackupRecord.id)
    ).group_by(BackupRecord.backup_type).all()
    by_type = {backup_type: count for backup_type, count in type_stats}
    
    # 最近备份时间
    last_backup = db.query(BackupRecord).order_by(desc(BackupRecord.created_at)).first()
    last_backup_time = last_backup.created_at if last_backup else None
    
    # 最近成功备份时间
    last_success = db.query(BackupRecord).filter(
        BackupRecord.status == BackupStatus.COMPLETED.value
    ).order_by(desc(BackupRecord.completed_at)).first()
    last_successful_backup = last_success.completed_at if last_success else None
    
    return BackupStatsResponse(
        total_backups=total_backups,
        total_size=total_size,
        by_status=by_status,
        by_type=by_type,
        last_backup_time=last_backup_time,
        last_successful_backup=last_successful_backup,
    )


@router.get("/{backup_id}", response_model=BackupResponse, summary="获取备份详情")
async def get_backup_detail(
    backup_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取单个备份记录的详细信息
    """
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")
    
    return BackupResponse(
        id=backup.id,
        name=backup.file_name or f"Backup-{backup.id}",
        backup_type=backup.backup_type,
        status=backup.status,
        file_name=backup.file_name,
        file_path=backup.file_path,
        file_size=backup.file_size,
        storage_type=backup.storage_type,
        storage_path=backup.storage_path,
        created_by=backup.created_by,
        started_at=backup.started_at,
        completed_at=backup.completed_at,
        duration_seconds=backup.duration_seconds,
        description=None,
        error_message=backup.error_message,
        created_at=backup.created_at,
    )


@router.post("/admin/backups", response_model=BackupResponse, summary="创建备份")
async def create_backup(
    request: BackupCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建新的备份任务
    
    支持全量备份、增量备份、配置备份
    备份操作在后台异步执行
    """
    # 创建备份记录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{request.name}_{timestamp}.tar.gz" if request.name else f"backup_{request.backup_type}_{timestamp}.tar.gz"
    
    backup = BackupRecord(
        backup_type=request.backup_type.value,
        file_name=file_name,
        status=BackupStatus.PENDING.value,
        storage_type=request.storage_type.value,
        created_by=current_user.username,
        started_at=None,
        completed_at=None,
    )
    
    db.add(backup)
    db.commit()
    db.refresh(backup)
    
    # 后台执行备份任务
    background_tasks.add_task(
        perform_backup,
        db=db,
        backup_id=backup.id,
        backup_type=request.backup_type.value,
        storage_type=request.storage_type.value,
        description=request.description,
    )
    
    return BackupResponse(
        id=backup.id,
        name=backup.file_name,
        backup_type=backup.backup_type,
        status=backup.status,
        file_name=backup.file_name,
        file_path=None,
        file_size=None,
        storage_type=backup.storage_type,
        storage_path=None,
        created_by=backup.created_by,
        started_at=backup.started_at,
        completed_at=backup.completed_at,
        duration_seconds=None,
        description=request.description,
        error_message=None,
        created_at=backup.created_at,
    )


@router.delete("/admin/backups/{backup_id}", summary="删除备份")
async def delete_backup(
    backup_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除指定的备份记录及关联的备份文件
    """
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")
    
    # 如果备份文件存在，尝试删除
    try:
        if backup.storage_type == StorageType.REMOTE.value:
            # 远程存储
            storage_client = get_storage_client()
            storage_client.delete(backup.storage_path)
        elif backup.storage_path and os.path.exists(backup.storage_path):
            # 本地存储
            os.remove(backup.storage_path)
    except Exception:
        # 删除文件失败不影响删除记录
        pass
    
    # 删除数据库记录
    db.delete(backup)
    db.commit()
    
    return {"message": "备份删除成功", "id": backup_id}


@router.post("/admin/backups/{backup_id}/restore", summary="恢复备份")
async def restore_backup(
    backup_id: int,
    request: RestoreRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    从备份恢复数据
    
    恢复操作会覆盖当前数据，执行前会自动创建预恢复备份
    需要确认操作
    """
    if not request.confirm:
        raise HTTPException(status_code=400, detail="需要确认恢复操作")
    
    backup = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="备份记录不存在")
    
    if backup.status != BackupStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail=f"备份状态不是已完成，无法恢复: {backup.status}")
    
    # 后台执行恢复任务
    background_tasks.add_task(
        perform_restore,
        db=db,
        backup_id=backup_id,
    )
    
    return {
        "message": "恢复任务已启动",
        "backup_id": backup_id,
        "backup_name": backup.file_name,
    }
