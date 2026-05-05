"""
BM-03 知识库模块初始化
提供SOP知识库、故障案例库、文档管理、智能检索和RAG增强功能
"""

from .sop import SOPKnowledgeBase
from .case import CaseLibrary
from .document import DocumentManager
from .search import IntelligentSearch
from .rag import RAGEnhancer
from .ai_assist import AIAssist

__all__ = [
    'SOPKnowledgeBase',
    'CaseLibrary',
    'DocumentManager',
    'IntelligentSearch',
    'RAGEnhancer',
    'AIAssist'
]

__version__ = '1.0.0'
