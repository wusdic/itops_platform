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

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["设备管理"])


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

@router.get("/", summary="获取设备列表")
async def list_devices(
    device_type: Optional[str] = Query(None, description="设备类型过滤"),
    vendor: Optional[str] = Query(None, description="厂商过滤"),
    enabled: Optional[bool] = Query(None, description="是否启用"),
    tag: Optional[str] = Query(None, description="标签过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取设备列表
    支持分页和过滤
    """
    try:
        from modules.collection.device_manager import get_device_manager
        from modules.collection.config_loader import get_config_loader
        
        manager = get_device_manager()
        loader = get_config_loader()
        
        # 获取设备配置
        devices = loader.get_devices(
            enabled_only=enabled,
            device_type=device_type,
            vendor=vendor,
            tag=tag,
        )
        
        # 应用分页
        total = len(devices)
        start = (pagination.page - 1) * pagination.page_size
        end = start + pagination.page_size
        paginated_devices = devices[start:end]
        
        # 转换为响应格式
        items = []
        for dev in paginated_devices:
            # 获取设备状态
            status = manager.get_device_status(dev.get('name'))
            last_metrics = manager.get_last_metrics(dev.get('name'))
            
            items.append({
                "name": dev.get("name"),
                "ip": dev.get("ip"),
                "type": dev.get("type"),
                "os": dev.get("os"),
                "os_version": dev.get("os_version"),
                "vendor": dev.get("vendor"),
                "protocols": dev.get("protocols", {}),
                "collect_enabled": dev.get("collect", {}).get("enabled", True),
                "collect_interval": dev.get("collect", {}).get("interval", 60),
                "tags": dev.get("tags", {}),
                "status": status.value if status else "unknown",
                "last_collect_time": last_metrics.timestamp.isoformat() if last_metrics and last_metrics.timestamp else None,
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
):
    """
    获取设备统计信息
    """
    try:
        from modules.collection.device_manager import get_device_manager
        from modules.collection.config_loader import get_config_loader
        
        manager = get_device_manager()
        loader = get_config_loader()
        
        devices = loader.get_devices()
        
        stats = {
            "total": len(devices),
            "online": 0,
            "offline": 0,
            "unknown": 0,
            "by_type": {},
            "by_vendor": {},
        }
        
        for dev in devices:
            dev_type = dev.get("type", "unknown")
            vendor = dev.get("vendor", "unknown")
            
            stats["by_type"][dev_type] = stats["by_type"].get(dev_type, 0) + 1
            stats["by_vendor"][vendor] = stats["by_vendor"].get(vendor, 0) + 1
            
            status = manager.get_device_status(dev.get("name"))
            if status:
                if status.value == "online":
                    stats["online"] += 1
                elif status.value == "offline":
                    stats["offline"] += 1
                else:
                    stats["unknown"] += 1
            else:
                stats["unknown"] += 1
        
        return stats
        
    except Exception as e:
        logger.error(f"获取设备统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_name}", summary="获取设备详情")
async def get_device(
    device_name: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取指定设备的详细信息
    """
    try:
        from modules.collection.device_manager import get_device_manager
        from modules.collection.config_loader import get_config_loader
        
        manager = get_device_manager()
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
