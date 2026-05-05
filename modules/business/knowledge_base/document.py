"""
BM-03 文档管理
提供通用文档的CRUD、富文本、Markdown支持、附件管理和全文检索
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Document, DocumentChunk, Category, Tag,
    DocumentType, DocumentStatus
)


class DocumentManager:
    """
    文档管理器
    
    提供通用文档的创建、查询、更新、删除
    支持富文本、Markdown格式、附件管理和权限控制
    """
    
    def __init__(self, db: Session):
        """
        初始化文档管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def _generate_doc_no(self, doc_type: DocumentType) -> str:
        """生成文档编号"""
        type_prefix = {
            DocumentType.SOP: 'SOP',
            DocumentType.FAULT_CASE: 'CASE',
            DocumentType.TECHNICAL: 'TECH',
            DocumentType.MANUAL: 'MAN',
            DocumentType.REPORT: 'RPT',
            DocumentType.OTHER: 'DOC',
        }.get(doc_type, 'DOC')
        
        today = datetime.now().strftime('%Y%m%d')
        count = self.db.query(Document).filter(
            Document.doc_type == doc_type,
            Document.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        return f"{type_prefix}{today}{str(count + 1).zfill(4)}"
    
    def create(
        self,
        title: str,
        doc_type: DocumentType,
        content: str,
        author: str,
        format: str = 'markdown',
        category_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        language: str = 'zh-CN',
        is_public: bool = True,
        permissions: Optional[Dict] = None,
        attachments: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
        **kwargs
    ) -> Document:
        """
        创建文档
        
        Args:
            title: 标题
            doc_type: 文档类型
            content: 内容
            author: 作者
            format: 格式(markdown/richtext/html)
            category_id: 分类ID
            tags: 标签
            language: 语言
            is_public: 是否公开
            permissions: 权限配置
            attachments: 附件列表
            metadata: 元数据
            
        Returns:
            创建的文档
        """
        doc_no = self._generate_doc_no(doc_type)
        
        document = Document(
            doc_no=doc_no,
            title=title,
            doc_type=doc_type,
            content=content,
            format=format,
            category_id=category_id,
            tags=','.join(tags) if tags else None,
            author=author,
            language=language,
            is_public=is_public,
            permissions=permissions,
            attachments=attachments,
            metadata=metadata,
            **kwargs
        )
        
        try:
            self.db.add(document)
            self.db.commit()
            return document
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_id(self, doc_id: int) -> Optional[Document]:
        """根据ID获取文档"""
        return self.db.query(Document).filter(
            Document.id == doc_id,
            Document.is_deleted == False
        ).first()
    
    def get_by_doc_no(self, doc_no: str) -> Optional[Document]:
        """根据文档编号获取文档"""
        return self.db.query(Document).filter(
            Document.doc_no == doc_no,
            Document.is_deleted == False
        ).first()
    
    def list(
        self,
        doc_type: Optional[DocumentType] = None,
        status: Optional[DocumentStatus] = None,
        category_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        keyword: Optional[str] = None,
        is_public: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> Tuple[List[Document], int]:
        """
        条件查询文档列表
        
        Args:
            doc_type: 文档类型
            status: 文档状态
            category_id: 分类ID
            tags: 标签
            author: 作者
            keyword: 关键词
            is_public: 是否公开
            page: 页码
            page_size: 每页数量
            order_by: 排序字段
            order_desc: 降序
            
        Returns:
            (文档列表, 总数)
        """
        query = self.db.query(Document).filter(Document.is_deleted == False)
        
        if doc_type:
            query = query.filter(Document.doc_type == doc_type)
        if status:
            query = query.filter(Document.status == status)
        if category_id:
            query = query.filter(Document.category_id == category_id)
        if author:
            query = query.filter(Document.author == author)
        if keyword:
            query = query.filter(
                Document.title.like(f'%{keyword}%') |
                Document.content.like(f'%{keyword}%')
            )
        if tags:
            for tag in tags:
                query = query.filter(Document.tags.contains(tag))
        if is_public is not None:
            query = query.filter(Document.is_public == is_public)
        
        total = query.count()
        
        order_col = getattr(Document, order_by, Document.created_at)
        if order_desc:
            query = query.order_by(order_col.desc())
        else:
            query = query.order_by(order_col.asc())
        
        docs = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return docs, total
    
    def update(
        self,
        doc_id: int,
        content: Optional[str] = None,
        content_html: Optional[str] = None,
        **kwargs
    ) -> Optional[Document]:
        """
        更新文档
        
        Args:
            doc_id: 文档ID
            content: 内容
            content_html: HTML内容
            **kwargs: 更新字段
            
        Returns:
            更新后的文档
        """
        document = self.get_by_id(doc_id)
        if not document:
            return None
        
        update_fields = [
            'title', 'category_id', 'tags', 'version', 'status',
            'language', 'is_public', 'permissions', 'attachments',
            'metadata'
        ]
        
        for key, value in kwargs.items():
            if key in update_fields and value is not None:
                if key == 'tags':
                    setattr(document, key, ','.join(value) if isinstance(value, list) else value)
                else:
                    setattr(document, key, value)
        
        if content:
            document.content = content
            # 更新内容时增加版本号
            current_version = document.version.split('.')
            new_version = f"{int(current_version[0])}.{int(current_version[1]) + 1}"
            document.version = new_version
        
        if content_html:
            document.content_html = content_html
        
        document.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return document
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, doc_id: int) -> bool:
        """删除文档(软删除)"""
        document = self.get_by_id(doc_id)
        if not document:
            return False
        
        document.is_deleted = True
        document.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def increment_view_count(self, doc_id: int) -> None:
        """增加查看次数"""
        document = self.get_by_id(doc_id)
        if document:
            document.view_count = (document.view_count or 0) + 1
            try:
                self.db.commit()
            except SQLAlchemyError:
                self.db.rollback()
    
    def increment_download_count(self, doc_id: int) -> None:
        """增加下载次数"""
        document = self.get_by_id(doc_id)
        if document:
            document.download_count = (document.download_count or 0) + 1
            try:
                self.db.commit()
            except SQLAlchemyError:
                self.db.rollback()
    
    def check_permission(
        self,
        doc_id: int,
        user_id: str,
        action: str = 'read'
    ) -> bool:
        """
        检查用户权限
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            action: 操作(read/write/delete)
            
        Returns:
            是否有权限
        """
        document = self.get_by_id(doc_id)
        if not document:
            return False
        
        # 公开文档允许读取
        if document.is_public and action == 'read':
            return True
        
        permissions = document.permissions or {}
        
        # 作者拥有所有权限
        if document.author == user_id:
            return True
        
        # 检查权限配置
        user_permission = permissions.get(user_id, {})
        if user_permission.get(action, False):
            return True
        
        # 检查角色权限
        role_permissions = permissions.get('roles', {})
        # 这里应该查询用户角色,然后检查角色权限
        # 简化处理
        
        return False
    
    def grant_permission(
        self,
        doc_id: int,
        user_id: str,
        permissions: Dict[str, bool]
    ) -> Tuple[bool, str]:
        """
        授予用户权限
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            permissions: 权限配置
            
        Returns:
            (是否成功, 消息)
        """
        document = self.get_by_id(doc_id)
        if not document:
            return False, '文档不存在'
        
        perms = document.permissions or {}
        perms[user_id] = permissions
        document.permissions = perms
        document.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '权限已更新'
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def revoke_permission(
        self,
        doc_id: int,
        user_id: str
    ) -> Tuple[bool, str]:
        """
        撤销用户权限
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            
        Returns:
            (是否成功, 消息)
        """
        document = self.get_by_id(doc_id)
        if not document:
            return False, '文档不存在'
        
        perms = document.permissions or {}
        if user_id in perms:
            del perms[user_id]
            document.permissions = perms
            document.updated_at = datetime.now()
            
            try:
                self.db.commit()
                return True, '权限已撤销'
            except SQLAlchemyError as e:
                self.db.rollback()
                raise e
        
        return True, '用户无特殊权限'


class AttachmentManager:
    """附件管理器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add_attachment(
        self,
        doc_id: int,
        name: str,
        file_url: str,
        file_type: str,
        file_size: int,
        uploader: str,
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, str, Optional[Document]]:
        """
        添加附件
        
        Args:
            doc_id: 文档ID
            name: 附件名称
            file_url: 文件URL
            file_type: 文件类型
            file_size: 文件大小
            uploader: 上传者
            metadata: 元数据
            
        Returns:
            (是否成功, 消息, 文档对象)
        """
        document = self.db.query(Document).filter(
            Document.id == doc_id
        ).first()
        
        if not document:
            return False, '文档不存在', None
        
        attachments = document.attachments or []
        attachment = {
            'id': len(attachments) + 1,
            'name': name,
            'url': file_url,
            'type': file_type,
            'size': file_size,
            'uploader': uploader,
            'upload_time': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        attachments.append(attachment)
        document.attachments = attachments
        document.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '附件已添加', document
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def remove_attachment(
        self,
        doc_id: int,
        attachment_id: int
    ) -> Tuple[bool, str, Optional[Document]]:
        """
        移除附件
        
        Args:
            doc_id: 文档ID
            attachment_id: 附件ID
            
        Returns:
            (是否成功, 消息, 文档对象)
        """
        document = self.db.query(Document).filter(
            Document.id == doc_id
        ).first()
        
        if not document:
            return False, '文档不存在', None
        
        attachments = document.attachments or []
        new_attachments = [a for a in attachments if a.get('id') != attachment_id]
        document.attachments = new_attachments
        document.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '附件已移除', document
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_attachment(self, doc_id: int, attachment_id: int) -> Optional[Dict]:
        """
        获取附件信息
        
        Args:
            doc_id: 文档ID
            attachment_id: 附件ID
            
        Returns:
            附件信息
        """
        document = self.db.query(Document).filter(
            Document.id == doc_id
        ).first()
        
        if not document:
            return None
        
        attachments = document.attachments or []
        for a in attachments:
            if a.get('id') == attachment_id:
                return a
        
        return None


class MarkdownProcessor:
    """Markdown处理器"""
    
    @staticmethod
    def to_html(markdown_text: str) -> str:
        """
        将Markdown转换为HTML
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            HTML文本
        """
        try:
            import markdown
            from markdown.extensions import extra, codehilite, toc
            
            extensions = [
                'extra',           # 缩写、属性列表、表格等
                'codehilite',      # 代码高亮
                'toc',             # 目录
                'fenced_code',     # 代码块
                'tables',          # 表格
                'nl2br',           # 换行符转换
            ]
            
            html = markdown.markdown(
                markdown_text,
                extensions=extensions,
                extension_configs={
                    'codehilite': {
                        'css_class': 'highlight',
                        'guess_lang': False
                    },
                    'toc': {
                        'title': '目录'
                    }
                }
            )
            
            return html
        except ImportError:
            # 如果没有markdown库,返回原文本
            return markdown_text.replace('\n', '<br>')
    
    @staticmethod
    def extract_toc(markdown_text: str) -> List[Dict]:
        """
        从Markdown中提取目录
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            目录列表
        """
        import re
        
        toc = []
        # 匹配标题
        pattern = r'^(#{1,6})\s+(.+)$'
        
        for i, line in enumerate(markdown_text.split('\n')):
            match = re.match(pattern, line)
            if match:
                level = len(match.group(1))
                title = match.group(2)
                toc.append({
                    'level': level,
                    'title': title,
                    'line': i + 1,
                    'anchor': re.sub(r'[^\w\s-]', '', title).replace(' ', '-').lower()
                })
        
        return toc
    
    @staticmethod
    def extract_code_blocks(markdown_text: str) -> List[Dict]:
        """
        提取代码块
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            代码块列表
        """
        import re
        
        code_blocks = []
        # 匹配```开头的代码块
        pattern = r'```(\w*)\n(.*?)```'
        
        for match in re.finditer(pattern, markdown_text, re.DOTALL):
            language = match.group(1) or 'text'
            code = match.group(2)
            code_blocks.append({
                'language': language,
                'code': code,
                'start': match.start(),
                'end': match.end()
            })
        
        return code_blocks
    
    @staticmethod
    def word_count(markdown_text: str) -> Dict[str, int]:
        """
        统计字数
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            字数统计
        """
        import re
        
        text = markdown_text
        
        # 去除代码块
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # 去除图片: ![alt](url)
        text = re.sub(r'!\[.*?]\(.*?\)', '', text)
        # 去除链接: [text](url) -> text
        text = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', text)
        # 去除标题标记
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        # 去除加粗斜体等
        text = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', text)
        text = re.sub(r'_{1,2}(.+?)_{1,2}', r'\1', text)
        # 去除行内代码
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # 统计 - 使用简单的方法
        chars = sum(1 for c in text if c not in ' \n\t')
        words = len(re.findall(r'[\w\u4e00-\u9fa5]+', text))
        lines = max(1, text.count('\n'))
        paragraphs = max(1, text.count('\n\n'))
        
        return {
            'chars': chars,
            'words': words,
            'lines': lines,
            'paragraphs': paragraphs
        }
