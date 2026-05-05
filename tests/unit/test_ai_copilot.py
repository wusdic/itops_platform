"""
BM-05 AI Copilot - Unit Tests
AI助手模块单元测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any


class TestLLMClient:
    """LLM客户端测试"""
    
    @pytest.fixture
    def config(self):
        return {
            "ollama": {
                "base_url": "http://localhost:11434",
                "timeout": 60,
                "retry_count": 2
            },
            "models": {
                "default": "qwen3.5:8b",
                "available": [
                    {
                        "name": "qwen3.5:8b",
                        "display_name": "通义千问3.5 8B",
                        "max_tokens": 8192,
                        "enabled": True
                    }
                ]
            },
            "conversation": {
                "max_history_messages": 50,
                "max_context_tokens": 30000
            }
        }
    
    def test_init_client(self, config):
        """测试客户端初始化"""
        from modules.business.ai_copilot import LLMClient
        
        client = LLMClient(config)
        
        assert client.base_url == "http://localhost:11434"
        assert client.timeout == 60
        assert client.retry_count == 2
        assert "qwen3.5:8b" in client._models
    
    def test_create_conversation(self, config):
        """测试创建对话"""
        from modules.business.ai_copilot import LLMClient
        
        client = LLMClient(config)
        conv = client.create_conversation("test_conv")
        
        assert conv.id == "test_conv"
        assert len(conv.messages) == 0
    
    def test_conversation_add_message(self, config):
        """测试对话添加消息"""
        from modules.business.ai_copilot import LLMClient
        
        client = LLMClient(config)
        conv = client.create_conversation("test_conv")
        
        msg = conv.add_message("user", "Hello, AI!")
        
        assert msg.role == "user"
        assert msg.content == "Hello, AI!"
        assert len(conv.messages) == 1
    
    def test_get_context(self, config):
        """测试获取上下文"""
        from modules.business.ai_copilot import LLMClient
        
        client = LLMClient(config)
        conv = client.create_conversation("test_conv")
        
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi there!")
        conv.add_message("user", "How are you?")
        
        context = conv.get_context()
        
        assert len(context) == 3
        assert context[0]["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_check_health(self, config):
        """测试健康检查"""
        from modules.business.ai_copilot import LLMClient
        
        client = LLMClient(config)
        
        with patch.object(client, '_get_client') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "qwen3.5:8b"}]}
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await client.check_health()
            
            assert result["status"] in ["healthy", "unhealthy", "error"]


class TestPromptEngine:
    """Prompt引擎测试"""
    
    @pytest.fixture
    def config(self):
        return {
            "prompts": {
                "system_prompt": "You are a helpful AI assistant."
            },
            "chain_of_thought": {
                "enabled": True,
                "max_steps": 5
            }
        }
    
    def test_init_engine(self, config):
        """测试引擎初始化"""
        from modules.business.ai_copilot import PromptEngine
        
        engine = PromptEngine(config)
        
        assert engine.system_prompt == "You are a helpful AI assistant."
        assert len(engine._templates) > 0
    
    def test_get_template(self, config):
        """测试获取模板"""
        from modules.business.ai_copilot import PromptEngine
        
        engine = PromptEngine(config)
        template = engine.get_template("fault_diagnosis")
        
        assert template is not None
        assert template.name == "故障诊断"
    
    def test_list_templates(self, config):
        """测试列出模板"""
        from modules.business.ai_copilot import PromptEngine
        
        engine = PromptEngine(config)
        templates = engine.list_templates()
        
        assert len(templates) > 0
        assert any(t["key"] == "fault_diagnosis" for t in templates)
    
    def test_fill_template(self, config):
        """测试填充模板"""
        from modules.business.ai_copilot import PromptEngine, PromptTemplate, TemplateType
        
        engine = PromptEngine(config)
        
        template = PromptTemplate(
            name="Test",
            template="Hello {{name}}, you are {{age}} years old.",
            template_type=TemplateType.CUSTOM
        )
        
        result = engine.fill_template(
            template,
            {"name": "Alice", "age": "25"}
        )
        
        assert "Alice" in result
        assert "25" in result
    
    def test_fill_template_with_conditionals(self, config):
        """测试条件填充"""
        from modules.business.ai_copilot import PromptEngine, PromptTemplate, TemplateType
        
        engine = PromptEngine(config)
        
        # 测试简单条件块
        template = PromptTemplate(
            name="Test",
            template="Report: {{content}}",
            template_type=TemplateType.CUSTOM
        )
        
        result = engine.fill_template(
            template,
            {"content": "Test content"},
            strict=False
        )
        assert "Test content" in result
        
        # 测试带可选变量的模板
        template2 = PromptTemplate(
            name="Test2",
            template="Header: {{header}}\nBody: {{body}}",
            template_type=TemplateType.CUSTOM
        )
        
        result = engine.fill_template(
            template2,
            {"header": "Title", "body": "Content"}
        )
        assert "Title" in result and "Content" in result
    
    def test_build_prompt(self, config):
        """测试构建Prompt"""
        from modules.business.ai_copilot import PromptEngine
        
        engine = PromptEngine(config)
        
        result = engine.build_prompt(
            "fault_diagnosis",
            {
                "fault_description": "Server is down",
                "fault_time": "2024-01-01 10:00",
                "logs": "Error logs...",
                "environment_info": "Production",
                "related_cases": ""
            },
            enable_cot=False
        )
        
        assert "Server is down" in result
        assert "You are a helpful AI assistant" in result
    
    def test_build_messages(self, config):
        """测试构建消息列表"""
        from modules.business.ai_copilot import PromptEngine
        
        engine = PromptEngine(config)
        
        messages = engine.build_messages(
            "daily_report",
            {
                "date": "2024-01-01",
                "system_status": "OK",
                "work_items": "Test work",
                "alerts_summary": "No alerts",
                "incidents_summary": "No incidents",
                "tomorrow_plan": "Continue testing",
                "notes": ""
            }
        )
        
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
    
    def test_validate_template(self, config):
        """测试验证模板"""
        from modules.business.ai_copilot import PromptEngine, PromptTemplate, TemplateType
        
        engine = PromptEngine(config)
        
        # 有效模板
        template = PromptTemplate(
            name="Valid",
            template="Hello {{name}}",
            template_type=TemplateType.CUSTOM
        )
        result = engine.validate_template(template)
        assert result["valid"] == True
        
        # 空模板
        template = PromptTemplate(
            name="Empty",
            template="",
            template_type=TemplateType.CUSTOM
        )
        result = engine.validate_template(template)
        assert result["valid"] == False


class TestRAGRetriever:
    """RAG检索器测试"""
    
    @pytest.fixture
    def config(self):
        return {
            "rag": {
                "enabled": True,
                "vector_db": {
                    "type": "qdrant",
                    "host": "localhost",
                    "port": 6333,
                    "collection_name": "test_collection"
                },
                "retrieval": {
                    "top_k": 5,
                    "min_similarity": 0.5,
                    "rerank_enabled": True,
                    "rerank_top_k": 3
                }
            }
        }
    
    def test_init_retriever(self, config):
        """测试检索器初始化"""
        from modules.business.ai_copilot import RAGRetriever
        
        retriever = RAGRetriever(config)
        
        assert retriever.enabled == True
        assert retriever.top_k == 5
        assert retriever.collection_name == "test_collection"
    
    def test_build_context(self, config):
        """测试构建上下文"""
        from modules.business.ai_copilot import RAGRetriever, DocumentChunk, RetrievalResult
        
        retriever = RAGRetriever(config)
        
        chunks = [
            DocumentChunk(
                id="1",
                content="This is first chunk about servers.",
                metadata={"source": "doc1"}
            ),
            DocumentChunk(
                id="2",
                content="This is second chunk about networking.",
                metadata={"source": "doc2"}
            )
        ]
        
        result = RetrievalResult(
            chunks=chunks,
            total_count=2,
            query="servers",
            retrieval_time=0.1
        )
        
        context = retriever.build_context(result)
        
        assert "servers" in context
        assert "doc1" in context
    
    def test_extract_citations(self, config):
        """测试提取引用"""
        from modules.business.ai_copilot import RAGRetriever, DocumentChunk, RetrievalResult
        
        retriever = RAGRetriever(config)
        
        chunks = [
            DocumentChunk(
                id="1",
                content="Important information about system.",
                metadata={"source": "manual", "title": "System Manual"}
            )
        ]
        
        result = RetrievalResult(
            chunks=chunks,
            total_count=1,
            query="system",
            retrieval_time=0.1
        )
        
        citations = retriever.extract_citations(result)
        
        assert len(citations) == 1
        assert citations[0].source == "manual"
        assert citations[0].title == "System Manual"


class TestScenarios:
    """AI场景测试"""
    
    @pytest.fixture
    def mock_llm_client(self):
        client = Mock()
        client.chat = AsyncMock(return_value={
            "content": "Test response",
            "done": True
        })
        client.chat_stream = AsyncMock(return_value=iter(["Test ", "response"]))
        return client
    
    @pytest.fixture
    def prompt_engine(self):
        from modules.business.ai_copilot import PromptEngine
        return PromptEngine()
    
    @pytest.fixture
    def mock_rag_service(self):
        service = Mock()
        service.search = AsyncMock(return_value={
            "context": "Related context from knowledge base",
            "citations": []
        })
        service.retriever = Mock()
        service.retriever.format_citations = Mock(return_value="")
        return service
    
    def test_fault_diagnosis_scenario(self, mock_llm_client, prompt_engine, mock_rag_service):
        """测试故障诊断场景"""
        from modules.business.ai_copilot import FaultDiagnosisScenario
        
        scenario = FaultDiagnosisScenario(
            mock_llm_client,
            prompt_engine,
            mock_rag_service
        )
        
        assert scenario.scenario_type == "fault_diagnosis"
        assert scenario.default_temperature == 0.3
    
    def test_daily_report_scenario(self, mock_llm_client, prompt_engine):
        """测试日报生成场景"""
        from modules.business.ai_copilot import DailyReportScenario
        
        scenario = DailyReportScenario(mock_llm_client, prompt_engine)
        
        assert scenario.scenario_type == "daily_report"
        assert scenario.default_temperature == 0.5
    
    def test_weekly_report_scenario(self, mock_llm_client, prompt_engine):
        """测试周报生成场景"""
        from modules.business.ai_copilot import WeeklyReportScenario
        
        scenario = WeeklyReportScenario(mock_llm_client, prompt_engine)
        
        assert scenario.scenario_type == "weekly_report"
    
    def test_sop_generation_scenario(self, mock_llm_client, prompt_engine):
        """测试SOP生成场景"""
        from modules.business.ai_copilot import SOPGenerationScenario
        
        scenario = SOPGenerationScenario(mock_llm_client, prompt_engine)
        
        assert scenario.scenario_type == "sop_generation"
    
    def test_change_review_scenario(self, mock_llm_client, prompt_engine):
        """测试变更评审场景"""
        from modules.business.ai_copilot import ChangeReviewScenario
        
        scenario = ChangeReviewScenario(mock_llm_client, prompt_engine)
        
        assert scenario.scenario_type == "change_review"
        assert scenario.default_temperature == 0.3
    
    def test_qa_scenario(self, mock_llm_client, prompt_engine):
        """测试问答场景"""
        from modules.business.ai_copilot import QAScenario
        
        scenario = QAScenario(mock_llm_client, prompt_engine)
        
        assert scenario.scenario_type == "qa"
        assert scenario.default_temperature == 0.7
    
    def test_ai_copilot_service_init(self, mock_llm_client, prompt_engine, mock_rag_service):
        """测试AI Copilot服务初始化"""
        from modules.business.ai_copilot import AICopilotService
        
        service = AICopilotService(
            mock_llm_client,
            prompt_engine,
            mock_rag_service
        )
        
        assert len(service.scenarios) == 6
        assert "fault_diagnosis" in service.scenarios
        assert "daily_report" in service.scenarios
    
    def test_list_scenarios(self, mock_llm_client, prompt_engine):
        """测试列出场景"""
        from modules.business.ai_copilot import AICopilotService
        
        service = AICopilotService(mock_llm_client, prompt_engine)
        scenarios = service.list_scenarios()
        
        assert len(scenarios) == 6
        assert any(s["type"] == "fault_diagnosis" for s in scenarios)
    
    @pytest.mark.asyncio
    async def test_execute_fault_diagnosis(self, mock_llm_client, prompt_engine, mock_rag_service):
        """测试执行故障诊断"""
        from modules.business.ai_copilot import AICopilotService
        
        service = AICopilotService(
            mock_llm_client,
            prompt_engine,
            mock_rag_service
        )
        
        result = await service.execute_scenario(
            "fault_diagnosis",
            fault_description="Server down",
            logs="Error log...",
            environment_info="Production"
        )
        
        assert result.success == True
        assert result.content == "Test response"
    
    @pytest.mark.asyncio
    async def test_execute_daily_report(self, mock_llm_client, prompt_engine):
        """测试生成日报"""
        from modules.business.ai_copilot import AICopilotService
        
        service = AICopilotService(mock_llm_client, prompt_engine)
        
        result = await service.execute_scenario(
            "daily_report",
            date="2024-01-01",
            system_status="OK"
        )
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_execute_qa_with_rag(self, mock_llm_client, prompt_engine, mock_rag_service):
        """测试问答（带RAG）"""
        from modules.business.ai_copilot import AICopilotService
        from modules.business.ai_copilot.rag import Citation
        
        # 设置正确的citation对象
        mock_citation = Citation(
            chunk_id="1",
            source="manual",
            title="Server Guide",
            relevance_score=0.9
        )
        mock_rag_service.search = AsyncMock(return_value={
            "context": "Related context from knowledge base",
            "citations": [mock_citation]
        })
        mock_rag_service.retriever.format_citations = Mock(return_value="\n[参考来源]\n1. [manual] Server Guide")
        
        service = AICopilotService(
            mock_llm_client,
            prompt_engine,
            mock_rag_service
        )
        
        result = await service.execute_scenario(
            "qa",
            question="How to restart server?"
        )
        
        assert result.success == True
        # 验证RAG被调用
        mock_rag_service.search.assert_called_once()


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def full_config(self):
        return {
            "ollama": {
                "base_url": "http://localhost:11434",
                "timeout": 60
            },
            "models": {
                "default": "qwen3.5:8b",
                "available": [
                    {"name": "qwen3.5:8b", "display_name": "Test", "enabled": True}
                ]
            },
            "conversation": {},
            "prompts": {
                "system_prompt": "You are an IT ops assistant."
            },
            "scenarios": {
                "fault_diagnosis": {"temperature": 0.3},
                "daily_report": {"temperature": 0.5},
                "qa": {"temperature": 0.7}
            },
            "rag": {
                "enabled": True,
                "vector_db": {"type": "qdrant", "host": "localhost", "port": 6333}
            }
        }
    
    def test_full_workflow(self, full_config):
        """测试完整工作流"""
        from modules.business.ai_copilot import (
            LLMClient, PromptEngine, RAGRetriever, AICopilotService
        )
        
        # 初始化组件
        llm = LLMClient(full_config)
        engine = PromptEngine(full_config)
        rag = RAGRetriever(full_config)
        
        # 创建服务
        service = AICopilotService(llm, engine, rag, full_config)
        
        # 验证组件已连接
        assert service.llm_client is llm
        assert service.prompt_engine is engine
        assert service.rag_service is rag
        
        # 列出所有场景
        scenarios = service.list_scenarios()
        assert len(scenarios) == 6


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
