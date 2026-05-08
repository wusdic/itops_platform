"""
监控管理API路由
提供监控数据采集、告警管理、指标查询等接口
"""

from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.alert import Alert, AlertLevel, AlertStatus, AlertCategory


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
    host: Optional[str] = Query(None, description="主机过滤"),
    start: Optional[datetime] = Query(None, description="开始时间"),
    end: Optional[datetime] = Query(None, description="结束时间"),
    step: int = Query(60, description="采样间隔(秒)"),
    limit: int = Query(1000, le=10000, description="返回点数限制"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    查询监控指标数据
    
    支持Prometheus查询语法，返回时序数据点列表
    注意：此接口需要连接到真实的监控系统（Prometheus/Zabbix）
    当前返回空数据，实际使用需要集成监控系统
    """
    # TODO: 调用监控模块获取数据
    # 实际实现需要连接到 Prometheus/Zabbix 等监控系统
    return {
        "metric": metric_name,
        "host": host,
        "points": [],
        "count": 0
    }


@router.get("/metrics/hosts", summary="获取主机列表")
async def get_hosts(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取已监控的主机列表"""
    # 从告警表中获取已监控的主机
    hosts = db.query(
        Alert.device_name,
        Alert.device_ip
    ).filter(
        Alert.device_name.isnot(None)
    ).distinct().all()
    
    return {
        "hosts": [
            {"host": h.device_name, "ip": h.device_ip, "status": "up"}
            for h in hosts if h.device_name
        ]
    }


@router.get("/metrics/available", summary="获取可用指标列表")
async def get_available_metrics(
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取系统中可用的指标列表"""
    # 预定义常用指标，实际应从监控系统获取
    return {
        "metrics": [
            "cpu_usage",
            "memory_usage",
            "disk_usage",
            "disk_inodes_usage",
            "network_in",
            "network_out",
            "tcp_connections",
            "load_average",
            "process_count",
        ]
    }


@router.post("/metrics/query", summary="PromQL查询")
async def promql_query(
    query: MetricQuery,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    使用PromQL查询指标
    
    支持Prometheus查询语法
    注意：需要连接到真实的Prometheus实例
    """
    # TODO: 调用Prometheus查询接口
    return {"status": "success", "data": []}


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
    """
    获取告警列表
    支持分页和过滤
    """
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
    """
    创建告警记录
    通常由监控系统自动创建，也可手动创建
    """
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
    """确认告警，表示已知悉该告警"""
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
):
    """获取所有告警规则"""
    # 预定义告警规则，实际应从配置文件或数据库获取
    return {
        "items": [
            {
                "id": 1,
                "name": "CPU过高告警",
                "metric": "cpu_usage",
                "condition": "> 80",
                "severity": "high",
                "duration": "5m",
                "enabled": True,
            },
            {
                "id": 2,
                "name": "内存过高告警",
                "metric": "memory_usage",
                "condition": "> 85",
                "severity": "medium",
                "duration": "5m",
                "enabled": True,
            },
            {
                "id": 3,
                "name": "磁盘空间不足告警",
                "metric": "disk_usage",
                "condition": "> 90",
                "severity": "critical",
                "duration": "1m",
                "enabled": True,
            },
        ]
    }


@router.get("/rules/{rule_id}", summary="获取告警规则详情")
async def get_alert_rule(
    rule_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取指定告警规则的详细信息"""
    # 预定义告警规则
    rules = {
        1: {"id": 1, "name": "CPU过高告警", "metric": "cpu_usage", "condition": "> 80", "severity": "high", "duration": "5m", "enabled": True},
        2: {"id": 2, "name": "内存过高告警", "metric": "memory_usage", "condition": "> 85", "severity": "medium", "duration": "5m", "enabled": True},
        3: {"id": 3, "name": "磁盘空间不足告警", "metric": "disk_usage", "condition": "> 90", "severity": "critical", "duration": "1m", "enabled": True},
    }
    
    if rule_id not in rules:
        raise HTTPException(status_code=404, detail="告警规则不存在")
    
    return rules[rule_id]


# ============== 监控视图接口 ==============

@router.get("/dashboards", summary="获取监控仪表盘列表")
async def get_dashboards(
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取预定义的监控仪表盘"""
    return {
        "items": [
            {"id": 1, "name": "系统概览", "type": "overview"},
            {"id": 2, "name": "网络监控", "type": "network"},
            {"id": 3, "name": "应用监控", "type": "application"},
        ]
    }


@router.get("/dashboards/{dashboard_id}", summary="获取仪表盘配置")
async def get_dashboard(
    dashboard_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取仪表盘的配置信息"""
    dashboards = {
        1: {"id": 1, "name": "系统概览", "panels": []},
        2: {"id": 2, "name": "网络监控", "panels": []},
        3: {"id": 3, "name": "应用监控", "panels": []},
    }
    
    if dashboard_id not in dashboards:
        raise HTTPException(status_code=404, detail="仪表盘不存在")
    
    return dashboards[dashboard_id]
