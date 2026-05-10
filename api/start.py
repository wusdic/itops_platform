#!/usr/bin/env python3
"""
应用启动入口
负责加载配置、初始化服务、启动应用
"""

import os
import sys
import logging
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """
    加载应用配置
    优先从环境变量读取，其次从配置文件读取
    """
    config = {
        # 环境配置
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "true").lower() == "true",
        
        # 服务配置
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", "8000")),
        "workers": int(os.getenv("WORKERS", "1")),
        
        # 数据库配置
        "db_type": os.getenv("ITOPS_DB_TYPE", "mysql"),
        "db_host": os.getenv("ITOPS_DB_HOST", "localhost"),
        "db_port": int(os.getenv("ITOPS_DB_PORT", "3306")),
        "db_user": os.getenv("ITOPS_DB_USER", "root"),
        "db_password": os.getenv("ITOPS_DB_PASSWORD", ""),
        "db_name": os.getenv("ITOPS_DB_NAME", "itops_platform"),
        
        # Redis配置
        "redis_host": os.getenv("REDIS_HOST", "localhost"),
        "redis_port": int(os.getenv("REDIS_PORT", "6379")),
        "redis_db": int(os.getenv("REDIS_DB", "0")),
        
        # 监控配置
        "monitoring_enabled": os.getenv("MONITORING_ENABLED", "true").lower() == "true",
        
        # AI配置
        "ai_enabled": os.getenv("AI_ENABLED", "true").lower() == "true",
        "ai_model": os.getenv("AI_MODEL", "gpt-4"),
    }
    
    return config


def init_database(config: dict):
    """
    初始化数据库
    """
    try:
        from modules.foundation.db_models.base import init_db, DatabaseManager
        
        db_config = {
            "type": config["db_type"],
            "host": config["db_host"],
            "port": config["db_port"],
            "username": config["db_user"],
            "password": config["db_password"],
            "database": config["db_name"],
        }
        
        db_manager = init_db(db_config)
        db_manager.create_all()
        
        logger.info("Database initialized successfully")
        return db_manager
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        return None


def init_redis(config: dict):
    """
    初始化Redis连接
    """
    try:
        from modules.foundation.redis_client.redis_client import RedisClient
        
        redis_client = RedisClient(
            host=config["redis_host"],
            port=config["redis_port"],
            db=config["redis_db"],
        )
        
        logger.info("Redis initialized successfully")
        return redis_client
    except Exception as e:
        logger.warning(f"Redis initialization failed: {e}")
        return None


def init_monitoring(config: dict):
    """
    初始化监控组件
    """
    if not config.get("monitoring_enabled"):
        logger.info("Monitoring is disabled")
        return None
    
    try:
        # 初始化监控客户端
        # from modules.collection.api_collector.prometheus_client import PrometheusClient
        
        logger.info("Monitoring initialized successfully")
        return True
    except Exception as e:
        logger.warning(f"Monitoring initialization failed: {e}")
        return None


# 全局 LLM 客户端
_llm_client = None


def init_ai(config: dict):
    """
    初始化AI组件
    """
    global _llm_client

    # Fallback: 优先用 config，否则用环境变量
    ai_enabled = config.get("ai_enabled")
    if ai_enabled is None:
        ai_enabled = os.getenv("AI_ENABLED", "true").lower() == "true"

    if not ai_enabled:
        logger.info("AI is disabled")
        return None

    try:
        # 加载 AI Copilot 配置（YAML）
        import yaml

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        copilot_config_path = os.path.join(project_root, "config", "templates", "ai_copilot.yaml")

        ai_config = {"ollama": {}, "models": {"default": "qwen3.6-27b-q4-k-m"}, "conversation": {}}
        if os.path.exists(copilot_config_path):
            with open(copilot_config_path, "r") as f:
                loaded = yaml.safe_load(f) or {}
                ai_config["ollama"] = loaded.get("ollama", {})
                ai_config["models"] = loaded.get("models", {"default": "qwen3.6-27b-q4-k-m"})
                ai_config["conversation"] = loaded.get("conversation", {})

        # base_url 优先用 dev.yaml 里的 ai.base_url（运行时通过环境变量传入）
        # 检查环境变量或传入的 config
        base_url = os.getenv("AI_BASE_URL", "http://127.0.0.1:11434")
        model = os.getenv("AI_MODEL", ai_config["models"].get("default", "qwen3.6-27b-q4-k-m"))
        ai_config["ollama"]["base_url"] = base_url
        ai_config["models"]["default"] = model

        # 初始化 LLM 客户端
        from modules.business.ai_copilot.llm_client import init_llm_client
        _llm_client = init_llm_client(ai_config)
        logger.info(f"AI initialized successfully: base_url={base_url}, model={model}")
        return True
    except Exception as e:
        logger.warning(f"AI initialization failed: {e}")
        return None


def get_llm_client():
    """获取全局 LLM 客户端"""
    return _llm_client


def start_server(config: dict):
    """
    启动应用服务器
    """
    import uvicorn
    
    # 根据环境选择日志级别
    log_level = "debug" if config["debug"] else "info"
    
    logger.info(f"Starting server in {config['environment']} mode...")
    logger.info(f"Server will listen on {config['host']}:{config['port']}")
    
    uvicorn.run(
        "api.main:app",
        host=config["host"],
        port=config["port"],
        workers=config["workers"] if config["environment"] == "production" else 1,
        reload=config["debug"],
        log_level=log_level,
    )


def main():
    """
    主函数
    """
    logger.info("=" * 60)
    logger.info("ITOps Platform API Gateway Starting...")
    logger.info("=" * 60)
    
    # 加载配置
    config = load_config()
    logger.info(f"Environment: {config['environment']}")
    logger.info(f"Debug mode: {config['debug']}")
    
    # 初始化数据库
    db_manager = init_database(config)
    
    # 初始化Redis
    redis_client = init_redis(config)
    
    # 初始化监控
    init_monitoring(config)
    
    # 初始化AI
    init_ai(config)
    
    # 启动服务器
    logger.info("=" * 60)
    logger.info("Initialization complete. Starting server...")
    logger.info("=" * 60)
    
    start_server(config)


if __name__ == "__main__":
    main()
