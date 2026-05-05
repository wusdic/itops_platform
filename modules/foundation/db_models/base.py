"""
数据库基础模型和连接管理
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool

# 尝试导入配置管理模块 (可选依赖)
try:
    from modules.foundation.config_manager.config import ConfigManager
    _config_available = True
except ImportError:
    # 配置管理器不存在，使用环境变量方式
    _config_available = False
    ConfigManager = None


Base = declarative_base()


class DatabaseManager:
    """数据库管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._engine = None
        self._session_factory = None
        self._config = None
    
    def setup(self, config: dict = None):
        """
        设置数据库连接
        
        Args:
            config: 数据库配置，如果为None则从环境变量或配置文件读取
        """
        if config is None:
            config = self._load_config()
        
        # 构建数据库URL
        db_type = config.get('type', 'mysql')
        
        if db_type == 'mysql':
            url = self._build_mysql_url(config)
        elif db_type == 'postgresql':
            url = self._build_postgresql_url(config)
        elif db_type == 'sqlite':
            url = f"sqlite:///{config.get('database', 'itops.db')}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        
        # 创建引擎
        self._engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=config.get('pool_size', 10),
            max_overflow=config.get('max_overflow', 20),
            pool_pre_ping=True,  # 连接前ping
            echo=config.get('echo', False)
        )
        
        # 创建session工厂
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )
        
        return self
    
    def _load_config(self) -> dict:
        """加载数据库配置"""
        if _config_available:
            try:
                config_manager = ConfigManager()
                if config_manager._config:
                    db_config = config_manager.get_database()
                    return {
                        'type': 'mysql',
                        'host': db_config.host,
                        'port': db_config.port,
                        'username': db_config.username,
                        'password': db_config.password,
                        'database': db_config.database,
                        'pool_size': db_config.pool_size,
                        'max_overflow': db_config.max_overflow
                    }
            except Exception:
                pass
        
        # 从环境变量读取
        return {
            'type': os.getenv('ITOPS_DB_TYPE', 'mysql'),
            'host': os.getenv('ITOPS_DB_HOST', 'localhost'),
            'port': int(os.getenv('ITOPS_DB_PORT', '3306')),
            'username': os.getenv('ITOPS_DB_USER', 'root'),
            'password': os.getenv('ITOPS_DB_PASSWORD', ''),
            'database': os.getenv('ITOPS_DB_NAME', 'itops_platform'),
            'pool_size': 10,
            'max_overflow': 20
        }
    
    def _build_mysql_url(self, config: dict) -> str:
        """构建MySQL URL"""
        return (
            f"mysql+pymysql://{config.get('username', 'root')}:"
            f"{config.get('password', '')}@"
            f"{config.get('host', 'localhost')}:"
            f"{config.get('port', 3306)}/"
            f"{config.get('database', 'itops_platform')}"
            f"?charset=utf8mb4"
        )
    
    def _build_postgresql_url(self, config: dict) -> str:
        """构建PostgreSQL URL"""
        return (
            f"postgresql://{config.get('username', 'postgres')}:"
            f"{config.get('password', '')}@"
            f"{config.get('host', 'localhost')}:"
            f"{config.get('port', 5432)}/"
            f"{config.get('database', 'itops_platform')}"
        )
    
    def get_engine(self):
        """获取数据库引擎"""
        if self._engine is None:
            self.setup()
        return self._engine
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        if self._session_factory is None:
            self.setup()
        return self._session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        获取会话上下文管理器
        
        使用示例：
        >>> with db_manager.session_scope() as session:
        ...     devices = session.query(Device).all()
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_all(self):
        """创建所有表"""
        if self._engine is None:
            self.setup()
        Base.metadata.create_all(self._engine)
    
    def drop_all(self):
        """删除所有表"""
        if self._engine is None:
            self.setup()
        Base.metadata.drop_all(self._engine)
    
    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()


# 全局数据库管理器实例
_db_manager = DatabaseManager()


def init_db(config: dict = None) -> DatabaseManager:
    """
    初始化数据库
    
    Args:
        config: 数据库配置
    
    Returns:
        DatabaseManager实例
    """
    return _db_manager.setup(config)


def close_db():
    """关闭数据库"""
    _db_manager.close()


def get_engine():
    """获取数据库引擎"""
    return _db_manager.get_engine()


def db_session() -> Generator[Session, None, None]:
    """获取数据库会话的生成器函数"""
    with _db_manager.session_scope() as session:
        yield session


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """获取会话上下文的便捷函数"""
    with _db_manager.session_scope() as session:
        yield session