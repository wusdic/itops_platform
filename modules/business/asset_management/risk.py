"""
风险评估模块
提供风险识别、风险等级、风险影响、替换计划生成、维保建议等功能
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    CRITICAL = 'critical'   # 严重
    HIGH = 'high'           # 高
    MEDIUM = 'medium'       # 中
    LOW = 'low'             # 低
    INFO = 'info'           # 信息


class RiskCategory(Enum):
    """风险类别"""
    HARDWARE_FAILURE = 'hardware_failure'       # 硬件故障
    SOFTWARE_FAILURE = 'software_failure'       # 软件故障
    CAPACITY = 'capacity'                       # 容量不足
    SECURITY = 'security'                       # 安全风险
    COMPLIANCE = 'compliance'                   # 合规风险
    VENDOR = 'vendor'                           # 供应商风险
    LIFECYCLE = 'lifecycle'                     # 生命周期风险
    MAINTENANCE = 'maintenance'                 # 维保风险
    PERFORMANCE = 'performance'                 # 性能风险
    DEPENDENCY = 'dependency'                   # 依赖风险


@dataclass
class RiskItem:
    """风险项"""
    risk_id: str = field(default_factory=lambda: f"RISK-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    asset_id: str = ''
    asset_name: str = ''
    
    # 风险信息
    risk_category: RiskCategory = RiskCategory.HARDWARE_FAILURE
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_name: str = ''
    description: str = ''
    
    # 风险指标
    probability: float = 0.5      # 发生概率 0-1
    impact: float = 0.5          # 影响程度 0-1
    risk_score: float = 0.0       # 风险值 = probability * impact * 100
    
    # 时间信息
    identified_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # 状态
    status: str = 'identified'   # identified, mitigating, accepted, resolved
    mitigation_plan: str = ''
    
    # 影响范围
    affected_services: List[str] = field(default_factory=list)
    affected_users: int = 0
    financial_impact: float = 0.0  # 预估经济损失
    
    # 建议
    recommendations: List[str] = field(default_factory=list)
    
    def calculate_risk_score(self) -> float:
        """计算风险值"""
        self.risk_score = self.probability * self.impact * 100
        return self.risk_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'risk_id': self.risk_id,
            'asset_id': self.asset_id,
            'asset_name': self.asset_name,
            'risk_category': self.risk_category.value,
            'risk_level': self.risk_level.value,
            'risk_name': self.risk_name,
            'description': self.description,
            'probability': self.probability,
            'impact': self.impact,
            'risk_score': self.risk_score,
            'identified_at': self.identified_at.isoformat(),
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'status': self.status,
            'mitigation_plan': self.mitigation_plan,
            'affected_services': self.affected_services,
            'affected_users': self.affected_users,
            'financial_impact': self.financial_impact,
            'recommendations': self.recommendations,
        }


@dataclass
class ReplacementPlan:
    """更换计划"""
    plan_id: str = field(default_factory=lambda: f"PLAN-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    asset_id: str = ''
    asset_name: str = ''
    
    # 更换信息
    replacement_reason: str = ''
    priority: str = 'medium'  # critical, high, medium, low
    
    # 时间安排
    recommended_replacement_date: Optional[datetime] = None
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    
    # 资源计划
    budget_required: float = 0.0
    labor_hours: float = 0.0
    downtime_hours: float = 0.0
    
    # 更换方案
    new_asset_spec: str = ''
    vendor: str = ''
    migration_plan: str = ''
    rollback_plan: str = ''
    
    # 状态
    status: str = 'proposed'  # proposed, approved, in_progress, completed, cancelled
    
    # 批准信息
    approved_by: str = ''
    approved_at: Optional[datetime] = None
    
    # 关联风险
    related_risk_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'plan_id': self.plan_id,
            'asset_id': self.asset_id,
            'asset_name': self.asset_name,
            'replacement_reason': self.replacement_reason,
            'priority': self.priority,
            'recommended_replacement_date': self.recommended_replacement_date.isoformat() if self.recommended_replacement_date else None,
            'planned_date': self.planned_date.isoformat() if self.planned_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'budget_required': self.budget_required,
            'labor_hours': self.labor_hours,
            'downtime_hours': self.downtime_hours,
            'new_asset_spec': self.new_asset_spec,
            'vendor': self.vendor,
            'migration_plan': self.migration_plan,
            'rollback_plan': self.rollback_plan,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'related_risk_ids': self.related_risk_ids,
        }


@dataclass
class MaintenanceRecommendation:
    """维保建议"""
    recommendation_id: str = field(default_factory=lambda: f"MAINT-REC-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    asset_id: str = ''
    asset_name: str = ''
    
    # 建议类型
    recommendation_type: str = ''  # preventive, corrective, upgrade, replacement
    title: str = ''
    description: str = ''
    urgency: str = 'medium'  # critical, high, medium, low
    
    # 时间建议
    recommended_time: Optional[datetime] = None
    estimated_duration_hours: float = 0.0
    
    # 资源需求
    estimated_cost: float = 0.0
    required_parts: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    
    # 状态
    status: str = 'pending'  # pending, scheduled, completed, cancelled
    
    # 预期效果
    expected_outcome: str = ''
    risk_reduction: float = 0.0  # 风险降低百分比
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'recommendation_id': self.recommendation_id,
            'asset_id': self.asset_id,
            'asset_name': self.asset_name,
            'recommendation_type': self.recommendation_type,
            'title': self.title,
            'description': self.description,
            'urgency': self.urgency,
            'recommended_time': self.recommended_time.isoformat() if self.recommended_time else None,
            'estimated_duration_hours': self.estimated_duration_hours,
            'estimated_cost': self.estimated_cost,
            'required_parts': self.required_parts,
            'required_skills': self.required_skills,
            'status': self.status,
            'expected_outcome': self.expected_outcome,
            'risk_reduction': self.risk_reduction,
            'created_at': self.created_at.isoformat(),
        }


class RiskAssessor:
    """风险评估器"""
    
    def __init__(self):
        self.risks: Dict[str, List[RiskItem]] = defaultdict(list)
        self.replacement_plans: Dict[str, ReplacementPlan] = {}
        self.maintenance_recommendations: Dict[str, List[MaintenanceRecommendation]] = defaultdict(list)
    
    # ==================== 风险识别 ====================
    
    def identify_risks(self, asset, health_score: Optional[Dict] = None,
                      lifespan_prediction: Optional[Dict] = None,
                      fault_stats: Optional[Dict] = None) -> List[RiskItem]:
        """识别资产风险"""
        risks = []
        now = datetime.now()
        
        # 1. 生命周期风险
        if lifespan_prediction:
            remaining_months = lifespan_prediction.get('remaining_lifespan_months', 60)
            eol_risk = lifespan_prediction.get('eol_risk', 'low')
            
            if remaining_months < 3:
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.LIFECYCLE,
                    risk_level=RiskLevel.CRITICAL,
                    risk_name='资产即将到达使用寿命',
                    description=f'资产剩余寿命约 {remaining_months:.1f} 个月',
                    probability=0.9,
                    impact=0.9,
                    identified_at=now,
                    recommendations=['立即启动更换流程', '制定数据迁移计划', '准备回滚方案'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
            elif remaining_months < 6:
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.LIFECYCLE,
                    risk_level=RiskLevel.HIGH,
                    risk_name='资产即将到达使用寿命',
                    description=f'资产剩余寿命约 {remaining_months:.1f} 个月',
                    probability=0.7,
                    impact=0.8,
                    identified_at=now,
                    recommendations=['启动更换规划', '开始选型评估'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
        
        # 2. 健康度风险
        if health_score:
            health_level = health_score.get('health_level', 'healthy')
            overall_score = health_score.get('overall_score', 100)
            
            if health_level == 'critical':
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.HARDWARE_FAILURE,
                    risk_level=RiskLevel.CRITICAL,
                    risk_name='资产健康度严重下降',
                    description=f'健康度评分 {overall_score}，存在严重故障风险',
                    probability=0.8,
                    impact=0.95,
                    identified_at=now,
                    recommendations=['建议立即更换', '加强监控', '准备应急预案'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
            elif health_level == 'warning':
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.HARDWARE_FAILURE,
                    risk_level=RiskLevel.HIGH,
                    risk_name='资产健康度下降',
                    description=f'健康度评分 {overall_score}，存在故障风险',
                    probability=0.5,
                    impact=0.7,
                    identified_at=now,
                    recommendations=['计划性维护', '准备更换备件'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
        
        # 3. 故障风险
        if fault_stats:
            mtbf_days = fault_stats.get('mtbf_days', 0)
            total_faults = fault_stats.get('total_faults', 0)
            critical_faults = fault_stats.get('critical_faults', 0)
            
            if critical_faults > 0:
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.HARDWARE_FAILURE,
                    risk_level=RiskLevel.HIGH,
                    risk_name='存在关键故障历史',
                    description=f'历史出现 {critical_faults} 次关键故障',
                    probability=0.6,
                    impact=0.9,
                    identified_at=now,
                    recommendations=['分析故障根因', '加强预防性维护', '准备备件'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
            
            if mtbf_days < 30:
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.HARDWARE_FAILURE,
                    risk_level=RiskLevel.HIGH,
                    risk_name='故障间隔过短',
                    description=f'平均故障间隔仅 {mtbf_days} 天',
                    probability=0.7,
                    impact=0.7,
                    identified_at=now,
                    recommendations=['评估更换必要性', '准备备件库存'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
        
        # 4. 保修风险
        if asset.warranty_expiry:
            days_remaining = (asset.warranty_expiry - now).days
            if days_remaining < 0:
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.MAINTENANCE,
                    risk_level=RiskLevel.MEDIUM,
                    risk_name='已过保修期',
                    description='资产已过保修期，维护成本将增加',
                    probability=0.6,
                    impact=0.5,
                    identified_at=now,
                    recommendations=['考虑购买延保服务', '准备设备维护预算'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
            elif days_remaining < 30:
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.MAINTENANCE,
                    risk_level=RiskLevel.LOW,
                    risk_name='保修期即将到期',
                    description=f'保修期还有 {days_remaining} 天到期',
                    probability=0.4,
                    impact=0.4,
                    identified_at=now,
                    recommendations=['提前安排设备检测', '评估续保必要性'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
        
        # 5. 依赖风险
        if hasattr(asset, 'relations') and asset.relations:
            critical_deps = [r for r in asset.relations if r.is_critical and r.relation_type.value == 'dependency']
            if critical_deps:
                risk = RiskItem(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    risk_category=RiskCategory.DEPENDENCY,
                    risk_level=RiskLevel.HIGH,
                    risk_name='关键依赖资产',
                    description=f'资产被 {len(critical_deps)} 个关键系统依赖',
                    probability=0.3,
                    impact=0.95,
                    identified_at=now,
                    recommendations=['制定容灾方案', '准备备用设备', '确保备件充足'],
                )
                risk.calculate_risk_score()
                risks.append(risk)
        
        # 存储风险
        self.risks[asset.asset_id] = risks
        return risks
    
    def get_risks(self, asset_id: str, risk_level: Optional[RiskLevel] = None) -> List[RiskItem]:
        """获取风险列表"""
        risks = self.risks.get(asset_id, [])
        if risk_level:
            risks = [r for r in risks if r.risk_level == risk_level]
        return sorted(risks, key=lambda x: x.risk_score, reverse=True)
    
    def get_all_risks(self, risk_level: Optional[RiskLevel] = None) -> List[RiskItem]:
        """获取所有风险"""
        all_risks = []
        for risks in self.risks.values():
            all_risks.extend(risks)
        if risk_level:
            all_risks = [r for r in all_risks if r.risk_level == risk_level]
        return sorted(all_risks, key=lambda x: x.risk_score, reverse=True)
    
    # ==================== 风险影响评估 ====================
    
    def assess_impact(self, risk: RiskItem, asset, affected_services: List[str] = None) -> Dict[str, Any]:
        """评估风险影响"""
        impact = {
            'risk_id': risk.risk_id,
            'asset_id': asset.asset_id,
            'affected_services': affected_services or [],
            'affected_users': 0,
            'financial_impact': 0.0,
            'operational_impact': 'medium',
            'recovery_time_estimate': 0.0,
        }
        
        # 基于资产类型和状态评估影响
        if asset.category.value == 'server':
            impact['affected_users'] = 100  # 默认估计
            impact['financial_impact'] = asset.purchase_price * 0.1  # 默认10%损失
            impact['recovery_time_estimate'] = 4.0  # 4小时
        elif asset.category.value == 'network':
            impact['affected_users'] = 500
            impact['financial_impact'] = asset.purchase_price * 0.15
            impact['recovery_time_estimate'] = 2.0
        elif asset.category.value == 'security':
            impact['affected_users'] = 1000
            impact['financial_impact'] = asset.purchase_price * 0.3
            impact['recovery_time_estimate'] = 8.0
            impact['operational_impact'] = 'high'
        
        # 基于风险等级调整
        if risk.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            impact['operational_impact'] = 'high'
            impact['financial_impact'] *= 2
        
        return impact
    
    # ==================== 替换计划生成 ====================
    
    def generate_replacement_plan(self, asset, risk: RiskItem,
                                  lifespan_prediction: Optional[Dict] = None) -> Optional[ReplacementPlan]:
        """生成替换计划"""
        now = datetime.now()
        
        # 检查是否需要生成替换计划
        if risk.risk_level not in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return None
        
        # 建议替换时间
        recommended_date = None
        if lifespan_prediction:
            pred_date = lifespan_prediction.get('predicted_replacement_date')
            if pred_date:
                recommended_date = datetime.fromisoformat(pred_date) if isinstance(pred_date, str) else pred_date
        
        if not recommended_date:
            # 默认提前6个月
            recommended_date = now + timedelta(days=180)
        
        # 估算成本
        budget = asset.purchase_price * 1.2  # 包含迁移和停机成本
        
        plan = ReplacementPlan(
            asset_id=asset.asset_id,
            asset_name=asset.name,
            replacement_reason=f'风险评估建议: {risk.risk_name}',
            priority='high' if risk.risk_level == RiskLevel.CRITICAL else 'medium',
            recommended_replacement_date=recommended_date,
            budget_required=budget,
            labor_hours=8.0,
            downtime_hours=4.0,
            new_asset_spec=f'替换为同型号或更高配置设备',
            migration_plan='制定详细数据迁移方案',
            rollback_plan='保留原设备作为备份',
            status='proposed',
            related_risk_ids=[risk.risk_id],
        )
        
        self.replacement_plans[asset.asset_id] = plan
        return plan
    
    def get_replacement_plan(self, asset_id: str) -> Optional[ReplacementPlan]:
        """获取替换计划"""
        return self.replacement_plans.get(asset_id)
    
    def get_pending_plans(self) -> List[ReplacementPlan]:
        """获取待执行替换计划"""
        return [p for p in self.replacement_plans.values() if p.status in ['proposed', 'approved']]
    
    def update_plan_status(self, asset_id: str, status: str) -> bool:
        """更新计划状态"""
        if asset_id in self.replacement_plans:
            self.replacement_plans[asset_id].status = status
            if status == 'completed':
                self.replacement_plans[asset_id].completed_date = datetime.now()
            return True
        return False
    
    # ==================== 维保建议 ====================
    
    def generate_maintenance_recommendations(self, asset, 
                                            health_score: Optional[Dict] = None,
                                            fault_stats: Optional[Dict] = None) -> List[MaintenanceRecommendation]:
        """生成维保建议"""
        recommendations = []
        now = datetime.now()
        
        # 基于健康度建议
        if health_score:
            overall_score = health_score.get('overall_score', 100)
            recommendations_list = health_score.get('recommendations', [])
            
            if overall_score < 40:
                rec = MaintenanceRecommendation(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    recommendation_type='corrective',
                    title='紧急维护检查',
                    description='资产健康度严重下降，需要进行全面检查和可能的更换',
                    urgency='critical',
                    recommended_time=now + timedelta(days=7),
                    estimated_duration_hours=8.0,
                    estimated_cost=5000.0,
                    required_skills=['硬件维护', '故障诊断'],
                    expected_outcome='恢复正常运行或完成更换',
                    risk_reduction=30.0,
                )
                recommendations.append(rec)
            elif overall_score < 60:
                rec = MaintenanceRecommendation(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    recommendation_type='preventive',
                    title='计划性维护',
                    description='进行预防性维护，检查关键部件状态',
                    urgency='medium',
                    recommended_time=now + timedelta(days=30),
                    estimated_duration_hours=4.0,
                    estimated_cost=2000.0,
                    required_skills=['硬件维护'],
                    expected_outcome='提高健康度评分',
                    risk_reduction=15.0,
                )
                recommendations.append(rec)
        
        # 基于故障统计建议
        if fault_stats:
            mtbf_days = fault_stats.get('mtbf_days', 0)
            mttr_hours = fault_stats.get('mttr_hours', 0)
            
            if mtbf_days < 30:
                rec = MaintenanceRecommendation(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    recommendation_type='upgrade',
                    title='升级或更换',
                    description=f'故障间隔过短({mtbf_days}天)，建议评估升级或更换方案',
                    urgency='high',
                    recommended_time=now + timedelta(days=60),
                    estimated_duration_hours=16.0,
                    estimated_cost=asset.purchase_price * 0.8,
                    required_skills=['系统迁移', '硬件维护'],
                    expected_outcome='减少故障率，提高可用性',
                    risk_reduction=50.0,
                )
                recommendations.append(rec)
            
            if mttr_hours > 8:
                rec = MaintenanceRecommendation(
                    asset_id=asset.asset_id,
                    asset_name=asset.name,
                    recommendation_type='preventive',
                    title='建立快速故障响应机制',
                    description=f'平均修复时间过长({mttr_hours}小时)，建议准备备件和快速响应流程',
                    urgency='medium',
                    recommended_time=now + timedelta(days=30),
                    estimated_duration_hours=2.0,
                    estimated_cost=1000.0,
                    required_skills=['运维管理'],
                    expected_outcome='缩短MTTR',
                    risk_reduction=10.0,
                )
                recommendations.append(rec)
        
        # 存储建议
        self.maintenance_recommendations[asset.asset_id] = recommendations
        return recommendations
    
    def get_maintenance_recommendations(self, asset_id: str) -> List[MaintenanceRecommendation]:
        """获取维保建议"""
        return self.maintenance_recommendations.get(asset_id, [])
    
    # ==================== 综合风险报告 ====================
    
    def generate_risk_report(self, asset, assessment_result: Optional[Dict] = None) -> Dict[str, Any]:
        """生成综合风险报告"""
        now = datetime.now()
        
        # 获取评估数据
        health_score = assessment_result.get('health_score') if assessment_result else None
        lifespan_pred = assessment_result.get('lifespan_prediction') if assessment_result else None
        fault_stats = assessment_result.get('fault_statistics') if assessment_result else None
        
        # 识别风险
        risks = self.identify_risks(asset, health_score, lifespan_pred, fault_stats)
        
        # 生成替换计划
        replacement_plans = []
        for risk in risks:
            if risk.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                plan = self.generate_replacement_plan(asset, risk, lifespan_pred)
                if plan:
                    replacement_plans.append(plan)
        
        # 生成维保建议
        maintenance_recs = self.generate_maintenance_recommendations(asset, health_score, fault_stats)
        
        # 计算风险汇总
        risk_summary = {
            'total_risks': len(risks),
            'critical_risks': len([r for r in risks if r.risk_level == RiskLevel.CRITICAL]),
            'high_risks': len([r for r in risks if r.risk_level == RiskLevel.HIGH]),
            'medium_risks': len([r for r in risks if r.risk_level == RiskLevel.MEDIUM]),
            'low_risks': len([r for r in risks if r.risk_level == RiskLevel.LOW]),
            'total_risk_score': sum(r.risk_score for r in risks),
        }
        
        return {
            'asset_id': asset.asset_id,
            'asset_name': asset.name,
            'report_generated_at': now.isoformat(),
            'risk_summary': risk_summary,
            'risks': [r.to_dict() for r in risks],
            'replacement_plans': [p.to_dict() for p in replacement_plans],
            'maintenance_recommendations': [rec.to_dict() for rec in maintenance_recs],
        }
