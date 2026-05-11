"""
NotificationTargetRule Service Layer
通知目标规则服务层 - CFG-026
提供通知目标规则的CRUD和匹配功能
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from modules.foundation.db_models.notification.notification_model import NotificationTargetRule

logger = logging.getLogger(__name__)


class NotificationTargetRuleService:
    """
    通知目标规则服务类
    提供规则的创建、查询、更新、删除和匹配功能
    """
    
    # 支持的通知渠道
    VALID_NOTIFY_CHANNELS = ["email", "dingtalk", "feishu", "wechat_work", "webhook", "sms", "phone"]
    
    # 支持的规则类型
    VALID_RULE_TYPES = ["alert_level", "device", "category", "custom"]
    
    def __init__(self, db: Session):
        """
        初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def create_rule(self, rule_data: Dict[str, Any]) -> NotificationTargetRule:
        """
        创建通知目标规则
        
        Args:
            rule_data: 规则数据字典
            
        Returns:
            创建的规则对象
            
        Raises:
            ValueError: 规则名称已存在或数据无效
        """
        name = rule_data.get("name", "").strip()
        if not name:
            raise ValueError("规则名称不能为空")
        
        # 检查名称是否重复
        existing = self.db.query(NotificationTargetRule).filter(
            NotificationTargetRule.name == name
        ).first()
        
        if existing:
            raise ValueError("规则名称已存在")
        
        # 验证规则类型
        rule_type = rule_data.get("rule_type", "alert_level")
        self._validate_rule_type(rule_type)
        
        # 验证通知渠道
        notify_channels = rule_data.get("notify_channels", [])
        for channel in notify_channels:
            self._validate_notify_channel(channel)
        
        # 创建规则
        db_rule = NotificationTargetRule(
            name=name,
            description=rule_data.get("description"),
            rule_type=rule_type,
            match_conditions=json.dumps(rule_data.get("match_conditions")) if rule_data.get("match_conditions") else None,
            notify_channels=json.dumps(notify_channels),
            notify_receivers=json.dumps(rule_data.get("notify_receivers")) if rule_data.get("notify_receivers") else None,
            notify_interval=rule_data.get("notify_interval", 300),
            max_notify_count=rule_data.get("max_notify_count", 3),
            escalation_config=json.dumps(rule_data.get("escalation_config")) if rule_data.get("escalation_config") else None,
            suppress_enabled=rule_data.get("suppress_enabled", False),
            suppress_until=rule_data.get("suppress_until"),
            time_windows=json.dumps(rule_data.get("time_windows")) if rule_data.get("time_windows") else None,
            priority=rule_data.get("priority", 100),
            enabled=True,
            created_by=rule_data.get("created_by"),
        )
        
        self.db.add(db_rule)
        self.db.commit()
        self.db.refresh(db_rule)
        
        logger.info(f"创建通知目标规则: {name}")
        return db_rule
    
    def get_rule_by_id(self, rule_id: int) -> Optional[NotificationTargetRule]:
        """
        通过ID获取规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            规则对象或None
        """
        return self.db.query(NotificationTargetRule).filter(
            NotificationTargetRule.id == rule_id
        ).first()
    
    def list_rules(
        self,
        rule_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[NotificationTargetRule]:
        """
        列出规则
        
        Args:
            rule_type: 规则类型过滤
            enabled: 启用状态过滤
            page: 页码
            page_size: 每页数量
            
        Returns:
            规则列表
        """
        query = self.db.query(NotificationTargetRule)
        
        if rule_type:
            query = query.filter(NotificationTargetRule.rule_type == rule_type)
        
        if enabled is not None:
            query = query.filter(NotificationTargetRule.enabled == enabled)
        
        offset = (page - 1) * page_size
        return query.order_by(
            NotificationTargetRule.priority.asc(),
            NotificationTargetRule.id.asc()
        ).offset(offset).limit(page_size).all()
    
    def update_rule(self, rule_id: int, update_data: Dict[str, Any]) -> NotificationTargetRule:
        """
        更新规则
        
        Args:
            rule_id: 规则ID
            update_data: 更新数据
            
        Returns:
            更新后的规则对象
            
        Raises:
            ValueError: 规则不存在
        """
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            raise ValueError("规则不存在")
        
        # 如果更新名称，检查是否重复
        if "name" in update_data:
            new_name = update_data["name"].strip()
            if new_name:
                existing = self.db.query(NotificationTargetRule).filter(
                    NotificationTargetRule.name == new_name,
                    NotificationTargetRule.id != rule_id
                ).first()
                if existing:
                    raise ValueError("规则名称已存在")
                rule.name = new_name
        
        # 更新其他字段
        for key, value in update_data.items():
            if key in ['match_conditions', 'notify_channels', 'notify_receivers', 'escalation_config', 'time_windows']:
                if value is not None:
                    setattr(rule, key, json.dumps(value))
            elif key not in ['name', 'created_by']:
                if value is not None:
                    setattr(rule, key, value)
        
        rule.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(rule)
        
        logger.info(f"更新通知目标规则: {rule_id}")
        return rule
    
    def delete_rule(self, rule_id: int) -> bool:
        """
        删除规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            是否删除成功
            
        Raises:
            ValueError: 规则不存在
        """
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            raise ValueError("规则不存在")
        
        self.db.delete(rule)
        self.db.commit()
        
        logger.info(f"删除通知目标规则: {rule_id}")
        return True
    
    def toggle_rule(self, rule_id: int, enabled: bool, updated_by: Optional[str] = None) -> NotificationTargetRule:
        """
        启用/禁用规则
        
        Args:
            rule_id: 规则ID
            enabled: 是否启用
            updated_by: 更新人
            
        Returns:
            更新后的规则对象
            
        Raises:
            ValueError: 规则不存在
        """
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            raise ValueError("规则不存在")
        
        rule.enabled = enabled
        rule.updated_at = datetime.now()
        if updated_by:
            rule.updated_by = updated_by
        
        self.db.commit()
        self.db.refresh(rule)
        
        logger.info(f"{'启用' if enabled else '禁用'}通知目标规则: {rule_id}")
        return rule
    
    def match_rules(
        self,
        alert_level: Optional[str] = None,
        device_id: Optional[int] = None,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据告警信息匹配通知目标规则
        
        Args:
            alert_level: 告警级别
            device_id: 设备ID
            device_name: 设备名称
            device_type: 设备类型
            category: 告警分类
            
        Returns:
            匹配的规则列表（按优先级排序）
        """
        # 获取所有启用的规则
        rules = self.db.query(NotificationTargetRule).filter(
            NotificationTargetRule.enabled == True
        ).order_by(NotificationTargetRule.priority.asc()).all()
        
        matched_rules = []
        
        for rule in rules:
            is_match = False
            
            # 按规则类型匹配
            if rule.rule_type == "alert_level":
                is_match = self._match_alert_level(rule, alert_level)
            elif rule.rule_type == "device":
                is_match = self._match_device(rule, device_id, device_type)
            elif rule.rule_type == "category":
                is_match = self._match_category(rule, category)
            elif rule.rule_type == "custom":
                # 自定义规则暂不实现
                is_match = False
            
            if is_match:
                matched_rules.append({
                    "id": rule.id,
                    "name": rule.name,
                    "notify_channels": json.loads(rule.notify_channels) if rule.notify_channels else [],
                    "notify_receivers": json.loads(rule.notify_receivers) if rule.notify_receivers else [],
                    "notify_interval": rule.notify_interval,
                    "max_notify_count": rule.max_notify_count,
                    "priority": rule.priority,
                })
        
        return matched_rules
    
    def _match_alert_level(self, rule: NotificationTargetRule, alert_level: Optional[str]) -> bool:
        """匹配告警级别规则"""
        if not alert_level:
            return False
        
        try:
            conditions = json.loads(rule.match_conditions) if rule.match_conditions else {}
            levels = conditions.get("levels", [])
            return alert_level in levels
        except (json.JSONDecodeError, TypeError):
            return False
    
    def _match_device(self, rule: NotificationTargetRule, device_id: Optional[int], device_type: Optional[str]) -> bool:
        """匹配设备规则"""
        try:
            conditions = json.loads(rule.match_conditions) if rule.match_conditions else {}
            device_ids = conditions.get("device_ids", [])
            device_types = conditions.get("device_types", [])
            
            if device_id and device_id in device_ids:
                return True
            if device_type and device_type in device_types:
                return True
            
            return False
        except (json.JSONDecodeError, TypeError):
            return False
    
    def _match_category(self, rule: NotificationTargetRule, category: Optional[str]) -> bool:
        """匹配告警分类规则"""
        if not category:
            return False
        
        try:
            conditions = json.loads(rule.match_conditions) if rule.match_conditions else {}
            categories = conditions.get("categories", [])
            return category in categories
        except (json.JSONDecodeError, TypeError):
            return False
    
    def _validate_rule_type(self, rule_type: str) -> bool:
        """
        验证规则类型
        
        Args:
            rule_type: 规则类型
            
        Returns:
            是否有效
            
        Raises:
            ValueError: 无效的规则类型
        """
        if rule_type not in self.VALID_RULE_TYPES:
            raise ValueError(f"无效的规则类型: {rule_type}，支持的类型: {', '.join(self.VALID_RULE_TYPES)}")
        return True
    
    def _validate_notify_channel(self, channel: str) -> bool:
        """
        验证通知渠道
        
        Args:
            channel: 通知渠道
            
        Returns:
            是否有效
            
        Raises:
            ValueError: 无效的通知渠道
        """
        if channel not in self.VALID_NOTIFY_CHANNELS:
            raise ValueError(f"无效的通知渠道: {channel}，支持的渠道: {', '.join(self.VALID_NOTIFY_CHANNELS)}")
        return True


def get_target_rule_service(db: Session) -> NotificationTargetRuleService:
    """
    获取通知目标规则服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        NotificationTargetRuleService实例
    """
    return NotificationTargetRuleService(db)