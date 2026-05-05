"""
流程引擎模块
提供流程定义、流程节点、流程路由、流程实例管理、流程历史等功能
"""

import yaml
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from modules.foundation.db_models.base import Base


class FlowNodeType(str, Enum):
    """流程节点类型"""
    START = 'start'           # 开始节点
    END = 'end'               # 结束节点
    TASK = 'task'             # 任务节点
    APPROVAL = 'approval'     # 审批节点
    NOTIFICATION = 'notification'  # 通知节点
    CONDITION = 'condition'   # 条件分支节点
    AUTOMATION = 'automation' # 自动化节点


class ApprovalMode(str, Enum):
    """审批模式"""
    ONE = 'one'              # 或签(任一审批人通过即可)
    ALL = 'all'              # 会签(所有审批人必须全部通过)


@dataclass
class FlowNode:
    """流程节点定义"""
    node_id: str
    name: str
    type: FlowNodeType
    config: Dict[str, Any] = field(default_factory=dict)
    assignee_type: Optional[str] = None  # user, role, department, variable
    assignee_value: Optional[str] = None
    timeout: Optional[int] = None  # 超时时间(分钟)
    auto_execute: bool = False


@dataclass
class FlowCondition:
    """流程条件定义"""
    variable: str
    operator: str  # eq, ne, gt, lt, ge, le, in, contains
    value: Any


@dataclass
class FlowTransition:
    """流程转移定义"""
    from_node: str
    to_node: str
    conditions: List[FlowCondition] = field(default_factory=list)
    condition_type: str = 'AND'  # AND, OR


@dataclass
class FlowDefinition:
    """流程定义"""
    flow_id: str
    name: str
    version: str
    description: Optional[str] = None
    nodes: List[FlowNode] = field(default_factory=list)
    transitions: List[FlowTransition] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    sla_config: Dict[str, Any] = field(default_factory=dict)
    
    def get_node(self, node_id: str) -> Optional[FlowNode]:
        """获取节点"""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None
    
    def get_start_node(self) -> Optional[FlowNode]:
        """获取开始节点"""
        for node in self.nodes:
            if node.type == FlowNodeType.START:
                return node
        return None
    
    def get_end_nodes(self) -> List[FlowNode]:
        """获取结束节点列表"""
        return [n for n in self.nodes if n.type == FlowNodeType.END]
    
    def get_next_nodes(self, current_node_id: str, context: Dict[str, Any]) -> List[FlowNode]:
        """根据条件获取下一节点"""
        next_nodes = []
        
        for transition in self.transitions:
            if transition.from_node != current_node_id:
                continue
            
            # 检查条件
            if self._check_conditions(transition, context):
                node = self.get_node(transition.to_node)
                if node:
                    next_nodes.append(node)
        
        return next_nodes
    
    def _check_conditions(self, transition: FlowTransition, context: Dict[str, Any]) -> bool:
        """检查条件是否满足"""
        if not transition.conditions:
            return True
        
        results = []
        for condition in transition.conditions:
            result = self._evaluate_condition(condition, context)
            results.append(result)
        
        if transition.condition_type == 'AND':
            return all(results)
        else:
            return any(results)
    
    def _evaluate_condition(self, condition: FlowCondition, context: Dict[str, Any]) -> bool:
        """评估条件"""
        actual_value = context.get(condition.variable)
        
        if condition.operator == 'eq':
            return actual_value == condition.value
        elif condition.operator == 'ne':
            return actual_value != condition.value
        elif condition.operator == 'gt':
            return actual_value > condition.value
        elif condition.operator == 'lt':
            return actual_value < condition.value
        elif condition.operator == 'ge':
            return actual_value >= condition.value
        elif condition.operator == 'le':
            return actual_value <= condition.value
        elif condition.operator == 'in':
            return actual_value in condition.value
        elif condition.operator == 'contains':
            return condition.value in str(actual_value)
        
        return False


class FlowInstance(Base):
    """流程实例模型"""
    __tablename__ = 'flow_instances'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(String(64), unique=True, nullable=False, index=True, comment='流程实例ID')
    
    # 关联工单
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), index=True, comment='工单ID')
    
    # 流程定义
    flow_id = Column(String(64), nullable=False, comment='流程定义ID')
    flow_version = Column(String(32), comment='流程版本')
    flow_name = Column(String(128), comment='流程名称')
    
    # 当前节点
    current_node_id = Column(String(64), comment='当前节点ID')
    current_node_name = Column(String(128), comment='当前节点名称')
    
    # 状态
    status = Column(String(32), default='running', comment='状态: running, completed, cancelled')
    
    # 上下文数据
    context_data = Column(Text, comment='上下文数据JSON')
    
    # 时间
    started_at = Column(DateTime, default=datetime.now, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('idx_flow_workorder', 'work_order_id'),
        Index('idx_flow_status', 'status'),
    )
    
    def __repr__(self):
        return f"<FlowInstance(id={self.id}, instance_id='{self.instance_id}')>"


class FlowHistory(Base):
    """流程历史记录模型"""
    __tablename__ = 'flow_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey('flow_instances.id'), index=True, comment='流程实例ID')
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), index=True, comment='工单ID')
    
    node_id = Column(String(64), comment='节点ID')
    node_name = Column(String(128), comment='节点名称')
    node_type = Column(String(32), comment='节点类型')
    
    action = Column(String(32), comment='操作: enter, execute, complete, skip, timeout')
    operator = Column(String(64), comment='操作人')
    
    input_data = Column(Text, comment='输入数据JSON')
    output_data = Column(Text, comment='输出数据JSON')
    
    created_at = Column(DateTime, default=datetime.now, comment='操作时间')
    
    def __repr__(self):
        return f"<FlowHistory(id={self.id}, action='{self.action}')>"


class FlowEngine:
    """
    流程引擎类
    
    管理流程定义、流程实例和流程执行
    """
    
    # 内置流程定义注册表
    _flow_definitions: Dict[str, FlowDefinition] = {}
    
    # 自动化任务处理器
    _automation_handlers: Dict[str, Callable] = {}
    
    def __init__(self, db_session):
        """
        初始化流程引擎
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self._init_builtin_flows()
    
    def _init_builtin_flows(self):
        """初始化内置流程"""
        # 标准工单流程
        standard_flow = FlowDefinition(
            flow_id='standard_workorder',
            name='标准工单流程',
            version='1.0',
            nodes=[
                FlowNode('start', '开始', FlowNodeType.START),
                FlowNode('process', '处理', FlowNodeType.TASK, timeout=480),
                FlowNode('approval', '审批', FlowNodeType.APPROVAL, timeout=1440),
                FlowNode('end', '结束', FlowNodeType.END),
            ],
            transitions=[
                FlowTransition('start', 'process'),
                FlowTransition('process', 'approval'),
                FlowTransition('approval', 'end', conditions=[
                    FlowCondition('approval_result', 'eq', 'approve')
                ]),
                FlowTransition('approval', 'process', conditions=[
                    FlowCondition('approval_result', 'eq', 'reject')
                ]),
            ]
        )
        self._flow_definitions['standard_workorder'] = standard_flow
        
        # 紧急故障流程
        emergency_flow = FlowDefinition(
            flow_id='emergency_fault',
            name='紧急故障处理流程',
            version='1.0',
            nodes=[
                FlowNode('start', '开始', FlowNodeType.START),
                FlowNode('handle', '紧急处理', FlowNodeType.TASK, timeout=60),
                FlowNode('review', '评审', FlowNodeType.APPROVAL, timeout=240),
                FlowNode('end', '结束', FlowNodeType.END),
            ],
            transitions=[
                FlowTransition('start', 'handle'),
                FlowTransition('handle', 'review'),
                FlowTransition('review', 'end'),
            ]
        )
        self._flow_definitions['emergency_fault'] = emergency_flow
        
        # 变更管理流程
        change_flow = FlowDefinition(
            flow_id='change_management',
            name='变更管理流程',
            version='1.0',
            nodes=[
                FlowNode('start', '开始', FlowNodeType.START),
                FlowNode('impact', '影响评估', FlowNodeType.TASK, timeout=1440),
                FlowNode(' CAB ', 'CAB评审', FlowNodeType.APPROVAL, timeout=2880),
                FlowNode('implement', '实施', FlowNodeType.TASK),
                FlowNode('verify', '验证', FlowNodeType.TASK),
                FlowNode('end', '结束', FlowNodeType.END),
            ],
            transitions=[
                FlowTransition('start', 'impact'),
                FlowTransition('impact', 'CAB'),
                FlowTransition('CAB', 'implement', conditions=[
                    FlowCondition('approval_result', 'eq', 'approve')
                ]),
                FlowTransition('implement', 'verify'),
                FlowTransition('verify', 'end'),
            ]
        )
        self._flow_definitions['change_management'] = change_flow
    
    def register_flow(self, flow_def: FlowDefinition):
        """
        注册流程定义
        
        Args:
            flow_def: 流程定义对象
        """
        self._flow_definitions[flow_def.flow_id] = flow_def
    
    def load_flow_from_yaml(self, yaml_path: str) -> FlowDefinition:
        """
        从YAML文件加载流程定义
        
        Args:
            yaml_path: YAML文件路径
            
        Returns:
            流程定义对象
        """
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return self._parse_flow_definition(data)
    
    def load_flow_from_json(self, json_str: str) -> FlowDefinition:
        """
        从JSON字符串加载流程定义
        
        Args:
            json_str: JSON字符串
            
        Returns:
            流程定义对象
        """
        data = json.loads(json_str)
        return self._parse_flow_definition(data)
    
    def _parse_flow_definition(self, data: Dict) -> FlowDefinition:
        """解析流程定义数据"""
        nodes = []
        for node_data in data.get('nodes', []):
            node = FlowNode(
                node_id=node_data['node_id'],
                name=node_data['name'],
                type=FlowNodeType(node_data['type']),
                config=node_data.get('config', {}),
                assignee_type=node_data.get('assignee_type'),
                assignee_value=node_data.get('assignee_value'),
                timeout=node_data.get('timeout'),
                auto_execute=node_data.get('auto_execute', False)
            )
            nodes.append(node)
        
        transitions = []
        for trans_data in data.get('transitions', []):
            conditions = []
            for cond_data in trans_data.get('conditions', []):
                condition = FlowCondition(
                    variable=cond_data['variable'],
                    operator=cond_data['operator'],
                    value=cond_data['value']
                )
                conditions.append(condition)
            
            transition = FlowTransition(
                from_node=trans_data['from'],
                to_node=trans_data['to'],
                conditions=conditions,
                condition_type=trans_data.get('condition_type', 'AND')
            )
            transitions.append(transition)
        
        return FlowDefinition(
            flow_id=data['flow_id'],
            name=data['name'],
            version=data.get('version', '1.0'),
            description=data.get('description'),
            nodes=nodes,
            transitions=transitions,
            variables=data.get('variables', {}),
            sla_config=data.get('sla_config', {})
        )
    
    def get_flow_definition(self, flow_id: str, version: Optional[str] = None) -> Optional[FlowDefinition]:
        """
        获取流程定义
        
        Args:
            flow_id: 流程ID
            version: 版本号
            
        Returns:
            流程定义对象
        """
        return self._flow_definitions.get(flow_id)
    
    def start_flow(
        self,
        work_order_id: int,
        flow_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Optional[FlowInstance]:
        """
        启动流程实例
        
        Args:
            work_order_id: 工单ID
            flow_id: 流程ID
            initial_context: 初始上下文
            
        Returns:
            流程实例对象
        """
        flow_def = self.get_flow_definition(flow_id)
        if not flow_def:
            return None
        
        start_node = flow_def.get_start_node()
        if not start_node:
            return None
        
        # 创建流程实例
        instance = FlowInstance(
            instance_id=f"FLOW-{uuid.uuid4().hex[:12].upper()}",
            work_order_id=work_order_id,
            flow_id=flow_id,
            flow_version=flow_def.version,
            flow_name=flow_def.name,
            current_node_id=start_node.node_id,
            current_node_name=start_node.name,
            status='running',
            context_data=json.dumps(initial_context or {})
        )
        
        self.db.add(instance)
        self.db.flush()
        
        # 记录历史
        self._record_history(
            instance.id,
            work_order_id,
            start_node.node_id,
            start_node.name,
            start_node.type.value,
            'enter',
            None,
            initial_context
        )
        
        self.db.commit()
        return instance
    
    def execute_node(
        self,
        instance_id: int,
        node_id: Optional[str] = None,
        action: str = 'complete',
        operator: str = 'system',
        input_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[FlowInstance]]:
        """
        执行流程节点
        
        Args:
            instance_id: 流程实例ID
            node_id: 节点ID(如果为None则执行当前节点)
            action: 操作类型
            operator: 操作人
            input_data: 输入数据
            
        Returns:
            (是否成功, 消息, 流程实例对象)
        """
        instance = self.db.query(FlowInstance).filter(
            FlowInstance.id == instance_id
        ).first()
        
        if not instance:
            return False, '流程实例不存在', None
        
        if instance.status != 'running':
            return False, f'流程实例状态为{instance.status},不能执行', None
        
        flow_def = self.get_flow_definition(instance.flow_id)
        if not flow_def:
            return False, '流程定义不存在', None
        
        # 确定执行节点
        current_node_id = node_id or instance.current_node_id
        current_node = flow_def.get_node(current_node_id)
        if not current_node:
            return False, f'节点{current_node_id}不存在', None
        
        # 更新上下文
        context = json.loads(instance.context_data or '{}')
        if input_data:
            context.update(input_data)
        
        # 根据节点类型处理
        if current_node.type == FlowNodeType.TASK:
            success, msg = self._execute_task_node(
                instance, current_node, flow_def, context, operator
            )
            if success:
                self.db.commit()
                return True, msg, instance
        
        elif current_node.type == FlowNodeType.APPROVAL:
            self._record_history(
                instance.id,
                instance.work_order_id,
                current_node.node_id,
                current_node.name,
                current_node.type.value,
                action,
                operator,
                input_data,
                output_data={'result': action}
            )
            
            # 更新上下文中的审批结果
            context['approval_result'] = action
            instance.context_data = json.dumps(context)
            self.db.flush()
        
        elif current_node.type == FlowNodeType.NOTIFICATION:
            self._execute_notification_node(current_node, context)
        
        elif current_node.type == FlowNodeType.AUTOMATION:
            self._execute_automation_node(instance, current_node, context)
        
        # 记录节点完成历史
        self._record_history(
            instance.id,
            instance.work_order_id,
            current_node.node_id,
            current_node.name,
            current_node.type.value,
            'complete',
            operator,
            input_data
        )
        
        # 转移到下一节点
        return self._transition_to_next(
            instance, flow_def, context, operator
        )
    
    def _execute_task_node(
        self,
        instance: FlowInstance,
        node: FlowNode,
        flow_def: FlowDefinition,
        context: Dict[str, Any],
        operator: str
    ) -> Tuple[bool, str]:
        """执行任务节点"""
        # 更新上下文
        context[node.node_id] = {'status': 'completed', 'completed_by': operator}
        instance.context_data = json.dumps(context)
        instance.updated_at = datetime.now()
        
        self.db.flush()
        return True, f'任务节点{node.name}执行完成'
    
    def _execute_notification_node(self, node: FlowNode, context: Dict[str, Any]):
        """执行通知节点"""
        config = node.config
        # TODO: 集成通知服务发送通知
        pass
    
    def _execute_automation_node(
        self,
        instance: FlowInstance,
        node: FlowNode,
        context: Dict[str, Any]
    ):
        """执行自动化节点"""
        handler_name = node.config.get('handler')
        if handler_name and handler_name in self._automation_handlers:
            handler = self._automation_handlers[handler_name]
            handler(instance, node, context)
    
    def _transition_to_next(
        self,
        instance: FlowInstance,
        flow_def: FlowDefinition,
        context: Dict[str, Any],
        operator: str
    ) -> Tuple[bool, str, Optional[FlowInstance]]:
        """转移到下一节点"""
        next_nodes = flow_def.get_next_nodes(instance.current_node_id, context)
        
        if not next_nodes:
            # 没有下一节点，流程结束
            instance.status = 'completed'
            instance.completed_at = datetime.now()
            self.db.flush()
            self.db.commit()
            return True, '流程已结束', instance
        
        # 处理条件分支 - 选择第一个匹配的节点
        next_node = next_nodes[0]
        
        # 进入新节点
        instance.current_node_id = next_node.node_id
        instance.current_node_name = next_node.name
        instance.context_data = json.dumps(context)
        instance.updated_at = datetime.now()
        
        # 记录进入新节点历史
        self._record_history(
            instance.id,
            instance.work_order_id,
            next_node.node_id,
            next_node.name,
            next_node.type.value,
            'enter',
            operator
        )
        
        # 如果是结束节点
        if next_node.type == FlowNodeType.END:
            instance.status = 'completed'
            instance.completed_at = datetime.now()
        
        self.db.flush()
        self.db.commit()
        return True, f'已转移到节点{next_node.name}', instance
    
    def _record_history(
        self,
        instance_id: int,
        work_order_id: int,
        node_id: str,
        node_name: str,
        node_type: str,
        action: str,
        operator: Optional[str] = None,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None
    ):
        """记录流程历史"""
        history = FlowHistory(
            instance_id=instance_id,
            work_order_id=work_order_id,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            action=action,
            operator=operator,
            input_data=json.dumps(input_data) if input_data else None,
            output_data=json.dumps(output_data) if output_data else None
        )
        self.db.add(history)
    
    def cancel_flow(self, instance_id: int, operator: str, reason: str) -> Tuple[bool, str]:
        """
        取消流程实例
        
        Args:
            instance_id: 流程实例ID
            operator: 操作人
            reason: 取消原因
            
        Returns:
            (是否成功, 消息)
        """
        instance = self.db.query(FlowInstance).filter(
            FlowInstance.id == instance_id
        ).first()
        
        if not instance:
            return False, '流程实例不存在'
        
        if instance.status != 'running':
            return False, f'流程实例状态为{instance.status},不能取消'
        
        instance.status = 'cancelled'
        instance.completed_at = datetime.now()
        instance.updated_at = datetime.now()
        
        # 记录历史
        self._record_history(
            instance.id,
            instance.work_order_id,
            instance.current_node_id,
            instance.current_node_name,
            'end',
            'cancel',
            operator,
            output_data={'reason': reason}
        )
        
        self.db.commit()
        return True, '流程已取消'
    
    def get_flow_instances(self, work_order_id: int) -> List[FlowInstance]:
        """
        获取工单的流程实例列表
        
        Args:
            work_order_id: 工单ID
            
        Returns:
            流程实例列表
        """
        return self.db.query(FlowInstance).filter(
            FlowInstance.work_order_id == work_order_id
        ).order_by(FlowInstance.started_at.desc()).all()
    
    def get_flow_history(self, instance_id: int) -> List[FlowHistory]:
        """
        获取流程实例的历史记录
        
        Args:
            instance_id: 流程实例ID
            
        Returns:
            历史记录列表
        """
        return self.db.query(FlowHistory).filter(
            FlowHistory.instance_id == instance_id
        ).order_by(FlowHistory.created_at.asc()).all()
    
    def register_automation_handler(self, name: str, handler: Callable):
        """
        注册自动化任务处理器
        
        Args:
            name: 处理器名称
            handler: 处理函数
        """
        self._automation_handlers[name] = handler
