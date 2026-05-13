"""
告警触发器 - 规则引擎
实现告警触发规则的评估和执行
"""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable

from .models import (
    AlertTriggerRule, TriggerEvent, ActionConfig, ActionType,
    ConditionConfig, AlertLevel
)

logger = logging.getLogger(__name__)


class AlertTriggerEngine:
    """
    告警触发引擎
    
    负责管理触发规则、评估条件、执行动作
    """
    
    def __init__(self):
        self._rules: Dict[str, AlertTriggerRule] = {}
        self._events: Dict[str, TriggerEvent] = {}
        self._last_trigger_time: Dict[str, datetime] = {}
        self._suppressed_keys: Dict[str, datetime] = {}
        
    # ============== 规则管理 ==============
    
    def add_rule(self, rule: AlertTriggerRule) -> str:
        """添加规则"""
        self._rules[rule.id] = rule
        logger.info(f"Added trigger rule: {rule.id} - {rule.name}")
        return rule.id
    
    def update_rule(self, rule: AlertTriggerRule) -> bool:
        """更新规则"""
        if rule.id not in self._rules:
            return False
        rule.updated_at = datetime.now()
        self._rules[rule.id] = rule
        logger.info(f"Updated trigger rule: {rule.id} - {rule.name}")
        return True
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除规则"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"Deleted trigger rule: {rule_id}")
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[AlertTriggerRule]:
        """获取规则"""
        return self._rules.get(rule_id)
    
    def list_rules(self, enabled_only: bool = False) -> List[AlertTriggerRule]:
        """列出规则"""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules
    
    # ============== 条件评估 ==============
    
    def evaluate_threshold(self, metric: str, value: float, operator: str, threshold: float) -> bool:
        """评估阈值条件"""
        operators = {
            ">": lambda v, t: v > t,
            "<": lambda v, t: v < t,
            ">=": lambda v, t: v >= t,
            "<=": lambda v, t: v <= t,
            "==": lambda v, t: v == t,
            "!=": lambda v, t: v != t,
        }
        op_func = operators.get(operator, operators[">"])
        return op_func(value, threshold)
    
    def evaluate_change(self, value: float, previous_value: float, change_percent: float) -> bool:
        """评估变化条件"""
        if previous_value == 0:
            return value > 0
        change = abs((value - previous_value) / previous_value * 100)
        return change >= change_percent
    
    def evaluate_rate(self, value: float, previous_value: float, rate_percent: float) -> bool:
        """评估速率条件"""
        if previous_value == 0:
            return value != 0
        rate = (value - previous_value) / previous_value * 100
        return abs(rate) >= rate_percent
    
    def evaluate_constant(self, duration: int, start_time: datetime) -> bool:
        """评估持续条件"""
        elapsed = (datetime.now() - start_time).total_seconds()
        return elapsed >= duration
    
    def evaluate_expression(self, expression: str, context: Dict[str, Any]) -> bool:
        """评估表达式条件"""
        try:
            # 安全评估：替换变量
            safe_expr = expression
            for key, val in context.items():
                if isinstance(val, (int, float)):
                    safe_expr = safe_expr.replace(f"{{{key}}}", str(val))
                    safe_expr = safe_expr.replace(f"${{{key}}}", str(val))
            
            # 使用 eval 计算表达式（受信任的表达式）
            result = eval(safe_expr, {"__builtins__": {}}, {})
            return bool(result)
        except Exception as e:
            logger.warning(f"Expression evaluation error: {e}, expression: {expression}")
            return False
    
    def evaluate_condition(self, rule: AlertTriggerRule, metric_data: Dict[str, Any]) -> bool:
        """
        评估规则条件
        
        Args:
            rule: 触发规则
            metric_data: 指标数据，包含 value, previous_value, duration 等
            
        Returns:
            bool: 是否满足条件
        """
        condition = rule.condition
        
        if condition.condition_type == "threshold":
            return self.evaluate_threshold(
                condition.metric_name,
                metric_data.get("value", 0),
                condition.operator,
                condition.threshold_value
            )
        
        elif condition.condition_type == "change":
            return self.evaluate_change(
                metric_data.get("value", 0),
                metric_data.get("previous_value", 0),
                condition.change_percent
            )
        
        elif condition.condition_type == "rate":
            return self.evaluate_rate(
                metric_data.get("value", 0),
                metric_data.get("previous_value", 0),
                condition.rate_percent
            )
        
        elif condition.condition_type == "constant":
            return self.evaluate_constant(
                condition.duration_seconds,
                metric_data.get("start_time", datetime.now())
            )
        
        elif condition.condition_type == "expression":
            return self.evaluate_expression(
                condition.expression,
                {
                    "value": metric_data.get("value", 0),
                    "previous_value": metric_data.get("previous_value", 0),
                    "metric": condition.metric_name,
                    **metric_data
                }
            )
        
        return False
    
    # ============== 触发管理 ==============
    
    def _should_trigger(self, rule: AlertTriggerRule, device_id: int, metric_name: str) -> bool:
        """检查是否应该触发"""
        # 检查启用状态
        if not rule.enabled:
            return False
        
        # 检查设备过滤
        if rule.device_ids and device_id not in rule.device_ids:
            return False
        
        # 检查触发间隔
        last_time = self._last_trigger_time.get(rule.id)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < rule.trigger_interval:
                logger.debug(f"Rule {rule.id} triggered too recently, skipping")
                return False
        
        # 检查抑制
        if rule.suppress_enabled and rule.suppress_key:
            suppress_time = self._suppressed_keys.get(rule.suppress_key)
            if suppress_time:
                elapsed = (datetime.now() - suppress_time).total_seconds()
                if elapsed < rule.suppress_duration:
                    logger.debug(f"Rule {rule.id} suppressed, skipping")
                    return False
        
        # 检查时间窗口
        if rule.time_windows:
            now = datetime.now()
            in_window = False
            for window in rule.time_windows:
                days = window.get("days", [0, 1, 2, 3, 4, 5, 6])
                start_hour = window.get("start_hour", 0)
                end_hour = window.get("end_hour", 23)
                
                if now.weekday() in days and start_hour <= now.hour < end_hour:
                    in_window = True
                    break
            if not in_window:
                logger.debug(f"Rule {rule.id} not in time window, skipping")
                return False
        
        return True
    
    def _add_suppress(self, rule: AlertTriggerRule, device_id: int, metric_name: str):
        """添加抑制"""
        if rule.suppress_enabled and rule.suppress_key:
            self._suppressed_keys[rule.suppress_key] = datetime.now()
    
    async def evaluate_and_trigger(
        self,
        metric_name: str,
        value: float,
        device_id: int,
        device_name: str = "",
        device_ip: str = "",
        previous_value: Optional[float] = None,
        **extra_data
    ) -> List[TriggerEvent]:
        """
        评估指标并触发规则
        
        Args:
            metric_name: 指标名称
            value: 当前值
            device_id: 设备ID
            device_name: 设备名称
            device_ip: 设备IP
            previous_value: 上一个值
            **extra_data: 额外数据
            
        Returns:
            List[TriggerEvent]: 触发的事件列表
        """
        triggered_events = []
        
        for rule in self.list_rules(enabled_only=True):
            # 检查指标名称匹配
            if rule.condition.metric_name and rule.condition.metric_name != metric_name:
                continue
            
            # 检查是否应该触发
            if not self._should_trigger(rule, device_id, metric_name):
                continue
            
            # 准备评估数据
            metric_data = {
                "value": value,
                "previous_value": previous_value or value,
                "metric": metric_name,
                "device_id": device_id,
                "device_name": device_name,
                "device_ip": device_ip,
                "start_time": datetime.now() - timedelta(seconds=rule.condition.duration_seconds),
                **extra_data
            }
            
            # 评估条件
            if self.evaluate_condition(rule, metric_data):
                logger.info(f"Rule {rule.id} triggered by metric {metric_name}={value}")
                
                # 创建触发事件
                event = TriggerEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    rule_id=rule.id,
                    rule_name=rule.name,
                    trigger_time=datetime.now(),
                    metric_name=metric_name,
                    metric_value=value,
                    threshold_value=rule.condition.threshold_value,
                    device_id=device_id,
                    device_name=device_name,
                    device_ip=device_ip,
                )
                
                # 更新规则统计
                rule.trigger_count += 1
                rule.last_triggered_at = datetime.now()
                self._last_trigger_time[rule.id] = datetime.now()
                
                # 添加抑制
                self._add_suppress(rule, device_id, metric_name)
                
                # 执行动作
                event = await self._execute_actions(rule, event)
                
                self._events[event.id] = event
                triggered_events.append(event)
        
        return triggered_events
    
    async def _execute_actions(self, rule: AlertTriggerRule, event: TriggerEvent) -> TriggerEvent:
        """执行规则动作"""
        event.status = "running"
        execution_results = []
        
        for action in rule.actions:
            if not action.enabled:
                continue
            
            try:
                if action.action_type == ActionType.SCRIPT:
                    result = await self._execute_script_action(action, event)
                    execution_results.append(result)
                    event.actions_executed.append(f"script:{action.script_name or 'unnamed'}")
                    
                elif action.action_type == ActionType.WORKORDER:
                    result = await self._execute_workorder_action(action, event)
                    execution_results.append(result)
                    event.actions_executed.append(f"workorder:{action.workorder_title_template or 'unnamed'}")
                    
                elif action.action_type == ActionType.NOTIFICATION:
                    result = await self._execute_notification_action(action, event)
                    execution_results.append(result)
                    event.actions_executed.append(f"notification:{','.join(action.notification_channels)}")
                    
            except Exception as e:
                logger.error(f"Action execution error: {e}")
                execution_results.append({
                    "action_type": action.action_type.value if isinstance(action.action_type, ActionType) else action.action_type,
                    "status": "failed",
                    "error": str(e)
                })
        
        event.execution_results = execution_results
        
        # 判断整体状态
        if all(r.get("status") == "success" for r in execution_results):
            event.status = "success"
        elif all(r.get("status") in ("failed", "skipped") for r in execution_results):
            event.status = "failed"
        else:
            event.status = "partial"
        
        return event
    
    async def _execute_script_action(self, action: ActionConfig, event: TriggerEvent) -> Dict[str, Any]:
        """执行脚本动作"""
        from modules.automation.script_executor import ScriptExecutor, ScriptType
        
        executor = ScriptExecutor()
        
        # 准备脚本参数
        params = {
            "rule_id": event.rule_id,
            "rule_name": event.rule_name,
            "metric_name": event.metric_name,
            "metric_value": event.metric_value,
            "threshold_value": event.threshold_value,
            "device_id": event.device_id,
            "device_name": event.device_name,
            "device_ip": event.device_ip,
            **action.script_params
        }
        
        script_content = action.script_content or f"#!/bin/bash\necho 'Alert triggered: {event.rule_name}'"
        
        try:
            result = executor.execute(
                script=script_content,
                script_type=ScriptType.SHELL,
                parameters=params,
                timeout=300
            )
            
            return {
                "action_type": "script",
                "script_name": action.script_name,
                "status": "success" if result.status.value == "success" else "failed",
                "return_code": result.return_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except Exception as e:
            return {
                "action_type": "script",
                "script_name": action.script_name,
                "status": "failed",
                "error": str(e)
            }
    
    async def _execute_workorder_action(self, action: ActionConfig, event: TriggerEvent) -> Dict[str, Any]:
        """执行工单创建动作"""
        try:
            from api.dependencies import get_db
            from modules.business.workorder.workorder import WorkOrderCore
            from modules.foundation.db_models.workorder import WorkOrderType, WorkOrderPriority
            
            # 获取数据库会话
            db = next(get_db())
            
            # 渲染模板
            title = self._render_template(
                action.workorder_title_template or "告警触发工单: {rule_name}",
                event
            )
            description = self._render_template(
                action.workorder_description_template or "告警触发自动创建\\n规则: {rule_name}\\n指标: {metric_name}\\n值: {metric_value}",
                event
            )
            
            # 映射工单类型和优先级
            type_mapping = {
                "fault": WorkOrderType.FAULT,
                "change": WorkOrderType.CHANGE,
                "inspection": WorkOrderType.INSPECTION,
                "security": WorkOrderType.SECURITY,
            }
            priority_mapping = {
                "P1": WorkOrderPriority.P1,
                "P2": WorkOrderPriority.P2,
                "P3": WorkOrderPriority.P3,
                "P4": WorkOrderPriority.P4,
            }
            
            core = WorkOrderCore(db)
            wo = core.create(
                title=title,
                order_type=type_mapping.get(action.workorder_type, WorkOrderType.FAULT),
                priority=priority_mapping.get(action.workorder_priority, WorkOrderPriority.P2),
                creator="system",
                description=description,
                device_id=event.device_id,
                device_name=event.device_name,
                device_ip=event.device_ip,
                alert_id=None,
            )
            
            return {
                "action_type": "workorder",
                "workorder_id": wo.id,
                "workorder_no": wo.order_no,
                "status": "success",
            }
        except Exception as e:
            logger.error(f"WorkOrder creation error: {e}")
            return {
                "action_type": "workorder",
                "status": "failed",
                "error": str(e)
            }
    
    async def _execute_notification_action(self, action: ActionConfig, event: TriggerEvent) -> Dict[str, Any]:
        """执行通知动作"""
        try:
            from modules.business.notification.notification_service import NotificationService
            
            service = NotificationService()
            
            # 渲染通知模板
            content = self._render_template(
                action.notification_template or "告警触发: {rule_name}\\n指标: {metric_name}\\n值: {metric_value}",
                event
            )
            
            # 发送通知
            results = []
            for channel in action.notification_channels:
                try:
                    await service.send(
                        channel=channel,
                        receivers=action.notification_receivers,
                        title=f"告警触发: {event.rule_name}",
                        content=content
                    )
                    results.append({"channel": channel, "status": "success"})
                except Exception as e:
                    results.append({"channel": channel, "status": "failed", "error": str(e)})
            
            return {
                "action_type": "notification",
                "results": results,
                "status": "success" if all(r.get("status") == "success" for r in results) else "partial",
            }
        except Exception as e:
            logger.error(f"Notification error: {e}")
            return {
                "action_type": "notification",
                "status": "failed",
                "error": str(e)
            }
    
    def _render_template(self, template: str, event: TriggerEvent) -> str:
        """渲染模板"""
        replacements = {
            "{rule_id}": event.rule_id,
            "{rule_name}": event.rule_name,
            "{metric_name}": event.metric_name,
            "{metric_value}": str(event.metric_value),
            "{threshold_value}": str(event.threshold_value),
            "{device_id}": str(event.device_id or ""),
            "{device_name}": event.device_name or "",
            "{device_ip}": event.device_ip or "",
            "{trigger_time}": event.trigger_time.isoformat() if event.trigger_time else "",
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        return result
    
    # ============== 事件管理 ==============
    
    def list_events(self, rule_id: Optional[str] = None, limit: int = 100) -> List[TriggerEvent]:
        """列出触发事件"""
        events = list(self._events.values())
        
        if rule_id:
            events = [e for e in events if e.rule_id == rule_id]
        
        # 按时间倒序
        events.sort(key=lambda e: e.trigger_time, reverse=True)
        
        return events[:limit]
    
    def clear_old_events(self, hours: int = 24):
        """清理旧事件"""
        cutoff = datetime.now() - timedelta(hours=hours)
        to_remove = [
            eid for eid, event in self._events.items()
            if event.trigger_time < cutoff
        ]
        for eid in to_remove:
            del self._events[eid]
        logger.info(f"Cleared {len(to_remove)} old trigger events")
    
    def get_event(self, event_id: str) -> Optional[TriggerEvent]:
        """获取事件"""
        return self._events.get(event_id)


# 全局实例
_trigger_engine: Optional[AlertTriggerEngine] = None


def get_trigger_engine() -> AlertTriggerEngine:
    """获取触发引擎实例"""
    global _trigger_engine
    if _trigger_engine is None:
        _trigger_engine = AlertTriggerEngine()
    return _trigger_engine


def set_trigger_engine(engine: AlertTriggerEngine):
    """设置触发引擎实例（用于测试）"""
    global _trigger_engine
    _trigger_engine = engine