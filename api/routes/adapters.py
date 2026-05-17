"""协议适配器管理API"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import get_db, get_current_user, CurrentUser, Session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["适配器管理"], prefix="/adapters")


# ============== 请求/响应模型 ==============

class AdapterTemplateCreate(BaseModel):
    protocol_type: str = Field(..., description="协议类型")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="描述")
    default_config: dict = Field(default_factory=dict, description="默认配置")
    enabled: bool = Field(True, description="是否启用")


class AdapterTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_config: Optional[dict] = None
    enabled: Optional[bool] = None


class DeviceProtocolConfigCreate(BaseModel):
    device_id: int
    protocol_type: str
    adapter_template_id: Optional[int] = None
    overrides: dict = Field(default_factory=dict)
    enabled: bool = True


class DeviceProtocolConfigUpdate(BaseModel):
    adapter_template_id: Optional[int] = None
    overrides: Optional[dict] = None
    enabled: Optional[bool] = None


# ============== 适配器模板CRUD ==============

@router.get("", response_model=dict)
def list_adapters(
    protocol_type: Optional[str] = Query(None, description="按协议类型筛选"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """获取所有适配器模板"""
    from modules.foundation.db_models.adapter import AdapterTemplate
    
    query = db.query(AdapterTemplate)
    if protocol_type:
        query = query.filter(AdapterTemplate.protocol_type == protocol_type)
    
    adapters = query.order_by(AdapterTemplate.protocol_type).all()
    return {
        "items": [a.to_dict() for a in adapters],
        "total": len(adapters),
    }


@router.post("", response_model=dict)
def create_adapter(
    data: AdapterTemplateCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """创建适配器模板"""
    from modules.foundation.db_models.adapter import AdapterTemplate
    from sqlalchemy.exc import IntegrityError
    
    existing = db.query(AdapterTemplate).filter(
        AdapterTemplate.protocol_type == data.protocol_type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"协议类型 {data.protocol_type} 已存在")
    
    adapter = AdapterTemplate(
        protocol_type=data.protocol_type,
        name=data.name,
        description=data.description,
        default_config=data.default_config,
        enabled=data.enabled,
    )
    db.add(adapter)
    try:
        db.commit()
        db.refresh(adapter)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="创建失败，协议类型已存在")
    
    logger.info(f"用户 {user.username} 创建适配器模板: {adapter.name}")
    return adapter.to_dict()


@router.put("/{adapter_id}", response_model=dict)
def update_adapter(
    adapter_id: int,
    data: AdapterTemplateUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """更新适配器模板"""
    from modules.foundation.db_models.adapter import AdapterTemplate
    
    adapter = db.query(AdapterTemplate).filter(AdapterTemplate.id == adapter_id).first()
    if not adapter:
        raise HTTPException(status_code=404, detail="适配器不存在")
    
    if data.name is not None:
        adapter.name = data.name
    if data.description is not None:
        adapter.description = data.description
    if data.default_config is not None:
        adapter.default_config = data.default_config
    if data.enabled is not None:
        adapter.enabled = data.enabled
    
    db.commit()
    db.refresh(adapter)
    
    logger.info(f"用户 {user.username} 更新适配器模板: {adapter.name}")
    return adapter.to_dict()


@router.delete("/{adapter_id}")
def delete_adapter(
    adapter_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """删除适配器模板"""
    from modules.foundation.db_models.adapter import AdapterTemplate
    
    adapter = db.query(AdapterTemplate).filter(AdapterTemplate.id == adapter_id).first()
    if not adapter:
        raise HTTPException(status_code=404, detail="适配器不存在")
    
    db.delete(adapter)
    db.commit()
    
    logger.info(f"用户 {user.username} 删除适配器模板: {adapter.name}")
    return {"message": "删除成功"}


# ============== 设备协议配置CRUD ==============

@router.get("/device/{device_id}/protocols", response_model=dict)
def list_device_protocols(
    device_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """获取设备的所有协议配置"""
    from modules.foundation.db_models.adapter import DeviceProtocolConfig, AdapterTemplate
    
    configs = db.query(DeviceProtocolConfig).filter(
        DeviceProtocolConfig.device_id == device_id
    ).all()
    
    result = []
    for cfg in configs:
        item = cfg.to_dict()
        # 附加适配器模板信息
        if cfg.adapter_template_id:
            tmpl = db.query(AdapterTemplate).filter(
                AdapterTemplate.id == cfg.adapter_template_id
            ).first()
            if tmpl:
                item["adapter_template"] = tmpl.to_dict()
        result.append(item)
    
    return {"items": result, "total": len(result)}


@router.put("/device/{device_id}/protocols", response_model=dict)
def save_device_protocols(
    device_id: int,
    data: List[DeviceProtocolConfigCreate],
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """批量保存设备的协议配置（覆盖式）"""
    from modules.foundation.db_models.adapter import DeviceProtocolConfig
    
    # 删除旧的
    db.query(DeviceProtocolConfig).filter(
        DeviceProtocolConfig.device_id == device_id
    ).delete()
    
    # 插入新的
    for item in data:
        cfg = DeviceProtocolConfig(
            device_id=item.device_id,
            protocol_type=item.protocol_type,
            adapter_template_id=item.adapter_template_id,
            overrides=item.overrides,
            enabled=item.enabled,
        )
        db.add(cfg)
    
    db.commit()
    
    logger.info(f"用户 {user.username} 更新设备 {device_id} 的协议配置，共 {len(data)} 条")
    return {"message": "保存成功", "count": len(data)}


@router.post("/device/{device_id}/protocols/{protocol_type}/test", response_model=dict)
def test_device_protocol(
    device_id: int,
    protocol_type: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """测试设备指定协议的连通性"""
    from modules.foundation.db_models.adapter import DeviceProtocolConfig, AdapterTemplate
    from modules.foundation.db_models.device import Device
    from modules.collection.collector_factory import CollectorFactory
    
    # 获取设备信息
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 获取设备协议配置
    cfg = db.query(DeviceProtocolConfig).filter(
        DeviceProtocolConfig.device_id == device_id,
        DeviceProtocolConfig.protocol_type == protocol_type,
    ).first()
    
    # 获取最终配置：设备覆盖 + 适配器模板 + 默认值
    final_config = {"host": device.ip_address}
    
    if cfg and cfg.adapter_template_id:
        tmpl = db.query(AdapterTemplate).filter(
            AdapterTemplate.id == cfg.adapter_template_id
        ).first()
        if tmpl and tmpl.default_config:
            final_config.update(tmpl.default_config)
    
    if cfg and cfg.overrides:
        final_config.update(cfg.overrides)
    
    # 执行连通性测试
    try:
        factory = CollectorFactory()
        collector = factory.create_collector(protocol_type, **final_config)
        result = collector.check()
        return {"success": True, "message": "连接成功", "config": final_config, "result": result}
    except Exception as e:
        return {"success": False, "message": str(e), "config": final_config}
