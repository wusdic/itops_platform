"""
监控管理API路由
提供监控数据采集、告警管理、指标查询等接口
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.alert import Alert, AlertLevel, AlertStatus, AlertCategory
from modules.foundation.db_models.monitoring import PerformanceMetric, DeviceMetricConfig
from modules.foundation.db_models.device import Device


router = APIRouter()
logger = logging.getLogger(__name__)


# ============== 请求/响应模型 ==============

class MetricQuery(BaseModel):
    """指标查询请求"""
    metric_name: Optional[str] = Field(None, description="指标名称（支持 cpu_usage/memory_usage/disk_usage）")
    metric_type: Optional[str] = Field(None, description="指标类型（cpu/memory/disk），会自动映射为 metric_name")
    device_id: Optional[int] = Field(None, description="设备ID")
    host: Optional[str] = Field(None, description="主机名/IP")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    step: Optional[int] = Field(60, description="采样间隔(秒)")


class MetricPoint(BaseModel):
    """指标数据点"""
    timestamp: datetime
    value: float


class MetricData(BaseModel):
    """指标数据"""
    metric: str
    host: str
    points: List[MetricPoint]


class AlertCreate(BaseModel):
    """创建告警请求"""
    title: str = Field(..., description="告警标题")
    severity: str = Field(..., description="严重程度: critical, high, medium, low, info")
    description: str = Field(None, description="告警描述")
    host: Optional[str] = Field(None, description="关联主机")
    metric_name: Optional[str] = Field(None, description="关联指标")
    threshold: Optional[float] = Field(None, description="触发阈值")
    current_value: Optional[float] = Field(None, description="当前值")


class AlertResponse(BaseModel):
    """告警响应"""
    id: int
    title: str
    severity: str
    status: str
    host: Optional[str] = None
    created_at: datetime
    updated_at: datetime


def _alert_to_dict(alert: Alert) -> dict:
    """告警转字典"""
    return {
        'id': alert.id,
        'alert_key': alert.alert_key,
        'device_id': alert.device_id,
        'device_name': alert.device_name,
        'device_ip': alert.device_ip,
        'level': alert.level.value if alert.level else 'info',
        'category': alert.category.value if alert.category else None,
        'title': alert.title,
        'message': alert.message,
        'metric_name': alert.metric_name,
        'metric_value': alert.metric_value,
        'threshold': alert.threshold,
        'unit': alert.unit,
        'status': alert.status.value if alert.status else 'active',
        'first_occurred_at': alert.first_occurred_at.isoformat() if alert.first_occurred_at else None,
        'occurred_at': alert.occurred_at.isoformat() if alert.occurred_at else None,
        'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
        'acknowledged_by': alert.acknowledged_by,
        'resolved_by': alert.resolved_by,
        'resolution_note': alert.resolution_note,
        'created_at': alert.created_at.isoformat() if alert.created_at else None,
        'updated_at': alert.updated_at.isoformat() if alert.updated_at else None,
    }


# ============== 监控接口 ==============

@router.get("/metrics", summary="查询监控指标")
async def query_metrics(
    metric_name: Optional[str] = Query(None, description="指标名称，不传则返回指标列表"),
    device_id: Optional[int] = Query(None, description="设备ID"),
    host: Optional[str] = Query(None, description="主机名/IP"),
    start: Optional[datetime] = Query(None, description="开始时间"),
    end: Optional[datetime] = Query(None, description="结束时间"),
    step: int = Query(60, description="采样间隔(秒)"),
    limit: int = Query(1000, le=10000, description="返回点数限制"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    从数据库查询监控指标数据
    返回时序数据点列表
    """
    # 如果没有指定时间范围，默认查询最近24小时
    if not end:
        end = datetime.now()
    if not start:
        start = end - timedelta(hours=24)
    
    # 构建查询
    query = db.query(PerformanceMetric).filter(
        PerformanceMetric.timestamp >= start,
        PerformanceMetric.timestamp <= end
    )
    
    if metric_name:
        query = query.filter(PerformanceMetric.metric_name == metric_name)
    
    if device_id:
        query = query.filter(PerformanceMetric.device_id == device_id)
    
    if host:
        query = query.filter(
            or_(
                PerformanceMetric.device_name.ilike(f"%{host}%"),
                PerformanceMetric.device_ip == host
            )
        )
    
    # 按时间和设备分组，取最近的数据点
    query = query.order_by(PerformanceMetric.timestamp.desc())
    
    metrics = query.limit(limit).all()
    
    # 按设备和指标分组返回
    result = {}
    for m in metrics:
        key = f"{m.device_name}:{m.metric_name}"
        if key not in result:
            result[key] = {
                'metric': m.metric_name,
                'host': m.device_name,
                'device_ip': m.device_ip,
                'category': m.metric_category,
                'unit': m.metric_unit,
                'points': []
            }
        result[key]['points'].append({
            'timestamp': m.timestamp.isoformat(),
            'value': m.value
        })
    
    return {
        'metrics': list(result.values()),
        'count': len(result),
        'start': start.isoformat(),
        'end': end.isoformat()
    }


@router.post("/metrics/collect", summary="手动采集设备指标")
async def collect_device_metrics(
    device_id: int = Query(..., description="设备ID"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    手动触发设备指标采集
    使用DeviceManager进行实时采集，数据存入数据库
    """
    # 获取设备信息
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    try:
        # 使用DeviceManager采集数据
        from modules.collection.device_manager import DeviceManager
        
        manager = DeviceManager()
        result = await manager.collect_device(device.hostname or device.name)
        
        if result and result.status.value == 'online':
            # 将采集的数据存入数据库
            stored_count = 0
            metrics_data = result.metrics
            
            # 存储CPU指标
            if 'cpu' in metrics_data:
                cpu_data = metrics_data['cpu']
                if 'usage' in cpu_data:
                    metric = PerformanceMetric(
                        device_id=device.id,
                        device_name=device.name,
                        device_ip=device.ip_address,
                        device_type=device.device_type.value if device.device_type else None,
                        metric_category='cpu',
                        metric_name='cpu_usage',
                        metric_unit='%',
                        value=cpu_data['usage'],
                        timestamp=datetime.now(),
                        collected_by=current_user.username,
                        source='ssh'
                    )
                    db.add(metric)
                    stored_count += 1
            
            # 存储内存指标
            if 'memory' in metrics_data:
                mem_data = metrics_data['memory']
                for key in ['total_mb', 'used_mb', 'available_mb', 'usage_percent']:
                    if key in mem_data:
                        metric = PerformanceMetric(
                            device_id=device.id,
                            device_name=device.name,
                            device_ip=device.ip_address,
                            device_type=device.device_type.value if device.device_type else None,
                            metric_category='memory',
                            metric_name=key,
                            metric_unit='MB' if 'mb' in key else '%',
                            value=mem_data[key],
                            timestamp=datetime.now(),
                            collected_by=current_user.username,
                            source='ssh'
                        )
                        db.add(metric)
                        stored_count += 1
            
            # 存储磁盘指标
            if 'disks' in metrics_data:
                for disk in metrics_data['disks']:
                    if 'usage_percent' in disk:
                        metric = PerformanceMetric(
                            device_id=device.id,
                            device_name=device.name,
                            device_ip=device.ip_address,
                            device_type=device.device_type.value if device.device_type else None,
                            metric_category='disk',
                            metric_name='disk_usage',
                            metric_unit='%',
                            value=float(disk['usage_percent']),
                            tags=json.dumps({'mount_point': disk.get('mounted_on', ''), 'filesystem': disk.get('filesystem', '')}),
                            timestamp=datetime.now(),
                            collected_by=current_user.username,
                            source='ssh'
                        )
                        db.add(metric)
                        stored_count += 1
            
            db.commit()
            
            return {
                'status': 'success',
                'device_id': device_id,
                'device_name': device.name,
                'metrics_collected': stored_count,
                'message': f'成功采集{stored_count}条指标数据'
            }
        else:
            return {
                'status': 'error',
                'device_id': device_id,
                'message': f'设备采集失败: {result.error if result else "未知错误"}'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'device_id': device_id,
            'message': f'采集异常: {str(e)}'
        }


@router.get("/metrics/hosts", summary="获取已监控主机列表")
async def get_monitored_hosts(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取已采集过指标的主机列表"""
    # 从指标表中获取有数据的主机
    hosts = db.query(
        PerformanceMetric.device_name,
        PerformanceMetric.device_ip,
        PerformanceMetric.device_type,
        func.max(PerformanceMetric.timestamp).label('last_collect')
    ).group_by(
        PerformanceMetric.device_name,
        PerformanceMetric.device_ip,
        PerformanceMetric.device_type
    ).all()
    
    return {
        "hosts": [
            {
                "name": h.device_name,
                "ip": h.device_ip,
                "type": h.device_type,
                "last_collect": h.last_collect.isoformat() if h.last_collect else None
            }
            for h in hosts
        ]
    }


@router.get("/metrics/available", summary="获取可用指标列表")
async def get_available_metrics(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取系统中已采集过的指标类型列表"""
    metrics = db.query(
        PerformanceMetric.metric_category,
        PerformanceMetric.metric_name,
        PerformanceMetric.metric_unit
    ).distinct().all()
    
    # 按类别分组
    categories = {}
    for m in metrics:
        if m.metric_category not in categories:
            categories[m.metric_category] = []
        categories[m.metric_category].append({
            'name': m.metric_name,
            'unit': m.metric_unit
        })
    
    return {
        "categories": [
            {'category': cat, 'metrics': items}
            for cat, items in categories.items()
        ]
    }


@router.post("/metrics/query", summary="PromQL风格查询")
async def promql_query(
    query: MetricQuery,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    PromQL风格的指标查询
    支持 metric_name（cpu_usage/memory_usage/disk_usage）或 metric_type（cpu/memory/disk）查询
    """
    # 映射 metric_type 到 metric_name
    TYPE_TO_NAME = {
        'cpu': 'cpu_usage',
        'memory': 'memory_usage',
        'disk': 'disk_usage',
        'network': 'network_in',
        'load': 'load_1m',
    }
    metric_name = query.metric_name
    if not metric_name and query.metric_type:
        metric_name = TYPE_TO_NAME.get(query.metric_type.lower() if query.metric_type else '', query.metric_type)

    if not query.start_time:
        query.start_time = datetime.now() - timedelta(hours=24)
    if not query.end_time:
        query.end_time = datetime.now()

    query_db = db.query(PerformanceMetric)

    if metric_name:
        query_db = query_db.filter(PerformanceMetric.metric_name == metric_name)

    query_db = query_db.filter(
        PerformanceMetric.timestamp >= query.start_time,
        PerformanceMetric.timestamp <= query.end_time
    )

    if query.device_id:
        query_db = query_db.filter(PerformanceMetric.device_id == query.device_id)

    if query.host:
        query_db = query_db.filter(
            or_(
                PerformanceMetric.device_name.ilike(f"%{query.host}%"),
                PerformanceMetric.device_ip == query.host
            )
        )

    metrics = query_db.order_by(PerformanceMetric.timestamp.desc()).limit(1000).all()

    return {
        "status": "success",
        "metric": metric_name or "all",
        "data": {"values": [{"timestamp": m.timestamp.isoformat(), "value": m.value} for m in metrics]},
        "points": [
            {"timestamp": m.timestamp.isoformat(), "value": m.value, "host": m.device_name}
            for m in metrics
        ]
    }


# ============== 告警接口 ==============

@router.get("/alerts", summary="获取告警列表")
async def get_alerts(
    status_filter: Optional[str] = Query(None, alias="status", description="状态过滤"),
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    host: Optional[str] = Query(None, description="主机过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取告警列表"""
    query = db.query(Alert)
    
    if status_filter:
        try:
            status_enum = AlertStatus(status_filter)
            query = query.filter(Alert.status == status_enum)
        except ValueError:
            pass
    
    if severity:
        try:
            level_enum = AlertLevel(severity)
            query = query.filter(Alert.level == level_enum)
        except ValueError:
            pass
    
    if host:
        query = query.filter(
            or_(
                Alert.device_name.ilike(f"%{host}%"),
                Alert.device_ip.ilike(f"%{host}%"),
            )
        )
    
    total = query.count()
    alerts = query.order_by(Alert.occurred_at.desc()).offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [_alert_to_dict(a) for a in alerts],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/alerts", summary="创建告警")
async def create_alert(
    alert: AlertCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建告警记录"""
    try:
        level_enum = AlertLevel(alert.severity)
    except ValueError:
        level_enum = AlertLevel.INFO
    
    db_alert = Alert(
        alert_key=f"{alert.host or 'system'}-{alert.metric_name or 'unknown'}-{int(datetime.now().timestamp())}",
        device_name=alert.host,
        level=level_enum,
        title=alert.title,
        message=alert.description,
        metric_name=alert.metric_name,
        metric_value=str(alert.current_value) if alert.current_value else None,
        threshold=str(alert.threshold) if alert.threshold else None,
        status=AlertStatus.ACTIVE,
        occurred_at=datetime.now(),
        first_occurred_at=datetime.now(),
    )
    
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    
    # 创建审计日志
    try:
        from modules.business.monitoring.alert_audit_service import AlertAuditService, AuditAction
        audit_service = AlertAuditService(db)
        audit_service.create_log(
            alert_id=db_alert.id,
            action=AuditAction.CREATE,
            alert_key=db_alert.alert_key,
            operator=current_user.username,
            field_name="status",
            old_value=None,
            new_value=AlertStatus.ACTIVE.value,
            reason="创建告警",
        )
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")
    
    return {
        "id": db_alert.id,
        "title": db_alert.title,
        "severity": db_alert.level.value,
        "status": db_alert.status.value,
        "created_at": db_alert.created_at.isoformat(),
    }


@router.get("/alerts/{alert_id}", summary="获取告警详情")
async def get_alert(
    alert_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定告警的详细信息"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    return _alert_to_dict(alert)


@router.put("/alerts/{alert_id}/acknowledge", summary="确认告警")
async def acknowledge_alert(
    alert_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """确认告警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    old_status = alert.status
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = current_user.username
    alert.acknowledged_at = datetime.now()
    alert.updated_at = datetime.now()
    db.commit()
    
    # 创建审计日志
    try:
        from modules.business.monitoring.alert_audit_service import AlertAuditService, AuditAction
        audit_service = AlertAuditService(db)
        audit_service.create_status_change_log(
            alert_id=alert_id,
            old_status=old_status,
            new_status=AlertStatus.ACKNOWLEDGED,
            operator=current_user.username,
            reason="确认告警",
        )
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")
    
    return {"status": "success", "message": "Alert acknowledged"}


@router.put("/alerts/{alert_id}/resolve", summary="解决告警")
async def resolve_alert(
    alert_id: int,
    resolution: str = Query("", description="解决方案描述"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解决告警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    old_status = alert.status
    alert.status = AlertStatus.RESOLVED
    alert.resolved_by = current_user.username
    alert.resolved_at = datetime.now()
    alert.resolution_note = resolution
    alert.updated_at = datetime.now()
    db.commit()
    
    # 创建审计日志
    try:
        from modules.business.monitoring.alert_audit_service import AlertAuditService, AuditAction
        audit_service = AlertAuditService(db)
        audit_service.create_status_change_log(
            alert_id=alert_id,
            old_status=old_status,
            new_status=AlertStatus.RESOLVED,
            operator=current_user.username,
            reason=resolution,
        )
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")
    
    return {"status": "success", "message": "Alert resolved"}


@router.delete("/alerts/{alert_id}", summary="删除告警")
async def delete_alert(
    alert_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除告警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    # 创建审计日志（在删除前）
    try:
        from modules.business.monitoring.alert_audit_service import AlertAuditService, AuditAction
        audit_service = AlertAuditService(db)
        audit_service.create_log(
            alert_id=alert_id,
            action=AuditAction.DELETE,
            alert_key=alert.alert_key,
            operator=current_user.username,
            reason="删除告警",
        )
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")
    
    db.delete(alert)
    db.commit()
    
    return {"status": "success", "message": "Alert deleted"}


# ============== 告警审计日志接口 ==============

class AlertAuditLogCreate(BaseModel):
    """创建告警审计日志"""
    action: str = Field(..., description="操作类型")
    field_name: Optional[str] = Field(None, description="字段名")
    old_value: Optional[str] = Field(None, description="旧值")
    new_value: Optional[str] = Field(None, description="新值")
    reason: Optional[str] = Field(None, description="原因")


class AlertAuditLogResponse(BaseModel):
    """告警审计日志响应"""
    id: int
    alert_id: int
    alert_key: Optional[str] = None
    action: str
    operator: Optional[str] = None
    operator_ip: Optional[str] = None
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    workorder_id: Optional[int] = None
    created_at: datetime


@router.get("/alerts/{alert_id}/audit-logs", summary="获取告警审计日志")
async def get_alert_audit_logs(
    alert_id: int,
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定告警的所有审计日志"""
    from modules.foundation.db_models.alert import AlertAuditLog

    query = db.query(AlertAuditLog).filter(AlertAuditLog.alert_id == alert_id)

    total = query.count()
    logs = query.order_by(AlertAuditLog.created_at.desc()).offset(pagination.offset).limit(pagination.limit).all()

    return {
        "items": [
            {
                "id": log.id,
                "alert_id": log.alert_id,
                "alert_key": log.alert_key,
                "action": log.action,
                "operator": log.operator,
                "operator_ip": log.operator_ip,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "reason": log.reason,
                "workorder_id": log.workorder_id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/alerts/{alert_id}/audit-logs", summary="创建告警审计日志")
async def create_alert_audit_log(
    alert_id: int,
    audit_log: AlertAuditLogCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """为告警创建审计日志记录"""
    from modules.foundation.db_models.alert import AlertAuditLog

    # 检查告警是否存在
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    # 创建审计日志
    db_audit_log = AlertAuditLog(
        alert_id=alert_id,
        alert_key=alert.alert_key,
        action=audit_log.action,
        operator=current_user.username,
        field_name=audit_log.field_name,
        old_value=audit_log.old_value,
        new_value=audit_log.new_value,
        reason=audit_log.reason,
    )

    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)

    return {
        "id": db_audit_log.id,
        "alert_id": db_audit_log.alert_id,
        "action": db_audit_log.action,
        "operator": db_audit_log.operator,
        "created_at": db_audit_log.created_at.isoformat() if db_audit_log.created_at else None,
    }


@router.get("/audit-logs", summary="获取告警审计日志列表")
async def get_audit_logs(
    alert_id: Optional[int] = Query(None, description="告警ID过滤"),
    action: Optional[str] = Query(None, description="操作类型过滤"),
    operator: Optional[str] = Query(None, description="操作人过滤"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取所有告警审计日志（支持多条件过滤）"""
    from modules.foundation.db_models.alert import AlertAuditLog

    query = db.query(AlertAuditLog)

    if alert_id:
        query = query.filter(AlertAuditLog.alert_id == alert_id)

    if action:
        query = query.filter(AlertAuditLog.action == action)

    if operator:
        query = query.filter(AlertAuditLog.operator == operator)

    if start_date:
        query = query.filter(AlertAuditLog.created_at >= start_date)

    if end_date:
        query = query.filter(AlertAuditLog.created_at <= end_date)

    total = query.count()
    logs = query.order_by(AlertAuditLog.created_at.desc()).offset(pagination.offset).limit(pagination.limit).all()

    return {
        "items": [
            {
                "id": log.id,
                "alert_id": log.alert_id,
                "alert_key": log.alert_key,
                "action": log.action,
                "operator": log.operator,
                "operator_ip": log.operator_ip,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "reason": log.reason,
                "workorder_id": log.workorder_id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


# ============== 告警规则接口 ==============

@router.get("/rules", summary="获取告警规则列表")
async def get_alert_rules(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取告警规则列表"""
    from modules.foundation.db_models.alert import AlertRule
    rules = db.query(AlertRule).all()
    
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "metric_name": r.metric_name,
                "expression": r.expression,
                "threshold_value": r.threshold_value,
                "comparison": r.comparison,
                "level": r.level.value if r.level else 'medium',
                "enabled": r.enabled,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rules
        ],
        "total": len(rules)
    }


@router.get("/rules/{rule_id}", summary="获取告警规则详情")
async def get_alert_rule(
    rule_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取告警规则详情"""
    from modules.foundation.db_models.alert import AlertRule
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="告警规则不存在")
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "category": rule.category.value if rule.category else None,
        "expression": rule.expression,
        "level": rule.level.value if rule.level else 'medium',
        "enabled": rule.enabled,
        "threshold_value": rule.threshold_value,
        "comparison": rule.comparison,
        "duration_seconds": rule.duration_seconds,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
    }


# ============== 监控视图接口 ==============

@router.get("/dashboards", summary="获取监控仪表盘列表")
async def get_dashboards(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取监控仪表盘列表"""
    # 从数据库获取有数据的主机作为仪表盘
    hosts = db.query(
        PerformanceMetric.device_name,
        PerformanceMetric.device_ip,
        func.count(PerformanceMetric.id).label('metric_count'),
        func.max(PerformanceMetric.timestamp).label('last_update')
    ).group_by(
        PerformanceMetric.device_name,
        PerformanceMetric.device_ip
    ).all()
    
    dashboards = [
        {
            "id": idx + 1,
            "name": f"{h.device_name} 概览",
            "type": "device",
            "host": h.device_name,
            "ip": h.device_ip,
            "metric_count": h.metric_count,
            "last_update": h.last_update.isoformat() if h.last_update else None
        }
        for idx, h in enumerate(hosts)
    ]
    
    return {"items": dashboards}


@router.get("/dashboards/{dashboard_id}", summary="获取仪表盘配置")
async def get_dashboard(
    dashboard_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取仪表盘的配置信息"""
    # 获取该仪表盘关联主机的最新指标
    hosts = db.query(
        PerformanceMetric.device_name,
        PerformanceMetric.device_ip
    ).distinct().offset(dashboard_id - 1).limit(1).first()
    
    if not hosts:
        raise HTTPException(status_code=404, detail="仪表盘不存在")
    
    # 获取最新指标
    latest_metrics = db.query(PerformanceMetric).filter(
        PerformanceMetric.device_name == hosts.device_name
    ).order_by(PerformanceMetric.timestamp.desc()).limit(20).all()
    
    # 按类别分组
    panels = {}
    for m in latest_metrics:
        if m.metric_category not in panels:
            panels[m.metric_category] = []
        panels[m.metric_category].append({
            'name': m.metric_name,
            'value': m.value,
            'unit': m.metric_unit,
            'timestamp': m.timestamp.isoformat()
        })
    
    return {
        "id": dashboard_id,
        "name": f"{hosts.device_name} 概览",
        "host": hosts.device_name,
        "ip": hosts.device_ip,
        "panels": panels
    }


# ============== 告警触发规则接口 ==============

class TriggerRuleCreate(BaseModel):
    """创建触发规则请求"""
    name: str = Field(..., description="规则名称")
    description: str = Field("", description="规则描述")
    enabled: bool = True
    condition_type: str = Field("threshold", description="条件类型: threshold, change, rate, constant, expression")
    match_conditions: dict = Field(..., description="匹配条件")
    alert_level: str = Field("warning", description="告警级别: critical, high, medium, low, info")
    alert_title_template: str = Field("{metric}告警", description="告警标题模板")
    alert_message_template: str = Field("{metric}超过阈值，当前值:{value}，阈值:{threshold}", description="告警消息模板")
    device_ids: List[int] = Field(default_factory=list, description="设备ID列表")
    device_types: List[str] = Field(default_factory=list, description="设备类型列表")
    tags_filter: dict = Field(default_factory=dict, description="标签过滤")
    suppress_enabled: bool = False
    suppress_duration: int = 300
    suppress_key: Optional[str] = None
    trigger_interval: int = 60
    actions: List[dict] = Field(default_factory=list, description="触发动作")
    time_windows: List[dict] = Field(default_factory=list, description="时间窗口")
    priority: int = 100


class TriggerRuleUpdate(BaseModel):
    """更新触发规则请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    condition_type: Optional[str] = None
    match_conditions: Optional[dict] = None
    alert_level: Optional[str] = None
    alert_title_template: Optional[str] = None
    alert_message_template: Optional[str] = None
    device_ids: Optional[List[int]] = None
    device_types: Optional[List[str]] = None
    tags_filter: Optional[dict] = None
    suppress_enabled: Optional[bool] = None
    suppress_duration: Optional[int] = None
    suppress_key: Optional[str] = None
    trigger_interval: Optional[int] = None
    actions: Optional[List[dict]] = None
    time_windows: Optional[List[dict]] = None
    priority: Optional[int] = None


@router.get("/trigger-rules", summary="获取触发规则列表")
async def get_trigger_rules(
    enabled: Optional[bool] = Query(None, description="启用状态过滤"),
    condition_type: Optional[str] = Query(None, description="条件类型过滤"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取告警触发规则列表"""
    from modules.business.monitoring.alert_trigger import (
        get_trigger_engine, TriggerCondition
    )
    
    engine = get_trigger_engine()
    rules = engine.list_rules(enabled_only=False)
    
    if enabled is not None:
        rules = [r for r in rules if r.enabled == enabled]
    
    if condition_type:
        rules = [r for r in rules if r.condition_type.value == condition_type]
    
    return {
        "items": [r.to_dict() for r in rules],
        "total": len(rules),
    }


@router.post("/trigger-rules", summary="创建触发规则")
async def create_trigger_rule(
    rule: TriggerRuleCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """创建新的触发规则"""
    from modules.business.monitoring.alert_trigger import (
        get_trigger_engine, TriggerRule, TriggerCondition
    )
    
    engine = get_trigger_engine()
    
    import uuid
    trigger_rule = TriggerRule(
        id=str(uuid.uuid4()),
        name=rule.name,
        description=rule.description,
        enabled=rule.enabled,
        condition_type=TriggerCondition(rule.condition_type),
        match_conditions=rule.match_conditions,
        alert_level=rule.alert_level,
        alert_title_template=rule.alert_title_template,
        alert_message_template=rule.alert_message_template,
        device_ids=rule.device_ids,
        device_types=rule.device_types,
        tags_filter=rule.tags_filter,
        suppress_enabled=rule.suppress_enabled,
        suppress_duration=rule.suppress_duration,
        suppress_key=rule.suppress_key,
        trigger_interval=rule.trigger_interval,
        actions=rule.actions,
        time_windows=rule.time_windows,
        priority=rule.priority,
        created_by=current_user.username,
    )
    
    engine.add_rule(trigger_rule)
    
    return {"id": trigger_rule.id, "message": "创建成功"}


@router.get("/trigger-rules/{rule_id}", summary="获取触发规则详情")
async def get_trigger_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取指定触发规则的详细信息"""
    from modules.business.monitoring.alert_trigger import get_trigger_engine
    
    engine = get_trigger_engine()
    rule = engine.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="触发规则不存在")
    
    return rule.to_dict()


@router.put("/trigger-rules/{rule_id}", summary="更新触发规则")
async def update_trigger_rule(
    rule_id: str,
    rule_update: TriggerRuleUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """更新触发规则"""
    from modules.business.monitoring.alert_trigger import (
        get_trigger_engine, TriggerCondition
    )
    
    engine = get_trigger_engine()
    rule = engine.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="触发规则不存在")
    
    update_data = rule_update.model_dump(exclude_unset=True)
    
    if 'condition_type' in update_data and update_data['condition_type']:
        update_data['condition_type'] = TriggerCondition(update_data['condition_type'])
    
    for key, value in update_data.items():
        if value is not None and hasattr(rule, key):
            setattr(rule, key, value)
    
    engine.update_rule(rule)
    
    return {"message": "更新成功"}


@router.delete("/trigger-rules/{rule_id}", summary="删除触发规则")
async def delete_trigger_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """删除触发规则"""
    from modules.business.monitoring.alert_trigger import get_trigger_engine
    
    engine = get_trigger_engine()
    
    if not engine.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="触发规则不存在")
    
    return {"message": "删除成功"}


@router.post("/trigger-rules/{rule_id}/test", summary="测试触发规则")
async def test_trigger_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """测试触发规则（模拟触发）"""
    from modules.business.monitoring.alert_trigger import get_trigger_engine
    
    engine = get_trigger_engine()
    rule = engine.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="触发规则不存在")
    
    # 模拟一个测试事件
    conditions = rule.match_conditions
    test_value = conditions.get('value', 90) + 10  # 超过阈值
    
    events = await engine.evaluate_and_trigger(
        metric_name=conditions.get('metric', 'cpu_usage'),
        value=test_value,
        device_id=1,
        device_name='test-server',
        device_ip='192.168.1.1',
    )
    
    return {
        "success": len(events) > 0,
        "triggered": len(events) > 0,
        "events": [e.to_dict() for e in events],
        "message": f"测试{'触发成功' if events else '未触发'}"
    }


@router.get("/trigger-events", summary="获取触发事件列表")
async def get_trigger_events(
    rule_id: Optional[str] = Query(None, description="规则ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, le=1000, description="返回数量"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取触发事件历史"""
    from modules.business.monitoring.alert_trigger import (
        get_trigger_engine, TriggerStatus
    )
    
    engine = get_trigger_engine()
    
    status_enum = None
    if status:
        try:
            status_enum = TriggerStatus(status)
        except ValueError:
            pass
    
    events = engine.list_events(
        rule_id=rule_id,
        status=status_enum,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    
    return {
        "items": [e.to_dict() for e in events],
        "total": len(events),
    }


@router.post("/trigger/evaluate", summary="评估指标触发条件")
async def evaluate_trigger(
    metric_name: str = Query(..., description="指标名称"),
    value: float = Query(..., description="指标值"),
    device_id: int = Query(..., description="设备ID"),
    device_name: str = Query(..., description="设备名称"),
    device_ip: str = Query(..., description="设备IP"),
    previous_value: Optional[float] = Query(None, description="前一个值"),
    duration_seconds: Optional[int] = Query(None, description="持续秒数"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """评估指标是否触发告警"""
    from modules.business.monitoring.alert_trigger import get_trigger_engine
    
    engine = get_trigger_engine()
    
    events = await engine.evaluate_and_trigger(
        metric_name=metric_name,
        value=value,
        device_id=device_id,
        device_name=device_name,
        device_ip=device_ip,
        previous_value=previous_value,
        duration_seconds=duration_seconds,
    )
    
    return {
        "triggered": len(events) > 0,
        "events": [e.to_dict() for e in events],
        "count": len(events),
    }


# ============== 设备采集项单项开关接口 ==============

class DeviceMetricConfigCreate(BaseModel):
    """创建设备采集项配置"""
    device_id: int = Field(..., description="设备ID")
    device_name: Optional[str] = Field(None, description="设备名称")
    metric_category: str = Field(..., description="指标类别，如 cpu, memory, disk, network")
    metric_name: str = Field(..., description="指标名称")
    enabled: bool = Field(True, description="是否启用")
    collect_interval: int = Field(0, description="采集间隔(秒)，0表示使用默认")
    alert_thresholds: Optional[str] = Field(None, description="告警阈值JSON")
    remark: Optional[str] = Field(None, description="备注")


class DeviceMetricConfigUpdate(BaseModel):
    """更新设备采集项配置"""
    enabled: Optional[bool] = Field(None, description="是否启用")
    collect_interval: Optional[int] = Field(None, description="采集间隔(秒)")
    alert_thresholds: Optional[str] = Field(None, description="告警阈值JSON")
    remark: Optional[str] = Field(None, description="备注")


class DeviceMetricConfigResponse(BaseModel):
    """设备采集项配置响应"""
    id: int
    device_id: int
    device_name: Optional[str]
    metric_category: str
    metric_name: str
    enabled: bool
    collect_interval: int
    alert_thresholds: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: Optional[str]
    updated_by: Optional[str]
    remark: Optional[str]


@router.get("/metric-configs", summary="获取设备采集项配置列表")
async def get_metric_configs(
    device_id: Optional[int] = Query(None, description="设备ID"),
    metric_category: Optional[str] = Query(None, description="指标类别"),
    enabled: Optional[bool] = Query(None, description="启用状态"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取设备采集项配置列表
    支持按设备ID、指标类别、启用状态过滤
    """
    query = db.query(DeviceMetricConfig)
    
    if device_id is not None:
        query = query.filter(DeviceMetricConfig.device_id == device_id)
    if metric_category:
        query = query.filter(DeviceMetricConfig.metric_category == metric_category)
    if enabled is not None:
        query = query.filter(DeviceMetricConfig.enabled == enabled)
    
    configs = query.order_by(DeviceMetricConfig.device_id, DeviceMetricConfig.metric_category, DeviceMetricConfig.metric_name).all()
    
    return {
        "items": [c.to_dict() for c in configs],
        "total": len(configs),
    }


@router.get("/metric-configs/{config_id}", summary="获取采集项配置详情")
async def get_metric_config(
    config_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定采集项配置的详细信息"""
    config = db.query(DeviceMetricConfig).filter(DeviceMetricConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="采集项配置不存在")
    
    return config.to_dict()


@router.post("/metric-configs", summary="创建设备采集项配置")
async def create_metric_config(
    config: DeviceMetricConfigCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建设备采集项配置
    用于启用/禁用特定设备的特定指标采集
    """
    # 检查是否已存在
    existing = db.query(DeviceMetricConfig).filter(
        DeviceMetricConfig.device_id == config.device_id,
        DeviceMetricConfig.metric_category == config.metric_category,
        DeviceMetricConfig.metric_name == config.metric_name,
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="采集项配置已存在，请使用PATCH更新")
    
    db_config = DeviceMetricConfig(
        device_id=config.device_id,
        device_name=config.device_name,
        metric_category=config.metric_category,
        metric_name=config.metric_name,
        enabled=config.enabled,
        collect_interval=config.collect_interval,
        alert_thresholds=config.alert_thresholds,
        remark=config.remark,
        created_by=current_user.username,
    )
    
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return {
        "status": "success",
        "message": "采集项配置创建成功",
        "config": db_config.to_dict(),
    }


@router.patch("/metric-configs/{config_id}", summary="更新采集项配置(单项开关)")
async def update_metric_config(
    config_id: int,
    update: DeviceMetricConfigUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新采集项配置
    主要用于启用/禁用特定指标的采集
    """
    config = db.query(DeviceMetricConfig).filter(DeviceMetricConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="采集项配置不存在")
    
    # 更新字段
    if update.enabled is not None:
        config.enabled = update.enabled
    if update.collect_interval is not None:
        config.collect_interval = update.collect_interval
    if update.alert_thresholds is not None:
        config.alert_thresholds = update.alert_thresholds
    if update.remark is not None:
        config.remark = update.remark
    
    config.updated_by = current_user.username
    db.commit()
    db.refresh(config)
    
    return {
        "status": "success",
        "message": "采集项配置更新成功",
        "config": config.to_dict(),
    }


@router.patch("/metric-configs/{config_id}/toggle", summary="切换采集项开关状态")
async def toggle_metric_config(
    config_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    快速切换采集项启用/禁用状态
    """
    config = db.query(DeviceMetricConfig).filter(DeviceMetricConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="采集项配置不存在")
    
    config.enabled = not config.enabled
    config.updated_by = current_user.username
    db.commit()
    db.refresh(config)
    
    return {
        "status": "success",
        "message": f"采集项已{'启用' if config.enabled else '禁用'}",
        "config": config.to_dict(),
    }


@router.delete("/metric-configs/{config_id}", summary="删除采集项配置")
async def delete_metric_config(
    config_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除采集项配置"""
    config = db.query(DeviceMetricConfig).filter(DeviceMetricConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="采集项配置不存在")
    
    db.delete(config)
    db.commit()
    
    return {
        "status": "success",
        "message": "采集项配置已删除",
    }


@router.get("/metric-configs/device/{device_id}", summary="获取设备的所有采集项配置")
async def get_device_metric_configs(
    device_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取指定设备的所有采集项配置
    """
    configs = db.query(DeviceMetricConfig).filter(
        DeviceMetricConfig.device_id == device_id
    ).order_by(DeviceMetricConfig.metric_category, DeviceMetricConfig.metric_name).all()
    
    return {
        "device_id": device_id,
        "items": [c.to_dict() for c in configs],
        "total": len(configs),
        "enabled_count": len([c for c in configs if c.enabled]),
        "disabled_count": len([c for c in configs if not c.enabled]),
    }


# ============== MON-031/MON-032: 仪表盘布局自定义 ==============

from modules.business.dashboard.persistence import (
    DashboardLayout as DashboardLayoutModel,
    DashboardLayoutSnapshot,
    DashboardLayoutData,
    DashboardLayoutService,
    LayoutItem,
    LayoutWidget,
    LayoutPosition,
    ColumnConfig,
    DEFAULT_COLUMNS,
)


class DashboardLayoutRequest(BaseModel):
    """仪表盘布局请求"""
    layout_id: Optional[str] = None
    name: str = "默认布局"
    description: Optional[str] = ""
    grid_size: str = "medium"
    columns: int = 12
    row_height: int = 80
    items: List[Dict[str, Any]] = []
    column_config: List[Dict[str, Any]] = []
    theme: str = "default"
    is_default: bool = False
    is_shared: bool = False
    tags: List[str] = []


class DashboardLayoutResponse(BaseModel):
    """仪表盘布局响应"""
    layout_id: str
    user_id: str
    name: str
    description: Optional[str]
    version: int
    grid_size: str
    columns: int
    row_height: int
    items: List[Dict[str, Any]]
    column_config: List[Dict[str, Any]]
    theme: str
    is_default: bool
    is_shared: bool
    tags: List[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: Optional[str]
    updated_by: Optional[str]


def _build_response(data: Any = None, code: int = 0, message: str = "success") -> Dict[str, Any]:
    """构建统一响应格式"""
    return {
        "code": code,
        "message": message,
        "data": data,
    }


@router.get("/dashboard/layout", summary="获取用户仪表盘布局")
async def get_dashboard_layout(
    layout_id: Optional[str] = Query(None, description="布局ID，不传则获取默认布局"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取用户仪表盘布局配置
    - 支持获取指定布局或默认布局
    - 包含widgets、位置、显示/隐藏配置、列宽等
    """
    try:
        service = DashboardLayoutService(db_session=db)
        layout_data = service.get_user_layout(current_user.user_id, layout_id)
        
        if not layout_data:
            # 创建默认布局
            layout_data = service.create_default_layout(current_user.user_id)
        
        return _build_response(data=layout_data.to_dict())
        
    except Exception as e:
        logger.error(f"获取布局失败: {e}")
        return _build_response(code=500, message=f"获取布局失败: {str(e)}")


@router.put("/dashboard/layout", summary="保存用户仪表盘布局")
async def save_dashboard_layout(
    layout: DashboardLayoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    保存用户仪表盘布局配置
    - 支持拖拽排序
    - 支持显示/隐藏列
    - 支持自定义列宽
    - 自动版本控制
    """
    try:
        import uuid
        
        # 生成layout_id
        layout_id = layout.layout_id
        if not layout_id:
            layout_id = f"layout_{uuid.uuid4().hex[:12]}"
        
        # 转换为DashboardLayoutData
        layout_data = DashboardLayoutData(
            layout_id=layout_id,
            user_id=current_user.user_id,
            name=layout.name,
            description=layout.description or "",
            version=1,
            grid_size=layout.grid_size,
            columns=layout.columns,
            row_height=layout.row_height,
            items=[LayoutItem.from_dict(item) for item in layout.items],
            column_config=[ColumnConfig.from_dict(c) for c in (layout.column_config or DEFAULT_COLUMNS)],
            theme=layout.theme,
            is_default=layout.is_default,
            is_shared=layout.is_shared,
            tags=layout.tags,
        )
        
        service = DashboardLayoutService(db_session=db)
        saved_layout = service.save_layout(current_user.user_id, layout_data, created_by=current_user.username)
        
        return _build_response(data=saved_layout.to_dict(), message="布局保存成功")
        
    except Exception as e:
        logger.error(f"保存布局失败: {e}")
        return _build_response(code=500, message=f"保存布局失败: {str(e)}")


@router.get("/dashboard/layouts", summary="获取用户所有仪表盘布局")
async def list_dashboard_layouts(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取用户所有仪表盘布局列表
    """
    try:
        service = DashboardLayoutService(db_session=db)
        layouts = service.list_user_layouts(current_user.user_id)
        
        return _build_response(data=[l.to_dict() for l in layouts])
        
    except Exception as e:
        logger.error(f"列出布局失败: {e}")
        return _build_response(code=500, message=f"列出布局失败: {str(e)}")


@router.delete("/dashboard/layout/{layout_id}", summary="删除仪表盘布局")
async def delete_dashboard_layout(
    layout_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除指定仪表盘布局
    """
    try:
        service = DashboardLayoutService(db_session=db)
        success = service.delete_layout(current_user.user_id, layout_id)
        
        if success:
            return _build_response(message="布局删除成功")
        else:
            return _build_response(code=404, message="布局不存在")
            
    except Exception as e:
        logger.error(f"删除布局失败: {e}")
        return _build_response(code=500, message=f"删除布局失败: {str(e)}")


@router.post("/dashboard/layout/snapshot", summary="创建布局快照")
async def create_layout_snapshot(
    layout_id: str = Query(..., description="布局ID"),
    comment: Optional[str] = Query(None, description="快照说明"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    为当前布局创建快照，用于版本回滚
    """
    try:
        service = DashboardLayoutService(db_session=db)
        layout_data = service.get_user_layout(current_user.user_id, layout_id)
        
        if not layout_data:
            return _build_response(code=404, message="布局不存在")
        
        success = service.create_snapshot(
            layout_id=layout_id,
            version=layout_data.version,
            snapshot_data=layout_data,
            created_by=current_user.username,
            comment=comment,
        )
        
        if success:
            return _build_response(message="快照创建成功")
        else:
            return _build_response(code=500, message="快照创建失败")
            
    except Exception as e:
        logger.error(f"创建快照失败: {e}")
        return _build_response(code=500, message=f"创建快照失败: {str(e)}")


@router.get("/dashboard/layout/snapshot/{layout_id}/{version}", summary="获取布局快照")
async def get_layout_snapshot(
    layout_id: str,
    version: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取指定版本的布局快照
    """
    try:
        service = DashboardLayoutService(db_session=db)
        snapshot = service.get_snapshot(layout_id, version)
        
        if snapshot:
            return _build_response(data=snapshot.to_dict())
        else:
            return _build_response(code=404, message="快照不存在")
            
    except Exception as e:
        logger.error(f"获取快照失败: {e}")
        return _build_response(code=500, message=f"获取快照失败: {str(e)}")


@router.get("/dashboard/columns", summary="获取仪表盘列配置")
async def get_dashboard_columns(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取仪表盘列配置（显示/隐藏、宽度等）
    """
    return _build_response(data=DEFAULT_COLUMNS)


# ============== 仪表盘统计接口 ==============

@router.get("/dashboard/stats", summary="获取仪表盘统计数据")
async def get_dashboard_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取仪表盘统计数据，包括：
    - 设备总数、在线数、离线数、维护数
    - 活跃告警数
    - 待处理工单数（pending + processing）
    - 最近7天告警趋势
    """
    from modules.foundation.db_models.device import Device, DeviceStatus
    from modules.foundation.db_models.alert import Alert, AlertStatus, AlertLevel
    from modules.foundation.db_models.workorder import WorkOrder, WorkOrderStatus
    
    # 设备统计
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == DeviceStatus.ONLINE).count()
    offline_devices = db.query(Device).filter(Device.status == DeviceStatus.OFFLINE).count()
    maintenance_devices = db.query(Device).filter(Device.status == DeviceStatus.MAINTENANCE).count()
    
    # 活跃告警数
    active_alerts = db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE).count()
    
    # 严重告警数（critical）
    critical_alerts = db.query(Alert).filter(
        Alert.status == AlertStatus.ACTIVE,
        Alert.level == AlertLevel.CRITICAL
    ).count()
    
    # 待处理工单数（pending + processing）
    pending_orders = db.query(WorkOrder).filter(
        WorkOrder.status.in_([WorkOrderStatus.PENDING, WorkOrderStatus.PROCESSING])
    ).count()
    
    # 最近7天告警趋势
    alert_trend = []
    for i in range(6, -1, -1):
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = db.query(Alert).filter(
            Alert.occurred_at >= day_start,
            Alert.occurred_at < day_end
        ).count()
        alert_trend.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'count': count
        })
    
    return {
        'devices': {
            'total': total_devices,
            'online': online_devices,
            'offline': offline_devices,
            'maintenance': maintenance_devices,
        },
        'alerts': {
            'active': active_alerts,
            'critical': critical_alerts,
            'trend': alert_trend,
        },
        'workorders': {
            'pending': pending_orders,
        }
    }
