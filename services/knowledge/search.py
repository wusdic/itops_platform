# -*- coding: utf-8 -*-
"""
ITOps Platform - Knowledge Search
知识库搜索服务
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class KnowledgeDocument:
    """知识文档"""
    id: Optional[str] = None
    title: str = ""
    content: str = ""
    summary: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class KnowledgeSearch:
    """知识库搜索服务"""
    
    def __init__(self, qdrant_client=None, embedding_model: str = None):
        self._qdrant = qdrant_client
        self._embedding_model = embedding_model or "text-embedding-ada-002"
        self._collection = "itops_knowledge"
        self._documents: Dict[str, KnowledgeDocument] = {}
    
    def set_qdrant(self, client):
        """设置Qdrant客户端"""
        self._qdrant = client
    
    async def add_document(self, doc: KnowledgeDocument) -> bool:
        """添加文档"""
        try:
            # 生成嵌入向量
            if not doc.embedding:
                doc.embedding = await self._generate_embedding(doc.content)
            
            # 存储文档
            self._documents[doc.id] = doc
            
            # 存储到向量数据库
            if self._qdrant:
                self._qdrant.upsert([{
                    "id": doc.id,
                    "vector": doc.embedding,
                    "payload": {
                        "title": doc.title,
                        "content": doc.content,
                        "summary": doc.summary,
                        "category": doc.category,
                        "tags": doc.tags,
                    }
                }])
            
            return True
        except Exception as e:
            print(f"添加文档失败: {e}")
            return False
    
    async def search(self, query: str, limit: int = 5, category: str = None) -> List[Dict[str, Any]]:
        """语义搜索"""
        try:
            # 生成查询向量
            query_embedding = await self._generate_embedding(query)
            
            # 向量搜索
            if self._qdrant:
                filter_cond = {"category": category} if category else None
                results = self._qdrant.search(
                    vector=query_embedding,
                    limit=limit,
                    filter_conditions=filter_cond
                )
                return results
            
            return []
        except Exception as e:
            print(f"知识库搜索失败: {e}")
            return []
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """生成嵌入向量"""
        # 简化实现：使用随机向量
        # 实际应该调用embedding模型
        import random
        return [random.random() for _ in range(1536)]
    
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id in self._documents:
            del self._documents[doc_id]
            
            if self._qdrant:
                self._qdrant.delete([doc_id])
            
            return True
        return False
    
    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """获取文档"""
        return self._documents.get(doc_id)
    
    def get_all_documents(self, category: str = None) -> List[KnowledgeDocument]:
        """获取所有文档"""
        docs = list(self._documents.values())
        if category:
            docs = [d for d in docs if d.category == category]
        return docs
