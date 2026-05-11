"""
通知渠道API路由
"""

import logging
from typing import Optional, List
from datetime import datetime
import json
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from modules.business.notification import (
    NotificationType, NotificationConfig, NotificationMessage,
    get_notification_manager, NotificationManager,
)
from modules.foundation.db_models.notification.notification_model import NotificationLog
from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["通知渠道"])


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


# ============== 通知历史接口 ==============

@router.get("/history", summary="获取通知历史")
async def get_notification_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    channel_type: Optional[str] = Query(None, description="渠道类型过滤"),
    success: Optional[bool] = Query(None, description="发送成功过滤"),
    alert_level: Optional[str] = Query(None, description="告警级别过滤"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取通知发送历史记录"""
    query = db.query(NotificationLog)
    
    if channel_type:
        query = query.filter(NotificationLog.channel_type == channel_type)
    
    if success is not None:
        query = query.filter(NotificationLog.success == success)
    
    if alert_level:
        query = query.filter(NotificationLog.alert_level == alert_level)
    
    if start_date:
        query = query.filter(NotificationLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(NotificationLog.created_at <= end_date)
    
    total = query.count()
    
    logs = query.order_by(NotificationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": [
            {
                "id": log.id,
                "channel_id": log.channel_id,
                "channel_name": log.channel_name,
                "channel_type": log.channel_type,
                "title": log.title,
                "content": log.content,
                "recipients": log.recipients,
                "success": log.success,
                "error_message": log.error_message,
                "status_code": log.status_code,
                "alert_id": log.alert_id,
                "alert_level": log.alert_level,
                "duration_ms": log.duration_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ============== 通知目标规则接口 ==============

class NotificationTargetRuleCreate(BaseModel):
    """创建通知目标规则"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    rule_type: str = Field(..., description="规则类型: alert_level, device, category, custom")
    match_conditions: Optional[dict] = Field(None, description="匹配条件")
    notify_channels: List[str] = Field(..., description="通知渠道列表")
    notify_receivers: Optional[List[str]] = Field(None, description="通知接收人")
    notify_interval: int = Field(300, description="重复通知间隔(秒)")
    max_notify_count: int = Field(3, description="最大通知次数")
    escalation_config: Optional[dict] = Field(None, description="升级配置")
    suppress_enabled: bool = Field(False, description="是否启用抑制")
    suppress_until: Optional[datetime] = Field(None, description="抑制截止时间")
    time_windows: Optional[List[dict]] = Field(None, description="通知时段")
    priority: int = Field(100, description="优先级")


class NotificationTargetRuleUpdate(BaseModel):
    """更新通知目标规则"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    match_conditions: Optional[dict] = None
    notify_channels: Optional[List[str]] = None
    notify_receivers: Optional[List[str]] = None
    notify_interval: Optional[int] = None
    max_notify_count: Optional[int] = None
    escalation_config: Optional[dict] = None
    suppress_enabled: Optional[bool] = None
    suppress_until: Optional[datetime] = None
    time_windows: Optional[List[dict]] = None
    priority: Optional[int] = None


@router.get("/target-rules", summary="获取通知目标规则列表")
async def get_target_rules(
    rule_type: Optional[str] = Query(None, description="规则类型过滤"),
    enabled: Optional[bool] = Query(None, description="启用状态过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取通知目标规则列表"""
    from modules.business.notification.target_config import get_target_rule_service

    service = get_target_rule_service(db)
    rules = service.list_rules(
        rule_type=rule_type,
        enabled=enabled,
        page=pagination.page,
        page_size=pagination.page_size,
    )

    # 获取总数（不带分页）
    all_rules = service.list_rules(rule_type=rule_type, enabled=enabled)

    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "rule_type": r.rule_type,
                "match_conditions": json.loads(r.match_conditions) if r.match_conditions else None,
                "notify_channels": json.loads(r.notify_channels) if r.notify_channels else [],
                "notify_receivers": json.loads(r.notify_receivers) if r.notify_receivers else [],
                "notify_interval": r.notify_interval,
                "max_notify_count": r.max_notify_count,
                "escalation_config": json.loads(r.escalation_config) if r.escalation_config else None,
                "suppress_enabled": r.suppress_enabled,
                "suppress_until": r.suppress_until.isoformat() if r.suppress_until else None,
                "time_windows": json.loads(r.time_windows) if r.time_windows else None,
                "priority": r.priority,
                "enabled": r.enabled,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "created_by": r.created_by,
            }
            for r in rules
        ],
        "total": len(all_rules),
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/target-rules", summary="创建通知目标规则")
async def create_target_rule(
    rule: NotificationTargetRuleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的通知目标规则"""
    from modules.business.notification.target_config import get_target_rule_service

    service = get_target_rule_service(db)
    rule_data = rule.model_dump()
    rule_data["created_by"] = current_user.username

    try:
        db_rule = service.create_rule(rule_data)
        return {
            "id": db_rule.id,
            "name": db_rule.name,
            "message": "通知目标规则创建成功",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/target-rules/{rule_id}", summary="获取通知目标规则详情")
async def get_target_rule(
    rule_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定通知目标规则的详细信息"""
    from modules.business.notification.target_config import get_target_rule_service

    service = get_target_rule_service(db)
    rule = service.get_rule_by_id(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "match_conditions": json.loads(rule.match_conditions) if rule.match_conditions else None,
        "notify_channels": json.loads(rule.notify_channels) if rule.notify_channels else [],
        "notify_receivers": json.loads(rule.notify_receivers) if rule.notify_receivers else [],
        "notify_interval": rule.notify_interval,
        "max_notify_count": rule.max_notify_count,
        "escalation_config": json.loads(rule.escalation_config) if rule.escalation_config else None,
        "suppress_enabled": rule.suppress_enabled,
        "suppress_until": rule.suppress_until.isoformat() if rule.suppress_until else None,
        "time_windows": json.loads(rule.time_windows) if rule.time_windows else None,
        "priority": rule.priority,
        "enabled": rule.enabled,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        "created_by": rule.created_by,
        "updated_by": rule.updated_by,
    }


@router.put("/target-rules/{rule_id}", summary="更新通知目标规则")
async def update_target_rule(
    rule_id: int,
    rule_update: NotificationTargetRuleUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新通知目标规则"""
    from modules.business.notification.target_config import get_target_rule_service

    service = get_target_rule_service(db)
    update_data = rule_update.model_dump(exclude_unset=True)
    update_data["updated_by"] = current_user.username

    try:
        service.update_rule(rule_id, update_data)
        return {"status": "success", "message": "规则更新成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/target-rules/{rule_id}", summary="删除通知目标规则")
async def delete_target_rule(
    rule_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除通知目标规则"""
    from modules.business.notification.target_config import get_target_rule_service

    service = get_target_rule_service(db)

    try:
        service.delete_rule(rule_id)
        return {"status": "success", "message": "规则删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/target-rules/{rule_id}/toggle", summary="启用/禁用通知目标规则")
async def toggle_target_rule(
    rule_id: int,
    enabled: bool = Query(..., description="是否启用"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """启用或禁用通知目标规则"""
    from modules.business.notification.target_config import get_target_rule_service

    service = get_target_rule_service(db)

    try:
        service.toggle_rule(rule_id, enabled=enabled, updated_by=current_user.username)
        return {"status": "success", "message": f"规则已{'启用' if enabled else '禁用'}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/target-rules/match", summary="匹配通知目标规则")
async def match_target_rules(
    alert_level: str = Query(..., description="告警级别"),
    device_id: Optional[int] = Query(None, description="设备ID"),
    device_name: Optional[str] = Query(None, description="设备名称"),
    device_type: Optional[str] = Query(None, description="设备类型"),
    category: Optional[str] = Query(None, description="告警分类"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据告警信息匹配通知目标规则"""
    from modules.business.notification.target_config import get_target_rule_service

    service = get_target_rule_service(db)
    matched_rules = service.match_rules(
        alert_level=alert_level,
        device_id=device_id,
        device_name=device_name,
        device_type=device_type,
        category=category,
    )

    return {
        "alert_level": alert_level,
        "matched_count": len(matched_rules),
        "matched_rules": matched_rules,
    }