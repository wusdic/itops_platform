"""
BM-05 AI Copilot - Prompt Engine
Prompt引擎 - 模板管理、变量填充、Chain of Thought支持
"""

import re
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """模板类型"""
    FAULT_DIAGNOSIS = "fault_diagnosis"
    DAILY_REPORT = "daily_report"
    WEEKLY_REPORT = "weekly_report"
    SOP_GENERATION = "sop_generation"
    CHANGE_REVIEW = "change_review"
    QA = "qa"
    CUSTOM = "custom"


@dataclass
class PromptTemplate:
    """Prompt模板"""
    name: str
    template: str
    template_type: TemplateType
    description: str = ""
    variables: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def extract_variables(self) -> List[str]:
        """从模板中提取变量名"""
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, self.template)
        return list(set(matches))


@dataclass
class ChainOfThoughtStep:
    """Chain of Thought步骤"""
    step_number: int
    instruction: str
    expected_output: str = ""
    is_required: bool = True


@dataclass 
class ChainOfThoughtConfig:
    """Chain of Thought配置"""
    enabled: bool = True
    max_steps: int = 5
    steps: List[ChainOfThoughtStep] = field(default_factory=list)
    final_answer_instruction: str = "基于以上分析，给出最终答案或建议"


class PromptEngine:
    """Prompt引擎"""
    
    # 内置模板
    BUILTIN_TEMPLATES = {
        TemplateType.FAULT_DIAGNOSIS: PromptTemplate(
            name="故障诊断",
            template_type=TemplateType.FAULT_DIAGNOSIS,
            description="用于分析和诊断系统故障",
            template="""你是一个经验丰富的IT运维工程师，擅长故障诊断。请分析以下故障信息：

【故障描述】
{{fault_description}}

【故障时间】
{{fault_time}}

【相关日志】
{{logs}}

【环境信息】
{{environment_info}}

{% if related_cases %}
【历史故障案例】
{{related_cases}}
{% endif %}

请按以下步骤进行分析：
1. 理解故障现象
2. 分析可能的原因
3. 制定排查计划
4. 给出解决建议

请用结构化的方式输出诊断报告。""",
            variables=["fault_description", "fault_time", "logs", "environment_info", "related_cases"]
        ),
        
        TemplateType.DAILY_REPORT: PromptTemplate(
            name="日报生成",
            template_type=TemplateType.DAILY_REPORT,
            description="生成每日运维报告",
            template="""请根据以下信息生成今日运维日报：

【日期】
{{date}}

【系统运行状态】
{{system_status}}

【今日工作内容】
{{work_items}}

【告警汇总】
{{alerts_summary}}

【事件汇总】
{{incidents_summary}}

【明日工作计划】
{{tomorrow_plan}}

【备注】
{{notes}}

请生成一份专业的日报，格式规范、内容完整。""",
            variables=["date", "system_status", "work_items", "alerts_summary", "incidents_summary", "tomorrow_plan", "notes"]
        ),
        
        TemplateType.WEEKLY_REPORT: PromptTemplate(
            name="周报生成",
            template_type=TemplateType.WEEKLY_REPORT,
            description="生成每周运维报告",
            template="""请根据以下信息生成本周运维周报：

【周期】
{{week_start}} 至 {{week_end}}

【本周工作概述】
{{summary}}

【系统运行统计】
{{system_stats}}

【主要工作成果】
{{achievements}}

【问题与改进】
{{issues_and_improvements}}

【下周计划】
{{next_week_plan}}

【指标达成情况】
{{metrics}}

【风险提示】
{{risks}}

请生成一份专业的周报，包含数据分析和趋势洞察。""",
            variables=["week_start", "week_end", "summary", "system_stats", "achievements", 
                      "issues_and_improvements", "next_week_plan", "metrics", "risks"]
        ),
        
        TemplateType.SOP_GENERATION: PromptTemplate(
            name="SOP生成",
            template_type=TemplateType.SOP_GENERATION,
            description="生成标准操作流程",
            template="""请为以下操作生成标准操作流程(SOP)：

【操作名称】
{{operation_name}}

【操作目的】
{{purpose}}

【适用范围】
{{scope}}

【前置条件】
{{prerequisites}}

【操作步骤】
{{operation_steps}}

{% if risk_points %}
【风险点】
{{risk_points}}
{% endif %}

{% if related_docs %}
【相关文档】
{{related_docs}}
{% endif %}

请生成一份详细的SOP文档，包含：操作步骤、注意事项、回滚方案、验证方法。""",
            variables=["operation_name", "purpose", "scope", "prerequisites", 
                      "operation_steps", "risk_points", "related_docs"]
        ),
        
        TemplateType.CHANGE_REVIEW: PromptTemplate(
            name="变更评审",
            template_type=TemplateType.CHANGE_REVIEW,
            description="辅助变更评审",
            template="""请对以下变更进行评审：

【变更标题】
{{change_title}}

【变更类型】
{{change_type}}

【变更描述】
{{change_description}}

【影响范围】
{{impact_scope}}

【实施计划】
{{implementation_plan}}

【回滚方案】
{{rollback_plan}}

【测试计划】
{{test_plan}}

{% if risk_assessment %}
【风险评估】
{{risk_assessment}}
{% endif %}

请从以下维度进行评审：
1. 变更必要性
2. 技术可行性
3. 风险可控性
4. 影响范围评估
5. 审批建议

请给出专业的评审意见和改进建议。""",
            variables=["change_title", "change_type", "change_description", "impact_scope",
                      "implementation_plan", "rollback_plan", "test_plan", "risk_assessment"]
        ),
        
        TemplateType.QA: PromptTemplate(
            name="智能问答",
            template_type=TemplateType.QA,
            description="IT运维知识问答",
            template="""【系统提示】
你是一个专业的IT运维知识助手。请根据以下背景知识回答用户问题。

{% if context %}
【相关背景知识】
{{context}}
{% endif %}

【用户问题】
{{question}}

{% if additional_info %}
【补充信息】
{{additional_info}}
{% endif %}

请：
1. 准确理解用户问题
2. 结合背景知识给出专业回答
3. 如需进一步信息，请明确指出
4. 回答要清晰、准确、实用""",
            variables=["context", "question", "additional_info"]
        )
    }
    
    # Chain of Thought 模板
    COT_STEPS = {
        TemplateType.FAULT_DIAGNOSIS: [
            ChainOfThoughtStep(1, "理解故障现象", "故障的表象是什么？", True),
            ChainOfThoughtStep(2, "收集信息", "需要哪些日志、监控数据、配置信息？", True),
            ChainOfThoughtStep(3, "分析原因", "可能的原因有哪些？按可能性排序", True),
            ChainOfThoughtStep(4, "制定方案", "如何验证和解决问题？", True),
            ChainOfThoughtStep(5, "总结建议", "给出最终诊断结论和解决建议", True),
        ],
        TemplateType.CHANGE_REVIEW: [
            ChainOfThoughtStep(1, "理解变更", "变更的目的是什么？", True),
            ChainOfThoughtStep(2, "评估影响", "会对哪些系统产生影响？", True),
            ChainOfThoughtStep(3, "分析风险", "可能存在哪些风险？", True),
            ChainOfThoughtStep(4, "检查方案", "实施方案是否完善？", True),
            ChainOfThoughtStep(5, "给出建议", "是否批准？需要什么改进？", True),
        ]
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化Prompt引擎
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.prompts_config = self.config.get("prompts", {})
        self.system_prompt = self.prompts_config.get("system_prompt", "")
        self.cot_config = self.config.get("chain_of_thought", {})
        
        # 模板存储
        self._templates: Dict[str, PromptTemplate] = {}
        self._custom_variables: Dict[str, Callable] = {}
        
        # 初始化内置模板
        self._init_builtin_templates()
        
    def _init_builtin_templates(self):
        """初始化内置模板"""
        for template_type, template in self.BUILTIN_TEMPLATES.items():
            self._templates[template_type.value] = template
            
        # 从配置加载模板
        templates_config = self.prompts_config.get("templates", {})
        for key, template_info in templates_config.items():
            if key in self._templates:
                # 更新已有模板
                self._templates[key].metadata.update(template_info)
            else:
                # 添加新模板
                self._templates[key] = PromptTemplate(
                    name=template_info.get("name", key),
                    template_type=TemplateType.CUSTOM,
                    description=template_info.get("description", ""),
                    template=template_info.get("template", ""),
                    metadata=template_info
                )
    
    def get_template(self, template_type: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self._templates.get(template_type)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有模板"""
        return [
            {
                "key": key,
                "name": t.name,
                "description": t.description,
                "template_type": t.template_type.value,
                "variables": t.extract_variables()
            }
            for key, t in self._templates.items()
        ]
    
    def register_template(self, key: str, template: PromptTemplate):
        """注册自定义模板"""
        self._templates[key] = template
        
    def register_variable_handler(self, var_name: str, handler: Callable):
        """注册变量处理器"""
        self._custom_variables[var_name] = handler
    
    def fill_template(self, template: PromptTemplate, variables: Dict[str, Any],
                      strict: bool = True) -> str:
        """
        填充模板变量
        
        Args:
            template: PromptTemplate对象
            variables: 变量字典
            strict: 是否严格检查缺失变量
            
        Returns:
            填充后的prompt
        """
        result = template.template
        
        # 检查缺失变量
        required_vars = template.extract_variables()
        missing = [v for v in required_vars if v not in variables]
        
        if missing and strict:
            raise ValueError(f"Missing required variables: {missing}")
        
        # 替换变量
        for var_name in required_vars:
            value = variables.get(var_name, "")
            if value is None:
                value = ""
            # 处理多行内容
            value_str = str(value).strip()
            result = result.replace(f"{{{{{var_name}}}}}", value_str)
        
        # 清理未填充的变量
        result = re.sub(r'\{\{(\w+)\}\}', '', result)
        
        # 清理空的条件块
        result = self._clean_empty_conditionals(result)
        
        return result.strip()
    
    def _clean_empty_conditionals(self, text: str) -> str:
        """清理空的条件块"""
        # 匹配 {% if xxx %} ... {% endif %} 块
        pattern = r'\{%\s*if\s+\w+\s*%\}\s*.*?\{%\s*endif\s*%\}'
        
        while True:
            new_text = re.sub(pattern, '', text, flags=re.DOTALL)
            if new_text == text:
                break
            text = new_text
            
        return text
    
    def build_prompt(self, template_type: str, variables: Dict[str, Any],
                     include_system: bool = True, enable_cot: bool = None) -> str:
        """
        构建完整Prompt
        
        Args:
            template_type: 模板类型
            variables: 变量字典
            include_system: 是否包含系统提示
            enable_cot: 是否启用Chain of Thought
            
        Returns:
            完整的prompt
        """
        template = self.get_template(template_type)
        if not template:
            raise ValueError(f"Template not found: {template_type}")
        
        # 填充模板
        content = self.fill_template(template, variables)
        
        # 添加Chain of Thought
        if enable_cot is None:
            enable_cot = self.cot_config.get("enabled", True)
            
        if enable_cot and template_type in self.COT_STEPS:
            content = self._add_chain_of_thought(content, template_type)
        
        # 组合最终prompt
        if include_system and self.system_prompt:
            return f"{self.system_prompt}\n\n{content}"
        else:
            return content
    
    def _add_chain_of_thought(self, content: str, template_type: str) -> str:
        """添加Chain of Thought"""
        steps = self.COT_STEPS.get(template_type, [])
        if not steps:
            return content
        
        max_steps = self.cot_config.get("max_steps", 5)
        steps = steps[:max_steps]
        
        cot_instruction = "\n\n【Chain of Thought 分析步骤】\n"
        for step in steps:
            cot_instruction += f"{step.step_number}. {step.instruction}"
            if step.expected_output:
                cot_instruction += f" ({step.expected_output})"
            cot_instruction += "\n"
        
        cot_instruction += f"\n最后: {self.cot_config.get('final_answer_instruction', '给出最终答案')}"
        
        return content + cot_instruction
    
    def build_messages(self, template_type: str, variables: Dict[str, Any],
                       history: List[Dict[str, str]] = None,
                       include_system: bool = True) -> List[Dict[str, str]]:
        """
        构建消息列表
        
        Args:
            template_type: 模板类型
            variables: 变量字典
            history: 历史消息
            include_system: 是否包含系统消息
            
        Returns:
            消息列表 [{"role": "...", "content": "..."}]
        """
        messages = []
        
        # 系统消息
        if include_system and self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # 历史消息
        if history:
            messages.extend(history)
        
        # 当前用户消息
        user_content = self.build_prompt(template_type, variables, include_system=False)
        messages.append({"role": "user", "content": user_content})
        
        return messages
    
    def create_custom_template(self, name: str, template_str: str,
                               template_type: TemplateType = TemplateType.CUSTOM,
                               description: str = "") -> PromptTemplate:
        """
        创建自定义模板
        
        Args:
            name: 模板名称
            template_str: 模板字符串
            template_type: 模板类型
            description: 描述
            
        Returns:
            PromptTemplate对象
        """
        template = PromptTemplate(
            name=name,
            template=template_str,
            template_type=template_type,
            description=description
        )
        return template
    
    def save_template_to_file(self, template: PromptTemplate, filepath: str):
        """保存模板到文件"""
        data = {
            "name": template.name,
            "template_type": template.template_type.value,
            "description": template.description,
            "template": template.template,
            "examples": template.examples,
            "metadata": template.metadata
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def load_template_from_file(self, filepath: str) -> PromptTemplate:
        """从文件加载模板"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return PromptTemplate(
            name=data["name"],
            template=data["template"],
            template_type=TemplateType(data.get("template_type", "custom")),
            description=data.get("description", ""),
            examples=data.get("examples", []),
            metadata=data.get("metadata", {})
        )
    
    def validate_template(self, template: PromptTemplate) -> Dict[str, Any]:
        """
        验证模板
        
        Args:
            template: 模板对象
            
        Returns:
            验证结果
        """
        errors = []
        warnings = []
        
        # 检查模板内容
        if not template.template.strip():
            errors.append("Template is empty")
            
        # 检查变量
        variables = template.extract_variables()
        if not variables:
            warnings.append("No variables found in template")
            
        # 检查未闭合的标签
        if template.template.count("{{") != template.template.count("}}"):
            errors.append("Unmatched variable braces")
            
        # 检查条件块
        if_blocks = len(re.findall(r'\{%\s*if\s+', template.template))
        endif_blocks = len(re.findall(r'\{%\s*endif\s*%\}', template.template))
        if if_blocks != endif_blocks:
            errors.append(f"Unmatched if/endif blocks: {if_blocks} if vs {endif_blocks} endif")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "variables": variables
        }


# 全局实例
_global_engine: Optional[PromptEngine] = None


def get_prompt_engine(config: Dict[str, Any] = None) -> PromptEngine:
    """获取全局Prompt引擎"""
    global _global_engine
    if _global_engine is None:
        _global_engine = PromptEngine(config)
    return _global_engine


def init_prompt_engine(config: Dict[str, Any]) -> PromptEngine:
    """初始化全局Prompt引擎"""
    global _global_engine
    _global_engine = PromptEngine(config)
    return _global_engine
