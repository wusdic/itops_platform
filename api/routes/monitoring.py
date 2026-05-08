"""
监控管理API路由
提供监控数据采集、告警管理、指标查询等接口
"""

from typing import Optional, List
from datetime import datetime, timedelta
import json

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.alert import Alert, AlertLevel, AlertStatus, AlertCategory
from modules.foundation.db_models.monitoring import PerformanceMetric
from modules.foundation.db_models.device import Device


router = APIRouter()


# ============== 请求/响应模型 ==============

class MetricQuery(BaseModel):
    """指标查询请求"""
    metric_name: str = Field(..., description="指标名称")
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
    简化实现，支持基本的指标和时间范围查询
    """
    if not query.start_time:
        query.start_time = datetime.now() - timedelta(hours=24)
    if not query.end_time:
        query.end_time = datetime.now()
    
    query_db = db.query(PerformanceMetric).filter(
        PerformanceMetric.metric_name == query.metric_name,
        PerformanceMetric.timestamp >= query.start_time,
        PerformanceMetric.timestamp <= query.end_time
    )
    
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
        "metric": query.metric_name,
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
    
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = current_user.username
    alert.acknowledged_at = datetime.now()
    alert.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "Alert acknowledged"}


@router.put("/alerts/{alert_id}/resolve", summary="解决告警")
async def resolve_alert(
    alert_id: int,
    resolution: str = Query(..., description="解决方案描述"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解决告警"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    alert.status = AlertStatus.RESOLVED
    alert.resolved_by = current_user.username
    alert.resolved_at = datetime.now()
    alert.resolution_note = resolution
    alert.updated_at = datetime.now()
    db.commit()
    
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
    
    db.delete(alert)
    db.commit()
    
    return {"status": "success", "message": "Alert deleted"}


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
