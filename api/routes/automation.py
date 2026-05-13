"""
告警触发自动化API路由
提供触发规则管理、条件评估和自动化执行接口
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user, CurrentUser
from modules.automation.alert_trigger.models import (
    AlertTriggerRule, TriggerEvent, ActionConfig, ActionType,
    ConditionConfig, AlertLevel as ModelAlertLevel
)
from modules.automation.alert_trigger.trigger import AlertTriggerEngine

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局触发引擎实例（内存存储，v1版本）
_trigger_engine = AlertTriggerEngine()


# ============== 请求/响应模型 ==============

class ConditionConfigRequest(BaseModel):
    """触发条件配置请求"""
    condition_type: str = Field("threshold", description="条件类型: threshold, change, rate, constant, expression")
    metric_name: str = Field("", description="指标名称")
    operator: str = Field(">", description="操作符: >, <, >=, <=, ==, !=")
    threshold_value: float = Field(0, description="阈值")
    duration_seconds: int = Field(0, description="持续时间(秒)")
    change_percent: float = Field(0, description="变化百分比")
    rate_percent: float = Field(0, description="速率百分比")
    expression: str = Field("", description="自定义表达式")


class ActionConfigRequest(BaseModel):
    """动作配置请求"""
    action_type: ActionType
    enabled: bool = True
    # 脚本配置
    script_name: Optional[str] = None
    script_content: Optional[str] = None
    script_params: Dict[str, Any] = {}
    # 工单配置
    workorder_title_template: Optional[str] = None
    workorder_description_template: Optional[str] = None
    workorder_type: str = "fault"
    workorder_priority: str = "P2"
    # 通知配置
    notification_channels: List[str] = []
    notification_receivers: List[str] = []
    notification_template: Optional[str] = None


class CreateTriggerRuleRequest(BaseModel):
    """创建触发规则请求"""
    name: str = Field(..., description="规则名称")
    description: str = Field("", description="规则描述")
    enabled: bool = Field(True, description="是否启用")
    condition: ConditionConfigRequest
    alert_level: str = Field("medium", description="告警级别")
    device_ids: List[int] = Field([], description="设备ID列表，空表示所有设备")
    device_tags: List[str] = Field([], description="设备标签过滤")
    trigger_interval: int = Field(300, description="触发间隔(秒)")
    suppress_enabled: bool = Field(False, description="是否启用抑制")
    suppress_duration: int = Field(300, description="抑制持续时间(秒)")
    suppress_key: str = Field("", description="抑制Key")
    time_windows: List[Dict[str, Any]] = Field([], description="时间窗口配置")
    actions: List[ActionConfigRequest] = Field([], description="动作列表")


class UpdateTriggerRuleRequest(BaseModel):
    """更新触发规则请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    condition: Optional[ConditionConfigRequest] = None
    alert_level: Optional[str] = None
    device_ids: Optional[List[int]] = None
    device_tags: Optional[List[str]] = None
    trigger_interval: Optional[int] = None
    suppress_enabled: Optional[bool] = None
    suppress_duration: Optional[int] = None
    suppress_key: Optional[str] = None
    time_windows: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[ActionConfigRequest]] = None


class TriggerRuleResponse(BaseModel):
    """触发规则响应"""
    id: str
    name: str
    description: str
    enabled: bool
    condition: Dict[str, Any]
    alert_level: str
    device_ids: List[int]
    device_tags: List[str]
    trigger_interval: int
    suppress_enabled: bool
    suppress_duration: int
    suppress_key: str
    time_windows: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: str
    updated_by: str
    trigger_count: int
    last_triggered_at: Optional[str] = None


class TriggerEventResponse(BaseModel):
    """触发事件响应"""
    id: str
    rule_id: str
    rule_name: str
    trigger_time: str
    metric_name: str
    metric_value: float
    threshold_value: float
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    device_ip: Optional[str] = None
    status: str
    actions_executed: List[str]
    execution_results: List[Dict[str, Any]]


class EvaluateMetricRequest(BaseModel):
    """评估指标请求"""
    metric_name: str = Field(..., description="指标名称")
    value: float = Field(..., description="当前值")
    previous_value: Optional[float] = Field(None, description="上次值")
    device_id: Optional[int] = Field(None, description="设备ID")
    device_name: Optional[str] = Field(None, description="设备名称")
    device_ip: Optional[str] = Field(None, description="设备IP")
    extra_data: Dict[str, Any] = Field({}, description="额外数据")


class EvaluateMetricResponse(BaseModel):
    """评估指标响应"""
    metric_name: str
    value: float
    triggered_rules: List[TriggerEventResponse]
    triggered_count: int


# ============== 辅助函数 ==============

def _rule_to_response(rule: AlertTriggerRule) -> TriggerRuleResponse:
    """将 AlertTriggerRule 转换为响应模型"""
    return TriggerRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        enabled=rule.enabled,
        condition={
            "condition_type": rule.condition.condition_type,
            "metric_name": rule.condition.metric_name,
            "operator": rule.condition.operator,
            "threshold_value": rule.condition.threshold_value,
            "duration_seconds": rule.condition.duration_seconds,
            "change_percent": rule.condition.change_percent,
            "rate_percent": rule.condition.rate_percent,
            "expression": rule.condition.expression,
        },
        alert_level=rule.alert_level,
        device_ids=rule.device_ids,
        device_tags=rule.device_tags,
        trigger_interval=rule.trigger_interval,
        suppress_enabled=rule.suppress_enabled,
        suppress_duration=rule.suppress_duration,
        suppress_key=rule.suppress_key,
        time_windows=rule.time_windows,
        actions=[
            {
                "action_type": a.action_type.value if isinstance(a.action_type, ActionType) else a.action_type,
                "enabled": a.enabled,
                "script_name": a.script_name,
                "script_params": a.script_params,
                "workorder_title_template": a.workorder_title_template,
                "workorder_description_template": a.workorder_description_template,
                "workorder_type": a.workorder_type,
                "workorder_priority": a.workorder_priority,
                "notification_channels": a.notification_channels,
                "notification_receivers": a.notification_receivers,
                "notification_template": a.notification_template,
            }
            for a in rule.actions
        ],
        created_at=rule.created_at.isoformat() if rule.created_at else None,
        updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
        created_by=rule.created_by,
        updated_by=rule.updated_by,
        trigger_count=rule.trigger_count,
        last_triggered_at=rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
    )


def _event_to_response(event: TriggerEvent) -> TriggerEventResponse:
    """将 TriggerEvent 转换为响应模型"""
    return TriggerEventResponse(
        id=event.id,
        rule_id=event.rule_id,
        rule_name=event.rule_name,
        trigger_time=event.trigger_time.isoformat() if event.trigger_time else "",
        metric_name=event.metric_name,
        metric_value=event.metric_value,
        threshold_value=event.threshold_value,
        device_id=event.device_id,
        device_name=event.device_name,
        device_ip=event.device_ip,
        status=event.status,
        actions_executed=event.actions_executed,
        execution_results=event.execution_results,
    )


def _request_to_action_config(req: ActionConfigRequest) -> ActionConfig:
    """将请求转换为 ActionConfig"""
    return ActionConfig(
        action_type=req.action_type,
        enabled=req.enabled,
        script_name=req.script_name,
        script_content=req.script_content,
        script_params=req.script_params,
        workorder_title_template=req.workorder_title_template,
        workorder_description_template=req.workorder_description_template,
        workorder_type=req.workorder_type,
        workorder_priority=req.workorder_priority,
        notification_channels=req.notification_channels,
        notification_receivers=req.notification_receivers,
        notification_template=req.notification_template,
    )


def _request_to_condition_config(req: ConditionConfigRequest) -> ConditionConfig:
    """将请求转换为 ConditionConfig"""
    return ConditionConfig(
        condition_type=req.condition_type,
        metric_name=req.metric_name,
        operator=req.operator,
        threshold_value=req.threshold_value,
        duration_seconds=req.duration_seconds,
        change_percent=req.change_percent,
        rate_percent=req.rate_percent,
        expression=req.expression,
    )


# ============== API路由 ==============

@router.get("/trigger-rules", summary="列出触发规则")
async def list_trigger_rules(
    enabled: Optional[bool] = Query(None, description="按启用状态过滤"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    列出所有触发规则
    
    - 不传 enabled: 返回所有规则
    - enabled=true: 只返回已启用的规则
    - enabled=false: 只返回已禁用的规则
    """
    rules = _trigger_engine.list_rules(enabled_only=enabled if enabled is not None else False)
    return {
        "total": len(rules),
        "rules": [_rule_to_response(r) for r in rules],
    }


@router.post("/trigger-rules", summary="创建触发规则", response_model=TriggerRuleResponse)
async def create_trigger_rule(
    request: CreateTriggerRuleRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    创建新的告警触发规则
    """
    rule_id = f"rule_{uuid.uuid4().hex[:12]}"
    
    rule = AlertTriggerRule(
        id=rule_id,
        name=request.name,
        description=request.description,
        enabled=request.enabled,
        condition=_request_to_condition_config(request.condition),
        alert_level=request.alert_level,
        device_ids=request.device_ids,
        device_tags=request.device_tags,
        trigger_interval=request.trigger_interval,
        suppress_enabled=request.suppress_enabled,
        suppress_duration=request.suppress_duration,
        suppress_key=request.suppress_key,
        time_windows=request.time_windows,
        actions=[_request_to_action_config(a) for a in request.actions],
        created_by=current_user.username,
        updated_by=current_user.username,
    )
    
    _trigger_engine.add_rule(rule)
    
    logger.info(f"Created trigger rule: {rule_id} by {current_user.username}")
    return _rule_to_response(rule)


@router.get("/trigger-rules/{rule_id}", summary="获取触发规则")
async def get_trigger_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取指定触发规则的详情
    """
    rule = _trigger_engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    return _rule_to_response(rule)


@router.put("/trigger-rules/{rule_id}", summary="更新触发规则", response_model=TriggerRuleResponse)
async def update_trigger_rule(
    rule_id: str,
    request: UpdateTriggerRuleRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    更新指定的触发规则
    """
    rule = _trigger_engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    
    # 更新字段
    if request.name is not None:
        rule.name = request.name
    if request.description is not None:
        rule.description = request.description
    if request.enabled is not None:
        rule.enabled = request.enabled
    if request.condition is not None:
        rule.condition = _request_to_condition_config(request.condition)
    if request.alert_level is not None:
        rule.alert_level = request.alert_level
    if request.device_ids is not None:
        rule.device_ids = request.device_ids
    if request.device_tags is not None:
        rule.device_tags = request.device_tags
    if request.trigger_interval is not None:
        rule.trigger_interval = request.trigger_interval
    if request.suppress_enabled is not None:
        rule.suppress_enabled = request.suppress_enabled
    if request.suppress_duration is not None:
        rule.suppress_duration = request.suppress_duration
    if request.suppress_key is not None:
        rule.suppress_key = request.suppress_key
    if request.time_windows is not None:
        rule.time_windows = request.time_windows
    if request.actions is not None:
        rule.actions = [_request_to_action_config(a) for a in request.actions]
    
    rule.updated_by = current_user.username
    rule.updated_at = datetime.now()
    
    _trigger_engine.update_rule(rule)
    
    logger.info(f"Updated trigger rule: {rule_id} by {current_user.username}")
    return _rule_to_response(rule)


@router.delete("/trigger-rules/{rule_id}", summary="删除触发规则")
async def delete_trigger_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    删除指定的触发规则
    """
    success = _trigger_engine.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    
    logger.info(f"Deleted trigger rule: {rule_id} by {current_user.username}")
    return {"message": f"规则 {rule_id} 已删除"}


@router.post("/trigger-rules/{rule_id}/test", summary="测试触发规则", response_model=TriggerEventResponse)
async def test_trigger_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    测试执行指定的触发规则（不会真正触发抑制和间隔限制）
    """
    rule = _trigger_engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    
    if not rule.enabled:
        raise HTTPException(status_code=400, detail="规则未启用，无法测试")
    
    if not rule.actions:
        raise HTTPException(status_code=400, detail="规则没有配置动作，无法测试")
    
    # 构造一个测试事件
    test_event = TriggerEvent(
        id=f"test_{uuid.uuid4().hex[:12]}",
        rule_id=rule.id,
        rule_name=rule.name,
        trigger_time=datetime.now(),
        metric_name=rule.condition.metric_name or "test_metric",
        metric_value=rule.condition.threshold_value,
        threshold_value=rule.condition.threshold_value,
        device_id=rule.device_ids[0] if rule.device_ids else None,
        device_name="test_device",
        device_ip="127.0.0.1",
    )
    
    # 执行动作（不修改规则统计）
    from modules.automation.alert_trigger.trigger import AlertTriggerEngine
    engine = AlertTriggerEngine()
    engine.add_rule(rule)
    
    try:
        result_event = await engine._execute_actions(rule, test_event)
        return _event_to_response(result_event)
    except Exception as e:
        logger.error(f"Test trigger rule failed: {e}")
        raise HTTPException(status_code=500, detail=f"测试执行失败: {str(e)}")


@router.post("/evaluate", summary="评估指标触发", response_model=EvaluateMetricResponse)
async def evaluate_metric(
    request: EvaluateMetricRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    评估指标是否触发规则
    
    将指标数据发送给触发引擎，评估是否满足任何规则的触发条件。
    如果满足条件，将触发相应的动作。
    """
    triggered_events = await _trigger_engine.evaluate_and_trigger(
        metric_name=request.metric_name,
        value=request.value,
        previous_value=request.previous_value,
        device_id=request.device_id,
        device_name=request.device_name,
        device_ip=request.device_ip,
        extra_data=request.extra_data,
    )
    
    return EvaluateMetricResponse(
        metric_name=request.metric_name,
        value=request.value,
        triggered_rules=[_event_to_response(e) for e in triggered_events],
        triggered_count=len(triggered_events),
    )


# ============== 脚本执行回滚API ==============

class RollbackRequest(BaseModel):
    """回滚请求"""
    rollback_script: Optional[str] = Field(None, description="回滚脚本内容")
    rollback_params: Dict[str, Any] = Field({}, description="回滚脚本参数")


class RollbackResponse(BaseModel):
    """回滚响应"""
    execution_id: str
    status: str
    snapshot_id: Optional[str] = None
    rollback_script_result: Optional[Dict[str, Any]] = None
    message: str
    duration: float


class SnapshotResponse(BaseModel):
    """快照响应"""
    id: str
    execution_id: str
    snapshot_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: str
    checksum: str


class CheckpointRequest(BaseModel):
    """保存检查点请求"""
    snapshot_type: str = Field("script_output", description="快照类型: device_config, database_state, script_output, full_system")
    data: Optional[Dict[str, Any]] = Field(None, description="快照数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="快照元数据")


# 全局脚本执行器实例
_script_executor: Optional[Any] = None


def get_script_executor() -> Any:
    """获取脚本执行器实例"""
    global _script_executor
    if _script_executor is None:
        from modules.automation.script_executor import ScriptExecutor
        _script_executor = ScriptExecutor()
    return _script_executor


@router.post("/executions/{execution_id}/rollback", summary="执行回滚", response_model=RollbackResponse)
async def execute_rollback(
    execution_id: str,
    request: RollbackRequest = RollbackRequest(),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    执行指定执行的回滚
    
    根据execution_id获取之前保存的快照，并执行回滚。
    如果提供了rollback_script，将执行该回滚脚本。
    """
    executor = get_script_executor()
    
    result = executor._rollback_manager.execute_rollback(
        execution_id=execution_id,
        rollback_script=request.rollback_script,
        rollback_params=request.rollback_params,
    )
    
    logger.info(f"Rollback executed for {execution_id} by {current_user.username}: {result.status.value}")
    
    return RollbackResponse(
        execution_id=result.execution_id,
        status=result.status.value,
        snapshot_id=result.snapshot_id,
        rollback_script_result=result.rollback_script_result,
        message=result.message,
        duration=result.duration,
    )


@router.post("/executions/{execution_id}/checkpoint", summary="保存检查点", response_model=SnapshotResponse)
async def save_checkpoint(
    execution_id: str,
    request: CheckpointRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    为指定执行保存检查点/快照
    
    在执行脚本之前调用，保存系统状态快照，用于可能的回滚。
    """
    executor = get_script_executor()
    
    from modules.automation.script_executor.rollback import SnapshotType
    type_map = {
        'device_config': SnapshotType.DEVICE_CONFIG,
        'database_state': SnapshotType.DATABASE_STATE,
        'script_output': SnapshotType.SCRIPT_OUTPUT,
        'full_system': SnapshotType.FULL_SYSTEM,
    }
    snap_type = type_map.get(request.snapshot_type, SnapshotType.SCRIPT_OUTPUT)
    
    snapshot = executor._rollback_manager.save_checkpoint(
        execution_id=execution_id,
        snapshot_type=snap_type,
        data=request.data,
        metadata=request.metadata,
    )
    
    logger.info(f"Checkpoint saved for {execution_id} by {current_user.username}")
    
    return SnapshotResponse(
        id=snapshot.id,
        execution_id=snapshot.execution_id,
        snapshot_type=snapshot.snapshot_type.value,
        data=snapshot.data,
        metadata=snapshot.metadata,
        created_at=snapshot.created_at.isoformat(),
        checksum=snapshot.checksum,
    )


@router.get("/executions/{execution_id}/snapshot", summary="获取快照")
async def get_snapshot(
    execution_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取指定执行的快照信息
    """
    executor = get_script_executor()
    snapshot = executor._rollback_manager.get_snapshot(execution_id)
    
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No snapshot found for execution {execution_id}")
    
    return SnapshotResponse(
        id=snapshot.id,
        execution_id=snapshot.execution_id,
        snapshot_type=snapshot.snapshot_type.value,
        data=snapshot.data,
        metadata=snapshot.metadata,
        created_at=snapshot.created_at.isoformat(),
        checksum=snapshot.checksum,
    )


@router.get("/rollback-history", summary="获取回滚历史")
async def get_rollback_history(
    limit: int = Query(100, description="返回数量限制"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取回滚历史记录
    """
    executor = get_script_executor()
    history = executor._rollback_manager.get_rollback_history(limit=limit)
    
    return {
        "total": len(history),
        "history": [
            {
                "execution_id": r.execution_id,
                "status": r.status.value,
                "snapshot_id": r.snapshot_id,
                "message": r.message,
                "duration": r.duration,
                "created_at": r.created_at.isoformat(),
            }
            for r in history
        ],
    }
