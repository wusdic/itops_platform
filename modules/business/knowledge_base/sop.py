"""
BM-03 SOP知识库
提供SOP文档的CRUD、版本管理、分类体系、标签管理和审核流程
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    SOPDocument, SOPVersion, SOPReview, Category, Tag,
    DocumentStatus, ReviewStatus
)


class SOPKnowledgeBase:
    """
    SOP知识库管理类
    
    提供SOP文档的创建、查询、更新、删除、版本管理
    分类体系、标签管理和审核流程功能
    """
    
    # 状态流转配置
    STATUS_TRANSITIONS = {
        DocumentStatus.DRAFT: [DocumentStatus.PENDING_REVIEW],
        DocumentStatus.PENDING_REVIEW: [DocumentStatus.APPROVED, DocumentStatus.REJECTED, DocumentStatus.DRAFT],
        DocumentStatus.REJECTED: [DocumentStatus.DRAFT, DocumentStatus.PENDING_REVIEW],
        DocumentStatus.APPROVED: [DocumentStatus.ARCHIVED, DocumentStatus.OBSOLETE],
        DocumentStatus.ARCHIVED: [DocumentStatus.APPROVED],
        DocumentStatus.OBSOLETE: [DocumentStatus.ARCHIVED],
    }
    
    def __init__(self, db: Session):
        """
        初始化SOP知识库
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def _generate_doc_no(self) -> str:
        """生成文档编号"""
        today = datetime.now().strftime('%Y%m%d')
        count = self.db.query(SOPDocument).filter(
            SOPDocument.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        return f"SOP{today}{str(count + 1).zfill(4)}"
    
    def create(
        self,
        title: str,
        content: str,
        author: str,
        category_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        related_cases: Optional[List[int]] = None,
        related_sops: Optional[List[int]] = None,
        **kwargs
    ) -> SOPDocument:
        """
        创建SOP文档
        
        Args:
            title: 标题
            content: 内容(Markdown)
            author: 作者
            category_id: 分类ID
            tags: 标签列表
            metadata: 扩展元数据
            related_cases: 关联故障案例
            related_sops: 关联SOP文档
            
        Returns:
            创建的SOP文档
        """
        doc_no = self._generate_doc_no()
        
        sop = SOPDocument(
            doc_no=doc_no,
            title=title,
            content=content,
            category_id=category_id,
            tags=','.join(tags) if tags else None,
            author=author,
            version='1.0.0',
            status=DocumentStatus.DRAFT,
            review_status=ReviewStatus.PENDING,
            related_cases=related_cases,
            related_sops=related_sops,
            metadata=metadata,
            **kwargs
        )
        
        try:
            self.db.add(sop)
            self.db.flush()
            
            # 创建初始版本
            version = SOPVersion(
                document_id=sop.id,
                version='1.0.0',
                content=content,
                author=author,
                change_summary='初始版本'
            )
            self.db.add(version)
            
            self.db.commit()
            return sop
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_id(self, sop_id: int) -> Optional[SOPDocument]:
        """根据ID获取SOP文档"""
        return self.db.query(SOPDocument).filter(
            SOPDocument.id == sop_id,
            SOPDocument.is_deleted == False
        ).first()
    
    def get_by_doc_no(self, doc_no: str) -> Optional[SOPDocument]:
        """根据文档编号获取SOP文档"""
        return self.db.query(SOPDocument).filter(
            SOPDocument.doc_no == doc_no,
            SOPDocument.is_deleted == False
        ).first()
    
    def list(
        self,
        status: Optional[DocumentStatus] = None,
        category_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        review_status: Optional[ReviewStatus] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> Tuple[List[SOPDocument], int]:
        """
        条件查询SOP文档列表
        
        Args:
            status: 文档状态
            category_id: 分类ID
            tags: 标签列表
            author: 作者
            review_status: 审核状态
            keyword: 关键词搜索
            page: 页码
            page_size: 每页数量
            order_by: 排序字段
            order_desc: 是否降序
            
        Returns:
            (文档列表, 总数)
        """
        query = self.db.query(SOPDocument).filter(SOPDocument.is_deleted == False)
        
        if status:
            query = query.filter(SOPDocument.status == status)
        if category_id:
            query = query.filter(SOPDocument.category_id == category_id)
        if author:
            query = query.filter(SOPDocument.author == author)
        if review_status:
            query = query.filter(SOPDocument.review_status == review_status)
        if keyword:
            query = query.filter(
                SOPDocument.title.like(f'%{keyword}%') |
                SOPDocument.content.like(f'%{keyword}%')
            )
        if tags:
            for tag in tags:
                query = query.filter(SOPDocument.tags.contains(tag))
        
        total = query.count()
        
        order_col = getattr(SOPDocument, order_by, SOPDocument.created_at)
        if order_desc:
            query = query.order_by(order_col.desc())
        else:
            query = query.order_by(order_col.asc())
        
        sops = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return sops, total
    
    def update(
        self,
        sop_id: int,
        operator: str,
        content: Optional[str] = None,
        **kwargs
    ) -> Optional[SOPDocument]:
        """
        更新SOP文档
        
        Args:
            sop_id: 文档ID
            operator: 操作人
            content: 新内容(触发版本更新)
            **kwargs: 更新字段
            
        Returns:
            更新后的文档
        """
        sop = self.get_by_id(sop_id)
        if not sop:
            return None
        
        update_fields = ['title', 'category_id', 'tags', 'metadata', 
                        'related_cases', 'related_sops', 'effective_date']
        
        for key, value in kwargs.items():
            if key in update_fields and value is not None:
                if key == 'tags':
                    setattr(sop, key, ','.join(value) if isinstance(value, list) else value)
                else:
                    setattr(sop, key, value)
        
        # 如果更新了内容,创建新版本
        if content and content != sop.content:
            self._create_version(sop, content, operator)
            sop.content = content
        
        sop.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return sop
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def _create_version(
        self,
        sop: SOPDocument,
        content: str,
        author: str,
        change_summary: Optional[str] = None
    ) -> SOPVersion:
        """创建新版本"""
        # 解析当前版本号
        current = sop.version.split('.')
        major = int(current[0])
        minor = int(current[1]) + 1
        new_version = f"{major}.{minor}"
        
        sop.version = new_version
        
        version = SOPVersion(
            document_id=sop.id,
            version=new_version,
            content=content,
            author=author,
            change_summary=change_summary or '内容更新'
        )
        self.db.add(version)
        return version
    
    def submit_review(self, sop_id: int, operator: str) -> Tuple[bool, str, Optional[SOPDocument]]:
        """
        提交审核
        
        Args:
            sop_id: 文档ID
            operator: 操作人
            
        Returns:
            (是否成功, 消息, 文档对象)
        """
        sop = self.get_by_id(sop_id)
        if not sop:
            return False, '文档不存在', None
        
        if sop.status not in [DocumentStatus.DRAFT, DocumentStatus.REJECTED]:
            return False, f'当前状态{sop.status.value}不能提交审核', None
        
        sop.status = DocumentStatus.PENDING_REVIEW
        sop.review_status = ReviewStatus.PENDING
        sop.updated_at = datetime.now()
        
        self._add_review_record(sop_id, 'review', operator, ReviewStatus.PENDING, '提交审核')
        
        try:
            self.db.commit()
            return True, '已提交审核', sop
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def review(
        self,
        sop_id: int,
        reviewer: str,
        status: ReviewStatus,
        comment: Optional[str] = None
    ) -> Tuple[bool, str, Optional[SOPDocument]]:
        """
        审核文档
        
        Args:
            sop_id: 文档ID
            reviewer: 审核人
            status: 审核状态
            comment: 审核意见
            
        Returns:
            (是否成功, 消息, 文档对象)
        """
        sop = self.get_by_id(sop_id)
        if not sop:
            return False, '文档不存在', None
        
        if sop.status != DocumentStatus.PENDING_REVIEW:
            return False, f'当前状态{sop.status.value}不是待审核', None
        
        sop.review_status = status
        sop.reviewer = reviewer
        sop.review_date = datetime.now()
        
        if status == ReviewStatus.APPROVED:
            sop.status = DocumentStatus.APPROVED
            sop.approval_date = datetime.now()
        elif status == ReviewStatus.REJECTED:
            sop.status = DocumentStatus.REJECTED
        else:
            return False, f'无效的审核状态{status}', None
        
        sop.updated_at = datetime.now()
        
        self._add_review_record(sop_id, 'review', reviewer, status, comment)
        
        try:
            self.db.commit()
            return True, f'审核{status.value}', sop
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def _add_review_record(
        self,
        sop_id: int,
        review_type: str,
        reviewer: str,
        status: ReviewStatus,
        comment: Optional[str]
    ) -> SOPReview:
        """添加审核记录"""
        record = SOPReview(
            document_id=sop_id,
            review_type=review_type,
            reviewer=reviewer,
            status=status,
            comment=comment
        )
        self.db.add(record)
        return record
    
    def get_versions(self, sop_id: int) -> List[SOPVersion]:
        """获取文档版本历史"""
        return self.db.query(SOPVersion).filter(
            SOPVersion.document_id == sop_id
        ).order_by(SOPVersion.created_at.desc()).all()
    
    def get_version(self, sop_id: int, version: str) -> Optional[SOPVersion]:
        """获取指定版本"""
        return self.db.query(SOPVersion).filter(
            SOPVersion.document_id == sop_id,
            SOPVersion.version == version
        ).first()
    
    def rollback_version(self, sop_id: int, version: str, operator: str) -> Tuple[bool, str]:
        """
        回滚到指定版本
        
        Args:
            sop_id: 文档ID
            version: 版本号
            operator: 操作人
            
        Returns:
            (是否成功, 消息)
        """
        target_version = self.get_version(sop_id, version)
        if not target_version:
            return False, '版本不存在'
        
        sop = self.get_by_id(sop_id)
        if not sop:
            return False, '文档不存在'
        
        self._create_version(sop, target_version.content, operator, f'回滚到版本{version}')
        
        try:
            self.db.commit()
            return True, f'已回滚到版本{version}'
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, sop_id: int, operator: str) -> bool:
        """删除SOP文档(软删除)"""
        sop = self.get_by_id(sop_id)
        if not sop:
            return False
        
        sop.is_deleted = True
        sop.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def increment_view_count(self, sop_id: int) -> None:
        """增加查看次数"""
        sop = self.get_by_id(sop_id)
        if sop:
            sop.view_count = (sop.view_count or 0) + 1
            try:
                self.db.commit()
            except SQLAlchemyError:
                self.db.rollback()
    
    def increment_like_count(self, sop_id: int) -> None:
        """增加点赞次数"""
        sop = self.get_by_id(sop_id)
        if sop:
            sop.like_count = (sop.like_count or 0) + 1
            try:
                self.db.commit()
            except SQLAlchemyError:
                self.db.rollback()
    
    def archive(self, sop_id: int) -> Tuple[bool, str]:
        """归档文档"""
        sop = self.get_by_id(sop_id)
        if not sop:
            return False, '文档不存在'
        
        if sop.status != DocumentStatus.APPROVED:
            return False, '只有已审批的文档可以归档'
        
        sop.status = DocumentStatus.ARCHIVED
        sop.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '文档已归档'
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def deprecate(self, sop_id: int, reason: str) -> Tuple[bool, str]:
        """废弃文档"""
        sop = self.get_by_id(sop_id)
        if not sop:
            return False, '文档不存在'
        
        sop.status = DocumentStatus.OBSOLETE
        sop.metadata = sop.metadata or {}
        sop.metadata['deprecate_reason'] = reason
        sop.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '文档已废弃'
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e


class CategoryManager:
    """分类管理器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        name: str,
        code: str,
        doc_type: Optional[str] = None,
        parent_id: Optional[int] = None,
        description: Optional[str] = None,
        sort_order: int = 0,
        icon: Optional[str] = None
    ) -> Category:
        """创建分类"""
        category = Category(
            name=name,
            code=code,
            doc_type=doc_type,
            parent_id=parent_id,
            description=description,
            sort_order=sort_order,
            icon=icon
        )
        
        try:
            self.db.add(category)
            self.db.commit()
            return category
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_id(self, category_id: int) -> Optional[Category]:
        return self.db.query(Category).filter(Category.id == category_id).first()
    
    def get_by_code(self, code: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.code == code).first()
    
    def list(self, doc_type: Optional[str] = None, parent_id: Optional[int] = None) -> List[Category]:
        """获取分类列表"""
        query = self.db.query(Category).filter(Category.is_active == True)
        
        if doc_type:
            query = query.filter(Category.doc_type == doc_type)
        if parent_id is not None:
            query = query.filter(Category.parent_id == parent_id)
        
        return query.order_by(Category.sort_order, Category.name).all()
    
    def get_tree(self, doc_type: Optional[str] = None) -> List[Dict]:
        """获取分类树"""
        roots = self.list(doc_type=doc_type, parent_id=None)
        return [c.to_dict(include_children=True) for c in roots]
    
    def update(self, category_id: int, **kwargs) -> Optional[Category]:
        """更新分类"""
        category = self.get_by_id(category_id)
        if not category:
            return None
        
        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        try:
            self.db.commit()
            return category
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, category_id: int) -> bool:
        """删除分类"""
        category = self.get_by_id(category_id)
        if not category:
            return False
        
        # 检查是否有子分类或文档
        children_count = self.db.query(Category).filter(Category.parent_id == category_id).count()
        if children_count > 0:
            raise ValueError('分类下有子分类,无法删除')
        
        category.is_active = False
        
        try:
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e


class TagManager:
    """标签管理器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, name: str, color: str = '#1890ff', category_id: Optional[int] = None) -> Tag:
        """创建标签"""
        tag = Tag(
            name=name,
            color=color,
            category_id=category_id
        )
        
        try:
            self.db.add(tag)
            self.db.commit()
            return tag
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_name(self, name: str) -> Optional[Tag]:
        return self.db.query(Tag).filter(Tag.name == name).first()
    
    def list(self, category_id: Optional[int] = None, top_n: Optional[int] = None) -> List[Tag]:
        """获取标签列表"""
        query = self.db.query(Tag)
        
        if category_id:
            query = query.filter(Tag.category_id == category_id)
        
        query = query.order_by(Tag.usage_count.desc(), Tag.name)
        
        if top_n:
            query = query.limit(top_n)
        
        return query.all()
    
    def update_usage_count(self, tag_name: str, delta: int = 1) -> None:
        """更新标签使用次数"""
        tag = self.get_by_name(tag_name)
        if tag:
            tag.usage_count = (tag.usage_count or 0) + delta
            try:
                self.db.commit()
            except SQLAlchemyError:
                self.db.rollback()
    
    def delete(self, tag_id: int) -> bool:
        """删除标签"""
        tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            return False
        
        self.db.delete(tag)
        
        try:
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
