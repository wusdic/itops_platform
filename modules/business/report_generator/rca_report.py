"""
RCA报告生成器
生成根因分析报告，包括故障时间线、根因分析、影响评估、改进措施
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .reporter import ReportGenerator, ReportType, Report, ReportStatus

logger = logging.getLogger(__name__)


class Severity(Enum):
    """严重程度枚举"""
    P1 = "P1"  # 严重
    P2 = "P2"  # 高
    P3 = "P3"  # 中
    P4 = "P4"  # 低


class RootCauseMethod(Enum):
    """根因分析方法"""
    FIVE_WHY = "5why"
    FISHBONE = "fishbone"
    FAULT_TREE = "fault_tree"
    ISHIKAWA = "ishikawa"


@dataclass
class TimelineEvent:
    """时间线事件"""
    timestamp: datetime
    event_type: str  # detection/notification/response/mitigation/resolution
    description: str
    actor: str = ""
    duration_seconds: int = 0


@dataclass
class ImpactAssessment:
    """影响评估"""
    affected_services: List[str] = field(default_factory=list)
    affected_users: int = 0
    affected_regions: List[str] = field(default_factory=list)
    business_loss: str = ""
    revenue_impact: float = 0.0
    customer_impact: str = ""


@dataclass
class FiveWhyAnalysis:
    """5Why分析"""
    problem: str = ""
    why_levels: List[Dict[str, str]] = field(default_factory=list)
    root_cause: str = ""
    confidence: str = "high"  # high/medium/low


@dataclass
class FishboneCategory:
    """鱼骨图类别"""
    category: str = ""  # 人/机/料/法/环/测
    causes: List[str] = field(default_factory=list)


@dataclass
class FishboneAnalysis:
    """鱼骨图分析"""
    problem: str = ""
    categories: List[FishboneCategory] = field(default_factory=list)
    root_causes: List[str] = field(default_factory=list)


@dataclass
class RootCauseAnalysis:
    """根因分析"""
    method: RootCauseMethod = RootCauseMethod.FIVE_WHY
    five_why: Optional[FiveWhyAnalysis] = None
    fishbone: Optional[FishboneAnalysis] = None
    contributing_factors: List[str] = field(default_factory=list)
    root_cause_summary: str = ""


@dataclass
class ActionItem:
    """改进措施项"""
    action: str = ""
    owner: str = ""
    due_date: Optional[datetime] = None
    status: str = "open"  # open/in_progress/completed/verified
    priority: str = "high"  # high/medium/low
    verification_method: str = ""


@dataclass
class RCAReportData:
    """RCA报告数据"""
    incident_id: str = ""
    incident_title: str = ""
    severity: Severity = Severity.P2
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    detection_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None
    
    timeline: List[TimelineEvent] = field(default_factory=list)
    impact: ImpactAssessment = field(default_factory=ImpactAssessment)
    root_cause: RootCauseAnalysis = field(default_factory=RootCauseAnalysis)
    action_items: List[ActionItem] = field(default_factory=list)
    
    summary: str = ""
    lessons_learned: List[str] = field(default_factory=list)


class RCAReportGenerator:
    """
    RCA报告生成器
    
    生成内容包括：
    - 故障时间线
    - 根因分析（5Why/鱼骨图）
    - 故障影响
    - 处理过程
    - 改进措施
    """
    
    def __init__(
        self,
        report_generator: ReportGenerator
    ):
        """
        初始化RCA报告生成器
        
        Args:
            report_generator: 报告生成器实例
        """
        self._report_generator = report_generator
    
    def generate(
        self,
        incident_id: str,
        incident_title: str,
        severity: Severity,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        timeline: Optional[List[Dict[str, Any]]] = None,
        impact: Optional[Dict[str, Any]] = None,
        root_cause_analysis: Optional[Dict[str, Any]] = None,
        action_items: Optional[List[Dict[str, Any]]] = None,
        lessons_learned: Optional[List[str]] = None,
    ) -> Report:
        """
        生成RCA报告
        
        Args:
            incident_id: 故障ID
            incident_title: 故障标题
            severity: 严重程度
            start_time: 故障开始时间
            end_time: 故障结束时间
            timeline: 时间线事件
            impact: 影响评估
            root_cause_analysis: 根因分析
            action_items: 改进措施
            lessons_learned: 经验教训
            
        Returns:
            生成的报告对象
        """
        # 创建报告
        report = self._report_generator.create_report(
            report_type=ReportType.RCA,
            title=f"RCA报告 - {incident_id}: {incident_title}",
            description=f"故障根因分析报告 - {severity.value}级别",
            period_start=start_time,
            period_end=end_time or datetime.now(),
            tags=['rca', 'incident', severity.value],
            custom_fields={
                'incident_id': incident_id,
                'severity': severity.value,
            }
        )
        
        # 构建上下文
        context = {
            'incident_id': incident_id,
            'incident_title': incident_title,
            'severity': severity,
            'start_time': start_time,
            'end_time': end_time,
            'detection_time': root_cause_analysis.get('detection_time') if root_cause_analysis else None,
            'resolution_time': end_time,
            'timeline': self._parse_timeline(timeline),
            'impact': self._parse_impact(impact),
            'root_cause': self._parse_root_cause(root_cause_analysis),
            'action_items': self._parse_action_items(action_items),
            'lessons_learned': lessons_learned or [],
            'duration': self._calculate_duration(start_time, end_time),
        }
        
        # 生成报告
        return self._report_generator.generate(report, context=context)
    
    def _parse_timeline(
        self,
        timeline_data: Optional[List[Dict[str, Any]]]
    ) -> List[TimelineEvent]:
        """解析时间线数据"""
        if not timeline_data:
            return []
        
        events = []
        for item in timeline_data:
            event = TimelineEvent(
                timestamp=item.get('timestamp', datetime.now()),
                event_type=item.get('type', 'unknown'),
                description=item.get('description', ''),
                actor=item.get('actor', ''),
                duration_seconds=item.get('duration', 0),
            )
            events.append(event)
        
        # 按时间排序
        events.sort(key=lambda e: e.timestamp)
        return events
    
    def _parse_impact(
        self,
        impact_data: Optional[Dict[str, Any]]
    ) -> ImpactAssessment:
        """解析影响评估数据"""
        if not impact_data:
            return ImpactAssessment()
        
        return ImpactAssessment(
            affected_services=impact_data.get('affected_services', []),
            affected_users=impact_data.get('affected_users', 0),
            affected_regions=impact_data.get('affected_regions', []),
            business_loss=impact_data.get('business_loss', ''),
            revenue_impact=impact_data.get('revenue_impact', 0.0),
            customer_impact=impact_data.get('customer_impact', ''),
        )
    
    def _parse_root_cause(
        self,
        rca_data: Optional[Dict[str, Any]]
    ) -> RootCauseAnalysis:
        """解析根因分析数据"""
        if not rca_data:
            return RootCauseAnalysis()
        
        analysis = RootCauseAnalysis()
        
        # 解析分析方法
        method_str = rca_data.get('method', '5why')
        try:
            analysis.method = RootCauseMethod(method_str)
        except ValueError:
            analysis.method = RootCauseMethod.FIVE_WHY
        
        # 5Why分析
        if 'five_why' in rca_data:
            why_data = rca_data['five_why']
            analysis.five_why = FiveWhyAnalysis(
                problem=why_data.get('problem', ''),
                why_levels=why_data.get('levels', []),
                root_cause=why_data.get('root_cause', ''),
                confidence=why_data.get('confidence', 'high'),
            )
        
        # 鱼骨图分析
        if 'fishbone' in rca_data:
            fishbone_data = rca_data['fishbone']
            categories = []
            
            for cat_data in fishbone_data.get('categories', []):
                category = FishboneCategory(
                    category=cat_data.get('name', ''),
                    causes=cat_data.get('causes', []),
                )
                categories.append(category)
            
            analysis.fishbone = FishboneAnalysis(
                problem=fishbone_data.get('problem', ''),
                categories=categories,
                root_causes=fishbone_data.get('root_causes', []),
            )
        
        analysis.contributing_factors = rca_data.get('contributing_factors', [])
        analysis.root_cause_summary = rca_data.get('summary', '')
        
        return analysis
    
    def _parse_action_items(
        self,
        actions_data: Optional[List[Dict[str, Any]]]
    ) -> List[ActionItem]:
        """解析改进措施数据"""
        if not actions_data:
            return []
        
        items = []
        for item_data in actions_data:
            item = ActionItem(
                action=item_data.get('action', ''),
                owner=item_data.get('owner', ''),
                due_date=item_data.get('due_date'),
                status=item_data.get('status', 'open'),
                priority=item_data.get('priority', 'high'),
                verification_method=item_data.get('verification_method', ''),
            )
            items.append(item)
        
        return items
    
    def _calculate_duration(
        self,
        start_time: datetime,
        end_time: Optional[datetime]
    ) -> int:
        """计算持续时间（秒）"""
        if not end_time:
            end_time = datetime.now()
        
        delta = end_time - start_time
        return int(delta.total_seconds())
    
    def perform_five_why(
        self,
        problem: str,
        why_1: str,
        why_2: str,
        why_3: str,
        why_4: str,
        why_5: str,
        root_cause: str
    ) -> FiveWhyAnalysis:
        """
        执行5Why分析
        
        Args:
            problem: 问题描述
            why_1-why_5: 逐层追问
            root_cause: 最终根因
            
        Returns:
            5Why分析结果
        """
        return FiveWhyAnalysis(
            problem=problem,
            why_levels=[
                {"question": "为什么？", "answer": why_1},
                {"question": "为什么？", "answer": why_2},
                {"question": "为什么？", "answer": why_3},
                {"question": "为什么？", "answer": why_4},
                {"question": "为什么？", "answer": why_5},
            ],
            root_cause=root_cause,
            confidence="high",
        )
    
    def perform_fishbone(
        self,
        problem: str,
        categories: Dict[str, List[str]]
    ) -> FishboneAnalysis:
        """
        执行鱼骨图分析
        
        Args:
            problem: 问题描述
            categories: 类别及原因 {'人': [...], '机': [...], ...}
            
        Returns:
            鱼骨图分析结果
        """
        fishbone_cats = []
        
        category_names = {
            '人': '人员因素',
            '机': '设备因素',
            '料': '物料因素',
            '法': '方法因素',
            '环': '环境因素',
            '测': '测量因素',
        }
        
        for cat_key, causes in categories.items():
            fishbone_cats.append(FishboneCategory(
                category=category_names.get(cat_key, cat_key),
                causes=causes,
            ))
        
        # 提取根因（最深层的原因）
        root_causes = []
        for cat in fishbone_cats:
            if cat.causes:
                root_causes.extend(cat.causes)
        
        return FishboneAnalysis(
            problem=problem,
            categories=fishbone_cats,
            root_causes=root_causes,
        )
    
    def generate_html_content(
        self,
        incident_id: str,
        incident_title: str,
        severity: Severity,
        start_time: datetime,
        end_time: Optional[datetime],
        timeline: List[TimelineEvent],
        impact: ImpactAssessment,
        root_cause: RootCauseAnalysis,
        action_items: List[ActionItem],
        lessons_learned: List[str],
        duration: int,
    ) -> str:
        """生成HTML格式RCA报告内容"""
        
        severity_colors = {
            Severity.P1: '#dc3545',
            Severity.P2: '#fd7e14',
            Severity.P3: '#ffc107',
            Severity.P4: '#28a745',
        }
        
        html = f"""
<h1>RCA报告 - {incident_id}</h1>
<div class="incident-header" style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
    <h2>{incident_title}</h2>
    <p><strong>严重级别:</strong> <span style="color: {severity_colors[severity]}; font-weight: bold;">{severity.value}</span></p>
    <p><strong>发生时间:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>恢复时间:</strong> {end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else '进行中'}</p>
    <p><strong>总时长:</strong> {self._format_duration(duration)}</p>
</div>

<h2>一、故障时间线</h2>
<div class="timeline">
"""
        
        event_type_names = {
            'detection': '发现',
            'notification': '通知',
            'response': '响应',
            'mitigation': '缓解',
            'resolution': '解决',
        }
        
        for i, event in enumerate(timeline):
            event_name = event_type_names.get(event.event_type, event.event_type)
            html += f"""
    <div class="timeline-item" style="margin: 15px 0; padding-left: 20px; border-left: 2px solid #007bff;">
        <p><strong>[{event.timestamp.strftime('%H:%M:%S')}] {event_name}</strong></p>
        <p>{event.description}</p>
        <p><em>执行人: {event.actor}</em></p>
    </div>
"""
        
        html += "</div>"
        
        # 影响评估
        html += """
<h2>二、故障影响</h2>
<div class="impact">
"""
        
        if impact.affected_services:
            html += f"<p><strong>受影响服务:</strong> {', '.join(impact.affected_services)}</p>"
        
        if impact.affected_users > 0:
            html += f"<p><strong>受影响用户:</strong> {impact.affected_users}人</p>"
        
        if impact.affected_regions:
            html += f"<p><strong>受影响区域:</strong> {', '.join(impact.affected_regions)}</p>"
        
        if impact.business_loss:
            html += f"<p><strong>业务损失:</strong> {impact.business_loss}</p>"
        
        if impact.revenue_impact > 0:
            html += f"<p><strong>收入影响:</strong> ¥{impact.revenue_impact:,.2f}</p>"
        
        if impact.customer_impact:
            html += f"<p><strong>客户影响:</strong> {impact.customer_impact}</p>"
        
        html += "</div>"
        
        # 根因分析
        html += "<h2>三、根因分析</h2>"
        
        if root_cause.five_why:
            html += self._generate_five_why_html(root_cause.five_why)
        
        if root_cause.fishbone:
            html += self._generate_fishbone_html(root_cause.fishbone)
        
        if root_cause.contributing_factors:
            html += "<h3>促成因素</h3><ul>"
            for factor in root_cause.contributing_factors:
                html += f"<li>{factor}</li>"
            html += "</ul>"
        
        # 改进措施
        if action_items:
            html += "<h2>四、改进措施</h2><table>"
            html += "<tr><th>措施</th><th>负责人</th><th>截止日期</th><th>优先级</th><th>状态</th></tr>"
            
            for item in action_items:
                html += f"<tr><td>{item.action}</td><td>{item.owner}</td>"
                html += f"<td>{item.due_date.strftime('%Y-%m-%d') if item.due_date else '待定'}</td>"
                html += f"<td>{item.priority.upper()}</td><td>{item.status}</td></tr>"
            
            html += "</table>"
        
        # 经验教训
        if lessons_learned:
            html += "<h2>五、经验教训</h2><ul>"
            for lesson in lessons_learned:
                html += f"<li>{lesson}</li>"
            html += "</ul>"
        
        # 预防建议
        html += """
<h2>六、预防建议</h2>
<ul>
    <li>建立完善的监控系统，确保故障及时发现</li>
    <li>制定详细的应急预案，定期演练</li>
    <li>加强值班人员培训，提高故障处理能力</li>
    <li>建立变更管理流程，减少变更风险</li>
</ul>
"""
        
        return html
    
    def _generate_five_why_html(self, five_why: FiveWhyAnalysis) -> str:
        """生成5Why分析HTML"""
        html = """
<div class="five-why" style="background: #e7f1ff; padding: 20px; border-radius: 8px;">
    <h3>5Why分析法</h3>
    <p><strong>问题:</strong> """ + five_why.problem + """</p>
    <div style="margin-left: 20px;">
"""
        
        for i, level in enumerate(five_why.why_levels, 1):
            html += f"""
        <p><strong>{i}. {level['question']}</strong></p>
        <p style="margin-left: 20px; color: #007bff;">{level['answer']}</p>
"""
        
        confidence_colors = {'high': 'green', 'medium': 'orange', 'low': 'red'}
        color = confidence_colors.get(five_why.confidence, 'gray')
        
        html += f"""
    </div>
    <p><strong>根因:</strong> <span style="color: {color};">{five_why.root_cause}</span></p>
    <p><strong>置信度:</strong> {five_why.confidence.upper()}</p>
</div>
"""
        return html
    
    def _generate_fishbone_html(self, fishbone: FishboneAnalysis) -> str:
        """生成鱼骨图分析HTML"""
        category_colors = {
            '人员因素': '#e74c3c',
            '设备因素': '#3498db',
            '物料因素': '#9b59b6',
            '方法因素': '#f39c12',
            '环境因素': '#1abc9c',
            '测量因素': '#34495e',
        }
        
        html = f"""
<div class="fishbone" style="background: #fff3cd; padding: 20px; border-radius: 8px;">
    <h3>鱼骨图分析法</h3>
    <p><strong>问题:</strong> {fishbone.problem}</p>
    <table style="width: 100%;">
        <tr>
"""
        
        for cat in fishbone.categories:
            color = category_colors.get(cat.category, '#666')
            html += f"""
            <td style="vertical-align: top; padding: 10px;">
                <div style="background: {color}; color: white; padding: 5px 10px; border-radius: 4px;">
                    {cat.category}
                </div>
                <ul>
"""
            for cause in cat.causes:
                html += f"<li>{cause}</li>"
            html += """
                </ul>
            </td>
"""
        
        html += """
        </tr>
    </table>
</div>
"""
        return html
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{minutes}分{secs}秒"
            return f"{minutes}分"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            if secs > 0:
                return f"{hours}小时{minutes}分{secs}秒"
            elif minutes > 0:
                return f"{hours}小时{minutes}分"
            return f"{hours}小时"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            parts = [f"{days}天"]
            if hours > 0:
                parts.append(f"{hours}小时")
            if minutes > 0:
                parts.append(f"{minutes}分")
            if secs > 0:
                parts.append(f"{secs}秒")
            return ''.join(parts)
    
    def get_template_variables(self) -> Dict[str, str]:
        """获取模板变量说明"""
        return {
            'incident_id': '故障ID',
            'incident_title': '故障标题',
            'severity': '严重程度 (P1-P4)',
            'start_time': '故障开始时间',
            'end_time': '故障结束时间',
            'duration': '故障持续时间（秒）',
            'timeline': '故障时间线',
            'timeline[].timestamp': '事件时间',
            'timeline[].event_type': '事件类型',
            'timeline[].description': '事件描述',
            'timeline[].actor': '执行人',
            'impact': '影响评估',
            'impact.affected_services': '受影响服务',
            'impact.affected_users': '受影响用户数',
            'impact.revenue_impact': '收入影响',
            'root_cause': '根因分析',
            'root_cause.five_why': '5Why分析结果',
            'root_cause.fishbone': '鱼骨图分析结果',
            'action_items': '改进措施列表',
            'action_items[].action': '措施描述',
            'action_items[].owner': '负责人',
            'action_items[].due_date': '截止日期',
            'action_items[].status': '状态',
            'lessons_learned': '经验教训列表',
        }
