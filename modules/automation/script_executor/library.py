"""
脚本库 (library.py)

提供脚本分类管理、脚本版本管理、脚本模板、脚本导入导出、脚本市场等功能
"""

import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml


class ScriptCategory(Enum):
    """脚本分类"""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    WEB = "web"
    SECURITY = "security"
    MONITORING = "monitoring"
    BACKUP = "backup"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"
    CUSTOM = "custom"


class ScriptStatus(Enum):
    """脚本状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class ScriptVersion:
    """脚本版本"""
    version: str
    content: str
    created_at: datetime
    created_by: str
    changelog: str = ""
    checksum: str = ""
    
    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.sha256(self.content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'changelog': self.changelog,
            'checksum': self.checksum,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScriptVersion':
        return cls(
            version=data['version'],
            content=data['content'],
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data['created_by'],
            changelog=data.get('changelog', ''),
            checksum=data.get('checksum', ''),
        )


@dataclass
class Script:
    """脚本定义"""
    id: str
    name: str
    description: str
    category: ScriptCategory
    script_type: str  # shell, powershell, python, ansible
    content: str
    version: str = "1.0.0"
    status: ScriptStatus = ScriptStatus.ACTIVE
    author: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    timeout: int = 300
    working_dir: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    versions: List[ScriptVersion] = field(default_factory=list)
    usage_count: int = 0
    rating: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_version(self, content: str, author: str, changelog: str = "") -> ScriptVersion:
        """添加新版本"""
        # 计算版本号
        parts = self.version.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        new_version = '.'.join(parts)
        
        version = ScriptVersion(
            version=new_version,
            content=content,
            created_at=datetime.now(),
            created_by=author,
            changelog=changelog,
        )
        
        self.versions.append(version)
        self.content = content
        self.version = new_version
        self.updated_at = datetime.now()
        
        return version
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'script_type': self.script_type,
            'content': self.content,
            'version': self.version,
            'status': self.status.value,
            'author': self.author,
            'tags': self.tags,
            'parameters': self.parameters,
            'timeout': self.timeout,
            'working_dir': self.working_dir,
            'env_vars': self.env_vars,
            'dependencies': self.dependencies,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'versions': [v.to_dict() for v in self.versions],
            'usage_count': self.usage_count,
            'rating': self.rating,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Script':
        """从字典创建"""
        versions = [
            ScriptVersion.from_dict(v) 
            for v in data.get('versions', [])
        ]
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            category=ScriptCategory(data.get('category', 'custom')),
            script_type=data.get('script_type', 'shell'),
            content=data['content'],
            version=data.get('version', '1.0.0'),
            status=ScriptStatus(data.get('status', 'active')),
            author=data.get('author', ''),
            tags=data.get('tags', []),
            parameters=data.get('parameters', []),
            timeout=data.get('timeout', 300),
            working_dir=data.get('working_dir'),
            env_vars=data.get('env_vars', {}),
            dependencies=data.get('dependencies', []),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
            versions=versions,
            usage_count=data.get('usage_count', 0),
            rating=data.get('rating', 0.0),
            metadata=data.get('metadata', {}),
        )


@dataclass
class ScriptTemplate:
    """脚本模板"""
    id: str
    name: str
    description: str
    category: ScriptCategory
    script_type: str
    content: str
    parameters: List[Dict[str, Any]]
    variables: List[Dict[str, str]]  # name, description, default
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'script_type': self.script_type,
            'content': self.content,
            'parameters': self.parameters,
            'variables': self.variables,
            'created_at': self.created_at.isoformat(),
            'usage_count': self.usage_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScriptTemplate':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            category=ScriptCategory(data['category']),
            script_type=data['script_type'],
            content=data['content'],
            parameters=data.get('parameters', []),
            variables=data.get('variables', []),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            usage_count=data.get('usage_count', 0),
        )


class ScriptLibrary:
    """
    脚本库管理
    
    提供脚本的CRUD操作、分类管理、版本管理、导入导出等功能
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化脚本库
        
        Args:
            storage_path: 存储路径，默认使用临时目录
        """
        self._storage_path = storage_path or tempfile.mkdtemp(prefix="script_library_")
        self._scripts: Dict[str, Script] = {}
        self._templates: Dict[str, ScriptTemplate] = {}
        self._lock = Lock()
        
        # 创建目录结构
        self._ensure_directories()
        
        # 加载已有数据
        self._load_data()
    
    def _ensure_directories(self):
        """确保目录结构存在"""
        directories = [
            self._storage_path,
            os.path.join(self._storage_path, "scripts"),
            os.path.join(self._storage_path, "templates"),
            os.path.join(self._storage_path, "market"),
            os.path.join(self._storage_path, "backups"),
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _load_data(self):
        """加载存储的数据"""
        scripts_dir = os.path.join(self._storage_path, "scripts")
        if os.path.exists(scripts_dir):
            for filename in os.listdir(scripts_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(scripts_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            script = Script.from_dict(data)
                            self._scripts[script.id] = script
                    except Exception:
                        pass
    
    def _save_script(self, script: Script):
        """保存脚本到磁盘"""
        scripts_dir = os.path.join(self._storage_path, "scripts")
        filepath = os.path.join(scripts_dir, f"{script.id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(script.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _generate_id(self, name: str) -> str:
        """生成脚本ID"""
        base = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        return f"{base}_{uuid.uuid4().hex[:8]}"
    
    # ==================== 脚本管理 ====================
    
    def create_script(
        self,
        name: str,
        content: str,
        script_type: str,
        description: str = "",
        category: ScriptCategory = ScriptCategory.CUSTOM,
        author: str = "",
        tags: Optional[List[str]] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        timeout: int = 300,
    ) -> Script:
        """
        创建新脚本
        
        Args:
            name: 脚本名称
            content: 脚本内容
            script_type: 脚本类型
            description: 描述
            category: 分类
            author: 作者
            tags: 标签
            parameters: 参数定义
            timeout: 超时时间
            
        Returns:
            Script: 创建的脚本对象
        """
        with self._lock:
            script_id = self._generate_id(name)
            script = Script(
                id=script_id,
                name=name,
                content=content,
                script_type=script_type,
                description=description,
                category=category,
                author=author,
                tags=tags or [],
                parameters=parameters or [],
                timeout=timeout,
            )
            
            # 添加初始版本
            script.add_version(content, author, "Initial version")
            
            self._scripts[script_id] = script
            self._save_script(script)
            
            return script
    
    def get_script(self, script_id: str) -> Optional[Script]:
        """
        获取脚本
        
        Args:
            script_id: 脚本ID
            
        Returns:
            Script: 脚本对象，不存在返回None
        """
        return self._scripts.get(script_id)
    
    def update_script(
        self,
        script_id: str,
        content: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[ScriptCategory] = None,
        tags: Optional[List[str]] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        timeout: Optional[int] = None,
        status: Optional[ScriptStatus] = None,
        author: str = "",
        changelog: str = "",
    ) -> Optional[Script]:
        """
        更新脚本
        
        Args:
            script_id: 脚本ID
            content: 新内容（会创建新版本）
            其他字段同上
            
        Returns:
            Script: 更新后的脚本对象
        """
        with self._lock:
            script = self._scripts.get(script_id)
            if not script:
                return None
            
            if content and content != script.content:
                script.add_version(content, author, changelog)
            if description is not None:
                script.description = description
            if category is not None:
                script.category = category
            if tags is not None:
                script.tags = tags
            if parameters is not None:
                script.parameters = parameters
            if timeout is not None:
                script.timeout = timeout
            if status is not None:
                script.status = status
            
            script.updated_at = datetime.now()
            self._save_script(script)
            
            return script
    
    def delete_script(self, script_id: str) -> bool:
        """
        删除脚本
        
        Args:
            script_id: 脚本ID
            
        Returns:
            bool: 是否成功删除
        """
        with self._lock:
            if script_id in self._scripts:
                # 删除文件
                scripts_dir = os.path.join(self._storage_path, "scripts")
                filepath = os.path.join(scripts_dir, f"{script_id}.json")
                if os.path.exists(filepath):
                    os.unlink(filepath)
                
                del self._scripts[script_id]
                return True
            return False
    
    def list_scripts(
        self,
        category: Optional[ScriptCategory] = None,
        status: Optional[ScriptStatus] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Script]:
        """
        列出脚本
        
        Args:
            category: 按分类过滤
            status: 按状态过滤
            tags: 按标签过滤
            search: 搜索关键词
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            List[Script]: 脚本列表
        """
        scripts = list(self._scripts.values())
        
        # 过滤
        if category:
            scripts = [s for s in scripts if s.category == category]
        if status:
            scripts = [s for s in scripts if s.status == status]
        if tags:
            scripts = [s for s in scripts if any(t in s.tags for t in tags)]
        if search:
            search_lower = search.lower()
            scripts = [
                s for s in scripts 
                if search_lower in s.name.lower() 
                or search_lower in s.description.lower()
            ]
        
        # 排序
        scripts.sort(key=lambda s: s.updated_at, reverse=True)
        
        # 分页
        return scripts[offset:offset + limit]
    
    def get_scripts_by_category(self, category: ScriptCategory) -> List[Script]:
        """获取指定分类的所有脚本"""
        return self.list_scripts(category=category)
    
    def increment_usage(self, script_id: str):
        """增加脚本使用次数"""
        with self._lock:
            script = self._scripts.get(script_id)
            if script:
                script.usage_count += 1
                self._save_script(script)
    
    # ==================== 版本管理 ====================
    
    def get_version(self, script_id: str, version: str) -> Optional[ScriptVersion]:
        """获取脚本指定版本"""
        script = self._scripts.get(script_id)
        if script:
            for v in script.versions:
                if v.version == version:
                    return v
        return None
    
    def get_versions(self, script_id: str) -> List[ScriptVersion]:
        """获取脚本所有版本"""
        script = self._scripts.get(script_id)
        return script.versions if script else []
    
    def rollback_version(self, script_id: str, version: str, author: str = "") -> bool:
        """
        回滚到指定版本
        
        Args:
            script_id: 脚本ID
            version: 版本号
            author: 操作人
            
        Returns:
            bool: 是否成功回滚
        """
        target_version = self.get_version(script_id, version)
        if not target_version:
            return False
        
        with self._lock:
            script = self._scripts.get(script_id)
            if script:
                script.add_version(
                    target_version.content,
                    author,
                    f"Rollback to version {version}"
                )
                self._save_script(script)
                return True
        return False
    
    # ==================== 模板管理 ====================
    
    def create_template(
        self,
        name: str,
        content: str,
        script_type: str,
        description: str,
        category: ScriptCategory = ScriptCategory.CUSTOM,
        parameters: Optional[List[Dict[str, Any]]] = None,
        variables: Optional[List[Dict[str, str]]] = None,
    ) -> ScriptTemplate:
        """
        创建脚本模板
        
        Args:
            name: 模板名称
            content: 模板内容
            script_type: 脚本类型
            description: 描述
            category: 分类
            parameters: 参数定义
            variables: 变量定义
            
        Returns:
            ScriptTemplate: 创建的模板对象
        """
        with self._lock:
            template_id = self._generate_id(name)
            template = ScriptTemplate(
                id=template_id,
                name=name,
                content=content,
                script_type=script_type,
                description=description,
                category=category,
                parameters=parameters or [],
                variables=variables or [],
            )
            
            self._templates[template_id] = template
            self._save_template(template)
            
            return template
    
    def get_template(self, template_id: str) -> Optional[ScriptTemplate]:
        """获取模板"""
        return self._templates.get(template_id)
    
    def list_templates(
        self,
        category: Optional[ScriptCategory] = None,
        script_type: Optional[str] = None,
    ) -> List[ScriptTemplate]:
        """列出模板"""
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        if script_type:
            templates = [t for t in templates if t.script_type == script_type]
        
        return templates
    
    def create_script_from_template(
        self,
        template_id: str,
        name: str,
        variables: Dict[str, str],
        author: str = "",
    ) -> Optional[Script]:
        """
        从模板创建脚本
        
        Args:
            template_id: 模板ID
            name: 脚本名称
            variables: 变量值
            author: 作者
            
        Returns:
            Script: 创建的脚本对象
        """
        template = self.get_template(template_id)
        if not template:
            return None
        
        # 替换变量
        content = template.content
        for var_name, var_value in variables.items():
            content = content.replace(f"${{{var_name}}}", var_value)
            content = content.replace(f"{{{{{var_name}}}}}", var_value)
        
        # 创建脚本
        script = self.create_script(
            name=name,
            content=content,
            script_type=template.script_type,
            description=f"Created from template: {template.name}",
            category=template.category,
            author=author,
            parameters=template.parameters,
        )
        
        # 增加模板使用次数
        template.usage_count += 1
        self._save_template(template)
        
        return script
    
    def _save_template(self, template: ScriptTemplate):
        """保存模板"""
        templates_dir = os.path.join(self._storage_path, "templates")
        filepath = os.path.join(templates_dir, f"{template.id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
    
    # ==================== 导入导出 ====================
    
    def export_script(self, script_id: str, format: str = "json") -> Optional[str]:
        """
        导出脚本
        
        Args:
            script_id: 脚本ID
            format: 导出格式 (json, yaml, text)
            
        Returns:
            str: 导出的内容，不存在返回None
        """
        script = self.get_script(script_id)
        if not script:
            return None
        
        if format == "json":
            return json.dumps(script.to_dict(), indent=2, ensure_ascii=False)
        elif format == "yaml":
            data = script.to_dict()
            # 移除versions避免过长
            if 'versions' in data:
                del data['versions']
            return yaml.dump(data, allow_unicode=True, default_flow_style=False)
        elif format == "text":
            return script.content
        return None
    
    def export_scripts(
        self,
        script_ids: List[str],
        output_path: Optional[str] = None,
    ) -> str:
        """
        批量导出脚本
        
        Args:
            script_ids: 脚本ID列表
            output_path: 输出文件路径
            
        Returns:
            str: 导出文件路径
        """
        export_data = []
        for script_id in script_ids:
            script = self.get_script(script_id)
            if script:
                export_data.append(script.to_dict())
        
        if not output_path:
            output_path = os.path.join(
                self._storage_path,
                "backups",
                f"scripts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def import_script(
        self,
        data: Union[str, Dict[str, Any]],
        format: str = "json",
        overwrite: bool = False,
    ) -> Optional[Script]:
        """
        导入脚本
        
        Args:
            data: 导入的数据
            format: 数据格式 (json, yaml, text)
            overwrite: 是否覆盖已存在的脚本
            
        Returns:
            Script: 导入的脚本对象
        """
        if format == "text":
            # 从文本创建简单脚本
            script = self.create_script(
                name=f"imported_script_{uuid.uuid4().hex[:8]}",
                content=data,
                script_type="shell",
            )
            return script
        
        # 解析数据
        if format == "json":
            if isinstance(data, str):
                parsed_data = json.loads(data)
            else:
                parsed_data = data
        elif format == "yaml":
            if isinstance(data, str):
                parsed_data = yaml.safe_load(data)
            else:
                parsed_data = data
        else:
            return None
        
        # 检查是否已存在
        script_id = parsed_data.get('id')
        if script_id and script_id in self._scripts and not overwrite:
            return None
        
        # 创建或更新脚本
        if script_id and script_id in self._scripts:
            script = self.update_script(
                script_id=script_id,
                content=parsed_data.get('content'),
                description=parsed_data.get('description'),
                category=ScriptCategory(parsed_data.get('category', 'custom')),
                tags=parsed_data.get('tags'),
                parameters=parsed_data.get('parameters'),
                timeout=parsed_data.get('timeout'),
            )
        else:
            script = Script.from_dict(parsed_data)
            if script.id not in self._scripts:
                script.id = self._generate_id(script.name)
            self._scripts[script.id] = script
            self._save_script(script)
        
        return script
    
    def import_from_file(
        self,
        filepath: str,
        overwrite: bool = False,
    ) -> List[Script]:
        """
        从文件导入脚本
        
        Args:
            filepath: 文件路径
            overwrite: 是否覆盖
            
        Returns:
            List[Script]: 导入的脚本列表
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return [
                self.import_script(item, format="json", overwrite=overwrite)
                for item in data
            ]
        else:
            script = self.import_script(data, format="json", overwrite=overwrite)
            return [script] if script else []
    
    def export_package(
        self,
        script_ids: List[str],
        output_path: Optional[str] = None,
    ) -> str:
        """
        导出脚本包（ZIP格式）
        
        Args:
            script_ids: 脚本ID列表
            output_path: 输出文件路径
            
        Returns:
            str: 导出的ZIP文件路径
        """
        if not output_path:
            output_path = os.path.join(
                self._storage_path,
                "backups",
                f"scripts_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for script_id in script_ids:
                script = self.get_script(script_id)
                if script:
                    # 添加脚本文件
                    ext = self._get_extension(script.script_type)
                    filename = f"{script.name}{ext}"
                    zipf.writestr(filename, script.content)
                    
                    # 添加元数据
                    meta_filename = f"{script.name}.meta.json"
                    zipf.writestr(meta_filename, json.dumps(script.to_dict(), indent=2))
        
        return output_path
    
    def import_package(
        self,
        zip_path: str,
        overwrite: bool = False,
    ) -> List[Script]:
        """
        导入脚本包（ZIP格式）
        
        Args:
            zip_path: ZIP文件路径
            overwrite: 是否覆盖
            
        Returns:
            List[Script]: 导入的脚本列表
        """
        imported = []
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            for filename in zipf.namelist():
                if filename.endswith('.meta.json'):
                    continue
                
                content = zipf.read(filename).decode('utf-8')
                script_type = self._detect_type_from_extension(filename)
                
                script = self.create_script(
                    name=os.path.splitext(os.path.basename(filename))[0],
                    content=content,
                    script_type=script_type,
                )
                imported.append(script)
                
                # 尝试读取元数据
                meta_filename = filename + '.meta.json'
                if meta_filename in zipf.namelist():
                    try:
                        meta_data = json.loads(zipf.read(meta_filename).decode('utf-8'))
                        # 更新元数据
                        self.update_script(
                            script.id,
                            description=meta_data.get('description', ''),
                            tags=meta_data.get('tags', []),
                            parameters=meta_data.get('parameters', []),
                        )
                    except:
                        pass
        
        return imported
    
    def _get_extension(self, script_type: str) -> str:
        """获取脚本类型对应的扩展名"""
        extensions = {
            'shell': '.sh',
            'powershell': '.ps1',
            'python': '.py',
            'ansible': '.yml',
        }
        return extensions.get(script_type, '.sh')
    
    def _detect_type_from_extension(self, filename: str) -> str:
        """从文件扩展名检测脚本类型"""
        ext = os.path.splitext(filename)[1].lower()
        type_map = {
            '.sh': 'shell',
            '.bash': 'shell',
            '.ps1': 'powershell',
            '.py': 'python',
            '.yml': 'ansible',
            '.yaml': 'ansible',
        }
        return type_map.get(ext, 'shell')
    
    # ==================== 脚本市场 ====================
    
    def publish_to_market(
        self,
        script_id: str,
        marketplace_path: Optional[str] = None,
    ) -> bool:
        """
        发布脚本到市场
        
        Args:
            script_id: 脚本ID
            marketplace_path: 市场路径
            
        Returns:
            bool: 是否成功发布
        """
        script = self.get_script(script_id)
        if not script:
            return False
        
        market_path = marketplace_path or os.path.join(self._storage_path, "market")
        os.makedirs(market_path, exist_ok=True)
        
        # 导出到市场
        export_data = {
            'id': script.id,
            'name': script.name,
            'description': script.description,
            'category': script.category.value,
            'script_type': script.script_type,
            'content': script.content,
            'version': script.version,
            'author': script.author,
            'tags': script.tags,
            'parameters': script.parameters,
            'published_at': datetime.now().isoformat(),
        }
        
        filepath = os.path.join(market_path, f"{script.id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return True
    
    def browse_market(
        self,
        category: Optional[ScriptCategory] = None,
        search: Optional[str] = None,
        marketplace_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        浏览市场
        
        Args:
            category: 按分类过滤
            search: 搜索关键词
            marketplace_path: 市场路径
            
        Returns:
            List[Dict[str, Any]]: 市场脚本列表
        """
        market_path = marketplace_path or os.path.join(self._storage_path, "market")
        
        if not os.path.exists(market_path):
            return []
        
        items = []
        for filename in os.listdir(market_path):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(market_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 过滤
                    if category and data.get('category') != category.value:
                        continue
                    if search:
                        search_lower = search.lower()
                        if (search_lower not in data.get('name', '').lower() and
                            search_lower not in data.get('description', '').lower()):
                            continue
                    
                    items.append(data)
            except:
                pass
        
        return items
    
    def install_from_market(
        self,
        market_item: Dict[str, Any],
        author: str = "",
    ) -> Optional[Script]:
        """
        从市场安装脚本
        
        Args:
            market_item: 市场项目数据
            author: 安装者
            
        Returns:
            Script: 安装的脚本
        """
        return self.create_script(
            name=f"{market_item['name']}_installed",
            content=market_item['content'],
            script_type=market_item['script_type'],
            description=market_item.get('description', ''),
            category=ScriptCategory(market_item.get('category', 'custom')),
            author=author,
            tags=market_item.get('tags', []),
            parameters=market_item.get('parameters', []),
        )
    
    # ==================== 统计 ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_scripts = len(self._scripts)
        total_templates = len(self._templates)
        
        # 按分类统计
        by_category: Dict[str, int] = {}
        for script in self._scripts.values():
            cat = script.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
        
        # 按状态统计
        by_status: Dict[str, int] = {}
        for script in self._scripts.values():
            status = script.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # 按类型统计
        by_type: Dict[str, int] = {}
        for script in self._scripts.values():
            stype = script.script_type
            by_type[stype] = by_type.get(stype, 0) + 1
        
        # 使用统计
        total_usage = sum(s.usage_count for s in self._scripts.values())
        avg_rating = sum(s.rating for s in self._scripts.values()) / max(total_scripts, 1)
        
        return {
            'total_scripts': total_scripts,
            'total_templates': total_templates,
            'by_category': by_category,
            'by_status': by_status,
            'by_type': by_type,
            'total_usage': total_usage,
            'average_rating': round(avg_rating, 2),
            'storage_path': self._storage_path,
        }


class Lock:
    """简单的线程锁"""
    def __init__(self):
        self._lock = threading.Lock()
    
    def __enter__(self):
        self._lock.acquire()
        return self
    
    def __exit__(self, *args):
        self._lock.release()


# 导入threading
import threading
