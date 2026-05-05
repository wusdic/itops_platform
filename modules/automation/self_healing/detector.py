"""
故障检测模块
提供故障模式识别、根因分析、影响评估、故障传播链等功能
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


class FaultSeverity(Enum):
    """故障严重程度"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class FaultCategory(Enum):
    """故障类别"""
    HARDWARE = 'hardware'
    SOFTWARE = 'software'
    NETWORK = 'network'
    CONFIGURATION = 'configuration'
    SECURITY = 'security'
    PERFORMANCE = 'performance'
    CAPACITY = 'capacity'
    DEPENDENCY = 'dependency'
    UNKNOWN = 'unknown'


class FaultStatus(Enum):
    """故障状态"""
    DETECTED = 'detected'
    ANALYZING = 'analyzing'
    ROOT_CAUSE_IDENTIFIED = 'root_cause_identified'
    AFFECTED_ASSESSED = 'affected_assessed'
    ESCALATED = 'escalated'
    RESOLVED = 'resolved'
    AUTO_HEALED = 'auto_healed'


@dataclass
class FaultPattern:
    """故障模式"""
    pattern_id: str = ''
    name: str = ''
    category: FaultCategory = FaultCategory.UNKNOWN
    
    # 匹配条件
    match_conditions: Dict[str, Any] = field(default_factory=dict)
    symptoms: List[str] = field(default_factory=list)
    
    # 故障特征
    typical_indicators: List[str] = field(default_factory=list)
    error_signatures: List[str] = field(default_factory=list)
    
    # 关联信息
    related_incidents: List[str] = field(default_factory=list)
    known_causes: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern_id': self.pattern_id,
            'name': self.name,
            'category': self.category.value,
            'match_conditions': self.match_conditions,
            'symptoms': self.symptoms,
            'typical_indicators': self.typical_indicators,
            'error_signatures': self.error_signatures,
            'related_incidents': self.related_incidents,
            'known_causes': self.known_causes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


@dataclass
class FaultEvent:
    """故障事件"""
    event_id: str = field(default_factory=lambda: f"FAULT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
    
    # 基本信息
    alert_id: str = ''
    asset_id: str = ''
    asset_name: str = ''
    severity: FaultSeverity = FaultSeverity.ERROR
    
    # 故障信息
    category: FaultCategory = FaultCategory.UNKNOWN
    pattern: Optional[FaultPattern] = None
    
    # 时间信息
    detected_at: datetime = field(default_factory=datetime.now)
    cleared_at: Optional[datetime] = None
    duration_seconds: int = 0
    
    # 状态
    status: FaultStatus = FaultStatus.DETECTED
    
    # 上下文
    alert_data: Dict[str, Any] = field(default_factory=dict)
    metrics_snapshot: Dict[str, float] = field(default_factory=dict)
    
    # 关联
    related_events: List[str] = field(default_factory=list)
    triggered_by: Optional[str] = None  # 触发的故障事件ID
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'alert_id': self.alert_id,
            'asset_id': self.asset_id,
            'asset_name': self.asset_name,
            'severity': self.severity.value,
            'category': self.category.value,
            'pattern': self.pattern.to_dict() if self.pattern else None,
            'detected_at': self.detected_at.isoformat(),
            'cleared_at': self.cleared_at.isoformat() if self.cleared_at else None,
            'duration_seconds': self.duration_seconds,
            'status': self.status.value,
            'alert_data': self.alert_data,
            'metrics_snapshot': self.metrics_snapshot,
            'related_events': self.related_events,
            'triggered_by': self.triggered_by,
        }


@dataclass
class RootCauseAnalysis:
    """根因分析结果"""
    fault_event_id: str = ''
    
    # 分析结果
    root_cause: str = ''
    root_cause_confidence: float = 0.0  # 0-100
    analysis_method: str = ''  # manual, automated, ml
    
    # 详细信息
    contributing_factors: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    # 建议
    remediation_steps: List[str] = field(default_factory=list)
    prevention_measures: List[str] = field(default_factory=list)
    
    # 分析信息
    analyzed_by: str = 'system'
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'fault_event_id': self.fault_event_id,
            'root_cause': self.root_cause,
            'root_cause_confidence': self.root_cause_confidence,
            'analysis_method': self.analysis_method,
            'contributing_factors': self.contributing_factors,
            'evidence': self.evidence,
            'timeline': self.timeline,
            'remediation_steps': self.remediation_steps,
            'prevention_measures': self.prevention_measures,
            'analyzed_by': self.analyzed_by,
            'analyzed_at': self.analyzed_at.isoformat(),
        }


@dataclass
class PropagationNode:
    """传播链节点"""
    asset_id: str = ''
    asset_name: str = ''
    relation_type: str = ''
    impact_level: str = 'indirect'  # direct, indirect
    impact_description: str = ''
    estimated_recovery_time: int = 0  # 分钟
    
    
@dataclass
class ImpactAssessment:
    """影响评估结果"""
    fault_event_id: str = ''
    
    # 影响范围
    affected_assets: List[str] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    affected_users: int = 0
    
    # 业务影响
    business_impact_level: str = 'low'  # low, medium, high, critical
    sla_impact: bool = False
    revenue_impact_estimate: float = 0.0
    
    # 传播链
    propagation_chain: List[PropagationNode] = field(default_factory=list)
    
    # 评估信息
    assessed_at: datetime = field(default_factory=datetime.now)
    assessment_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'fault_event_id': self.fault_event_id,
            'affected_assets': self.affected_assets,
            'affected_services': self.affected_services,
            'affected_users': self.affected_users,
            'business_impact_level': self.business_impact_level,
            'sla_impact': self.sla_impact,
            'revenue_impact_estimate': self.revenue_impact_estimate,
            'propagation_chain': [
                {
                    'asset_id': n.asset_id,
                    'asset_name': n.asset_name,
                    'relation_type': n.relation_type,
                    'impact_level': n.impact_level,
                    'impact_description': n.impact_description,
                    'estimated_recovery_time': n.estimated_recovery_time,
                }
                for n in self.propagation_chain
            ],
            'assessed_at': self.assessed_at.isoformat(),
            'assessment_confidence': self.assessment_confidence,
        }


class FaultDetector:
    """故障检测器"""
    
    def __init__(self):
        # 故障模式库
        self.patterns: Dict[str, FaultPattern] = {}
        
        # 活跃故障
        self.active_faults: Dict[str, FaultEvent] = {}
        
        # 故障历史
        self.fault_history: List[FaultEvent] = []
        
        # 根因分析缓存
        self.analysis_cache: Dict[str, RootCauseAnalysis] = {}
        
        # 资产关系图 (asset_id -> [(related_asset_id, relation_type)])
        self.asset_relations: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        # 初始化默认故障模式
        self._init_default_patterns()
    
    def _init_default_patterns(self):
        """初始化默认故障模式"""
        patterns = [
            FaultPattern(
                pattern_id='PAT-001',
                name='CPU过载',
                category=FaultCategory.PERFORMANCE,
                match_conditions={'metric': 'cpu_usage', 'operator': '>', 'threshold': 90},
                symptoms=['CPU使用率持续高于90%', '系统响应变慢'],
                typical_indicators=['cpu_usage', 'load_average', 'cpu_temperature'],
                error_signatures=['high_cpu', 'cpu_throttle'],
            ),
            FaultPattern(
                pattern_id='PAT-002',
                name='内存耗尽',
                category=FaultCategory.CAPACITY,
                match_conditions={'metric': 'memory_usage', 'operator': '>', 'threshold': 90},
                symptoms=['内存使用率过高', '可能出现OOM'],
                typical_indicators=['memory_usage', 'swap_usage', 'oom_count'],
                error_signatures=['out_of_memory', 'oom_killer'],
            ),
            FaultPattern(
                pattern_id='PAT-003',
                name='磁盘空间不足',
                category=FaultCategory.CAPACITY,
                match_conditions={'metric': 'disk_usage', 'operator': '>', 'threshold': 85},
                symptoms=['磁盘空间不足', '无法写入数据'],
                typical_indicators=['disk_usage', 'inode_usage', 'disk_io_wait'],
                error_signatures=['no_space-left', 'disk_full'],
            ),
            FaultPattern(
                pattern_id='PAT-004',
                name='网络连接失败',
                category=FaultCategory.NETWORK,
                match_conditions={'metric': 'network_errors', 'operator': '>', 'threshold': 10},
                symptoms=['网络连接异常', '丢包率高'],
                typical_indicators=['packet_loss', 'latency', 'connection_failures'],
                error_signatures=['connection_timeout', 'network_unreachable'],
            ),
            FaultPattern(
                pattern_id='PAT-005',
                name='服务无响应',
                category=FaultCategory.SOFTWARE,
                match_conditions={'metric': 'service_health', 'operator': '==', 'threshold': 0},
                symptoms=['服务无法访问', '健康检查失败'],
                typical_indicators=['http_5xx_count', 'response_time', 'error_rate'],
                error_signatures=['service_down', 'health_check_failed'],
            ),
            FaultPattern(
                pattern_id='PAT-006',
                name='硬件故障',
                category=FaultCategory.HARDWARE,
                match_conditions={'metric': 'hardware_health', 'operator': '<', 'threshold': 50},
                symptoms=['硬件健康度下降', '可能出现硬件故障'],
                typical_indicators=['smart_status', 'temperature', 'power_status'],
                error_signatures=['hardware_error', 'disk_smart_failed'],
            ),
        ]
        
        for pattern in patterns:
            self.patterns[pattern.pattern_id] = pattern
    
    # ==================== 故障检测 ====================
    
    def register_pattern(self, pattern: FaultPattern) -> bool:
        """注册故障模式"""
        try:
            self.patterns[pattern.pattern_id] = pattern
            logger.info(f"Registered fault pattern: {pattern.pattern_id} - {pattern.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register pattern: {e}")
            return False
    
    def detect_fault(self, alert_data: Dict[str, Any]) -> Optional[FaultEvent]:
        """检测故障"""
        try:
            # 匹配故障模式
            matched_pattern = self._match_pattern(alert_data)
            
            if not matched_pattern:
                return None
            
            # 创建故障事件
            fault_event = FaultEvent(
                alert_id=alert_data.get('alert_id', ''),
                asset_id=alert_data.get('asset_id', ''),
                asset_name=alert_data.get('asset_name', ''),
                severity=self._determine_severity(alert_data, matched_pattern),
                category=matched_pattern.category,
                pattern=matched_pattern,
                alert_data=alert_data,
                metrics_snapshot=alert_data.get('metrics', {}),
            )
            
            # 存储活跃故障
            self.active_faults[fault_event.event_id] = fault_event
            
            logger.info(f"Fault detected: {fault_event.event_id} - {matched_pattern.name}")
            return fault_event
            
        except Exception as e:
            logger.error(f"Failed to detect fault: {e}")
            return None
    
    def _match_pattern(self, alert_data: Dict[str, Any]) -> Optional[FaultPattern]:
        """匹配故障模式"""
        alert_type = alert_data.get('alert_type', '')
        metric_name = alert_data.get('metric_name', '')
        
        for pattern in self.patterns.values():
            # 检查告警类型匹配
            if alert_type and alert_type.lower() in [s.lower() for s in pattern.symptoms]:
                return pattern
            
            # 检查指标名称匹配
            if metric_name and any(metric_name.lower() in ind.lower() for ind in pattern.typical_indicators):
                return pattern
            
            # 检查条件匹配
            conditions = pattern.match_conditions
            if conditions.get('metric') == metric_name:
                threshold = conditions.get('threshold', 0)
                operator = conditions.get('operator', '>')
                value = alert_data.get('value', 0)
                
                if self._evaluate_condition(value, operator, threshold):
                    return pattern
        
        return None
    
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
        return False
    
    def _determine_severity(self, alert_data: Dict[str, Any], pattern: FaultPattern) -> FaultSeverity:
        """确定故障严重程度"""
        severity_str = alert_data.get('severity', 'error').lower()
        
        if severity_str == 'critical':
            return FaultSeverity.CRITICAL
        elif severity_str == 'warning':
            return FaultSeverity.WARNING
        elif severity_str == 'info':
            return FaultSeverity.INFO
        else:
            return FaultSeverity.ERROR
    
    # ==================== 根因分析 ====================
    
    def analyze_root_cause(self, fault_event_id: str) -> Optional[RootCauseAnalysis]:
        """执行根因分析"""
        fault_event = self.active_faults.get(fault_event_id)
        if not fault_event:
            logger.warning(f"Fault event not found: {fault_event_id}")
            return None
        
        fault_event.status = FaultStatus.ANALYZING
        
        # 基于故障模式和已知原因进行推断
        if fault_event.pattern and fault_event.pattern.known_causes:
            root_cause = fault_event.pattern.known_causes[0]
            confidence = 75.0
            remediation = [f"检查{root_cause}", "执行相应修复操作"]
        else:
            root_cause = f"{fault_event.category.value}相关问题"
            confidence = 50.0
            remediation = ["进一步诊断", "联系技术支持"]
        
        # 获取关联事件进行因果分析
        if fault_event.related_events:
            related_analysis = self._analyze_event_chain(fault_event)
            if related_analysis:
                root_cause = related_analysis.get('root_cause', root_cause)
                confidence = max(confidence, related_analysis.get('confidence', 0))
        
        analysis = RootCauseAnalysis(
            fault_event_id=fault_event_id,
            root_cause=root_cause,
            root_cause_confidence=confidence,
            analysis_method='automated',
            contributing_factors=[fault_event.category.value],
            remediation_steps=remediation,
            prevention_measures=['加强监控', '定期巡检'],
            evidence=[{'source': 'alert_data', 'data': fault_event.alert_data}],
        )
        
        self.analysis_cache[fault_event_id] = analysis
        fault_event.status = FaultStatus.ROOT_CAUSE_IDENTIFIED
        
        logger.info(f"Root cause analysis completed for {fault_event_id}: {root_cause}")
        return analysis
    
    def _analyze_event_chain(self, fault_event: FaultEvent) -> Optional[Dict[str, Any]]:
        """分析事件链"""
        if not fault_event.related_events:
            return None
        
        # 查找最早的事件作为根因
        earliest_event = None
        for event_id in fault_event.related_events:
            if event_id in self.fault_history:
                event = self.fault_history[self.fault_history.index(event_id)]
                if not earliest_event or event.detected_at < earliest_event.detected_at:
                    earliest_event = event
        
        if earliest_event:
            return {
                'root_cause': f"由{earliest_event.category.value}故障引起",
                'confidence': 85.0,
            }
        
        return None
    
    def get_root_cause(self, fault_event_id: str) -> Optional[RootCauseAnalysis]:
        """获取根因分析结果"""
        return self.analysis_cache.get(fault_event_id)
    
    # ==================== 影响评估 ====================
    
    def assess_impact(self, fault_event_id: str) -> ImpactAssessment:
        """评估故障影响"""
        fault_event = self.active_faults.get(fault_event_id)
        if not fault_event:
            return ImpactAssessment(fault_event_id=fault_event_id)
        
        # 获取传播链
        propagation = self._trace_propagation(fault_event.asset_id)
        
        # 收集受影响资产
        affected_assets = [fault_event.asset_id]
        affected_services = []
        
        for node in propagation:
            affected_assets.append(node.asset_id)
            if node.impact_level == 'direct':
                affected_services.append(node.asset_id)
        
        # 评估业务影响
        business_impact = self._assess_business_impact(fault_event, len(affected_assets))
        
        assessment = ImpactAssessment(
            fault_event_id=fault_event_id,
            affected_assets=affected_assets,
            affected_services=affected_services,
            affected_users=business_impact['affected_users'],
            business_impact_level=business_impact['level'],
            sla_impact=business_impact['sla_impact'],
            revenue_impact_estimate=business_impact['revenue_impact'],
            propagation_chain=propagation,
            assessment_confidence=80.0,
        )
        
        fault_event.status = FaultStatus.AFFECTED_ASSESSED
        return assessment
    
    def _trace_propagation(self, asset_id: str, max_depth: int = 5) -> List[PropagationNode]:
        """追踪故障传播链"""
        propagation = []
        visited = set()
        queue = deque([(asset_id, 0)])
        
        while queue and len(propagation) < max_depth * 10:
            current_id, depth = queue.popleft()
            
            if current_id in visited or depth >= max_depth:
                continue
            
            visited.add(current_id)
            
            # 获取关联资产
            relations = self.asset_relations.get(current_id, [])
            for related_id, relation_type in relations:
                if related_id not in visited:
                    node = PropagationNode(
                        asset_id=related_id,
                        asset_name=related_id,  # 简化，实际应该查询资产名称
                        relation_type=relation_type,
                        impact_level='direct' if depth == 0 else 'indirect',
                        impact_description=f'通过{relation_type}关联',
                        estimated_recovery_time=15 if depth == 0 else 30,
                    )
                    propagation.append(node)
                    queue.append((related_id, depth + 1))
        
        return propagation
    
    def _assess_business_impact(self, fault_event: FaultEvent, affected_count: int) -> Dict[str, Any]:
        """评估业务影响"""
        impact = {
            'affected_users': 0,
            'level': 'low',
            'sla_impact': False,
            'revenue_impact': 0.0,
        }
        
        # 基于故障严重程度和影响范围
        if fault_event.severity == FaultSeverity.CRITICAL:
            impact['level'] = 'critical'
            impact['sla_impact'] = True
            impact['revenue_impact'] = 10000.0 * affected_count
        elif fault_event.severity == FaultSeverity.ERROR:
            impact['level'] = 'high' if affected_count > 3 else 'medium'
            impact['revenue_impact'] = 1000.0 * affected_count
        
        # 估算影响用户数
        impact['affected_users'] = affected_count * 50  # 简化估算
        
        return impact
    
    # ==================== 资产关系管理 ====================
    
    def register_asset_relation(self, asset_id: str, related_asset_id: str, relation_type: str):
        """注册资产关系"""
        self.asset_relations[asset_id].append((related_asset_id, relation_type))
        self.asset_relations[related_asset_id].append((asset_id, relation_type))
    
    def link_fault_events(self, source_event_id: str, target_event_id: str):
        """关联故障事件"""
        if source_event_id in self.active_faults:
            self.active_faults[source_event_id].related_events.append(target_event_id)
            self.active_faults[source_event_id].triggered_by = target_event_id
    
    # ==================== 故障管理 ====================
    
    def get_active_faults(self, severity: Optional[FaultSeverity] = None) -> List[FaultEvent]:
        """获取活跃故障"""
        faults = list(self.active_faults.values())
        if severity:
            faults = [f for f in faults if f.severity == severity]
        return sorted(faults, key=lambda x: x.detected_at, reverse=True)
    
    def resolve_fault(self, fault_event_id: str, auto_healed: bool = False):
        """解决故障"""
        if fault_event_id in self.active_faults:
            fault_event = self.active_faults[fault_event_id]
            fault_event.cleared_at = datetime.now()
            fault_event.duration_seconds = int((fault_event.cleared_at - fault_event.detected_at).total_seconds())
            fault_event.status = FaultStatus.AUTO_HEALED if auto_healed else FaultStatus.RESOLVED
            
            # 移动到历史
            self.fault_history.append(fault_event)
            del self.active_faults[fault_event_id]
            
            logger.info(f"Fault resolved: {fault_event_id}, auto_healed: {auto_healed}")
    
    def get_fault_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取故障统计"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_faults = [f for f in self.fault_history if f.detected_at > cutoff]
        
        stats = {
            'total_faults': len(recent_faults),
            'auto_healed_count': len([f for f in recent_faults if f.status == FaultStatus.AUTO_HEALED]),
            'manual_resolved_count': len([f for f in recent_faults if f.status == FaultStatus.RESOLVED]),
            'by_category': defaultdict(int),
            'by_severity': defaultdict(int),
            'avg_duration_seconds': 0,
        }
        
        for fault in recent_faults:
            stats['by_category'][fault.category.value] += 1
            stats['by_severity'][fault.severity.value] += 1
        
        durations = [f.duration_seconds for f in recent_faults if f.duration_seconds > 0]
        if durations:
            stats['avg_duration_seconds'] = sum(durations) / len(durations)
        
        stats['by_category'] = dict(stats['by_category'])
        stats['by_severity'] = dict(stats['by_severity'])
        
        return stats
