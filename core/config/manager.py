# -*- coding: utf-8 -*-
"""
ITOps Platform - 核心配置管理器
基于GitHub版本架构设计，支持多格式、热更新、加密配置
"""
import os
import yaml
import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
import threading
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ConfigEncryption:
    """配置加密工具类"""
    
    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """从密码派生加密密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    @staticmethod
    def encrypt(data: str, key: bytes) -> str:
        """加密数据"""
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()
    
    @staticmethod
    def decrypt(encrypted_data: str, key: bytes) -> str:
        """解密数据"""
        f = Fernet(key)
        return f.decrypt(encrypted_data.encode()).decode()


class ConfigLoader:
    """配置加载器 - 支持多格式、多环境"""
    
    SEARCH_PATHS = [
        "config/default.yaml",
        "config/{env}.yaml",
        "config/local.yaml",
    ]
    
    def __init__(self, env: str = None):
        self.env = env or os.getenv("ITOPS_ENV", "development")
        self._config: Dict[str, Any] = {}
        self._load_timestamp: datetime = None
        self._file_hashes: Dict[str, str] = {}
        self._encryption_key: Optional[bytes] = None
        self._watch_callbacks: List[callable] = []
    
    def set_encryption_key(self, password: str, salt: bytes = None):
        """设置加密密钥"""
        if salt is None:
            salt = b"itops_platform_salt_v1"
        self._encryption_key = ConfigEncryption.derive_key(password, salt)
    
    def add_watch_callback(self, callback: callable):
        """添加配置变更回调"""
        self._watch_callbacks.append(callback)
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _calculate_file_hash(self, path: Path) -> str:
        """计算文件哈希"""
        if not path.exists():
            return ""
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def _should_reload(self) -> bool:
        """检查是否需要重新加载"""
        for pattern in self.SEARCH_PATHS:
            path = Path(pattern.format(env=self.env))
            if path.exists():
                current_hash = self._calculate_file_hash(path)
                if str(path) in self._file_hashes and self._file_hashes[str(path)] != current_hash:
                    return True
        return False
    
    def _load_yaml(self, path: Path) -> Dict:
        """加载YAML配置"""
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_json(self, path: Path) -> Dict:
        """加载JSON配置"""
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_env(self, path: Path) -> Dict:
        """加载ENV配置"""
        if not path.exists():
            return {}
        result = {}
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    result[key.strip()] = value.strip()
        return result
    
    def load(self, reload: bool = False) -> Dict[str, Any]:
        """加载配置"""
        if not reload and self._config and not self._should_reload():
            return self._config
        
        configs = []
        for pattern in self.SEARCH_PATHS:
            path = Path(pattern.format(env=self.env))
            if path.exists():
                self._file_hashes[str(path)] = self._calculate_file_hash(path)
                suffix = path.suffix.lower()
                if suffix in ['.yaml', '.yml']:
                    configs.append(self._load_yaml(path))
                elif suffix == '.json':
                    configs.append(self._load_json(path))
                elif suffix == '.env':
                    configs.append(self._load_env(path))
        
        # 合并配置（后面的覆盖前面的）
        self._config = {}
        for config in configs:
            self._config = self._deep_merge(self._config, config)
        
        # 应用环境变量覆盖
        self._apply_env_overrides()
        
        # 解密敏感字段
        self._decrypt_sensitive()
        
        self._load_timestamp = datetime.now()
        return self._config
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        for key, value in os.environ.items():
            if key.startswith("ITOPS_"):
                config_key = key[6:].lower()
                # 支持嵌套键: ITOPS_DATABASE__HOST
                if '__' in config_key:
                    parts = config_key.split('__')
                    current = self._config
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = self._parse_value(value)
                else:
                    self._config[config_key] = self._parse_value(value)
    
    def _parse_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 布尔值
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        # 数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        # JSON字符串
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value
    
    def _decrypt_sensitive(self):
        """解密敏感字段"""
        if not self._encryption_key:
            return
        
        def decrypt_field(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key.endswith('_encrypted') and isinstance(value, str):
                        # 移除_encrypted后缀，使用原键名
                        orig_key = key[:-10]
                        try:
                            data[orig_key] = ConfigEncryption.decrypt(value, self._encryption_key)
                            del data[key]
                        except Exception:
                            pass
                    else:
                        decrypt_field(value)
                return data
            return data
        
        self._config = decrypt_field(self._config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if not self._config:
            self.load()
        
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def reload(self):
        """重新加载配置"""
        self.load(reload=True)
        for callback in self._watch_callbacks:
            try:
                callback(self._config)
            except Exception as e:
                print(f"配置变更回调失败: {e}")


class ConfigValidator:
    """配置验证器 - 链式调用"""
    
    def __init__(self, value, name: str = "value"):
        self.value = value
        self.name = name
        self._errors: List[str] = []
    
    def required(self) -> 'ConfigValidator':
        """值不能为空"""
        if self.value is None or self.value == "":
            self._errors.append(f"{self.name} 是必填项")
        return self
    
    def min_length(self, length: int) -> 'ConfigValidator':
        """最小长度"""
        if self.value and len(str(self.value)) < length:
            self._errors.append(f"{self.name} 长度不能小于 {length}")
        return self
    
    def max_length(self, length: int) -> 'ConfigValidator':
        """最大长度"""
        if self.value and len(str(self.value)) > length:
            self._errors.append(f"{self.name} 长度不能大于 {length}")
        return self
    
    def in_range(self, min_val: float, max_val: float) -> 'ConfigValidator':
        """数值范围"""
        if self.value is not None:
            try:
                val = float(self.value)
                if val < min_val or val > max_val:
                    self._errors.append(f"{self.name} 必须在 {min_val} 和 {max_val} 之间")
            except (ValueError, TypeError):
                self._errors.append(f"{self.name} 必须是数字")
        return self
    
    def one_of(self, choices: List[Any]) -> 'ConfigValidator':
        """枚举值"""
        if self.value not in choices:
            self._errors.append(f"{self.name} 必须是 {choices} 之一")
        return self
    
    def is_url(self) -> 'ConfigValidator':
        """必须是URL"""
        if self.value:
            if not (self.value.startswith('http://') or self.value.startswith('https://')):
                self._errors.append(f"{self.name} 必须是有效的URL")
        return self
    
    def is_email(self) -> 'ConfigValidator':
        """必须是邮箱"""
        import re
        if self.value and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', self.value):
            self._errors.append(f"{self.name} 必须是有效的邮箱地址")
        return self
    
    def matches(self, pattern: str) -> 'ConfigValidator':
        """正则匹配"""
        import re
        if self.value and not re.match(pattern, str(self.value)):
            self._errors.append(f"{self.name} 格式不匹配")
        return self
    
    def validate(self) -> bool:
        """验证配置"""
        if self._errors:
            raise ValueError(f"配置验证失败: {'; '.join(self._errors)}")
        return True
    
    def get_errors(self) -> List[str]:
        """获取错误列表"""
        return self._errors.copy()


class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    database: str = "itops"
    username: str = "root"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20


class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = None
    max_connections: int = 50


class TDengineConfig:
    """TDengine配置"""
    host: str = "localhost"
    port: int = 6041
    username: str = "root"
    password: str = "taosdata"
    database: str = "itops"
    

class InfluxDBConfig:
    """InfluxDB配置"""
    url: str = "http://localhost:8086"
    token: str = ""
    org: str = "itops"
    bucket: str = "metrics"


class MinIOConfig:
    """MinIO配置"""
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "itops"
    secure: bool = False


class QdrantConfig:
    """Qdrant配置"""
    host: str = "localhost"
    port: int = 6333
    collection: str = "itops_knowledge"


class LLMConfig:
    """LLM配置"""
    provider: str = "qwen"
    api_base: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = "qwen2.5-7b-instruct"
    temperature: float = 0.7
    max_tokens: int = 2048


class ConfigManager:
    """
    配置管理器 - 单例模式
    支持热更新、加密、验证
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._loader = ConfigLoader()
        self._cache: Dict[str, Any] = {}
        self._watch_callbacks: List[callable] = []
        
        # 注册默认配置变更回调
        self._loader.add_watch_callback(self._on_config_change)
    
    def _on_config_change(self, new_config: Dict):
        """配置变更回调"""
        self._cache.clear()
        for callback in self._watch_callbacks:
            try:
                callback(new_config)
            except Exception as e:
                print(f"配置变更回调失败: {e}")
    
    def add_watch_callback(self, callback: callable):
        """添加配置变更监听"""
        self._watch_callbacks.append(callback)
    
    def load(self, config_dir: str = None):
        """加载配置"""
        if config_dir:
            # 设置配置目录
            import os
            os.chdir(config_dir)
        return self._loader.load()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if key not in self._cache:
            self._cache[key] = self._loader.get(key, default)
        return self._cache[key]
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置节"""
        return self.get(section, {})
    
    @property
    def database(self) -> DatabaseConfig:
        """数据库配置"""
        return self._bind_config(DatabaseConfig)
    
    @property
    def redis(self) -> RedisConfig:
        """Redis配置"""
        return self._bind_config(RedisConfig)
    
    @property
    def tdengine(self) -> TDengineConfig:
        """TDengine配置"""
        return self._bind_config(TDengineConfig)
    
    @property
    def influxdb(self) -> InfluxDBConfig:
        """InfluxDB配置"""
        return self._bind_config(InfluxDBConfig)
    
    @property
    def minio(self) -> MinIOConfig:
        """MinIO配置"""
        return self._bind_config(MinIOConfig)
    
    @property
    def qdrant(self) -> QdrantConfig:
        """Qdrant配置"""
        return self._bind_config(QdrantConfig)
    
    @property
    def llm(self) -> LLMConfig:
        """LLM配置"""
        return self._bind_config(LLMConfig)
    
    def _bind_config(self, config_class):
        """绑定配置类"""
        config = config_class()
        section = config_class.__name__.replace('Config', '').lower()
        section_config = self.get_section(section)
        
        for key, value in section_config.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    def reload(self):
        """重新加载配置"""
        self._cache.clear()
        self._loader.reload()
    
    def validate(self, section: str = None) -> bool:
        """验证配置"""
        if section:
            section_config = self.get_section(section)
            for key, value in section_config.items():
                ConfigValidator(value, f"{section}.{key}").required().validate()
            return True
        
        # 验证所有配置
        sections = ['database', 'redis', 'tdengine', 'influxdb', 'minio', 'qdrant', 'llm']
        for section in sections:
            try:
                config = self.get_section(section)
                if config:
                    print(f"✓ {section} 配置加载成功")
                else:
                    print(f"✗ {section} 配置为空")
            except Exception as e:
                print(f"✗ {section} 配置验证失败: {e}")
        
        return True
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """获取单例实例"""
        return cls()


def get_config() -> ConfigManager:
    """获取配置管理器快捷函数"""
    return ConfigManager.get_instance()
