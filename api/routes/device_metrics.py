"""
设备采集精细化开关API路由

提供设备指标采集项的精细化配置管理:
- GET /api/v1/devices/{id}/metrics - 获取设备所有指标配置
- PATCH /api/v1/devices/{id}/metrics - 更新设备指标配置
- GET /api/v1/devices/{id}/metrics/categories - 获取所有指标类别
- POST /api/v1/devices/{id}/metrics/bulk - 批量更新指标配置

响应格式: {"data":..., "code":0, "message":"success"}
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["采集精细化开关"], prefix="/api/v1/devices")


# ============== 请求/响应模型 ==============

class MetricConfigItem(BaseModel):
    """指标配置项"""
    metric_name: str = Field(..., description="指标名称")
    metric_category: str = Field(..., description="指标类别")
    enabled: bool = Field(True, description="是否启用")
    collect_interval: int = Field(0, description="采集间隔(秒),0表示使用默认")
    params: Optional[str] = Field(None, description="自定义参数(JSON)")


class MetricConfigUpdateRequest(BaseModel):
    """更新单个指标配置请求"""
    metric_name: str = Field(..., description="指标名称")
    metric_category: Optional[str] = Field(None, description="指标类别")
    enabled: Optional[bool] = Field(None, description="是否启用")
    collect_interval: Optional[int] = Field(None, description="采集间隔(秒)")
    params: Optional[str] = Field(None, description="自定义参数(JSON)")


class BulkMetricConfigRequest(BaseModel):
    """批量更新指标配置请求"""
    configs: List[MetricConfigItem] = Field(..., description="配置列表")


class MetricCategoryResponse(BaseModel):
    """指标类别响应"""
    categories: List[Dict[str, Any]] = Field(..., description="类别列表")


# ============== 标准响应格式 ==============

def success_response(data: Any = None, message: str = "success", code: int = 0) -> Dict[str, Any]:
    """构建成功响应"""
    return {
        "code": code,
        "message": message,
        "data": data
    }


def error_response(message: str, code: int = 1, data: Any = None) -> Dict[str, Any]:
    """构建错误响应"""
    return {
        "code": code,
        "message": message,
        "data": data
    }


# ============== API 端点 ==============

@router.get("/{device_id}/metrics", summary="获取设备所有指标配置")
async def get_device_metrics(
    device_id: int,
    metric_category: Optional[str] = Query(None, description="指标类别过滤"),
    enabled: Optional[bool] = Query(None, description="启用状态过滤"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取指定设备的所有指标采集配置
    
    - **device_id**: 设备ID
    - **metric_category**: 按指标类别过滤(如cpu, memory, disk等)
    - **enabled**: 按启用状态过滤
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
            
            return success_response(
                data={
                    "device_id": device_id,
                    "configs": [c.to_dict() for c in configs],
                    "total": len(configs)
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取设备指标配置失败: {e}")
        return error_response(message=f"获取设备指标配置失败: {str(e)}")


@router.patch("/{device_id}/metrics", summary="更新设备指标配置")
async def update_device_metric(
    device_id: int,
    request: MetricConfigUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    更新设备特定指标采集项的配置
    
    - **device_id**: 设备ID
    - **metric_name**: 指标名称(必需)
    - **metric_category**: 指标类别(可选)
    - **enabled**: 是否启用采集
    - **collect_interval**: 采集间隔(秒),0表示使用默认
    - **params**: 自定义参数(JSON格式)
    """
    try:
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from modules.foundation.db.client import get_db_session
        
        with get_db_session() as session:
            # 查找现有配置
            config = session.query(DeviceMetricConfig).filter(
                DeviceMetricConfig.device_id == device_id,
                DeviceMetricConfig.metric_name == request.metric_name
            ).first()
            
            if config is None:
                # 如果不存在，创建新配置
                config = DeviceMetricConfig(
                    device_id=device_id,
                    device_name=f"device_{device_id}",
                    metric_category=request.metric_category or 'general',
                    metric_name=request.metric_name,
                    enabled=request.enabled if request.enabled is not None else True,
                    collect_interval=request.collect_interval if request.collect_interval else 0,
                    params=request.params,
                    created_by=current_user.username,
                    updated_by=current_user.username,
                )
                session.add(config)
                session.commit()
                session.refresh(config)
                action = "created"
            else:
                # 更新现有配置
                if request.enabled is not None:
                    config.enabled = request.enabled
                if request.collect_interval is not None:
                    config.collect_interval = request.collect_interval
                if request.params is not None:
                    config.params = request.params
                if request.metric_category is not None:
                    config.metric_category = request.metric_category
                config.updated_by = current_user.username
                session.commit()
                session.refresh(config)
                action = "updated"
            
            return success_response(
                data={
                    "action": action,
                    "config": config.to_dict()
                },
                message=f"Metric {request.metric_name} configuration {action}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新设备指标配置失败: {e}")
        return error_response(message=f"更新设备指标配置失败: {str(e)}")


@router.get("/{device_id}/metrics/categories", summary="获取设备支持的指标类别")
async def get_metric_categories(
    device_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取设备支持的所有指标类别及其默认配置
    
    - **device_id**: 设备ID
    """
    try:
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from modules.foundation.db.client import get_db_session
        
        # 预定义的指标类别及其说明
        DEFAULT_CATEGORIES = [
            {
                "category": "cpu",
                "name": "CPU",
                "description": "CPU相关指标",
                "metrics": ["cpu_usage_percent", "cpu_user_percent", "cpu_system_percent", "cpu_idle_percent", "cpu_iowait_percent"]
            },
            {
                "category": "memory",
                "name": "内存",
                "description": "内存相关指标",
                "metrics": ["memory_usage_percent", "memory_available_percent", "memory_swap_percent", "memory_cached_percent"]
            },
            {
                "category": "disk",
                "name": "磁盘",
                "description": "磁盘相关指标",
                "metrics": ["disk_usage_percent", "disk_read_bytes", "disk_write_bytes", "disk_read_count", "disk_write_count", "disk_inode_percent"]
            },
            {
                "category": "network",
                "name": "网络",
                "description": "网络相关指标",
                "metrics": ["network_in_bytes", "network_out_bytes", "network_in_packets", "network_out_packets", "network_error_percent", "network_tcp_connections"]
            },
            {
                "category": "process",
                "name": "进程",
                "description": "进程相关指标",
                "metrics": ["process_count", "thread_count", "file_descriptor_count", "zombie_process_count"]
            },
            {
                "category": "system",
                "name": "系统",
                "description": "系统相关指标",
                "metrics": ["load_average_1min", "load_average_5min", "load_average_15min", "uptime_days", "system_entropy"]
            },
            {
                "category": "service",
                "name": "服务",
                "description": "服务相关指标",
                "metrics": ["service_status", "service_response_time", "service_uptime"]
            },
            {
                "category": "security",
                "name": "安全",
                "description": "安全相关指标",
                "metrics": ["login_failures", "sudo_usage", "selinux_status", "firewall_status"]
            }
        ]
        
        # 获取设备已配置的类别
        with get_db_session() as session:
            configured_categories = session.query(DeviceMetricConfig.metric_category).filter(
                DeviceMetricConfig.device_id == device_id
            ).distinct().all()
            
            configured_set = {c[0] for c in configured_categories}
        
        # 合并结果，标记已配置的类别
        result = []
        for cat in DEFAULT_CATEGORIES:
            cat_copy = cat.copy()
            cat_copy["has_custom_config"] = cat_copy["category"] in configured_set
            result.append(cat_copy)
        
        return success_response(
            data={
                "device_id": device_id,
                "categories": result,
                "total": len(result)
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指标类别失败: {e}")
        return error_response(message=f"获取指标类别失败: {str(e)}")


@router.post("/{device_id}/metrics/bulk", summary="批量更新设备指标配置")
async def bulk_update_metrics(
    device_id: int,
    request: BulkMetricConfigRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    批量更新设备的多个指标采集配置
    
    - **device_id**: 设备ID
    - **configs**: 配置列表，每个配置包含:
        - metric_name: 指标名称(必需)
        - metric_category: 指标类别(必需)
        - enabled: 是否启用(可选)
        - collect_interval: 采集间隔(可选)
        - params: 自定义参数(可选)
    """
    try:
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from modules.foundation.db.client import get_db_session
        
        results = {
            "created": [],
            "updated": [],
            "failed": []
        }
        
        with get_db_session() as session:
            for item in request.configs:
                try:
                    # 查找现有配置
                    config = session.query(DeviceMetricConfig).filter(
                        DeviceMetricConfig.device_id == device_id,
                        DeviceMetricConfig.metric_name == item.metric_name
                    ).first()
                    
                    if config is None:
                        # 创建新配置
                        config = DeviceMetricConfig(
                            device_id=device_id,
                            device_name=f"device_{device_id}",
                            metric_category=item.metric_category,
                            metric_name=item.metric_name,
                            enabled=item.enabled,
                            collect_interval=item.collect_interval,
                            params=item.params,
                            created_by=current_user.username,
                            updated_by=current_user.username,
                        )
                        session.add(config)
                        results["created"].append(item.metric_name)
                    else:
                        # 更新现有配置
                        config.enabled = item.enabled
                        config.collect_interval = item.collect_interval
                        if item.params:
                            config.params = item.params
                        config.updated_by = current_user.username
                        results["updated"].append(item.metric_name)
                        
                except Exception as e:
                    results["failed"].append({
                        "metric_name": item.metric_name,
                        "error": str(e)
                    })
            
            session.commit()
        
        return success_response(
            data={
                "device_id": device_id,
                "results": results,
                "total_created": len(results["created"]),
                "total_updated": len(results["updated"]),
                "total_failed": len(results["failed"])
            },
            message=f"批量更新完成: 创建{len(results['created'])}个,更新{len(results['updated'])}个,失败{len(results['failed'])}个"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量更新设备指标配置失败: {e}")
        return error_response(message=f"批量更新设备指标配置失败: {str(e)}")


# ============== 直接通过device_name的端点 ==============

@router.get("/name/{device_name}/metrics", summary="通过设备名获取指标配置")
async def get_device_metrics_by_name(
    device_name: str,
    metric_category: Optional[str] = Query(None, description="指标类别过滤"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    通过设备名称获取设备的所有指标采集配置
    """
    try:
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from modules.foundation.db.client import get_db_session
        
        with get_db_session() as session:
            query = session.query(DeviceMetricConfig).filter(
                DeviceMetricConfig.device_name == device_name
            )
            
            if metric_category:
                query = query.filter(DeviceMetricConfig.metric_category == metric_category)
            
            configs = query.all()
            
            return success_response(
                data={
                    "device_name": device_name,
                    "configs": [c.to_dict() for c in configs],
                    "total": len(configs)
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取设备指标配置失败: {e}")
        return error_response(message=f"获取设备指标配置失败: {str(e)}")


@router.patch("/name/{device_name}/metrics", summary="通过设备名更新指标配置")
async def update_device_metric_by_name(
    device_name: str,
    request: MetricConfigUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    通过设备名称更新设备特定指标采集项的配置
    """
    try:
        from modules.foundation.db_models.monitoring import DeviceMetricConfig
        from modules.foundation.db.client import get_db_session
        
        with get_db_session() as session:
            config = session.query(DeviceMetricConfig).filter(
                DeviceMetricConfig.device_name == device_name,
                DeviceMetricConfig.metric_name == request.metric_name
            ).first()
            
            if config is None:
                config = DeviceMetricConfig(
                    device_id=0,  # 通过device_name定位，device_id可能为0
                    device_name=device_name,
                    metric_category=request.metric_category or 'general',
                    metric_name=request.metric_name,
                    enabled=request.enabled if request.enabled is not None else True,
                    collect_interval=request.collect_interval if request.collect_interval else 0,
                    params=request.params,
                    created_by=current_user.username,
                    updated_by=current_user.username,
                )
                session.add(config)
                session.commit()
                session.refresh(config)
                action = "created"
            else:
                if request.enabled is not None:
                    config.enabled = request.enabled
                if request.collect_interval is not None:
                    config.collect_interval = request.collect_interval
                if request.params is not None:
                    config.params = request.params
                if request.metric_category is not None:
                    config.metric_category = request.metric_category
                config.updated_by = current_user.username
                session.commit()
                session.refresh(config)
                action = "updated"
            
            return success_response(
                data={
                    "action": action,
                    "device_name": device_name,
                    "config": config.to_dict()
                },
                message=f"Metric {request.metric_name} configuration {action}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新设备指标配置失败: {e}")
        return error_response(message=f"更新设备指标配置失败: {str(e)}")
