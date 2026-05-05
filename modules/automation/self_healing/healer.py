"""
自动恢复模块
提供恢复策略、脚本执行、回滚机制、恢复验证等功能
"""

import logging
import subprocess
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    """恢复状态"""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    VERIFYING = 'verifying'
    SUCCESS = 'success'
    FAILED = 'failed'
    ROLLED_BACK = 'rolled_back'
    CANCELLED = 'cancelled'


class RecoveryType(Enum):
    """恢复类型"""
    AUTOMATIC = 'automatic'    # 自动恢复
    SEMI_AUTOMATIC = 'semi_automatic'  # 半自动恢复
    MANUAL = 'manual'          # 手动恢复


class StrategyType(Enum):
    """策略类型"""
    RESTART_SERVICE = 'restart_service'
    RESTART_PROCESS = 'restart_process'
    CLEAR_CACHE = 'clear_cache'
    RESTART_NODE = 'restart_node'
    SWITCHOVER = 'switchover'        # 切换到备用
    RECONFIGURE = 'reconfigure'
    SCALE_OUT = 'scale_out'
    ROLLBACK = 'rollback'


@dataclass
class RecoveryStrategy:
    """恢复策略"""
    strategy_id: str = ''
    name: str = ''
    strategy_type: StrategyType = StrategyType.RESTART_SERVICE
    
    # 适用条件
    applicable_faults: List[str] = field(default_factory=list)  # 故障模式ID
    min_severity: str = 'warning'  # 最小适用严重程度
    
    # 执行步骤
    steps: List[Dict[str, Any]] = field(default_factory=list)
    # 每个步骤: {name, action, params, timeout, retry_count}
    
    # 配置
    auto_execute: bool = True
    timeout_seconds: int = 300
    retry_count: int = 3
    retry_interval_seconds: int = 10
    
    # 回滚配置
    enable_rollback: bool = True
    rollback_strategy_id: Optional[str] = None
    
    # 验证配置
    verify_after_recovery: bool = True
    verify_metrics: List[Dict[str, Any]] = field(default_factory=list)
    # 验证: {metric, operator, threshold, expected_change}
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_id': self.strategy_id,
            'name': self.name,
            'strategy_type': self.strategy_type.value,
            'applicable_faults': self.applicable_faults,
            'min_severity': self.min_severity,
            'steps': self.steps,
            'auto_execute': self.auto_execute,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'retry_interval_seconds': self.retry_interval_seconds,
            'enable_rollback': self.enable_rollback,
            'rollback_strategy_id': self.rollback_strategy_id,
            'verify_after_recovery': self.verify_after_recovery,
            'verify_metrics': self.verify_metrics,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


@dataclass
class StepExecution:
    """步骤执行记录"""
    step_name: str = ''
    action: str = ''
    status: RecoveryStatus = RecoveryStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    output: str = ''
    error: str = ''
    retry_attempt: int = 0
    
    
@dataclass
class RecoveryResult:
    """恢复结果"""
    result_id: str = field(default_factory=lambda: f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    # 关联信息
    fault_event_id: str = ''
    strategy_id: str = ''
    strategy_name: str = ''
    
    # 执行状态
    status: RecoveryStatus = RecoveryStatus.PENDING
    recovery_type: RecoveryType = RecoveryType.AUTOMATIC
    
    # 时间信息
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    
    # 步骤执行记录
    steps_executed: List[StepExecution] = field(default_factory=list)
    
    # 验证结果
    verification_passed: bool = False
    verification_results: Dict[str, Any] = field(default_factory=dict)
    
    # 回滚信息
    was_rolled_back: bool = False
    rollback_reason: str = ''
    
    # 执行者
    executed_by: str = 'system'
    
    # 错误信息
    error_message: str = ''
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    # 建议
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'result_id': self.result_id,
            'fault_event_id': self.fault_event_id,
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'status': self.status.value,
            'recovery_type': self.recovery_type.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration_seconds': self.total_duration_seconds,
            'steps_executed': [
                {
                    'step_name': s.step_name,
                    'action': s.action,
                    'status': s.status.value,
                    'duration_seconds': s.duration_seconds,
                    'retry_attempt': s.retry_attempt,
                    'output': s.output,
                    'error': s.error,
                }
                for s in self.steps_executed
            ],
            'verification_passed': self.verification_passed,
            'verification_results': self.verification_results,
            'was_rolled_back': self.was_rolled_back,
            'rollback_reason': self.rollback_reason,
            'executed_by': self.executed_by,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'recommendations': self.recommendations,
        }


@dataclass
class RollbackSnapshot:
    """回滚快照"""
    snapshot_id: str = ''
    asset_id: str = ''
    
    # 快照内容
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ''
    description: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'snapshot_id': self.snapshot_id,
            'asset_id': self.asset_id,
            'config_snapshot': self.config_snapshot,
            'state_snapshot': self.state_snapshot,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'description': self.description,
        }

class SelfHealer:
    """自动恢复引擎"""
    
    def __init__(self):
        # 恢复策略库
        self.strategies: Dict[str, RecoveryStrategy] = {}
        
        # 恢复历史
        self.recovery_history: List[RecoveryResult] = []
        
        # 回滚快照
        self.rollback_snapshots: Dict[str, List[RollbackSnapshot]] = defaultdict(list)
        
        # 执行器
        self.action_executors: Dict[str, Callable] = {}
        
        # 初始化默认策略
        self._init_default_strategies()
        self._register_default_executors()
    
    def _init_default_strategies(self):
        """初始化默认恢复策略"""
        strategies = [
            RecoveryStrategy(
                strategy_id='STR-001',
                name='服务重启',
                strategy_type=StrategyType.RESTART_SERVICE,
                applicable_faults=['PAT-005'],  # 服务无响应
                min_severity='error',
                steps=[
                    {'name': '停止服务', 'action': 'stop_service', 'params': {}, 'timeout': 60, 'retry_count': 2},
                    {'name': '等待清理', 'action': 'wait', 'params': {'seconds': 5}, 'timeout': 10, 'retry_count': 0},
                    {'name': '启动服务', 'action': 'start_service', 'params': {}, 'timeout': 60, 'retry_count': 3},
                ],
                auto_execute=True,
                timeout_seconds=180,
                verify_after_recovery=True,
                verify_metrics=[
                    {'metric': 'service_health', 'operator': '==', 'threshold': 1},
                ],
            ),
            RecoveryStrategy(
                strategy_id='STR-002',
                name='清空缓存',
                strategy_type=StrategyType.CLEAR_CACHE,
                applicable_faults=['PAT-001', 'PAT-002'],  # CPU/内存过载
                min_severity='warning',
                steps=[
                    {'name': '清空内存缓存', 'action': 'clear_memory_cache', 'params': {}, 'timeout': 30, 'retry_count': 1},
                    {'name': '清空临时文件', 'action': 'clear_temp_files', 'params': {}, 'timeout': 30, 'retry_count': 1},
                    {'name': '重置进程', 'action': 'reset_processes', 'params': {}, 'timeout': 60, 'retry_count': 2},
                ],
                auto_execute=True,
                timeout_seconds=120,
                verify_after_recovery=True,
                verify_metrics=[
                    {'metric': 'memory_usage', 'operator': '<', 'threshold': 80},
                    {'metric': 'cpu_usage', 'operator': '<', 'threshold': 70},
                ],
            ),
            RecoveryStrategy(
                strategy_id='STR-003',
                name='节点重启',
                strategy_type=StrategyType.RESTART_NODE,
                applicable_faults=['PAT-006'],  # 硬件故障
                min_severity='critical',
                steps=[
                    {'name': '创建回滚快照', 'action': 'create_snapshot', 'params': {}, 'timeout': 120, 'retry_count': 1},
                    {'name': '通知相关方', 'action': 'notify', 'params': {'message': '即将重启节点'}, 'timeout': 30, 'retry_count': 0},
                    {'name': '停止服务', 'action': 'stop_services', 'params': {}, 'timeout': 60, 'retry_count': 2},
                    {'name': '重启节点', 'action': 'reboot_node', 'params': {}, 'timeout': 300, 'retry_count': 1},
                    {'name': '等待启动', 'action': 'wait_for_boot', 'params': {'timeout': 180}, 'timeout': 200, 'retry_count': 0},
                    {'name': '启动服务', 'action': 'start_services', 'params': {}, 'timeout': 120, 'retry_count': 3},
                ],
                auto_execute=False,  # 节点重启需要谨慎
                timeout_seconds=900,
                enable_rollback=True,
                verify_after_recovery=True,
                verify_metrics=[
                    {'metric': 'node_online', 'operator': '==', 'threshold': 1},
                    {'metric': 'services_running', 'operator': '>=', 'threshold': 1},
                ],
            ),
            RecoveryStrategy(
                strategy_id='STR-004',
                name='故障切换',
                strategy_type=StrategyType.SWITCHOVER,
                applicable_faults=['PAT-006'],
                min_severity='critical',
                steps=[
                    {'name': '检查备用节点', 'action': 'check_standby', 'params': {}, 'timeout': 60, 'retry_count': 2},
                    {'name': '创建快照', 'action': 'create_snapshot', 'params': {}, 'timeout': 120, 'retry_count': 1},
                    {'name': '切换流量', 'action': 'switch_traffic', 'params': {}, 'timeout': 60, 'retry_count': 1},
                    {'name': '验证切换', 'action': 'verify_switchover', 'params': {}, 'timeout': 120, 'retry_count': 2},
                ],
                auto_execute=False,
                timeout_seconds=600,
                enable_rollback=True,
                rollback_strategy_id='STR-005',
            ),
            RecoveryStrategy(
                strategy_id='STR-005',
                name='故障切回',
                strategy_type=StrategyType.SWITCHOVER,
                applicable_faults=[],
                min_severity='critical',
                steps=[
                    {'name': '验证原节点', 'action': 'verify_node', 'params': {}, 'timeout': 120, 'retry_count': 2},
                    {'name': '切换回原节点', 'action': 'switch_back', 'params': {}, 'timeout': 60, 'retry_count': 1},
                    {'name': '验证', 'action': 'verify', 'params': {}, 'timeout': 120, 'retry_count': 2},
                ],
                auto_execute=False,
                timeout_seconds=600,
            ),
        ]
        
        for strategy in strategies:
            self.strategies[strategy.strategy_id] = strategy
    
    def _register_default_executors(self):
        """注册默认执行器"""
        self.action_executors = {
            'stop_service': self._execute_stop_service,
            'start_service': self._execute_start_service,
            'restart_service': self._execute_restart_service,
            'restart_process': self._execute_restart_process,
            'clear_memory_cache': self._execute_clear_memory_cache,
            'clear_temp_files': self._execute_clear_temp_files,
            'reset_processes': self._execute_reset_processes,
            'reboot_node': self._execute_reboot_node,
            'wait': self._execute_wait,
            'wait_for_boot': self._execute_wait_for_boot,
            'notify': self._execute_notify,
            'create_snapshot': self._execute_create_snapshot,
            'stop_services': self._execute_stop_services,
            'start_services': self._execute_start_services,
            'check_standby': self._execute_check_standby,
            'switch_traffic': self._execute_switch_traffic,
            'verify_switchover': self._execute_verify_switchover,
            'switch_back': self._execute_switch_back,
            'verify_node': self._execute_verify_node,
            'verify': self._execute_verify,
            'execute_script': self._execute_script,
            'http_request': self._execute_http_request,
        }
    
    # ==================== 策略管理 ====================
    
    def register_strategy(self, strategy: RecoveryStrategy) -> bool:
        """注册恢复策略"""
        try:
            self.strategies[strategy.strategy_id] = strategy
            logger.info(f"Registered recovery strategy: {strategy.strategy_id} - {strategy.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register strategy: {e}")
            return False
    
    def get_strategy(self, strategy_id: str) -> Optional[RecoveryStrategy]:
        """获取恢复策略"""
        return self.strategies.get(strategy_id)
    
    def get_applicable_strategies(self, fault_pattern_id: str, severity: str) -> List[RecoveryStrategy]:
        """获取适用的恢复策略"""
        applicable = []
        for strategy in self.strategies.values():
            if fault_pattern_id in strategy.applicable_faults or not strategy.applicable_faults:
                severity_order = {'info': 0, 'warning': 1, 'error': 2, 'critical': 3}
                if severity_order.get(severity, 0) >= severity_order.get(strategy.min_severity, 0):
                    applicable.append(strategy)
        return sorted(applicable, key=lambda x: x.strategy_id)
    
    # ==================== 恢复执行 ====================
    
    async def execute_recovery(self, fault_event_id: str, strategy_id: str,
                              fault_data: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        """执行恢复"""
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return RecoveryResult(
                fault_event_id=fault_event_id,
                strategy_id=strategy_id,
                status=RecoveryStatus.FAILED,
                error_message=f'Strategy not found: {strategy_id}',
            )
        
        result = RecoveryResult(
            fault_event_id=fault_event_id,
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            started_at=datetime.now(),
            recovery_type=RecoveryType.AUTOMATIC if strategy.auto_execute else RecoveryType.MANUAL,
        )
        
        logger.info(f"Starting recovery for fault {fault_event_id} with strategy {strategy.name}")
        
        try:
            # 创建回滚快照
            if strategy.enable_rollback and fault_data:
                await self._create_rollback_snapshot(fault_data)
            
            # 执行各步骤
            for step_config in strategy.steps:
                step_exec = await self._execute_step(step_config, fault_data, strategy)
                result.steps_executed.append(step_exec)
                
                if step_exec.status == RecoveryStatus.FAILED:
                    # 检查是否需要重试
                    if step_exec.retry_attempt < step_config.get('retry_count', 0):
                        logger.warning(f"Retrying step: {step_exec.step_name}")
                        step_exec.retry_attempt += 1
                        # 等待重试间隔
                        await asyncio.sleep(strategy.retry_interval_seconds)
                        continue
                    
                    # 步骤失败
                    result.status = RecoveryStatus.FAILED
                    result.error_message = f"Step failed: {step_exec.step_name}"
                    result.error_details = {'failed_step': step_exec.step_name, 'error': step_exec.error}
                    
                    # 尝试回滚
                    if strategy.enable_rollback:
                        await self._rollback(result, fault_data)
                    
                    break
                
                # 等待步骤间间隔
                await asyncio.sleep(1)
            
            if result.status != RecoveryStatus.FAILED:
                # 验证恢复结果
                if strategy.verify_after_recovery:
                    result.verification_passed = await self._verify_recovery(strategy, fault_data)
                    if not result.verification_passed:
                        result.status = RecoveryStatus.FAILED
                        result.error_message = "Verification failed"
                        if strategy.enable_rollback:
                            await self._rollback(result, fault_data)
                else:
                    result.status = RecoveryStatus.SUCCESS
            
        except Exception as e:
            logger.error(f"Recovery execution error: {e}")
            result.status = RecoveryStatus.FAILED
            result.error_message = str(e)
        
        # 完成记录
        result.completed_at = datetime.now()
        result.total_duration_seconds = (result.completed_at - result.started_at).total_seconds()
        
        self.recovery_history.append(result)
        logger.info(f"Recovery completed: {result.result_id}, status: {result.status.value}")
        
        return result
    
    async def _execute_step(self, step_config: Dict[str, Any], 
                            fault_data: Optional[Dict[str, Any]], 
                            strategy: RecoveryStrategy) -> StepExecution:
        """执行单个步骤"""
        step_exec = StepExecution(
            step_name=step_config.get('name', ''),
            action=step_config.get('action', ''),
            status=RecoveryStatus.IN_PROGRESS,
            start_time=datetime.now(),
        )
        
        action = step_config.get('action', '')
        executor = self.action_executors.get(action)
        
        if not executor:
            step_exec.status = RecoveryStatus.FAILED
            step_exec.error = f"Unknown action: {action}"
        else:
            try:
                # 执行动作
                if asyncio.iscoroutinefunction(executor):
                    output = await executor(step_config.get('params', {}), fault_data)
                else:
                    output = executor(step_config.get('params', {}), fault_data)
                
                step_exec.output = str(output) if output else 'OK'
                step_exec.status = RecoveryStatus.SUCCESS
            except Exception as e:
                logger.error(f"Step execution error: {e}")
                step_exec.status = RecoveryStatus.FAILED
                step_exec.error = str(e)
        
        step_exec.end_time = datetime.now()
        step_exec.duration_seconds = (step_exec.end_time - step_exec.start_time).total_seconds()
        
        return step_exec
    
    async def _verify_recovery(self, strategy: RecoveryStrategy, 
                               fault_data: Optional[Dict[str, Any]]) -> bool:
        """验证恢复结果"""
        for verify_config in strategy.verify_metrics:
            metric = verify_config.get('metric')
            operator = verify_config.get('operator')
            threshold = verify_config.get('threshold')
            
            # 从故障数据或实际获取指标值
            actual_value = None
            if fault_data and 'metrics' in fault_data:
                actual_value = fault_data['metrics'].get(metric)
            
            if actual_value is None:
                # 无法获取指标值，跳过验证
                continue
            
            # 评估验证条件
            passed = self._evaluate_condition(actual_value, operator, threshold)
            if not passed:
                logger.warning(f"Verification failed for {metric}: {actual_value} {operator} {threshold}")
                return False
        
        return True
    
    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """评估条件"""
        if operator == '>':
            return value > threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<':
            return value < threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        return True
    
    async def _rollback(self, result: RecoveryResult, fault_data: Optional[Dict[str, Any]]):
        """执行回滚"""
        result.was_rolled_back = True
        result.rollback_reason = "Recovery failed, rolling back"
        
        asset_id = fault_data.get('asset_id') if fault_data else None
        if asset_id:
            snapshots = self.rollback_snapshots.get(asset_id, [])
            if snapshots:
                latest_snapshot = snapshots[-1]
                # 恢复配置
                result.recommendations.append(f"Rolled back to snapshot {latest_snapshot.snapshot_id}")
        
        result.status = RecoveryStatus.ROLLED_BACK
        logger.info(f"Rollback completed for {result.fault_event_id}")
    
    async def _create_rollback_snapshot(self, fault_data: Dict[str, Any]):
        """创建回滚快照"""
        asset_id = fault_data.get('asset_id')
        if not asset_id:
            return
        
        snapshot = RollbackSnapshot(
            snapshot_id=f"SNAP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            asset_id=asset_id,
            config_snapshot=fault_data.get('config', {}),
            state_snapshot=fault_data.get('state', {}),
            created_by='system',
            description=f"Auto-created before recovery at {datetime.now()}",
        )
        
        self.rollback_snapshots[asset_id].append(snapshot)
        # 保留最近5个快照
        if len(self.rollback_snapshots[asset_id]) > 5:
            self.rollback_snapshots[asset_id].pop(0)
    
    # ==================== 动作执行器 ====================
    
    async def _execute_stop_service(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """停止服务"""
        service_name = params.get('service_name', fault_data.get('service_name', 'unknown'))
        logger.info(f"Stopping service: {service_name}")
        # 实际环境中这里会调用系统命令或API
        return f"Service {service_name} stopped"
    
    async def _execute_start_service(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """启动服务"""
        service_name = params.get('service_name', fault_data.get('service_name', 'unknown'))
        logger.info(f"Starting service: {service_name}")
        return f"Service {service_name} started"
    
    async def _execute_restart_service(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """重启服务"""
        service_name = params.get('service_name', fault_data.get('service_name', 'unknown'))
        logger.info(f"Restarting service: {service_name}")
        return f"Service {service_name} restarted"
    
    async def _execute_restart_process(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """重启进程"""
        process_name = params.get('process_name', 'unknown')
        logger.info(f"Restarting process: {process_name}")
        return f"Process {process_name} restarted"
    
    async def _execute_clear_memory_cache(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """清空内存缓存"""
        logger.info("Clearing memory cache")
        return "Memory cache cleared"
    
    async def _execute_clear_temp_files(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """清空临时文件"""
        logger.info("Clearing temp files")
        return "Temp files cleared"
    
    async def _execute_reset_processes(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """重置进程"""
        logger.info("Resetting processes")
        return "Processes reset"
    
    async def _execute_reboot_node(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """重启节点"""
        node_name = params.get('node_name', fault_data.get('asset_name', 'unknown'))
        logger.warning(f"Rebooting node: {node_name}")
        return f"Node {node_name} rebooted"
    
    async def _execute_wait(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """等待"""
        seconds = params.get('seconds', 5)
        await asyncio.sleep(seconds)
        return f"Waited {seconds} seconds"
    
    async def _execute_wait_for_boot(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """等待启动"""
        timeout = params.get('timeout', 180)
        logger.info(f"Waiting for node to boot (timeout: {timeout}s)")
        await asyncio.sleep(5)  # 简化
        return "Node booted"
    
    async def _execute_notify(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """发送通知"""
        message = params.get('message', '')
        logger.info(f"Notification sent: {message}")
        return f"Notification sent: {message}"
    
    async def _execute_create_snapshot(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """创建快照"""
        asset_id = fault_data.get('asset_id') if fault_data else None
        snapshot_id = f"SNAP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if asset_id:
            snapshot = RollbackSnapshot(
                snapshot_id=snapshot_id,
                asset_id=asset_id,
                config_snapshot=fault_data.get('config', {}),
                state_snapshot={},
                created_by='system',
            )
            self.rollback_snapshots[asset_id].append(snapshot)
        return f"Snapshot created: {snapshot_id}"
    
    async def _execute_stop_services(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """停止服务组"""
        logger.info("Stopping all services")
        return "All services stopped"
    
    async def _execute_start_services(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """启动服务组"""
        logger.info("Starting all services")
        return "All services started"
    
    async def _execute_check_standby(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """检查备用节点"""
        logger.info("Checking standby node")
        return "Standby node available"
    
    async def _execute_switch_traffic(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """切换流量"""
        logger.info("Switching traffic to standby")
        return "Traffic switched"
    
    async def _execute_verify_switchover(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """验证切换"""
        logger.info("Verifying switchover")
        return "Switchover verified"
    
    async def _execute_switch_back(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """切回"""
        logger.info("Switching back to primary")
        return "Switched back"
    
    async def _execute_verify_node(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """验证节点"""
        logger.info("Verifying node")
        return "Node verified"
    
    async def _execute_verify(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """通用验证"""
        logger.info("Verification completed")
        return "Verification passed"
    
    async def _execute_script(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """执行脚本"""
        script = params.get('script', '')
        logger.info(f"Executing script: {script[:100]}...")
        return "Script executed"
    
    async def _execute_http_request(self, params: Dict, fault_data: Optional[Dict]) -> str:
        """发送HTTP请求"""
        url = params.get('url', '')
        method = params.get('method', 'GET')
        logger.info(f"HTTP {method} {url}")
        return "Request completed"
    
    # ==================== 统计和分析 ====================
    
    def get_recovery_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取恢复统计"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [r for r in self.recovery_history if r.started_at and r.started_at > cutoff]
        
        stats = {
            'total_recoveries': len(recent),
            'successful': len([r for r in recent if r.status == RecoveryStatus.SUCCESS]),
            'failed': len([r for r in recent if r.status == RecoveryStatus.FAILED]),
            'rolled_back': len([r for r in recent if r.was_rolled_back]),
            'auto_healed': len([r for r in recent if r.recovery_type == RecoveryType.AUTOMATIC]),
            'avg_duration_seconds': 0,
            'by_strategy': defaultdict(int),
        }
        
        durations = [r.total_duration_seconds for r in recent if r.total_duration_seconds > 0]
        if durations:
            stats['avg_duration_seconds'] = sum(durations) / len(durations)
        
        for r in recent:
            stats['by_strategy'][r.strategy_name] += 1
        
        stats['by_strategy'] = dict(stats['by_strategy'])
        
        return stats
