"""
设备管理API路由

提供设备的增删改查、采集控制、状态查询等接口
与配置文件驱动的设备管理方案集成
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import func

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams, Session
from modules.foundation.db_models.device import Device

logger = logging.getLogger(__name__)

router = APIRouter(tags=["设备管理"], prefix="/api/v1/devices")


# ============== 请求/响应模型 ==============

class DeviceCollectRequest(BaseModel):
    """采集请求"""
    device_name: str = Field(..., description="设备名称")
    protocol: Optional[str] = Field(None, description="指定协议，不指定则自动选择")


class DeviceCollectResponse(BaseModel):
    """采集响应"""
    device_name: str
    device_ip: str
    device_type: str
    vendor: str
    status: str
    timestamp: str
    metrics: dict
    error: Optional[str] = None


class DeviceConfigResponse(BaseModel):
    """设备配置响应"""
    name: str
    ip: str
    type: str
    os: Optional[str] = None
    os_version: Optional[str] = None
    vendor: Optional[str] = None
    protocols: dict
    collect_enabled: bool
    collect_interval: int
    tags: dict
    status: str = "unknown"
    last_collect_time: Optional[str] = None


class DeviceStatsResponse(BaseModel):
    """设备统计响应"""
    total: int
    online: int
    offline: int
    unknown: int
    by_type: dict
    by_vendor: dict


class ProtocolInfo(BaseModel):
    """协议信息"""
    name: str
    type: str
    default_port: int
    capabilities: List[str]
    required_credentials: List[str]
    description: str


# ============== 设备接口 ==============

@router.get("", summary="获取设备列表")
async def list_devices(
    device_type: Optional[str] = Query(None, description="设备类型过滤"),
    vendor: Optional[str] = Query(None, description="厂商过滤"),
    enabled: Optional[bool] = Query(None, description="是否启用"),
    tag: Optional[str] = Query(None, description="标签过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取设备列表
    优先从MySQL数据库获取设备，支持分页和过滤。
    """
    try:
        from modules.collection.device_manager import get_device_manager
        
        manager = get_device_manager()
        
        # 从MySQL数据库获取设备列表
        query = db.query(Device)
        
        # 应用过滤条件
        if device_type:
            from modules.foundation.db_models.device import DeviceType as DBDeviceType
            type_mapping = {
                'server': DBDeviceType.SERVER_LINUX,
                'network': DBDeviceType.NETWORK_SWITCH,
                'storage': DBDeviceType.STORAGE_NAS,
                'security': DBDeviceType.SECURITY_IPS,
                'virtual': DBDeviceType.SERVER_VMWARE,
                'cloud': DBDeviceType.OTHER,
                'other': DBDeviceType.OTHER,
            }
            db_type = type_mapping.get(device_type, DBDeviceType.OTHER)
            query = query.filter(Device.device_type == db_type)
        
        if vendor:
            query = query.filter(Device.vendor.ilike(f"%{vendor}%"))
        
        if tag:
            query = query.filter(Device.tags.ilike(f"%{tag}%"))
        
        # 获取总数并分页
        total = query.count()
        devices = query.offset(pagination.offset).limit(pagination.limit).all()
        
        # 转换为响应格式，合并实时状态
        items = []
        for dev in devices:
            status = manager.get_device_status(dev.name)
            last_metrics = manager.get_last_metrics(dev.name)
            
            # 优先用数据库中的status，fallback到manager内存状态
            db_status = dev.status.value if dev.status else "unknown"
            # 如果数据库状态不是真实采集得到的，尝试从manager获取实时状态
            if db_status in ("unknown", None) and status and status.value != "unknown":
                final_status = status.value
            else:
                final_status = db_status

            items.append({
                "name": dev.name,
                "ip": dev.ip_address,
                "type": dev.device_type.value if dev.device_type else "other",
                "os": dev.os_type,
                "os_version": dev.os_version,
                "vendor": dev.vendor,
                "manufacturer": dev.manufacturer,
                "model": dev.model,
                "protocols": {},  # 从数据库读取可扩展
                "collect_enabled": dev.monitor_enabled if dev.monitor_enabled is not None else True,
                "collect_interval": 60,
                "tags": dev.tags,
                "status": final_status,
                "last_collect_time": last_metrics.timestamp.isoformat() if last_metrics and last_metrics.timestamp else None,
                "location": dev.location,
                "idc": dev.idc,
                "cabinet": dev.cabinet,
            })
        
        return {
            "items": items,
            "total": total,
            "page": pagination.page,
            "page_size": pagination.page_size,
        }
        
    except Exception as e:
        logger.error(f"获取设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="获取设备统计")
async def get_device_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取设备统计信息，优先从MySQL数据库统计
    """
    try:
        from modules.collection.device_manager import get_device_manager
        
        manager = get_device_manager()
        
        # 从MySQL数据库获取统计
        total = db.query(Device).count()
        
        from modules.foundation.db_models.device import DeviceStatus as DBDeviceStatus
        online = db.query(Device).filter(Device.status == DBDeviceStatus.ONLINE).count()
        offline = db.query(Device).filter(Device.status == DBDeviceStatus.OFFLINE).count()
        unknown = db.query(Device).filter(Device.status == DBDeviceStatus.UNKNOWN).count()
        
        # 按类型统计
        from modules.foundation.db_models.device import DeviceType as DBDeviceType
        by_type = {}
        for dt in DBDeviceType:
            count = db.query(Device).filter(Device.device_type == dt).count()
            if count > 0:
                by_type[dt.value] = count
        
        # 按厂商统计
        by_vendor = {}
        vendor_results = db.query(Device.vendor, func.count(Device.id)).filter(
            Device.vendor.isnot(None)
        ).group_by(Device.vendor).all()
        for vendor, count in vendor_results:
            by_vendor[vendor] = count
        
        stats = {
            "total": total,
            "online": online,
            "offline": offline,
            "unknown": unknown,
            "by_type": by_type,
            "by_vendor": by_vendor,
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"获取设备统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_name}", summary="获取设备详情")
async def get_device(
    device_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取指定设备的详细信息，优先从MySQL数据库获取
    """
    try:
        from modules.collection.device_manager import get_device_manager
        
        manager = get_device_manager()
        
        # 优先从MySQL数据库获取设备详情
        db_device = db.query(Device).filter(
            (Device.name == device_name) | (Device.hostname == device_name)
        ).first()
        
        if db_device:
            device = {
                "name": db_device.name,
                "ip": db_device.ip_address,
                "type": db_device.device_type.value if db_device.device_type else "other",
                "os": db_device.os_type,
                "os_version": db_device.os_version,
                "vendor": db_device.vendor,
                "manufacturer": db_device.manufacturer,
                "model": db_device.model,
                "serial_number": db_device.serial_number,
                "protocols": {},
                "collect_enabled": db_device.monitor_enabled if db_device.monitor_enabled is not None else True,
                "tags": db_device.tags,
                "location": db_device.location,
                "idc": db_device.idc,
                "cabinet": db_device.cabinet,
                "status": db_device.status.value if db_device.status else "unknown",
                "cpu": db_device.cpu,
                "memory": db_device.memory,
                "disk": db_device.disk,
            }
        else:
            # 回退到YAML配置
            from modules.collection.config_loader import get_config_loader
            loader = get_config_loader()
            device = loader.get_device_by_name(device_name)
            if not device:
                raise HTTPException(status_code=404, detail=f"设备不存在: {device_name}")
        
        # 获取设备状态和最近指标
        status = manager.get_device_status(device_name)
        last_metrics = manager.get_last_metrics(device_name)
        
        return {
            "name": device.get("name"),
            "ip": device.get("ip"),
            "type": device.get("type"),
            "os": device.get("os"),
            "os_version": device.get("os_version"),
            "vendor": device.get("vendor"),
            "protocols": device.get("protocols", {}),
            "credentials": device.get("credentials", {}),
            "api": device.get("api", {}),
            "kubernetes": device.get("kubernetes", {}),
            "collect": device.get("collect", {}),
            "tags": device.get("tags", {}),
            "status": status.value if status else "unknown",
            "last_collect_time": last_metrics.timestamp.isoformat() if last_metrics and last_metrics.timestamp else None,
            "last_metrics": last_metrics.metrics if last_metrics else None,
            "config_file": device.get("_config_file"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取设备详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect", summary="采集设备指标")
async def collect_device(
    request: DeviceCollectRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    手动触发设备指标采集
    """
    try:
        from modules.collection.device_manager import get_device_manager
        
        manager = get_device_manager()
        
        metrics = await manager.collect_device(request.device_name, request.protocol)
        
        if not metrics:
            raise HTTPException(status_code=404, detail=f"设备不存在: {request.device_name}")
        
        return DeviceCollectResponse(
            device_name=metrics.device_name,
            device_ip=metrics.device_ip,
            device_type=metrics.device_type,
            vendor=metrics.vendor,
            status=metrics.status.value if metrics.status else "unknown",
            timestamp=metrics.timestamp.isoformat() if metrics.timestamp else "",
            metrics=metrics.metrics,
            error=metrics.error,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"采集设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/all", summary="采集所有设备")
async def collect_all_devices(
    enabled_only: bool = Query(True, description="只采集已启用的设备"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    批量采集所有设备指标
    """
    try:
        from modules.collection.device_manager import get_device_manager
        
        manager = get_device_manager()
        
        results = await manager.collect_all(enabled_only=enabled_only)
        
        items = []
        for metrics in results:
            if metrics:
                items.append(DeviceCollectResponse(
                    device_name=metrics.device_name,
                    device_ip=metrics.device_ip,
                    device_type=metrics.device_type,
                    vendor=metrics.vendor,
                    status=metrics.status.value if metrics.status else "unknown",
                    timestamp=metrics.timestamp.isoformat() if metrics.timestamp else "",
                    metrics=metrics.metrics,
                    error=metrics.error,
                ))
        
        return {
            "items": items,
            "total": len(items),
            "successful": len([m for m in results if m and m.status and m.status.value == "online"]),
            "failed": len([m for m in results if m and m.status and m.status.value == "offline"]),
        }
        
    except Exception as e:
        logger.error(f"批量采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_name}/status", summary="获取设备状态")
async def get_device_status(
    device_name: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取设备当前状态
    """
    try:
        from modules.collection.device_manager import get_device_manager
        
        manager = get_device_manager()
        status = manager.get_device_status(device_name)
        
        return {
            "device_name": device_name,
            "status": status.value if status else "unknown",
            "last_update": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"获取设备状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_name}/metrics", summary="获取设备指标")
async def get_device_metrics(
    device_name: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取设备最近一次采集的指标数据
    """
    try:
        from modules.collection.device_manager import get_device_manager
        
        manager = get_device_manager()
        metrics = manager.get_last_metrics(device_name)
        
        if not metrics:
            raise HTTPException(status_code=404, detail=f"设备无指标数据: {device_name}")
        
        return {
            "device_name": metrics.device_name,
            "device_ip": metrics.device_ip,
            "device_type": metrics.device_type,
            "vendor": metrics.vendor,
            "timestamp": metrics.timestamp.isoformat() if metrics.timestamp else None,
            "status": metrics.status.value if metrics.status else "unknown",
            "metrics": metrics.metrics,
            "error": metrics.error,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取设备指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_name}/metrics/history", summary="获取设备指标历史")
async def get_device_metrics_history(
    device_name: str,
    metric_type: str = Query("cpu", description="指标类型: cpu/memory/disk/network"),
    hours: int = Query(24, description="查询时间范围(小时)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取设备指标历史数据
    如果没有TDengine历史数据，则从device_manager获取最新数据点填充
    """
    try:
        from modules.collection.device_manager import get_device_manager
        from datetime import timedelta
        
        manager = get_device_manager()
        last_metrics = manager._last_metrics.get(device_name)
        
        if not last_metrics or not last_metrics.metrics:
            raise HTTPException(status_code=404, detail=f"设备无指标数据: {device_name}")
        
        # 根据 metric_type 提取对应的指标值
        value = None
        metrics_data = last_metrics.metrics
        
        if metric_type == "cpu":
            if "cpu" in metrics_data and "usage" in metrics_data["cpu"]:
                value = metrics_data["cpu"]["usage"]
        elif metric_type == "memory":
            if "memory" in metrics_data:
                # 优先使用 usage_percent
                if "usage_percent" in metrics_data["memory"]:
                    value = metrics_data["memory"]["usage_percent"]
                elif "used_mb" in metrics_data["memory"] and "total_mb" in metrics_data["memory"]:
                    total = metrics_data["memory"]["total_mb"]
                    if total > 0:
                        value = (metrics_data["memory"]["used_mb"] / total) * 100
        elif metric_type == "disk":
            if "disks" in metrics_data and len(metrics_data["disks"]) > 0:
                # 使用第一个磁盘的使用率
                for disk in metrics_data["disks"]:
                    if "usage_percent" in disk:
                        value = disk["usage_percent"]
                        break
        elif metric_type == "network":
            if "network" in metrics_data and "bandwidth_mbps" in metrics_data["network"]:
                value = metrics_data["network"]["bandwidth_mbps"]
        
        if value is None:
            raise HTTPException(status_code=404, detail=f"设备无{metric_type}指标数据: {device_name}")
        
        # 生成时间序列数据点（从当前时间往前推hours小时，每5分钟一个点）
        # 由于只有最新数据，我们用最新数据填充
        now = datetime.now()
        points = []
        for i in range(hours * 12):  # 每5分钟一个点
            timestamp = now - timedelta(minutes=5 * (hours * 12 - 1 - i))
            points.append({
                "timestamp": timestamp.isoformat(),
                "value": value
            })
        
        return {
            "device_name": device_name,
            "metric_type": metric_type,
            "points": points,
            "latest_value": value,
            "latest_timestamp": last_metrics.timestamp.isoformat() if last_metrics.timestamp else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取设备指标历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 采集项配置接口 ==============

class MetricConfigUpdateRequest(BaseModel):
    """采集项配置更新请求"""
    enabled: Optional[bool] = Field(None, description="是否启用采集")
    collect_interval: Optional[int] = Field(None, description="采集间隔(秒)")
    params: Optional[str] = Field(None, description="自定义参数配置(JSON)")


class MetricConfigResponse(BaseModel):
    """采集项配置响应"""
    id: int
    device_id: int
    device_name: str
    metric_category: str
    metric_name: str
    enabled: bool
    collect_interval: int
    params: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.patch("/{device_id}/metrics/{metric}", summary="更新设备指标采集配置")
async def update_device_metric_config(
    device_id: int,
    metric: str,
    request: MetricConfigUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    更新设备特定指标采集项的配置
    支持启用/禁用采集、调整采集间隔、自定义参数
    """
    try:
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from modules.foundation.db.client import get_db_session
        
        with get_db_session() as session:
            # 查找现有配置
            config = session.query(DeviceMetricConfig).filter(
                DeviceMetricConfig.device_id == device_id,
                DeviceMetricConfig.metric_name == metric
            ).first()
            
            if config is None:
                # 如果不存在，创建新配置
                config = DeviceMetricConfig(
                    device_id=device_id,
                    device_name=f"device_{device_id}",  # 后续可通过device manager获取真实名称
                    metric_category='general',  # 默认分类
                    metric_name=metric,
                    enabled=request.enabled if request.enabled is not None else True,
                    collect_interval=request.collect_interval if request.collect_interval else 0,
                    params=request.params,
                    created_by=current_user.username,
                    updated_by=current_user.username,
                )
                session.add(config)
                session.commit()
                session.refresh(config)
                status = "created"
            else:
                # 更新现有配置
                if request.enabled is not None:
                    config.enabled = request.enabled
                if request.collect_interval is not None:
                    config.collect_interval = request.collect_interval
                if request.params is not None:
                    config.params = request.params
                config.updated_by = current_user.username
                session.commit()
                session.refresh(config)
                status = "success"
            
            return {
                "status": status,
                "message": f"Metric {metric} configuration updated",
                "data": config.to_dict()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新设备指标配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}/metrics/{metric}/config", summary="获取设备指标配置")
async def get_device_metric_config(
    device_id: int,
    metric: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取设备特定指标的采集配置
    """
    try:
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from modules.foundation.db.client import get_db_session
        
        with get_db_session() as session:
            config = session.query(DeviceMetricConfig).filter(
                DeviceMetricConfig.device_id == device_id,
                DeviceMetricConfig.metric_name == metric
            ).first()
            
            if not config:
                raise HTTPException(status_code=404, detail=f"Metric config not found for device {device_id}, metric {metric}")
            
            return {
                "status": "success",
                "data": config.to_dict()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取设备指标配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}/metrics/configs", summary="获取设备所有指标配置")
async def list_device_metric_configs(
    device_id: int,
    metric_category: Optional[str] = Query(None, description="指标类别过滤"),
    enabled: Optional[bool] = Query(None, description="启用状态过滤"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取设备所有指标的采集配置
    """
    try:
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from modules.foundation.db.client import get_db_session
        
        with get_db_session() as session:
            query = session.query(DeviceMetricConfig).filter(
                DeviceMetricConfig.device_id == device_id
            )
            
            if metric_category:
                query = query.filter(DeviceMetricConfig.metric_category == metric_category)
            if enabled is not None:
                query = query.filter(DeviceMetricConfig.enabled == enabled)
            
            configs = query.all()
            
            return {
                "status": "success",
                "data": [c.to_dict() for c in configs],
                "total": len(configs)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取设备指标配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 适配器接口 ==============

@router.get("/adapters/list", summary="获取支持的适配器列表")
async def list_adapters(
    protocol: Optional[str] = Query(None, description="协议类型过滤"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取所有已注册的采集适配器
    """
    try:
        from modules.collection.adapter_registry import get_registry, ProtocolType
        
        registry = get_registry()
        
        if protocol:
            try:
                protocol_enum = ProtocolType(protocol.lower())
                adapters = registry.list_adapters(protocol_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"未知协议: {protocol}")
        else:
            adapters = registry.list_adapters()
        
        return {
            "items": [
                {
                    "name": a.name,
                    "protocol": a.protocol.value,
                    "default_port": a.default_port,
                    "capabilities": a.capabilities,
                    "required_credentials": a.required_credentials,
                    "optional_credentials": a.optional_credentials,
                    "description": a.description,
                    "version": a.version,
                }
                for a in adapters
            ],
            "total": len(adapters),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取适配器列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adapters/protocols", summary="获取支持的协议列表")
async def list_protocols(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取所有支持的协议类型
    """
    from modules.collection.adapter_registry import ProtocolType
    
    return {
        "items": [
            {"name": p.value, "description": p.name}
            for p in ProtocolType
        ],
        "total": len(ProtocolType),
    }


# ============== 配置接口 ==============

@router.post("/config/reload", summary="重新加载配置")
async def reload_config(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    重新从配置文件加载设备配置
    """
    try:
        from modules.collection.config_loader import reload_config
        
        reload_config()
        
        return {
            "status": "success",
            "message": "配置已重新加载",
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/stats", summary="获取配置统计")
async def get_config_stats(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取配置统计信息
    """
    try:
        from modules.collection.config_loader import get_config_loader
        
        loader = get_config_loader()
        stats = loader.get_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"获取配置统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
