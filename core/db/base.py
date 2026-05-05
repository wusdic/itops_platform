# -*- coding: utf-8 -*-
"""
ITOps Platform - 核心数据库层
基于SQLAlchemy的数据库连接和会话管理
"""
import os
from contextlib import contextmanager
from typing import Generator, Optional
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Float,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    sessionmaker,
    Session,
    scoped_session,
)
from sqlalchemy.pool import QueuePool

Base = declarative_base()


class BaseModel(Base):
    """基础模型类"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class DatabaseManager:
    """数据库管理器 - 单例模式"""
    
    _instance = None
    _lock = __import__('threading').Lock()
    
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
        
        self._engine = None
        self._session_factory = None
        self._scoped_session = None
        self._config = {}
    
    def configure(
        self,
        host: str = "localhost",
        port: int = 3306,
        database: str = "itops",
        username: str = "root",
        password: str = "",
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_recycle: int = 3600,
        echo: bool = False
    ):
        """配置数据库连接"""
        self._config = {
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "password": password,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_recycle": pool_recycle,
            "echo": echo,
        }
        
        # 构建连接URL
        db_url = (
            f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
            f"?charset=utf8mb4"
        )
        
        # 创建引擎
        self._engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            echo=echo,
        )
        
        # 创建会话工厂
        self._session_factory = sessionmaker(bind=self._engine)
        self._scoped_session = scoped_session(self._session_factory)
    
    def configure_from_url(self, db_url: str, **kwargs):
        """从URL配置数据库"""
        self._engine = create_engine(db_url, pool_pre_ping=True, **kwargs)
        self._session_factory = sessionmaker(bind=self._engine)
        self._scoped_session = scoped_session(self._session_factory)
    
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self._engine)
    
    def drop_tables(self):
        """删除所有表"""
        Base.metadata.drop_all(self._engine)
    
    def get_session(self) -> Session:
        """获取会话"""
        return self._scoped_session()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """会话上下文管理器"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute(self, sql: str, params: dict = None):
        """执行原生SQL"""
        with self.get_session() as session:
            result = session.execute(sql, params or {})
            return result
    
    @property
    def engine(self):
        return self._engine


class DatabaseSession:
    """数据库会话辅助类"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self._db_manager = db_manager or DatabaseManager()
    
    def __enter__(self) -> Session:
        self._session = self._db_manager.get_session()
        return self._session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._session.rollback()
        else:
            self._session.commit()
        self._session.close()


def get_db_session() -> DatabaseSession:
    """获取数据库会话"""
    return DatabaseSession()
