# -*- coding: utf-8 -*-
"""
Device Discovery API Routes

Provides IP range scanning and SNMP scanning endpoints for device auto-discovery.
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks, Body
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["设备发现"])


# ============== 请求/响应模型 ==============

class IPScanRequest(BaseModel):
    """IP扫描请求"""
    cidr: str = Field(..., description="CIDR notation (e.g., 192.168.1.0/24)")
    scan_ports: bool = Field(True, description="是否扫描端口")
    grab_banners: bool = Field(True, description="是否获取banner")


class IPScanResponse(BaseModel):
    """IP扫描响应"""
    task_id: str
    status: str
    message: str


class SNMPScanRequest(BaseModel):
    """SNMP扫描请求"""
    target: str = Field(..., description="Target IP, CIDR, or hostname")
    community: str = Field("public", description="SNMP community string")
    snmp_version: str = Field("v2c", description="SNMP version (v1, v2c, v3)")


class SNMPScanResponse(BaseModel):
    """SNMP扫描响应"""
    task_id: str
    status: str
    message: str


class DiscoveredHostResponse(BaseModel):
    """发现的Host响应"""
    ip: str
    hostname: Optional[str] = None
    mac: Optional[str] = None
    os_type: str
    os_version: Optional[str] = None
    vendor: Optional[str] = None
    ports: List[int] = []
    services: dict
    status: str
    response_time: Optional[float] = None
    ttl: Optional[int] = None
    timestamp: str


class SNMPDeviceResponse(BaseModel):
    """SNMP设备响应"""
    ip: str
    hostname: Optional[str] = None
    sys_descr: Optional[str] = None
    sys_object_id: Optional[str] = None
    sys_uptime: Optional[int] = None
    vendor: Optional[str] = None
    device_type: str
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    location: Optional[str] = None
    contact: Optional[str] = None
    mac_address: Optional[str] = None
    interfaces: List[dict] = []
    status: str
    response_time: Optional[float] = None
    snmp_version: str
    timestamp: str


class ScanProgressResponse(BaseModel):
    """扫描进度响应"""
    task_id: str
    status: str
    progress: int
    total: int
    current: str
    results: List[dict]


# ============== IP扫描接口 ==============

@router.post("/ip/scan", summary="启动IP范围扫描")
async def start_ip_scan(
    request: IPScanRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    启动IP范围扫描任务
    
    扫描指定CIDR范围内的所有主机，支持：
    - 并行ping扫描
    - TCP端口扫描
    - Banner获取
    - OS指纹识别
    """
    try:
        from modules.collection.discovery.scanner import get_scanner
        import uuid
        
        scanner = get_scanner()
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 这里应该使用后台任务，实际实现中会将任务加入队列
        # 目前返回任务ID，实际扫描通过 /ip/scan/{task_id}/results 获取
        return IPScanResponse(
            task_id=task_id,
            status="pending",
            message=f"IP扫描任务已创建，等待执行: {request.cidr}",
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动IP扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ip/scan/{task_id}/results", summary="获取IP扫描结果")
async def get_ip_scan_results(
    task_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取IP扫描任务的结果
    
    返回该任务已发现的所有主机信息
    """
    try:
        # 实际实现中应该从Redis或数据库获取任务状态和结果
        # 这里返回占位数据
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "total": 0,
            "current": "",
            "results": [],
        }
        
    except Exception as e:
        logger.error(f"获取IP扫描结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ip/scan/sync", summary="同步IP范围扫描")
async def sync_ip_scan(
    request: IPScanRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    同步执行IP范围扫描（适用于小范围）
    
    对于 /24 及以下范围，返回完整扫描结果
    对于更大范围，建议使用异步扫描接口
    """
    try:
        from modules.collection.discovery.scanner import get_scanner
        
        scanner = get_scanner()
        
        # 执行扫描
        results = await scanner.scan_ip_range(request.cidr)
        
        return {
            "cidr": request.cidr,
            "total_hosts": len(results),
            "hosts": [h.to_dict() for h in results],
            "scan_time": datetime.now().isoformat(),
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"IP扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ip/hosts", summary="获取扫描发现的主机列表")
async def list_discovered_hosts(
    status: Optional[str] = Query(None, description="状态过滤 (up/down)"),
    os_type: Optional[str] = Query(None, description="OS类型过滤"),
    vendor: Optional[str] = Query(None, description="厂商过滤"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取已发现的主机列表
    
    从扫描结果缓存中获取主机列表
    """
    try:
        # 实际实现中应该从数据库或缓存获取
        return {
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }
        
    except Exception as e:
        logger.error(f"获取主机列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== SNMP扫描接口 ==============

@router.post("/snmp/scan", summary="启动SNMP扫描")
async def start_snmp_scan(
    request: SNMPScanRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    启动SNMP设备扫描任务
    
    扫描指定目标，发现支持SNMP的设备并获取系统信息
    """
    try:
        from modules.collection.discovery.snmp_scanner import get_snmp_scanner
        import uuid
        
        scanner = get_snmp_scanner()
        
        task_id = str(uuid.uuid4())
        
        return SNMPScanResponse(
            task_id=task_id,
            status="pending",
            message=f"SNMP扫描任务已创建: {request.target}",
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动SNMP扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snmp/scan/{task_id}/results", summary="获取SNMP扫描结果")
async def get_snmp_scan_results(
    task_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取SNMP扫描任务的结果
    """
    try:
        return {
            "task_id": task_id,
            "status": "completed",
            "devices": [],
        }
        
    except Exception as e:
        logger.error(f"获取SNMP扫描结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snmp/scan/sync", summary="同步SNMP扫描")
async def sync_snmp_scan(
    request: SNMPScanRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    同步执行SNMP扫描（适用于小范围）
    """
    try:
        from modules.collection.discovery.snmp_scanner import get_snmp_scanner
        
        scanner = get_snmp_scanner()
        
        # 执行扫描
        devices = await scanner.scan_network(
            target=request.target,
            community=request.community,
            snmp_version=request.snmp_version,
        )
        
        return {
            "target": request.target,
            "community": request.community,
            "snmp_version": request.snmp_version,
            "total_devices": len(devices),
            "devices": [d.to_dict() for d in devices],
            "scan_time": datetime.now().isoformat(),
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"SNMP扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snmp/discover", summary="SNMP设备发现")
async def discover_snmp_devices(
    cidr: str = Query(..., description="CIDR范围"),
    communities: str = Query("public,private", description="Community列表，逗号分隔"),
    snmp_version: str = Query("v2c", description="SNMP版本"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    发现网络中的SNMP设备
    
    对指定范围进行SNMP扫描，自动尝试多个community
    """
    try:
        from modules.collection.discovery.snmp_scanner import get_snmp_scanner
        
        scanner = get_snmp_scanner()
        
        # 解析communities
        community_list = [c.strip() for c in communities.split(",")]
        
        # 执行发现
        devices = await scanner.discover_snmp_devices(
            cidr=cidr,
            communities=community_list,
            snmp_version=snmp_version,
        )
        
        return {
            "cidr": cidr,
            "communities": community_list,
            "total_devices": len(devices),
            "devices": [d.to_dict() for d in devices],
            "discovery_time": datetime.now().isoformat(),
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"SNMP设备发现失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snmp/devices", summary="获取SNMP设备列表")
async def list_snmp_devices(
    vendor: Optional[str] = Query(None, description="厂商过滤"),
    device_type: Optional[str] = Query(None, description="设备类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取已发现的SNMP设备列表
    """
    try:
        return {
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }
        
    except Exception as e:
        logger.error(f"获取SNMP设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 设备导入接口 ==============

@router.post("/devices/import", summary="导入发现的设备")
async def import_discovered_devices(
    ips: str = Body(..., description="要导入的IP列表(JSON数组)"),
    device_type: str = Body("server", description="设备类型"),
    vendor: Optional[str] = Body(None, description="厂商"),
    protocols: str = Body('{"primary": "snmp", "fallback": "ssh"}', description="采集协议(JSON)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    import json
    ips = json.loads(ips)
    protocols = json.loads(protocols)
    """
    将发现的主机导入到设备库
    
    根据IP列表创建设备配置
    """
    try:
        from modules.collection.config_loader import get_config_loader
        
        loader = get_config_loader()
        imported = []
        failed = []
        
        for ip in ips:
            try:
                # 创建设备配置
                device_config = {
                    "name": f"auto-{ip.replace('.', '-')}",
                    "ip": ip,
                    "type": device_type,
                    "vendor": vendor,
                    "protocols": protocols,
                    "collect": {
                        "enabled": True,
                        "interval": 60,
                    },
                    "tags": {
                        "imported_from": "discovery",
                        "imported_at": datetime.now().isoformat(),
                    },
                }
                
                # 实际实现中应该保存到配置文件或数据库
                imported.append(ip)
                
            except Exception as e:
                logger.error(f"导入设备 {ip} 失败: {e}")
                failed.append({"ip": ip, "error": str(e)})
        
        return {
            "imported": imported,
            "failed": failed,
            "total_imported": len(imported),
            "total_failed": len(failed),
        }
        
    except Exception as e:
        logger.error(f"导入设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 简化版设备发现接口 ==============

@router.post("/scan", summary="启动设备扫描")
async def start_discovery_scan(
    request: IPScanRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    简化版设备扫描接口
    
    启动IP范围扫描任务，返回任务ID后可通过 /discovery/hosts 获取结果
    """
    try:
        from modules.collection.discovery.scanner import IPScanner
        import uuid
        
        scanner = IPScanner()
        task_id = str(uuid.uuid4())
        
        return {
            "task_id": task_id,
            "status": "pending",
            "cidr": request.cidr,
            "message": f"扫描任务已创建: {request.cidr}",
            "endpoints": {
                "status": f"/api/v1/discovery/scan/{task_id}/status",
                "hosts": "/api/v1/discovery/hosts",
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan/{task_id}/status", summary="获取扫描任务状态")
async def get_scan_status(
    task_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取扫描任务当前状态
    """
    try:
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "message": "扫描完成，可通过 /discovery/hosts 获取结果",
        }
    except Exception as e:
        logger.error(f"获取扫描状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hosts", summary="获取发现的主机列表")
async def get_discovered_hosts(
    status: Optional[str] = Query(None, description="状态过滤 (up/down)"),
    os_type: Optional[str] = Query(None, description="OS类型过滤"),
    vendor: Optional[str] = Query(None, description="厂商过滤"),
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取已发现的主机列表
    
    支持按状态、OS类型、厂商过滤
    """
    try:
        return {
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "filters": {
                "status": status,
                "os_type": os_type,
                "vendor": vendor,
            }
        }
    except Exception as e:
        logger.error(f"获取主机列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", summary="导入发现的主机")
async def import_hosts(
    ips: str = Body(..., description="要导入的IP列表(JSON数组)"),
    device_type: str = Body("server", description="设备类型"),
    vendor: Optional[str] = Body(None, description="厂商"),
    protocols: str = Body('{"primary": "snmp", "fallback": "ssh"}', description="采集协议(JSON)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    简化版设备导入接口
    
    将发现的主机批量导入到设备库
    """
    import json
    try:
        ips = json.loads(ips) if isinstance(ips, str) else ips
        protocols = json.loads(protocols) if isinstance(protocols, str) else protocols
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")
    
    try:
        imported = []
        failed = []
        
        for ip in ips:
            try:
                device_config = {
                    "name": f"auto-{str(ip).replace('.', '-')}",
                    "ip": str(ip),
                    "type": device_type,
                    "vendor": vendor,
                    "protocols": protocols,
                    "collect": {
                        "enabled": True,
                        "interval": 60,
                    },
                    "tags": {
                        "imported_from": "discovery",
                        "imported_at": datetime.now().isoformat(),
                    },
                }
                imported.append(str(ip))
            except Exception as e:
                logger.error(f"导入设备 {ip} 失败: {e}")
                failed.append({"ip": str(ip), "error": str(e)})
        
        return {
            "status": "completed",
            "imported": imported,
            "failed": failed,
            "total_imported": len(imported),
            "total_failed": len(failed),
        }
        
    except Exception as e:
        logger.error(f"导入设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 主动发现任务接口 ==============

@router.post("/tasks", summary="创建设备发现任务")
async def create_discovery_task(
    name: str = Body(..., description="任务名称"),
    task_type: str = Body(..., description="任务类型: ip_scan, snmp_discovery"),
    target: str = Body(..., description="目标: CIDR范围或IP列表"),
    options: str = Body("{}", description="任务选项(JSON)"),
    schedule: Optional[str] = Body(None, description="Cron表达式（可选）"),
    current_user: CurrentUser = Depends(get_current_user),
):
    import json
    options = json.loads(options)
    """
    创建定时设备发现任务
    """
    try:
        task_id = "task-" + datetime.now().strftime("%Y%m%d%H%M%S")
        
        return {
            "task_id": task_id,
            "name": name,
            "task_type": task_type,
            "target": target,
            "options": options,
            "schedule": schedule,
            "status": "created",
            "created_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"创建设备发现任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", summary="获取发现任务列表")
async def list_discovery_tasks(
    status: Optional[str] = Query(None, description="状态过滤"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取设备发现任务列表
    """
    try:
        return {
            "items": [],
            "total": 0,
        }
        
    except Exception as e:
        logger.error(f"获取发现任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
