# -*- coding: utf-8 -*-
"""
ITOps Platform - CMDB
配置管理数据库
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Asset:
    """资产"""
    id: Optional[int] = None
    name: str = ""
    ip_address: str = ""
    mac_address: str = ""
    hostname: str = ""
    asset_type: str = ""  # server, network, security, storage
    vendor: str = ""  # huawei, h3c, nsfocus, toposec, etc.
    model: str = ""
    serial_number: str = ""
    os_type: str = ""
    os_version: str = ""
    status: str = "active"  # active, inactive, maintenance, retired
    location: str = ""
    department: str = ""
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class CMDB:
    """配置管理数据库"""
    
    def __init__(self):
        self._assets: Dict[int, Asset] = {}
        self._assets_by_ip: Dict[str, Asset] = {}
        self._assets_by_name: Dict[str, Asset] = {}
        self._next_id = 1
    
    def add_asset(self, asset: Asset) -> int:
        """添加资产"""
        if asset.id is None:
            asset.id = self._next_id
            self._next_id += 1
        
        self._assets[asset.id] = asset
        
        if asset.ip_address:
            self._assets_by_ip[asset.ip_address] = asset
        if asset.name:
            self._assets_by_name[asset.name] = asset
        
        return asset.id
    
    def update_asset(self, asset: Asset) -> bool:
        """更新资产"""
        if asset.id not in self._assets:
            return False
        
        old_asset = self._assets[asset.id]
        
        # 更新索引
        if old_asset.ip_address and old_asset.ip_address != asset.ip_address:
            self._assets_by_ip.pop(old_asset.ip_address, None)
        if old_asset.name and old_asset.name != asset.name:
            self._assets_by_name.pop(old_asset.name, None)
        
        if asset.ip_address:
            self._assets_by_ip[asset.ip_address] = asset
        if asset.name:
            self._assets_by_name[asset.name] = asset
        
        self._assets[asset.id] = asset
        asset.updated_at = datetime.now()
        
        return True
    
    def delete_asset(self, asset_id: int) -> bool:
        """删除资产"""
        if asset_id not in self._assets:
            return False
        
        asset = self._assets[asset_id]
        
        if asset.ip_address:
            self._assets_by_ip.pop(asset.ip_address, None)
        if asset.name:
            self._assets_by_name.pop(asset.name, None)
        
        del self._assets[asset_id]
        return True
    
    def get_asset(self, asset_id: int) -> Optional[Asset]:
        """获取资产"""
        return self._assets.get(asset_id)
    
    def get_asset_by_ip(self, ip_address: str) -> Optional[Asset]:
        """通过IP获取资产"""
        return self._assets_by_ip.get(ip_address)
    
    def get_asset_by_name(self, name: str) -> Optional[Asset]:
        """通过名称获取资产"""
        return self._assets_by_name.get(name)
    
    def get_all_assets(
        self,
        asset_type: str = None,
        vendor: str = None,
        status: str = None
    ) -> List[Asset]:
        """获取所有资产"""
        assets = list(self._assets.values())
        
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        if vendor:
            assets = [a for a in assets if a.vendor == vendor]
        if status:
            assets = [a for a in assets if a.status == status]
        
        return assets
    
    def search_assets(self, query: str) -> List[Asset]:
        """搜索资产"""
        query = query.lower()
        results = []
        
        for asset in self._assets.values():
            # 匹配名称、IP、主机名
            if query in asset.name.lower():
                results.append(asset)
            elif asset.ip_address and query in asset.ip_address.lower():
                results.append(asset)
            elif asset.hostname and query in asset.hostname.lower():
                results.append(asset)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取资产统计"""
        assets = list(self._assets.values())
        
        by_type = {}
        by_vendor = {}
        by_status = {}
        
        for asset in assets:
            by_type[asset.asset_type] = by_type.get(asset.asset_type, 0) + 1
            by_vendor[asset.vendor] = by_vendor.get(asset.vendor, 0) + 1
            by_status[asset.status] = by_status.get(asset.status, 0) + 1
        
        return {
            "total": len(assets),
            "by_type": by_type,
            "by_vendor": by_vendor,
            "by_status": by_status,
        }
