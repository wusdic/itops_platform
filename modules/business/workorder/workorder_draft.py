"""
Work Order Draft Module
Provides draft save and auto-recovery functionality for work orders
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DraftStatus(str, Enum):
    """Draft status"""
    ACTIVE = "active"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


@dataclass
class WorkOrderDraft:
    """Work order draft model (not a DB model, used for API responses)"""
    draft_id: str
    user_id: str
    username: str
    
    # Draft content
    order_type: str = None
    title: str = None
    description: str = None
    priority: str = "P3"
    device_id: int = None
    device_name: str = None
    device_ip: str = None
    assignee: str = None
    expected_end: datetime = None
    impact: str = None
    tags: List[str] = field(default_factory=list)
    attachments: List[Dict] = field(default_factory=list)
    
    # Metadata
    status: DraftStatus = DraftStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = None
    
    # Auto-save tracking
    is_auto_save: bool = False
    last_auto_save: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'draft_id': self.draft_id,
            'user_id': self.user_id,
            'username': self.username,
            'order_type': self.order_type,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_ip': self.device_ip,
            'assignee': self.assignee,
            'expected_end': self.expected_end.isoformat() if self.expected_end else None,
            'impact': self.impact,
            'tags': self.tags,
            'attachments': self.attachments,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_auto_save': self.is_auto_save,
            'last_auto_save': self.last_auto_save.isoformat() if self.last_auto_save else None,
        }


class WorkOrderDraftManager:
    """
    Work Order Draft Manager
    
    Manages work order draft save, auto-save, and recovery functionality.
    Drafts are stored in Redis for quick access with periodic persistence to DB.
    """
    
    # Draft expiration time (7 days)
    DRAFT_EXPIRATION_DAYS = 7
    
    # Auto-save interval (30 seconds)
    AUTO_SAVE_INTERVAL_SECONDS = 30
    
    def __init__(self, redis_client=None, db_session=None):
        """
        Initialize Draft Manager
        
        Args:
            redis_client: Redis client for draft storage
            db_session: Database session for persistence
        """
        self.redis = redis_client
        self.db = db_session
    
    def _get_draft_key(self, user_id: str, draft_id: str = None) -> str:
        """Get Redis key for draft"""
        if draft_id:
            return f"workorder:draft:{user_id}:{draft_id}"
        return f"workorder:draft:{user_id}:*"
    
    def _get_sla_key(self, workorder_id: int) -> str:
        """Get Redis key for SLA tracking"""
        return f"workorder:sla:{workorder_id}"
    
    def save_draft(
        self,
        user_id: str,
        username: str,
        draft_id: str = None,
        draft_data: Dict[str, Any] = None,
        is_auto_save: bool = False
    ) -> Tuple[str, WorkOrderDraft]:
        """
        Save a work order draft
        
        Args:
            user_id: User ID
            username: Username
            draft_id: Existing draft ID (for updates) or None (for new)
            draft_data: Draft content
            is_auto_save: Whether this is an auto-save
            
        Returns:
            (draft_id, WorkOrderDraft)
        """
        import uuid
        
        # Generate new draft_id if not provided
        if not draft_id:
            draft_id = str(uuid.uuid4())
        
        now = datetime.now()
        
        # Create or update draft
        draft = WorkOrderDraft(
            draft_id=draft_id,
            user_id=user_id,
            username=username,
            order_type=draft_data.get('order_type') if draft_data else None,
            title=draft_data.get('title') if draft_data else None,
            description=draft_data.get('description') if draft_data else None,
            priority=draft_data.get('priority', 'P3') if draft_data else 'P3',
            device_id=draft_data.get('device_id') if draft_data else None,
            device_name=draft_data.get('device_name') if draft_data else None,
            device_ip=draft_data.get('device_ip') if draft_data else None,
            assignee=draft_data.get('assignee') if draft_data else None,
            expected_end=datetime.fromisoformat(draft_data['expected_end']) if draft_data and draft_data.get('expected_end') else None,
            impact=draft_data.get('impact') if draft_data else None,
            tags=draft_data.get('tags', []) if draft_data else [],
            attachments=draft_data.get('attachments', []) if draft_data else [],
            status=DraftStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=self.DRAFT_EXPIRATION_DAYS),
            is_auto_save=is_auto_save,
            last_auto_save=now if is_auto_save else None
        )
        
        # Store in Redis
        if self.redis:
            try:
                key = self._get_draft_key(user_id, draft_id)
                self.redis.set(key, json.dumps(draft.to_dict()), ex=60*60*24*self.DRAFT_EXPIRATION_DAYS)
            except Exception as e:
                logger.error(f"Failed to save draft to Redis: {e}")
        
        return draft_id, draft
    
    def get_draft(self, user_id: str, draft_id: str) -> Optional[WorkOrderDraft]:
        """
        Get a draft by ID
        
        Args:
            user_id: User ID
            draft_id: Draft ID
            
        Returns:
            WorkOrderDraft or None
        """
        if not self.redis:
            return None
        
        try:
            key = self._get_draft_key(user_id, draft_id)
            data = self.redis.get(key)
            if data:
                return self._dict_to_draft(json.loads(data))
        except Exception as e:
            logger.error(f"Failed to get draft from Redis: {e}")
        
        return None
    
    def list_drafts(self, user_id: str) -> List[WorkOrderDraft]:
        """
        List all drafts for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of WorkOrderDraft
        """
        if not self.redis:
            return []
        
        try:
            pattern = self._get_draft_key(user_id)
            keys = self.redis.keys(pattern)
            drafts = []
            for key in keys:
                data = self.redis.get(key)
                if data:
                    drafts.append(self._dict_to_draft(json.loads(data)))
            
            # Sort by updated_at descending
            drafts.sort(key=lambda d: d.updated_at, reverse=True)
            return drafts
        except Exception as e:
            logger.error(f"Failed to list drafts from Redis: {e}")
            return []
    
    def delete_draft(self, user_id: str, draft_id: str) -> bool:
        """
        Delete a draft
        
        Args:
            user_id: User ID
            draft_id: Draft ID
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            key = self._get_draft_key(user_id, draft_id)
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete draft from Redis: {e}")
            return False
    
    def cleanup_expired_drafts(self) -> int:
        """
        Clean up expired drafts
        
        Returns:
            Number of drafts cleaned up
        """
        # This would typically be a scheduled task
        # For now, Redis TTL handles expiration automatically
        return 0
    
    def _dict_to_draft(self, data: Dict) -> WorkOrderDraft:
        """Convert dictionary to WorkOrderDraft"""
        return WorkOrderDraft(
            draft_id=data['draft_id'],
            user_id=data['user_id'],
            username=data['username'],
            order_type=data.get('order_type'),
            title=data.get('title'),
            description=data.get('description'),
            priority=data.get('priority', 'P3'),
            device_id=data.get('device_id'),
            device_name=data.get('device_name'),
            device_ip=data.get('device_ip'),
            assignee=data.get('assignee'),
            expected_end=datetime.fromisoformat(data['expected_end']) if data.get('expected_end') else None,
            impact=data.get('impact'),
            tags=data.get('tags', []),
            attachments=data.get('attachments', []),
            status=DraftStatus(data.get('status', 'active')),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            is_auto_save=data.get('is_auto_save', False),
            last_auto_save=datetime.fromisoformat(data['last_auto_save']) if data.get('last_auto_save') else None
        )


class SLATracker:
    """
    SLA Tracker and Escalation Manager
    
    Tracks SLA timers for work orders and triggers escalations when thresholds are exceeded.
    """
    
    # SLA breach thresholds (in minutes)
    RESPONSE_BREACH_THRESHOLDS = {
        'P1': 15,
        'P2': 30,
        'P3': 60,
        'P4': 120
    }
    
    RESOLVE_BREACH_THRESHOLDS = {
        'P1': 60,
        'P2': 240,
        'P3': 480,
        'P4': 1440
    }
    
    # Escalation levels
    ESCALATION_LEVELS = [
        {'level': 1, 'delay_minutes': 0, 'notify': ['assignee']},
        {'level': 2, 'delay_minutes': 15, 'notify': ['assignee', 'team_lead']},
        {'level': 3, 'delay_minutes': 30, 'notify': ['assignee', 'team_lead', 'manager']},
        {'level': 4, 'delay_minutes': 60, 'notify': ['assignee', 'team_lead', 'manager', 'director']},
    ]
    
    def __init__(self, redis_client=None, db_session=None, notification_service=None):
        """
        Initialize SLA Tracker
        
        Args:
            redis_client: Redis client for SLA tracking
            db_session: Database session
            notification_service: Notification service for escalations
        """
        self.redis = redis_client
        self.db = db_session
        self.notification = notification_service
    
    def _get_sla_key(self, workorder_id: int, sla_type: str) -> str:
        """Get Redis key for SLA tracking"""
        return f"workorder:sla:{sla_type}:{workorder_id}"
    
    def start_sla_timer(self, workorder_id: int, priority: str, sla_type: str = 'response') -> Dict[str, Any]:
        """
        Start SLA timer for a work order
        
        Args:
            workorder_id: Work order ID
            priority: Work order priority (P1-P4)
            sla_type: SLA type ('response' or 'resolve')
            
        Returns:
            SLA timer info
        """
        now = datetime.now()
        
        # Calculate deadline
        if sla_type == 'response':
            threshold_minutes = self.RESPONSE_BREACH_THRESHOLDS.get(priority, 60)
        else:
            threshold_minutes = self.RESOLVE_BREACH_THRESHOLDS.get(priority, 480)
        
        deadline = now + timedelta(minutes=threshold_minutes)
        
        timer_info = {
            'workorder_id': workorder_id,
            'sla_type': sla_type,
            'priority': priority,
            'start_time': now.isoformat(),
            'deadline': deadline.isoformat(),
            'threshold_minutes': threshold_minutes,
            'breached': False,
            'escalation_level': 0,
            'last_check': now.isoformat()
        }
        
        if self.redis:
            try:
                key = self._get_sla_key(workorder_id, sla_type)
                self.redis.set(key, json.dumps(timer_info), ex=60*60*24*7)  # 7 days TTL
            except Exception as e:
                logger.error(f"Failed to start SLA timer in Redis: {e}")
        
        return timer_info
    
    def check_sla_status(self, workorder_id: int, sla_type: str = 'response') -> Dict[str, Any]:
        """
        Check current SLA status
        
        Args:
            workorder_id: Work order ID
            sla_type: SLA type ('response' or 'resolve')
            
        Returns:
            SLA status info
        """
        now = datetime.now()
        
        if self.redis:
            try:
                key = self._get_sla_key(workorder_id, sla_type)
                data = self.redis.get(key)
                if data:
                    timer_info = json.loads(data)
                    
                    # Check if breached
                    deadline = datetime.fromisoformat(timer_info['deadline'])
                    if now > deadline:
                        timer_info['breached'] = True
                        timer_info['breach_duration_minutes'] = int((now - deadline).total_seconds() / 60)
                    
                    # Calculate remaining time
                    if not timer_info['breached']:
                        timer_info['remaining_minutes'] = int((deadline - now).total_seconds() / 60)
                    else:
                        timer_info['remaining_minutes'] = 0
                    
                    return timer_info
            except Exception as e:
                logger.error(f"Failed to check SLA status: {e}")
        
        return {
            'workorder_id': workorder_id,
            'sla_type': sla_type,
            'breached': False,
            'remaining_minutes': None
        }
    
    def record_sla_response(self, workorder_id: int) -> Dict[str, Any]:
        """
        Record SLA response time (when work order is first acknowledged)
        
        Args:
            workorder_id: Work order ID
            
        Returns:
            SLA response info
        """
        now = datetime.now()
        
        # Remove response SLA timer (response completed)
        if self.redis:
            try:
                key = self._get_sla_key(workorder_id, 'response')
                self.redis.delete(key)
            except Exception as e:
                logger.error(f"Failed to clear SLA response timer: {e}")
        
        return {
            'workorder_id': workorder_id,
            'response_recorded_at': now.isoformat(),
            'response_sla_met': True
        }
    
    def check_and_escalate(self, workorder_id: int) -> List[Dict[str, Any]]:
        """
        Check SLA status and trigger escalations if needed
        
        Args:
            workorder_id: Work order ID
            
        Returns:
            List of escalation events
        """
        escalations = []
        now = datetime.now()
        
        # Check both response and resolve SLA
        for sla_type in ['response', 'resolve']:
            status = self.check_sla_status(workorder_id, sla_type)
            
            if status.get('breached'):
                breach_duration = status.get('breach_duration_minutes', 0)
                current_level = status.get('escalation_level', 0)
                
                # Check if we need to escalate to next level
                for esc_level in self.ESCALATION_LEVELS[current_level + 1:]:
                    if breach_duration >= esc_level['delay_minutes']:
                        escalation = {
                            'workorder_id': workorder_id,
                            'sla_type': sla_type,
                            'escalation_level': esc_level['level'],
                            'notified_roles': esc_level['notify'],
                            'breach_duration_minutes': breach_duration,
                            'timestamp': now.isoformat()
                        }
                        escalations.append(escalation)
                        
                        # Send notifications
                        if self.notification:
                            self._send_escalation_notification(escalation)
                        
                        # Update escalation level
                        status['escalation_level'] = esc_level['level']
                        if self.redis:
                            try:
                                key = self._get_sla_key(workorder_id, sla_type)
                                self.redis.set(key, json.dumps(status), ex=60*60*24*7)
                            except Exception as e:
                                logger.error(f"Failed to update escalation level: {e}")
        
        return escalations
    
    def _send_escalation_notification(self, escalation: Dict[str, Any]) -> None:
        """Send escalation notification"""
        if not self.notification:
            return
        
        try:
            self.notification.send(
                notification_type='sla_escalation',
                title=f"SLA超时升级 - 工单 {escalation['workorder_id']}",
                content=f"SLA类型: {escalation['sla_type']}, "
                        f"升级级别: L{escalation['escalation_level']}, "
                        f"超时时长: {escalation['breach_duration_minutes']}分钟",
                recipients=escalation['notified_roles']
            )
        except Exception as e:
            logger.error(f"Failed to send escalation notification: {e}")
    
    def get_sla_summary(self, workorder_ids: List[int] = None) -> Dict[str, Any]:
        """
        Get SLA summary for work orders
        
        Args:
            workorder_ids: List of work order IDs (None for all)
            
        Returns:
            SLA summary statistics
        """
        summary = {
            'total_tracked': 0,
            'response_breached': 0,
            'resolve_breached': 0,
            'at_risk': 0,  # Less than 15 minutes remaining
            'healthy': 0,
            'breached_workorders': []
        }
        
        if not self.redis:
            return summary
        
        try:
            if workorder_ids:
                for wid in workorder_ids:
                    for sla_type in ['response', 'resolve']:
                        status = self.check_sla_status(wid, sla_type)
                        summary['total_tracked'] += 1
                        
                        if status.get('breached'):
                            if sla_type == 'response':
                                summary['response_breached'] += 1
                            else:
                                summary['resolve_breached'] += 1
                            summary['breached_workorders'].append({
                                'workorder_id': wid,
                                'sla_type': sla_type,
                                'breach_duration_minutes': status.get('breach_duration_minutes', 0)
                            })
                        elif status.get('remaining_minutes', 999) < 15:
                            summary['at_risk'] += 1
                        else:
                            summary['healthy'] += 1
            else:
                # Scan all SLA keys
                pattern = "workorder:sla:*"
                keys = self.redis.keys(pattern)
                for key in keys:
                    data = self.redis.get(key)
                    if data:
                        status = json.loads(data)
                        summary['total_tracked'] += 1
                        
                        if status.get('breached'):
                            if status['sla_type'] == 'response':
                                summary['response_breached'] += 1
                            else:
                                summary['resolve_breached'] += 1
                        elif status.get('remaining_minutes', 999) < 15:
                            summary['at_risk'] += 1
                        else:
                            summary['healthy'] += 1
        except Exception as e:
            logger.error(f"Failed to get SLA summary: {e}")
        
        return summary
