"""
变更管理模块
提供变更申请、变更评审、变更实施、变更验证、变更回滚等功能
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from modules.foundation.db_models.base import Base


class ChangeStatus(str, Enum):
    """变更状态"""
    DRAFT = 'draft'                     # 草稿
    PENDING_REVIEW = 'pending_review'   # 待评审
    IN_REVIEW = 'in_review'            # 评审中
    APPROVED = 'approved'               # 已批准
    REJECTED = 'rejected'               # 已拒绝
    SCHEDULED = 'scheduled'             # 已排期
    IN_PROGRESS = 'in_progress'         # 实施中
    VERIFIED = 'verified'              # 已验证
    COMPLETED = 'completed'            # 已完成
    FAILED = 'failed'                  # 实施失败
    ROLLED_BACK = 'rolled_back'        # 已回滚
    CANCELLED = 'cancelled'            # 已取消


class ChangeRisk(str, Enum):
    """变更风险等级"""
    CRITICAL = 'critical'               # 重大
    HIGH = 'high'                      # 高
    MEDIUM = 'medium'                  # 中
    LOW = 'low'                        # 低


class ChangeRecord(Base):
    """变更记录模型"""
    __tablename__ = 'change_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    change_no = Column(String(64), unique=True, nullable=False, index=True, comment='变更编号')
    
    # 关联工单
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), index=True, comment='工单ID')
    
    # 变更基本信息
    title = Column(String(256), nullable=False, comment='变更标题')
    change_type = Column(String(64), comment='变更类型: emergency, normal, standard')
    category = Column(String(64), comment='变更类别')
    
    # 风险评估
    risk_level = Column(String(32), comment='风险等级')
    impact = Column(Text, comment='影响范围')
    rollback_plan = Column(Text, comment='回滚方案')
    test_plan = Column(Text, comment='测试计划')
    
    # 时间安排
    scheduled_start = Column(DateTime, comment='计划开始时间')
    scheduled_end = Column(DateTime, comment='计划结束时间')
    actual_start = Column(DateTime, comment='实际开始时间')
    actual_end = Column(DateTime, comment='实际结束时间')
    maintenance_window = Column(String(128), comment='维护窗口')
    
    # 实施信息
    implementor = Column(String(64), comment='实施人')
    implementor_email = Column(String(128), comment='实施人邮箱')
    
    # 状态
    status = Column(String(32), default=ChangeStatus.DRAFT.value, comment='变更状态')
    
    # 评审信息
    review_board = Column(String(64), comment='评审委员会: CAB, TCM, self')
    reviewers = Column(Text, comment='评审人列表JSON')
    review_comments = Column(Text, comment='评审意见JSON')
    
    # 实施记录
    implementation_steps = Column(Text, comment='实施步骤JSON')
    implementation_log = Column(Text, comment='实施日志JSON')
    
    # 验证信息
    verification_result = Column(Text, comment='验证结果')
    verification_by = Column(String(64), comment='验证人')
    verification_at = Column(DateTime, comment='验证时间')
    
    # 回滚信息
    rollback_reason = Column(Text, comment='回滚原因')
    rollback_at = Column(DateTime, comment='回滚时间')
    rollback_by = Column(String(64), comment='回滚人')
    
    # 审批信息
    approval_status = Column(String(32), comment='审批状态')
    approvers = Column(Text, comment='审批人JSON')
    approval_history = Column(Text, comment='审批历史JSON')
    
    # 关联资源
    related_devices = Column(Text, comment='关联设备JSON')
    related_services = Column(Text, comment='关联服务JSON')
    related_configs = Column(Text, comment='关联配置JSON')
    
    # 附件
    attachments = Column(Text, comment='附件列表JSON')
    
    # 元数据
    applicant = Column(String(64), nullable=False, comment='申请人')
    applicant_email = Column(String(128), comment='申请人邮箱')
    applicant_dept = Column(String(128), comment='申请部门')
    
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('idx_change_workorder', 'work_order_id'),
        Index('idx_change_status', 'status'),
        Index('idx_change_applicant', 'applicant'),
    )
    
    def __repr__(self):
        return f"<ChangeRecord(id={self.id}, change_no='{self.change_no}')>"


class ChangeManager:
    """
    变更管理类
    
    提供变更申请、变更评审、变更实施、变更验证、变更回滚等功能
    """
    
    def __init__(self, db_session):
        """
        初始化变更管理
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
    
    def generate_change_no(self, change_type: str = 'normal') -> str:
        """
        生成变更编号
        
        格式: CHG{类型}{日期}{序号}
        例如: CHG-N20260428001
        
        Args:
            change_type: 变更类型
            
        Returns:
            变更编号
        """
        type_prefix = {
            'emergency': 'EMG',
            'normal': 'N',
            'standard': 'STD'
        }.get(change_type, 'CHG')
        
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 查询当天该类型变更数量
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = self.db.query(ChangeRecord).filter(
            ChangeRecord.change_type == change_type,
            ChangeRecord.created_at >= today_start
        ).count()
        
        sequence = str(count + 1).zfill(4)
        return f"CHG-{type_prefix}{date_str}{sequence}"
    
    def create(
        self,
        work_order_id: int,
        title: str,
        applicant: str,
        change_type: str = 'normal',
        category: Optional[str] = None,
        risk_level: Optional[str] = None,
        impact: Optional[str] = None,
        rollback_plan: Optional[str] = None,
        test_plan: Optional[str] = None,
        scheduled_start: Optional[datetime] = None,
        scheduled_end: Optional[datetime] = None,
        maintenance_window: Optional[str] = None,
        related_devices: Optional[List[Dict]] = None,
        related_services: Optional[List[str]] = None,
        related_configs: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None,
        applicant_email: Optional[str] = None,
        applicant_dept: Optional[str] = None,
        **kwargs
    ) -> ChangeRecord:
        """
        创建变更申请
        
        Args:
            work_order_id: 工单ID
            title: 变更标题
            applicant: 申请人
            change_type: 变更类型
            category: 变更类别
            risk_level: 风险等级
            impact: 影响范围
            rollback_plan: 回滚方案
            test_plan: 测试计划
            scheduled_start: 计划开始时间
            scheduled_end: 计划结束时间
            maintenance_window: 维护窗口
            related_devices: 关联设备
            related_services: 关联服务
            related_configs: 关联配置
            attachments: 附件
            applicant_email: 申请人邮箱
            applicant_dept: 申请部门
            
        Returns:
            变更记录对象
        """
        change_no = self.generate_change_no(change_type)
        
        change = ChangeRecord(
            change_no=change_no,
            work_order_id=work_order_id,
            title=title,
            change_type=change_type,
            category=category,
            risk_level=risk_level or ChangeRisk.MEDIUM.value,
            impact=impact,
            rollback_plan=rollback_plan,
            test_plan=test_plan,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            maintenance_window=maintenance_window,
            related_devices=json.dumps(related_devices) if related_devices else None,
            related_services=json.dumps(related_services) if related_services else None,
            related_configs=json.dumps(related_configs) if related_configs else None,
            attachments=json.dumps(attachments) if attachments else None,
            applicant=applicant,
            applicant_email=applicant_email,
            applicant_dept=applicant_dept,
            status=ChangeStatus.DRAFT.value
        )
        
        self.db.add(change)
        self.db.flush()
        self.db.commit()
        return change
    
    def get_by_id(self, change_id: int) -> Optional[ChangeRecord]:
        """获取变更记录"""
        return self.db.query(ChangeRecord).filter(
            ChangeRecord.id == change_id
        ).first()
    
    def get_by_change_no(self, change_no: str) -> Optional[ChangeRecord]:
        """根据变更编号获取变更记录"""
        return self.db.query(ChangeRecord).filter(
            ChangeRecord.change_no == change_no
        ).first()
    
    def list(
        self,
        status: Optional[ChangeStatus] = None,
        change_type: Optional[str] = None,
        applicant: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ChangeRecord], int]:
        """
        查询变更记录列表
        
        Args:
            status: 变更状态
            change_type: 变更类型
            applicant: 申请人
            start_time: 创建时间起始
            end_time: 创建时间结束
            page: 页码
            page_size: 每页数量
            
        Returns:
            (变更记录列表, 总数)
        """
        query = self.db.query(ChangeRecord)
        
        if status:
            query = query.filter(ChangeRecord.status == status.value)
        if change_type:
            query = query.filter(ChangeRecord.change_type == change_type)
        if applicant:
            query = query.filter(ChangeRecord.applicant == applicant)
        if start_time:
            query = query.filter(ChangeRecord.created_at >= start_time)
        if end_time:
            query = query.filter(ChangeRecord.created_at <= end_time)
        
        total = query.count()
        
        records = query.order_by(ChangeRecord.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return records, total
    
    def update(
        self,
        change_id: int,
        **kwargs
    ) -> Optional[ChangeRecord]:
        """
        更新变更记录
        
        Args:
            change_id: 变更ID
            **kwargs: 更新字段
            
        Returns:
            更新后的变更记录
        """
        change = self.get_by_id(change_id)
        if not change:
            return None
        
        allowed_fields = [
            'title', 'change_type', 'category', 'risk_level', 'impact',
            'rollback_plan', 'test_plan', 'scheduled_start', 'scheduled_end',
            'maintenance_window', 'related_devices', 'related_services',
            'related_configs', 'attachments'
        ]
        
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        for key, value in update_data.items():
            if key in ['related_devices', 'related_services', 'related_configs', 'attachments']:
                setattr(change, key, json.dumps(value) if isinstance(value, list) else value)
            else:
                setattr(change, key, value)
        
        change.updated_at = datetime.now()
        
        self.db.commit()
        return change
    
    def submit_for_review(
        self,
        change_id: int,
        reviewers: List[Dict[str, Any]],
        review_board: str = 'CAB'
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        提交变更评审
        
        Args:
            change_id: 变更ID
            reviewers: 评审人列表 [{'name': str, 'email': str, 'role': str}]
            review_board: 评审委员会类型
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status not in [ChangeStatus.DRAFT.value, ChangeStatus.REJECTED.value]:
            return False, f'变更状态为{change.status},不能提交评审', None
        
        change.status = ChangeStatus.PENDING_REVIEW.value
        change.review_board = review_board
        change.reviewers = json.dumps(reviewers)
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更已提交评审', change
    
    def add_review_comment(
        self,
        change_id: int,
        reviewer: str,
        comment: str,
        decision: Optional[str] = None  # approve, reject
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        添加评审意见
        
        Args:
            change_id: 变更ID
            reviewer: 评审人
            comment: 评审意见
            decision: 评审决定
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status not in [ChangeStatus.PENDING_REVIEW.value, ChangeStatus.IN_REVIEW.value]:
            return False, f'变更状态为{change.status},不能添加评审意见', None
        
        # 解析现有评审意见
        comments = []
        if change.review_comments:
            try:
                comments = json.loads(change.review_comments)
            except json.JSONDecodeError:
                comments = []
        
        # 添加新评审意见
        comments.append({
            'reviewer': reviewer,
            'comment': comment,
            'decision': decision,
            'timestamp': datetime.now().isoformat()
        })
        
        change.review_comments = json.dumps(comments)
        change.status = ChangeStatus.IN_REVIEW.value
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '评审意见已添加', change
    
    def approve_change(
        self,
        change_id: int,
        approver: str,
        approvers: List[Dict[str, Any]]
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        批准变更
        
        Args:
            change_id: 变更ID
            approver: 审批人
            approvers: 审批人列表
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status not in [ChangeStatus.IN_REVIEW.value, ChangeStatus.PENDING_REVIEW.value]:
            return False, f'变更状态为{change.status},不能审批', None
        
        change.status = ChangeStatus.APPROVED.value
        change.approval_status = 'approved'
        change.approvers = json.dumps(approvers)
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更已批准', change
    
    def reject_change(
        self,
        change_id: int,
        approver: str,
        reason: str
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        拒绝变更
        
        Args:
            change_id: 变更ID
            approver: 审批人
            reason: 拒绝原因
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status not in [ChangeStatus.IN_REVIEW.value, ChangeStatus.PENDING_REVIEW.value]:
            return False, f'变更状态为{change.status},不能拒绝', None
        
        # 添加拒绝原因到评审意见
        comments = []
        if change.review_comments:
            try:
                comments = json.loads(change.review_comments)
            except json.JSONDecodeError:
                comments = []
        
        comments.append({
            'reviewer': approver,
            'comment': reason,
            'decision': 'reject',
            'timestamp': datetime.now().isoformat()
        })
        
        change.status = ChangeStatus.REJECTED.value
        change.approval_status = 'rejected'
        change.review_comments = json.dumps(comments)
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更已拒绝', change
    
    def schedule(
        self,
        change_id: int,
        scheduled_start: datetime,
        scheduled_end: datetime
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        排期变更
        
        Args:
            change_id: 变更ID
            scheduled_start: 计划开始时间
            scheduled_end: 计划结束时间
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status != ChangeStatus.APPROVED.value:
            return False, f'变更状态为{change.status},不能排期', None
        
        change.scheduled_start = scheduled_start
        change.scheduled_end = scheduled_end
        change.status = ChangeStatus.SCHEDULED.value
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更已排期', change
    
    def start_implementation(
        self,
        change_id: int,
        implementor: str,
        implementor_email: Optional[str] = None
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        开始实施变更
        
        Args:
            change_id: 变更ID
            implementor: 实施人
            implementor_email: 实施人邮箱
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status != ChangeStatus.SCHEDULED.value:
            return False, f'变更状态为{change.status},不能开始实施', None
        
        change.status = ChangeStatus.IN_PROGRESS.value
        change.actual_start = datetime.now()
        change.implementor = implementor
        change.implementor_email = implementor_email
        change.implementation_steps = json.dumps([])
        change.implementation_log = json.dumps([])
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更已开始实施', change
    
    def add_implementation_step(
        self,
        change_id: int,
        step: Dict[str, Any],
        operator: str
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        添加实施步骤
        
        Args:
            change_id: 变更ID
            step: 步骤信息 {'order': int, 'name': str, 'command': str, 'result': str}
            operator: 操作人
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status != ChangeStatus.IN_PROGRESS.value:
            return False, f'变更状态为{change.status},不能添加实施步骤', None
        
        # 解析现有步骤
        steps = []
        if change.implementation_steps:
            try:
                steps = json.loads(change.implementation_steps)
            except json.JSONDecodeError:
                steps = []
        
        step['added_by'] = operator
        step['added_at'] = datetime.now().isoformat()
        steps.append(step)
        
        change.implementation_steps = json.dumps(steps)
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '实施步骤已添加', change
    
    def log_implementation(
        self,
        change_id: int,
        log_entry: str,
        operator: str
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        记录实施日志
        
        Args:
            change_id: 变更ID
            log_entry: 日志内容
            operator: 操作人
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status != ChangeStatus.IN_PROGRESS.value:
            return False, f'变更状态为{change.status},不能记录实施日志', None
        
        # 解析现有日志
        logs = []
        if change.implementation_log:
            try:
                logs = json.loads(change.implementation_log)
            except json.JSONDecodeError:
                logs = []
        
        logs.append({
            'timestamp': datetime.now().isoformat(),
            'operator': operator,
            'entry': log_entry
        })
        
        change.implementation_log = json.dumps(logs)
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '实施日志已记录', change
    
    def complete_implementation(
        self,
        change_id: int
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        完成变更实施
        
        Args:
            change_id: 变更ID
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status != ChangeStatus.IN_PROGRESS.value:
            return False, f'变更状态为{change.status},不能完成实施', None
        
        change.status = ChangeStatus.COMPLETED.value
        change.actual_end = datetime.now()
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更实施已完成', change
    
    def verify(
        self,
        change_id: int,
        verification_result: str,
        verifier: str
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        验证变更
        
        Args:
            change_id: 变更ID
            verification_result: 验证结果
            verifier: 验证人
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status != ChangeStatus.COMPLETED.value:
            return False, f'变更状态为{change.status},不能验证', None
        
        change.status = ChangeStatus.VERIFIED.value
        change.verification_result = verification_result
        change.verification_by = verifier
        change.verification_at = datetime.now()
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更已验证', change
    
    def rollback(
        self,
        change_id: int,
        reason: str,
        operator: str
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        回滚变更
        
        Args:
            change_id: 变更ID
            reason: 回滚原因
            operator: 操作人
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status not in [
            ChangeStatus.IN_PROGRESS.value,
            ChangeStatus.COMPLETED.value,
            ChangeStatus.VERIFIED.value
        ]:
            return False, f'变更状态为{change.status},不能回滚', None
        
        if not change.rollback_plan:
            return False, '该变更没有回滚方案,无法回滚', None
        
        change.status = ChangeStatus.ROLLED_BACK.value
        change.rollback_reason = reason
        change.rollback_by = operator
        change.rollback_at = datetime.now()
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更已开始回滚', change
    
    def cancel(
        self,
        change_id: int,
        operator: str,
        reason: Optional[str] = None
    ) -> Tuple[bool, str, Optional[ChangeRecord]]:
        """
        取消变更
        
        Args:
            change_id: 变更ID
            operator: 操作人
            reason: 取消原因
            
        Returns:
            (是否成功, 消息, 变更记录对象)
        """
        change = self.get_by_id(change_id)
        if not change:
            return False, '变更记录不存在', None
        
        if change.status in [ChangeStatus.COMPLETED.value, ChangeStatus.VERIFIED.value]:
            return False, f'变更状态为{change.status},不能取消', None
        
        change.status = ChangeStatus.CANCELLED.value
        if reason:
            change.rollback_reason = reason
        change.updated_at = datetime.now()
        
        self.db.commit()
        return True, '变更已取消', change
    
    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取变更统计信息
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            统计数据
        """
        query = self.db.query(ChangeRecord)
        
        if start_time:
            query = query.filter(ChangeRecord.created_at >= start_time)
        if end_time:
            query = query.filter(ChangeRecord.created_at <= end_time)
        
        total = query.count()
        
        status_counts = {}
        for status in ChangeStatus:
            count = query.filter(ChangeRecord.status == status.value).count()
            status_counts[status.value] = count
        
        type_counts = {}
        for change_type in ['emergency', 'normal', 'standard']:
            count = query.filter(ChangeRecord.change_type == change_type).count()
            type_counts[change_type] = count
        
        return {
            'total': total,
            'status_distribution': status_counts,
            'type_distribution': type_counts
        }
