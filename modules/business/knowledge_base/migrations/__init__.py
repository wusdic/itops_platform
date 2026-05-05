"""
BM-03 知识库数据库迁移
创建知识库相关的数据库表
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, JSON, Float, Enum as SQLEnum, Index, Table
)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime
import os

Base = declarative_base()


# 文档分类关联表(多对多)
document_tags = Table(
    'kb_document_tags',
    Base.metadata,
    Column('document_id', Integer, ForeignKey('kb_documents.id')),
    Column('tag_id', Integer, ForeignKey('kb_tags.id'))
)


def get_database_url(config: dict = None) -> str:
    """获取数据库URL"""
    if config and 'database' in config:
        db_config = config['database']
        db_type = db_config.get('type', 'sqlite')
        if db_type == 'sqlite':
            return db_config.get('path', './data/knowledge_base.db')
        elif db_type == 'mysql':
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', 3306)
            user = db_config.get('user', 'root')
            password = db_config.get('password', '')
            database = db_config.get('database', 'knowledge_base')
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        elif db_type == 'postgresql':
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', 5432)
            user = db_config.get('user', 'postgres')
            password = db_config.get('password', '')
            database = db_config.get('database', 'knowledge_base')
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    # 默认SQLite
    return 'sqlite:///./data/knowledge_base.db'


def create_tables(database_url: str = None):
    """
    创建所有知识库表
    
    Args:
        database_url: 数据库连接URL
    """
    if not database_url:
        database_url = get_database_url()
    
    # 确保目录存在
    if database_url.startswith('sqlite:///'):
        db_path = database_url.replace('sqlite:///', '')
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
    
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    return engine


def drop_tables(database_url: str = None):
    """
    删除所有知识库表(慎用)
    
    Args:
        database_url: 数据库连接URL
    """
    if not database_url:
        database_url = get_database_url()
    
    engine = create_engine(database_url)
    Base.metadata.drop_all(engine)


def upgrade(database_url: str = None):
    """升级数据库"""
    engine = create_engine(database_url or get_database_url())
    
    # 创建索引
    with engine.connect() as conn:
        # SOP文档索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sop_documents_status 
            ON kb_sop_documents(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sop_documents_category 
            ON kb_sop_documents(category_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sop_documents_author 
            ON kb_sop_documents(author)
        """)
        
        # 故障案例索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fault_cases_level 
            ON kb_fault_cases(fault_level)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fault_cases_status 
            ON kb_fault_cases(fault_status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fault_cases_category 
            ON kb_fault_cases(category_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fault_cases_occurrence 
            ON kb_fault_cases(occurrence_time)
        """)
        
        # 通用文档索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_type 
            ON kb_documents(doc_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_status 
            ON kb_documents(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_category 
            ON kb_documents(category_id)
        """)
        
        # 分块索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_doc 
            ON kb_document_chunks(document_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_sop 
            ON kb_document_chunks(sop_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_case 
            ON kb_document_chunks(fault_case_id)
        """)
        
        conn.commit()


def downgrade(database_url: str = None):
    """降级数据库"""
    engine = create_engine(database_url or get_database_url())
    
    with engine.connect() as conn:
        # 删除索引
        conn.execute("DROP INDEX IF EXISTS idx_sop_documents_status")
        conn.execute("DROP INDEX IF EXISTS idx_sop_documents_category")
        conn.execute("DROP INDEX IF EXISTS idx_sop_documents_author")
        conn.execute("DROP INDEX IF EXISTS idx_fault_cases_level")
        conn.execute("DROP INDEX IF EXISTS idx_fault_cases_status")
        conn.execute("DROP INDEX IF EXISTS idx_fault_cases_category")
        conn.execute("DROP INDEX IF EXISTS idx_fault_cases_occurrence")
        conn.execute("DROP INDEX IF EXISTS idx_documents_type")
        conn.execute("DROP INDEX IF EXISTS idx_documents_status")
        conn.execute("DROP INDEX IF EXISTS idx_documents_category")
        conn.execute("DROP INDEX IF EXISTS idx_document_chunks_doc")
        conn.execute("DROP INDEX IF EXISTS idx_document_chunks_sop")
        conn.execute("DROP INDEX IF EXISTS idx_document_chunks_case")
        
        conn.commit()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'create':
            print("Creating tables...")
            create_tables()
            print("Tables created successfully!")
        elif command == 'drop':
            print("Dropping tables...")
            drop_tables()
            print("Tables dropped successfully!")
        elif command == 'upgrade':
            print("Upgrading database...")
            upgrade()
            print("Database upgraded successfully!")
        elif command == 'downgrade':
            print("Downgrading database...")
            downgrade()
            print("Database downgraded successfully!")
        else:
            print(f"Unknown command: {command}")
            print("Available commands: create, drop, upgrade, downgrade")
    else:
        print("Creating tables by default...")
        create_tables()
        print("Tables created successfully!")
