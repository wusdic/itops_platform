"""
通知渠道API路由
"""

import logging
from typing import Optional, List
from datetime import datetime
import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from modules.business.notification import (
    NotificationType, NotificationConfig, NotificationMessage,
    get_notification_manager, NotificationManager,
    send_dingtalk_message, send_feishu_message, send_wechat_work_message,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["通知渠道"])


# ============ 请求模型 ============

class NotificationConfigCreate(BaseModel):
    """创建通知配置"""
    name: str = Field(..., description="配置名称")
    type: str = Field(..., description="类型: email, dingtalk, feishu, wechat_work, webhook")
    enabled: bool = True
    
    # 通用
    webhook_url: Optional[str] = None
    timeout: int = 30
    
    # 邮件
    smtp_host: Optional[str] = None
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = False
    from_email: Optional[str] = None
    from_name: str = "IT运维平台"
    
    # 钉钉/飞书/企微
    webhook_token: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    # 告警级别过滤
    alert_levels: List[str] = []


class NotificationConfigUpdate(BaseModel):
    """更新通知配置"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    timeout: Optional[int] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: Optional[bool] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    webhook_token: Optional[str] = None
    webhook_secret: Optional[str] = None
    alert_levels: Optional[List[str]] = None


class SendNotificationRequest(BaseModel):
    """发送通知请求"""
    type: str = Field(..., description="通知类型: dingtalk, feishu, wechat_work, webhook")
    webhook_url: str = Field(..., description="Webhook URL")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    recipients: List[str] = Field(default_factory=list, description="@人员手机号")


class SendAlertNotificationRequest(BaseModel):
    """发送告警通知请求"""
    alert_id: str
    title: str
    content: str
    level: str = "info"
    device_name: Optional[str] = None
    device_ip: Optional[str] = None


# ============ API端点 ============

@router.get("/channels", summary="获取所有通知渠道")
async def get_channels():
    """获取所有通知渠道配置"""
    manager = get_notification_manager()
    channels = []
    
    for config in manager.list_configs():
        channels.append({
            "id": config.id,
            "name": config.name,
            "type": config.type.value if isinstance(config.type, NotificationType) else config.type,
            "enabled": config.enabled,
            "webhook_url": config.webhook_url,
            "alert_levels": config.alert_levels,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        })
    
    return {"channels": channels, "total": len(channels)}


@router.get("/channels/{channel_id}", summary="获取单个通知渠道")
async def get_channel(channel_id: str):
    """获取指定通知渠道配置"""
    manager = get_notification_manager()
    config = manager.get_config(channel_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    
    return {
        "id": config.id,
        "name": config.name,
        "type": config.type.value if isinstance(config.type, NotificationType) else config.type,
        "enabled": config.enabled,
        "webhook_url": config.webhook_url,
        "timeout": config.timeout,
        "smtp_host": config.smtp_host,
        "smtp_port": config.smtp_port,
        "from_email": config.from_email,
        "from_name": config.from_name,
        "webhook_token": config.webhook_token,
        "alert_levels": config.alert_levels,
    }


@router.post("/channels", summary="创建通知渠道")
async def create_channel(config: NotificationConfigCreate):
    """创建新的通知渠道配置"""
    manager = get_notification_manager()
    
    notification_config = NotificationConfig(
        name=config.name,
        type=NotificationType(config.type),
        enabled=config.enabled,
        webhook_url=config.webhook_url,
        timeout=config.timeout,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_password=config.smtp_password,
        smtp_use_tls=config.smtp_use_tls,
        from_email=config.from_email,
        from_name=config.from_name,
        webhook_token=config.webhook_token,
        webhook_secret=config.webhook_secret,
        alert_levels=config.alert_levels,
    )
    
    channel_id = manager.add_config(notification_config)
    
    return {"id": channel_id, "message": "创建成功"}


@router.put("/channels/{channel_id}", summary="更新通知渠道")
async def update_channel(channel_id: str, config: NotificationConfigUpdate):
    """更新通知渠道配置"""
    manager = get_notification_manager()
    
    existing = manager.get_config(channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    
    # 更新字段
    update_data = config.model_dump(exclude_unset=True)
    
    if update_data.get('type'):
        update_data['type'] = NotificationType(update_data['type'])
    
    for key, value in update_data.items():
        if hasattr(existing, key) and value is not None:
            setattr(existing, key, value)
    
    manager.update_config(existing)
    
    return {"message": "更新成功"}


@router.delete("/channels/{channel_id}", summary="删除通知渠道")
async def delete_channel(channel_id: str):
    """删除通知渠道配置"""
    manager = get_notification_manager()
    
    existing = manager.get_config(channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    
    manager.delete_config(channel_id)
    
    return {"message": "删除成功"}


@router.post("/send", summary="发送通知")
async def send_notification(request: SendNotificationRequest):
    """发送通知消息"""
    notification_type = NotificationType(request.type)
    
    try:
        if notification_type == NotificationType.DINGTALK:
            success = await send_dingtalk_message(
                request.webhook_url,
                request.title,
                request.content,
                request.recipients
            )
        elif notification_type == NotificationType.FEISHU:
            success = await send_feishu_message(
                request.webhook_url,
                request.title,
                request.content
            )
        elif notification_type == NotificationType.WECHAT_WORK:
            success = await send_wechat_work_message(
                request.webhook_url,
                request.title,
                request.content
            )
        elif notification_type == NotificationType.WEBHOOK:
            manager = get_notification_manager()
            message = NotificationMessage(
                type=notification_type,
                recipients=[],
                title=request.title,
                content=request.content,
            )
            manager._configs['temp'] = NotificationConfig(
                id='temp',
                name='temp',
                type=notification_type,
                webhook_url=request.webhook_url
            )
            success = await manager._sender.send(message)
        else:
            raise HTTPException(status_code=400, detail="不支持的通知类型")
        
        return {"success": success, "message": "发送成功" if success else "发送失败"}
    
    except Exception as e:
        logger.error(f"发送通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert", summary="发送告警通知")
async def send_alert_notification(request: SendAlertNotificationRequest):
    """通过已配置渠道发送告警通知"""
    manager = get_notification_manager()
    
    # 创建模拟告警对象
    class Alert:
        id = request.alert_id
        title = request.title
        message = request.content
        level = request.level
        device_name = request.device_name
        device_ip = request.device_ip
    
    results = await manager.send_alert_notification(Alert())
    
    return {
        "success": any(results),
        "results": results,
        "message": f"发送完成，成功 {sum(results)}/{len(results)}"
    }


@router.get("/types", summary="获取通知类型列表")
async def get_notification_types():
    """获取支持的的通知类型"""
    return {
        "types": [
            {"value": "email", "label": "邮件", "description": "通过SMTP发送邮件"},
            {"value": "dingtalk", "label": "钉钉", "description": "钉钉群机器人"},
            {"value": "feishu", "label": "飞书", "description": "飞书群机器人"},
            {"value": "wechat_work", "label": "企业微信", "description": "企业微信群机器人"},
            {"value": "webhook", "label": "Webhook", "description": "通用HTTP回调"},
        ]
    }


@router.post("/test/{channel_id}", summary="测试通知渠道")
async def test_channel(channel_id: str):
    """测试通知渠道配置"""
    manager = get_notification_manager()
    config = manager.get_config(channel_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="通知渠道不存在")
    
    message = NotificationMessage(
        type=config.type,
        recipients=config.webhook_token.split(",") if config.webhook_token else [],
        title="[测试] IT运维平台通知渠道测试",
        content="这是一条测试消息，用于验证通知渠道配置是否正确。\n\n如果收到此消息，说明配置成功！",
        alert_level="info",
    )
    
    success = await manager._sender.send(message)
    
    return {
        "success": success,
        "message": "测试消息发送成功" if success else "测试消息发送失败，请检查配置"
    }