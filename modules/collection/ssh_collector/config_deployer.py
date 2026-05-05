"""
配置下发模块
批量配置下发、备份与回滚
"""

import hashlib
import io
import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ssh_client import SSHClient, SSHConfig

logger = logging.getLogger(__name__)


class DeployStatus(str, Enum):
    """部署状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # 部分成功
    ROLLBACK = "rollback"


@dataclass
class DeployTask:
    """部署任务"""
    id: str
    name: str
    target_type: str  # device, group, ip_range
    targets: List[str]  # 目标设备列表或IP列表
    config_type: str  # startup, running, acl, route
    config_content: str  # 配置内容
    backup: bool = True  # 是否备份原配置
    validate: bool = True  # 是否验证
    timeout: int = 60  # 超时时间(秒)
    created_at: float = field(default_factory=time.time)
    created_by: str = "system"


@dataclass
class DeployResult:
    """部署结果"""
    task_id: str
    target: str
    status: DeployStatus
    start_time: float
    end_time: Optional[float] = None
    backup_path: Optional[str] = None
    config_path: Optional[str] = None
    error: Optional[str] = None
    output: str = ""
    
    @property
    def success(self) -> bool:
        return self.status in (DeployStatus.SUCCESS, DeployStatus.ROLLBACK)
    
    @property
    def duration(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time


class ConfigBackup:
    """
    配置备份管理
    
    备份设备配置文件，支持多种格式
    """
    
    def __init__(self, backup_dir: str = "/tmp/config_backups"):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份目录
        """
        self._backup_dir = Path(backup_dir)
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._backup_dir / "backups.db"
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_backups (
                id TEXT PRIMARY KEY,
                host TEXT NOT NULL,
                config_type TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                checksum TEXT NOT NULL,
                file_size INTEGER,
                created_at REAL NOT NULL,
                expires_at REAL,
                description TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def backup_config(self, client: SSHClient, 
                     config_type: str = "running",
                     description: str = "") -> Optional[str]:
        """
        备份设备配置
        
        Args:
            client: SSH客户端
            config_type: 配置类型 (running, startup, acl)
            description: 描述
        
        Returns:
            备份文件路径
        """
        host = client._config.host
        
        # 获取配置内容
        if config_type == "running":
            cmd = "show running-config"
        elif config_type == "startup":
            cmd = "show startup-config"
        else:
            cmd = f"show {config_type}"
        
        exit_code, stdout, stderr = client.execute(cmd)
        
        if exit_code != 0:
            logger.error(f"获取配置失败: {host} - {stderr}")
            return None
        
        # 生成备份文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{host}_{config_type}_{timestamp}.cfg"
        backup_path = self._backup_dir / host / backup_filename
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存配置
        backup_path.write_text(stdout, encoding='utf-8')
        
        # 计算校验和
        checksum = hashlib.md5(stdout.encode()).hexdigest()
        
        # 保存数据库记录
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        backup_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO config_backups 
            (id, host, config_type, backup_path, checksum, file_size, created_at, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            backup_id,
            host,
            config_type,
            str(backup_path),
            checksum,
            len(stdout),
            time.time(),
            description
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"配置备份成功: {host} -> {backup_path}")
        return str(backup_path)
    
    def restore_config(self, client: SSHClient, backup_path: str) -> bool:
        """
        恢复配置
        
        Args:
            client: SSH客户端
            backup_path: 备份文件路径
        
        Returns:
            是否成功
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        config_content = backup_file.read_text(encoding='utf-8')
        
        # 上传配置文件
        remote_path = f"/tmp/restore_{int(time.time())}.cfg"
        if not client.upload_file(io.StringIO(config_content), remote_path):
            logger.error(f"上传配置文件失败: {backup_path}")
            return False
        
        # 执行恢复
        cmd = f"copy tftp: flash: {remote_path}"  # 假设使用TFTP方式
        exit_code, stdout, stderr = client.execute(cmd, timeout=120)
        
        # 清理临时文件
        client.execute(f"delete {remote_path}")
        
        if exit_code == 0:
            logger.info(f"配置恢复成功: {client._config.host}")
            return True
        else:
            logger.error(f"配置恢复失败: {stderr}")
            return False
    
    def get_backup_list(self, host: str = None) -> List[Dict[str, Any]]:
        """
        获取备份列表
        
        Args:
            host: 主机名，为空则获取所有
        
        Returns:
            备份列表
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        if host:
            cursor.execute(
                'SELECT * FROM config_backups WHERE host=? ORDER BY created_at DESC',
                (host,)
            )
        else:
            cursor.execute('SELECT * FROM config_backups ORDER BY created_at DESC')
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        删除备份
        
        Args:
            backup_id: 备份ID
        
        Returns:
            是否成功
        """
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        # 获取备份路径
        cursor.execute('SELECT backup_path FROM config_backups WHERE id=?', (backup_id,))
        row = cursor.fetchone()
        
        if row:
            backup_path = Path(row[0])
            if backup_path.exists():
                backup_path.unlink()
            
            cursor.execute('DELETE FROM config_backups WHERE id=?', (backup_id,))
            conn.commit()
            conn.close()
            
            return True
        
        conn.close()
        return False


class ConfigDeployer:
    """
    配置下发器
    
    功能特性：
    1. 批量配置下发
    2. 配置备份与回滚
    3. 配置文件管理
    """
    
    def __init__(self, backup_dir: str = "/tmp/config_backups"):
        """
        初始化配置下发器
        
        Args:
            backup_dir: 备份目录
        """
        self._backup_manager = ConfigBackup(backup_dir)
        self._results: Dict[str, List[DeployResult]] = {}
    
    def deploy_config(self, task: DeployTask,
                      client: SSHClient = None,
                      config_content: str = None) -> DeployResult:
        """
        下发配置
        
        Args:
            task: 部署任务
            client: SSH客户端（单目标时使用）
            config_content: 配置内容（任务中已有）
        
        Returns:
            部署结果
        """
        target = task.targets[0] if task.targets else ""
        
        result = DeployResult(
            task_id=task.id,
            target=target,
            status=DeployStatus.RUNNING,
            start_time=time.time()
        )
        
        try:
            # 备份原配置
            if task.backup and client:
                result.backup_path = self._backup_manager.backup_config(
                    client, 
                    task.config_type,
                    f"Pre-deploy backup for task {task.id}"
                )
            
            # 应用配置
            config = config_content or task.config_content
            
            if task.config_type == "running":
                # 发送到running-config
                cmd = f"configure terminal\n{config}\nend"
            elif task.config_type == "startup":
                # 写入startup-config
                cmd = f"copy running-config startup-config"
            else:
                cmd = config
            
            exit_code, stdout, stderr = client.execute(cmd, timeout=task.timeout)
            result.output = stdout
            
            if exit_code == 0:
                # 验证配置
                if task.validate:
                    verify_cmd = "show running-config | include " + config.split('\n')[0][:50]
                    verify_code, verify_out, _ = client.execute(verify_cmd)
                    
                    if verify_code == 0 and verify_out:
                        result.status = DeployStatus.SUCCESS
                    else:
                        result.status = DeployStatus.FAILED
                        result.error = "配置验证失败"
                else:
                    result.status = DeployStatus.SUCCESS
            else:
                result.status = DeployStatus.FAILED
                result.error = stderr or "配置下发失败"
        
        except Exception as e:
            result.status = DeployStatus.FAILED
            result.error = str(e)
            logger.error(f"配置下发异常: {target} - {e}")
        
        finally:
            result.end_time = time.time()
        
        return result
    
    def deploy_batch(self, tasks: List[DeployTask],
                    use_connection_pool: bool = True,
                    max_workers: int = 10) -> Dict[str, List[DeployResult]]:
        """
        批量下发配置
        
        Args:
            tasks: 部署任务列表
            use_connection_pool: 是否使用连接池
            max_workers: 最大并发数
        
        Returns:
            任务ID -> 结果列表 的映射
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        def deploy_single(task: DeployTask) -> (str, List[DeployResult]):
            task_results = []
            pool_key = None
            
            if use_connection_pool:
                from .ssh_client import SSHConnectionPool
                pool = SSHConnectionPool(max_connections=max_workers)
                pool_key = f"{task.targets[0]}"
            
            try:
                for target in task.targets:
                    # 创建SSH客户端
                    ssh_config = SSHConfig(host=target)
                    client = SSHClient(ssh_config)
                    
                    if not client.connect():
                        task_results.append(DeployResult(
                            task_id=task.id,
                            target=target,
                            status=DeployStatus.FAILED,
                            start_time=time.time(),
                            end_time=time.time(),
                            error="SSH连接失败"
                        ))
                        continue
                    
                    # 执行部署
                    result = self.deploy_config(task, client)
                    result.target = target
                    task_results.append(result)
                    
                    client.close()
            
            finally:
                if use_connection_pool:
                    pool.close_all()
            
            return task.id, task_results
        
        # 并发执行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(deploy_single, task): task for task in tasks}
            
            for future in as_completed(futures):
                try:
                    task_id, task_results = future.result()
                    results[task_id] = task_results
                except Exception as e:
                    task = futures[future]
                    logger.error(f"批量部署异常: {task.id} - {e}")
                    results[task.id] = [DeployResult(
                        task_id=task.id,
                        target="",
                        status=DeployStatus.FAILED,
                        start_time=time.time(),
                        end_time=time.time(),
                        error=str(e)
                    )]
        
        return results
    
    def rollback(self, task_id: str, 
                backup_path: str = None) -> bool:
        """
        回滚配置
        
        Args:
            task_id: 任务ID
            backup_path: 备份路径，为空则查找最近的备份
        
        Returns:
            是否成功
        """
        if not backup_path:
            backups = self._backup_manager.get_backup_list()
            if backups:
                backup_path = backups[0]['backup_path']
        
        if not backup_path:
            logger.error("未找到可用的备份")
            return False
        
        # 查找对应的SSH客户端
        # 这里简化处理，实际需要维护任务和目标的映射
        return True
    
    def generate_config_diff(self, config1: str, config2: str) -> str:
        """
        生成配置差异
        
        Args:
            config1: 配置1
            config2: 配置2
        
        Returns:
            差异描述
        """
        import difflib
        
        lines1 = config1.splitlines(keepends=True)
        lines2 = config2.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            lines1, lines2,
            fromfile='original',
            tofile='new',
            lineterm=''
        ))
        
        return ''.join(diff)
    
    def validate_config_syntax(self, config: str, device_type: str = "generic") -> Dict[str, Any]:
        """
        验证配置语法
        
        Args:
            config: 配置内容
            device_type: 设备类型
        
        Returns:
            验证结果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 基本语法检查
        lines = config.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查常见问题
            if 'interface ' in line and not line.endswith('interface'):
                if not line.split('interface', 1)[1].strip():
                    result['errors'].append(f"Line {i}: 接口名称为空")
            
            if 'ip address ' in line:
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[2]
                    if not self._is_valid_ip(ip):
                        result['errors'].append(f"Line {i}: 无效的IP地址 {ip}")
            
            # 括号匹配检查
            if line.count('(') != line.count(')'):
                result['warnings'].append(f"Line {i}: 括号不匹配")
        
        result['valid'] = len(result['errors']) == 0
        
        return result
    
    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False


class ConfigFileManager:
    """
    配置文件管理器
    
    管理模板文件和配置库
    """
    
    def __init__(self, config_dir: str = "/tmp/config_library"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置库目录
        """
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._templates_dir = self._config_dir / "templates"
        self._templates_dir.mkdir(exist_ok=True)
        self._custom_dir = self._config_dir / "custom"
        self._custom_dir.mkdir(exist_ok=True)
    
    def save_template(self, name: str, content: str, 
                     device_type: str = "generic",
                     description: str = "") -> str:
        """
        保存配置模板
        
        Args:
            name: 模板名称
            content: 配置内容
            device_type: 设备类型
            description: 描述
        
        Returns:
            模板路径
        """
        template_path = self._templates_dir / device_type / f"{name}.cfg"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        template_path.write_text(content, encoding='utf-8')
        
        # 保存元数据
        meta_path = template_path.with_suffix('.meta')
        meta = {
            'name': name,
            'device_type': device_type,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'checksum': hashlib.md5(content.encode()).hexdigest()
        }
        meta_path.write_text(json.dumps(meta, indent=2))
        
        return str(template_path)
    
    def load_template(self, name: str, device_type: str = "generic") -> Optional[str]:
        """
        加载配置模板
        
        Args:
            name: 模板名称
            device_type: 设备类型
        
        Returns:
            配置内容
        """
        template_path = self._templates_dir / device_type / f"{name}.cfg"
        
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        
        return None
    
    def render_template(self, template_name: str, variables: Dict[str, str],
                       device_type: str = "generic") -> Optional[str]:
        """
        渲染配置模板
        
        Args:
            template_name: 模板名称
            variables: 变量字典
            device_type: 设备类型
        
        Returns:
            渲染后的配置
        """
        template = self.load_template(template_name, device_type)
        
        if not template:
            return None
        
        # 简单的变量替换
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        
        return template
    
    def list_templates(self, device_type: str = None) -> List[Dict[str, Any]]:
        """
        列出模板
        
        Args:
            device_type: 设备类型
        
        Returns:
            模板列表
        """
        templates = []
        
        search_dir = self._templates_dir
        if device_type:
            search_dir = search_dir / device_type
        
        if not search_dir.exists():
            return templates
        
        for template_file in search_dir.glob("*.cfg"):
            meta_path = template_file.with_suffix('.meta')
            
            template_info = {
                'name': template_file.stem,
                'path': str(template_file),
                'size': template_file.stat().st_size,
                'modified': datetime.fromtimestamp(template_file.stat().st_mtime).isoformat()
            }
            
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                template_info.update(meta)
            
            templates.append(template_info)
        
        return templates
