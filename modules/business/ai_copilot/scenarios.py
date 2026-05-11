"""
BM-05 AI Copilot - AI Scenarios
AI场景应用 - 故障诊断、日报、周报、SOP、变更评审、智能问答
"""

import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """场景类型"""
    FAULT_DIAGNOSIS = "fault_diagnosis"
    DAILY_REPORT = "daily_report"
    WEEKLY_REPORT = "weekly_report"
    SOP_GENERATION = "sop_generation"
    CHANGE_REVIEW = "change_review"
    QA = "qa"


@dataclass
class ScenarioConfig:
    """场景配置"""
    model: str = "qwen3.5-9b-deepseek-v4-flash-q8_0"
    temperature: float = 0.7
    max_tokens: int = 8192
    enable_rag: bool = False
    rag_top_k: int = 5


@dataclass
class ScenarioResult:
    """场景执行结果"""
    scenario_type: str
    success: bool
    content: str = ""
    citations: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type,
            "success": self.success,
            "content": self.content,
            "citations": self.citations,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "error": self.error
        }


class BaseScenario:
    """场景基类"""
    
    def __init__(self, llm_client, prompt_engine, rag_service=None, config: Dict = None):
        """
        初始化场景
        
        Args:
            llm_client: LLM客户端
            prompt_engine: Prompt引擎
            rag_service: RAG服务
            config: 配置
        """
        self.llm_client = llm_client
        self.prompt_engine = prompt_engine
        self.rag_service = rag_service
        self.config = config or {}
        self.scenario_type = "base"
        self.default_temperature = 0.7
        self.default_max_tokens = 8192
        
    def _get_scenario_config(self) -> ScenarioConfig:
        """获取场景配置"""
        scenarios_config = self.config.get("scenarios", {})
        scenario_cfg = scenarios_config.get(self.scenario_type, {})
        
        return ScenarioConfig(
            model=scenario_cfg.get("model", "qwen3.5-9b-deepseek-v4-flash-q8_0"),
            temperature=scenario_cfg.get("temperature", self.default_temperature),
            max_tokens=scenario_cfg.get("max_tokens", self.default_max_tokens),
            enable_rag=scenario_cfg.get("enable_rag", False),
            rag_top_k=scenario_cfg.get("rag_top_k", 5)
        )
    
    async def _get_context(self, query: str) -> str:
        """获取RAG上下文"""
        if not self.rag_service:
            return ""
            
        cfg = self._get_scenario_config()
        if not cfg.enable_rag:
            return ""
            
        result = await self.rag_service.search(query, self.scenario_type)
        return result.get("context", "")
    
    async def execute(self, **kwargs) -> ScenarioResult:
        """执行场景"""
        raise NotImplementedError
        
    async def execute_stream(self, **kwargs) -> AsyncGenerator[str, None]:
        """流式执行场景"""
        raise NotImplementedError


class FaultDiagnosisScenario(BaseScenario):
    """故障诊断助手"""
    
    def __init__(self, llm_client, prompt_engine, rag_service=None, config: Dict = None):
        super().__init__(llm_client, prompt_engine, rag_service, config)
        self.scenario_type = "fault_diagnosis"
        self.default_temperature = 0.3
        
    async def execute(self, fault_description: str, fault_time: str = None,
                     logs: str = "", environment_info: str = "",
                     related_cases: str = "") -> ScenarioResult:
        """
        执行故障诊断
        
        Args:
            fault_description: 故障描述
            fault_time: 故障时间
            logs: 相关日志
            environment_info: 环境信息
            related_cases: 历史故障案例
            
        Returns:
            诊断结果
        """
        start_time = time.time()
        cfg = self._get_scenario_config()
        
        try:
            # 构建变量
            variables = {
                "fault_description": fault_description,
                "fault_time": fault_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "logs": logs,
                "environment_info": environment_info,
                "related_cases": related_cases
            }
            
            # 获取RAG上下文
            rag_context = await self._get_context(fault_description)
            if rag_context:
                variables["related_cases"] = rag_context
                
            # 构建prompt
            messages = self.prompt_engine.build_messages(
                self.scenario_type,
                variables,
                include_system=True
            )
            
            # 调用LLM
            response = await self.llm_client.chat(
                messages,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens
            )
            
            execution_time = time.time() - start_time
            
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=True,
                content=response.get("content", ""),
                metadata={
                    "fault_description": fault_description,
                    "model_used": cfg.model
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Fault diagnosis failed: {e}")
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def execute_stream(self, fault_description: str, fault_time: str = None,
                            logs: str = "", environment_info: str = "",
                            related_cases: str = "") -> AsyncGenerator[str, ScenarioResult]:
        """流式执行故障诊断"""
        start_time = time.time()
        cfg = self._get_scenario_config()
        
        try:
            variables = {
                "fault_description": fault_description,
                "fault_time": fault_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "logs": logs,
                "environment_info": environment_info,
                "related_cases": related_cases
            }
            
            rag_context = await self._get_context(fault_description)
            if rag_context:
                variables["related_cases"] = rag_context
                
            messages = self.prompt_engine.build_messages(
                self.scenario_type,
                variables,
                include_system=True
            )
            
            full_content = ""
            async for chunk in self.llm_client.chat_stream(
                messages,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens
            ):
                full_content += chunk
                yield chunk
            
            yield ScenarioResult(
                scenario_type=self.scenario_type,
                success=True,
                content=full_content,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Fault diagnosis stream failed: {e}")
            yield ScenarioResult(
                scenario_type=self.scenario_type,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )


class DailyReportScenario(BaseScenario):
    """日报生成助手"""
    
    def __init__(self, llm_client, prompt_engine, rag_service=None, config: Dict = None):
        super().__init__(llm_client, prompt_engine, rag_service, config)
        self.scenario_type = "daily_report"
        self.default_temperature = 0.5
        
    async def execute(self, date: str = None, system_status: str = "",
                     work_items: str = "", alerts_summary: str = "",
                     incidents_summary: str = "", tomorrow_plan: str = "",
                     notes: str = "") -> ScenarioResult:
        """
        生成日报
        
        Args:
            date: 日期
            system_status: 系统运行状态
            work_items: 今日工作内容
            alerts_summary: 告警汇总
            incidents_summary: 事件汇总
            tomorrow_plan: 明日工作计划
            notes: 备注
            
        Returns:
            日报内容
        """
        start_time = time.time()
        cfg = self._get_scenario_config()
        
        try:
            variables = {
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "system_status": system_status,
                "work_items": work_items,
                "alerts_summary": alerts_summary,
                "incidents_summary": incidents_summary,
                "tomorrow_plan": tomorrow_plan,
                "notes": notes
            }
            
            messages = self.prompt_engine.build_messages(
                self.scenario_type,
                variables,
                include_system=True
            )
            
            response = await self.llm_client.chat(
                messages,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens
            )
            
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=True,
                content=response.get("content", ""),
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Daily report generation failed: {e}")
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )


class WeeklyReportScenario(BaseScenario):
    """周报生成助手"""
    
    def __init__(self, llm_client, prompt_engine, rag_service=None, config: Dict = None):
        super().__init__(llm_client, prompt_engine, rag_service, config)
        self.scenario_type = "weekly_report"
        self.default_temperature = 0.5
        
    async def execute(self, week_start: str = None, week_end: str = None,
                     summary: str = "", system_stats: str = "",
                     achievements: str = "", issues_and_improvements: str = "",
                     next_week_plan: str = "", metrics: str = "",
                     risks: str = "") -> ScenarioResult:
        """
        生成周报
        
        Args:
            week_start: 周开始日期
            week_end: 周结束日期
            summary: 本周工作概述
            system_stats: 系统运行统计
            achievements: 主要工作成果
            issues_and_improvements: 问题与改进
            next_week_plan: 下周计划
            metrics: 指标达成情况
            risks: 风险提示
            
        Returns:
            周报内容
        """
        start_time = time.time()
        cfg = self._get_scenario_config()
        
        try:
            # 计算默认周日期
            today = datetime.now()
            week_start = week_start or (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
            week_end = week_end or today.strftime("%Y-%m-%d")
            
            variables = {
                "week_start": week_start,
                "week_end": week_end,
                "summary": summary,
                "system_stats": system_stats,
                "achievements": achievements,
                "issues_and_improvements": issues_and_improvements,
                "next_week_plan": next_week_plan,
                "metrics": metrics,
                "risks": risks
            }
            
            messages = self.prompt_engine.build_messages(
                self.scenario_type,
                variables,
                include_system=True
            )
            
            response = await self.llm_client.chat(
                messages,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens
            )
            
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=True,
                content=response.get("content", ""),
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )


class SOPGenerationScenario(BaseScenario):
    """SOP生成助手"""
    
    def __init__(self, llm_client, prompt_engine, rag_service=None, config: Dict = None):
        super().__init__(llm_client, prompt_engine, rag_service, config)
        self.scenario_type = "sop_generation"
        self.default_temperature = 0.4
        
    async def execute(self, operation_name: str, purpose: str = "",
                     scope: str = "", prerequisites: str = "",
                     operation_steps: str = "", risk_points: str = "",
                     related_docs: str = "") -> ScenarioResult:
        """
        生成SOP
        
        Args:
            operation_name: 操作名称
            purpose: 操作目的
            scope: 适用范围
            prerequisites: 前置条件
            operation_steps: 操作步骤
            risk_points: 风险点
            related_docs: 相关文档
            
        Returns:
            SOP文档
        """
        start_time = time.time()
        cfg = self._get_scenario_config()
        
        try:
            variables = {
                "operation_name": operation_name,
                "purpose": purpose,
                "scope": scope,
                "prerequisites": prerequisites,
                "operation_steps": operation_steps,
                "risk_points": risk_points,
                "related_docs": related_docs
            }
            
            # 获取相关SOP参考
            rag_context = await self._get_context(operation_name)
            if rag_context:
                variables["related_docs"] = f"{related_docs}\n\n{rag_context}" if related_docs else rag_context
                
            messages = self.prompt_engine.build_messages(
                self.scenario_type,
                variables,
                include_system=True
            )
            
            response = await self.llm_client.chat(
                messages,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens
            )
            
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=True,
                content=response.get("content", ""),
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"SOP generation failed: {e}")
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )


class ChangeReviewScenario(BaseScenario):
    """变更评审助手"""
    
    def __init__(self, llm_client, prompt_engine, rag_service=None, config: Dict = None):
        super().__init__(llm_client, prompt_engine, rag_service, config)
        self.scenario_type = "change_review"
        self.default_temperature = 0.3
        
    async def execute(self, change_title: str, change_type: str = "",
                     change_description: str = "", impact_scope: str = "",
                     implementation_plan: str = "", rollback_plan: str = "",
                     test_plan: str = "", risk_assessment: str = "") -> ScenarioResult:
        """
        变更评审
        
        Args:
            change_title: 变更标题
            change_type: 变更类型
            change_description: 变更描述
            impact_scope: 影响范围
            implementation_plan: 实施计划
            rollback_plan: 回滚方案
            test_plan: 测试计划
            risk_assessment: 风险评估
            
        Returns:
            评审结果
        """
        start_time = time.time()
        cfg = self._get_scenario_config()
        
        try:
            variables = {
                "change_title": change_title,
                "change_type": change_type,
                "change_description": change_description,
                "impact_scope": impact_scope,
                "implementation_plan": implementation_plan,
                "rollback_plan": rollback_plan,
                "test_plan": test_plan,
                "risk_assessment": risk_assessment
            }
            
            # 获取历史变更案例
            rag_context = await self._get_context(change_title)
            if rag_context:
                variables["risk_assessment"] = f"{risk_assessment}\n\n历史案例参考:\n{rag_context}" if risk_assessment else f"历史案例参考:\n{rag_context}"
                
            messages = self.prompt_engine.build_messages(
                self.scenario_type,
                variables,
                include_system=True
            )
            
            response = await self.llm_client.chat(
                messages,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens
            )
            
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=True,
                content=response.get("content", ""),
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Change review failed: {e}")
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )


class QAScenario(BaseScenario):
    """智能问答助手"""
    
    def __init__(self, llm_client, prompt_engine, rag_service=None, config: Dict = None):
        super().__init__(llm_client, prompt_engine, rag_service, config)
        self.scenario_type = "qa"
        self.default_temperature = 0.7
        
    async def execute(self, question: str, context: str = "",
                     additional_info: str = "") -> ScenarioResult:
        """
        智能问答
        
        Args:
            question: 问题
            context: 相关上下文
            additional_info: 补充信息
            
        Returns:
            答案
        """
        start_time = time.time()
        cfg = self._get_scenario_config()
        
        try:
            # 如果没有提供context，从RAG获取
            if not context and self.rag_service:
                rag_result = await self.rag_service.search(question, self.scenario_type)
                context = rag_result.get("context", "")
                citations = rag_result.get("citations", [])
            else:
                citations = []
                
            variables = {
                "question": question,
                "context": context,
                "additional_info": additional_info
            }
            
            messages = self.prompt_engine.build_messages(
                self.scenario_type,
                variables,
                include_system=True
            )
            
            response = await self.llm_client.chat(
                messages,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens
            )
            
            content = response.get("content", "")
            
            # 如果有引用，添加到内容末尾
            if citations and self.rag_service:
                citations_formatted = self.rag_service.retriever.format_citations(citations)
                content += citations_formatted
                
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=True,
                content=content,
                citations=[c.to_dict() for c in citations] if hasattr(citations[0], 'to_dict') else citations,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"QA failed: {e}")
            return ScenarioResult(
                scenario_type=self.scenario_type,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )


class AICopilotService:
    """AI Copilot服务 - 统一入口"""
    
    def __init__(self, llm_client, prompt_engine, rag_service=None, config: Dict = None):
        """
        初始化AI Copilot服务
        
        Args:
            llm_client: LLM客户端
            prompt_engine: Prompt引擎
            rag_service: RAG服务
            config: 配置
        """
        self.llm_client = llm_client
        self.prompt_engine = prompt_engine
        self.rag_service = rag_service
        self.config = config or {}
        
        # 初始化各场景
        self.scenarios = {
            ScenarioType.FAULT_DIAGNOSIS.value: FaultDiagnosisScenario(
                llm_client, prompt_engine, rag_service, config
            ),
            ScenarioType.DAILY_REPORT.value: DailyReportScenario(
                llm_client, prompt_engine, rag_service, config
            ),
            ScenarioType.WEEKLY_REPORT.value: WeeklyReportScenario(
                llm_client, prompt_engine, rag_service, config
            ),
            ScenarioType.SOP_GENERATION.value: SOPGenerationScenario(
                llm_client, prompt_engine, rag_service, config
            ),
            ScenarioType.CHANGE_REVIEW.value: ChangeReviewScenario(
                llm_client, prompt_engine, rag_service, config
            ),
            ScenarioType.QA.value: QAScenario(
                llm_client, prompt_engine, rag_service, config
            )
        }
        
    def get_scenario(self, scenario_type: str) -> Optional[BaseScenario]:
        """获取场景"""
        return self.scenarios.get(scenario_type)
    
    async def execute_scenario(self, scenario_type: str, **kwargs) -> ScenarioResult:
        """执行场景"""
        scenario = self.get_scenario(scenario_type)
        if not scenario:
            return ScenarioResult(
                scenario_type=scenario_type,
                success=False,
                error=f"Unknown scenario type: {scenario_type}"
            )
        return await scenario.execute(**kwargs)
    
    def list_scenarios(self) -> List[Dict[str, Any]]:
        """列出所有场景"""
        return [
            {
                "type": stype.value,
                "name": self._get_scenario_display_name(stype.value),
                "description": self._get_scenario_description(stype.value)
            }
            for stype in ScenarioType
        ]
    
    def _get_scenario_display_name(self, scenario_type: str) -> str:
        """获取场景显示名称"""
        names = {
            "fault_diagnosis": "故障诊断助手",
            "daily_report": "日报生成助手",
            "weekly_report": "周报生成助手",
            "sop_generation": "SOP生成助手",
            "change_review": "变更评审助手",
            "qa": "智能问答助手"
        }
        return names.get(scenario_type, scenario_type)
    
    def _get_scenario_description(self, scenario_type: str) -> str:
        """获取场景描述"""
        descriptions = {
            "fault_diagnosis": "分析系统故障，提供诊断建议",
            "daily_report": "生成每日运维日报",
            "weekly_report": "生成每周运维周报",
            "sop_generation": "生成标准操作流程文档",
            "change_review": "辅助变更评审",
            "qa": "IT运维知识问答"
        }
        return descriptions.get(scenario_type, "")


# 全局实例
_global_service: Optional[AICopilotService] = None


def get_ai_copilot_service(llm_client=None, prompt_engine=None, 
                          rag_service=None, config: Dict = None) -> AICopilotService:
    """获取全局AI Copilot服务"""
    global _global_service
    if _global_service is None and all([llm_client, prompt_engine]):
        _global_service = AICopilotService(llm_client, prompt_engine, rag_service, config)
    return _global_service
