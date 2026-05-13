"""
BM-05 AI Copilot Module
AI助手模块
"""

from .llm_client import LLMClient, SyncLLMClient, get_llm_client, init_llm_client, Message, Conversation, ModelInfo
from .prompt_engine import PromptEngine, PromptTemplate, TemplateType, get_prompt_engine, init_prompt_engine
from .rag import RAGRetriever, RAGService, DocumentChunk, RetrievalResult, Citation, get_rag_retriever, init_rag_retriever
from .scenarios import (
    AICopilotService, BaseScenario, ScenarioType, ScenarioResult,
    FaultDiagnosisScenario, DailyReportScenario, WeeklyReportScenario,
    SOPGenerationScenario, ChangeReviewScenario, QAScenario,
    get_ai_copilot_service
)
from .root_cause import RootCauseAnalyzer, RootCauseResult, get_root_cause_analyzer, init_root_cause_analyzer

__all__ = [
    # LLM Client
    "LLMClient",
    "SyncLLMClient", 
    "get_llm_client",
    "init_llm_client",
    
    # Prompt Engine
    "PromptEngine",
    "PromptTemplate",
    "TemplateType",
    "get_prompt_engine",
    "init_prompt_engine",
    
    # RAG
    "RAGRetriever",
    "RAGService",
    "get_rag_retriever",
    "init_rag_retriever",
    
    # Scenarios
    "AICopilotService",
    "BaseScenario",
    "ScenarioType",
    "ScenarioResult",
    "FaultDiagnosisScenario",
    "DailyReportScenario",
    "WeeklyReportScenario",
    "SOPGenerationScenario",
    "ChangeReviewScenario",
    "QAScenario",
    "get_ai_copilot_service",

    # Root Cause Analysis
    "RootCauseAnalyzer",
    "RootCauseResult",
    "get_root_cause_analyzer",
    "init_root_cause_analyzer",
]

__version__ = "1.0.0"
