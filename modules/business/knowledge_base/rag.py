"""
BM-03 RAG增强
提供文档向量化、分块策略、上下文构建和引用追溯
"""

import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import DocumentChunk, Document, SOPDocument, FaultCase


class ChunkMethod(str, Enum):
    """分块方式"""
    FIXED = 'fixed'                 # 固定长度分块
    PARAGRAPH = 'paragraph'         # 段落分块
    SENTENCE = 'sentence'          # 句子分块
    SEMANTIC = 'semantic'          # 语义分块


class RAGEnhancer:
    """
    RAG增强类
    
    提供文档向量化、分块、上下文构建和引用追溯功能
    """
    
    def __init__(self, db: Session, vector_store=None, embedder=None):
        """
        初始化RAG增强
        
        Args:
            db: 数据库会话
            vector_store: 向量存储客户端
            embedder: 向量嵌入器
        """
        self.db = db
        self.vector_store = vector_store
        self.embedder = embedder
    
    def process_document(
        self,
        doc_type: str,
        doc_id: int,
        chunk_method: ChunkMethod = ChunkMethod.PARAGRAPH,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        metadata_extractor: Optional[Callable] = None
    ) -> Tuple[bool, str, int]:
        """
        处理文档(分块+向量化)
        
        Args:
            doc_type: 文档类型(document/sop/fault_case)
            doc_id: 文档ID
            chunk_method: 分块方式
            chunk_size: 分块大小
            chunk_overlap: 重叠大小
            metadata_extractor: 元数据提取器
            
        Returns:
            (是否成功, 消息, 分块数量)
        """
        # 获取文档
        if doc_type == 'document':
            doc = self.db.query(Document).filter(Document.id == doc_id).first()
        elif doc_type == 'sop':
            doc = self.db.query(SOPDocument).filter(SOPDocument.id == doc_id).first()
        elif doc_type == 'fault_case':
            doc = self.db.query(FaultCase).filter(FaultCase.id == doc_id).first()
        else:
            return False, f'不支持的文档类型{doc_type}', 0
        
        if not doc:
            return False, '文档不存在', 0
        
        # 获取内容
        content = self._extract_content(doc, doc_type)
        if not content:
            return False, '文档内容为空', 0
        
        # 删除旧的分块
        self._delete_chunks(doc_type, doc_id)
        
        # 分块
        chunks = self._chunk_text(
            content, chunk_method, chunk_size, chunk_overlap
        )
        
        # 创建分块记录
        chunk_records = []
        for i, chunk_content in enumerate(chunks):
            # 计算内容哈希
            content_hash = hashlib.md5(chunk_content.encode()).hexdigest()
            
            # 提取元数据
            metadata = {
                'title': getattr(doc, 'title', ''),
                'chunk_index': i,
                'chunk_method': chunk_method.value
            }
            
            if metadata_extractor:
                try:
                    metadata.update(metadata_extractor(doc, i))
                except Exception:
                    pass
            
            chunk_record = DocumentChunk(
                document_id=doc_id if doc_type == 'document' else None,
                sop_id=doc_id if doc_type == 'sop' else None,
                fault_case_id=doc_id if doc_type == 'fault_case' else None,
                chunk_index=i,
                content=chunk_content,
                content_hash=content_hash,
                metadata=metadata,
                chunk_method=chunk_method.value
            )
            chunk_records.append(chunk_record)
        
        try:
            self.db.add_all(chunk_records)
            self.db.flush()
            
            # 向量化
            if self.vector_store and self.embedder:
                self._vectorize_chunks(chunk_records)
            
            self.db.commit()
            return True, '处理完成', len(chunks)
        except SQLAlchemyError as e:
            self.db.rollback()
            return False, f'处理失败:{str(e)}', 0
    
    def _extract_content(self, doc, doc_type: str) -> str:
        """提取文档内容"""
        if doc_type == 'fault_case':
            # 故障案例特殊处理
            parts = []
            if doc.title:
                parts.append(f"标题: {doc.title}")
            if doc.symptom:
                parts.append(f"故障现象: {doc.symptom}")
            if doc.root_cause:
                parts.append(f"根本原因: {doc.root_cause}")
            if doc.solution:
                parts.append(f"解决方案: {doc.solution}")
            if doc.lessons_learned:
                parts.append(f"经验教训: {doc.lessons_learned}")
            return '\n\n'.join(parts)
        else:
            return doc.content or ''
    
    def _chunk_text(
        self,
        text: str,
        method: ChunkMethod,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """
        文本分块
        
        Args:
            text: 文本内容
            method: 分块方式
            chunk_size: 分块大小
            overlap: 重叠大小
            
        Returns:
            分块列表
        """
        if method == ChunkMethod.FIXED:
            return self._fixed_chunk(text, chunk_size, overlap)
        elif method == ChunkMethod.PARAGRAPH:
            return self._paragraph_chunk(text, chunk_size, overlap)
        elif method == ChunkMethod.SENTENCE:
            return self._sentence_chunk(text, chunk_size, overlap)
        elif method == ChunkMethod.SEMANTIC:
            return self._semantic_chunk(text, chunk_size, overlap)
        else:
            return self._paragraph_chunk(text, chunk_size, overlap)
    
    def _fixed_chunk(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """固定长度分块"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # 调整边界避免截断句子
            if end < len(text):
                # 找最后一个句号或换行
                last_punct = max(
                    chunk.rfind('。'),
                    chunk.rfind('。'),
                    chunk.rfind('！'),
                    chunk.rfind('？'),
                    chunk.rfind('\n')
                )
                if last_punct > chunk_size * 0.5:
                    chunk = chunk[:last_punct + 1]
                    end = start + len(chunk)
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return [c for c in chunks if c]
    
    def _paragraph_chunk(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """段落分块"""
        # 按换行分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # 如果单个段落超过分块大小
            if para_size > chunk_size:
                # 先保存当前chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # 递归分割大段落
                sub_chunks = self._fixed_chunk(para, chunk_size, overlap)
                chunks.extend(sub_chunks[:-1])  # 最后一个可能需要合并
                current_chunk = [sub_chunks[-1]]
                current_size = len(sub_chunks[-1])
            elif current_size + para_size + 2 <= chunk_size:
                current_chunk.append(para)
                current_size += para_size + 2
            else:
                # 保存当前chunk,开始新的
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return [c for c in chunks if c]
    
    def _sentence_chunk(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """句子分块"""
        # 句子结束标记
        sentence_delimiters = '。！？；'
        
        sentences = []
        current = ''
        
        for char in text:
            current += char
            if char in sentence_delimiters:
                sentences.append(current)
                current = ''
        
        if current.strip():
            sentences.append(current)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence)
            
            if current_size + sentence_size <= chunk_size:
                current_chunk.append(sentence)
                current_size += sentence_size
            else:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                    # 重叠处理:保留部分句子
                    overlap_sentences = []
                    overlap_size = 0
                    for s in reversed(current_chunk):
                        if overlap_size + len(s) <= overlap:
                            overlap_sentences.insert(0, s)
                            overlap_size += len(s)
                        else:
                            break
                    current_chunk = overlap_sentences
                    current_size = overlap_size
                current_chunk.append(sentence)
                current_size = sentence_size
        
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        return [c for c in chunks if c]
    
    def _semantic_chunk(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        语义分块(基于主题边界)
        
        简化实现:结合段落分块和标题识别
        """
        # 提取标题作为语义边界
        lines = text.split('\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        current_title = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否为标题(以#开头或是全大写/数字开头)
            is_title = line.startswith('#') or (
                line and line[0] in '0123456789ABCDEF'
                and len(line) < 100
            )
            
            if is_title:
                # 保存当前chunk
                if current_chunk and current_size > 0:
                    chunks.append('\n'.join(current_chunk))
                
                # 检查标题后的内容是否可以作为新chunk的开始
                current_chunk = [line]
                current_size = len(line)
                current_title = line
            else:
                line_size = len(line)
                
                if current_size + line_size + 1 <= chunk_size:
                    current_chunk.append(line)
                    current_size += line_size + 1
                else:
                    if current_chunk:
                        chunks.append('\n'.join(current_chunk))
                    
                    # 新chunk保留标题和部分内容
                    if current_title:
                        current_chunk = [current_title, line]
                        current_size = len(current_title) + len(line) + 1
                    else:
                        current_chunk = [line]
                        current_size = line_size
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return [c for c in chunks if c]
    
    def _delete_chunks(self, doc_type: str, doc_id: int) -> None:
        """删除旧分块"""
        if doc_type == 'document':
            self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc_id
            ).delete()
        elif doc_type == 'sop':
            self.db.query(DocumentChunk).filter(
                DocumentChunk.sop_id == doc_id
            ).delete()
        elif doc_type == 'fault_case':
            self.db.query(DocumentChunk).filter(
                DocumentChunk.fault_case_id == doc_id
            ).delete()
    
    def _vectorize_chunks(self, chunks: List[DocumentChunk]) -> None:
        """向量化分块"""
        if not self.vector_store or not self.embedder:
            return
        
        for chunk in chunks:
            try:
                # 生成向量
                vector = self.embedder.embed(chunk.content)
                
                # 存储到向量数据库
                vector_id = self.vector_store.insert(
                    collection_name=self._get_collection_name(chunk),
                    vector=vector,
                    payload={
                        'chunk_id': chunk.id,
                        'content': chunk.content[:500],
                        'metadata': chunk.metadata
                    }
                )
                
                # 更新分块记录
                chunk.vector_id = vector_id
            except Exception as e:
                print(f"Vectorization failed for chunk {chunk.id}: {e}")
    
    def _get_collection_name(self, chunk: DocumentChunk) -> str:
        """获取集合名称"""
        if chunk.sop_id:
            return 'kb_sop'
        elif chunk.fault_case_id:
            return 'kb_fault_case'
        else:
            return 'kb_document'
    
    def build_context(
        self,
        query: str,
        top_k: int = 5,
        doc_types: Optional[List[str]] = None
    ) -> Tuple[str, List[Dict]]:
        """
        构建检索上下文
        
        Args:
            query: 查询语句
            top_k: 返回topk个相关块
            doc_types: 文档类型筛选
            
        Returns:
            (上下文字符串, 引用列表)
        """
        if not self.vector_store or not self.embedder:
            return '', []
        
        try:
            # 生成查询向量
            query_vector = self.embedder.embed(query)
            
            # 向量搜索
            results = self.vector_store.search(
                query_vector,
                top_k=top_k,
                filter_conditions={} if not doc_types else {'doc_type': {'$in': doc_types}}
            )
            
            # 构建上下文
            context_parts = []
            citations = []
            
            for i, result in enumerate(results):
                chunk_id = result.get('chunk_id')
                content = result.get('content', '')
                score = result.get('score', 0)
                
                if chunk_id:
                    chunk = self.db.query(DocumentChunk).filter(
                        DocumentChunk.id == chunk_id
                    ).first()
                    
                    if chunk:
                        # 获取文档信息
                        doc_info = self._get_doc_info(chunk)
                        
                        citation = {
                            'chunk_id': chunk_id,
                            'doc_id': doc_info['doc_id'],
                            'doc_type': doc_info['doc_type'],
                            'doc_no': doc_info['doc_no'],
                            'title': doc_info['title'],
                            'chunk_index': chunk.chunk_index,
                            'score': score
                        }
                        citations.append(citation)
                        
                        # 添加到上下文
                        context_parts.append(
                            f"[{i+1}] 文档: {doc_info['title']}\n{chunk.content}"
                        )
            
            context = '\n\n'.join(context_parts)
            return context, citations
        except Exception as e:
            return '', []
    
    def _get_doc_info(self, chunk: DocumentChunk) -> Dict:
        """获取文档信息"""
        if chunk.document_id:
            doc = self.db.query(Document).filter(
                Document.id == chunk.document_id
            ).first()
            doc_type = 'document'
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
            return {'doc_id': None, 'doc_type': None, 'doc_no': None, 'title': ''}
        
        if doc:
            return {
                'doc_id': doc.id,
                'doc_type': doc_type,
                'doc_no': getattr(doc, 'doc_no', getattr(doc, 'case_no', '')),
                'title': doc.title if hasattr(doc, 'title') else ''
            }
        
        return {'doc_id': None, 'doc_type': doc_type, 'doc_no': None, 'title': ''}
    
    def trace_citation(
        self,
        chunk_id: int
    ) -> Optional[Dict]:
        """
        追溯引用(根据chunk_id找到原文位置)
        
        Args:
            chunk_id: 分块ID
            
        Returns:
            引用信息
        """
        chunk = self.db.query(DocumentChunk).filter(
            DocumentChunk.id == chunk_id
        ).first()
        
        if not chunk:
            return None
        
        doc_info = self._get_doc_info(chunk)
        
        return {
            'chunk_id': chunk_id,
            'doc_id': doc_info['doc_id'],
            'doc_type': doc_info['doc_type'],
            'doc_no': doc_info['doc_no'],
            'title': doc_info['title'],
            'content': chunk.content,
            'chunk_index': chunk.chunk_index,
            'chunk_method': chunk.chunk_method,
            'metadata': chunk.metadata
        }
    
    def batch_process(
        self,
        doc_type: str,
        doc_ids: List[int],
        chunk_method: ChunkMethod = ChunkMethod.PARAGRAPH,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[int, int]:
        """
        批量处理文档
        
        Args:
            doc_type: 文档类型
            doc_ids: 文档ID列表
            chunk_method: 分块方式
            progress_callback: 进度回调
            
        Returns:
            (成功数量, 失败数量)
        """
        success_count = 0
        fail_count = 0
        
        total = len(doc_ids)
        for i, doc_id in enumerate(doc_ids):
            success, msg, count = self.process_document(
                doc_type, doc_id, chunk_method
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            if progress_callback:
                progress_callback(i + 1, total, doc_id, success, msg)
        
        return success_count, fail_count
    
    def rebuild_index(self, collection_name: str) -> Tuple[bool, str]:
        """
        重建向量索引
        
        Args:
            collection_name: 集合名称
            
        Returns:
            (是否成功, 消息)
        """
        if not self.vector_store:
            return False, '未配置向量存储'
        
        try:
            # 清空集合
            self.vector_store.delete_collection(collection_name)
            
            # 重建
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.vector_id.isnot(None)
            ).all()
            
            count = 0
            for chunk in chunks:
                if chunk.vector_id:
                    count += 1
            
            return True, f'索引重建完成,共{count}条记录'
        except Exception as e:
            return False, f'重建失败:{str(e)}'
