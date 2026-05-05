"""
周期性报告生成器
生成周报、月报、年报，包含趋势分析、对比分析、改进建议、KPI达成情况
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .reporter import ReportGenerator, ReportType, Report, ReportStatus

logger = logging.getLogger(__name__)


class ReportPeriod(Enum):
    """报告周期枚举"""
    WEEKLY = "weekly"     # 周报
    MONTHLY = "monthly"   # 月报
    YEARLY = "yearly"     # 年报


@dataclass
class TrendData:
    """趋势数据"""
    period: str = ""
    value: float = 0.0
    change_rate: float = 0.0  # 变化率百分比
    trend: str = ""  # up/down/stable


@dataclass
class KPIMetric:
    """KPI指标"""
    name: str = ""
    target: float = 0.0
    actual: float = 0.0
    unit: str = "%"
    achieved: bool = False
    gap: float = 0.0


@dataclass
class ComparisonData:
    """对比数据"""
    current_period: str = ""
    previous_period: str = ""
    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    improvements: List[str] = field(default_factory=list)
    regressions: List[str] = field(default_factory=list)


@dataclass
class ImprovementSuggestion:
    """改进建议"""
    category: str = ""
    title: str = ""
    description: str = ""
    priority: str = "medium"  # high/medium/low
    estimated_impact: str = ""
    owner: str = ""


class PeriodicReportGenerator:
    """
    周期性报告生成器
    
    生成内容包括：
    - 周报/月报/年报
    - 趋势分析
    - 对比分析
    - 改进建议
    - KPI达成情况
    """
    
    # 周报周期
    WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    def __init__(
        self,
        report_generator: ReportGenerator,
        data_sources: Optional[Dict[str, Any]] = None
    ):
        """
        初始化周期性报告生成器
        
        Args:
            report_generator: 报告生成器实例
            data_sources: 数据源配置
        """
        self._report_generator = report_generator
        self._data_sources = data_sources or {}
    
    def generate(
        self,
        period: ReportPeriod,
        period_start: datetime,
        period_end: datetime,
        data: Optional[Dict[str, Any]] = None,
        kpi_targets: Optional[Dict[str, float]] = None,
        previous_period_data: Optional[Dict[str, Any]] = None,
    ) -> Report:
        """
        生成周期性报告
        
        Args:
            period: 报告周期
            period_start: 周期开始时间
            period_end: 周期结束时间
            data: 报告数据
            kpi_targets: KPI目标
            previous_period_data: 上周期数据（用于对比）
            
        Returns:
            生成的报告对象
        """
        # 确定报告类型
        report_type_map = {
            ReportPeriod.WEEKLY: ReportType.WEEKLY,
            ReportPeriod.MONTHLY: ReportType.MONTHLY,
            ReportPeriod.YEARLY: ReportType.YEARLY,
        }
        report_type = report_type_map.get(period, ReportType.WEEKLY)
        
        # 生成标题
        period_str = self._format_period_string(period, period_start, period_end)
        
        # 创建报告
        report = self._report_generator.create_report(
            report_type=report_type,
            title=f"{period.value.capitalize()}报告 - {period_str}",
            description=self._generate_description(period, period_start, period_end),
            period_start=period_start,
            period_end=period_end,
            tags=[period.value, 'periodic'],
        )
        
        # 收集数据
        context = {
            'period': period,
            'period_start': period_start,
            'period_end': period_end,
            'period_str': period_str,
            'data': data or {},
            'kpi_targets': kpi_targets or {},
            'trends': self._analyze_trends(data),
            'comparison': self._analyze_comparison(data, previous_period_data),
            'kpis': self._calculate_kpis(data, kpi_targets),
            'suggestions': self._generate_suggestions(data),
        }
        
        # 生成报告
        return self._report_generator.generate(report, context=context)
    
    def generate_weekly(
        self,
        week_start: Optional[datetime] = None,
        data: Optional[Dict[str, Any]] = None,
        kpi_targets: Optional[Dict[str, float]] = None,
    ) -> Report:
        """
        生成周报
        
        Args:
            week_start: 周开始日期（默认为上周一）
            data: 报告数据
            kpi_targets: KPI目标
            
        Returns:
            生成的报告对象
        """
        if week_start is None:
            # 默认上周
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday() + 7)
        
        week_start = week_start.replace(hour=0, minute=0, second=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return self.generate(
            period=ReportPeriod.WEEKLY,
            period_start=week_start,
            period_end=week_end,
            data=data,
            kpi_targets=kpi_targets,
        )
    
    def generate_monthly(
        self,
        month: Optional[int] = None,
        year: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        kpi_targets: Optional[Dict[str, float]] = None,
    ) -> Report:
        """
        生成月报
        
        Args:
            month: 月份（1-12），默认为上个月
            year: 年份，默认为今年
            data: 报告数据
            kpi_targets: KPI目标
            
        Returns:
            生成的报告对象
        """
        if month is None or year is None:
            today = datetime.now()
            if month is None:
                month = today.month - 1 if today.month > 1 else 12
            if year is None:
                year = today.year if today.month > 1 else today.year - 1
        
        # 月初
        month_start = datetime(year, month, 1, 0, 0, 0)
        
        # 月末
        if month == 12:
            month_end = datetime(year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
        else:
            month_end = datetime(year, month + 1, 1, 0, 0, 0) - timedelta(seconds=1)
        
        return self.generate(
            period=ReportPeriod.MONTHLY,
            period_start=month_start,
            period_end=month_end,
            data=data,
            kpi_targets=kpi_targets,
        )
    
    def generate_yearly(
        self,
        year: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        kpi_targets: Optional[Dict[str, float]] = None,
    ) -> Report:
        """
        生成年报
        
        Args:
            year: 年份，默认为去年
            data: 报告数据
            kpi_targets: KPI目标
            
        Returns:
            生成的报告对象
        """
        if year is None:
            year = datetime.now().year - 1
        
        year_start = datetime(year, 1, 1, 0, 0, 0)
        year_end = datetime(year, 12, 31, 23, 59, 59)
        
        return self.generate(
            period=ReportPeriod.YEARLY,
            period_start=year_start,
            period_end=year_end,
            data=data,
            kpi_targets=kpi_targets,
        )
    
    def _format_period_string(
        self,
        period: ReportPeriod,
        period_start: datetime,
        period_end: datetime
    ) -> str:
        """格式化周期字符串"""
        if period == ReportPeriod.WEEKLY:
            return f"{period_start.strftime('%Y-%m-%d')} 至 {period_end.strftime('%Y-%m-%d')}"
        elif period == ReportPeriod.MONTHLY:
            return period_start.strftime('%Y年%m月')
        elif period == ReportPeriod.YEARLY:
            return period_start.strftime('%Y年')
        else:
            return f"{period_start.strftime('%Y-%m-%d')} 至 {period_end.strftime('%Y-%m-%d')}"
    
    def _generate_description(
        self,
        period: ReportPeriod,
        period_start: datetime,
        period_end: datetime
    ) -> str:
        """生成报告描述"""
        period_str = self._format_period_string(period, period_start, period_end)
        return f"{period.value.capitalize()}运维{period_str}总结报告"
    
    def _analyze_trends(self, data: Optional[Dict[str, Any]]) -> Dict[str, List[TrendData]]:
        """分析趋势"""
        trends = {}
        
        if not data:
            return trends
        
        # 提取趋势数据
        metric_data = data.get('trends', {})
        
        for metric_name, values in metric_data.items():
            trend_list = []
            
            if isinstance(values, list):
                for i, val in enumerate(values):
                    trend = TrendData(
                        period=f"Period {i+1}",
                        value=val,
                    )
                    
                    # 计算变化率
                    if i > 0:
                        prev = values[i - 1]
                        if prev != 0:
                            trend.change_rate = ((val - prev) / prev) * 100
                            trend.trend = 'up' if val > prev else ('down' if val < prev else 'stable')
                    
                    trend_list.append(trend)
            
            trends[metric_name] = trend_list
        
        return trends
    
    def _analyze_comparison(
        self,
        current_data: Optional[Dict[str, Any]],
        previous_data: Optional[Dict[str, Any]]
    ) -> ComparisonData:
        """分析对比数据"""
        comparison = ComparisonData()
        
        if not current_data:
            return comparison
        
        # 提取关键指标对比
        current_metrics = current_data.get('metrics', {})
        previous_metrics = previous_data.get('metrics', {}) if previous_data else {}
        
        for metric_name, current_value in current_metrics.items():
            previous_value = previous_metrics.get(metric_name, 0)
            
            comparison.metrics[metric_name] = {
                'current': current_value,
                'previous': previous_value,
                'change': current_value - previous_value,
                'change_rate': ((current_value - previous_value) / previous_value * 100) if previous_value else 0,
            }
            
            # 判断改进或退化
            if current_value > previous_value:
                comparison.improvements.append(f"{metric_name}提升{comparison.metrics[metric_name]['change_rate']:.1f}%")
            elif current_value < previous_value:
                comparison.regressions.append(f"{metric_name}下降{abs(comparison.metrics[metric_name]['change_rate']):.1f}%")
        
        return comparison
    
    def _calculate_kpis(
        self,
        data: Optional[Dict[str, Any]],
        targets: Optional[Dict[str, float]]
    ) -> List[KPIMetric]:
        """计算KPI达成情况"""
        kpis = []
        
        if not data or not targets:
            return kpis
        
        actuals = data.get('kpis', {})
        
        for metric_name, target in targets.items():
            actual = actuals.get(metric_name, 0)
            
            kpi = KPIMetric(
                name=metric_name,
                target=target,
                actual=actual,
                achieved=actual >= target,
                gap=target - actual,
            )
            
            kpis.append(kpi)
        
        return kpis
    
    def _generate_suggestions(
        self,
        data: Optional[Dict[str, Any]]
    ) -> List[ImprovementSuggestion]:
        """生成改进建议"""
        suggestions = []
        
        if not data:
            return suggestions
        
        # 从数据中提取建议
        suggested = data.get('suggestions', [])
        
        for sug in suggested:
            suggestion = ImprovementSuggestion(
                category=sug.get('category', ''),
                title=sug.get('title', ''),
                description=sug.get('description', ''),
                priority=sug.get('priority', 'medium'),
                estimated_impact=sug.get('estimated_impact', ''),
                owner=sug.get('owner', ''),
            )
            suggestions.append(suggestion)
        
        # 自动生成建议
        metrics = data.get('metrics', {})
        
        # CPU使用率高建议
        if metrics.get('cpu_avg') and metrics['cpu_avg'] > 80:
            suggestions.append(ImprovementSuggestion(
                category='性能优化',
                title='CPU使用率过高',
                description=f"平均CPU使用率达到{metrics['cpu_avg']:.1f}%，建议进行资源优化或扩容",
                priority='high',
                estimated_impact='提升系统响应速度20%',
            ))
        
        # 可用性低建议
        if metrics.get('availability') and metrics['availability'] < 99.9:
            suggestions.append(ImprovementSuggestion(
                category='可用性提升',
                title='系统可用性需提升',
                description=f"当前可用性{metrics['availability']:.2f}%，未达到99.9%目标",
                priority='high',
                estimated_impact='减少业务中断时间',
            ))
        
        return suggestions
    
    def generate_html_content(
        self,
        period: ReportPeriod,
        period_start: datetime,
        period_end: datetime,
        data: Dict[str, Any],
        trends: Dict[str, List[TrendData]],
        comparison: ComparisonData,
        kpis: List[KPIMetric],
        suggestions: List[ImprovementSuggestion],
    ) -> str:
        """生成HTML格式报告内容"""
        period_str = self._format_period_string(period, period_start, period_end)
        
        html = f"""
<h1>{period.value.capitalize()}报告</h1>
<p><strong>统计周期:</strong> {period_str}</p>
<p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<h2>一、执行摘要</h2>
<div class="executive-summary">
    <p>本报告总结{period_str}期间的运维工作情况，包括系统运行状态、告警处理、KPI达成情况等。</p>
</div>
"""
        
        # 关键指标概览
        metrics = data.get('metrics', {})
        html += "<h2>二、关键指标概览</h2><table>"
        html += "<tr><th>指标</th><th>数值</th><th>环比</th></tr>"
        
        for metric_name, values in metrics.items():
            display_name = self._get_metric_display_name(metric_name)
            change_rate = 0
            trend_icon = "→"
            
            if comparison.metrics.get(metric_name):
                change_rate = comparison.metrics[metric_name]['change_rate']
                if change_rate > 0:
                    trend_icon = f"↑ {change_rate:.1f}%"
                elif change_rate < 0:
                    trend_icon = f"↓ {abs(change_rate):.1f}%"
            
            html += f"<tr><td>{display_name}</td><td>{values}</td><td>{trend_icon}</td></tr>"
        
        html += "</table>"
        
        # 趋势分析
        if trends:
            html += "<h2>三、趋势分析</h2>"
            
            for metric_name, trend_data in trends.items():
                display_name = self._get_metric_display_name(metric_name)
                html += f"<h3>{display_name}趋势</h3><table>"
                html += "<tr><th>周期</th><th>数值</th><th>变化</th></tr>"
                
                for trend in trend_data:
                    change_str = f"{trend.trend} {trend.change_rate:.1f}%" if trend.change_rate else "-"
                    html += f"<tr><td>{trend.period}</td><td>{trend.value}</td><td>{change_str}</td></tr>"
                
                html += "</table>"
        
        # KPI达成情况
        if kpis:
            html += "<h2>四、KPI达成情况</h2><table>"
            html += "<tr><th>KPI指标</th><th>目标</th><th>实际</th><th>达成</th><th>差距</th></tr>"
            
            achieved_count = sum(1 for k in kpis if k.achieved)
            
            for kpi in kpis:
                status = "✓ 达成" if kpi.achieved else "✗ 未达成"
                gap_str = f"{kpi.gap:.1f}{kpi.unit}" if kpi.gap > 0 else "-"
                html += f"<tr><td>{kpi.name}</td><td>{kpi.target}{kpi.unit}</td><td>{kpi.actual}{kpi.unit}</td><td>{status}</td><td>{gap_str}</td></tr>"
            
            html += "</table>"
            html += f"<p><strong>总体达成率:</strong> {achieved_count}/{len(kpis)} ({(achieved_count/len(kpis)*100) if kpis else 0:.1f}%)</p>"
        
        # 对比分析
        if comparison.improvements or comparison.regressions:
            html += "<h2>五、环比分析</h2>"
            
            if comparison.improvements:
                html += "<h3>改进项</h3><ul>"
                for imp in comparison.improvements:
                    html += f"<li>{imp}</li>"
                html += "</ul>"
            
            if comparison.regressions:
                html += "<h3>退步项</h3><ul>"
                for reg in comparison.regressions:
                    html += f"<li>{reg}</li>"
                html += "</ul>"
        
        # 改进建议
        if suggestions:
            html += "<h2>六、改进建议</h2>"
            
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            sorted_suggestions = sorted(suggestions, key=lambda s: priority_order.get(s.priority, 1))
            
            for sug in sorted_suggestions:
                priority_color = {'high': 'red', 'medium': 'orange', 'low': 'green'}.get(sug.priority, 'gray')
                html += f"""
<div class="suggestion" style="border-left: 4px solid {priority_color}; padding: 10px; margin: 10px 0;">
    <h4>{sug.title} <span style="color: {priority_color};">[{sug.priority.upper()}]</span></h4>
    <p><strong>类别:</strong> {sug.category}</p>
    <p>{sug.description}</p>
    <p><strong>预计影响:</strong> {sug.estimated_impact}</p>
    <p><strong>负责人:</strong> {sug.owner or '待指定'}</p>
</div>
"""
        
        # 下周期计划
        html += """
<h2>七、下周期工作计划</h2>
<ul>
    <li>继续监控系统运行状态</li>
    <li>跟进本周期遗留问题</li>
    <li>执行已批准的变更计划</li>
</ul>
"""
        
        return html
    
    @staticmethod
    def _get_metric_display_name(metric_name: str) -> str:
        """获取指标显示名称"""
        name_map = {
            'cpu_avg': '平均CPU使用率',
            'memory_avg': '平均内存使用率',
            'disk_avg': '平均磁盘使用率',
            'availability': '系统可用性',
            'mttr': '平均修复时间',
            'mttf': '平均故障间隔',
            'incident_count': '故障数量',
            'alert_count': '告警数量',
            'change_count': '变更数量',
        }
        return name_map.get(metric_name, metric_name)
    
    def get_template_variables(self) -> Dict[str, str]:
        """获取模板变量说明"""
        return {
            'period': '报告周期类型',
            'period_start': '周期开始时间',
            'period_end': '周期结束时间',
            'period_str': '周期字符串',
            'data': '原始数据',
            'data.metrics': '关键指标数据',
            'data.trends': '趋势数据',
            'trends': '趋势分析结果',
            'comparison': '对比分析结果',
            'comparison.improvements': '改进项列表',
            'comparison.regressions': '退步项列表',
            'kpis': 'KPI达成情况列表',
            'kpis[].name': 'KPI名称',
            'kpis[].target': 'KPI目标值',
            'kpis[].actual': 'KPI实际值',
            'kpis[].achieved': '是否达成',
            'suggestions': '改进建议列表',
            'suggestions[].title': '建议标题',
            'suggestions[].priority': '优先级',
            'suggestions[].description': '建议描述',
        }
