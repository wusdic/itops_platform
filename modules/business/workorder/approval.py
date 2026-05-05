"""
审批处理模块
提供多级审批、会签/或签、审批意见、审批代理、审批超时处理等功能
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from modules.foundation.db_models.base import Base


class ApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = 'pending'           # 待审批
    APPROVED = 'approved'         # 已通过
    REJECTED = 'rejected'         # 已拒绝
    CANCELLED = 'cancelled'       # 已取消
    TIMEOUT = 'timeout'           # 已超时
    DELEGATED = 'delegated'       # 已委托


class ApprovalMode(str, Enum):
    """审批模式"""
    ONE = 'one'                  # 或签(任一审批人通过即可)
    ALL = 'all'                  # 会签(所有审批人必须全部通过)


class ApprovalRecord(Base):
    """审批记录模型"""
    __tablename__ = 'approval_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联工单
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), index=True, comment='工单ID')
    
    # 审批流程
    flow_instance_id = Column(Integer, ForeignKey('flow_instances.id'), comment='流程实例ID')
    approval_node_id = Column(String(64), comment='审批节点ID')
    
    # 审批配置
    approver = Column(String(64), comment='审批人')
    approver_email = Column(String(128), comment='审批人邮箱')
    approver_role = Column(String(64), comment='审批人角色')
    
    # 审批模式
    mode = Column(String(16), default=ApprovalMode.ONE.value, comment='审批模式')
    
    # 状态
    status = Column(String(32), default=ApprovalStatus.PENDING.value, comment='审批状态')
    
    # 结果
    action = Column(String(16), comment='操作: approve, reject')
    comment = Column(Text, comment='审批意见')
    
    # 时间
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    expires_at = Column(DateTime, comment='过期时间')
    completed_at = Column(DateTime, comment='完成时间')
    
    # 委托
    delegated_from = Column(String(64), comment='委托人')
    delegated_to = Column(String(64), comment='被委托人')
    
    # 索引
    __table_args__ = (
        Index('idx_approval_workorder', 'work_order_id'),
        Index('idx_approval_approver', 'approver'),
        Index('idx_approval_status', 'status'),
    )
    
    def __repr__(self):
        return f"<ApprovalRecord(id={self.id}, approver='{self.approver}', status='{self.status}')>"


class ApprovalDelegation(Base):
    """审批代理配置模型"""
    __tablename__ = 'approval_delegations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 委托人
    delegator = Column(String(64), nullable=False, index=True, comment='委托人')
    delegator_email = Column(String(128), comment='委托人邮箱')
    
    # 被委托人
    delegate = Column(String(64), nullable=False, comment='被委托人')
    delegate_email = Column(String(128), comment='被委托人邮箱')
    
    # 代理配置
    start_time = Column(DateTime, comment='代理开始时间')
    end_time = Column(DateTime, comment='代理结束时间')
    reason = Column(Text, comment='代理原因')
    
    # 生效范围
    scope = Column(Text, comment='代理范围JSON: 包含哪些角色/部门等')
    
    # 状态
    is_active = Column(Boolean, default=True, comment='是否生效')
    
    # 时间
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def __repr__(self):
        return f"<ApprovalDelegation(id={self.id}, delegator='{self.delegator}', delegate='{self.delegate}')>"


class ApprovalHandler:
    """
    审批处理器
    
    管理多级审批、会签/或签、审批意见、审批代理、审批超时等功能
    """
    
    # 超时提醒配置(小时)
    TIMEOUT_WARNING_HOURS = [24, 4, 1]
    
    def __init__(self, db_session):
        """
        初始化审批处理器
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
    
    def create_approval(
        self,
        work_order_id: int,
        approvers: List[Dict[str, Any]],
        mode: ApprovalMode = ApprovalMode.ONE,
        flow_instance_id: Optional[int] = None,
        approval_node_id: Optional[str] = None,
        timeout_minutes: Optional[int] = None,
        reason: Optional[str] = None
    ) -> List[ApprovalRecord]:
        """
        创建审批任务
        
        Args:
            work_order_id: 工单ID
            approvers: 审批人列表 [{'approver': str, 'email': str, 'role': str}]
            mode: 审批模式
            flow_instance_id: 流程实例ID
            approval_node_id: 审批节点ID
            timeout_minutes: 超时时间(分钟)
            reason: 审批原因
            
        Returns:
            审批记录列表
        """
        now = datetime.now()
        expires_at = now + timedelta(minutes=timeout_minutes) if timeout_minutes else None
        
        records = []
        for approver_info in approvers:
            record = ApprovalRecord(
                work_order_id=work_order_id,
                flow_instance_id=flow_instance_id,
                approval_node_id=approval_node_id,
                approver=approver_info['approver'],
                approver_email=approver_info.get('email'),
                approver_role=approver_info.get('role'),
                mode=mode.value,
                status=ApprovalStatus.PENDING.value,
                created_at=now,
                expires_at=expires_at
            )
            self.db.add(record)
            records.append(record)
        
        self.db.flush()
        self.db.commit()
        return records
    
    def approve(
        self,
        approval_id: int,
        approver: str,
        comment: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, str, Optional[ApprovalRecord]]:
        """
        审批通过
        
        Args:
            approval_id: 审批记录ID
            approver: 审批人
            comment: 审批意见
            
        Returns:
            (是否成功, 消息, 审批记录对象)
        """
        record = self.get_by_id(approval_id)
        if not record:
            return False, '审批记录不存在', None
        
        if record.status != ApprovalStatus.PENDING.value:
            return False, f'审批状态为{record.status},不能操作', None
        
        if record.approver != approver:
            # 检查是否是被委托人
            delegation = self._get_active_delegation(approver, record.approver_role)
            if not delegation or delegation.delegate != approver:
                return False, '您没有审批权限', None
        
        record.action = 'approve'
        record.comment = comment
        record.status = ApprovalStatus.APPROVED.value
        record.completed_at = datetime.now()
        
        self.db.flush()
        self.db.commit()
        return True, '审批已通过', record
    
    def reject(
        self,
        approval_id: int,
        approver: str,
        comment: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, str, Optional[ApprovalRecord]]:
        """
        审批拒绝
        
        Args:
            approval_id: 审批记录ID
            approver: 审批人
            comment: 审批意见
            
        Returns:
            (是否成功, 消息, 审批记录对象)
        """
        record = self.get_by_id(approval_id)
        if not record:
            return False, '审批记录不存在', None
        
        if record.status != ApprovalStatus.PENDING.value:
            return False, f'审批状态为{record.status},不能操作', None
        
        if record.approver != approver:
            # 检查是否是被委托人
            delegation = self._get_active_delegation(approver, record.approver_role)
            if not delegation or delegation.delegate != approver:
                return False, '您没有审批权限', None
        
        record.action = 'reject'
        record.comment = comment
        record.status = ApprovalStatus.REJECTED.value
        record.completed_at = datetime.now()
        
        self.db.flush()
        self.db.commit()
        return True, '审批已拒绝', record
    
    def get_by_id(self, approval_id: int) -> Optional[ApprovalRecord]:
        """获取审批记录"""
        return self.db.query(ApprovalRecord).filter(
            ApprovalRecord.id == approval_id
        ).first()
    
    def get_pending_approvals(
        self,
        approver: str,
        include_delegated: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ApprovalRecord], int]:
        """
        获取待我审批的列表
        
        Args:
            approver: 审批人
            include_delegated: 是否包含被委托的审批
            page: 页码
            page_size: 每页数量
            
        Returns:
            (审批记录列表, 总数)
        """
        query = self.db.query(ApprovalRecord).filter(
            ApprovalRecord.status == ApprovalStatus.PENDING.value
        )
        
        # 直接分配给我的
        direct_query = query.filter(ApprovalRecord.approver == approver)
        
        if include_delegated:
            # 查询被委托的
            delegations = self._get_delegations_to(approver)
            delegated_froms = [d.delegator for d in delegations]
            if delegated_froms:
                delegated_query = query.filter(
                    ApprovalRecord.approver.in_(delegated_froms)
                )
                query = direct_query.union(delegated_query)
            else:
                query = direct_query
        else:
            query = direct_query
        
        total = query.count()
        records = query.order_by(ApprovalRecord.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return records, total
    
    def get_work_order_approvals(
        self,
        work_order_id: int
    ) -> List[ApprovalRecord]:
        """
        获取工单的所有审批记录
        
        Args:
            work_order_id: 工单ID
            
        Returns:
            审批记录列表
        """
        return self.db.query(ApprovalRecord).filter(
            ApprovalRecord.work_order_id == work_order_id
        ).order_by(ApprovalRecord.created_at.asc()).all()
    
    def check_approval_complete(self, work_order_id: int) -> Dict[str, Any]:
        """
        检查工单的审批是否完成
        
        Args:
            work_order_id: 工单ID
            
        Returns:
            审批结果信息
        """
        records = self.get_work_order_approvals(work_order_id)
        if not records:
            return {'complete': False, 'result': None}
        
        # 检查是否所有审批都完成
        all_complete = all(
            r.status in [ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value]
            for r in records
        )
        
        if not all_complete:
            return {'complete': False, 'result': None}
        
        # 获取审批模式
        mode = records[0].mode if records else ApprovalMode.ONE.value
        
        if mode == ApprovalMode.ONE.value:
            # 或签模式: 任一通过即通过
            result = 'approved' if any(
                r.status == ApprovalStatus.APPROVED.value for r in records
            ) else 'rejected'
        else:
            # 会签模式: 全部通过才通过
            result = 'approved' if all(
                r.status == ApprovalStatus.APPROVED.value for r in records
            ) else 'rejected'
        
        return {
            'complete': True,
            'result': result,
            'records': records
        }
    
    def create_delegation(
        self,
        delegator: str,
        delegate: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        scope: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        delegator_email: Optional[str] = None,
        delegate_email: Optional[str] = None
    ) -> ApprovalDelegation:
        """
        创建审批代理
        
        Args:
            delegator: 委托人
            delegate: 被委托人
            start_time: 代理开始时间
            end_time: 代理结束时间
            scope: 代理范围
            reason: 代理原因
            delegator_email: 委托人邮箱
            delegate_email: 被委托人邮箱
            
        Returns:
            代理配置对象
        """
        # 检查是否已有相同配置
        existing = self.db.query(ApprovalDelegation).filter(
            ApprovalDelegation.delegator == delegator,
            ApprovalDelegation.delegate == delegate,
            ApprovalDelegation.is_active == True
        ).first()
        
        if existing:
            # 更新现有配置
            existing.end_time = end_time
            existing.start_time = start_time or existing.start_time
            existing.scope = json.dumps(scope) if scope else existing.scope
            existing.reason = reason
            existing.updated_at = datetime.now()
            self.db.flush()
            self.db.commit()
            return existing
        
        delegation = ApprovalDelegation(
            delegator=delegator,
            delegator_email=delegator_email,
            delegate=delegate,
            delegate_email=delegate_email,
            start_time=start_time or datetime.now(),
            end_time=end_time,
            scope=json.dumps(scope) if scope else None,
            reason=reason,
            is_active=True
        )
        
        self.db.add(delegation)
        self.db.commit()
        return delegation
    
    def cancel_delegation(
        self,
        delegation_id: int,
        delegator: str
    ) -> Tuple[bool, str]:
        """
        取消审批代理
        
        Args:
            delegation_id: 代理ID
            delegator: 委托人
            
        Returns:
            (是否成功, 消息)
        """
        delegation = self.db.query(ApprovalDelegation).filter(
            ApprovalDelegation.id == delegation_id
        ).first()
        
        if not delegation:
            return False, '代理配置不存在'
        
        if delegation.delegator != delegator:
            return False, '您没有权限取消此代理'
        
        delegation.is_active = False
        delegation.updated_at = datetime.now()
        
        self.db.commit()
        return True, '代理已取消'
    
    def _get_active_delegation(self, delegate: str, role: Optional[str]) -> Optional[ApprovalDelegation]:
        """获取有效的委托配置"""
        now = datetime.now()
        query = self.db.query(ApprovalDelegation).filter(
            ApprovalDelegation.delegate == delegate,
            ApprovalDelegation.is_active == True,
            ApprovalDelegation.start_time <= now,
            (ApprovalDelegation.end_time.is_(None) | (ApprovalDelegation.end_time >= now))
        )
        return query.first()
    
    def _get_delegations_to(self, delegate: str) -> List[ApprovalDelegation]:
        """获取委托给某人的所有配置"""
        now = datetime.now()
        return self.db.query(ApprovalDelegation).filter(
            ApprovalDelegation.delegate == delegate,
            ApprovalDelegation.is_active == True,
            ApprovalDelegation.start_time <= now,
            (ApprovalDelegation.end_time.is_(None) | (ApprovalDelegation.end_time >= now))
        ).all()
    
    def get_timeout_approvals(self) -> List[ApprovalRecord]:
        """
        获取超时的审批记录
        
        Returns:
            超时审批列表
        """
        now = datetime.now()
        return self.db.query(ApprovalRecord).filter(
            ApprovalRecord.status == ApprovalStatus.PENDING.value,
            ApprovalRecord.expires_at < now
        ).all()
    
    def get_warning_approvals(self) -> List[Dict[str, Any]]:
        """
        获取即将超时的审批记录
        
        Returns:
            预警信息列表
        """
        now = datetime.now()
        warnings = []
        
        for hours in self.TIMEOUT_WARNING_HOURS:
            warning_time = now + timedelta(hours=hours)
            threshold = warning_time - timedelta(minutes=30)  # 30分钟内的窗口
            
            records = self.db.query(ApprovalRecord).filter(
                ApprovalRecord.status == ApprovalStatus.PENDING.value,
                ApprovalRecord.expires_at >= threshold,
                ApprovalRecord.expires_at <= warning_time
            ).all()
            
            for record in records:
                if record.expires_at:
                    remaining = (record.expires_at - now).total_seconds() / 3600
                    warnings.append({
                        'approval_id': record.id,
                        'approver': record.approver,
                        'expires_at': record.expires_at,
                        'remaining_hours': round(remaining, 1)
                    })
        
        return warnings
    
    def cancel_approval(
        self,
        approval_id: int,
        operator: str
    ) -> Tuple[bool, str]:
        """
        取消审批任务
        
        Args:
            approval_id: 审批记录ID
            operator: 操作人
            
        Returns:
            (是否成功, 消息)
        """
        record = self.get_by_id(approval_id)
        if not record:
            return False, '审批记录不存在'
        
        if record.status != ApprovalStatus.PENDING.value:
            return False, f'审批状态为{record.status},不能取消'
        
        record.status = ApprovalStatus.CANCELLED.value
        record.completed_at = datetime.now()
        
        self.db.commit()
        return True, '审批已取消'
    
    def delegate_approval(
        self,
        approval_id: int,
        from_approver: str,
        to_approver: str,
        to_approver_email: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Tuple[bool, str, Optional[ApprovalRecord]]:
        """
        转交审批
        
        Args:
            approval_id: 审批记录ID
            from_approver: 原审批人
            to_approver: 新审批人
            to_approver_email: 新审批人邮箱
            comment: 转交原因
            
        Returns:
            (是否成功, 消息, 审批记录对象)
        """
        record = self.get_by_id(approval_id)
        if not record:
            return False, '审批记录不存在', None
        
        if record.status != ApprovalStatus.PENDING.value:
            return False, f'审批状态为{record.status},不能转交', None
        
        if record.approver != from_approver:
            return False, '您没有权限转交此审批', None
        
        # 更新原记录状态
        record.status = ApprovalStatus.DELEGATED.value
        record.delegated_from = from_approver
        record.delegated_to = to_approver
        record.comment = f'转交给{to_approver}: {comment}' if comment else f'转交给{to_approver}'
        record.completed_at = datetime.now()
        
        # 创建新记录
        new_record = ApprovalRecord(
            work_order_id=record.work_order_id,
            flow_instance_id=record.flow_instance_id,
            approval_node_id=record.approval_node_id,
            approver=to_approver,
            approver_email=to_approver_email,
            approver_role=record.approver_role,
            mode=record.mode,
            status=ApprovalStatus.PENDING.value,
            expires_at=record.expires_at,
            delegated_from=from_approver
        )
        self.db.add(new_record)
        
        self.db.flush()
        self.db.commit()
        return True, f'审批已转交给{to_approver}', new_record
    
    def get_approval_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        approver: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取审批统计信息
        
        Args:
            start_time: 统计开始时间
            end_time: 统计结束时间
            approver: 审批人
            
        Returns:
            统计信息
        """
        query = self.db.query(ApprovalRecord)
        
        if start_time:
            query = query.filter(ApprovalRecord.created_at >= start_time)
        if end_time:
            query = query.filter(ApprovalRecord.created_at <= end_time)
        if approver:
            query = query.filter(ApprovalRecord.approver == approver)
        
        total = query.count()
        approved = query.filter(ApprovalRecord.status == ApprovalStatus.APPROVED.value).count()
        rejected = query.filter(ApprovalRecord.status == ApprovalStatus.REJECTED.value).count()
        pending = query.filter(ApprovalRecord.status == ApprovalStatus.PENDING.value).count()
        timeout = query.filter(ApprovalRecord.status == ApprovalStatus.TIMEOUT.value).count()
        
        return {
            'total': total,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'timeout': timeout,
            'approval_rate': round(approved / total * 100, 2) if total > 0 else 0
        }
