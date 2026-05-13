"""
SLA Manager Module
提供SLA实时计时器计算和超时升级管理功能
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SLAStatus:
    """SLA状态数据类"""
    workorder_id: int
    remaining_seconds: int
    deadline: datetime
    sla_level: str  # P1, P2, P3, P4
    breach_warning: bool
    is_breached: bool
    escalation_level: int
    response_timer: Optional[Dict] = None
    resolve_timer: Optional[Dict] = None


class SLAManager:
    """
    SLA管理器
    
    提供SLA实时计时器计算和超时升级功能
    支持响应SLA和解决SLA两种类型
    """
    
    # SLA配置阈值(分钟) - 按优先级
    RESPONSE_THRESHOLDS = {
        'P1': 15,
        'P2': 30,
        'P3': 60,
        'P4': 120
    }
    
    RESOLVE_THRESHOLDS = {
        'P1': 60,
        'P2': 240,
        'P3': 480,
        'P4': 1440
    }
    
    # 升级级别定义
    ESCALATION_LEVELS = [
        {'level': 1, 'delay_minutes': 0, 'notify': ['assignee']},
        {'level': 2, 'delay_minutes': 15, 'notify': ['assignee', 'team_lead']},
        {'level': 3, 'delay_minutes': 30, 'notify': ['assignee', 'team_lead', 'manager']},
        {'level': 4, 'delay_minutes': 60, 'notify': ['assignee', 'team_lead', 'manager', 'director']},
    ]
    
    def __init__(self, redis_client=None, db_session=None, notification_service=None):
        """
        初始化SLA管理器
        
        Args:
            redis_client: Redis客户端用于SLA计时
            db_session: 数据库会话
            notification_service: 通知服务
        """
        self.redis = redis_client
        self.db = db_session
        self.notification = notification_service
    
    def _get_sla_key(self, workorder_id: int, sla_type: str) -> str:
        """获取Redis SLA键"""
        return f"workorder:sla:{sla_type}:{workorder_id}"
    
    def compute_sla_status(self, workorder_id: int) -> Dict[str, Any]:
        """
        计算工单的SLA状态
        
        Args:
            workorder_id: 工单ID
            
        Returns:
            包含以下字段的字典:
            - remaining_seconds: 剩余秒数(负数表示已超时)
            - deadline: 截止时间
            - sla_level: SLA级别(P1-P4)
            - breach_warning: 是否警告(剩余时间<15分钟)
            - is_breached: 是否已超时
            - escalation_level: 当前升级级别(0-4)
            - response_timer: 响应SLA详情
            - resolve_timer: 解决SLA详情
        """
        now = datetime.now()
        
        # 获取SLA配置 - 从数据库或缓存
        priority, created_at, status = self._get_workorder_info(workorder_id)
        
        if not priority or not created_at:
            return {
                'workorder_id': workorder_id,
                'remaining_seconds': None,
                'deadline': None,
                'sla_level': None,
                'breach_warning': False,
                'is_breached': False,
                'escalation_level': 0,
                'error': '工单不存在'
            }
        
        # 计算响应SLA
        response_deadline = created_at + timedelta(minutes=self.RESPONSE_THRESHOLDS.get(priority, 60))
        response_remaining = (response_deadline - now).total_seconds()
        response_timer = self._build_timer_info(
            workorder_id, priority, 'response', response_deadline, now
        )
        
        # 计算解决SLA
        resolve_deadline = created_at + timedelta(minutes=self.RESOLVE_THRESHOLDS.get(priority, 480))
        resolve_remaining = (resolve_deadline - now).total_seconds()
        resolve_timer = self._build_timer_info(
            workorder_id, priority, 'resolve', resolve_deadline, now
        )
        
        # 确定主要状态(取较早超时的SLA)
        if response_remaining < resolve_remaining:
            main_remaining = response_remaining
            main_deadline = response_deadline
            main_type = 'response'
        else:
            main_remaining = resolve_remaining
            main_deadline = resolve_deadline
            main_type = 'resolve'
        
        is_breached = main_remaining < 0
        breach_warning = 0 < main_remaining < 900  # < 15分钟警告
        
        # 计算升级级别
        escalation_level = 0
        if is_breached:
            breach_minutes = int(-main_remaining / 60)
            for level_info in self.ESCALATION_LEVELS:
                if breach_minutes >= level_info['delay_minutes']:
                    escalation_level = level_info['level']
        
        # 如果工单已解决/关闭,清除超时状态
        if status in ['resolved', 'closed', 'cancelled']:
            is_breached = False
            breach_warning = False
            escalation_level = 0
        
        return {
            'workorder_id': workorder_id,
            'remaining_seconds': int(main_remaining),
            'deadline': main_deadline.isoformat(),
            'sla_level': priority,
            'breach_warning': breach_warning,
            'is_breached': is_breached,
            'escalation_level': escalation_level,
            'sla_type': main_type,
            'response_timer': response_timer,
            'resolve_timer': resolve_timer
        }
    
    def _build_timer_info(self, workorder_id: int, priority: str, 
                          sla_type: str, deadline: datetime, 
                          now: datetime) -> Dict[str, Any]:
        """构建SLA计时器信息"""
        remaining = (deadline - now).total_seconds()
        is_breached = remaining < 0
        threshold_minutes = (self.RESPONSE_THRESHOLDS if sla_type == 'response' 
                             else self.RESOLVE_THRESHOLDS).get(priority, 60)
        
        return {
            'sla_type': sla_type,
            'priority': priority,
            'threshold_minutes': threshold_minutes,
            'deadline': deadline.isoformat(),
            'remaining_seconds': int(remaining),
            'is_breached': is_breached,
            'breach_duration_seconds': int(-remaining) if is_breached else 0
        }
    
    def _get_workorder_info(self, workorder_id: int) -> Tuple[Optional[str], Optional[datetime], Optional[str]]:
        """获取工单的优先级、创建时间和状态"""
        if self.db:
            try:
                from modules.foundation.db_models.workorder import WorkOrder
                wo = self.db.query(WorkOrder).filter(
                    WorkOrder.id == workorder_id,
                    WorkOrder.is_deleted == False
                ).first()
                if wo:
                    return (wo.priority.value if wo.priority else 'P3',
                            wo.created_at,
                            wo.status.value if wo.status else None)
            except Exception as e:
                logger.error(f"Failed to get workorder info: {e}")
        
        return None, None, None
    
    def check_escalation(self, workorder_id: int) -> List[Dict[str, Any]]:
        """
        检查并触发升级
        
        Args:
            workorder_id: 工单ID
            
        Returns:
            升级事件列表
        """
        escalations = []
        status = self.compute_sla_status(workorder_id)
        
        if not status.get('is_breached'):
            return escalations
        
        breach_seconds = -status['remaining_seconds']
        breach_minutes = int(breach_seconds / 60)
        
        # 触发所有适用的升级级别 (delay_minutes <= breach_minutes)
        for level_info in self.ESCALATION_LEVELS:
            if breach_minutes >= level_info['delay_minutes']:
                escalation = {
                    'workorder_id': workorder_id,
                    'sla_type': status.get('sla_type', 'resolve'),
                    'escalation_level': level_info['level'],
                    'notified_roles': level_info['notify'],
                    'breach_duration_minutes': breach_minutes,
                    'timestamp': datetime.now().isoformat()
                }
                escalations.append(escalation)
                
                # 保存升级记录到数据库
                self._save_escalation_record(escalation)
                
                # 发送通知
                if self.notification:
                    self._send_escalation_notification(escalation)
        
        return escalations
    
    def _save_escalation_record(self, escalation: Dict[str, Any]) -> bool:
        """保存升级记录到数据库"""
        if not self.db:
            return False
        
        try:
            from modules.foundation.db_models.workorder import WorkOrderEscalation
            
            record = WorkOrderEscalation(
                work_order_id=escalation['workorder_id'],
                escalation_level=escalation['escalation_level'],
                notified_roles=json.dumps(escalation['notified_roles']),
                breach_duration_minutes=escalation['breach_duration_minutes'],
                sla_type=escalation.get('sla_type', 'resolve'),
                is_notified=True
            )
            self.db.add(record)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save escalation record: {e}")
            self.db.rollback()
            return False
    
    def _send_escalation_notification(self, escalation: Dict[str, Any]) -> None:
        """发送升级通知"""
        if not self.notification:
            return
        
        try:
            self.notification.send(
                notification_type='sla_escalation',
                title=f"SLA超时升级 - 工单 {escalation['workorder_id']}",
                content=f"SLA类型: {escalation.get('sla_type', 'resolve')}, "
                        f"升级级别: L{escalation['escalation_level']}, "
                        f"超时时长: {escalation['breach_duration_minutes']}分钟",
                recipients=escalation['notified_roles']
            )
        except Exception as e:
            logger.error(f"Failed to send escalation notification: {e}")
    
    def start_sla_timer(self, workorder_id: int, priority: str, sla_type: str = 'response') -> Dict[str, Any]:
        """
        启动SLA计时器
        
        Args:
            workorder_id: 工单ID
            priority: 优先级
            sla_type: SLA类型(response/resolve)
            
        Returns:
            计时器信息
        """
        now = datetime.now()
        thresholds = (self.RESPONSE_THRESHOLDS if sla_type == 'response' 
                      else self.RESOLVE_THRESHOLDS)
        threshold_minutes = thresholds.get(priority, 60)
        deadline = now + timedelta(minutes=threshold_minutes)
        
        timer_info = {
            'workorder_id': workorder_id,
            'sla_type': sla_type,
            'priority': priority,
            'start_time': now.isoformat(),
            'deadline': deadline.isoformat(),
            'threshold_minutes': threshold_minutes,
            'is_breached': False,
            'escalation_level': 0,
            'last_check': now.isoformat()
        }
        
        if self.redis:
            try:
                key = self._get_sla_key(workorder_id, sla_type)
                self.redis.set(key, json.dumps(timer_info), ex=60*60*24*7)  # 7天TTL
            except Exception as e:
                logger.error(f"Failed to start SLA timer in Redis: {e}")
        
        return timer_info
    
    def get_escalation_history(self, workorder_id: int) -> List[Dict[str, Any]]:
        """获取工单的升级历史"""
        if not self.db:
            return []
        
        try:
            from modules.foundation.db_models.workorder import WorkOrderEscalation
            records = self.db.query(WorkOrderEscalation).filter(
                WorkOrderEscalation.work_order_id == workorder_id
            ).order_by(WorkOrderEscalation.created_at.desc()).all()
            
            return [
                {
                    'id': r.id,
                    'escalation_level': r.escalation_level,
                    'notified_roles': json.loads(r.notified_roles) if r.notified_roles else [],
                    'breach_duration_minutes': r.breach_duration_minutes,
                    'sla_type': r.sla_type,
                    'created_at': r.created_at.isoformat() if r.created_at else None
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"Failed to get escalation history: {e}")
            return []