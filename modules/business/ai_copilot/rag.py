"""
BM-05 AI Copilot - RAG Retrieval
RAG检索 - 知识库检索、上下文构建、引用追溯、重排序
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """文档块"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    vector: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score
        }


@dataclass
class RetrievalResult:
    """检索结果"""
    chunks: List[DocumentChunk]
    total_count: int
    query: str
    retrieval_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "total_count": self.total_count,
            "query": self.query,
            "retrieval_time": self.retrieval_time,
            "metadata": self.metadata
        }


@dataclass
class Citation:
    """引用信息"""
    chunk_id: str
    source: str
    title: str = ""
    url: str = ""
    snippet: str = ""
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score
        }


class RAGRetriever:
    """RAG检索器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化RAG检索器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.rag_config = config.get("rag", {})
        self.vector_config = self.rag_config.get("vector_db", {})
        self.retrieval_config = self.rag_config.get("retrieval", {})
        
        # 配置参数
        self.enabled = self.rag_config.get("enabled", True)
        self.top_k = self.retrieval_config.get("top_k", 10)
        self.min_similarity = self.retrieval_config.get("min_similarity", 0.5)
        self.max_context_length = self.retrieval_config.get("max_context_length", 4000)
        self.rerank_enabled = self.retrieval_config.get("rerank_enabled", True)
        self.rerank_top_k = self.retrieval_config.get("rerank_top_k", 5)
        
        # 向量数据库配置
        self.db_type = self.vector_config.get("type", "qdrant")
        self.db_host = self.vector_config.get("host", "localhost")
        self.db_port = self.vector_config.get("port", 6333)
        self.collection_name = self.vector_config.get("collection_name", "itops_knowledge")
        
        # 知识库源配置
        self.knowledge_sources = self.rag_config.get("knowledge_base", {}).get("sources", [])
        
        # 缓存
        self._embedding_cache: Dict[str, List[float]] = {}
        
    def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        return httpx.AsyncClient(timeout=30.0)
    
    async def check_health(self) -> Dict[str, Any]:
        """检查RAG服务健康状态"""
        try:
            async with self._get_client() as client:
                # 检查Qdrant
                response = await client.get(f"http://{self.db_host}:{self.db_port}/collections")
                if response.status_code == 200:
                    collections = response.json().get("result", {}).get("collections", [])
                    return {
                        "status": "healthy",
                        "vector_db": {
                            "type": self.db_type,
                            "host": self.db_host,
                            "port": self.db_port,
                            "collections": [c["name"] for c in collections]
                        }
                    }
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本向量
        
        Args:
            text: 输入文本
            
        Returns:
            向量列表
        """
        # 检查缓存
        cache_key = text[:100]  # 使用前100字符作为缓存键
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        try:
            async with self._get_client() as client:
                response = await client.post(
                    "http://localhost:11434/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": text}
                )
                
                if response.status_code == 200:
                    embedding = response.json().get("embedding", [])
                    self._embedding_cache[cache_key] = embedding
                    return embedding
                else:
                    logger.error(f"Embedding failed: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return []
    
    async def retrieve(self, query: str, collection: str = None,
                      top_k: int = None, min_score: float = None) -> RetrievalResult:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            collection: 集合名称（默认使用配置的集合）
            top_k: 返回数量
            min_score: 最小相似度
            
        Returns:
            检索结果
        """
        import time
        start_time = time.time()
        
        if not self.enabled:
            return RetrievalResult(
                chunks=[],
                total_count=0,
                query=query,
                retrieval_time=0.0
            )
        
        top_k = top_k or self.top_k
        min_score = min_score or self.min_similarity
        collection = collection or self.collection_name
        
        # 获取查询向量
        query_vector = await self.get_embedding(query)
        if not query_vector:
            logger.warning("Failed to get query embedding")
            return RetrievalResult(
                chunks=[],
                total_count=0,
                query=query,
                retrieval_time=time.time() - start_time
            )
        
        try:
            # Qdrant检索
            async with self._get_client() as client:
                search_payload = {
                    "vector": query_vector,
                    "limit": top_k * 2,  # 多检索一些，后面会重排序
                    "with_payload": True,
                    "score_threshold": min_score
                }
                
                response = await client.post(
                    f"http://{self.db_host}:{self.db_port}/collections/{collection}/points/search",
                    json=search_payload
                )
                
                if response.status_code == 200:
                    results = response.json().get("result", [])
                    
                    chunks = []
                    for item in results:
                        chunk = DocumentChunk(
                            id=item.get("id", ""),
                            content=item.get("payload", {}).get("content", ""),
                            metadata=item.get("payload", {}).get("metadata", {}),
                            score=item.get("score", 0.0)
                        )
                        chunks.append(chunk)
                    
                    # 重排序
                    if self.rerank_enabled and len(chunks) > self.rerank_top_k:
                        chunks = await self._rerank(query, chunks)
                        chunks = chunks[:self.rerank_top_k]
                    
                    retrieval_time = time.time() - start_time
                    
                    return RetrievalResult(
                        chunks=chunks,
                        total_count=len(chunks),
                        query=query,
                        retrieval_time=retrieval_time
                    )
                else:
                    logger.error(f"Retrieval failed: {response.status_code}")
                    return RetrievalResult(
                        chunks=[],
                        total_count=0,
                        query=query,
                        retrieval_time=time.time() - start_time
                    )
                    
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return RetrievalResult(
                chunks=[],
                total_count=0,
                query=query,
                retrieval_time=time.time() - start_time,
                metadata={"error": str(e)}
            )
    
    async def retrieve_multi_collection(self, query: str, 
                                        collections: List[str] = None) -> RetrievalResult:
        """
        多集合检索
        
        Args:
            query: 查询文本
            collections: 集合列表
            
        Returns:
            合并后的检索结果
        """
        collections = collections or [s["name"] for s in self.knowledge_sources if s.get("enabled")]
        
        all_chunks = []
        
        for collection in collections:
            result = await self.retrieve(query, collection)
            all_chunks.extend(result.chunks)
        
        # 合并后重排序
        if len(all_chunks) > self.rerank_top_k and self.rerank_enabled:
            all_chunks = await self._rerank(query, all_chunks)
            all_chunks = all_chunks[:self.rerank_top_k]
        
        # 按分数排序
        all_chunks.sort(key=lambda x: x.score, reverse=True)
        
        return RetrievalResult(
            chunks=all_chunks,
            total_count=len(all_chunks),
            query=query,
            retrieval_time=0.0
        )
    
    async def _rerank(self, query: str, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        重排序
        
        Args:
            query: 查询文本
            chunks: 候选文档块
            
        Returns:
            重排序后的文档块
        """
        # 简单的重排序策略：结合语义相似度和关键词匹配
        query_keywords = set(query.lower().split())
        
        for chunk in chunks:
            # 基础分数
            base_score = chunk.score
            
            # 关键词匹配加分
            content_lower = chunk.content.lower()
            keyword_matches = sum(1 for kw in query_keywords if kw in content_lower)
            keyword_boost = keyword_matches * 0.05
            
            # 长度惩罚（太长或太短的文档略微减分）
            length = len(chunk.content)
            length_penalty = 0
            if length < 100:
                length_penalty = -0.1
            elif length > 3000:
                length_penalty = -0.05
            
            # 更新分数
            chunk.score = base_score + keyword_boost + length_penalty
        
        return sorted(chunks, key=lambda x: x.score, reverse=True)
    
    def build_context(self, retrieval_result: RetrievalResult, 
                      max_length: int = None) -> str:
        """
        构建上下文
        
        Args:
            retrieval_result: 检索结果
            max_length: 最大长度
            
        Returns:
            上下文字符串
        """
        max_length = max_length or self.max_context_length
        
        context_parts = []
        total_length = 0
        
        for chunk in retrieval_result.chunks:
            chunk_text = f"[来源: {chunk.metadata.get('source', '未知')}]\n{chunk.content}\n"
            chunk_length = len(chunk_text)
            
            if total_length + chunk_length > max_length:
                break
                
            context_parts.append(chunk_text)
            total_length += chunk_length
        
        if context_parts:
            header = f"【参考知识 ({len(context_parts)}条)】\n"
            return header + "\n---\n".join(context_parts)
        else:
            return ""
    
    def extract_citations(self, retrieval_result: RetrievalResult) -> List[Citation]:
        """
        提取引用信息
        
        Args:
            retrieval_result: 检索结果
            
        Returns:
            引用列表
        """
        citations = []
        
        for chunk in retrieval_result.chunks:
            citation = Citation(
                chunk_id=chunk.id,
                source=chunk.metadata.get("source", "未知"),
                title=chunk.metadata.get("title", ""),
                url=chunk.metadata.get("url", ""),
                snippet=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                relevance_score=chunk.score
            )
            citations.append(citation)
            
        return citations
    
    def format_citations(self, citations: List[Citation]) -> str:
        """
        格式化引用
        
        Args:
            citations: 引用列表
            
        Returns:
            格式化后的引用字符串
        """
        if not citations:
            return ""
            
        lines = ["\n【参考来源】"]
        for i, cite in enumerate(citations, 1):
            lines.append(f"{i}. [{cite.source}] {cite.title}")
            if cite.url:
                lines.append(f"   URL: {cite.url}")
            lines.append(f"   相关度: {cite.relevance_score:.2f}")
            
        return "\n".join(lines)


class RAGService:
    """RAG服务封装"""
    
    def __init__(self, config: Dict[str, Any]):
        self.retriever = RAGRetriever(config)
        
    async def search(self, query: str, scenario: str = None) -> Dict[str, Any]:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            scenario: 场景类型
            
        Returns:
            搜索结果
        """
        # 根据场景确定要检索的集合
        collections = None
        if scenario:
            source_map = {
                "fault_diagnosis": ["fault_cases", "ops_documents"],
                "sop_generation": ["sop_library"],
                "qa": ["ops_documents", "alert_knowledge"]
            }
            collections = source_map.get(scenario)
        
        # 执行检索
        if collections:
            result = await self.retriever.retrieve_multi_collection(query, collections)
        else:
            result = await self.retriever.retrieve(query)
        
        # 构建上下文
        context = self.retriever.build_context(result)
        citations = self.retriever.extract_citations(result)
        citations_str = self.retriever.format_citations(citations)
        
        return {
            "context": context,
            "citations": citations,
            "citations_formatted": citations_str,
            "result": result.to_dict()
        }


# 全局实例
_global_rag: Optional[RAGRetriever] = None


def get_rag_retriever(config: Dict[str, Any] = None) -> RAGRetriever:
    """获取全局RAG检索器"""
    global _global_rag
    if _global_rag is None and config is not None:
        _global_rag = RAGRetriever(config)
    return _global_rag


def init_rag_retriever(config: Dict[str, Any]) -> RAGRetriever:
    """初始化全局RAG检索器"""
    global _global_rag
    _global_rag = RAGRetriever(config)
    return _global_rag
