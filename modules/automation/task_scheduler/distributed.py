"""分布式调度 - 多实例协调、任务分片、主从选举"""
import asyncio
import logging
import uuid
import hashlib
from typing import Optional, Callable, Dict, Any, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """节点角色"""
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


class ElectionState(Enum):
    """选举状态"""
    IDLE = "idle"
    ELECTING = "electing"
    LEADER = "leader"


@dataclass
class ClusterNode:
    """集群节点"""
    node_id: str
    host: str
    port: int
    role: NodeRole = NodeRole.FOLLOWER
    is_active: bool = True
    last_heartbeat: datetime = field(default_factory=datetime.now)
    priority: int = 1
    version: int = 0
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"
    
    def is_alive(self, timeout: int = 30) -> bool:
        """检查节点是否存活"""
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < timeout


@dataclass
class TaskShard:
    """任务分片"""
    shard_id: str
    task_id: str
    assigned_node: Optional[str] = None
    status: str = "pending"
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class DistributedScheduler:
    """
    分布式调度器
    支持功能:
    - 多实例协调（可选）
    - 任务分片
    - 主从选举
    """
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        host: str = "localhost",
        port: int = 8765,
        cluster_nodes: Optional[List[Dict[str, Any]]] = None,
        election_timeout: int = 10,
        heartbeat_interval: int = 5,
        replication_factor: int = 2,
    ):
        """
        初始化分布式调度器
        
        Args:
            node_id: 节点ID
            host: 主机地址
            port: 端口
            cluster_nodes: 集群节点列表
            election_timeout: 选举超时（秒）
            heartbeat_interval: 心跳间隔（秒）
            replication_factor: 复制因子
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.host = host
        self.port = port
        self.cluster_nodes = cluster_nodes or []
        self.election_timeout = election_timeout
        self.heartbeat_interval = heartbeat_interval
        self.replication_factor = replication_factor
        
        # 状态
        self._role = NodeRole.FOLLOWER
        self._election_state = ElectionState.IDLE
        self._leader: Optional[ClusterNode] = None
        self._nodes: Dict[str, ClusterNode] = {}
        self._running = False
        self._server: Optional[asyncio.Server] = None
        
        # 任务分片
        self._shards: Dict[str, TaskShard] = {}
        self._task_ownership: Dict[str, Set[str]] = {}  # task_id -> node_ids
        
        # 回调
        self._on_leader_change: Optional[Callable] = None
        self._on_node_change: Optional[Callable] = None
        
        # 本地任务锁
        self._local_tasks: Set[str] = set()
        
        # 注册本节点
        self._register_node()
    
    def _register_node(self):
        """注册本节点"""
        self._nodes[self.node_id] = ClusterNode(
            node_id=self.node_id,
            host=self.host,
            port=self.port,
            role=self._role,
            priority=1,
        )
        
        # 注册其他节点
        for node_info in self.cluster_nodes:
            if node_info.get('node_id') != self.node_id:
                self._nodes[node_info['node_id']] = ClusterNode(
                    node_id=node_info['node_id'],
                    host=node_info['host'],
                    port=node_info['port'],
                    priority=node_info.get('priority', 1),
                )
    
    async def start(self):
        """启动分布式调度器"""
        if self._running:
            return
        
        self._running = True
        
        # 启动RPC服务器
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port
        )
        
        # 启动心跳任务
        asyncio.create_task(self._heartbeat_loop())
        
        # 启动选举任务
        asyncio.create_task(self._election_loop())
        
        logger.info(f"Distributed scheduler started: {self.node_id} on {self.host}:{self.port}")
    
    async def stop(self):
        """停止分布式调度器"""
        self._running = False
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        logger.info("Distributed scheduler stopped")
    
    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理连接"""
        addr = writer.get_extra_info('peername')
        
        try:
            while self._running:
                data = await reader.read(4096)
                if not data:
                    break
                
                message = json.loads(data.decode())
                response = await self._process_message(message)
                
                if response:
                    writer.write(json.dumps(response).encode())
                    await writer.drain()
        
        except Exception as e:
            logger.error(f"Error handling connection from {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def _process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理消息"""
        msg_type = message.get('type')
        
        if msg_type == 'heartbeat':
            return await self._handle_heartbeat(message)
        elif msg_type == 'election':
            return await self._handle_election(message)
        elif msg_type == 'vote':
            return await self._handle_vote(message)
        elif msg_type == 'task_shard':
            return await self._handle_task_shard(message)
        elif msg_type == 'task_complete':
            return await self._handle_task_complete(message)
        elif msg_type == 'get_leader':
            return {'type': 'leader', 'leader': self._leader.node_id if self._leader else None}
        elif msg_type == 'get_nodes':
            return {'type': 'nodes', 'nodes': list(self._nodes.keys())}
        
        return None
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                # 发送心跳
                await self._send_heartbeat()
                
                # 更新本节点心跳
                if self.node_id in self._nodes:
                    self._nodes[self.node_id].last_heartbeat = datetime.now()
                
                # 检查其他节点
                self._check_nodes_alive()
            
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
            
            await asyncio.sleep(self.heartbeat_interval)
    
    async def _send_heartbeat(self):
        """发送心跳"""
        for node_id, node in self._nodes.items():
            if node_id == self.node_id:
                continue
            
            try:
                reader, writer = await asyncio.open_connection(node.host, node.port)
                
                message = {
                    'type': 'heartbeat',
                    'node_id': self.node_id,
                    'timestamp': datetime.now().isoformat(),
                }
                
                writer.write(json.dumps(message).encode())
                await writer.drain()
                
                response = await asyncio.wait_for(reader.read(1024), timeout=5)
                data = json.loads(response.decode())
                
                # 更新节点状态
                if node_id in self._nodes:
                    self._nodes[node_id].last_heartbeat = datetime.now()
                    self._nodes[node_id].is_active = True
                
                writer.close()
                await writer.wait_closed()
            
            except Exception as e:
                if node_id in self._nodes:
                    self._nodes[node_id].is_active = False
                logger.debug(f"Heartbeat failed for node {node_id}: {e}")
    
    def _check_nodes_alive(self):
        """检查节点存活"""
        for node_id, node in self._nodes.items():
            if not node.is_alive(timeout=self.election_timeout * 2):
                if node.is_active:
                    node.is_active = False
                    logger.warning(f"Node {node_id} is not alive")
                    
                    # 如果是leader，触发选举
                    if self._leader and self._leader.node_id == node_id:
                        asyncio.create_task(self._start_election())
    
    async def _handle_heartbeat(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理心跳"""
        from_node = message.get('node_id')
        
        if from_node in self._nodes:
            self._nodes[from_node].last_heartbeat = datetime.now()
            self._nodes[from_node].is_active = True
        
        return {'type': 'heartbeat_ack', 'node_id': self.node_id}
    
    async def _election_loop(self):
        """选举循环"""
        while self._running:
            try:
                # 检查是否需要选举
                if self._should_start_election():
                    await self._start_election()
            
            except Exception as e:
                logger.error(f"Error in election loop: {e}")
            
            await asyncio.sleep(1)
    
    def _should_start_election(self) -> bool:
        """检查是否需要开始选举"""
        # 如果没有leader
        if not self._leader:
            return True
        
        # 如果leader不活跃
        if not self._leader.is_alive(timeout=self.election_timeout):
            return True
        
        return False
    
    async def _start_election(self):
        """开始选举"""
        if self._election_state == ElectionState.ELECTING:
            return
        
        self._election_state = ElectionState.ELECTING
        logger.info(f"Starting election on node {self.node_id}")
        
        # 成为候选人
        self._role = NodeRole.CANDIDATE
        self._nodes[self.node_id].role = NodeRole.CANDIDATE
        
        # 请求投票
        votes = 1  # 自己投自己
        term = int(datetime.now().timestamp())
        
        for node_id, node in self._nodes.items():
            if node_id == self.node_id:
                continue
            
            if not node.is_active:
                continue
            
            # 比较优先级
            if node.priority > self._nodes[self.node_id].priority:
                continue
            
            try:
                reader, writer = await asyncio.open_connection(node.host, node.port)
                
                message = {
                    'type': 'vote',
                    'candidate_id': self.node_id,
                    'term': term,
                }
                
                writer.write(json.dumps(message).encode())
                await writer.drain()
                
                response = await asyncio.wait_for(reader.read(1024), timeout=5)
                data = json.loads(response.decode())
                
                if data.get('vote_granted'):
                    votes += 1
                
                writer.close()
                await writer.wait_closed()
            
            except Exception as e:
                logger.debug(f"Vote request failed for node {node_id}: {e}")
        
        # 检查是否获得多数票
        majority = len(self._nodes) // 2 + 1
        
        if votes >= majority:
            await self._become_leader()
        else:
            self._role = NodeRole.FOLLOWER
            self._nodes[self.node_id].role = NodeRole.FOLLOWER
        
        self._election_state = ElectionState.IDLE
    
    async def _become_leader(self):
        """成为leader"""
        self._role = NodeRole.LEADER
        self._election_state = ElectionState.LEADER
        self._nodes[self.node_id].role = NodeRole.LEADER
        self._nodes[self.node_id].version += 1
        
        # 通知其他节点
        for node_id, node in self._nodes.items():
            if node_id == self.node_id:
                continue
            
            try:
                reader, writer = await asyncio.open_connection(node.host, node.port)
                
                message = {
                    'type': 'leader_change',
                    'leader_id': self.node_id,
                    'term': self._nodes[self.node_id].version,
                }
                
                writer.write(json.dumps(message).encode())
                await writer.drain()
                writer.close()
            
            except Exception as e:
                logger.debug(f"Notify leader change failed for node {node_id}: {e}")
        
        logger.info(f"Node {self.node_id} became leader")
        
        if self._on_leader_change:
            self._on_leader_change(self.node_id)
    
    async def _handle_vote(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理投票请求"""
        candidate_id = message.get('candidate_id')
        term = message.get('term', 0)
        
        # 比较term
        my_term = self._nodes[self.node_id].version
        
        if term < my_term:
            return {'type': 'vote_response', 'vote_granted': False}
        
        # 比较优先级
        if candidate_id in self._nodes:
            if self._nodes[candidate_id].priority > self._nodes[self.node_id].priority:
                return {'type': 'vote_response', 'vote_granted': False}
        
        # 投票
        self._role = NodeRole.FOLLOWER
        return {'type': 'vote_response', 'vote_granted': True}
    
    async def _handle_election(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理选举消息"""
        # 类似于投票处理
        return await self._handle_vote(message)
    
    # 任务分片
    
    def create_shards(self, task_id: str, num_shards: int) -> List[TaskShard]:
        """创建任务分片"""
        shards = []
        active_nodes = [n for n in self._nodes.values() if n.is_active and n.role == NodeRole.LEADER]
        
        if not active_nodes:
            active_nodes = [n for n in self._nodes.values() if n.is_active]
        
        if not active_nodes:
            # 单机模式，所有分片分配给自己
            for i in range(num_shards):
                shard = TaskShard(
                    shard_id=f"{task_id}_{i}",
                    task_id=task_id,
                    assigned_node=self.node_id,
                )
                shards.append(shard)
                self._shards[shard.shard_id] = shard
        else:
            # 分配到多个节点
            for i in range(num_shards):
                node_index = i % len(active_nodes)
                shard = TaskShard(
                    shard_id=f"{task_id}_{i}",
                    task_id=task_id,
                    assigned_node=active_nodes[node_index].node_id,
                )
                shards.append(shard)
                self._shards[shard.shard_id] = shard
        
        # 记录任务所有权
        self._task_ownership[task_id] = {s.assigned_node for s in shards}
        
        return shards
    
    def get_shard(self, shard_id: str) -> Optional[TaskShard]:
        """获取分片"""
        return self._shards.get(shard_id)
    
    def get_shards_for_task(self, task_id: str) -> List[TaskShard]:
        """获取任务的所有分片"""
        return [s for s in self._shards.values() if s.task_id == task_id]
    
    def is_task_owned(self, task_id: str) -> bool:
        """检查任务是否由本节点拥有"""
        shards = self.get_shards_for_task(task_id)
        
        if not shards:
            # 没有分片，默认本节点负责
            return True
        
        return any(s.assigned_node == self.node_id for s in shards)
    
    def get_owned_tasks(self) -> List[str]:
        """获取本节点拥有的任务"""
        owned = set()
        
        for shard in self._shards.values():
            if shard.assigned_node == self.node_id:
                owned.add(shard.task_id)
        
        return list(owned)
    
    async def _handle_task_shard(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务分片消息"""
        action = message.get('action')
        
        if action == 'create':
            task_id = message.get('task_id')
            num_shards = message.get('num_shards', 1)
            shards = self.create_shards(task_id, num_shards)
            
            return {
                'type': 'shards_created',
                'shards': [
                    {
                        'shard_id': s.shard_id,
                        'task_id': s.task_id,
                        'assigned_node': s.assigned_node,
                    }
                    for s in shards
                ]
            }
        
        elif action == 'update':
            shard_id = message.get('shard_id')
            status = message.get('status')
            progress = message.get('progress')
            
            if shard_id in self._shards:
                self._shards[shard_id].status = status
                self._shards[shard_id].progress = progress
            
            return {'type': 'shard_updated'}
        
        return {'type': 'error', 'message': 'Unknown action'}
    
    async def _handle_task_complete(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务完成"""
        shard_id = message.get('shard_id')
        
        if shard_id in self._shards:
            self._shards[shard_id].status = 'completed'
            self._shards[shard_id].progress = 1.0
            
            # 检查所有分片是否完成
            task_id = self._shards[shard_id].task_id
            shards = self.get_shards_for_task(task_id)
            
            if all(s.status == 'completed' for s in shards):
                return {
                    'type': 'task_completed',
                    'task_id': task_id,
                }
        
        return {'type': 'acknowledged'}
    
    # 属性
    
    @property
    def is_leader(self) -> bool:
        """是否为leader"""
        return self._role == NodeRole.LEADER
    
    @property
    def role(self) -> NodeRole:
        """获取角色"""
        return self._role
    
    @property
    def leader(self) -> Optional[ClusterNode]:
        """获取leader"""
        return self._leader
    
    @property
    def nodes(self) -> Dict[str, ClusterNode]:
        """获取所有节点"""
        return self._nodes.copy()
    
    def on_leader_change(self, callback: Callable):
        """注册leader变化回调"""
        self._on_leader_change = callback
    
    def on_node_change(self, callback: Callable):
        """注册节点变化回调"""
        self._on_node_change = callback
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """获取集群状态"""
        return {
            'node_id': self.node_id,
            'role': self._role.value,
            'leader': self._leader.node_id if self._leader else None,
            'is_leader': self.is_leader,
            'nodes': [
                {
                    'node_id': n.node_id,
                    'address': n.address,
                    'role': n.role.value,
                    'is_active': n.is_active,
                    'is_alive': n.is_alive(timeout=self.election_timeout * 2),
                }
                for n in self._nodes.values()
            ],
            'shards': {
                'total': len(self._shards),
                'pending': sum(1 for s in self._shards.values() if s.status == 'pending'),
                'completed': sum(1 for s in self._shards.values() if s.status == 'completed'),
            }
        }
