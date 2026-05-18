"""协议适配器管理API"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.dependencies import get_db, get_current_user, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter()


class AdapterTemplateCreate(BaseModel):
    name: str
    protocol_type: str
    description: Optional[str] = None
    default_config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class AdapterTemplateUpdate(BaseModel):
    name: Optional[str] = None
    protocol_type: Optional[str] = None
    description: Optional[str] = None
    default_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class DeviceProtocolConfigCreate(BaseModel):
    device_id: Optional[int] = None  # 可选：优先使用URL参数
    protocol_type: str
    adapter_template_id: Optional[int] = None
    overrides: Dict[str, Any] = {}
    enabled: bool = True


class DeviceProtocolConfigUpdate(BaseModel):
    device_id: Optional[int] = None
    protocol_type: Optional[str] = None
    adapter_template_id: Optional[int] = None
    overrides: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


@router.get("/adapters", response_model=dict)
def list_adapter_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    protocol_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """获取协议适配器模板列表"""
    from modules.foundation.db_models.adapter import AdapterTemplate

    query = db.query(AdapterTemplate)
    if protocol_type:
        query = query.filter(AdapterTemplate.protocol_type == protocol_type)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [t.to_dict() for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/adapters", response_model=dict)
def create_adapter_template(
    template: AdapterTemplateCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """创建协议适配器模板"""
    from modules.foundation.db_models.adapter import AdapterTemplate

    existing = db.query(AdapterTemplate).filter(
        AdapterTemplate.name == template.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="模板名称已存在")

    db_template = AdapterTemplate(
        name=template.name,
        protocol_type=template.protocol_type,
        description=template.description,
        default_config=template.default_config,
        enabled=template.enabled,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    logger.info(f"用户 {user.username} 创建适配器模板: {template.name}")
    return db_template.to_dict()


@router.put("/adapters/{adapter_id}", response_model=dict)
def update_adapter_template(
    adapter_id: int,
    template: AdapterTemplateUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """更新协议适配器模板"""
    from modules.foundation.db_models.adapter import AdapterTemplate

    db_template = db.query(AdapterTemplate).filter(
        AdapterTemplate.id == adapter_id
    ).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="模板不存在")

    update_data = template.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_template, key, value)

    db.commit()
    db.refresh(db_template)

    logger.info(f"用户 {user.username} 更新适配器模板: {adapter_id}")
    return db_template.to_dict()


@router.delete("/adapters/{adapter_id}")
def delete_adapter_template(
    adapter_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """删除协议适配器模板"""
    from modules.foundation.db_models.adapter import AdapterTemplate

    db_template = db.query(AdapterTemplate).filter(
        AdapterTemplate.id == adapter_id
    ).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="模板不存在")

    db.delete(db_template)
    db.commit()

    logger.info(f"用户 {user.username} 删除适配器模板: {adapter_id}")
    return {"message": "删除成功"}


@router.get("/device/{device_id}/protocols", response_model=dict)
def get_device_protocols(
    device_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """获取设备的所有协议配置"""
    from modules.foundation.db_models.adapter import DeviceProtocolConfig

    configs = db.query(DeviceProtocolConfig).filter(
        DeviceProtocolConfig.device_id == device_id
    ).all()

    return {
        "items": [c.to_dict() for c in configs],
        "total": len(configs),
    }


@router.put("/device/{device_id}/protocols", response_model=dict)
def save_device_protocols(
    device_id: int,
    data: List[DeviceProtocolConfigCreate],
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """批量保存设备协议配置（先删后插）"""
    from modules.foundation.db_models.adapter import DeviceProtocolConfig

    # 先删除该设备的所有协议配置
    db.query(DeviceProtocolConfig).filter(
        DeviceProtocolConfig.device_id == device_id
    ).delete()

    # 插入新的
    for item in data:
        cfg = DeviceProtocolConfig(
            device_id=device_id,
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

    # 构建配置：CollectorFactory._create_ssh_collector 期望
    # {ip, credentials: {ssh: {port, username, password, key_file, timeout}}}
    ssh_creds = {}
    if cfg and cfg.overrides:
        ssh_creds = {
            "port": cfg.overrides.get("port", 22),
            "username": cfg.overrides.get("username", ""),
            "password": cfg.overrides.get("password", ""),
            "timeout": cfg.overrides.get("timeout", 30),
        }

    final_config = {
        "ip": device.ip_address,
        "protocols": {"primary": protocol_type},
        "credentials": {"ssh": ssh_creds},
    }

    # 执行连通性测试
    try:
        factory = CollectorFactory()
        collector = factory.create_collector(final_config)

        # 根据协议类型选择正确的连通性测试方法
        if protocol_type.lower() == 'ssh':
            result = collector.connect()
            if result:
                collector.close()
        elif protocol_type.lower() in ('mysql', 'postgres', 'redis', 'rabbitmq', 'kafka',
                                        'elasticsearch', 'mongodb', 'clickhouse', 'tdengine',
                                        'zookeeper', 'nacos'):
            result = collector.connect()
        elif protocol_type.lower() in ('http', 'prometheus', 'kubernetes', 'docker', 'vmware'):
            result = collector.check() if hasattr(collector, 'check') else True
        else:
            result = collector.check() if hasattr(collector, 'check') else True

        return {"success": bool(result), "message": "连接成功" if result else "连接失败", "config": final_config, "result": result}
    except Exception as e:
        return {"success": False, "message": str(e), "config": final_config}
