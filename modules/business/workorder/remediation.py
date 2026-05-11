"""
AI Remediation Suggestions Module
Provides AI-powered remediation suggestions and fix recommendations
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RemediationPriority(str, Enum):
    """Remediation action priority"""
    CRITICAL = "critical"    # Immediate action required
    HIGH = "high"           # Action within 1 hour
    MEDIUM = "medium"       # Action within 4 hours
    LOW = "low"             # Action within 24 hours


class RemediationType(str, Enum):
    """Remediation action type"""
    IMMEDIATE_FIX = "immediate_fix"      # Can be executed immediately
    PLAN_REMEDIATION = "plan_remediation"  # Requires planning
    ESCALATION = "escalation"            # Requires escalation
    MONITORING = "monitoring"            # Enhanced monitoring
    PREVENTION = "prevention"             # Preventive action
    WORKAROUND = "workaround"            # Temporary workaround


@dataclass
class RemediationAction:
    """Single remediation action"""
    action: str
    description: str
    priority: RemediationPriority
    action_type: RemediationType
    estimated_time_minutes: int
    risk_level: str  # low, medium, high
    prerequisites: List[str] = field(default_factory=list)
    rollback_plan: str = None
    affected_systems: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'action': self.action,
            'description': self.description,
            'priority': self.priority.value,
            'action_type': self.action_type.value,
            'estimated_time_minutes': self.estimated_time_minutes,
            'risk_level': self.risk_level,
            'prerequisites': self.prerequisites,
            'rollback_plan': self.rollback_plan,
            'affected_systems': self.affected_systems
        }


@dataclass
class RemediationSuggestion:
    """Complete remediation suggestion for an incident"""
    summary: str
    immediate_actions: List[RemediationAction]
    planned_actions: List[RemediationAction]
    prevention_actions: List[RemediationAction]
    monitoring_actions: List[RemediationAction]
    escalation_required: bool
    escalation_reason: str = None
    estimated_total_time_minutes: int = 0
    risk_assessment: str = None
    alternative_solutions: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    related_documents: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'summary': self.summary,
            'immediate_actions': [a.to_dict() for a in self.immediate_actions],
            'planned_actions': [a.to_dict() for a in self.planned_actions],
            'prevention_actions': [a.to_dict() for a in self.prevention_actions],
            'monitoring_actions': [a.to_dict() for a in self.monitoring_actions],
            'escalation_required': self.escalation_required,
            'escalation_reason': self.escalation_reason,
            'estimated_total_time_minutes': self.estimated_total_time_minutes,
            'risk_assessment': self.risk_assessment,
            'alternative_solutions': self.alternative_solutions,
            'success_criteria': self.success_criteria,
            'related_documents': self.related_documents,
            'created_at': self.created_at.isoformat()
        }


class RemediationAdvisor:
    """
    AI-powered Remediation Advisor
    
    Analyzes work orders and incidents to suggest remediation actions
    including immediate fixes, planned remediation, and prevention measures.
    """
    
    # Common remediation templates by category
    HARDWARE_REMEDIATIONS = {
        'disk': RemediationAction(
            action="检查磁盘状态",
            description="检查磁盘健康状态、RAID配置和可用空间",
            priority=RemediationPriority.HIGH,
            action_type=RemediationType.IMMEDIATE_FIX,
            estimated_time_minutes=15,
            risk_level="low",
            prerequisites=["SSH访问权限"],
            affected_systems=["存储系统"]
        ),
        'memory': RemediationAction(
            action="内存诊断",
            description="运行内存诊断工具检查是否存在硬件故障",
            priority=RemediationPriority.HIGH,
            action_type=RemediationType.IMMEDIATE_FIX,
            estimated_time_minutes=30,
            risk_level="low",
            prerequisites=["管理员权限"],
            affected_systems=["计算节点"]
        ),
        'power': RemediationAction(
            action="检查电源系统",
            description="检查UPS状态、电源模块和电缆连接",
            priority=RemediationPriority.CRITICAL,
            action_type=RemediationType.IMMEDIATE_FIX,
            estimated_time_minutes=10,
            risk_level="low",
            prerequisites=["机房物理访问权限"],
            affected_systems=["全部设备"]
        ),
    }
    
    SOFTWARE_REMEDIATIONS = {
        'restart': RemediationAction(
            action="重启服务",
            description="重启相关服务进程",
            priority=RemediationPriority.MEDIUM,
            action_type=RemediationType.IMMEDIATE_FIX,
            estimated_time_minutes=5,
            risk_level="medium",
            prerequisites=["服务重启权限"],
            rollback_plan="重新启动服务",
            affected_systems=["目标服务"]
        ),
        'bug': RemediationAction(
            action="应用补丁",
            description="应用官方补丁或更新版本修复Bug",
            priority=RemediationPriority.HIGH,
            action_type=RemediationType.PLAN_REMEDIATION,
            estimated_time_minutes=60,
            risk_level="high",
            prerequisites=["补丁包、测试环境"],
            rollback_plan="回滚到上一版本",
            affected_systems=["应用服务"]
        ),
    }
    
    NETWORK_REMEDIATIONS = {
        'dns': RemediationAction(
            action="检查DNS配置",
            description="验证DNS服务器状态和解析配置",
            priority=RemediationPriority.HIGH,
            action_type=RemediationType.IMMEDIATE_FIX,
            estimated_time_minutes=15,
            risk_level="low",
            prerequisites=["网络管理权限"],
            affected_systems=["网络服务"]
        ),
        'firewall': RemediationAction(
            action="检查防火墙规则",
            description="审查并调整防火墙规则确保必要的通信",
            priority=RemediationPriority.HIGH,
            action_type=RemediationType.IMMEDIATE_FIX,
            estimated_time_minutes=20,
            risk_level="medium",
            prerequisites=["防火墙配置权限"],
            rollback_plan="恢复原有防火墙规则",
            affected_systems=["网络安全"]
        ),
    }
    
    def __init__(self, llm_client=None):
        """
        Initialize Remediation Advisor
        
        Args:
            llm_client: Optional LLM client for AI-powered suggestions
        """
        self.llm_client = llm_client
    
    def suggest(
        self,
        title: str,
        description: str,
        root_cause: str = None,
        category: str = None,
        device_info: Dict[str, Any] = None,
        alert_info: Dict[str, Any] = None,
        metrics: Dict[str, Any] = None,
        historical_resolutions: List[Dict[str, Any]] = None
    ) -> RemediationSuggestion:
        """
        Generate remediation suggestions for an incident
        
        Args:
            title: Work order/incident title
            description: Detailed description
            root_cause: Identified root cause (optional)
            category: Root cause category (hardware, software, etc.)
            device_info: Related device information
            alert_info: Related alert information
            metrics: System metrics if available
            historical_resolutions: Similar historical resolutions
            
        Returns:
            RemediationSuggestion with recommended actions
        """
        text = f"{title or ''} {description or ''}".lower()
        
        # Determine category from root cause if not provided
        if not category and root_cause:
            category = self._infer_category_from_cause(root_cause)
        
        # Generate immediate actions
        immediate = self._generate_immediate_actions(text, category, device_info)
        
        # Generate planned remediation actions
        planned = self._generate_planned_actions(text, category, root_cause)
        
        # Generate prevention actions
        prevention = self._generate_prevention_actions(category, root_cause)
        
        # Generate enhanced monitoring actions
        monitoring = self._generate_monitoring_actions(category, device_info)
        
        # Check if escalation is needed
        escalation_needed, escalation_reason = self._check_escalation(
            category, immediate, planned
        )
        
        # Calculate total estimated time
        total_time = sum(a.estimated_time_minutes for a in immediate + planned)
        
        # Generate summary
        summary = self._generate_summary(
            category, root_cause, immediate, escalation_needed
        )
        
        # Get historical solutions if available
        alternatives = []
        if historical_resolutions:
            alternatives = [r.get('resolution', '') for r in historical_resolutions[:3]]
        
        return RemediationSuggestion(
            summary=summary,
            immediate_actions=immediate,
            planned_actions=planned,
            prevention_actions=prevention,
            monitoring_actions=monitoring,
            escalation_required=escalation_needed,
            escalation_reason=escalation_reason,
            estimated_total_time_minutes=total_time,
            risk_assessment=self._assess_risk(immediate, planned),
            alternative_solutions=alternatives,
            success_criteria=self._generate_success_criteria(category),
            related_documents=self._find_related_docs(category)
        )
    
    def _infer_category_from_cause(self, root_cause: str) -> str:
        """Infer category from root cause text"""
        cause_lower = root_cause.lower()
        
        if any(p in cause_lower for p in ['硬件', '磁盘', '电源', '内存', 'cpu', 'server']):
            return 'hardware'
        if any(p in cause_lower for p in ['软件', '应用', '服务', '进程', 'bug']):
            return 'software'
        if any(p in cause_lower for p in ['网络', 'dns', '防火墙', '连接']):
            return 'network'
        if any(p in cause_lower for p in ['配置', '权限']):
            return 'configuration'
        if any(p in cause_lower for p in ['流程', '操作', '人员']):
            return 'process'
        if any(p in cause_lower for p in ['外部', '第三方', '供应商']):
            return 'external'
        
        return 'unknown'
    
    def _generate_immediate_actions(
        self,
        text: str,
        category: str,
        device_info: Dict[str, Any] = None
    ) -> List[RemediationAction]:
        """Generate immediate fix actions"""
        actions = []
        
        # Common immediate actions by category
        if category == 'hardware':
            if any(p in text for p in ['disk', '磁盘', 'raid']):
                actions.append(self.HARDWARE_REMEDIATIONS['disk'])
            if any(p in text for p in ['memory', '内存']):
                actions.append(self.HARDWARE_REMEDIATIONS['memory'])
            if any(p in text for p in ['power', '电源']):
                actions.append(self.HARDWARE_REMEDIATIONS['power'])
            # Default hardware action
            if not actions:
                actions.append(RemediationAction(
                    action="检查设备硬件状态",
                    description="检查设备硬件指示灯、风扇、电源等状态",
                    priority=RemediationPriority.HIGH,
                    action_type=RemediationType.IMMEDIATE_FIX,
                    estimated_time_minutes=15,
                    risk_level="low",
                    prerequisites=["设备管理权限"],
                    affected_systems=["目标设备"]
                ))
        
        elif category == 'software':
            if any(p in text for p in ['crash', '崩溃', '停止']):
                actions.append(self.SOFTWARE_REMEDIATIONS['restart'])
            if any(p in text for p in ['bug', '缺陷', '异常']):
                actions.append(self.SOFTWARE_REMEDIATIONS['bug'])
            if not actions:
                actions.append(RemediationAction(
                    action="检查服务状态",
                    description="检查服务进程、资源使用和日志",
                    priority=RemediationPriority.MEDIUM,
                    action_type=RemediationType.IMMEDIATE_FIX,
                    estimated_time_minutes=10,
                    risk_level="low",
                    prerequisites=["服务管理权限"],
                    affected_systems=["目标服务"]
                ))
        
        elif category == 'network':
            if any(p in text for p in ['dns']):
                actions.append(self.NETWORK_REMEDIATIONS['dns'])
            if any(p in text for p in ['firewall', '防火墙', '连接']):
                actions.append(self.NETWORK_REMEDIATIONS['firewall'])
            if not actions:
                actions.append(RemediationAction(
                    action="检查网络连通性",
                    description="测试网络路由、延迟和丢包率",
                    priority=RemediationPriority.HIGH,
                    action_type=RemediationType.IMMEDIATE_FIX,
                    estimated_time_minutes=15,
                    risk_level="low",
                    prerequisites=["网络工具"],
                    affected_systems=["网络服务"]
                ))
        
        elif category == 'configuration':
            actions.append(RemediationAction(
                action="检查最近配置变更",
                description="审查最近的配置变更记录",
                priority=RemediationPriority.HIGH,
                action_type=RemediationType.IMMEDIATE_FIX,
                estimated_time_minutes=10,
                risk_level="low",
                prerequisites=["配置管理权限"],
                rollback_plan="回滚到之前的配置",
                affected_systems=["相关系统"]
            ))
        
        else:
            actions.append(RemediationAction(
                action="收集故障信息",
                description="收集日志、监控数据和现场信息",
                priority=RemediationPriority.MEDIUM,
                action_type=RemediationType.IMMEDIATE_FIX,
                estimated_time_minutes=15,
                risk_level="low",
                prerequisites=["日志查看权限"],
                affected_systems=["目标系统"]
            ))
        
        return actions
    
    def _generate_planned_actions(
        self,
        text: str,
        category: str,
        root_cause: str = None
    ) -> List[RemediationAction]:
        """Generate planned remediation actions"""
        actions = []
        
        if category == 'hardware':
            actions.append(RemediationAction(
                action="制定硬件更换计划",
                description="根据硬件故障情况制定更换或维修计划",
                priority=RemediationPriority.MEDIUM,
                action_type=RemediationType.PLAN_REMEDIATION,
                estimated_time_minutes=60,
                risk_level="medium",
                prerequisites=["备件资源、变更窗口"],
                rollback_plan="延后更换时间",
                affected_systems=["目标设备"]
            ))
        
        elif category == 'software':
            actions.append(RemediationAction(
                action="应用安全补丁或更新",
                description="下载并测试最新安全补丁或版本更新",
                priority=RemediationPriority.MEDIUM,
                action_type=RemediationType.PLAN_REMEDIATION,
                estimated_time_minutes=120,
                risk_level="high",
                prerequisites=["补丁包、测试环境、维护窗口"],
                rollback_plan="回滚到当前版本",
                affected_systems=["应用服务"]
            ))
        
        elif category == 'network':
            actions.append(RemediationAction(
                action="网络架构优化",
                description="分析网络架构瓶颈并进行优化",
                priority=RemediationPriority.LOW,
                action_type=RemediationType.PLAN_REMEDIATION,
                estimated_time_minutes=240,
                risk_level="medium",
                prerequisites=["网络规划、网络变更权限"],
                rollback_plan="保持原有网络架构",
                affected_systems=["网络基础设施"]
            ))
        
        return actions
    
    def _generate_prevention_actions(
        self,
        category: str,
        root_cause: str = None
    ) -> List[RemediationAction]:
        """Generate preventive actions"""
        actions = []
        
        if category == 'hardware':
            actions.append(RemediationAction(
                action="建立硬件健康检查机制",
                description="定期检查硬件状态，及时发现潜在故障",
                priority=RemediationPriority.MEDIUM,
                action_type=RemediationType.PREVENTION,
                estimated_time_minutes=30,
                risk_level="low",
                prerequisites=["监控工具"],
                affected_systems=["全部设备"]
            ))
            actions.append(RemediationAction(
                action="准备备用硬件",
                description="关键设备准备备件，缩短故障恢复时间",
                priority=RemediationPriority.LOW,
                action_type=RemediationType.PREVENTION,
                estimated_time_minutes=0,
                risk_level="low",
                prerequisites=["备件库存"],
                affected_systems=["关键设备"]
            ))
        
        elif category == 'software':
            actions.append(RemediationAction(
                action="建立版本管理机制",
                description="规范软件版本管理和变更流程",
                priority=RemediationPriority.MEDIUM,
                action_type=RemediationType.PREVENTION,
                estimated_time_minutes=30,
                risk_level="low",
                prerequisites=["版本管理工具"],
                affected_systems=["应用服务"]
            ))
            actions.append(RemediationAction(
                action="加强测试流程",
                description="在发布前进行更全面的测试",
                priority=RemediationPriority.MEDIUM,
                action_type=RemediationType.PREVENTION,
                estimated_time_minutes=60,
                risk_level="low",
                prerequisites=["测试环境"],
                affected_systems=["应用服务"]
            ))
        
        elif category == 'network':
            actions.append(RemediationAction(
                action="建立网络监控告警",
                description="配置网络指标监控和告警阈值",
                priority=RemediationPriority.MEDIUM,
                action_type=RemediationType.PREVENTION,
                estimated_time_minutes=30,
                risk_level="low",
                prerequisites=["监控工具"],
                affected_systems=["网络服务"]
            ))
        
        elif category == 'configuration':
            actions.append(RemediationAction(
                action="建立配置审计机制",
                description="定期审计配置变更，确保合规性",
                priority=RemediationPriority.MEDIUM,
                action_type=RemediationType.PREVENTION,
                estimated_time_minutes=30,
                risk_level="low",
                prerequisites=["配置管理工具"],
                affected_systems=["全部系统"]
            ))
        
        return actions
    
    def _generate_monitoring_actions(
        self,
        category: str,
        device_info: Dict[str, Any] = None
    ) -> List[RemediationAction]:
        """Generate enhanced monitoring actions"""
        actions = []
        
        system_name = device_info.get('name', '目标系统') if device_info else '目标系统'
        
        actions.append(RemediationAction(
            action="增强监控指标",
            description=f"增加{system_name}的监控指标采集",
            priority=RemediationPriority.LOW,
            action_type=RemediationType.MONITORING,
            estimated_time_minutes=20,
            risk_level="low",
            prerequisites=["监控配置权限"],
            affected_systems=[system_name]
        ))
        
        actions.append(RemediationAction(
            action="设置告警升级规则",
            description="配置告警升级机制，确保重要告警及时处理",
            priority=RemediationPriority.LOW,
            action_type=RemediationType.MONITORING,
            estimated_time_minutes=15,
            risk_level="low",
            prerequisites=["告警系统权限"],
            affected_systems=["告警系统"]
        ))
        
        return actions
    
    def _check_escalation(
        self,
        category: str,
        immediate_actions: List[RemediationAction],
        planned_actions: List[RemediationAction]
    ) -> Tuple[bool, str]:
        """Check if escalation is required"""
        # Check for critical priority actions
        for action in immediate_actions:
            if action.priority == RemediationPriority.CRITICAL:
                return True, "存在紧急处理的动作，需要上级支持"
        
        # Check for high-risk actions
        for action in immediate_actions + planned_actions:
            if action.risk_level == "high":
                return True, "存在高风险操作，需要管理层审批"
        
        # Check for infrastructure category
        if category == 'hardware':
            return True, "硬件问题可能需要供应商或专家支持"
        
        # Check total estimated time
        total_time = sum(a.estimated_time_minutes for a in immediate_actions + planned_actions)
        if total_time > 240:  # More than 4 hours
            return True, "预计处理时间较长，需要资源协调"
        
        return False, None
    
    def _generate_summary(
        self,
        category: str,
        root_cause: str,
        immediate_actions: List[RemediationAction],
        escalation_needed: bool
    ) -> str:
        """Generate remediation summary"""
        category_names = {
            'hardware': '硬件问题',
            'software': '软件问题',
            'network': '网络问题',
            'configuration': '配置问题',
            'process': '流程问题',
            'external': '外部因素',
            'unknown': '未知问题'
        }
        
        cat_name = category_names.get(category, '未知问题')
        cause_text = root_cause or '待确定'
        action_count = len(immediate_actions)
        escalation_text = '需要升级处理' if escalation_needed else '可在当前级别处理'
        
        return f"针对{cat_name}（原因：{cause_text}），建议立即执行{action_count}项紧急处理动作，{escalation_text}"
    
    def _assess_risk(
        self,
        immediate_actions: List[RemediationAction],
        planned_actions: List[RemediationAction]
    ) -> str:
        """Assess overall risk of remediation"""
        all_actions = immediate_actions + planned_actions
        
        high_risk_count = sum(1 for a in all_actions if a.risk_level == "high")
        medium_risk_count = sum(1 for a in all_actions if a.risk_level == "medium")
        
        if high_risk_count > 0:
            return "高风险：存在高风险操作，建议在低峰期执行并准备回滚方案"
        elif medium_risk_count > 0:
            return "中风险：存在中风险操作，建议在维护窗口执行"
        else:
            return "低风险：操作风险可控，可按计划执行"
    
    def _generate_success_criteria(self, category: str) -> List[str]:
        """Generate success criteria for remediation"""
        criteria = [
            "相关服务恢复正常运行",
            "监控系统显示指标正常",
            "用户反馈问题已解决"
        ]
        
        if category == 'hardware':
            criteria.append("硬件状态指示灯显示正常")
            criteria.append("硬件自检通过")
        elif category == 'software':
            criteria.append("应用日志无异常错误")
            criteria.append("服务响应时间正常")
        elif category == 'network':
            criteria.append("网络连通性测试通过")
            criteria.append("延迟和丢包率在正常范围")
        elif category == 'configuration':
            criteria.append("配置验证通过")
            criteria.append("功能测试通过")
        
        return criteria
    
    def _find_related_docs(self, category: str) -> List[Dict[str, str]]:
        """Find related documentation"""
        docs = []
        
        if category == 'hardware':
            docs.append({'title': '硬件维护手册', 'url': '/docs/hardware-maintenance'})
            docs.append({'title': '设备故障处理流程', 'url': '/docs/hardware-troubleshooting'})
        elif category == 'software':
            docs.append({'title': '应用运维手册', 'url': '/docs/app-operations'})
            docs.append({'title': '变更管理流程', 'url': '/docs/change-management'})
        elif category == 'network':
            docs.append({'title': '网络运维手册', 'url': '/docs/network-operations'})
            docs.append({'title': '网络安全策略', 'url': '/docs/network-security'})
        elif category == 'configuration':
            docs.append({'title': '配置管理规范', 'url': '/docs/config-management'})
        
        return docs
