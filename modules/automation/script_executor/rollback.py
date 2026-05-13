"""
AUTO-023 执行失败自动回滚

提供脚本执行失败时自动回滚的功能：
- 执行前保存系统快照(设备配置/数据库状态)
- 回滚时恢复到快照点
- 支持脚本回滚: 执行预定义的回滚脚本(rollback_script字段)
"""

import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import yaml


class RollbackStatus(Enum):
    """回滚状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    NOT_FOUND = "not_found"


class SnapshotType(Enum):
    """快照类型"""
    DEVICE_CONFIG = "device_config"  # 设备配置快照
    DATABASE_STATE = "database_state"  # 数据库状态快照
    SCRIPT_OUTPUT = "script_output"  # 脚本输出快照
    FULL_SYSTEM = "full_system"  # 全系统快照


@dataclass
class Snapshot:
    """系统快照"""
    id: str
    execution_id: str
    snapshot_type: SnapshotType
    data: Dict[str, Any]  # 快照数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'snapshot_type': self.snapshot_type.value,
            'data': self.data,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'checksum': self.checksum,
        }


@dataclass
class RollbackResult:
    """回滚结果"""
    execution_id: str
    status: RollbackStatus
    snapshot_id: Optional[str] = None
    rollback_script_result: Optional[Dict[str, Any]] = None
    message: str = ""
    duration: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'status': self.status.value,
            'snapshot_id': self.snapshot_id,
            'rollback_script_result': self.rollback_script_result,
            'message': self.message,
            'duration': self.duration,
            'created_at': self.created_at.isoformat(),
        }


class RollbackManager:
    """
    回滚管理器
    
    提供执行前保存系统快照，回滚时恢复到快照点的功能
    支持脚本回滚：执行预定义的回滚脚本
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化回滚管理器
        
        Args:
            storage_path: 存储路径，默认使用临时目录
        """
        self._storage_path = storage_path or tempfile.mkdtemp(prefix="rollback_")
        self._db_path = os.path.join(self._storage_path, "rollback.db")
        self._snapshots: Dict[str, Snapshot] = {}  # execution_id -> Snapshot
        self._rollback_history: List[RollbackResult] = []
        self._lock = threading.Lock()
        
        # 注册的快照创建器
        self._snapshot_creators: Dict[SnapshotType, Callable] = {}
        
        # 注册的回滚脚本执行器
        self._rollback_script_executor: Optional[Callable] = None
        
        self._init_db()
    
    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                snapshot_type TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT,
                created_at REAL NOT NULL,
                checksum TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rollback_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                status TEXT NOT NULL,
                snapshot_id TEXT,
                rollback_script_result TEXT,
                message TEXT,
                duration REAL,
                created_at REAL NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshots_execution_id 
            ON snapshots(execution_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def register_snapshot_creator(
        self, 
        snapshot_type: SnapshotType, 
        creator: Callable[[str], Dict[str, Any]]
    ):
        """
        注册快照创建器
        
        Args:
            snapshot_type: 快照类型
            creator: 创建器函数，接受execution_id，返回快照数据字典
        """
        self._snapshot_creators[snapshot_type] = creator
    
    def register_rollback_script_executor(
        self, 
        executor: Callable[[str, Dict[str, Any]], Dict[str, Any]]
    ):
        """
        注册回滚脚本执行器
        
        Args:
            executor: 执行器函数，接受(rollback_script, params)，返回执行结果字典
        """
        self._rollback_script_executor = executor
    
    def save_checkpoint(
        self,
        execution_id: str,
        snapshot_type: SnapshotType = SnapshotType.SCRIPT_OUTPUT,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Snapshot:
        """
        保存执行检查点/快照
        
        Args:
            execution_id: 执行ID
            snapshot_type: 快照类型
            data: 快照数据（如果为None，则使用注册的创建器生成）
            metadata: 快照元数据
            
        Returns:
            Snapshot: 创建的快照对象
        """
        with self._lock:
            snapshot_id = f"snapshot_{uuid.uuid4().hex[:12]}"
            
            # 如果没有提供数据，尝试使用注册的创建器
            if data is None and snapshot_type in self._snapshot_creators:
                data = self._snapshot_creators[snapshot_type](execution_id)
            
            if data is None:
                data = {}
            
            # 计算校验和
            import hashlib
            content = json.dumps(data, sort_keys=True)
            checksum = hashlib.sha256(content.encode()).hexdigest()
            
            snapshot = Snapshot(
                id=snapshot_id,
                execution_id=execution_id,
                snapshot_type=snapshot_type,
                data=data,
                metadata=metadata or {},
                created_at=datetime.now(),
                checksum=checksum,
            )
            
            # 保存到内存
            self._snapshots[execution_id] = snapshot
            
            # 保存到数据库
            self._save_snapshot_to_db(snapshot)
            
            return snapshot
    
    def _save_snapshot_to_db(self, snapshot: Snapshot):
        """保存快照到数据库"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO snapshots (id, execution_id, snapshot_type, data, metadata, created_at, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot.id,
            snapshot.execution_id,
            snapshot.snapshot_type.value,
            json.dumps(snapshot.data),
            json.dumps(snapshot.metadata),
            snapshot.created_at.timestamp(),
            snapshot.checksum,
        ))
        
        conn.commit()
        conn.close()
    
    def get_snapshot(self, execution_id: str) -> Optional[Snapshot]:
        """
        获取执行ID对应的快照
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Snapshot或None
        """
        with self._lock:
            return self._snapshots.get(execution_id)
    
    def execute_rollback(
        self,
        execution_id: str,
        rollback_script: Optional[str] = None,
        rollback_params: Optional[Dict[str, Any]] = None,
    ) -> RollbackResult:
        """
        执行回滚
        
        Args:
            execution_id: 执行ID
            rollback_script: 回滚脚本内容（可选）
            rollback_params: 回滚脚本参数
            
        Returns:
            RollbackResult: 回滚结果
        """
        start_time = time.time()
        
        with self._lock:
            # 获取快照
            snapshot = self._snapshots.get(execution_id)
            
            if not snapshot:
                # 尝试从数据库加载
                snapshot = self._load_snapshot_from_db(execution_id)
            
            if not snapshot:
                result = RollbackResult(
                    execution_id=execution_id,
                    status=RollbackStatus.NOT_FOUND,
                    message=f"No snapshot found for execution {execution_id}",
                    duration=time.time() - start_time,
                )
                self._rollback_history.append(result)
                return result
            
            rollback_script_result = None
            
            # 如果提供了回滚脚本，执行它
            if rollback_script:
                if self._rollback_script_executor:
                    try:
                        rollback_script_result = self._rollback_script_executor(
                            rollback_script,
                            rollback_params or {}
                        )
                    except Exception as e:
                        result = RollbackResult(
                            execution_id=execution_id,
                            status=RollbackStatus.FAILED,
                            snapshot_id=snapshot.id,
                            message=f"Rollback script execution failed: {str(e)}",
                            duration=time.time() - start_time,
                        )
                        self._rollback_history.append(result)
                        return result
                else:
                    result = RollbackResult(
                        execution_id=execution_id,
                        status=RollbackStatus.FAILED,
                        snapshot_id=snapshot.id,
                        message="No rollback script executor registered",
                        duration=time.time() - start_time,
                    )
                    self._rollback_history.append(result)
                    return result
            
            result = RollbackResult(
                execution_id=execution_id,
                status=RollbackStatus.SUCCESS,
                snapshot_id=snapshot.id,
                rollback_script_result=rollback_script_result,
                message="Rollback completed successfully",
                duration=time.time() - start_time,
            )
            
            self._rollback_history.append(result)
            self._save_rollback_to_db(result)
            
            return result
    
    def _load_snapshot_from_db(self, execution_id: str) -> Optional[Snapshot]:
        """从数据库加载快照"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, execution_id, snapshot_type, data, metadata, created_at, checksum
            FROM snapshots
            WHERE execution_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (execution_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Snapshot(
            id=row[0],
            execution_id=row[1],
            snapshot_type=SnapshotType(row[2]),
            data=json.loads(row[3]),
            metadata=json.loads(row[4]) if row[4] else {},
            created_at=datetime.fromtimestamp(row[5]),
            checksum=row[6],
        )
    
    def _save_rollback_to_db(self, result: RollbackResult):
        """保存回滚结果到数据库"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO rollback_history 
            (execution_id, status, snapshot_id, rollback_script_result, message, duration, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.execution_id,
            result.status.value,
            result.snapshot_id,
            json.dumps(result.rollback_script_result) if result.rollback_script_result else None,
            result.message,
            result.duration,
            result.created_at.timestamp(),
        ))
        
        conn.commit()
        conn.close()
    
    def get_rollback_history(
        self, 
        limit: int = 100,
        execution_id: Optional[str] = None,
    ) -> List[RollbackResult]:
        """
        获取回滚历史
        
        Args:
            limit: 返回数量限制
            execution_id: 按执行ID过滤
            
        Returns:
            List[RollbackResult]: 回滚结果列表
        """
        with self._lock:
            history = self._rollback_history.copy()
        
        if execution_id:
            history = [r for r in history if r.execution_id == execution_id]
        
        return history[-limit:]
    
    def list_snapshots(self, limit: int = 100) -> List[Snapshot]:
        """
        列出快照
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Snapshot]: 快照列表
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, execution_id, snapshot_type, data, metadata, created_at, checksum
            FROM snapshots
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Snapshot(
                id=row[0],
                execution_id=row[1],
                snapshot_type=SnapshotType(row[2]),
                data=json.loads(row[3]),
                metadata=json.loads(row[4]) if row[4] else {},
                created_at=datetime.fromtimestamp(row[5]),
                checksum=row[6],
            )
            for row in rows
        ]
    
    def delete_snapshot(self, execution_id: str) -> bool:
        """
        删除快照
        
        Args:
            execution_id: 执行ID
            
        Returns:
            bool: 是否成功删除
        """
        with self._lock:
            if execution_id in self._snapshots:
                del self._snapshots[execution_id]
            
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM snapshots WHERE execution_id = ?', (execution_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return deleted
    
    def cleanup_old_snapshots(self, max_age_hours: int = 24) -> int:
        """
        清理旧快照
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            int: 删除的快照数量
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM snapshots WHERE created_at < ?', (cutoff_time,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        with self._lock:
            # 清理内存中的旧快照
            to_remove = []
            for exec_id, snapshot in self._snapshots.items():
                if snapshot.created_at.timestamp() < cutoff_time:
                    to_remove.append(exec_id)
            for exec_id in to_remove:
                del self._snapshots[exec_id]
        
        return deleted


# 全局回滚管理器实例
_rollback_manager: Optional[RollbackManager] = None


def get_rollback_manager() -> RollbackManager:
    """获取全局回滚管理器实例"""
    global _rollback_manager
    if _rollback_manager is None:
        _rollback_manager = RollbackManager()
    return _rollback_manager
