"""
资产模型模块
提供资产台账、资产分类、资产属性、资产标签、资产关系等功能
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


class AssetCategory(Enum):
    """资产分类枚举"""
    SERVER = 'server'
    NETWORK = 'network'
    SECURITY = 'security'
    STORAGE = 'storage'
    SOFTWARE = 'software'
    DATABASE = 'database'
    CLOUD = 'cloud'
    VIRTUAL = 'virtual'
    OTHER = 'other'


class AssetStatus(Enum):
    """资产状态枚举"""
    PLANNED = 'planned'           # 规划中
    PROCURED = 'procured'        # 已采购
    IN_STORAGE = 'in_storage'    # 入库
    INSTALLED = 'installed'      # 已安装
    RUNNING = 'running'          # 运行中
    MAINTENANCE = 'maintenance'  # 维护中
    FAULT = 'fault'              # 故障
    DECOMMISSIONED = 'decommissioned'  # 已退役
    SCRAPPED = 'scrapped'        # 已报废


class AssetType(Enum):
    """资产类型枚举"""
    # 服务器类
    PHYSICAL_SERVER = 'physical_server'
    BLADE_SERVER = 'blade_server'
    RACK_SERVER = 'rack_server'
    TOWER_SERVER = 'tower_server'
    
    # 网络类
    ROUTER = 'router'
    SWITCH = 'switch'
    FIREWALL = 'firewall'
    LOAD_BALANCER = 'load_balancer'
    WIRELESS_AP = 'wireless_ap'
    
    # 安全设备
    IDS_IPS = 'ids_ips'
    WAF = 'waf'
    VPN_GATEWAY = 'vpn_gateway'
    ANTIVIRUS_SERVER = 'antivirus_server'
    
    # 存储
    NAS = 'nas'
    SAN = 'san'
    TAPE_LIBRARY = 'tape_library'
    
    # 软件
    OS = 'os'
    MIDDLEWARE = 'middleware'
    APPLICATION = 'application'
    
    # 其他
    OTHER = 'other'


class RelationType(Enum):
    """资产关系类型"""
    PARENT_CHILD = 'parent_child'       # 上下级关系
    DEPENDENCY = 'dependency'           # 依赖关系
    NETWORK = 'network'                 # 网络连接
    CLUSTER = 'cluster'                # 集群关系
    BACKUP = 'backup'                  # 备份关系
    MONITOR = 'monitor'                # 监控关系


@dataclass
class AssetAttribute:
    """资产属性"""
    key: str
    value: Any
    type: str = 'string'  # string, number, boolean, date, list
    description: str = ''
    is_required: bool = False
    is_system: bool = False  # 系统属性 vs 自定义属性


@dataclass
class AssetTag:
    """资产标签"""
    name: str
    category: str = 'general'  # general, business, technical, compliance
    color: str = '#666666'
    description: str = ''
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Asset:
    """资产模型"""
    asset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ''
    category: AssetCategory = AssetCategory.SERVER
    asset_type: AssetType = AssetType.PHYSICAL_SERVER
    status: AssetStatus = AssetStatus.PLANNED
    
    # 基本信息
    manufacturer: str = ''
    model: str = ''
    serial_number: str = ''
    asset_number: str = ''  # 资产编号
    
    # 位置信息
    location: str = ''
    idc: str = ''
    rack: str = ''
    rack_position: str = ''
    
    # 网络信息
    ip_address: str = ''
    mac_address: str = ''
    hostname: str = ''
    
    # 业务信息
    business_unit: str = ''
    application: str = ''
    owner: str = ''
    contact: str = ''
    
    # 配置信息
    cpu: str = ''
    memory: str = ''
    disk: str = ''
    bandwidth: str = ''
    
    # 采购信息
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    purchase_price: float = 0.0
    vendor: str = ''
    
    # 生命周期
    expected_lifespan: int = 60  # 预期使用寿命（月）
    install_date: Optional[datetime] = None
    commissioning_date: Optional[datetime] = None
    
    # 状态信息
    attributes: Dict[str, AssetAttribute] = field(default_factory=dict)
    tags: List[AssetTag] = field(default_factory=list)
    relations: List['AssetRelation'] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ''
    description: str = ''
    notes: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'asset_id': self.asset_id,
            'name': self.name,
            'category': self.category.value,
            'asset_type': self.asset_type.value,
            'status': self.status.value,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'serial_number': self.serial_number,
            'asset_number': self.asset_number,
            'location': self.location,
            'idc': self.idc,
            'rack': self.rack,
            'rack_position': self.rack_position,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'hostname': self.hostname,
            'business_unit': self.business_unit,
            'application': self.application,
            'owner': self.owner,
            'contact': self.contact,
            'cpu': self.cpu,
            'memory': self.memory,
            'disk': self.disk,
            'bandwidth': self.bandwidth,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'warranty_expiry': self.warranty_expiry.isoformat() if self.warranty_expiry else None,
            'purchase_price': self.purchase_price,
            'vendor': self.vendor,
            'expected_lifespan': self.expected_lifespan,
            'install_date': self.install_date.isoformat() if self.install_date else None,
            'commissioning_date': self.commissioning_date.isoformat() if self.commissioning_date else None,
            'attributes': {k: {'key': v.key, 'value': v.value, 'type': v.type, 'description': v.description} 
                          for k, v in self.attributes.items()},
            'tags': [{'name': t.name, 'category': t.category, 'color': t.color, 'description': t.description} 
                    for t in self.tags],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'description': self.description,
            'notes': self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Asset':
        """从字典创建资产"""
        tags = [AssetTag(**t) for t in data.get('tags', [])]
        attributes = {k: AssetAttribute(**v) for k, v in data.get('attributes', {}).items()}
        
        return cls(
            asset_id=data.get('asset_id', str(uuid.uuid4())),
            name=data.get('name', ''),
            category=AssetCategory(data.get('category', 'server')),
            asset_type=AssetType(data.get('asset_type', 'physical_server')),
            status=AssetStatus(data.get('status', 'planned')),
            manufacturer=data.get('manufacturer', ''),
            model=data.get('model', ''),
            serial_number=data.get('serial_number', ''),
            asset_number=data.get('asset_number', ''),
            location=data.get('location', ''),
            idc=data.get('idc', ''),
            rack=data.get('rack', ''),
            rack_position=data.get('rack_position', ''),
            ip_address=data.get('ip_address', ''),
            mac_address=data.get('mac_address', ''),
            hostname=data.get('hostname', ''),
            business_unit=data.get('business_unit', ''),
            application=data.get('application', ''),
            owner=data.get('owner', ''),
            contact=data.get('contact', ''),
            cpu=data.get('cpu', ''),
            memory=data.get('memory', ''),
            disk=data.get('disk', ''),
            bandwidth=data.get('bandwidth', ''),
            purchase_date=datetime.fromisoformat(data['purchase_date']) if data.get('purchase_date') else None,
            warranty_expiry=datetime.fromisoformat(data['warranty_expiry']) if data.get('warranty_expiry') else None,
            purchase_price=data.get('purchase_price', 0.0),
            vendor=data.get('vendor', ''),
            expected_lifespan=data.get('expected_lifespan', 60),
            install_date=datetime.fromisoformat(data['install_date']) if data.get('install_date') else None,
            commissioning_date=datetime.fromisoformat(data['commissioning_date']) if data.get('commissioning_date') else None,
            attributes=attributes,
            tags=tags,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            created_by=data.get('created_by', ''),
            description=data.get('description', ''),
            notes=data.get('notes', ''),
        )
    
    def add_attribute(self, key: str, value: Any, attr_type: str = 'string', 
                     description: str = '', is_required: bool = False, is_system: bool = False) -> None:
        """添加资产属性"""
        self.attributes[key] = AssetAttribute(
            key=key, value=value, type=attr_type, 
            description=description, is_required=is_required, is_system=is_system
        )
        self.updated_at = datetime.now()
    
    def add_tag(self, name: str, category: str = 'general', color: str = '#666666', 
                description: str = '') -> None:
        """添加资产标签"""
        # 检查是否已存在
        if not any(t.name == name for t in self.tags):
            self.tags.append(AssetTag(name=name, category=category, color=color, description=description))
            self.updated_at = datetime.now()
    
    def remove_tag(self, name: str) -> bool:
        """移除资产标签"""
        for i, tag in enumerate(self.tags):
            if tag.name == name:
                self.tags.pop(i)
                self.updated_at = datetime.now()
                return True
        return False
    
    def has_tag(self, tag_name: str) -> bool:
        """检查是否有指定标签"""
        return any(t.name == tag_name for t in self.tags)
    
    def get_uptime(self) -> int:
        """获取运行时间（天）"""
        if self.commissioning_date:
            return (datetime.now() - self.commissioning_date).days
        return 0
    
    def get_age_months(self) -> int:
        """获取资产月龄"""
        if self.purchase_date:
            delta = datetime.now() - self.purchase_date
            return delta.days // 30
        return 0


@dataclass
class AssetRelation:
    """资产关系"""
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_asset_id: str = ''
    target_asset_id: str = ''
    relation_type: RelationType = RelationType.DEPENDENCY
    description: str = ''
    is_critical: bool = False  # 是否关键依赖
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'relation_id': self.relation_id,
            'source_asset_id': self.source_asset_id,
            'target_asset_id': self.target_asset_id,
            'relation_type': self.relation_type.value,
            'description': self.description,
            'is_critical': self.is_critical,
            'created_at': self.created_at.isoformat(),
        }


class AssetManager:
    """资产管理器"""
    
    def __init__(self):
        self.assets: Dict[str, Asset] = {}
        self.relations: Dict[str, List[AssetRelation]] = defaultdict(list)
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag_name -> asset_ids
        self.category_index: Dict[AssetCategory, Set[str]] = defaultdict(set)
        self.status_index: Dict[AssetStatus, Set[str]] = defaultdict(set)
    
    def add_asset(self, asset: Asset) -> bool:
        """添加资产"""
        try:
            self.assets[asset.asset_id] = asset
            self._update_indexes(asset)
            logger.info(f"Asset added: {asset.asset_id} - {asset.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add asset: {e}")
            return False
    
    def update_asset(self, asset: Asset) -> bool:
        """更新资产"""
        try:
            old_asset = self.assets.get(asset.asset_id)
            if old_asset:
                # 清理旧索引
                self._clear_indexes(old_asset)
            
            asset.updated_at = datetime.now()
            self.assets[asset.asset_id] = asset
            self._update_indexes(asset)
            logger.info(f"Asset updated: {asset.asset_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update asset: {e}")
            return False
    
    def delete_asset(self, asset_id: str) -> bool:
        """删除资产"""
        if asset_id in self.assets:
            asset = self.assets.pop(asset_id)
            self._clear_indexes(asset)
            # 清理关系
            self._clear_relations(asset_id)
            logger.info(f"Asset deleted: {asset_id}")
            return True
        return False
    
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """获取资产"""
        return self.assets.get(asset_id)
    
    def get_assets_by_category(self, category: AssetCategory) -> List[Asset]:
        """按分类获取资产"""
        asset_ids = self.category_index.get(category, set())
        return [self.assets[aid] for aid in asset_ids if aid in self.assets]
    
    def get_assets_by_status(self, status: AssetStatus) -> List[Asset]:
        """按状态获取资产"""
        asset_ids = self.status_index.get(status, set())
        return [self.assets[aid] for aid in asset_ids if aid in self.assets]
    
    def get_assets_by_tag(self, tag_name: str) -> List[Asset]:
        """按标签获取资产"""
        asset_ids = self.tag_index.get(tag_name, set())
        return [self.assets[aid] for aid in asset_ids if aid in self.assets]
    
    def search_assets(self, query: str) -> List[Asset]:
        """搜索资产"""
        query_lower = query.lower()
        results = []
        for asset in self.assets.values():
            if (query_lower in asset.name.lower() or
                query_lower in asset.serial_number.lower() or
                query_lower in asset.asset_number.lower() or
                query_lower in asset.ip_address.lower() or
                query_lower in asset.hostname.lower() or
                query_lower in asset.manufacturer.lower() or
                query_lower in asset.location.lower()):
                results.append(asset)
        return results
    
    def add_relation(self, relation: AssetRelation) -> bool:
        """添加资产关系"""
        try:
            self.relations[relation.source_asset_id].append(relation)
            # 同时添加反向关系
            reverse_relation = AssetRelation(
                source_asset_id=relation.target_asset_id,
                target_asset_id=relation.source_asset_id,
                relation_type=relation.relation_type,
                description=f"反向: {relation.description}",
                is_critical=relation.is_critical,
            )
            self.relations[relation.target_asset_id].append(reverse_relation)
            logger.info(f"Relation added: {relation.source_asset_id} -> {relation.target_asset_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add relation: {e}")
            return False
    
    def get_relations(self, asset_id: str, relation_type: Optional[RelationType] = None) -> List[AssetRelation]:
        """获取资产关系"""
        relations = self.relations.get(asset_id, [])
        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]
        return relations
    
    def get_dependent_assets(self, asset_id: str, include_critical_only: bool = False) -> List[str]:
        """获取依赖此资产的资产列表"""
        relations = self.get_relations(asset_id, RelationType.DEPENDENCY)
        if include_critical_only:
            relations = [r for r in relations if r.is_critical]
        return [r.target_asset_id for r in relations if r.source_asset_id == asset_id]
    
    def _update_indexes(self, asset: Asset) -> None:
        """更新索引"""
        self.category_index[asset.category].add(asset.asset_id)
        self.status_index[asset.status].add(asset.asset_id)
        for tag in asset.tags:
            self.tag_index[tag.name].add(asset.asset_id)
    
    def _clear_indexes(self, asset: Asset) -> None:
        """清理索引"""
        self.category_index[asset.category].discard(asset.asset_id)
        self.status_index[asset.status].discard(asset.asset_id)
        for tag in asset.tags:
            self.tag_index[tag.name].discard(asset.asset_id)
    
    def _clear_relations(self, asset_id: str) -> None:
        """清理关系"""
        if asset_id in self.relations:
            # 清理所有涉及此资产的关系
            for other_id, relations in self.relations.items():
                self.relations[other_id] = [
                    r for r in relations 
                    if r.source_asset_id != asset_id and r.target_asset_id != asset_id
                ]
            del self.relations[asset_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取资产统计信息"""
        stats = {
            'total': len(self.assets),
            'by_category': {},
            'by_status': {},
            'by_type': {},
            'total_value': 0.0,
        }
        
        for asset in self.assets.values():
            # 按分类统计
            cat = asset.category.value
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            
            # 按状态统计
            status = asset.status.value
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # 按类型统计
            asset_type = asset.asset_type.value
            stats['by_type'][asset_type] = stats['by_type'].get(asset_type, 0) + 1
            
            # 总价值
            stats['total_value'] += asset.purchase_price
        
        return stats
