"""
MON-028 告警审计日志服务
提供告警操作审计日志的创建、查询、统计功能

功能：
- 记录告警的创建、确认、解决、关闭等操作
- 跟踪告警状态变更、分配变更等详细变更
- 支持按告警ID、操作人、时间范围等多维度查询
- 关联工单，用于审计追溯
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from modules.foundation.db_models.alert import AlertAuditLog, Alert, AlertStatus, AlertLevel

logger = logging.getLogger(__name__)


# ============== 数据结构 ==============

class AuditAction:
    """审计操作类型常量"""
    CREATE = "create"
    ACKNOWLEDGE = "acknowledge"
    RESOLVE = "resolve"
    CLOSE = "close"
    UPDATE = "update"
    DELETE = "delete"
    ASSIGN = "assign"
    ESCALATE = "escalate"
    SUPPRESS = "suppress"
    RESTORE = "restore"

    @classmethod
    def all_actions(cls) -> List[str]:
        return [
            cls.CREATE, cls.ACKNOWLEDGE, cls.RESOLVE, cls.CLOSE,
            cls.UPDATE, cls.DELETE, cls.ASSIGN, cls.ESCALATE,
            cls.SUPPRESS, cls.RESTORE
        ]


@dataclass
class AuditLogFilter:
    """审计日志查询过滤条件"""
    alert_id: Optional[int] = None
    alert_key: Optional[str] = None
    action: Optional[str] = None
    operator: Optional[str] = None
    field_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    workorder_id: Optional[int] = None


@dataclass
class AuditLogStats:
    """审计日志统计结果"""
    total_count: int = 0
    by_action: Dict[str, int] = field(default_factory=dict)
    by_operator: Dict[str, int] = field(default_factory=dict)
    by_day: Dict[str, int] = field(default_factory=dict)


# ============== 服务类 ==============

class AlertAuditService:
    """
    告警审计日志服务
    
    提供统一的接口进行告警操作审计日志的创建和查询，
    确保所有告警操作都能被追踪和审计。
    """

    def __init__(self, db: Session):
        """
        初始化审计服务
        
        Args:
            db: 数据库会话
        """
        self._db = db

    def create_log(
        self,
        alert_id: int,
        action: str,
        alert_key: Optional[str] = None,
        operator: Optional[str] = None,
        operator_ip: Optional[str] = None,
        field_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        reason: Optional[str] = None,
        workorder_id: Optional[int] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AlertAuditLog:
        """
        创建审计日志记录
        
        Args:
            alert_id: 告警ID
            action: 操作类型 (create, acknowledge, resolve, close, update, delete)
            alert_key: 告警唯一标识
            operator: 操作人
            operator_ip: 操作人IP
            field_name: 被修改的字段名
            old_value: 旧值
            new_value: 新值
            reason: 操作原因
            workorder_id: 关联工单ID
            user_agent: 用户代理
            request_id: 请求ID
            
        Returns:
            创建的审计日志记录
        """
        # 如果没有提供alert_key，尝试从数据库获取
        if not alert_key:
            alert = self._db.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert_key = alert.alert_key

        audit_log = AlertAuditLog(
            alert_id=alert_id,
            alert_key=alert_key,
            action=action,
            operator=operator,
            operator_ip=operator_ip,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            workorder_id=workorder_id,
            user_agent=user_agent,
            request_id=request_id,
        )

        self._db.add(audit_log)
        self._db.commit()
        self._db.refresh(audit_log)

        logger.info(f"Created audit log: alert_id={alert_id}, action={action}, operator={operator}")
        return audit_log

    def create_status_change_log(
        self,
        alert_id: int,
        old_status: AlertStatus,
        new_status: AlertStatus,
        operator: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> AlertAuditLog:
        """
        创建状态变更审计日志
        
        Args:
            alert_id: 告警ID
            old_status: 旧状态
            new_status: 新状态
            operator: 操作人
            reason: 变更原因
            **kwargs: 其他参数
            
        Returns:
            创建的审计日志记录
        """
        return self.create_log(
            alert_id=alert_id,
            action=AuditAction.UPDATE if old_status != new_status else AuditAction.CREATE,
            field_name="status",
            old_value=old_status.value if isinstance(old_status, AlertStatus) else str(old_status),
            new_value=new_status.value if isinstance(new_status, AlertStatus) else str(new_status),
            operator=operator,
            reason=reason,
            **kwargs
        )

    def create_assignment_log(
        self,
        alert_id: int,
        old_assignee: Optional[str],
        new_assignee: Optional[str],
        operator: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> AlertAuditLog:
        """
        创建分配变更审计日志
        
        Args:
            alert_id: 告警ID
            old_assignee: 原处理人
            new_assignee: 新处理人
            operator: 操作人
            reason: 变更原因
            **kwargs: 其他参数
            
        Returns:
            创建的审计日志记录
        """
        return self.create_log(
            alert_id=alert_id,
            action=AuditAction.ASSIGN,
            field_name="assignee",
            old_value=old_assignee,
            new_value=new_assignee,
            operator=operator,
            reason=reason,
            **kwargs
        )

    def create_level_change_log(
        self,
        alert_id: int,
        old_level: AlertLevel,
        new_level: AlertLevel,
        operator: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> AlertAuditLog:
        """
        创建级别变更审计日志
        
        Args:
            alert_id: 告警ID
            old_level: 旧级别
            new_level: 新级别
            operator: 操作人
            reason: 变更原因
            **kwargs: 其他参数
            
        Returns:
            创建的审计日志记录
        """
        return self.create_log(
            alert_id=alert_id,
            action=AuditAction.UPDATE,
            field_name="level",
            old_value=old_level.value if isinstance(old_level, AlertLevel) else str(old_level),
            new_value=new_level.value if isinstance(new_level, AlertLevel) else str(new_level),
            operator=operator,
            reason=reason,
            **kwargs
        )

    def query_logs(
        self,
        filters: Optional[AuditLogFilter] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[AlertAuditLog], int]:
        """
        查询审计日志
        
        Args:
            filters: 查询过滤条件
            page: 页码 (从1开始)
            page_size: 每页数量
            
        Returns:
            (审计日志列表, 总数)
        """
        query = self._db.query(AlertAuditLog)

        if filters:
            if filters.alert_id:
                query = query.filter(AlertAuditLog.alert_id == filters.alert_id)
            if filters.alert_key:
                query = query.filter(AlertAuditLog.alert_key == filters.alert_key)
            if filters.action:
                query = query.filter(AlertAuditLog.action == filters.action)
            if filters.operator:
                query = query.filter(AlertAuditLog.operator == filters.operator)
            if filters.field_name:
                query = query.filter(AlertAuditLog.field_name == filters.field_name)
            if filters.start_date:
                query = query.filter(AlertAuditLog.created_at >= filters.start_date)
            if filters.end_date:
                query = query.filter(AlertAuditLog.created_at <= filters.end_date)
            if filters.workorder_id:
                query = query.filter(AlertAuditLog.workorder_id == filters.workorder_id)

        total = query.count()
        offset = (page - 1) * page_size
        
        logs = query.order_by(desc(AlertAuditLog.created_at)).offset(offset).limit(page_size).all()
        
        return logs, total

    def get_logs_by_alert_id(
        self,
        alert_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[AlertAuditLog], int]:
        """
        获取指定告警的所有审计日志
        
        Args:
            alert_id: 告警ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            (审计日志列表, 总数)
        """
        filters = AuditLogFilter(alert_id=alert_id)
        return self.query_logs(filters, page, page_size)

    def get_logs_by_operator(
        self,
        operator: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[AlertAuditLog], int]:
        """
        获取指定操作人的所有审计日志
        
        Args:
            operator: 操作人
            page: 页码
            page_size: 每页数量
            
        Returns:
            (审计日志列表, 总数)
        """
        filters = AuditLogFilter(operator=operator)
        return self.query_logs(filters, page, page_size)

    def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[AlertAuditLog], int]:
        """
        获取指定时间范围内的审计日志
        
        Args:
            start_date: 开始时间
            end_date: 结束时间
            page: 页码
            page_size: 每页数量
            
        Returns:
            (审计日志列表, 总数)
        """
        filters = AuditLogFilter(start_date=start_date, end_date=end_date)
        return self.query_logs(filters, page, page_size)

    def get_stats(
        self,
        alert_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AuditLogStats:
        """
        获取审计日志统计信息
        
        Args:
            alert_id: 告警ID (可选)
            start_date: 开始时间 (可选)
            end_date: 结束时间 (可选)
            
        Returns:
            统计结果
        """
        query = self._db.query(AlertAuditLog)

        if alert_id:
            query = query.filter(AlertAuditLog.alert_id == alert_id)
        if start_date:
            query = query.filter(AlertAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AlertAuditLog.created_at <= end_date)

        total = query.count()
        
        # 按操作类型统计
        action_counts = {}
        for log in query.all():
            action = log.action
            action_counts[action] = action_counts.get(action, 0) + 1

        # 按操作人统计
        operator_counts = {}
        for log in query.all():
            operator = log.operator or "system"
            operator_counts[operator] = operator_counts.get(operator, 0) + 1

        # 按日期统计
        day_counts = {}
        for log in query.all():
            day = log.created_at.strftime("%Y-%m-%d")
            day_counts[day] = day_counts.get(day, 0) + 1

        return AuditLogStats(
            total_count=total,
            by_action=action_counts,
            by_operator=operator_counts,
            by_day=day_counts,
        )

    def get_operation_timeline(
        self,
        alert_id: int,
    ) -> List[Dict[str, Any]]:
        """
        获取告警的操作时间线
        
        Args:
            alert_id: 告警ID
            
        Returns:
            操作时间线列表，按时间倒序
        """
        logs, _ = self.get_logs_by_alert_id(alert_id, page=1, page_size=1000)
        
        timeline = []
        for log in logs:
            timeline.append({
                "id": log.id,
                "action": log.action,
                "operator": log.operator,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "reason": log.reason,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })
        
        return timeline

    def delete_logs_by_alert_id(self, alert_id: int) -> int:
        """
        删除指定告警的所有审计日志（仅用于测试或数据清理）
        
        Args:
            alert_id: 告警ID
            
        Returns:
            删除的记录数
        """
        count = self._db.query(AlertAuditLog).filter(
            AlertAuditLog.alert_id == alert_id
        ).delete()
        self._db.commit()
        return count


# ============== 辅助函数 ==============

def get_audit_service(db: Session) -> AlertAuditService:
    """
    获取审计服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        AlertAuditService实例
    """
    return AlertAuditService(db)


def create_auto_audit_log(
    db: Session,
    alert_id: int,
    action: str,
    operator: Optional[str] = "system",
    **kwargs
) -> Optional[AlertAuditLog]:
    """
    快速创建审计日志的辅助函数
    
    Args:
        db: 数据库会话
        alert_id: 告警ID
        action: 操作类型
        operator: 操作人 (默认为system)
        **kwargs: 其他参数
        
    Returns:
        创建的审计日志或None
    """
    try:
        service = AlertAuditService(db)
        return service.create_log(
            alert_id=alert_id,
            action=action,
            operator=operator,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to create auto audit log: {e}")
        return None