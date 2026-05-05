"""
API路由模块
"""

from fastapi import APIRouter

from .monitoring import router as monitoring_router
from .workorder import router as workorder_router
from .knowledge import router as knowledge_router
from .report import router as report_router
from .report_templates_api import router as report_templates_router
from .report_generate_api import router as report_generate_router
from .report_schedule_api import router as report_schedule_router
from .asset import router as asset_router
from .ai import router as ai_router
from .admin import router as admin_router
from .notification import router as notification_router
from .device_api import router as device_router
from .auth import router as auth_router

__all__ = [
    "monitoring_router",
    "workorder_router",
    "knowledge_router",
    "report_router",
    "report_templates_router",
    "report_generate_router",
    "report_schedule_router",
    "asset_router",
    "ai_router",
    "admin_router",
    "notification_router",
    "device_router",
    "auth_router",
]