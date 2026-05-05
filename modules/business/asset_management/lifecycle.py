"""
生命周期管理模块
提供采购记录、上线/下线、维保管理、退网退役、资产变更历史等功能
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


class LifecycleEventType(Enum):
    """生命周期事件类型"""
    # 采购阶段
    PROCUREMENT_PLANNED = 'procurement_planned'
    PROCUREMENT_APPROVED = 'procurement_approved'
    PROCUREMENT_ORDERED = 'procurement_ordered'
    PROCUREMENT_RECEIVED = 'procurement_received'
    
    # 上线阶段
    STORAGE_IN = 'storage_in'
    STORAGE_OUT = 'storage_out'
    INSTALLATION_START = 'installation_start'
    INSTALLATION_COMPLETE = 'installation_complete'
    COMMISSIONING = 'commissioning'
    ONLINE = 'online'
    
    # 运行阶段
    MAINTENANCE_SCHEDULED = 'maintenance_scheduled'
    MAINTENANCE_START = 'maintenance_start'
    MAINTENANCE_COMPLETE = 'maintenance_complete'
    HARDWARE_UPGRADE = 'hardware_upgrade'
    SOFTWARE_UPDATE = 'software_update'
    CONFIG_CHANGE = 'config_change'
    RELOCATION = 'relocation'
    
    # 下线阶段
    DECOMMISSION_PLANNED = 'decommission_planned'
    DECOMMISSION_APPROVED = 'decommission_approved'
    SERVICE_STOP = 'service_stop'
    DATA_MIGRATION = 'data_migration'
    OFFLINE = 'offline'
    
    # 退役阶段
    DECOMMISSIONED = 'decommissioned'
    SCRAPPED = 'scrapped'
    RECYCLED = 'recycled'
    
    # 变更
    STATUS_CHANGE = 'status_change'
    OWNER_CHANGE = 'owner_change'
    ATTRIBUTE_CHANGE = 'attribute_change'


@dataclass
class LifecycleEvent:
    """生命周期事件"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str = ''
    event_type: LifecycleEventType = LifecycleEventType.PROCUREMENT_PLANNED
    
    # 事件信息
    title: str = ''
    description: str = ''
    
    # 时间信息
    planned_date: Optional[datetime] = None
    actual_date: Optional[datetime] = None
    
    # 参与者
    created_by: str = ''
    assigned_to: str = ''
    
    # 状态
    status: str = 'pending'  # pending, in_progress, completed, cancelled
    
    # 相关资源
    related_asset_ids: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'asset_id': self.asset_id,
            'event_type': self.event_type.value,
            'title': self.title,
            'description': self.description,
            'planned_date': self.planned_date.isoformat() if self.planned_date else None,
            'actual_date': self.actual_date.isoformat() if self.actual_date else None,
            'created_by': self.created_by,
            'assigned_to': self.assigned_to,
            'status': self.status,
            'related_asset_ids': self.related_asset_ids,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


@dataclass
class PurchaseRecord:
    """采购记录"""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str = ''
    
    # 采购信息
    purchase_date: datetime = field(default_factory=datetime.now)
    purchase_order_no: str = ''
    invoice_no: str = ''
    
    # 供应商信息
    vendor: str = ''
    vendor_contact: str = ''
    vendor_phone: str = ''
    
    # 商品信息
    product_name: str = ''
    product_model: str = ''
    product_spec: str = ''
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    currency: str = 'CNY'
    
    # 付款信息
    payment_method: str = ''
    payment_status: str = 'pending'  # pending, paid, cancelled
    
    # 交付信息
    expected_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    delivery_address: str = ''
    
    # 附件
    attachments: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ''
    notes: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'record_id': self.record_id,
            'asset_id': self.asset_id,
            'purchase_date': self.purchase_date.isoformat(),
            'purchase_order_no': self.purchase_order_no,
            'invoice_no': self.invoice_no,
            'vendor': self.vendor,
            'vendor_contact': self.vendor_contact,
            'vendor_phone': self.vendor_phone,
            'product_name': self.product_name,
            'product_model': self.product_model,
            'product_spec': self.product_spec,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'actual_delivery_date': self.actual_delivery_date.isoformat() if self.actual_delivery_date else None,
            'delivery_address': self.delivery_address,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'notes': self.notes,
        }


@dataclass
class MaintenanceRecord:
    """维保记录"""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str = ''
    
    # 维保类型
    maintenance_type: str = 'preventive'  # preventive, corrective, predictive, emergency
    title: str = ''
    description: str = ''
    
    # 时间信息
    scheduled_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_hours: float = 0.0
    
    # 维保人员
    performed_by: str = ''
    vendor: str = ''
    
    # 维保内容
    work_summary: str = ''
    replaced_parts: List[str] = field(default_factory=list)
    test_results: str = ''
    
    # 费用
    cost: float = 0.0
    currency: str = 'CNY'
    
    # 状态
    status: str = 'scheduled'  # scheduled, in_progress, completed, cancelled
    
    # 结果
    result: str = 'success'  # success, partial, failed
    
    # 相关事件
    related_event_id: Optional[str] = None
    
    # 附件
    attachments: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ''
    notes: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'record_id': self.record_id,
            'asset_id': self.asset_id,
            'maintenance_type': self.maintenance_type,
            'title': self.title,
            'description': self.description,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'duration_hours': self.duration_hours,
            'performed_by': self.performed_by,
            'vendor': self.vendor,
            'work_summary': self.work_summary,
            'replaced_parts': self.replaced_parts,
            'test_results': self.test_results,
            'cost': self.cost,
            'currency': self.currency,
            'status': self.status,
            'result': self.result,
            'related_event_id': self.related_event_id,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'notes': self.notes,
        }


@dataclass
class ChangeHistory:
    """变更历史记录"""
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str = ''
    
    # 变更信息
    field_name: str = ''
    old_value: Any = None
    new_value: Any = None
    change_type: str = 'update'  # create, update, delete
    
    # 变更原因
    change_reason: str = ''
    change_category: str = 'general'  # general, maintenance, upgrade, incident
    
    # 参与者
    changed_by: str = ''
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'change_id': self.change_id,
            'asset_id': self.asset_id,
            'field_name': self.field_name,
            'old_value': str(self.old_value) if self.old_value else None,
            'new_value': str(self.new_value) if self.new_value else None,
            'change_type': self.change_type,
            'change_reason': self.change_reason,
            'change_category': self.change_category,
            'changed_by': self.changed_by,
            'created_at': self.created_at.isoformat(),
        }


class LifecycleManager:
    """生命周期管理器"""
    
    def __init__(self):
        self.events: Dict[str, List[LifecycleEvent]] = defaultdict(list)
        self.purchase_records: Dict[str, PurchaseRecord] = {}
        self.maintenance_records: Dict[str, List[MaintenanceRecord]] = defaultdict(list)
        self.change_history: Dict[str, List[ChangeHistory]] = defaultdict(list)
    
    # ==================== 生命周期事件管理 ====================
    
    def create_event(self, event: LifecycleEvent) -> bool:
        """创建生命周期事件"""
        try:
            self.events[event.asset_id].append(event)
            logger.info(f"Lifecycle event created: {event.event_id} for asset {event.asset_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create lifecycle event: {e}")
            return False
    
    def get_events(self, asset_id: str, event_type: Optional[LifecycleEventType] = None) -> List[LifecycleEvent]:
        """获取资产的生命周期事件"""
        events = self.events.get(asset_id, [])
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return sorted(events, key=lambda x: x.created_at, reverse=True)
    
    def get_upcoming_events(self, days: int = 30) -> List[LifecycleEvent]:
        """获取即将到来的事件"""
        cutoff = datetime.now() + timedelta(days=days)
        upcoming = []
        for events in self.events.values():
            for event in events:
                if event.planned_date and event.planned_date <= cutoff and event.status == 'pending':
                    upcoming.append(event)
        return sorted(upcoming, key=lambda x: x.planned_date)
    
    def update_event_status(self, event_id: str, asset_id: str, status: str, actual_date: Optional[datetime] = None) -> bool:
        """更新事件状态"""
        events = self.events.get(asset_id, [])
        for event in events:
            if event.event_id == event_id:
                event.status = status
                if actual_date:
                    event.actual_date = actual_date
                event.updated_at = datetime.now()
                return True
        return False
    
    def complete_event(self, event_id: str, asset_id: str) -> bool:
        """完成事件"""
        return self.update_event_status(event_id, asset_id, 'completed', datetime.now())
    
    # ==================== 采购记录管理 ====================
    
    def add_purchase_record(self, record: PurchaseRecord) -> bool:
        """添加采购记录"""
        try:
            self.purchase_records[record.asset_id] = record
            logger.info(f"Purchase record added for asset {record.asset_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add purchase record: {e}")
            return False
    
    def get_purchase_record(self, asset_id: str) -> Optional[PurchaseRecord]:
        """获取采购记录"""
        return self.purchase_records.get(asset_id)
    
    # ==================== 维保记录管理 ====================
    
    def add_maintenance_record(self, record: MaintenanceRecord) -> bool:
        """添加维保记录"""
        try:
            self.maintenance_records[record.asset_id].append(record)
            logger.info(f"Maintenance record added: {record.record_id} for asset {record.asset_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add maintenance record: {e}")
            return False
    
    def get_maintenance_records(self, asset_id: str, maintenance_type: Optional[str] = None) -> List[MaintenanceRecord]:
        """获取维保记录"""
        records = self.maintenance_records.get(asset_id, [])
        if maintenance_type:
            records = [r for r in records if r.maintenance_type == maintenance_type]
        return sorted(records, key=lambda x: x.created_at, reverse=True)
    
    def get_upcoming_maintenance(self, days: int = 30) -> List[MaintenanceRecord]:
        """获取即将到来的维保计划"""
        cutoff = datetime.now() + timedelta(days=days)
        upcoming = []
        for records in self.maintenance_records.values():
            for record in records:
                if record.scheduled_date and record.scheduled_date <= cutoff and record.status == 'scheduled':
                    upcoming.append(record)
        return sorted(upcoming, key=lambda x: x.scheduled_date)
    
    def get_maintenance_stats(self, asset_id: str) -> Dict[str, Any]:
        """获取维保统计"""
        records = self.maintenance_records.get(asset_id, [])
        return {
            'total_count': len(records),
            'preventive_count': len([r for r in records if r.maintenance_type == 'preventive']),
            'corrective_count': len([r for r in records if r.maintenance_type == 'corrective']),
            'emergency_count': len([r for r in records if r.maintenance_type == 'emergency']),
            'total_cost': sum(r.cost for r in records),
            'total_duration_hours': sum(r.duration_hours for r in records),
        }
    
    # ==================== 变更历史管理 ====================
    
    def record_change(self, change: ChangeHistory) -> bool:
        """记录变更"""
        try:
            self.change_history[change.asset_id].append(change)
            return True
        except Exception as e:
            logger.error(f"Failed to record change: {e}")
            return False
    
    def get_change_history(self, asset_id: str, field_name: Optional[str] = None) -> List[ChangeHistory]:
        """获取变更历史"""
        history = self.change_history.get(asset_id, [])
        if field_name:
            history = [h for h in history if h.field_name == field_name]
        return sorted(history, key=lambda x: x.created_at, reverse=True)
    
    # ==================== 生命周期流程 ====================
    
    def commission_asset(self, asset_id: str, user: str, commissioning_date: Optional[datetime] = None) -> bool:
        """资产上线"""
        event = LifecycleEvent(
            asset_id=asset_id,
            event_type=LifecycleEventType.COMMISSIONING,
            title='资产上线',
            description='资产正式投入使用',
            actual_date=commissioning_date or datetime.now(),
            created_by=user,
            status='completed',
        )
        return self.create_event(event)
    
    def decommission_asset(self, asset_id: str, user: str, reason: str = '') -> bool:
        """资产退役"""
        event = LifecycleEvent(
            asset_id=asset_id,
            event_type=LifecycleEventType.DECOMMISSIONED,
            title='资产退役',
            description=reason,
            actual_date=datetime.now(),
            created_by=user,
            status='completed',
        )
        return self.create_event(event)
    
    def schedule_maintenance(self, asset_id: str, scheduled_date: datetime, title: str, 
                            description: str, user: str) -> Optional[str]:
        """计划维保"""
        record = MaintenanceRecord(
            asset_id=asset_id,
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            status='scheduled',
            created_by=user,
        )
        if self.add_maintenance_record(record):
            return record.record_id
        return None
    
    # ==================== 统计分析 ====================
    
    def get_lifecycle_timeline(self, asset_id: str) -> List[Dict[str, Any]]:
        """获取生命周期时间线"""
        events = self.get_events(asset_id)
        timeline = []
        for event in events:
            timeline.append({
                'date': event.actual_date or event.planned_date,
                'type': event.event_type.value,
                'title': event.title,
                'status': event.status,
            })
        return sorted(timeline, key=lambda x: x['date'] if x['date'] else datetime.min)
    
    def get_warranty_status(self, asset_id: str, purchase_record: Optional[PurchaseRecord] = None) -> Dict[str, Any]:
        """获取保修状态"""
        record = purchase_record or self.get_purchase_record(asset_id)
        if not record:
            return {'has_warranty': False}
        
        warranty_expiry = record.actual_delivery_date + timedelta(days=365) if record.actual_delivery_date else None
        if not warranty_expiry:
            return {'has_warranty': False}
        
        now = datetime.now()
        days_remaining = (warranty_expiry - now).days
        
        return {
            'has_warranty': True,
            'warranty_expiry': warranty_expiry,
            'days_remaining': days_remaining,
            'is_expired': days_remaining < 0,
            'expiring_soon': 0 <= days_remaining <= 30,
        }
