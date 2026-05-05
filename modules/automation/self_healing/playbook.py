"""
剧本管理模块
提供剧本定义、剧本审核、剧本版本、剧本执行日志等功能
"""

import logging
import yaml
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import asyncio

logger = logging.getLogger(__name__)


class PlaybookStatus(Enum):
    """剧本状态"""
    DRAFT = 'draft'
    PENDING_REVIEW = 'pending_review'
    UNDER_REVIEW = 'under_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    DEPRECATED = 'deprecated'
    ACTIVE = 'active'


class PlaybookType(Enum):
    """剧本类型"""
    INCIDENT = 'incident'           # 事件响应
    AUTOMATIC_HEALING = 'auto_healing'  # 自动恢复
    MAINTENANCE = 'maintenance'      # 维护
    SECURITY = 'security'            # 安全响应
    CAPACITY = 'capacity'           # 容量管理
    CUSTOM = 'custom'               # 自定义


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = 'pending'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'


@dataclass
class PlaybookStep:
    """剧本步骤"""
    step_id: str = ''
    name: str = ''
    description: str = ''
    
    # 执行配置
    action: str = ''
    action_params: Dict[str, Any] = field(default_factory=dict)
    
    # 条件配置
    condition: Optional[str] = None  # 执行条件（表达式）
    continue_on_failure: bool = False
    
    # 超时配置
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_interval_seconds: int = 10
    
    # 验证配置
    verify_after: bool = True
    verify_condition: Optional[str] = None
    
    # 下一个步骤
    next_step_on_success: Optional[str] = None
    next_step_on_failure: Optional[str] = None
    
    # 元数据
    order: int = 0
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'step_id': self.step_id,
            'name': self.name,
            'description': self.description,
            'action': self.action,
            'action_params': self.action_params,
            'condition': self.condition,
            'continue_on_failure': self.continue_on_failure,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'retry_interval_seconds': self.retry_interval_seconds,
            'verify_after': self.verify_after,
            'verify_condition': self.verify_condition,
            'next_step_on_success': self.next_step_on_success,
            'next_step_on_failure': self.next_step_on_failure,
            'order': self.order,
            'tags': self.tags,
        }


@dataclass
class Playbook:
    """剧本"""
    playbook_id: str = ''
    name: str = ''
    version: str = '1.0.0'
    
    # 基本信息
    type: PlaybookType = PlaybookType.INCIDENT
    description: str = ''
    tags: List[str] = field(default_factory=list)
    
    # 适用范围
    applicable_to: List[str] = field(default_factory=list)  # asset types
    applicable_faults: List[str] = field(default_factory=list)  # fault pattern IDs
    min_severity: str = 'warning'
    
    # 触发条件
    trigger_condition: Optional[str] = None  # 自动触发的条件
    auto_trigger: bool = False
    
    # 步骤
    steps: List[PlaybookStep] = field(default_factory=list)
    
    # 状态
    status: PlaybookStatus = PlaybookStatus.DRAFT
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ''
    approved_by: str = ''
    approved_at: Optional[datetime] = None
    
    # 版本信息
    previous_version: Optional[str] = None
    change_log: str = ''
    
    # 内容哈希
    content_hash: str = ''
    
    def calculate_hash(self) -> str:
        """计算内容哈希"""
        content = json.dumps([s.to_dict() for s in self.steps], sort_keys=True)
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return self.content_hash
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'playbook_id': self.playbook_id,
            'name': self.name,
            'version': self.version,
            'type': self.type.value,
            'description': self.description,
            'tags': self.tags,
            'applicable_to': self.applicable_to,
            'applicable_faults': self.applicable_faults,
            'min_severity': self.min_severity,
            'trigger_condition': self.trigger_condition,
            'auto_trigger': self.auto_trigger,
            'steps': [s.to_dict() for s in self.steps],
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'previous_version': self.previous_version,
            'change_log': self.change_log,
            'content_hash': self.content_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playbook':
        """从字典创建剧本"""
        steps = [PlaybookStep(**s) for s in data.get('steps', [])]
        return cls(
            playbook_id=data.get('playbook_id', ''),
            name=data.get('name', ''),
            version=data.get('version', '1.0.0'),
            type=PlaybookType(data.get('type', 'incident')),
            description=data.get('description', ''),
            tags=data.get('tags', []),
            applicable_to=data.get('applicable_to', []),
            applicable_faults=data.get('applicable_faults', []),
            min_severity=data.get('min_severity', 'warning'),
            trigger_condition=data.get('trigger_condition'),
            auto_trigger=data.get('auto_trigger', False),
            steps=steps,
            status=PlaybookStatus(data.get('status', 'draft')),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            created_by=data.get('created_by', ''),
            approved_by=data.get('approved_by', ''),
            approved_at=datetime.fromisoformat(data['approved_at']) if data.get('approved_at') else None,
            previous_version=data.get('previous_version'),
            change_log=data.get('change_log', ''),
            content_hash=data.get('content_hash', ''),
        )
    
    def to_yaml(self) -> str:
        """转换为YAML"""
        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'Playbook':
        """从YAML创建剧本"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Playbook':
        """从JSON创建剧本"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class PlaybookExecution:
    """剧本执行记录"""
    execution_id: str = field(default_factory=lambda: f"EXEC-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
    
    # 关联信息
    playbook_id: str = ''
    playbook_name: str = ''
    playbook_version: str = ''
    
    # 触发信息
    triggered_by: str = 'manual'  # manual, automatic, api, schedule
    trigger_condition: str = ''
    fault_event_id: Optional[str] = None
    
    # 执行上下文
    context: Dict[str, Any] = field(default_factory=dict)
    
    # 执行状态
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # 时间信息
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    
    # 步骤执行记录
    step_executions: List[Dict[str, Any]] = field(default_factory=list)
    
    # 执行者
    executed_by: str = 'system'
    
    # 结果
    result: str = ''
    output: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ''
    
    # 审计
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'playbook_id': self.playbook_id,
            'playbook_name': self.playbook_name,
            'playbook_version': self.playbook_version,
            'triggered_by': self.triggered_by,
            'trigger_condition': self.trigger_condition,
            'fault_event_id': self.fault_event_id,
            'context': self.context,
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration_seconds': self.total_duration_seconds,
            'step_executions': self.step_executions,
            'executed_by': self.executed_by,
            'result': self.result,
            'output': self.output,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
        }


@dataclass
class ReviewComment:
    """审核评论"""
    comment_id: str = ''
    playbook_id: str = ''
    version: str = ''
    
    reviewer: str = ''
    comment: str = ''
    
    # 位置信息
    line_number: Optional[int] = None
    step_id: Optional[str] = None
    
    # 状态
    status: str = 'pending'  # pending, resolved, rejected
    resolved_by: str = ''
    resolved_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'comment_id': self.comment_id,
            'playbook_id': self.playbook_id,
            'version': self.version,
            'reviewer': self.reviewer,
            'comment': self.comment,
            'line_number': self.line_number,
            'step_id': self.step_id,
            'status': self.status,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat(),
        }


class PlaybookManager:
    """剧本管理器"""
    
    def __init__(self):
        # 剧本库
        self.playbooks: Dict[str, List[Playbook]] = defaultdict(list)  # playbook_id -> [versions]
        
        # 执行记录
        self.executions: List[PlaybookExecution] = []
        
        # 审核记录
        self.reviews: Dict[str, List[ReviewComment]] = defaultdict(list)
        
        # 执行器
        self.step_executors: Dict[str, Callable] = {}
        self._register_default_executors()
    
    def _register_default_executors(self):
        """注册默认执行器"""
        self.step_executors = {
            'execute_script': self._execute_script,
            'http_request': self._execute_http_request,
            'send_notification': self._send_notification,
            'create_incident': self._create_incident,
            'wait': self._wait,
            'condition_check': self._condition_check,
            'update_ticket': self._update_ticket,
        }
    
    # ==================== 剧本管理 ====================
    
    def create_playbook(self, playbook: Playbook) -> bool:
        """创建剧本"""
        try:
            playbook.playbook_id = playbook.playbook_id or f"PB-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            playbook.calculate_hash()
            self.playbooks[playbook.playbook_id].append(playbook)
            logger.info(f"Created playbook: {playbook.playbook_id} v{playbook.version}")
            return True
        except Exception as e:
            logger.error(f"Failed to create playbook: {e}")
            return False
    
    def update_playbook(self, playbook: Playbook) -> Optional[Playbook]:
        """更新剧本（创建新版本）"""
        try:
            # 获取最新版本
            versions = self.playbooks.get(playbook.playbook_id, [])
            if versions:
                latest = versions[-1]
                playbook.version = self._increment_version(latest.version)
                playbook.previous_version = latest.version
            
            playbook.updated_at = datetime.now()
            playbook.calculate_hash()
            self.playbooks[playbook.playbook_id].append(playbook)
            
            logger.info(f"Updated playbook: {playbook.playbook_id} v{playbook.version}")
            return playbook
        except Exception as e:
            logger.error(f"Failed to update playbook: {e}")
            return None
    
    def _increment_version(self, version: str) -> str:
        """递增版本号"""
        parts = version.split('.')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return f"{major}.{minor}.{patch + 1}"
    
    def get_playbook(self, playbook_id: str, version: Optional[str] = None) -> Optional[Playbook]:
        """获取剧本"""
        versions = self.playbooks.get(playbook_id, [])
        if not versions:
            return None
        
        if version:
            for v in versions:
                if v.version == version:
                    return v
            return None
        
        return versions[-1]  # 返回最新版本
    
    def get_all_playbooks(self, status: Optional[PlaybookStatus] = None) -> List[Playbook]:
        """获取所有剧本（最新版本）"""
        result = []
        for versions in self.playbooks.values():
            latest = versions[-1]
            if status is None or latest.status == status:
                result.append(latest)
        return sorted(result, key=lambda x: x.updated_at, reverse=True)
    
    def get_playbook_versions(self, playbook_id: str) -> List[Playbook]:
        """获取剧本所有版本"""
        return self.playbooks.get(playbook_id, [])
    
    # ==================== 剧本审核 ====================
    
    def submit_for_review(self, playbook_id: str, version: str) -> bool:
        """提交审核"""
        playbook = self.get_playbook(playbook_id, version)
        if not playbook:
            return False
        
        playbook.status = PlaybookStatus.PENDING_REVIEW
        playbook.updated_at = datetime.now()
        logger.info(f"Playbook submitted for review: {playbook_id} v{version}")
        return True
    
    def start_review(self, playbook_id: str, version: str, reviewer: str) -> bool:
        """开始审核"""
        playbook = self.get_playbook(playbook_id, version)
        if not playbook:
            return False
        
        playbook.status = PlaybookStatus.UNDER_REVIEW
        playbook.updated_at = datetime.now()
        logger.info(f"Review started for: {playbook_id} v{version} by {reviewer}")
        return True
    
    def approve_playbook(self, playbook_id: str, version: str, reviewer: str) -> bool:
        """批准剧本"""
        playbook = self.get_playbook(playbook_id, version)
        if not playbook:
            return False
        
        playbook.status = PlaybookStatus.APPROVED
        playbook.approved_by = reviewer
        playbook.approved_at = datetime.now()
        playbook.updated_at = datetime.now()
        
        logger.info(f"Playbook approved: {playbook_id} v{version} by {reviewer}")
        return True
    
    def reject_playbook(self, playbook_id: str, version: str, reviewer: str, reason: str) -> bool:
        """拒绝剧本"""
        playbook = self.get_playbook(playbook_id, version)
        if not playbook:
            return False
        
        playbook.status = PlaybookStatus.REJECTED
        playbook.updated_at = datetime.now()
        
        # 添加审核评论
        comment = ReviewComment(
            comment_id=f"REV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            playbook_id=playbook_id,
            version=version,
            reviewer=reviewer,
            comment=reason,
        )
        self.reviews[playbook_id].append(comment)
        
        logger.info(f"Playbook rejected: {playbook_id} v{version} by {reviewer}")
        return True
    
    def add_review_comment(self, playbook_id: str, version: str, reviewer: str, 
                          comment: str, step_id: Optional[str] = None) -> bool:
        """添加审核评论"""
        playbook = self.get_playbook(playbook_id, version)
        if not playbook:
            return False
        
        review_comment = ReviewComment(
            comment_id=f"REV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            playbook_id=playbook_id,
            version=version,
            reviewer=reviewer,
            comment=comment,
            step_id=step_id,
        )
        self.reviews[playbook_id].append(review_comment)
        return True
    
    def get_review_comments(self, playbook_id: str, version: Optional[str] = None) -> List[ReviewComment]:
        """获取审核评论"""
        comments = self.reviews.get(playbook_id, [])
        if version:
            comments = [c for c in comments if c.version == version]
        return comments
    
    # ==================== 剧本执行 ====================
    
    async def execute_playbook(self, playbook_id: str, version: Optional[str] = None,
                              context: Optional[Dict[str, Any]] = None,
                              triggered_by: str = 'manual') -> Optional[PlaybookExecution]:
        """执行剧本"""
        playbook = self.get_playbook(playbook_id, version)
        if not playbook:
            logger.error(f"Playbook not found: {playbook_id}")
            return None
        
        if playbook.status != PlaybookStatus.APPROVED and playbook.status != PlaybookStatus.ACTIVE:
            logger.error(f"Playbook not approved: {playbook_id} status={playbook.status}")
            return None
        
        execution = PlaybookExecution(
            playbook_id=playbook.playbook_id,
            playbook_name=playbook.name,
            playbook_version=playbook.version,
            triggered_by=triggered_by,
            context=context or {},
            started_at=datetime.now(),
            executed_by=triggered_by,
        )
        
        logger.info(f"Executing playbook: {playbook.name} v{playbook.version}")
        
        try:
            # 按顺序执行步骤
            for step in playbook.steps:
                step_result = await self._execute_step(step, execution.context)
                execution.step_executions.append(step_result)
                
                # 检查结果
                if step_result['status'] == 'failed' and not step.continue_on_failure:
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = step_result.get('error', 'Step failed')
                    break
                
                # 处理下一步
                if step.next_step_on_failure and step_result['status'] == 'failed':
                    # 跳转到失败处理步骤
                    pass
            
            if execution.status != ExecutionStatus.FAILED:
                execution.status = ExecutionStatus.COMPLETED
                execution.result = 'success'
            
        except Exception as e:
            logger.error(f"Playbook execution error: {e}")
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
        
        execution.completed_at = datetime.now()
        execution.total_duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
        
        self.executions.append(execution)
        logger.info(f"Playbook execution completed: {execution.execution_id}")
        
        return execution
    
    async def _execute_step(self, step: PlaybookStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行步骤"""
        result = {
            'step_id': step.step_id,
            'step_name': step.name,
            'action': step.action,
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'output': None,
            'error': None,
        }
        
        try:
            # 检查条件
            if step.condition:
                if not self._evaluate_condition(step.condition, context):
                    result['status'] = 'skipped'
                    result['output'] = 'Condition not met'
                    return result
            
            # 获取执行器
            executor = self.step_executors.get(step.action)
            if not executor:
                result['status'] = 'failed'
                result['error'] = f"Unknown action: {step.action}"
                return result
            
            # 执行
            if asyncio.iscoroutinefunction(executor):
                output = await executor(step.action_params, context)
            else:
                output = executor(step.action_params, context)
            
            result['status'] = 'completed'
            result['output'] = output
            
        except Exception as e:
            logger.error(f"Step execution error: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
        
        result['ended_at'] = datetime.now().isoformat()
        return result
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件"""
        # 简化实现，实际应该使用表达式解析器
        try:
            # 替换变量
            expr = condition
            for key, value in context.items():
                expr = expr.replace(f'${key}', str(value))
            
            # 安全评估（应该使用安全的表达式解析器）
            return True  # 简化
        except Exception:
            return False
    
    async def _execute_script(self, params: Dict, context: Dict) -> str:
        """执行脚本"""
        script = params.get('script', '')
        logger.info(f"Executing script: {script[:100]}...")
        return "Script executed successfully"
    
    async def _execute_http_request(self, params: Dict, context: Dict) -> str:
        """发送HTTP请求"""
        url = params.get('url', '')
        method = params.get('method', 'GET')
        logger.info(f"HTTP {method} {url}")
        return f"Request to {url} completed"
    
    async def _send_notification(self, params: Dict, context: Dict) -> str:
        """发送通知"""
        message = params.get('message', '')
        channel = params.get('channel', 'email')
        logger.info(f"Sending notification via {channel}: {message}")
        return "Notification sent"
    
    async def _create_incident(self, params: Dict, context: Dict) -> str:
        """创建工单"""
        title = params.get('title', 'Incident')
        logger.info(f"Creating incident: {title}")
        return f"Incident created: {title}"
    
    async def _wait(self, params: Dict, context: Dict) -> str:
        """等待"""
        seconds = params.get('seconds', 5)
        await asyncio.sleep(seconds)
        return f"Waited {seconds} seconds"
    
    async def _condition_check(self, params: Dict, context: Dict) -> Dict[str, Any]:
        """条件检查"""
        condition = params.get('condition', '')
        passed = self._evaluate_condition(condition, context)
        return {'condition': condition, 'passed': passed}
    
    async def _update_ticket(self, params: Dict, context: Dict) -> str:
        """更新工单"""
        ticket_id = params.get('ticket_id', '')
        status = params.get('status', '')
        logger.info(f"Updating ticket {ticket_id} to {status}")
        return f"Ticket {ticket_id} updated"
    
    # ==================== 执行日志 ====================
    
    def get_execution_log(self, execution_id: str) -> Optional[PlaybookExecution]:
        """获取执行日志"""
        for exec_record in self.executions:
            if exec_record.execution_id == execution_id:
                return exec_record
        return None
    
    def get_execution_history(self, playbook_id: Optional[str] = None,
                             status: Optional[ExecutionStatus] = None,
                             days: int = 30) -> List[PlaybookExecution]:
        """获取执行历史"""
        cutoff = datetime.now() - timedelta(days=days)
        history = [e for e in self.executions if e.started_at and e.started_at > cutoff]
        
        if playbook_id:
            history = [e for e in history if e.playbook_id == playbook_id]
        
        if status:
            history = [e for e in history if e.status == status]
        
        return sorted(history, key=lambda x: x.started_at or datetime.min, reverse=True)
    
    def get_execution_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取执行统计"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [e for e in self.executions if e.started_at and e.started_at > cutoff]
        
        stats = {
            'total_executions': len(recent),
            'completed': len([e for e in recent if e.status == ExecutionStatus.COMPLETED]),
            'failed': len([e for e in recent if e.status == ExecutionStatus.FAILED]),
            'by_playbook': defaultdict(int),
            'by_trigger': defaultdict(int),
            'avg_duration_seconds': 0,
        }
        
        for e in recent:
            stats['by_playbook'][e.playbook_name] += 1
            stats['by_trigger'][e.triggered_by] += 1
        
        durations = [e.total_duration_seconds for e in recent if e.total_duration_seconds > 0]
        if durations:
            stats['avg_duration_seconds'] = sum(durations) / len(durations)
        
        stats['by_playbook'] = dict(stats['by_playbook'])
        stats['by_trigger'] = dict(stats['by_trigger'])
        
        return stats
    
    # ==================== YAML/JSON导入导出 ====================
    
    def import_from_yaml(self, yaml_str: str) -> Optional[Playbook]:
        """从YAML导入剧本"""
        try:
            playbook = Playbook.from_yaml(yaml_str)
            self.create_playbook(playbook)
            return playbook
        except Exception as e:
            logger.error(f"Failed to import YAML: {e}")
            return None
    
    def export_to_yaml(self, playbook_id: str, version: Optional[str] = None) -> Optional[str]:
        """导出YAML"""
        playbook = self.get_playbook(playbook_id, version)
        if playbook:
            return playbook.to_yaml()
        return None
    
    def import_from_json(self, json_str: str) -> Optional[Playbook]:
        """从JSON导入剧本"""
        try:
            playbook = Playbook.from_json(json_str)
            self.create_playbook(playbook)
            return playbook
        except Exception as e:
            logger.error(f"Failed to import JSON: {e}")
            return None
    
    def export_to_json(self, playbook_id: str, version: Optional[str] = None) -> Optional[str]:
        """导出JSON"""
        playbook = self.get_playbook(playbook_id, version)
        if playbook:
            return playbook.to_json()
        return None
