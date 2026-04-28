"""
配置管理核心模块
支持 YAML/JSON/ENV 配置文件，敏感信息加密，配置热更新
"""

import os
import yaml
import json
import base64
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    username: str = "root"
    password: str = ""
    database: str = "itops_platform"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    max_connections: int = 50


@dataclass
class MonitorConfig:
    """监控配置"""
    snmp_timeout: int = 5
    snmp_retries: int = 3
    agent_port: int = 10050
    collection_interval: int = 60
    alert_check_interval: int = 30


@dataclass
class AIConfig:
    """AI配置"""
    provider: str = "ollama"  # ollama, openai, azure
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class AppConfig:
    """应用配置"""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    secret_key: str = ""
    cors_origins: list = field(default_factory=lambda: ["*"])
    log_level: str = "INFO"


class ConfigManager:
    """
    统一配置管理器
    
    功能特性：
    1. 支持多格式配置：YAML, JSON, ENV
    2. 配置热更新
    3. 敏感信息加密
    4. 配置验证
    5. 环境变量覆盖
    
    使用示例：
    >>> config = ConfigManager()
    >>> config.load("config.yaml")
    >>> db_config = config.get_database()
    >>> config.set("app.debug", True)
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._config: Dict[str, Any] = {}
        self._config_file: Optional[Path] = None
        self._encryption_key: Optional[bytes] = None
        self._validator = None
        self._watchers: list = []
        
        # 加载环境变量前缀
        self._env_prefix = "ITOPS_"
    
    def load(self, config_path: Union[str, Path], validate: bool = True) -> 'ConfigManager':
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            validate: 是否验证配置
        
        Returns:
            self
        """
        self._config_file = Path(config_path)
        
        if not self._config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        # 根据文件扩展名选择加载方式
        suffix = self._config_file.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            self._load_yaml()
        elif suffix == '.json':
            self._load_json()
        else:
            raise ValueError(f"不支持的配置文件格式: {suffix}")
        
        # 加载环境变量覆盖
        self._load_env_overrides()
        
        # 加密存储的敏感信息
        self._decrypt_secrets()
        
        # 验证配置
        if validate:
            self.validate()
        
        logger.info(f"配置加载成功: {config_path}")
        return self
    
    def _load_yaml(self):
        """加载YAML配置"""
        with open(self._config_file, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}
    
    def _load_json(self):
        """加载JSON配置"""
        with open(self._config_file, 'r', encoding='utf-8') as f:
            self._config = json.load(f)
    
    def _load_env_overrides(self):
        """加载环境变量覆盖"""
        for key, value in os.environ.items():
            if key.startswith(self._env_prefix):
                config_key = key[len(self._env_prefix):].lower()
                self._set_nested(config_key, self._parse_env_value(value))
    
    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 尝试转换为不同类型
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
        elif value.isdigit():
            return int(value)
        elif value.replace('.', '', 1).isdigit():
            return float(value)
        return value
    
    def _set_nested(self, key: str, value: Any):
        """设置嵌套配置"""
        keys = key.split('.')
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    
    def _decrypt_secrets(self):
        """解密敏感信息"""
        secrets = self._config.get('secrets', {})
        if not secrets:
            return
        
        # 生成解密密钥（实际使用时应该从安全存储获取）
        self._encryption_key = self._generate_key(
            self._config.get('encryption_key', 'default-key-change-me')
        )
        
        cipher = Fernet(self._encryption_key)
        
        for key, encrypted_value in secrets.items():
            try:
                # 如果值不是base64编码的加密值，直接使用
                if not encrypted_value.startswith('enc:'):
                    continue
                    
                encrypted_data = base64.b64decode(encrypted_value[4:])
                decrypted = cipher.decrypt(encrypted_data)
                self._set_nested(key, decrypted.decode('utf-8'))
            except Exception as e:
                logger.warning(f"解密配置失败 [{key}]: {e}")
    
    def _generate_key(self, password: str) -> bytes:
        """生成加密密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'itops-platform-salt',
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        current = self._config
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any, persist: bool = False):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            persist: 是否持久化到文件
        """
        self._set_nested(key, value)
        
        if persist and self._config_file:
            self._save()
    
    def _save(self):
        """保存配置到文件"""
        suffix = self._config_file.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self._config, f, default_flow_style=False)
        elif suffix == '.json':
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        
        logger.info(f"配置已保存: {self._config_file}")
    
    def get_database(self) -> DatabaseConfig:
        """获取数据库配置"""
        db_config = self.get('database', {})
        return DatabaseConfig(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 3306),
            username=db_config.get('username', 'root'),
            password=db_config.get('password', ''),
            database=db_config.get('database', 'itops_platform'),
            pool_size=db_config.get('pool_size', 10),
            max_overflow=db_config.get('max_overflow', 20),
            echo=db_config.get('echo', False)
        )
    
    def get_redis(self) -> RedisConfig:
        """获取Redis配置"""
        redis_config = self.get('redis', {})
        return RedisConfig(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            password=redis_config.get('password', ''),
            db=redis_config.get('db', 0),
            max_connections=redis_config.get('max_connections', 50)
        )
    
    def get_monitor(self) -> MonitorConfig:
        """获取监控配置"""
        monitor_config = self.get('monitor', {})
        return MonitorConfig(
            snmp_timeout=monitor_config.get('snmp_timeout', 5),
            snmp_retries=monitor_config.get('snmp_retries', 3),
            agent_port=monitor_config.get('agent_port', 10050),
            collection_interval=monitor_config.get('collection_interval', 60),
            alert_check_interval=monitor_config.get('alert_check_interval', 30)
        )
    
    def get_ai(self) -> AIConfig:
        """获取AI配置"""
        ai_config = self.get('ai', {})
        return AIConfig(
            provider=ai_config.get('provider', 'ollama'),
            base_url=ai_config.get('base_url', 'http://localhost:11434'),
            model=ai_config.get('model', 'qwen2.5:7b'),
            api_key=ai_config.get('api_key', ''),
            temperature=ai_config.get('temperature', 0.7),
            max_tokens=ai_config.get('max_tokens', 4096)
        )
    
    def get_app(self) -> AppConfig:
        """获取应用配置"""
        app_config = self.get('app', {})
        return AppConfig(
            host=app_config.get('host', '0.0.0.0'),
            port=app_config.get('port', 8080),
            debug=app_config.get('debug', False),
            secret_key=app_config.get('secret_key', ''),
            cors_origins=app_config.get('cors_origins', ['*']),
            log_level=app_config.get('log_level', 'INFO')
        )
    
    def validate(self) -> bool:
        """
        验证配置
        
        Returns:
            验证是否通过
        
        Raises:
            ValueError: 配置验证失败
        """
        errors = []
        
        # 验证数据库配置
        if not self.get('database.host'):
            errors.append("数据库主机未配置")
        
        # 验证应用配置
        if not self.get('app.port'):
            errors.append("应用端口未配置")
        
        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
        
        logger.info("配置验证通过")
        return True
    
    def encrypt_value(self, value: str) -> str:
        """
        加密敏感值
        
        Args:
            value: 待加密的值
        
        Returns:
            加密后的值（格式: enc:base64）
        """
        if not self._encryption_key:
            self._encryption_key = self._generate_key(
                self._config.get('encryption_key', 'default-key-change-me')
            )
        
        cipher = Fernet(self._encryption_key)
        encrypted = cipher.encrypt(value.encode())
        return f"enc:{base64.b64encode(encrypted).decode()}"
    
    def watch(self, callback):
        """
        监听配置变化
        
        Args:
            callback: 配置变化时的回调函数
        """
        self._watchers.append(callback)
    
    def reload(self):
        """重新加载配置"""
        if self._config_file and self._config_file.exists():
            self._config = {}
            self.load(self._config_file, validate=False)
            for callback in self._watchers:
                callback(self._config)
            logger.info("配置已重新加载")
    
    def to_dict(self) -> Dict[str, Any]:
        """获取配置字典（不含敏感信息）"""
        result = {}
        for key, value in self._config.items():
            if key == 'secrets' or 'password' in key.lower() or 'key' in key.lower():
                result[key] = "***ENCRYPTED***"
            else:
                result[key] = value
        return result


class Config:
    """配置类别名，用于类型提示"""
    pass


def create_default_config(path: Union[str, Path] = "config.yaml"):
    """
    创建默认配置文件
    
    Args:
        path: 配置文件路径
    """
    default_config = {
        'app': {
            'host': '0.0.0.0',
            'port': 8080,
            'debug': False,
            'secret_key': 'change-me-in-production',
            'log_level': 'INFO'
        },
        'database': {
            'host': 'localhost',
            'port': 3306,
            'username': 'root',
            'password': '',
            'database': 'itops_platform',
            'pool_size': 10
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'password': '',
            'db': 0
        },
        'monitor': {
            'snmp_timeout': 5,
            'snmp_retries': 3,
            'agent_port': 10050,
            'collection_interval': 60
        },
        'ai': {
            'provider': 'ollama',
            'base_url': 'http://localhost:11434',
            'model': 'qwen2.5:7b',
            'temperature': 0.7
        },
        'encryption_key': 'change-me-in-production'
    }
    
    path = Path(path)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(default_config, f, default_flow_style=False, indent=2)
    
    print(f"默认配置已创建: {path}")
    return path