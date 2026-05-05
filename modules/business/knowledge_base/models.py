"""
BM-03 知识库数据库模型
包含SOP文档、故障案例、文档管理、分类标签等模型
"""

import json
from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, JSON, Float, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class DocumentType(str, Enum):
    """文档类型"""
    SOP = 'sop'                      # SOP标准操作程序
    FAULT_CASE = 'fault_case'        # 故障案例
    TECHNICAL = 'technical'          # 技术文档
    MANUAL = 'manual'                # 手册
    REPORT = 'report'               # 报告
    OTHER = 'other'                 # 其他


class DocumentStatus(str, Enum):
    """文档状态"""
    DRAFT = 'draft'                  # 草稿
    PENDING_REVIEW = 'pending_review'  # 待审核
    APPROVED = 'approved'            # 已通过
    REJECTED = 'rejected'            # 已拒绝
    ARCHIVED = 'archived'            # 已归档
    OBSOLETE = 'obsolete'            # 已废弃


class ReviewStatus(str, Enum):
    """审核状态"""
    PENDING = 'pending'              # 待审核
    APPROVED = 'approved'            # 已通过
    REJECTED = 'rejected'            # 已拒绝


class FaultLevel(str, Enum):
    """故障级别"""
    P1 = 'p1'                        # 重大故障
    P2 = 'p2'                        # 严重故障
    P3 = 'p3'                        # 一般故障
    P4 = 'p4'                        # 轻微故障


class FaultStatus(str, Enum):
    """故障状态"""
    OPEN = 'open'                    # 待处理
    INVESTIGATING = 'investigating'  # 调查中
    IDENTIFIED = 'identified'        # 已定位
    RESOLVED = 'resolved'            # 已解决
    CLOSED = 'closed'                # 已关闭
    RECURRING = 'recurring'          # 反复发生


class SOPDocument(Base):
    """SOP文档模型"""
    __tablename__ = 'kb_sop_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_no = Column(String(50), unique=True, nullable=False, index=True)  # 文档编号
    title = Column(String(200), nullable=False)
    content = Column(Text)                          # Markdown内容
    content_html = Column(Text)                     # HTML渲染内容
    category_id = Column(Integer, ForeignKey('kb_categories.id'))
    tags = Column(String(500))                     # 逗号分隔的标签
    version = Column(String(20), default='1.0.0')   # 当前版本
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.DRAFT)
    author = Column(String(100))                   # 作者
    reviewer = Column(String(100))                  # 审核人
    approver = Column(String(100))                  # 审批人
    review_status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING)
    review_comment = Column(Text)                   # 审核意见
    effective_date = Column(DateTime)               # 生效日期
    review_date = Column(DateTime)                  # 审核日期
    approval_date = Column(DateTime)                # 审批日期
    view_count = Column(Integer, default=0)         # 查看次数
    like_count = Column(Integer, default=0)         # 点赞次数
    related_cases = Column(JSON)                    # 关联故障案例
    related_sops = Column(JSON)                     # 关联SOP文档
    extra_data = Column(JSON)                         # 扩展元数据(重命名为避免与orm reserved冲突)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False)

    # 关系
    category = relationship('Category', back_populates='sop_documents')
    versions = relationship('SOPVersion', back_populates='document', order_by='SOPVersion.version.desc()')
    reviews = relationship('SOPReview', back_populates='document')
    chunks = relationship('DocumentChunk', 
                          primaryjoin="SOPDocument.id==DocumentChunk.sop_id",
                          foreign_keys="DocumentChunk.sop_id",
                          viewonly=True)

    def to_dict(self):
        return {
            'id': self.id,
            'doc_no': self.doc_no,
            'title': self.title,
            'content': self.content,
            'category_id': self.category_id,
            'tags': self.tags.split(',') if self.tags else [],
            'version': self.version,
            'status': self.status.value if self.status else None,
            'author': self.author,
            'reviewer': self.reviewer,
            'approver': self.approver,
            'review_status': self.review_status.value if self.review_status else None,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SOPVersion(Base):
    """SOP文档版本"""
    __tablename__ = 'kb_sop_versions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('kb_sop_documents.id'), nullable=False)
    version = Column(String(20), nullable=False)
    content = Column(Text)
    content_html = Column(Text)
    change_summary = Column(Text)                   # 变更说明
    author = Column(String(100))                    # 变更人
    created_at = Column(DateTime, default=datetime.now)

    document = relationship('SOPDocument', back_populates='versions')

    __table_args__ = (
        Index('idx_sop_version_doc', 'document_id', 'version'),
    )


class SOPReview(Base):
    """SOP审核记录"""
    __tablename__ = 'kb_sop_reviews'

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('kb_sop_documents.id'), nullable=False)
    review_type = Column(String(20))               # review/approve
    reviewer = Column(String(100), nullable=False)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    document = relationship('SOPDocument', back_populates='reviews')


class FaultCase(Base):
    """故障案例模型"""
    __tablename__ = 'kb_fault_cases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_no = Column(String(50), unique=True, nullable=False, index=True)  # 案例编号
    title = Column(String(200), nullable=False)
    
    # 故障基本信息
    fault_level = Column(SQLEnum(FaultLevel), default=FaultLevel.P3)
    fault_status = Column(SQLEnum(FaultStatus), default=FaultStatus.OPEN)
    fault_category = Column(String(100))            # 故障分类
    symptom = Column(Text)                          # 故障现象
    root_cause = Column(Text)                      # 根本原因
    
    # 影响范围
    affected_systems = Column(JSON)                # 受影响系统列表
    affected_services = Column(JSON)               # 受影响服务列表
    user_impact = Column(String(20))               # 用户影响: none/low/medium/high/critical
    business_impact = Column(String(50))          # 业务影响描述
    duration = Column(Integer)                      # 持续时间(分钟)
    outage_time = Column(Integer)                  # 宕机时间(分钟)
    
    # 解决方案
    solution = Column(Text)                         # 解决方案
    workaround = Column(Text)                       # 临时方案
    prevention = Column(Text)                       # 预防措施
    
    # 经验教训
    lessons_learned = Column(Text)                 # 经验教训
    improvement = Column(Text)                      # 改进建议
    related_docs = Column(JSON)                    # 相关文档
    related_cases = Column(JSON)                    # 关联案例
    
    # 元数据
    tags = Column(String(500))
    category_id = Column(Integer, ForeignKey('kb_categories.id'))
    occurrence_time = Column(DateTime)             # 发生时间
    resolution_time = Column(DateTime)             # 解决时间
    author = Column(String(100))
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    extra_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False)

    category = relationship('Category', back_populates='fault_cases')
    chunks = relationship('DocumentChunk', 
                          primaryjoin="FaultCase.id==DocumentChunk.fault_case_id",
                          foreign_keys="DocumentChunk.fault_case_id",
                          viewonly=True)

    def to_dict(self):
        return {
            'id': self.id,
            'case_no': self.case_no,
            'title': self.title,
            'fault_level': self.fault_level.value if self.fault_level else None,
            'fault_status': self.fault_status.value if self.fault_status else None,
            'fault_category': self.fault_category,
            'symptom': self.symptom,
            'root_cause': self.root_cause,
            'affected_systems': self.affected_systems or [],
            'user_impact': self.user_impact,
            'business_impact': self.business_impact,
            'duration': self.duration,
            'solution': self.solution,
            'workaround': self.workaround,
            'prevention': self.prevention,
            'lessons_learned': self.lessons_learned,
            'tags': self.tags.split(',') if self.tags else [],
            'occurrence_time': self.occurrence_time.isoformat() if self.occurrence_time else None,
            'resolution_time': self.resolution_time.isoformat() if self.resolution_time else None,
            'author': self.author,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Category(Base):
    """文档分类"""
    __tablename__ = 'kb_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey('kb_categories.id'))
    code = Column(String(50), unique=True)
    doc_type = Column(SQLEnum(DocumentType))        # 文档类型
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    icon = Column(String(50))                      # 图标
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    parent = relationship('Category', remote_side=[id], backref='children')
    sop_documents = relationship('SOPDocument', back_populates='category')
    fault_cases = relationship('FaultCase', back_populates='category')
    tags = relationship('Tag', back_populates='category')

    def to_dict(self, include_children=False):
        result = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'code': self.code,
            'doc_type': self.doc_type.value if self.doc_type else None,
            'description': self.description,
            'sort_order': self.sort_order,
            'icon': self.icon,
            'is_active': self.is_active,
        }
        if include_children:
            result['children'] = [c.to_dict(include_children=True) for c in self.children if c.is_active]
        return result


class Tag(Base):
    """文档标签"""
    __tablename__ = 'kb_tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    color = Column(String(20))                      # 标签颜色
    category_id = Column(Integer, ForeignKey('kb_categories.id'))
    description = Column(Text)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    category = relationship('Category', back_populates='tags')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'category_id': self.category_id,
            'description': self.description,
            'usage_count': self.usage_count,
        }


class Document(Base):
    """通用文档模型"""
    __tablename__ = 'kb_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_no = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    doc_type = Column(SQLEnum(DocumentType), nullable=False)
    content = Column(Text)
    content_html = Column(Text)
    format = Column(String(20), default='markdown')  # markdown/richtext/html
    category_id = Column(Integer, ForeignKey('kb_categories.id'))
    tags = Column(String(500))
    version = Column(String(20), default='1.0.0')
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.DRAFT)
    author = Column(String(100))
    language = Column(String(10), default='zh-CN')
    is_public = Column(Boolean, default=True)       # 是否公开
    permissions = Column(JSON)                     # 权限配置
    attachments = Column(JSON)                     # 附件列表
    extra_data = Column(JSON)
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False)

    category = relationship('Category')
    chunks = relationship('DocumentChunk', 
                          primaryjoin="Document.id==DocumentChunk.document_id",
                          foreign_keys="DocumentChunk.document_id",
                          viewonly=True)

    def to_dict(self):
        return {
            'id': self.id,
            'doc_no': self.doc_no,
            'title': self.title,
            'doc_type': self.doc_type.value if self.doc_type else None,
            'content': self.content,
            'category_id': self.category_id,
            'tags': self.tags.split(',') if self.tags else [],
            'version': self.version,
            'status': self.status.value if self.status else None,
            'author': self.author,
            'is_public': self.is_public,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DocumentChunk(Base):
    """文档分块(向量化)"""
    __tablename__ = 'kb_document_chunks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('kb_documents.id'))
    sop_id = Column(Integer, ForeignKey('kb_sop_documents.id'))
    fault_case_id = Column(Integer, ForeignKey('kb_fault_cases.id'))
    chunk_index = Column(Integer, default=0)       # 分块序号
    content = Column(Text, nullable=False)         # 原始内容
    content_hash = Column(String(64))              # 内容哈希
    vector_id = Column(String(100))                # 向量库ID
    extra_data = Column(JSON)                         # 元数据: 标题、页码、位置等
    chunk_method = Column(String(20))              # 分块方式: fixed/paragraph/sentence
    created_at = Column(DateTime, default=datetime.now)

    # Relationships defined in parent models to avoid conflicts

    __table_args__ = (
        Index('idx_chunk_doc', 'document_id'),
        Index('idx_chunk_sop', 'sop_id'),
        Index('idx_chunk_case', 'fault_case_id'),
        Index('idx_chunk_hash', 'content_hash'),
    )


class SearchHistory(Base):
    """搜索历史"""
    __tablename__ = 'kb_search_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500), nullable=False)
    search_type = Column(String(20))               # fulltext/semantic/hybrid
    result_count = Column(Integer, default=0)
    user_id = Column(String(100))
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)


class SearchBookmark(Base):
    """搜索书签/收藏"""
    __tablename__ = 'kb_search_bookmarks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500), nullable=False)
    title = Column(String(200))
    user_id = Column(String(100), nullable=False)
    filters = Column(JSON)                         # 保存的筛选条件
    created_at = Column(DateTime, default=datetime.now)
