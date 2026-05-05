"""
报告模板管理
提供模板定义、变量管理、预览和模板市场功能
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TemplateFormat(Enum):
    """模板格式"""
    MARKDOWN = "markdown"
    HTML = "html"
    JINJA2 = "jinja2"


class TemplateCategory(Enum):
    """模板分类"""
    DAILY = "daily"           # 日巡检
    PERIODIC = "periodic"     # 周期性报告
    RCA = "rca"              # RCA报告
    CHANGE = "change"        # 变更报告
    SUMMARY = "summary"       # 总结报告
    CUSTOM = "custom"         # 自定义


@dataclass
class TemplateVariable:
    """模板变量"""
    name: str
    description: str
    var_type: str  # string/number/date/list/dict
    required: bool = True
    default_value: Any = None
    example: str = ""


@dataclass
class ReportTemplate:
    """报告模板"""
    template_id: str
    name: str
    description: str
    category: TemplateCategory
    format: TemplateFormat
    content: str
    variables: List[TemplateVariable] = field(default_factory=list)
    author: str = "System"
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    preview_data: Optional[Dict[str, Any]] = None
    isBuiltIn: bool = False


class TemplateMarket:
    """模板市场"""
    
    def __init__(self):
        """初始化模板市场"""
        self._templates: Dict[str, ReportTemplate] = {}
        self._register_builtin_templates()
    
    def _register_builtin_templates(self):
        """注册内置模板"""
        # 日巡检报告模板
        self.register(self._create_daily_report_template())
        
        # 周报模板
        self.register(self._create_weekly_report_template())
        
        # 月报模板
        self.register(self._create_monthly_report_template())
        
        # RCA报告模板
        self.register(self._create_rca_report_template())
        
        # 变更报告模板
        self.register(self._create_change_report_template())
        
        logger.info(f"Registered {len(self._templates)} builtin templates")
    
    def _create_daily_report_template(self) -> ReportTemplate:
        """创建日巡检报告模板"""
        content = """# 日巡检报告

**日期**: {{ report_date }}
**值班人**: {{ duty_person }}
**班次**: {{ duty_shift }}

## 一、监控数据汇总

| 指标 | 数值 |
|------|------|
| 主机总数 | {{ monitoring.total_hosts }} |
| 在线主机 | {{ monitoring.online_hosts }} |
| 离线主机 | {{ monitoring.offline_hosts }} |
| 平均CPU使用率 | {{ monitoring.cpu_avg_usage }}% |
| 平均内存使用率 | {{ monitoring.memory_avg_usage }}% |
| 平均磁盘使用率 | {{ monitoring.disk_avg_usage }}% |

## 二、告警统计

| 级别 | 数量 |
|------|------|
| 严重 | {{ alerts.critical_count }} |
| 警告 | {{ alerts.warning_count }} |
| 信息 | {{ alerts.info_count }} |
| 已解决 | {{ alerts.resolved_count }} |

## 三、设备状态

{% if devices %}
| 设备名称 | 类型 | 状态 | 问题 |
|----------|------|------|------|
{% for device in devices %}
| {{ device.name }} | {{ device.type }} | {{ device.status }} | {{ device.issues | join(', ') }} |
{% endfor %}
{% else %}
暂无设备异常
{% endif %}

## 四、异常记录

{% if anomalies %}
| 时间 | 来源 | 级别 | 描述 | 状态 |
|------|------|------|------|------|
{% for anomaly in anomalies %}
| {{ anomaly.time }} | {{ anomaly.source }} | {{ anomaly.severity }} | {{ anomaly.description }} | {{ anomaly.handled }} |
{% endfor %}
{% else %}
当日无异常记录
{% endif %}

## 五、巡检结论

{{ conclusions }}
"""
        
        return ReportTemplate(
            template_id="daily_report_default",
            name="标准日巡检报告",
            description="日常运维巡检标准模板",
            category=TemplateCategory.DAILY,
            format=TemplateFormat.JINJA2,
            content=content,
            variables=[
                TemplateVariable("report_date", "报告日期", "date"),
                TemplateVariable("duty_person", "值班人员", "string"),
                TemplateVariable("duty_shift", "班次", "string"),
                TemplateVariable("monitoring", "监控数据", "dict"),
                TemplateVariable("alerts", "告警数据", "dict"),
                TemplateVariable("devices", "设备列表", "list"),
                TemplateVariable("anomalies", "异常列表", "list"),
                TemplateVariable("conclusions", "巡检结论", "string"),
            ],
            tags=['daily', 'inspection'],
            isBuiltIn=True,
        )
    
    def _create_weekly_report_template(self) -> ReportTemplate:
        """创建周报模板"""
        content = """# 周报

**统计周期**: {{ period_start }} 至 {{ period_end }}
**生成时间**: {{ generated_at }}

## 一、执行摘要

{{ executive_summary }}

## 二、本周工作完成情况

{% for task in completed_tasks %}
- [x] {{ task }}
{% endfor %}

{% for task in pending_tasks %}
- [ ] {{ task }}
{% endfor %}

## 三、KPI达成情况

| 指标 | 目标 | 实际 | 达成率 |
|------|------|------|--------|
{% for kpi in kpis %}
| {{ kpi.name }} | {{ kpi.target }} | {{ kpi.actual }} | {{ kpi.achieved }}% |
{% endfor %}

## 四、问题与风险

{% if issues %}
{% for issue in issues %}
### {{ issue.title }}
- **级别**: {{ issue.severity }}
- **描述**: {{ issue.description }}
- **影响**: {{ issue.impact }}
{% endfor %}
{% else %}
本周无重大问题
{% endif %}

## 五、趋势分析

{{ trend_analysis }}

## 六、下周工作计划

{% for plan in next_week_plans %}
- {{ plan }}
{% endfor %}

## 七、改进建议

{% for suggestion in suggestions %}
### {{ suggestion.title }}
{{ suggestion.description }}
- 优先级: {{ suggestion.priority }}
- 负责人: {{ suggestion.owner }}
{% endfor %}
"""
        
        return ReportTemplate(
            template_id="weekly_report_default",
            name="标准周报",
            description="周运维工作报告模板",
            category=TemplateCategory.PERIODIC,
            format=TemplateFormat.JINJA2,
            content=content,
            variables=[
                TemplateVariable("period_start", "周期开始", "date"),
                TemplateVariable("period_end", "周期结束", "date"),
                TemplateVariable("executive_summary", "执行摘要", "string"),
                TemplateVariable("completed_tasks", "已完成任务", "list"),
                TemplateVariable("pending_tasks", "待完成任务", "list"),
                TemplateVariable("kpis", "KPI列表", "list"),
                TemplateVariable("issues", "问题列表", "list"),
                TemplateVariable("trend_analysis", "趋势分析", "string"),
                TemplateVariable("next_week_plans", "下周计划", "list"),
                TemplateVariable("suggestions", "改进建议", "list"),
            ],
            tags=['weekly', 'periodic'],
            isBuiltIn=True,
        )
    
    def _create_monthly_report_template(self) -> ReportTemplate:
        """创建月报模板"""
        content = """# 月报

**月份**: {{ month }}
**生成时间**: {{ generated_at }}

## 一、月度概览

{{ overview }}

## 二、关键指标

### 2.1 系统运行指标

| 指标 | 本月 | 上月 | 环比 |
|------|------|------|------|
{% for metric in system_metrics %}
| {{ metric.name }} | {{ metric.current }} | {{ metric.previous }} | {{ metric.change }} |
{% endfor %}

### 2.2 运维工作指标

| 指标 | 本月 | 上月 | 环比 |
|------|------|------|------|
{% for metric in ops_metrics %}
| {{ metric.name }} | {{ metric.current }} | {{ metric.previous }} | {{ metric.change }} |
{% endfor %}

## 三、KPI达成情况

{% for kpi in kpis %}
- **{{ kpi.name }}**: {{ kpi.actual }} / {{ kpi.target }} ({{ kpi.achieved }})
{% endfor %}

## 四、重大事件回顾

{% for event in major_events %}
### {{ event.date }} - {{ event.title }}
{{ event.description }}

**影响范围**: {{ event.impact }}
**处理措施**: {{ event.resolution }}
{% endfor %}

## 五、趋势分析

{{ trend_analysis }}

## 六、改进措施执行情况

| 措施 | 负责人 | 计划完成时间 | 实际完成时间 | 状态 |
|------|--------|--------------|--------------|------|
{% for action in actions %}
| {{ action.name }} | {{ action.owner }} | {{ action.plan_date }} | {{ action.actual_date }} | {{ action.status }} |
{% endfor %}

## 七、问题与风险

### 问题列表
{% for issue in issues %}
- {{ issue }}
{% endfor %}

### 风险预警
{% for risk in risks %}
- {{ risk }}
{% endfor %}

## 八、下月工作计划

{% for plan in next_month_plans %}
- {{ plan }}
{% endfor %}

## 九、资源需求

{{ resource_requirements }}
"""
        
        return ReportTemplate(
            template_id="monthly_report_default",
            name="标准月报",
            description="月度运维工作报告模板",
            category=TemplateCategory.PERIODIC,
            format=TemplateFormat.JINJA2,
            content=content,
            variables=[
                TemplateVariable("month", "月份", "string"),
                TemplateVariable("overview", "月度概览", "string"),
                TemplateVariable("system_metrics", "系统指标", "list"),
                TemplateVariable("ops_metrics", "运维指标", "list"),
                TemplateVariable("kpis", "KPI列表", "list"),
                TemplateVariable("major_events", "重大事件", "list"),
                TemplateVariable("trend_analysis", "趋势分析", "string"),
                TemplateVariable("actions", "改进措施", "list"),
                TemplateVariable("issues", "问题列表", "list"),
                TemplateVariable("risks", "风险列表", "list"),
                TemplateVariable("next_month_plans", "下月计划", "list"),
                TemplateVariable("resource_requirements", "资源需求", "string"),
            ],
            tags=['monthly', 'periodic'],
            isBuiltIn=True,
        )
    
    def _create_rca_report_template(self) -> ReportTemplate:
        """创建RCA报告模板"""
        content = """# RCA报告 - {{ incident_id }}

## 基本信息

| 项目 | 内容 |
|------|------|
| 故障ID | {{ incident_id }} |
| 故障标题 | {{ incident_title }} |
| 严重级别 | {{ severity }} |
| 发生时间 | {{ start_time }} |
| 恢复时间 | {{ end_time }} |
| 总时长 | {{ duration }} |

## 一、故障概述

{{ summary }}

## 二、故障时间线

{% for event in timeline %}
- **[{{ event.time }}]** {{ event.type }}: {{ event.description }} ({{ event.actor }})
{% endfor %}

## 三、影响评估

| 项目 | 详情 |
|------|------|
| 受影响服务 | {{ impact.services | join(', ') }} |
| 受影响用户 | {{ impact.users }} |
| 受影响区域 | {{ impact.regions | join(', ') }} |
| 业务损失 | {{ impact.business_loss }} |
| 收入影响 | {{ impact.revenue }} |

## 四、根因分析

### 分析方法

{{ analysis_method }}

### 问题描述

{{ problem_statement }}

### 5Why分析

{% for level in five_why %}
**Why {{ loop.index }}**: {{ level.question }}
{{ level.answer }}
{% endfor %}

**最终根因**: {{ root_cause }}

### 鱼骨图分析

{% for category in fishbone %}
**{{ category.name }}**:
{% for cause in category.causes %}
- {{ cause }}
{% endfor %}
{% endfor %}

### 促成因素

{% for factor in contributing_factors %}
- {{ factor }}
{% endfor %}

## 五、改进措施

| 措施 | 负责人 | 截止日期 | 优先级 | 状态 |
|------|--------|----------|--------|------|
{% for action in action_items %}
| {{ action.description }} | {{ action.owner }} | {{ action.due_date }} | {{ action.priority }} | {{ action.status }} |
{% endfor %}

## 六、经验教训

{% for lesson in lessons_learned %}
- {{ lesson }}
{% endfor %}

## 七、预防建议

{% for suggestion in prevention %}
- {{ suggestion }}
{% endfor %}

---
**报告人**: {{ author }}
**审核人**: {{ reviewer }}
**生成时间**: {{ generated_at }}
"""
        
        return ReportTemplate(
            template_id="rca_report_default",
            name="标准RCA报告",
            description="根因分析报告模板",
            category=TemplateCategory.RCA,
            format=TemplateFormat.JINJA2,
            content=content,
            variables=[
                TemplateVariable("incident_id", "故障ID", "string"),
                TemplateVariable("incident_title", "故障标题", "string"),
                TemplateVariable("severity", "严重级别", "string"),
                TemplateVariable("start_time", "开始时间", "date"),
                TemplateVariable("end_time", "结束时间", "date"),
                TemplateVariable("duration", "持续时间", "string"),
                TemplateVariable("summary", "故障概述", "string"),
                TemplateVariable("timeline", "时间线", "list"),
                TemplateVariable("impact", "影响评估", "dict"),
                TemplateVariable("analysis_method", "分析方法", "string"),
                TemplateVariable("problem_statement", "问题陈述", "string"),
                TemplateVariable("five_why", "5Why分析", "list"),
                TemplateVariable("root_cause", "根因", "string"),
                TemplateVariable("fishbone", "鱼骨图", "list"),
                TemplateVariable("contributing_factors", "促成因素", "list"),
                TemplateVariable("action_items", "改进措施", "list"),
                TemplateVariable("lessons_learned", "经验教训", "list"),
                TemplateVariable("prevention", "预防建议", "list"),
            ],
            tags=['rca', 'incident'],
            isBuiltIn=True,
        )
    
    def _create_change_report_template(self) -> ReportTemplate:
        """创建变更报告模板"""
        content = """# 变更报告 - {{ change_id }}

## 变更基本信息

| 项目 | 内容 |
|------|------|
| 变更ID | {{ change_id }} |
| 变更类型 | {{ change_type }} |
| 申请人 | {{ applicant }} |
| 申请时间 | {{ apply_time }} |
| 计划执行时间 | {{ scheduled_time }} |
| 审批状态 | {{ approval_status }} |

## 一、变更内容

### 1.1 变更背景

{{ background }}

### 1.2 变更范围

{% for scope in scopes %}
- {{ scope }}
{% endfor %}

### 1.3 变更步骤

{% for step in steps %}
{{ loop.index }}. {{ step }}
{% endfor %}

### 1.4 变更验证

{{ verification }}

## 二、风险评估

### 2.1 影响分析

{{ impact_analysis }}

### 2.2 回滚方案

{{ rollback_plan }}

### 2.3 应急预案

{% for plan in contingency %}
- {{ plan }}
{% endfor %}

## 三、审批记录

| 审批人 | 角色 | 审批时间 | 意见 |
|--------|------|----------|------|
{% for approval in approvals %}
| {{ approval.name }} | {{ approval.role }} | {{ approval.time }} | {{ approval.comment }} |
{% endfor %}

## 四、执行记录

{% if execution %}
- **开始时间**: {{ execution.start_time }}
- **结束时间**: {{ execution.end_time }}
- **执行人**: {{ execution.executor }}
- **执行结果**: {{ execution.result }}

### 执行详情

{{ execution.details }}
{% else %}
变更尚未执行
{% endif %}

## 五、验证结果

{{ verification_result }}

## 六、总结

{{ summary }}
"""
        
        return ReportTemplate(
            template_id="change_report_default",
            name="标准变更报告",
            description="变更执行报告模板",
            category=TemplateCategory.CHANGE,
            format=TemplateFormat.JINJA2,
            content=content,
            variables=[
                TemplateVariable("change_id", "变更ID", "string"),
                TemplateVariable("change_type", "变更类型", "string"),
                TemplateVariable("applicant", "申请人", "string"),
                TemplateVariable("apply_time", "申请时间", "date"),
                TemplateVariable("scheduled_time", "计划时间", "date"),
                TemplateVariable("background", "变更背景", "string"),
                TemplateVariable("scopes", "变更范围", "list"),
                TemplateVariable("steps", "变更步骤", "list"),
                TemplateVariable("verification", "验证方法", "string"),
                TemplateVariable("impact_analysis", "影响分析", "string"),
                TemplateVariable("rollback_plan", "回滚方案", "string"),
                TemplateVariable("contingency", "应急预案", "list"),
                TemplateVariable("approvals", "审批记录", "list"),
                TemplateVariable("execution", "执行记录", "dict"),
                TemplateVariable("verification_result", "验证结果", "string"),
                TemplateVariable("summary", "总结", "string"),
            ],
            tags=['change'],
            isBuiltIn=True,
        )
    
    def register(self, template: ReportTemplate):
        """注册模板"""
        self._templates[template.template_id] = template
        logger.info(f"Registered template: {template.template_id}")
    
    def unregister(self, template_id: str):
        """取消注册模板"""
        if template_id in self._templates:
            del self._templates[template_id]
            logger.info(f"Unregistered template: {template_id}")
    
    def get(self, template_id: str) -> Optional[ReportTemplate]:
        """获取模板"""
        return self._templates.get(template_id)
    
    def list(
        self,
        category: Optional[TemplateCategory] = None,
        tag: Optional[str] = None,
        include_builtin: bool = True,
    ) -> List[ReportTemplate]:
        """列出模板"""
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if tag:
            templates = [t for t in templates if tag in t.tags]
        
        if not include_builtin:
            templates = [t for t in templates if not t.isBuiltIn]
        
        return sorted(templates, key=lambda t: t.name)
    
    def search(self, keyword: str) -> List[ReportTemplate]:
        """搜索模板"""
        keyword = keyword.lower()
        results = []
        
        for template in self._templates.values():
            if (keyword in template.name.lower() or
                keyword in template.description.lower() or
                any(keyword in tag.lower() for tag in template.tags)):
                results.append(template)
        
        return results


class TemplateManager:
    """
    模板管理器
    
    功能：
    - 模板定义（Markdown/HTML）
    - 模板变量管理
    - 模板预览
    - 模板市场
    """
    
    def __init__(self, market: Optional[TemplateMarket] = None):
        """
        初始化模板管理器
        
        Args:
            market: 模板市场实例
        """
        self._market = market or TemplateMarket()
        self._custom_templates: Dict[str, ReportTemplate] = {}
    
    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        category: TemplateCategory,
        content: str,
        format: TemplateFormat = TemplateFormat.JINJA2,
        variables: Optional[List[TemplateVariable]] = None,
        tags: Optional[List[str]] = None,
    ) -> ReportTemplate:
        """
        创建模板
        
        Args:
            template_id: 模板ID
            name: 模板名称
            description: 模板描述
            category: 分类
            content: 模板内容
            format: 格式
            variables: 变量列表
            tags: 标签
            
        Returns:
            创建的模板
        """
        template = ReportTemplate(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            format=format,
            content=content,
            variables=variables or [],
            tags=tags or [],
            isBuiltIn=False,
        )
        
        self._custom_templates[template_id] = template
        self._market.register(template)
        
        return template
    
    def update_template(
        self,
        template_id: str,
        **updates
    ) -> Optional[ReportTemplate]:
        """
        更新模板
        
        Args:
            template_id: 模板ID
            **updates: 更新字段
            
        Returns:
            更新后的模板
        """
        template = self.get_template(template_id)
        
        if not template:
            return None
        
        if template.isBuiltIn:
            logger.warning(f"Cannot update built-in template: {template_id}")
            return None
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.now()
        
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """
        删除模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            是否删除成功
        """
        if template_id not in self._custom_templates:
            return False
        
        del self._custom_templates[template_id]
        self._market.unregister(template_id)
        
        return True
    
    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """获取模板"""
        return self._market.get(template_id)
    
    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        include_builtin: bool = True,
    ) -> List[ReportTemplate]:
        """列出模板"""
        templates = list(self._custom_templates.values())
        
        if include_builtin:
            templates.extend(self._market.list(
                category=category,
                include_builtin=True,
            ))
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        # 去重
        seen = set()
        unique_templates = []
        for t in templates:
            if t.template_id not in seen:
                seen.add(t.template_id)
                unique_templates.append(t)
        
        return unique_templates
    
    def preview(
        self,
        template_id: str,
        preview_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        预览模板
        
        Args:
            template_id: 模板ID
            preview_data: 预览数据
            
        Returns:
            渲染后的内容
        """
        template = self.get_template(template_id)
        
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # 使用预览数据或生成示例数据
        data = preview_data or template.preview_data or self._generate_preview_data(template)
        
        # 渲染模板
        from jinja2 import Template
        
        try:
            return Template(template.content).render(**data)
        except Exception as e:
            logger.error(f"Error rendering template preview: {e}")
            return f"Error rendering preview: {e}"
    
    def _generate_preview_data(self, template: ReportTemplate) -> Dict[str, Any]:
        """生成预览数据"""
        data = {}
        
        for var in template.variables:
            if var.default_value is not None:
                data[var.name] = var.default_value
            else:
                data[var.name] = self._generate_sample_value(var)
        
        return data
    
    def _generate_sample_value(self, var: TemplateVariable) -> Any:
        """生成示例值"""
        samples = {
            'string': '示例文本',
            'number': 100,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'list': ['项目1', '项目2', '项目3'],
            'dict': {'key1': 'value1', 'key2': 'value2'},
        }
        
        return samples.get(var.var_type, '')
    
    def export_template(self, template_id: str) -> Dict[str, Any]:
        """导出模板"""
        template = self.get_template(template_id)
        
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        return {
            'template_id': template.template_id,
            'name': template.name,
            'description': template.description,
            'category': template.category.value,
            'format': template.format.value,
            'content': template.content,
            'variables': [
                {
                    'name': v.name,
                    'description': v.description,
                    'type': v.var_type,
                    'required': v.required,
                    'default_value': v.default_value,
                }
                for v in template.variables
            ],
            'tags': template.tags,
        }
    
    def import_template(self, template_data: Dict[str, Any]) -> ReportTemplate:
        """导入模板"""
        variables = []
        
        for var_data in template_data.get('variables', []):
            variables.append(TemplateVariable(
                name=var_data['name'],
                description=var_data.get('description', ''),
                var_type=var_data.get('type', 'string'),
                required=var_data.get('required', True),
                default_value=var_data.get('default_value'),
            ))
        
        template = self.create_template(
            template_id=template_data['template_id'],
            name=template_data['name'],
            description=template_data.get('description', ''),
            category=TemplateCategory(template_data.get('category', 'custom')),
            content=template_data['content'],
            format=TemplateFormat(template_data.get('format', 'jinja2')),
            variables=variables,
            tags=template_data.get('tags', []),
        )
        
        return template
    
    @property
    def market(self) -> TemplateMarket:
        """获取模板市场"""
        return self._market
