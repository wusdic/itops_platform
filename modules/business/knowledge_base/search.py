"""
BM-03 智能检索
提供全文搜索、向量语义搜索、混合检索、搜索建议和结果高亮
"""

import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Document, SOPDocument, FaultCase, DocumentChunk, SearchHistory,
    SearchBookmark
)


class SearchType(str, Enum):
    """搜索类型"""
    FULLTEXT = 'fulltext'             # 全文搜索
    SEMANTIC = 'semantic'             # 向量语义搜索
    HYBRID = 'hybrid'                 # 混合搜索


class SearchResult:
    """搜索结果"""
    
    def __init__(
        self,
        doc_id: int,
        doc_type: str,
        title: str,
        content: str,
        score: float,
        highlights: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ):
        self.doc_id = doc_id
        self.doc_type = doc_type
        self.title = title
        self.content = content
        self.score = score
        self.highlights = highlights or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        return {
            'doc_id': self.doc_id,
            'doc_type': self.doc_type,
            'title': self.title,
            'content': self.content[:200] + '...' if len(self.content) > 200 else self.content,
            'score': round(self.score, 4),
            'highlights': self.highlights,
            'metadata': self.metadata
        }


class IntelligentSearch:
    """
    智能搜索引擎
    
    提供全文搜索、向量语义搜索和混合检索
    支持搜索建议和结果高亮
    """
    
    def __init__(self, db: Session, vector_store=None, embedder=None):
        """
        初始化搜索引擎
        
        Args:
            db: 数据库会话
            vector_store: 向量存储客户端(Qdrant/Milvus)
            embedder: 向量嵌入器
        """
        self.db = db
        self.vector_store = vector_store
        self.embedder = embedder
    
    def search(
        self,
        query: str,
        search_type: SearchType = SearchType.HYBRID,
        doc_types: Optional[List[str]] = None,
        category_ids: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[str] = None,
        include_semantic_weight: float = 0.5,
        **kwargs
    ) -> Tuple[List[SearchResult], int]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            search_type: 搜索类型
            doc_types: 文档类型筛选
            category_ids: 分类ID筛选
            tags: 标签筛选
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            page_size: 每页数量
            user_id: 用户ID(记录历史)
            include_semantic_weight: 语义搜索权重(0-1)
            
        Returns:
            (搜索结果列表, 总数)
        """
        if not query or not query.strip():
            return [], 0
        
        query = query.strip()
        
        if search_type == SearchType.FULLTEXT:
            results = self._fulltext_search(
                query, doc_types, category_ids, tags,
                start_time, end_time, page, page_size
            )
        elif search_type == SearchType.SEMANTIC:
            results = self._semantic_search(
                query, doc_types, category_ids, tags,
                page, page_size, include_semantic_weight
            )
        else:  # HYBRID
            results = self._hybrid_search(
                query, doc_types, category_ids, tags,
                start_time, end_time, page, page_size,
                include_semantic_weight
            )
        
        # 记录搜索历史
        if user_id:
            self._record_search_history(query, search_type.value, len(results), user_id)
        
        return results, len(results)
    
    def _fulltext_search(
        self,
        query: str,
        doc_types: Optional[List[str]],
        category_ids: Optional[List[int]],
        tags: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        page: int,
        page_size: int
    ) -> List[SearchResult]:
        """全文搜索"""
        results = []
        
        # 搜索SOP文档
        if not doc_types or 'sop' in doc_types:
            sop_results = self._search_sop_documents(
                query, category_ids, tags, start_time, end_time
            )
            results.extend(sop_results)
        
        # 搜索故障案例
        if not doc_types or 'case' in doc_types or 'fault_case' in doc_types:
            case_results = self._search_fault_cases(
                query, category_ids, tags, start_time, end_time
            )
            results.extend(case_results)
        
        # 搜索通用文档
        if not doc_types or 'document' in doc_types:
            doc_results = self._search_documents(
                query, category_ids, tags, start_time, end_time
            )
            results.extend(doc_results)
        
        # 排序并分页
        results.sort(key=lambda x: x.score, reverse=True)
        start = (page - 1) * page_size
        end = start + page_size
        
        return results[start:end]
    
    def _search_sop_documents(
        self,
        query: str,
        category_ids: Optional[List[int]],
        tags: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> List[SearchResult]:
        """搜索SOP文档"""
        search_query = self.db.query(SOPDocument).filter(
            SOPDocument.is_deleted == False
        )
        
        # 全文匹配
        search_query = search_query.filter(
            SOPDocument.title.like(f'%{query}%') |
            SOPDocument.content.like(f'%{query}%')
        )
        
        # 分类筛选
        if category_ids:
            search_query = search_query.filter(
                SOPDocument.category_id.in_(category_ids)
            )
        
        # 标签筛选
        if tags:
            for tag in tags:
                search_query = search_query.filter(
                    SOPDocument.tags.contains(tag)
                )
        
        # 时间筛选
        if start_time:
            search_query = search_query.filter(SOPDocument.created_at >= start_time)
        if end_time:
            search_query = search_query.filter(SOPDocument.created_at <= end_time)
        
        sops = search_query.all()
        
        results = []
        for sop in sops:
            # 计算相关性得分
            score = self._calculate_fulltext_score(sop.title, sop.content, query)
            
            # 生成高亮片段
            highlights = self._generate_highlights(sop.content, query)
            
            results.append(SearchResult(
                doc_id=sop.id,
                doc_type='sop',
                title=sop.title,
                content=sop.content or '',
                score=score,
                highlights=highlights,
                metadata={
                    'doc_no': sop.doc_no,
                    'version': sop.version,
                    'status': sop.status.value if sop.status else None,
                    'author': sop.author,
                    'view_count': sop.view_count
                }
            ))
        
        return results
    
    def _search_fault_cases(
        self,
        query: str,
        category_ids: Optional[List[int]],
        tags: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> List[SearchResult]:
        """搜索故障案例"""
        search_query = self.db.query(FaultCase).filter(
            FaultCase.is_deleted == False
        )
        
        # 全文匹配
        search_query = search_query.filter(
            FaultCase.title.like(f'%{query}%') |
            FaultCase.symptom.like(f'%{query}%') |
            FaultCase.root_cause.like(f'%{query}%') |
            FaultCase.solution.like(f'%{query}%')
        )
        
        # 分类筛选
        if category_ids:
            search_query = search_query.filter(
                FaultCase.category_id.in_(category_ids)
            )
        
        # 标签筛选
        if tags:
            for tag in tags:
                search_query = search_query.filter(
                    FaultCase.tags.contains(tag)
                )
        
        # 时间筛选
        if start_time:
            search_query = search_query.filter(FaultCase.occurrence_time >= start_time)
        if end_time:
            search_query = search_query.filter(FaultCase.occurrence_time <= end_time)
        
        cases = search_query.all()
        
        results = []
        for case in cases:
            score = self._calculate_fulltext_score(case.title, case.symptom, query)
            highlights = self._generate_highlights(case.solution or case.symptom, query)
            
            results.append(SearchResult(
                doc_id=case.id,
                doc_type='fault_case',
                title=case.title,
                content=case.symptom or '',
                score=score,
                highlights=highlights,
                metadata={
                    'case_no': case.case_no,
                    'fault_level': case.fault_level.value if case.fault_level else None,
                    'fault_status': case.fault_status.value if case.fault_status else None,
                    'author': case.author,
                    'view_count': case.view_count
                }
            ))
        
        return results
    
    def _search_documents(
        self,
        query: str,
        category_ids: Optional[List[int]],
        tags: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> List[SearchResult]:
        """搜索通用文档"""
        search_query = self.db.query(Document).filter(
            Document.is_deleted == False
        )
        
        search_query = search_query.filter(
            Document.title.like(f'%{query}%') |
            Document.content.like(f'%{query}%')
        )
        
        if category_ids:
            search_query = search_query.filter(
                Document.category_id.in_(category_ids)
            )
        
        if tags:
            for tag in tags:
                search_query = search_query.filter(
                    Document.tags.contains(tag)
                )
        
        if start_time:
            search_query = search_query.filter(Document.created_at >= start_time)
        if end_time:
            search_query = search_query.filter(Document.created_at <= end_time)
        
        docs = search_query.all()
        
        results = []
        for doc in docs:
            score = self._calculate_fulltext_score(doc.title, doc.content, query)
            highlights = self._generate_highlights(doc.content, query)
            
            results.append(SearchResult(
                doc_id=doc.id,
                doc_type=doc.doc_type.value if doc.doc_type else 'document',
                title=doc.title,
                content=doc.content or '',
                score=score,
                highlights=highlights,
                metadata={
                    'doc_no': doc.doc_no,
                    'version': doc.version,
                    'author': doc.author,
                    'view_count': doc.view_count
                }
            ))
        
        return results
    
    def _semantic_search(
        self,
        query: str,
        doc_types: Optional[List[str]],
        category_ids: Optional[List[int]],
        tags: Optional[List[str]],
        page: int,
        page_size: int,
        weight: float
    ) -> List[SearchResult]:
        """向量语义搜索"""
        if not self.vector_store or not self.embedder:
            # 如果没有配置向量搜索,回退到全文搜索
            return self._fulltext_search(
                query, doc_types, category_ids, tags,
                None, None, page, page_size
            )
        
        try:
            # 生成查询向量
            query_vector = self.embedder.embed(query)
            
            # 向量数据库搜索
            vector_results = self.vector_store.search(
                query_vector,
                top_k=page_size * 2,  # 获取更多结果用于排序
                filter_conditions=self._build_filter_conditions(
                    doc_types, category_ids, tags
                )
            )
            
            results = []
            for vr in vector_results:
                # 获取原始文档
                chunk = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id == vr.get('chunk_id')
                ).first()
                
                if not chunk:
                    continue
                
                # 根据chunk类型获取文档
                if chunk.document_id:
                    doc = self.db.query(Document).filter(
                        Document.id == chunk.document_id
                    ).first()
                    doc_type = doc.doc_type.value if doc and doc.doc_type else 'document'
                elif chunk.sop_id:
                    doc = self.db.query(SOPDocument).filter(
                        SOPDocument.id == chunk.sop_id
                    ).first()
                    doc_type = 'sop'
                elif chunk.fault_case_id:
                    doc = self.db.query(FaultCase).filter(
                        FaultCase.id == chunk.fault_case_id
                    ).first()
                    doc_type = 'fault_case'
                else:
                    continue
                
                if doc:
                    metadata = chunk.metadata or {}
                    metadata.update({
                        'doc_no': getattr(doc, 'doc_no', None),
                        'author': getattr(doc, 'author', None),
                        'view_count': getattr(doc, 'view_count', 0),
                        'chunk_id': chunk.id,
                        'chunk_index': chunk.chunk_index
                    })
                    
                    results.append(SearchResult(
                        doc_id=doc.id,
                        doc_type=doc_type,
                        title=metadata.get('title', doc.title if hasattr(doc, 'title') else ''),
                        content=chunk.content,
                        score=vr.get('score', 0) * weight,
                        highlights=[],
                        metadata=metadata
                    ))
            
            return results
        except Exception as e:
            # 向量搜索失败时回退到全文搜索
            print(f"Semantic search failed: {e}")
            return self._fulltext_search(
                query, doc_types, category_ids, tags,
                None, None, page, page_size
            )
    
    def _hybrid_search(
        self,
        query: str,
        doc_types: Optional[List[str]],
        category_ids: Optional[List[int]],
        tags: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        page: int,
        page_size: int,
        semantic_weight: float = 0.5
    ) -> List[SearchResult]:
        """混合搜索"""
        fulltext_results = self._fulltext_search(
            query, doc_types, category_ids, tags,
            start_time, end_time, 1, page_size * 2
        )
        
        semantic_results = self._semantic_search(
            query, doc_types, category_ids, tags,
            1, page_size * 2, semantic_weight
        )
        
        # 合并结果
        result_map = {}
        
        for r in fulltext_results:
            r.score = r.score * (1 - semantic_weight)
            result_map[f"{r.doc_type}_{r.doc_id}"] = r
        
        for r in semantic_results:
            key = f"{r.doc_type}_{r.doc_id}"
            if key in result_map:
                result_map[key].score += r.score
            else:
                result_map[key] = r
        
        # 排序
        results = sorted(
            result_map.values(),
            key=lambda x: x.score,
            reverse=True
        )
        
        start = (page - 1) * page_size
        return results[start:start + page_size]
    
    def _calculate_fulltext_score(self, title: str, content: str, query: str) -> float:
        """计算全文搜索得分"""
        if not content:
            content = ''
        
        text = f"{title} {content}".lower()
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        score = 0.0
        
        # 标题精确匹配
        if title and query_lower in title.lower():
            score += 10.0
        
        # 标题分词匹配
        for term in query_terms:
            if title and term in title.lower():
                score += 5.0
        
        # 内容匹配次数
        count = text.count(query_lower)
        score += count * 2.0
        
        # 分词匹配
        for term in query_terms:
            count = text.count(term)
            score += count * 0.5
        
        # 位置奖励(标题开头)
        if title and title.lower().startswith(query_lower):
            score += 3.0
        
        return score
    
    def _generate_highlights(self, content: str, query: str, max_length: int = 150) -> List[str]:
        """生成搜索结果高亮片段"""
        if not content:
            return []
        
        highlights = []
        query_lower = query.lower()
        content_lower = content.lower()
        
        # 找到所有匹配位置
        positions = []
        start = 0
        while True:
            pos = content_lower.find(query_lower, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        
        # 生成高亮片段
        for pos in positions[:3]:  # 最多3个片段
            start = max(0, pos - 50)
            end = min(len(content), pos + len(query) + 100)
            
            # 调整边界避免截断单词
            if start > 0:
                # 向前找到单词边界
                while start > 0 and content[start] not in ' \t\n':
                    start -= 1
            
            if end < len(content):
                # 向后找到单词边界
                while end < len(content) and content[end] not in ' \t\n':
                    end += 1
            
            snippet = content[start:end].strip()
            
            # 添加省略号
            if start > 0:
                snippet = '...' + snippet
            if end < len(content):
                snippet = snippet + '...'
            
            # 高亮标记
            snippet = re.sub(
                re.escape(query),
                f'<em>{query}</em>',
                snippet,
                flags=re.IGNORECASE
            )
            
            highlights.append(snippet)
        
        return highlights
    
    def _build_filter_conditions(
        self,
        doc_types: Optional[List[str]],
        category_ids: Optional[List[int]],
        tags: Optional[List[str]]
    ) -> Dict:
        """构建向量搜索过滤条件"""
        conditions = {}
        
        if doc_types:
            conditions['doc_type'] = {'$in': doc_types}
        
        if category_ids:
            conditions['category_id'] = {'$in': category_ids}
        
        if tags:
            conditions['tags'] = {'$contains_any': tags}
        
        return conditions
    
    def _record_search_history(
        self,
        query: str,
        search_type: str,
        result_count: int,
        user_id: str
    ) -> None:
        """记录搜索历史"""
        history = SearchHistory(
            query=query,
            search_type=search_type,
            result_count=result_count,
            user_id=user_id
        )
        
        try:
            self.db.add(history)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
    
    def get_search_suggestions(
        self,
        query: str,
        limit: int = 10
    ) -> List[str]:
        """
        获取搜索建议
        
        Args:
            query: 查询词
            limit: 返回数量
            
        Returns:
            建议列表
        """
        suggestions = set()
        
        # 从历史记录中获取
        histories = self.db.query(SearchHistory).filter(
            SearchHistory.query.like(f'{query}%')
        ).order_by(
            SearchHistory.created_at.desc()
        ).limit(limit).all()
        
        for h in histories:
            suggestions.add(h.query)
        
        # 从文档标题中获取
        titles = self.db.query(SOPDocument.title).filter(
            SOPDocument.title.like(f'%{query}%'),
            SOPDocument.is_deleted == False
        ).limit(limit).all()
        
        for t in titles:
            if t[0]:
                suggestions.add(t[0])
        
        cases = self.db.query(FaultCase.title).filter(
            FaultCase.title.like(f'%{query}%'),
            FaultCase.is_deleted == False
        ).limit(limit).all()
        
        for c in cases:
            if c[0]:
                suggestions.add(c[0])
        
        return list(suggestions)[:limit]
    
    def save_bookmark(
        self,
        query: str,
        title: str,
        user_id: str,
        filters: Optional[Dict] = None
    ) -> SearchBookmark:
        """
        保存搜索书签
        
        Args:
            query: 查询
            title: 标题
            user_id: 用户ID
            filters: 筛选条件
            
        Returns:
            书签对象
        """
        bookmark = SearchBookmark(
            query=query,
            title=title,
            user_id=user_id,
            filters=filters
        )
        
        try:
            self.db.add(bookmark)
            self.db.commit()
            return bookmark
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_bookmarks(self, user_id: str) -> List[SearchBookmark]:
        """获取用户书签"""
        return self.db.query(SearchBookmark).filter(
            SearchBookmark.user_id == user_id
        ).order_by(SearchBookmark.created_at.desc()).all()
    
    def delete_bookmark(self, bookmark_id: int, user_id: str) -> bool:
        """删除书签"""
        bookmark = self.db.query(SearchBookmark).filter(
            SearchBookmark.id == bookmark_id,
            SearchBookmark.user_id == user_id
        ).first()
        
        if not bookmark:
            return False
        
        self.db.delete(bookmark)
        
        try:
            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False
