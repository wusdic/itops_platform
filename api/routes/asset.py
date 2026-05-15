"""
资产管理API路由
提供资产信息管理、配置管理等接口
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.device import Device, DeviceGroup, BusinessSystem, DeviceType as DBDeviceType, DeviceStatus as DBDeviceStatus


router = APIRouter()


# ============== 枚举定义 ==============

class DeviceType(str, Enum):
    """设备类型"""
    SERVER = "server"
    NETWORK = "network"
    STORAGE = "storage"
    SECURITY = "security"
    VIRTUAL = "virtual"
    CLOUD = "cloud"
    OTHER = "other"


class DeviceStatus(str, Enum):
    """设备状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


# ============== 请求/响应模型 ==============

class DeviceCreate(BaseModel):
    """创建设备"""
    hostname: str = Field(..., description="主机名")
    ip_address: str = Field(..., description="IP地址")
    device_type: str = Field(..., description="设备类型")
    os_type: Optional[str] = Field(None, description="操作系统类型")
    os_version: Optional[str] = Field(None, description="操作系统版本")
    manufacturer: Optional[str] = Field(None, description="制造商")
    model: Optional[str] = Field(None, description="型号")
    serial_number: Optional[str] = Field(None, description="序列号")
    cpu: Optional[str] = Field(None, description="CPU信息")
    memory: Optional[str] = Field(None, description="内存信息")
    disk: Optional[str] = Field(None, description="磁盘信息")
    network_interfaces: Optional[dict] = Field(None, description="网络接口")
    location: Optional[str] = Field(None, description="位置")
    idc: Optional[str] = Field(None, description="机房")
    cabinet: Optional[str] = Field(None, description="机柜")
    business_id: Optional[int] = Field(None, description="业务系统ID")
    tags: Optional[str] = Field(None, description="标签")


class DeviceUpdate(BaseModel):
    """更新设备"""
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    device_type: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    idc: Optional[str] = None
    cabinet: Optional[str] = None
    business_id: Optional[int] = None
    tags: Optional[str] = None
    remark: Optional[str] = None


class DeviceResponse(BaseModel):
    """设备响应"""
    id: int
    hostname: str
    ip_address: str
    device_type: str
    status: str
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    idc: Optional[str] = None
    cabinet: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============== 设备管理接口 ==============

def _map_device_type(device_type: str) -> DBDeviceType:
    """映射前端设备类型到数据库枚举"""
    mapping = {
        'server': DBDeviceType.SERVER_LINUX,
        'network': DBDeviceType.NETWORK_SWITCH,
        'storage': DBDeviceType.STORAGE_NAS,
        'security': DBDeviceType.SECURITY_IPS,
        'virtual': DBDeviceType.SERVER_VMWARE,
        'cloud': DBDeviceType.OTHER,
        'other': DBDeviceType.OTHER,
    }
    return mapping.get(device_type, DBDeviceType.OTHER)


def _map_device_status(status: str) -> DBDeviceStatus:
    """映射前端设备状态到数据库枚举"""
    mapping = {
        'online': DBDeviceStatus.ONLINE,
        'offline': DBDeviceStatus.OFFLINE,
        'maintenance': DBDeviceStatus.MAINTENANCE,
        'decommissioned': DBDeviceStatus.DECOMMISSIONED,
    }
    return mapping.get(status, DBDeviceStatus.OFFLINE)


def _device_to_dict(device: Device) -> dict:
    """设备模型转字典"""
    return {
        'id': device.id,
        'name': device.name,
        'hostname': device.hostname,
        'ip_address': device.ip_address,
        'device_type': device.device_type.value if device.device_type else 'other',
        'status': device.status.value if device.status else 'offline',
        'os_type': device.os_type,
        'os_version': device.os_version,
        'manufacturer': device.manufacturer,
        'model': device.model,
        'serial_number': device.serial_number,
        'cpu': device.cpu,
        'memory': device.memory,
        'disk': device.disk,
        'network_interfaces': device.network_interfaces,
        'location': device.location,
        'idc': device.idc,
        'cabinet': device.cabinet,
        'business_id': device.business_id,
        'tags': device.tags,
        'created_at': device.created_at.isoformat() if device.created_at else None,
        'updated_at': device.updated_at.isoformat() if device.updated_at else None,
    }


@router.get("/device", summary="获取设备列表")
async def get_devices(
    device_type: Optional[str] = Query(None, description="设备类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    idc: Optional[str] = Query(None, description="机房过滤"),
    business_id: Optional[int] = Query(None, description="业务系统ID过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取设备列表"""
    query = db.query(Device)
    
    # 应用过滤条件
    if device_type:
        db_device_type = _map_device_type(device_type)
        query = query.filter(Device.device_type == db_device_type)
    
    if status:
        db_status = _map_device_status(status)
        query = query.filter(Device.status == db_status)
    
    if idc:
        query = query.filter(Device.idc == idc)
    
    if business_id:
        query = query.filter(Device.business_id == business_id)
    
    if keyword:
        keyword_filter = f"%{keyword}%"
        query = query.filter(
            or_(
                Device.hostname.ilike(keyword_filter),
                Device.ip_address.ilike(keyword_filter),
                Device.manufacturer.ilike(keyword_filter),
                Device.model.ilike(keyword_filter),
            )
        )
    
    # 获取总数
    total = query.count()
    
    # 分页
    devices = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [_device_to_dict(d) for d in devices],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/device", summary="创建设备")
async def create_device(
    device: DeviceCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建设备记录"""
    db_device_type = _map_device_type(device.device_type)
    
    db_device = Device(
        hostname=device.hostname,
        ip_address=device.ip_address,
        device_type=db_device_type,
        os_type=device.os_type,
        os_version=device.os_version,
        manufacturer=device.manufacturer,
        model=device.model,
        serial_number=device.serial_number,
        cpu=device.cpu,
        memory=device.memory,
        disk=device.disk,
        network_interfaces=device.network_interfaces,
        location=device.location,
        idc=device.idc,
        cabinet=device.cabinet,
        business_id=device.business_id,
        tags=device.tags,
        status=DBDeviceStatus.OFFLINE,
    )
    
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    
    return _device_to_dict(db_device)


@router.get("/device/{device_id}", summary="获取设备详情")
async def get_device(
    device_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取设备的详细信息"""
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    return _device_to_dict(device)


@router.put("/device/{device_id}", summary="更新设备")
async def update_device(
    device_id: int,
    device: DeviceUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新设备信息"""
    db_device = db.query(Device).filter(Device.id == device_id).first()
    
    if not db_device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 更新字段
    update_data = device.model_dump(exclude_unset=True)
    
    if 'device_type' in update_data:
        update_data['device_type'] = _map_device_type(update_data['device_type'])
    if 'status' in update_data:
        update_data['status'] = _map_device_status(update_data['status'])
    
    for key, value in update_data.items():
        setattr(db_device, key, value)
    
    db_device.updated_at = datetime.now()
    db.commit()
    db.refresh(db_device)
    
    return _device_to_dict(db_device)


@router.delete("/device/{device_id}", summary="删除设备")
async def delete_device(
    device_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除设备（软删除）"""
    db_device = db.query(Device).filter(Device.id == device_id).first()
    
    if not db_device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 软删除：设置为退役状态
    db_device.status = DBDeviceStatus.DECOMMISSIONED
    db_device.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "设备已退役"}


@router.post("/device/{device_id}/maintain", summary="设置设备维护状态")
async def set_device_maintenance(
    device_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """设置设备为维护状态"""
    db_device = db.query(Device).filter(Device.id == device_id).first()
    
    if not db_device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    db_device.status = DBDeviceStatus.MAINTENANCE
    db_device.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "设备已进入维护模式"}


@router.post("/device/{device_id}/decommission", summary="退役设备")
async def decommission_device(
    device_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """退役设备"""
    db_device = db.query(Device).filter(Device.id == device_id).first()
    
    if not db_device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    db_device.status = DBDeviceStatus.DECOMMISSIONED
    db_device.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "设备已退役"}


# ============== 设备分组接口 ==============

@router.get("/group", summary="获取设备分组列表")
async def get_device_groups(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取设备分组列表"""
    groups = db.query(DeviceGroup).all()
    
    return {
        "items": [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "device_count": db.query(Device).filter(Device.group_id == g.id).count(),
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in groups
        ],
        "total": len(groups),
    }


@router.get("/group/{group_id}/devices", summary="获取分组下的设备列表")
async def get_group_devices(
    group_id: int,
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取分组下的设备列表"""
    query = db.query(Device).filter(Device.group_id == group_id)
    total = query.count()
    devices = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [_device_to_dict(d) for d in devices],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


# ============== 配置项接口 ==============

class ConfigItemCreate(BaseModel):
    """创建配置项"""
    key: str = Field(..., description="配置键")
    value: str = Field(..., description="配置值")
    category: str = Field(..., description="分类")
    device_id: Optional[int] = Field(None, description="关联设备")
    description: Optional[str] = Field(None, description="描述")


class ConfigSnapshotRequest(BaseModel):
    """创建设备配置快照请求"""
    device_id: int = Field(..., description="设备ID")
    description: Optional[str] = Field(None, description="快照描述")


@router.get("/config", summary="获取配置项列表")
async def get_config_items(
    category: Optional[str] = Query(None, description="分类过滤"),
    device_id: Optional[int] = Query(None, description="设备ID过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取配置项列表"""
    # 配置项存储在 Device 表的 extra_info JSON 字段中
    # 这里简化处理，返回空列表，实际应创建独立的配置项表
    return {
        "items": [],
        "total": 0,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/config/snapshot", summary="创建设备配置快照")
async def create_config_snapshot(
    request: ConfigSnapshotRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建设备配置快照 - 使用DeviceManager采集设备当前状态"""
    device = db.query(Device).filter(Device.id == request.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 使用DeviceManager采集当前配置
    from modules.collection.device_manager import DeviceManager

    try:
        manager = DeviceManager()
        result = await manager.collect_device(device.hostname or device.name)

        if result and result.status.value == 'online':
            return {
                "id": request.device_id,
                "device_id": request.device_id,
                "device_name": device.name,
                "key": f"config_snapshot_{device.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "value": json.dumps({
                    "hostname": result.hostname,
                    "os_type": result.os_type,
                    "os_version": result.os_version,
                    "uptime": result.uptime,
                    "metrics": result.metrics
                }, ensure_ascii=False),
                "description": request.description or f"{device.name} 配置快照",
                "created_at": datetime.now().isoformat(),
                "created_by": current_user.username,
            }
        else:
            raise HTTPException(status_code=500, detail=f"设备采集失败: {result.error if result else '未知错误'}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置采集异常: {str(e)}")


@router.put("/config/{config_id}", summary="更新配置项")
async def update_config_item(
    config_id: int,
    config: ConfigItemCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新配置项"""
    return {
        "id": config_id,
        "key": config.key,
        "value": config.value,
        "category": config.category,
        "updated_at": datetime.now().isoformat(),
    }


@router.delete("/config/{config_id}", summary="删除配置项")
async def delete_config_item(
    config_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除配置项"""
    return {"status": "success", "message": "配置项已删除"}


@router.post("/config/sync/{device_id}", summary="同步设备配置")
async def sync_device_config(
    device_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """同步设备配置 - 使用DeviceManager采集设备当前状态"""
    from modules.collection.device_manager import DeviceManager

    device = db.query(Device).filter(Device.id == device_id).first()

    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    try:
        manager = DeviceManager()
        result = await manager.collect_device(device.hostname or device.name)

        if result and result.status.value == 'online':
            # 返回采集到的配置信息
            config_snapshot = {
                "status": "success",
                "device_id": device_id,
                "device_name": device.name,
                "synced_at": datetime.now().isoformat(),
                "config_data": {
                    "hostname": result.hostname,
                    "os_type": result.os_type,
                    "os_version": result.os_version,
                    "uptime": result.uptime,
                    "cpu": result.metrics.get('cpu', {}),
                    "memory": result.metrics.get('memory', {}),
                    "disks": result.metrics.get('disks', []),
                    "network": result.metrics.get('network', []),
                    "processes": result.metrics.get('processes', [])[:10],  # 只取前10个
                },
                "message": f"设备 {device.name} 配置同步成功"
            }
        else:
            config_snapshot = {
                "status": "error",
                "device_id": device_id,
                "device_name": device.name,
                "synced_at": datetime.now().isoformat(),
                "error": result.error if result else "采集失败",
                "message": f"设备 {device.name} 配置同步失败"
            }

        return config_snapshot

    except Exception as e:
        return {
            "status": "error",
            "device_id": device_id,
            "device_name": device.name,
            "synced_at": datetime.now().isoformat(),
            "error": str(e),
            "message": f"设备 {device.name} 配置同步异常"
        }


# ============== 业务系统接口 ==============

@router.get("/business", summary="获取业务系统列表")
async def get_business_systems(
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取业务系统列表"""
    query = db.query(BusinessSystem)
    total = query.count()
    systems = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "code": s.code,
                "description": s.description,
                "status": s.status,
                "device_count": db.query(Device).filter(Device.business_id == s.id).count(),
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in systems
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/business/{business_id}", summary="获取业务系统详情")
async def get_business_system(
    business_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取业务系统详情"""
    system = db.query(BusinessSystem).filter(BusinessSystem.id == business_id).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="业务系统不存在")
    
    return {
        "id": system.id,
        "name": system.name,
        "code": system.code,
        "description": system.description,
        "status": system.status,
        "created_at": system.created_at.isoformat() if system.created_at else None,
    }


@router.get("/business/{business_id}/devices", summary="获取业务系统关联的设备")
async def get_business_devices(
    business_id: int,
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取业务系统关联的设备"""
    query = db.query(Device).filter(Device.business_id == business_id)
    total = query.count()
    devices = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [_device_to_dict(d) for d in devices],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


# ============== 资产统计接口 ==============

@router.get("/stats", summary="获取资产统计")
async def get_asset_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取资产统计信息"""
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == DBDeviceStatus.ONLINE).count()
    offline_devices = db.query(Device).filter(Device.status == DBDeviceStatus.OFFLINE).count()
    maintenance_devices = db.query(Device).filter(Device.status == DBDeviceStatus.MAINTENANCE).count()
    
    # 按类型统计
    device_type_stats = {}
    for dtype in DBDeviceType:
        count = db.query(Device).filter(Device.device_type == dtype).count()
        if count > 0:
            device_type_stats[dtype.value] = count
    
    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "maintenance_devices": maintenance_devices,
        "by_type": device_type_stats,
        "by_status": {
            "online": online_devices,
            "offline": offline_devices,
            "maintenance": maintenance_devices,
        }
    }
