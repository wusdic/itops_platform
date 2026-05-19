"""
平台层备份恢复管理模块
BM-08 系统管理
提供数据库、配置、文件的备份和恢复功能
"""

import logging
import os
import json
import shutil
import hashlib
import tarfile
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import subprocess

logger = logging.getLogger(__name__)


class BackupType(str, Enum):
    """备份类型枚举"""
    FULL = 'full'           # 全量备份
    INCREMENTAL = 'incremental'  # 增量备份
    DIFFERENTIAL = 'differential'  # 差异备份


class BackupTarget(str, Enum):
    """备份目标枚举"""
    DATABASE = 'database'   # 数据库
    CONFIG = 'config'       # 配置文件
    FILES = 'files'         # 文件
    ALL = 'all'            # 全部


class BackupStatus(str, Enum):
    """备份状态枚举"""
    PENDING = 'pending'     # 待执行
    RUNNING = 'running'     # 执行中
    SUCCESS = 'success'     # 成功
    FAILED = 'failed'       # 失败
    CANCELLED = 'cancelled' # 已取消


class RestoreStatus(str, Enum):
    """恢复状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'


@dataclass
class BackupConfig:
    """备份配置"""
    # 备份存储路径（支持环境变量覆盖）
    backup_dir: str = os.getenv('ITOPS_BACKUP_DIR', '/data/backup')
    
    # 保留策略
    retention_days: int = 30  # 保留天数
    max_backups: int = 10  # 最大备份数量
    
    # 压缩设置
    compression_enabled: bool = True
    compression_level: int = 9  # 压缩级别 0-9
    
    # 加密设置
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    
    # 数据库备份设置
    db_backup_enabled: bool = True
    db_backup_tables: List[str] = field(default_factory=list)  # 空表示全部表
    
    # 文件备份设置
    file_backup_enabled: bool = True
    file_backup_paths: List[str] = field(default_factory=list)
    file_exclude_patterns: List[str] = field(default_factory=lambda: ['*.pyc', '__pycache__', '.git', '*.log'])
    
    # 调度设置
    auto_backup_enabled: bool = True
    backup_schedule: str = '0 2 * * *'  # 默认每天凌晨2点
    incremental_interval_hours: int = 6  # 增量备份间隔
    
    # 通知设置
    notify_on_success: bool = True
    notify_on_failure: bool = True


@dataclass
class BackupRecord:
    """备份记录"""
    id: str
    name: str
    backup_type: BackupType
    status: BackupStatus
    
    # 文件信息
    file_path: Optional[str] = None
    file_size: int = 0
    file_md5: Optional[str] = None
    
    # 备份信息
    targets: List[BackupTarget] = field(default_factory=list)
    included_items: List[str] = field(default_factory=list)  # 包含的具体项
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: int = 0
    
    # 统计信息
    total_size: int = 0  # 备份总大小
    db_records: int = 0  # 数据库记录数
    file_count: int = 0  # 文件数
    
    # 关联信息
    previous_backup_id: Optional[str] = None  # 用于增量/差异备份
    next_backup_id: Optional[str] = None  # 下一个增量/差异备份
    
    # 错误信息
    error_message: Optional[str] = None
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'backup_type': self.backup_type.value if isinstance(self.backup_type, BackupType) else self.backup_type,
            'status': self.status.value if isinstance(self.status, BackupStatus) else self.status,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_md5': self.file_md5,
            'targets': [t.value if isinstance(t, BackupTarget) else t for t in self.targets],
            'included_items': self.included_items,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'total_size': self.total_size,
            'db_records': self.db_records,
            'file_count': self.file_count,
            'previous_backup_id': self.previous_backup_id,
            'next_backup_id': self.next_backup_id,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.metadata,
        }


@dataclass
class RestoreRecord:
    """恢复记录"""
    id: str
    backup_id: str
    status: RestoreStatus
    
    # 恢复目标
    target: BackupTarget = BackupTarget.ALL
    target_path: Optional[str] = None
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: int = 0
    
    # 恢复前备份ID（恢复前自动备份）
    pre_restore_backup_id: Optional[str] = None
    
    # 错误信息
    error_message: Optional[str] = None
    
    # 恢复详情
    restored_items: List[str] = field(default_factory=list)
    skipped_items: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'backup_id': self.backup_id,
            'status': self.status.value if isinstance(self.status, RestoreStatus) else self.status,
            'target': self.target.value if isinstance(self.target, BackupTarget) else self.target,
            'target_path': self.target_path,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'pre_restore_backup_id': self.pre_restore_backup_id,
            'error_message': self.error_message,
            'restored_items': self.restored_items,
            'skipped_items': self.skipped_items,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class BackupManager:
    """
    备份恢复管理器
    """
    
    def __init__(self, config: Optional[BackupConfig] = None):
        self.config = config or BackupConfig()
        self._backups: Dict[str, BackupRecord] = {}
        self._restores: Dict[str, RestoreRecord] = {}
        
        # 确保备份目录存在
        os.makedirs(self.config.backup_dir, exist_ok=True)
        
        # 回调函数
        self._progress_callbacks: List[Callable] = []
        self._completion_callbacks: List[Callable] = []
        
        logger.info(f'BackupManager initialized with backup_dir={self.config.backup_dir}')
    
    def register_progress_callback(self, callback: Callable):
        """注册进度回调"""
        self._progress_callbacks.append(callback)
    
    def register_completion_callback(self, callback: Callable):
        """注册完成回调"""
        self._completion_callbacks.append(callback)
    
    def _trigger_progress(self, backup_id: str, progress: float, message: str):
        """触发进度回调"""
        for callback in self._progress_callbacks:
            try:
                callback(backup_id, progress, message)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def _trigger_completion(self, backup_id: str, status: BackupStatus):
        """触发完成回调"""
        for callback in self._completion_callbacks:
            try:
                callback(backup_id, status)
            except Exception as e:
                logger.error(f"Completion callback error: {e}")
    
    def _calculate_file_md5(self, file_path: str) -> Optional[str]:
        """计算文件MD5"""
        try:
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"MD5 calculation failed: {e}")
            return None
    
    def _create_backup_name(self, backup_type: BackupType) -> str:
        """生成备份文件名"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        type_str = backup_type.value if isinstance(backup_type, BackupType) else backup_type
        return f"backup_{type_str}_{timestamp}"
    
    def _get_backup_path(self, name: str) -> str:
        """获取备份文件完整路径"""
        if self.config.compression_enabled:
            return os.path.join(self.config.backup_dir, f"{name}.tar.gz")
        return os.path.join(self.config.backup_dir, f"{name}.tar")
    
    async def create_backup(
        self,
        name: str,
        backup_type: BackupType = BackupType.FULL,
        targets: List[BackupTarget] = None,
        description: str = ''
    ) -> BackupRecord:
        """
        创建备份
        
        Args:
            name: 备份名称
            backup_type: 备份类型
            targets: 备份目标列表
            description: 备份描述
        
        Returns:
            备份记录
        """
        import uuid
        
        if targets is None:
            targets = [BackupTarget.ALL]
        
        record = BackupRecord(
            id=str(uuid.uuid4()),
            name=name,
            backup_type=backup_type,
            status=BackupStatus.RUNNING,
            targets=targets,
        )
        
        self._backups[record.id] = record
        
        try:
            backup_name = self._create_backup_name(backup_type)
            backup_path = self._get_backup_path(backup_name)
            
            record.metadata['description'] = description
            record.metadata['backup_name'] = backup_name
            
            self._trigger_progress(record.id, 0.0, '开始备份...')
            
            # 创建临时目录
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix='backup_')
            
            try:
                total_size = 0
                included_items = []
                file_count = 0
                db_records = 0
                
                # 备份数据库
                if BackupTarget.DATABASE in targets or BackupTarget.ALL in targets:
                    self._trigger_progress(record.id, 0.1, '备份数据库...')
                    db_path = await self._backup_database(temp_dir)
                    if db_path and os.path.exists(db_path):
                        total_size += os.path.getsize(db_path)
                        included_items.append(f"database:{db_path}")
                        file_count += 1
                        # 尝试获取记录数
                        try:
                            import sqlite3
                            conn = sqlite3.connect(db_path)
                            cursor = conn.execute("SELECT SUM(cnt) FROM (SELECT COUNT(*) as cnt FROM alerts UNION ALL SELECT COUNT(*) FROM devices UNION ALL SELECT COUNT(*) FROM work_orders)")
                            db_records = cursor.fetchone()[0] or 0
                            conn.close()
                        except:
                            pass
                
                # 备份配置文件
                if BackupTarget.CONFIG in targets or BackupTarget.ALL in targets:
                    self._trigger_progress(record.id, 0.4, '备份配置文件...')
                    config_path = await self._backup_config(temp_dir)
                    if config_path and os.path.exists(config_path):
                        total_size += os.path.getsize(config_path)
                        included_items.append(f"config:{config_path}")
                        file_count += 1
                
                # 备份文件
                if BackupTarget.FILES in targets or BackupTarget.ALL in targets:
                    self._trigger_progress(record.id, 0.6, '备份文件...')
                    files_path = await self._backup_files(temp_dir)
                    if files_path and os.path.exists(files_path):
                        total_size += os.path.getsize(files_path)
                        included_items.append(f"files:{files_path}")
                        file_count += 1
                
                self._trigger_progress(record.id, 0.8, '打包备份文件...')
                
                # 创建压缩包
                await self._create_archive(temp_dir, backup_path)
                
                # 计算MD5
                file_md5 = self._calculate_file_md5(backup_path)
                file_size = os.path.getsize(backup_path)
                
                # 更新记录
                record.file_path = backup_path
                record.file_size = file_size
                record.file_md5 = file_md5
                record.total_size = total_size
                record.db_records = db_records
                record.file_count = file_count
                record.included_items = included_items
                record.status = BackupStatus.SUCCESS
                record.completed_at = datetime.now()
                record.duration_seconds = int((record.completed_at - record.started_at).total_seconds())
                
                self._trigger_progress(record.id, 1.0, '备份完成')
                self._trigger_completion(record.id, BackupStatus.SUCCESS)
                
                logger.info(f"Backup completed: {record.id}, size={file_size}")
            
            finally:
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        except Exception as e:
            record.status = BackupStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now()
            record.duration_seconds = int((record.completed_at - record.started_at).total_seconds())
            self._trigger_completion(record.id, BackupStatus.FAILED)
            logger.error(f"Backup failed: {e}")
        
        return record
    
    async def _backup_database(self, temp_dir: str) -> Optional[str]:
        """备份数据库"""
        try:
            from modules.foundation.db_models.base import engine
            
            db_path = os.path.join(temp_dir, 'database.db')
            
            # 使用SQLite直接复制
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from modules.foundation.db_models.base import Base
            
            # 获取数据库URL
            db_url = str(engine.url)
            
            if 'sqlite' in db_url:
                # SQLite直接复制
                sqlite_path = db_url.replace('sqlite:///', '')
                if os.path.exists(sqlite_path):
                    shutil.copy2(sqlite_path, db_path)
                    return db_path
            else:
                # 其他数据库使用SQLite临时存储
                # 这是一个简化实现，实际应该分表导出
                source_engine = create_engine(db_url)
                
                # 创建临时SQLite
                temp_engine = create_engine(f'sqlite:///{db_path}')
                Base.metadata.create_all(temp_engine)
                
                # 复制数据
                source_session = sessionmaker(bind=source_engine)()
                temp_session = sessionmaker(bind=temp_engine)()
                
                for table in Base.metadata.sorted_tables:
                    try:
                        source_session.execute(f"DROP TABLE IF EXISTS {table.name}")
                        source_session.execute(f"CREATE TABLE {table.name} AS SELECT * FROM {table.name}")
                        rows = source_session.execute(f"SELECT * FROM {table.name}").fetchall()
                        temp_session.bulk_insert_mappings(table, [dict(zip(table.columns.keys(), row)) for row in rows])
                    except Exception as e:
                        logger.warning(f"Table {table.name} backup skipped: {e}")
                
                source_session.close()
                temp_session.close()
                temp_engine.dispose()
                source_engine.dispose()
                
                return db_path
        
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return None
    
    async def _backup_config(self, temp_dir: str) -> Optional[str]:
        """备份配置文件"""
        try:
            config_data = {}
            
            # 收集配置目录
            config_paths = [
                '/home/zcxx/.hermes/projects/itops_platform/config',
                '/home/zcxx/.hermes/projects/itops_platform/settings',
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if file.endswith(('.json', '.yaml', '.yml', '.ini', '.conf')):
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, '/home/zcxx/.hermes/projects/itops_platform')
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        config_data[rel_path] = f.read()
                                except:
                                    pass
            
            config_path = os.path.join(temp_dir, 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            return config_path
        
        except Exception as e:
            logger.error(f"Config backup failed: {e}")
            return None
    
    async def _backup_files(self, temp_dir: str) -> Optional[str]:
        """备份文件"""
        try:
            files_dir = os.path.join(temp_dir, 'files')
            os.makedirs(files_dir, exist_ok=True)
            
            # 备份目录列表
            backup_paths = self.config.file_backup_paths or [
                '/home/zcxx/.hermes/projects/itops_platform/docs',
                '/home/zcxx/.hermes/projects/itops_platform/reports',
            ]
            
            # 排除模式
            exclude_patterns = set(self.config.file_exclude_patterns)
            
            for base_path in backup_paths:
                if not os.path.exists(base_path):
                    continue
                
                rel_base = os.path.relpath(base_path, '/home/zcxx/.hermes/projects/itops_platform')
                dest_dir = os.path.join(files_dir, rel_base)
                os.makedirs(dest_dir, exist_ok=True)
                
                for root, dirs, files in os.walk(base_path):
                    # 排除目录
                    dirs[:] = [d for d in dirs if d not in exclude_patterns and not any(
                        d.endswith(pat.replace('*', '')) for pat in exclude_patterns if '*' in pat
                    )]
                    
                    for file in files:
                        # 排除文件
                        if any(file.endswith(pat.replace('*', '')) for pat in exclude_patterns if '*' in pat):
                            continue
                        
                        src_file = os.path.join(root, file)
                        rel_file = os.path.relpath(src_file, base_path)
                        dest_file = os.path.join(dest_dir, rel_file)
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        shutil.copy2(src_file, dest_file)
            
            return files_dir
        
        except Exception as e:
            logger.error(f"Files backup failed: {e}")
            return None
    
    async def _create_archive(self, source_dir: str, dest_path: str):
        """创建压缩包"""
        if self.config.compression_enabled:
            with tarfile.open(dest_path, 'w:gz', compresslevel=self.config.compression_level) as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
        else:
            with tarfile.open(dest_path, 'w') as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
    
    async def restore(
        self,
        backup_id: str,
        target: BackupTarget = BackupTarget.ALL,
        target_path: Optional[str] = None,
        create_pre_backup: bool = True
    ) -> RestoreRecord:
        """
        恢复备份
        
        Args:
            backup_id: 备份ID
            target: 恢复目标
            target_path: 恢复路径
            create_pre_backup: 恢复前是否创建备份
        
        Returns:
            恢复记录
        """
        import uuid
        
        backup = self._backups.get(backup_id)
        if not backup:
            raise ValueError(f"Backup {backup_id} not found")
        
        record = RestoreRecord(
            id=str(uuid.uuid4()),
            backup_id=backup_id,
            status=RestoreStatus.RUNNING,
            target=target,
            target_path=target_path,
        )
        
        self._restores[record.id] = record
        
        try:
            # 恢复前备份
            if create_pre_backup:
                pre_backup = await self.create_backup(
                    name=f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    backup_type=BackupType.FULL,
                    targets=[target],
                    description=f"恢复前自动备份"
                )
                record.pre_restore_backup_id = pre_backup.id
            
            # 解压备份文件
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix='restore_')
            
            try:
                if backup.file_path and os.path.exists(backup.file_path):
                    await self._extract_archive(backup.file_path, temp_dir)
                    
                    # 恢复各个目标
                    if target == BackupTarget.DATABASE or target == BackupTarget.ALL:
                        await self._restore_database(temp_dir)
                        record.restored_items.append('database')
                    
                    if target == BackupTarget.CONFIG or target == BackupTarget.ALL:
                        await self._restore_config(temp_dir)
                        record.restored_items.append('config')
                    
                    if target == BackupTarget.FILES or target == BackupTarget.ALL:
                        await self._restore_files(temp_dir)
                        record.restored_items.append('files')
                
                record.status = RestoreStatus.SUCCESS
                record.completed_at = datetime.now()
                record.duration_seconds = int((record.completed_at - record.started_at).total_seconds())
                
                logger.info(f"Restore completed: {record.id}")
            
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        except Exception as e:
            record.status = RestoreStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now()
            record.duration_seconds = int((record.completed_at - record.started_at).total_seconds())
            logger.error(f"Restore failed: {e}")
        
        return record
    
    async def _extract_archive(self, archive_path: str, dest_dir: str):
        """解压备份文件"""
        with tarfile.open(archive_path, 'r:*') as tar:
            tar.extractall(dest_dir)
    
    async def _restore_database(self, temp_dir: str):
        """恢复数据库"""
        db_path = os.path.join(temp_dir, 'database.db')
        if not os.path.exists(db_path):
            logger.warning("Database backup not found in archive")
            return
        
        from sqlalchemy import create_engine
        from modules.foundation.db_models.base import engine
        
        db_url = str(engine.url)
        
        if 'sqlite' in db_url:
            sqlite_path = db_url.replace('sqlite:///', '')
            shutil.copy2(db_path, sqlite_path)
            logger.info(f"Database restored to {sqlite_path}")
    
    async def _restore_config(self, temp_dir: str):
        """恢复配置文件"""
        config_path = os.path.join(temp_dir, 'config.json')
        if not os.path.exists(config_path):
            logger.warning("Config backup not found in archive")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        for rel_path, content in config_data.items():
            file_path = os.path.join('/home/zcxx/.hermes/projects/itops_platform', rel_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        logger.info(f"Config restored: {len(config_data)} files")
    
    async def _restore_files(self, temp_dir: str):
        """恢复文件"""
        files_dir = os.path.join(temp_dir, 'files')
        if not os.path.exists(files_dir):
            logger.warning("Files backup not found in archive")
            return
        
        base_dir = '/home/zcxx/.hermes/projects/itops_platform'
        
        for root, dirs, files in os.walk(files_dir):
            for file in files:
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, files_dir)
                dest_file = os.path.join(base_dir, rel_path)
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.copy2(src_file, dest_file)
        
        logger.info(f"Files restored from {files_dir}")
    
    def get_backup(self, backup_id: str) -> Optional[BackupRecord]:
        """获取备份记录"""
        return self._backups.get(backup_id)
    
    def list_backups(
        self,
        status: Optional[BackupStatus] = None,
        backup_type: Optional[BackupType] = None,
        limit: int = 100
    ) -> List[BackupRecord]:
        """列出备份记录"""
        backups = list(self._backups.values())
        
        if status:
            backups = [b for b in backups if b.status == status]
        
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        
        # 按时间倒序
        backups.sort(key=lambda b: b.started_at, reverse=True)
        
        return backups[:limit]
    
    def get_restore(self, restore_id: str) -> Optional[RestoreRecord]:
        """获取恢复记录"""
        return self._restores.get(restore_id)
    
    def list_restores(self, limit: int = 100) -> List[RestoreRecord]:
        """列出恢复记录"""
        restores = list(self._restores.values())
        restores.sort(key=lambda r: r.started_at, reverse=True)
        return restores[:limit]
    
    def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        backup = self._backups.get(backup_id)
        if not backup:
            return False
        
        # 删除备份文件
        if backup.file_path and os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
            except Exception as e:
                logger.error(f"Failed to delete backup file: {e}")
        
        # 删除记录
        del self._backups[backup_id]
        return True
    
    def cleanup_old_backups(self) -> int:
        """清理过期备份"""
        cutoff = datetime.now() - timedelta(days=self.config.retention_days)
        to_remove = [
            bid for bid, backup in self._backups.items()
            if backup.created_at < cutoff
        ]
        
        for bid in to_remove:
            self.delete_backup(bid)
        
        # 超过最大数量限制
        backups = self.list_backups()
        if len(backups) > self.config.max_backups:
            for backup in backups[self.config.max_backups:]:
                self.delete_backup(backup.id)
        
        logger.info(f"Cleaned up {len(to_remove)} old backups")
        return len(to_remove)


# 全局实例
_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    """获取备份管理器单例"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager


def init_backup_manager(config: Optional[BackupConfig] = None) -> BackupManager:
    """初始化备份管理器"""
    global _backup_manager
    _backup_manager = BackupManager(config)
    return _backup_manager
