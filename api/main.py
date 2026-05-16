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
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import (
    monitoring_router,
    workorder_router,
    knowledge_router,
    report_router,
    inspection_router,
    asset_router,
    ai_router,
    admin_router,
    notification_router,
    device_router,
    device_metrics_router,
    device_import_router,
    auth_router,
    discovery_router,
    automation_router,
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

    # 初始化AI（LLM客户端）
    try:
        from api.start import init_ai
        ai_result = init_ai({})
        if ai_result:
            logger.info("AI (LLM) initialized successfully")
        else:
            logger.warning("AI initialization returned None (disabled or failed)")
    except Exception as e:
        logger.warning(f"AI initialization skipped: {e}")
    
    # 启动设备定时采集任务
    periodic_collect_task = None
    try:
        from modules.collection.device_manager import get_device_manager
        import asyncio
        
        manager = get_device_manager()
        # 从配置获取采集间隔，默认60秒
        interval = 60
        try:
            from modules.collection.config_loader import get_config_loader
            loader = get_config_loader()
            interval = loader.get_global_config('collect.default_interval') or 60
        except Exception:
            pass
        
        # 启动定时采集为后台任务
        periodic_collect_task = asyncio.create_task(
            manager.start_periodic_collect(interval=interval)
        )
        logger.info(f"设备定时采集任务已启动 (间隔: {interval}秒)")
    except Exception as e:
        logger.warning(f"设备定时采集任务启动失败: {e}")
    
    logger.info("ITOps Platform API Gateway started successfully")
    
    yield
    
    # 关闭时清理资源
    logger.info("Shutting down ITOps Platform API Gateway...")
    
    # 停止定时采集任务
    if periodic_collect_task:
        try:
            from modules.collection.device_manager import get_device_manager
            manager = get_device_manager()
            manager.stop()
            periodic_collect_task.cancel()
            logger.info("设备定时采集任务已停止")
        except Exception as e:
            logger.warning(f"停止设备定时采集任务失败: {e}")
    
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
        inspection_router,
        prefix="/api/v1/inspection",
        tags=["巡检管理"],
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
        prefix="",
        tags=["设备管理"],
    )

    app.include_router(
        device_metrics_router,
        prefix="/api/v1/devices",
        tags=["采集精细化开关"],
    )

    app.include_router(
        device_import_router,
        prefix="/api/v1/devices",
        tags=["设备批量导入"],
    )

    app.include_router(
        auth_router,
        prefix="/api/v1/auth",
        tags=["认证"],
    )

    app.include_router(
        discovery_router,
        prefix="/api/v1/discovery",
        tags=["设备发现"],
    )

    app.include_router(
        automation_router,
        prefix="/api/v1/automation",
        tags=["自动化触发"],
    )

    # 前端静态文件服务 - 使用中间件方式避免路由冲突
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    if os.path.exists(dist_path):
        @app.middleware("static_files")
        async def static_files_middleware(request: Request, call_next):
            path = request.url.path
            
            # 拦截 /assets/* 请求
            if path.startswith("/assets/"):
                file_path = os.path.join(dist_path, path.lstrip("/"))
                if os.path.isfile(file_path):
                    return FileResponse(file_path)
            
            response = await call_next(request)
            return response
        
        @app.get("/")
        async def serve_index():
            return FileResponse(os.path.join(dist_path, "index.html"))
        
        # SPA fallback路由 - 必须放在API路由之后，处理所有HTTP方法
        @app.get("/{path:path}")
        async def serve_spa_get(path: str):
            if path.startswith("api/"):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(os.path.join(dist_path, "index.html"))

        @app.post("/{path:path}")
        async def serve_spa_post(path: str):
            if path.startswith("api/"):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(os.path.join(dist_path, "index.html"))

        @app.put("/{path:path}")
        async def serve_spa_put(path: str):
            if path.startswith("api/"):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(os.path.join(dist_path, "index.html"))

        @app.delete("/{path:path}")
        async def serve_spa_delete(path: str):
            if path.startswith("api/"):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            return FileResponse(os.path.join(dist_path, "index.html"))
        
        logger.info(f"Frontend static files enabled at /assets/ from: {dist_path}")

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
