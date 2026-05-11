"""
文档多级审核模块
BM-05 知识库
提供文档多级审核流程管理
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


class ReviewStatus(str, Enum):
    """审核状态枚举"""
    PENDING = 'pending'           # 待审核
    IN_REVIEW = 'in_review'      # 审核中
    APPROVED = 'approved'        # 已批准
    REJECTED = 'rejected'        # 已拒绝
    REVISION_REQUESTED = 'revision_requested'  # 需修订
    WITHDRAWN = 'withdrawn'      # 已撤回


class ReviewLevel(str, Enum):
    """审核级别枚举"""
    LEVEL_1 = 'level_1'  # 一级审核（初审）
    LEVEL_2 = 'level_2'  # 二级审核（复审）
    LEVEL_3 = 'level_3'  # 三级审核（终审）


class ReviewAction(str, Enum):
    """审核动作枚举"""
    SUBMIT = 'submit'              # 提交审核
    APPROVE = 'approve'           # 批准
    REJECT = 'reject'             # 拒绝
    REQUEST_REVISION = 'request_revision'  # 要求修订
    WITHDRAW = 'withdraw'         # 撤回


@dataclass
class ReviewLevelConfig:
    """审核级别配置"""
    level: ReviewLevel
    name: str
    description: str = ''
    
    # 审核人配置
    reviewer_role: str = ''  # 审核人角色
    specific_reviewers: List[str] = field(default_factory=list)  # 指定审核人
    require_all_approved: bool = True  # 是否需要全部审核人批准
    
    # 条件配置
    auto_assign: bool = True  # 是否自动分配审核人
    allow_skip: bool = False  # 是否允许跳过此级别
    
    # 时间配置
    timeout_hours: int = 48  # 审核超时时间
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level.value if isinstance(self.level, ReviewLevel) else self.level,
            'name': self.name,
            'description': self.description,
            'reviewer_role': self.reviewer_role,
            'specific_reviewers': self.specific_reviewers,
            'require_all_approved': self.require_all_approved,
            'auto_assign': self.auto_assign,
            'allow_skip': self.allow_skip,
            'timeout_hours': self.timeout_hours,
        }


@dataclass
class ReviewFlowConfig:
    """审核流程配置"""
    id: str
    name: str
    description: str = ''
    
    # 审核级别列表（按顺序）
    levels: List[ReviewLevelConfig] = field(default_factory=list)
    
    # 全局配置
    enable_timeout_notification: bool = True
    timeout_notification_interval: int = 24  # 超时提醒间隔(小时)
    allow_withdraw_after_approve: bool = False  # 批准后是否允许撤回
    
    # 条件配置
    applicable_doc_types: List[str] = field(default_factory=list)  # 适用文档类型
    applicable_categories: List[int] = field(default_factory=list)  # 适用分类
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = 'system'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'levels': [l.to_dict() for l in self.levels],
            'enable_timeout_notification': self.enable_timeout_notification,
            'timeout_notification_interval': self.timeout_notification_interval,
            'allow_withdraw_after_approve': self.allow_withdraw_after_approve,
            'applicable_doc_types': self.applicable_doc_types,
            'applicable_categories': self.applicable_categories,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }


@dataclass
class ReviewRecord:
    """审核记录"""
    id: str
    flow_id: str
    document_id: int
    document_type: str
    document_title: str
    
    # 当前级别
    current_level: int = 1
    total_levels: int = 1
    
    # 状态
    status: ReviewStatus = ReviewStatus.PENDING
    
    # 提交信息
    submitted_at: datetime = field(default_factory=datetime.now)
    submitted_by: str = ''
    submit_comment: str = ''
    
    # 审核记录列表
    reviews: List[Dict[str, Any]] = field(default_factory=list)
    
    # 完成信息
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    final_comment: str = ''
    
    # 超时信息
    current_level_deadline: Optional[datetime] = None
    timeout_notified: bool = False
    
    # 历史
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'flow_id': self.flow_id,
            'document_id': self.document_id,
            'document_type': self.document_type,
            'document_title': self.document_title,
            'current_level': self.current_level,
            'total_levels': self.total_levels,
            'status': self.status.value if isinstance(self.status, ReviewStatus) else self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'submitted_by': self.submitted_by,
            'submit_comment': self.submit_comment,
            'reviews': self.reviews,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by': self.completed_by,
            'final_comment': self.final_comment,
            'current_level_deadline': self.current_level_deadline.isoformat() if self.current_level_deadline else None,
            'history': self.history,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DocumentReviewFlow:
    """
    文档多级审核流程管理器
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._flows: Dict[str, ReviewFlowConfig] = {}
        self._active_reviews: Dict[str, ReviewRecord] = {}  # review_id -> record
        self._document_reviews: Dict[int, str] = {}  # document_id -> review_id (仅记录当前活跃审核)
        
        # 回调函数
        self._review_callbacks: Dict[str, List[Callable]] = {
            'submitted': [],
            'approved': [],
            'rejected': [],
            'revision_requested': [],
            'withdrawn': [],
            'timeout': [],
        }
        
        # 初始化默认流程
        self._init_default_flows()
        
        logger.info('DocumentReviewFlow initialized')
    
    def _init_default_flows(self):
        """初始化默认审核流程"""
        # 标准审核流程（三级审核）
        standard_flow = ReviewFlowConfig(
            id='standard',
            name='标准审核流程',
            description='标准三级审核流程：初审 -> 复审 -> 终审',
            levels=[
                ReviewLevelConfig(
                    level=ReviewLevel.LEVEL_1,
                    name='初审',
                    description='文档作者提交后，由组长进行初审',
                    reviewer_role='team_leader',
                    require_all_approved=True,
                    timeout_hours=24,
                ),
                ReviewLevelConfig(
                    level=ReviewLevel.LEVEL_2,
                    name='复审',
                    description='由部门经理进行复审',
                    reviewer_role='department_manager',
                    require_all_approved=True,
                    timeout_hours=48,
                ),
                ReviewLevelConfig(
                    level=ReviewLevel.LEVEL_3,
                    name='终审',
                    description='由技术总监进行最终审批',
                    reviewer_role='tech_director',
                    require_all_approved=True,
                    timeout_hours=72,
                ),
            ],
            applicable_doc_types=['sop', 'policy', 'standard'],
        )
        self.add_flow(standard_flow)
        
        # 简易审核流程（一级审核）
        simple_flow = ReviewFlowConfig(
            id='simple',
            name='简易审核流程',
            description='简易一级审核流程：提交 -> 批准',
            levels=[
                ReviewLevelConfig(
                    level=ReviewLevel.LEVEL_1,
                    name='审核',
                    description='由审核人直接审核',
                    reviewer_role='reviewer',
                    require_all_approved=True,
                    timeout_hours=48,
                ),
            ],
            applicable_doc_types=['notice', 'template'],
        )
        self.add_flow(simple_flow)
        
        # 紧急审核流程（快速一级）
        urgent_flow = ReviewFlowConfig(
            id='urgent',
            name='紧急审核流程',
            description='紧急情况下的快速一级审核',
            levels=[
                ReviewLevelConfig(
                    level=ReviewLevel.LEVEL_1,
                    name='快速审核',
                    description='值班负责人快速审批',
                    reviewer_role='on_duty_leader',
                    require_all_approved=False,
                    allow_skip=True,
                    timeout_hours=4,
                ),
            ],
            applicable_doc_types=['sop', 'policy', 'standard', 'notice'],
        )
        self.add_flow(urgent_flow)
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调函数"""
        if event in self._review_callbacks:
            self._review_callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, record: ReviewRecord):
        """触发回调"""
        for callback in self._review_callbacks.get(event, []):
            try:
                callback(record)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    def add_flow(self, flow: ReviewFlowConfig) -> str:
        """添加审核流程"""
        self._flows[flow.id] = flow
        logger.info(f'Added review flow: {flow.id} - {flow.name}')
        return flow.id
    
    def update_flow(self, flow: ReviewFlowConfig):
        """更新审核流程"""
        flow.updated_at = datetime.now()
        self._flows[flow.id] = flow
    
    def delete_flow(self, flow_id: str) -> bool:
        """删除审核流程"""
        if flow_id in self._flows:
            del self._flows[flow_id]
            return True
        return False
    
    def get_flow(self, flow_id: str) -> Optional[ReviewFlowConfig]:
        """获取审核流程"""
        return self._flows.get(flow_id)
    
    def list_flows(self) -> List[ReviewFlowConfig]:
        """列出所有审核流程"""
        return list(self._flows.values())
    
    def select_flow(self, document_type: str, category_id: Optional[int] = None) -> Optional[ReviewFlowConfig]:
        """根据文档类型和分类选择审核流程"""
        for flow in self._flows.values():
            # 检查文档类型
            if flow.applicable_doc_types and document_type not in flow.applicable_doc_types:
                continue
            # 检查分类
            if flow.applicable_categories and category_id not in flow.applicable_categories:
                continue
            return flow
        return None
    
    def submit_for_review(
        self,
        flow_id: str,
        document_id: int,
        document_type: str,
        document_title: str,
        submitter: str,
        comment: str = ''
    ) -> Optional[ReviewRecord]:
        """提交文档审核"""
        flow = self._flows.get(flow_id)
        if not flow:
            logger.error(f"Flow {flow_id} not found")
            return None
        
        # 检查是否已有活跃审核
        if document_id in self._document_reviews:
            existing_review = self._document_reviews[document_id]
            if existing_review in self._active_reviews:
                record = self._active_reviews[existing_review]
                if record.status not in [ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.WITHDRAWN]:
                    logger.warning(f"Document {document_id} already has active review")
                    return None
        
        # 创建审核记录
        import uuid
        record = ReviewRecord(
            id=str(uuid.uuid4()),
            flow_id=flow_id,
            document_id=document_id,
            document_type=document_type,
            document_title=document_title,
            current_level=1,
            total_levels=len(flow.levels),
            status=ReviewStatus.PENDING,
            submitted_by=submitter,
            submit_comment=comment,
        )
        
        # 设置当前级别截止时间
        if flow.levels:
            record.current_level_deadline = datetime.now() + timedelta(hours=flow.levels[0].timeout_hours)
        
        # 添加历史记录
        record.history.append({
            'action': ReviewAction.SUBMIT.value,
            'timestamp': datetime.now().isoformat(),
            'user': submitter,
            'comment': comment,
        })
        
        # 存储
        self._active_reviews[record.id] = record
        self._document_reviews[document_id] = record.id
        
        # 触发回调
        self._trigger_callbacks('submitted', record)
        
        logger.info(f"Review submitted: {record.id} for document {document_id}")
        return record
    
    def approve(
        self,
        review_id: str,
        reviewer: str,
        comment: str = ''
    ) -> bool:
        """批准审核"""
        record = self._active_reviews.get(review_id)
        if not record:
            logger.error(f"Review {review_id} not found")
            return False
        
        flow = self._flows.get(record.flow_id)
        if not flow:
            return False
        
        # 检查状态
        if record.status not in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]:
            logger.warning(f"Review {review_id} is not in reviewable state: {record.status}")
            return False
        
        # 获取当前级别配置
        current_level_index = record.current_level - 1
        if current_level_index >= len(flow.levels):
            logger.error(f"Invalid level index: {current_level_index}")
            return False
        
        level_config = flow.levels[current_level_index]
        
        # 添加审核记录
        review_record = {
            'level': record.current_level,
            'level_name': level_config.name,
            'action': ReviewAction.APPROVE.value,
            'reviewer': reviewer,
            'comment': comment,
            'timestamp': datetime.now().isoformat(),
        }
        record.reviews.append(review_record)
        
        # 添加历史
        record.history.append({
            'action': ReviewAction.APPROVE.value,
            'timestamp': datetime.now().isoformat(),
            'user': reviewer,
            'comment': comment,
            'level': record.current_level,
        })
        
        # 检查是否完成所有级别
        if record.current_level >= record.total_levels:
            # 完成审核
            record.status = ReviewStatus.APPROVED
            record.completed_at = datetime.now()
            record.completed_by = reviewer
            record.final_comment = comment
            
            # 移除活跃审核
            if record.document_id in self._document_reviews:
                del self._document_reviews[record.document_id]
            
            self._trigger_callbacks('approved', record)
            logger.info(f"Review {review_id} approved")
        else:
            # 进入下一级别
            record.current_level += 1
            next_level_index = record.current_level - 1
            if next_level_index < len(flow.levels):
                record.current_level_deadline = datetime.now() + timedelta(hours=flow.levels[next_level_index].timeout_hours)
            record.status = ReviewStatus.IN_REVIEW
            
            self._trigger_callbacks('approved', record)
            logger.info(f"Review {review_id} advanced to level {record.current_level}")
        
        record.updated_at = datetime.now()
        return True
    
    def reject(
        self,
        review_id: str,
        reviewer: str,
        comment: str = ''
    ) -> bool:
        """拒绝审核"""
        record = self._active_reviews.get(review_id)
        if not record:
            return False
        
        # 添加审核记录
        flow = self._flows.get(record.flow_id)
        level_config = flow.levels[record.current_level - 1] if flow and record.current_level <= len(flow.levels) else None
        
        review_record = {
            'level': record.current_level,
            'level_name': level_config.name if level_config else 'Unknown',
            'action': ReviewAction.REJECT.value,
            'reviewer': reviewer,
            'comment': comment,
            'timestamp': datetime.now().isoformat(),
        }
        record.reviews.append(review_record)
        
        # 添加历史
        record.history.append({
            'action': ReviewAction.REJECT.value,
            'timestamp': datetime.now().isoformat(),
            'user': reviewer,
            'comment': comment,
            'level': record.current_level,
        })
        
        # 拒绝审核
        record.status = ReviewStatus.REJECTED
        record.completed_at = datetime.now()
        record.completed_by = reviewer
        record.final_comment = comment
        
        # 移除活跃审核
        if record.document_id in self._document_reviews:
            del self._document_reviews[record.document_id]
        
        self._trigger_callbacks('rejected', record)
        record.updated_at = datetime.now()
        
        logger.info(f"Review {review_id} rejected")
        return True
    
    def request_revision(
        self,
        review_id: str,
        reviewer: str,
        comment: str = ''
    ) -> bool:
        """要求修订"""
        record = self._active_reviews.get(review_id)
        if not record:
            return False
        
        flow = self._flows.get(record.flow_id)
        level_config = flow.levels[record.current_level - 1] if flow and record.current_level <= len(flow.levels) else None
        
        review_record = {
            'level': record.current_level,
            'level_name': level_config.name if level_config else 'Unknown',
            'action': ReviewAction.REQUEST_REVISION.value,
            'reviewer': reviewer,
            'comment': comment,
            'timestamp': datetime.now().isoformat(),
        }
        record.reviews.append(review_record)
        
        record.history.append({
            'action': ReviewAction.REQUEST_REVISION.value,
            'timestamp': datetime.now().isoformat(),
            'user': reviewer,
            'comment': comment,
            'level': record.current_level,
        })
        
        record.status = ReviewStatus.REVISION_REQUESTED
        
        self._trigger_callbacks('revision_requested', record)
        record.updated_at = datetime.now()
        
        logger.info(f"Revision requested for review {review_id}")
        return True
    
    def withdraw(self, review_id: str, user: str, comment: str = '') -> bool:
        """撤回审核"""
        record = self._active_reviews.get(review_id)
        if not record:
            return False
        
        # 检查是否允许撤回
        flow = self._flows.get(record.flow_id)
        if not flow:
            return False
        
        if record.status == ReviewStatus.APPROVED and not flow.allow_withdraw_after_approve:
            logger.warning(f"Cannot withdraw approved review {review_id}")
            return False
        
        record.history.append({
            'action': ReviewAction.WITHDRAW.value,
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'comment': comment,
        })
        
        record.status = ReviewStatus.WITHDRAWN
        record.completed_at = datetime.now()
        record.completed_by = user
        
        if record.document_id in self._document_reviews:
            del self._document_reviews[record.document_id]
        
        self._trigger_callbacks('withdrawn', record)
        record.updated_at = datetime.now()
        
        logger.info(f"Review {review_id} withdrawn")
        return True
    
    def resubmit(self, review_id: str, user: str, comment: str = '') -> bool:
        """重新提交（修订后）"""
        record = self._active_reviews.get(review_id)
        if not record:
            return False
        
        if record.status != ReviewStatus.REVISION_REQUESTED:
            logger.warning(f"Review {review_id} is not in revision requested state")
            return False
        
        flow = self._flows.get(record.flow_id)
        if not flow:
            return False
        
        record.history.append({
            'action': ReviewAction.SUBMIT.value,
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'comment': comment,
            'note': 'Resubmitted after revision',
        })
        
        record.status = ReviewStatus.PENDING
        if flow.levels:
            record.current_level_deadline = datetime.now() + timedelta(hours=flow.levels[0].timeout_hours)
        
        record.updated_at = datetime.now()
        logger.info(f"Review {review_id} resubmitted")
        return True
    
    def get_review(self, review_id: str) -> Optional[ReviewRecord]:
        """获取审核记录"""
        return self._active_reviews.get(review_id)
    
    def get_review_by_document(self, document_id: int) -> Optional[ReviewRecord]:
        """根据文档ID获取审核记录"""
        review_id = self._document_reviews.get(document_id)
        if review_id:
            return self._active_reviews.get(review_id)
        return None
    
    def list_reviews(
        self,
        status: Optional[ReviewStatus] = None,
        flow_id: Optional[str] = None,
        submitted_by: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 100
    ) -> List[ReviewRecord]:
        """列出审核记录"""
        reviews = list(self._active_reviews.values())
        
        if status:
            reviews = [r for r in reviews if r.status == status]
        
        if flow_id:
            reviews = [r for r in reviews if r.flow_id == flow_id]
        
        if submitted_by:
            reviews = [r for r in reviews if r.submitted_by == submitted_by]
        
        if document_type:
            reviews = [r for r in reviews if r.document_type == document_type]
        
        # 按时间倒序
        reviews.sort(key=lambda r: r.submitted_at, reverse=True)
        
        return reviews[:limit]
    
    def get_pending_reviews(self, reviewer_role: Optional[str] = None) -> List[ReviewRecord]:
        """获取待审核记录"""
        pending = []
        
        for record in self._active_reviews.values():
            if record.status not in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]:
                continue
            
            flow = self._flows.get(record.flow_id)
            if not flow:
                continue
            
            # 检查是否超时
            if record.current_level_deadline and datetime.now() > record.current_level_deadline:
                # 超时处理
                self._handle_timeout(record)
                continue
            
            pending.append(record)
        
        return pending
    
    def _handle_timeout(self, record: ReviewRecord):
        """处理超时"""
        flow = self._flows.get(record.flow_id)
        if not flow:
            return
        
        # 触发超时回调
        if not record.timeout_notified:
            self._trigger_callbacks('timeout', record)
            record.timeout_notified = True
            record.updated_at = datetime.now()
            logger.warning(f"Review {record.id} has timed out")


# 全局实例
_review_flow: Optional[DocumentReviewFlow] = None


def get_review_flow() -> DocumentReviewFlow:
    """获取审核流程管理器单例"""
    global _review_flow
    if _review_flow is None:
        _review_flow = DocumentReviewFlow()
    return _review_flow


def init_review_flow(config: Optional[Dict[str, Any]] = None) -> DocumentReviewFlow:
    """初始化审核流程管理器"""
    global _review_flow
    _review_flow = DocumentReviewFlow(config)
    return _review_flow
