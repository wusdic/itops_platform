"""
FastAPI应用入口
API网关层主入口
"""

import os
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from api.routes import (
    monitoring_router,
    workorder_router,
    knowledge_router,
    report_router,
    report_templates_router,
    report_generate_router,
    report_schedule_router,
    asset_router,
    ai_router,
    admin_router,
    notification_router,
    device_router,
    auth_router,
)
from api.dependencies import get_settings
from api.middleware.logging import LoggingMiddleware
from api.middleware.error_handler import ErrorHandlerMiddleware
from api.middleware.performance import PerformanceMiddleware
from api.middleware.request_id import RequestIDMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    应用生命周期管理
    启动时初始化服务，关闭时清理资源
    """
    logger.info("Starting ITOps Platform API Gateway...")
    
    # 初始化数据库
    try:
        from modules.foundation.db_models.base import init_db
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
    
    # 初始化其他服务
    try:
        settings = get_settings()
        logger.info(f"Environment: {settings.ENVIRONMENT}")
    except Exception as e:
        logger.warning(f"Settings initialization skipped: {e}")
    
    logger.info("ITOps Platform API Gateway started successfully")
    
    yield
    
    # 关闭时清理资源
    logger.info("Shutting down ITOps Platform API Gateway...")
    try:
        from modules.foundation.db_models.base import close_db
        close_db()
    except Exception as e:
        logger.warning(f"Database cleanup skipped: {e}")
    
    logger.info("ITOps Platform API Gateway stopped")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例
    """
    app = FastAPI(
        title="ITOps Platform API",
        description="智能化运维平台API网关",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # 添加CORS中间件
    # CORS配置从环境变量读取，支持环境变量覆盖
    settings = get_settings()
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    cors_origins = cors_origins_env.split(",") if cors_origins_env else settings.CORS_ORIGINS
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # 添加GZip压缩中间件
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 添加自定义中间件
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    
    # 注册路由
    app.include_router(
        monitoring_router,
        prefix="/api/v1/monitoring",
        tags=["监控管理"],
    )
    
    app.include_router(
        workorder_router,
        prefix="/api/v1/workorders",
        tags=["工单管理"],
    )
    
    app.include_router(
        knowledge_router,
        prefix="/api/v1/knowledge",
        tags=["知识库"],
    )
    
    app.include_router(
        report_router,
        prefix="/api/v1/report",
        tags=["报表管理"],
    )
    
    app.include_router(
        report_templates_router,
        prefix="/api/v1/report/templates",
        tags=["报告模板管理"],
    )
    
    app.include_router(
        report_generate_router,
        prefix="/api/v1/report/generate",
        tags=["报告生成"],
    )
    
    app.include_router(
        report_schedule_router,
        prefix="/api/v1/report/schedule",
        tags=["定时报告"],
    )
    
    app.include_router(
        asset_router,
        prefix="/api/v1/assets",
        tags=["资产管理"],
    )
    
    app.include_router(
        ai_router,
        prefix="/api/v1/ai",
        tags=["AI助手"],
    )
    
    app.include_router(
        admin_router,
        prefix="/api/v1/admin",
        tags=["系统管理"],
    )
    
    app.include_router(
        notification_router,
        prefix="/api/v1/notifications",
        tags=["通知渠道"],
    )

    app.include_router(
        device_router,
        prefix="/api/v1/devices",
        tags=["设备管理"],
    )

    app.include_router(
        auth_router,
        prefix="/api/v1/auth",
        tags=["认证"],
    )

    # 健康检查端点
    @app.get("/health", tags=["系统"])
    async def health_check():
        """健康检查接口"""
        return {
            "status": "healthy",
            "service": "itops-platform-api",
            "version": "1.0.0",
        }
    
    @app.get("/ready", tags=["系统"])
    async def readiness_check():
        """就绪检查接口"""
        # 可以添加更多依赖检查
        return {
            "status": "ready",
            "service": "itops-platform-api",
        }
    
    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理器"""
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": str(exc),
                "path": str(request.url),
            },
        )
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
