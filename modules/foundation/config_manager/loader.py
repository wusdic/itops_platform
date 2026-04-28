"""
配置加载器
支持多环境配置、配置优先级、配置合并
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
import json
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    配置加载器
    
    功能特性：
    1. 多环境配置（dev, test, staging, prod）
    2. 配置合并（基础配置 + 环境配置）
    3. 配置覆盖优先级
    4. 动态配置路径解析
    
    使用示例：
    >>> loader = ConfigLoader()
    >>> loader.add_path("config/base.yaml")
    >>> loader.add_path("config/prod.yaml")
    >>> config = loader.load()
    """
    
    def __init__(self):
        self._paths: List[Path] = []
        self._env: str = os.getenv('ITOPS_ENV', 'dev')
        self._base_dir: Optional[Path] = None
        self._config: Dict[str, Any] = {}
    
    def set_base_dir(self, base_dir: Union[str, Path]) -> 'ConfigLoader':
        """
        设置配置基础目录
        
        Args:
            base_dir: 基础目录路径
        
        Returns:
            self
        """
        self._base_dir = Path(base_dir)
        return self
    
    def set_env(self, env: str) -> 'ConfigLoader':
        """
        设置运行环境
        
        Args:
            env: 环境名称 (dev, test, staging, prod)
        
        Returns:
            self
        """
        self._env = env
        return self
    
    def add_path(self, path: Union[str, Path]) -> 'ConfigLoader':
        """
        添加配置文件路径
        
        Args:
            path: 配置文件路径
        
        Returns:
            self
        """
        if self._base_dir:
            path = self._base_dir / path
        else:
            path = Path(path)
        
        self._paths.append(path)
        return self
    
    def add_search_paths(self) -> 'ConfigLoader':
        """
        添加搜索路径（支持多环境）
        
        搜索顺序（后面的覆盖前面的）：
        1. config/default.yaml
        2. config/{env}.yaml
        3. config/local.yaml (如果存在)
        """
        if not self._base_dir:
            self._base_dir = Path(".")
        
        # 默认配置
        default_path = self._base_dir / "config" / "default.yaml"
        if default_path.exists():
            self._paths.append(default_path)
        
        # 环境配置
        env_path = self._base_dir / "config" / f"{self._env}.yaml"
        if env_path.exists():
            self._paths.append(env_path)
        
        # 本地配置（不会被提交到版本控制）
        local_path = self._base_dir / "config" / "local.yaml"
        if local_path.exists():
            self._paths.append(local_path)
        
        return self
    
    def load(self) -> Dict[str, Any]:
        """
        加载并合并所有配置
        
        Returns:
            合并后的配置字典
        """
        self._config = {}
        
        for path in self._paths:
            if not path.exists():
                logger.warning(f"配置文件不存在: {path}")
                continue
            
            try:
                config_data = self._load_file(path)
                self._merge_config(config_data)
                logger.debug(f"加载配置: {path}")
            except Exception as e:
                logger.error(f"加载配置失败 {path}: {e}")
        
        return self._config
    
    def _load_file(self, path: Path) -> Dict[str, Any]:
        """加载单个配置文件"""
        suffix = path.suffix.lower()
        
        with open(path, 'r', encoding='utf-8') as f:
            if suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f) or {}
            elif suffix == '.json':
                return json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {suffix}")
    
    def _merge_config(self, new_config: Dict[str, Any], base: Optional[Dict] = None):
        """
        深度合并配置
        
        Args:
            new_config: 新配置
            base: 基础配置
        """
        target = base if base is not None else self._config
        
        for key, value in new_config.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                self._merge_config(value, target[key])
            else:
                # 直接覆盖
                target[key] = value
    
    def get_env(self) -> str:
        """获取当前环境"""
        return self._env
    
    def get_config(self) -> Dict[str, Any]:
        """获取加载的配置"""
        return self._config
    
    def save(self, path: Optional[Path] = None) -> Path:
        """
        保存配置到文件
        
        Args:
            path: 保存路径，默认覆盖第一个加载的文件
        
        Returns:
            保存的文件路径
        """
        if not path:
            path = self._paths[0] if self._paths else Path("config.yaml")
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self._config, f, default_flow_style=False, indent=2)
        
        logger.info(f"配置已保存: {path}")
        return path


class ConfigMerger:
    """
    配置合并工具
    
    用于合并来自不同来源的配置
    """
    
    @staticmethod
    def merge(*configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多个配置字典
        
        Args:
            *configs: 配置字典列表，后面的会覆盖前面的
        
        Returns:
            合并后的配置
        """
        result = {}
        for config in configs:
            ConfigLoader()._merge_config(config, result)
        return result
    
    @staticmethod
    def merge_override(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        用override覆盖base配置
        
        Args:
            base: 基础配置
            override: 覆盖配置
        
        Returns:
            合并后的配置
        """
        result = base.copy()
        ConfigLoader()._merge_config(override, result)
        return result