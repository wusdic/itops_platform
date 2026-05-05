"""
BM-03 故障案例库
提供故障案例的CRUD、分类管理、影响范围和解决方案管理
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    FaultCase, Category, Tag,
    FaultLevel, FaultStatus
)


class CaseLibrary:
    """
    故障案例库管理类
    
    提供故障案例的创建、查询、更新、删除
    故障分类、影响范围和解决方案管理功能
    """
    
    def __init__(self, db: Session):
        """
        初始化故障案例库
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def _generate_case_no(self) -> str:
        """生成案例编号"""
        today = datetime.now().strftime('%Y%m%d')
        count = self.db.query(FaultCase).filter(
            FaultCase.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        return f"CASE{today}{str(count + 1).zfill(4)}"
    
    def create(
        self,
        title: str,
        author: str,
        fault_category: str,
        symptom: Optional[str] = None,
        fault_level: FaultLevel = FaultLevel.P3,
        affected_systems: Optional[List[str]] = None,
        affected_services: Optional[List[str]] = None,
        user_impact: Optional[str] = None,
        business_impact: Optional[str] = None,
        duration: Optional[int] = None,
        outage_time: Optional[int] = None,
        occurrence_time: Optional[datetime] = None,
        category_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        **kwargs
    ) -> FaultCase:
        """
        创建故障案例
        
        Args:
            title: 标题
            author: 作者
            fault_category: 故障分类
            symptom: 故障现象
            fault_level: 故障级别
            affected_systems: 受影响系统
            affected_services: 受影响服务
            user_impact: 用户影响
            business_impact: 业务影响
            duration: 持续时间(分钟)
            outage_time: 宕机时间(分钟)
            occurrence_time: 发生时间
            category_id: 分类ID
            tags: 标签
            metadata: 元数据
            
        Returns:
            创建的故障案例
        """
        case_no = self._generate_case_no()
        
        fault_case = FaultCase(
            case_no=case_no,
            title=title,
            author=author,
            fault_category=fault_category,
            symptom=symptom,
            fault_level=fault_level,
            fault_status=FaultStatus.OPEN,
            affected_systems=affected_systems,
            affected_services=affected_services,
            user_impact=user_impact,
            business_impact=business_impact,
            duration=duration,
            outage_time=outage_time,
            occurrence_time=occurrence_time,
            category_id=category_id,
            tags=','.join(tags) if tags else None,
            metadata=metadata,
            **kwargs
        )
        
        try:
            self.db.add(fault_case)
            self.db.commit()
            return fault_case
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_id(self, case_id: int) -> Optional[FaultCase]:
        """根据ID获取故障案例"""
        return self.db.query(FaultCase).filter(
            FaultCase.id == case_id,
            FaultCase.is_deleted == False
        ).first()
    
    def get_by_case_no(self, case_no: str) -> Optional[FaultCase]:
        """根据案例编号获取故障案例"""
        return self.db.query(FaultCase).filter(
            FaultCase.case_no == case_no,
            FaultCase.is_deleted == False
        ).first()
    
    def list(
        self,
        fault_level: Optional[FaultLevel] = None,
        fault_status: Optional[FaultStatus] = None,
        fault_category: Optional[str] = None,
        category_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> Tuple[List[FaultCase], int]:
        """
        条件查询故障案例列表
        
        Args:
            fault_level: 故障级别
            fault_status: 故障状态
            fault_category: 故障分类
            category_id: 分类ID
            tags: 标签
            author: 作者
            keyword: 关键词
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            page_size: 每页数量
            order_by: 排序字段
            order_desc: 降序
            
        Returns:
            (案例列表, 总数)
        """
        query = self.db.query(FaultCase).filter(FaultCase.is_deleted == False)
        
        if fault_level:
            query = query.filter(FaultCase.fault_level == fault_level)
        if fault_status:
            query = query.filter(FaultCase.fault_status == fault_status)
        if fault_category:
            query = query.filter(FaultCase.fault_category == fault_category)
        if category_id:
            query = query.filter(FaultCase.category_id == category_id)
        if author:
            query = query.filter(FaultCase.author == author)
        if start_time:
            query = query.filter(FaultCase.occurrence_time >= start_time)
        if end_time:
            query = query.filter(FaultCase.occurrence_time <= end_time)
        if keyword:
            query = query.filter(
                FaultCase.title.like(f'%{keyword}%') |
                FaultCase.symptom.like(f'%{keyword}%') |
                FaultCase.root_cause.like(f'%{keyword}%')
            )
        if tags:
            for tag in tags:
                query = query.filter(FaultCase.tags.contains(tag))
        
        total = query.count()
        
        order_col = getattr(FaultCase, order_by, FaultCase.created_at)
        if order_desc:
            query = query.order_by(order_col.desc())
        else:
            query = query.order_by(order_col.asc())
        
        cases = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return cases, total
    
    def update(
        self,
        case_id: int,
        root_cause: Optional[str] = None,
        solution: Optional[str] = None,
        workaround: Optional[str] = None,
        prevention: Optional[str] = None,
        lessons_learned: Optional[str] = None,
        improvement: Optional[str] = None,
        **kwargs
    ) -> Optional[FaultCase]:
        """
        更新故障案例(完善分析信息)
        
        Args:
            case_id: 案例ID
            root_cause: 根本原因
            solution: 解决方案
            workaround: 临时方案
            prevention: 预防措施
            lessons_learned: 经验教训
            improvement: 改进建议
            **kwargs: 其他更新字段
            
        Returns:
            更新后的案例
        """
        fault_case = self.get_by_id(case_id)
        if not fault_case:
            return None
        
        update_fields = [
            'title', 'symptom', 'fault_level', 'fault_category',
            'affected_systems', 'affected_services', 'user_impact',
            'business_impact', 'duration', 'outage_time',
            'occurrence_time', 'category_id', 'tags', 'metadata',
            'root_cause', 'solution', 'workaround', 'prevention',
            'lessons_learned', 'improvement', 'related_docs', 'related_cases'
        ]
        
        for key, value in kwargs.items():
            if key in update_fields and value is not None:
                setattr(fault_case, key, value)
        
        fault_case.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return fault_case
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def update_status(
        self,
        case_id: int,
        new_status: FaultStatus,
        comment: Optional[str] = None
    ) -> Tuple[bool, str, Optional[FaultCase]]:
        """
        更新故障状态
        
        Args:
            case_id: 案例ID
            new_status: 新状态
            comment: 说明
            
        Returns:
            (是否成功, 消息, 案例对象)
        """
        fault_case = self.get_by_id(case_id)
        if not fault_case:
            return False, '案例不存在', None
        
        fault_case.fault_status = new_status
        
        if new_status == FaultStatus.RESOLVED and not fault_case.resolution_time:
            fault_case.resolution_time = datetime.now()
        
        fault_case.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, f'状态已更新为{new_status.value}', fault_case
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def add_solution(
        self,
        case_id: int,
        solution: str,
        workaround: Optional[str] = None,
        prevention: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        添加解决方案
        
        Args:
            case_id: 案例ID
            solution: 解决方案
            workaround: 临时方案
            prevention: 预防措施
            
        Returns:
            (是否成功, 消息)
        """
        fault_case = self.get_by_id(case_id)
        if not fault_case:
            return False, '案例不存在'
        
        if solution:
            fault_case.solution = solution
        if workaround:
            fault_case.workaround = workaround
        if prevention:
            fault_case.prevention = prevention
        
        if fault_case.fault_status == FaultStatus.OPEN:
            fault_case.fault_status = FaultStatus.INVESTIGATING
        
        fault_case.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '解决方案已保存'
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def add_lessons_learned(
        self,
        case_id: int,
        root_cause: str,
        lessons_learned: str,
        improvement: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        添加经验教训
        
        Args:
            case_id: 案例ID
            root_cause: 根本原因
            lessons_learned: 经验教训
            improvement: 改进建议
            
        Returns:
            (是否成功, 消息)
        """
        fault_case = self.get_by_id(case_id)
        if not fault_case:
            return False, '案例不存在'
        
        fault_case.root_cause = root_cause
        fault_case.lessons_learned = lessons_learned
        if improvement:
            fault_case.improvement = improvement
        
        fault_case.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '经验教训已保存'
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def link_related_cases(self, case_id: int, related_ids: List[int]) -> Tuple[bool, str]:
        """
        关联案例
        
        Args:
            case_id: 案例ID
            related_ids: 关联的案例ID列表
            
        Returns:
            (是否成功, 消息)
        """
        fault_case = self.get_by_id(case_id)
        if not fault_case:
            return False, '案例不存在'
        
        related_cases = fault_case.related_cases or []
        for rid in related_ids:
            if rid not in related_cases:
                related_cases.append(rid)
        
        fault_case.related_cases = related_cases
        fault_case.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '关联案例已保存'
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def link_related_docs(self, case_id: int, doc_ids: List[int]) -> Tuple[bool, str]:
        """
        关联文档
        
        Args:
            case_id: 案例ID
            doc_ids: 关联的文档ID列表
            
        Returns:
            (是否成功, 消息)
        """
        fault_case = self.get_by_id(case_id)
        if not fault_case:
            return False, '案例不存在'
        
        related_docs = fault_case.related_docs or []
        for did in doc_ids:
            if did not in related_docs:
                related_docs.append(did)
        
        fault_case.related_docs = related_docs
        fault_case.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True, '关联文档已保存'
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, case_id: int) -> bool:
        """删除故障案例(软删除)"""
        fault_case = self.get_by_id(case_id)
        if not fault_case:
            return False
        
        fault_case.is_deleted = True
        fault_case.updated_at = datetime.now()
        
        try:
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def increment_view_count(self, case_id: int) -> None:
        """增加查看次数"""
        fault_case = self.get_by_id(case_id)
        if fault_case:
            fault_case.view_count = (fault_case.view_count or 0) + 1
            try:
                self.db.commit()
            except SQLAlchemyError:
                self.db.rollback()
    
    def get_categories_stats(self) -> List[Dict]:
        """获取各故障分类的统计"""
        from sqlalchemy import func
        
        results = self.db.query(
            FaultCase.fault_category,
            func.count(FaultCase.id).label('count')
        ).filter(
            FaultCase.is_deleted == False
        ).group_by(
            FaultCase.fault_category
        ).all()
        
        return [{'category': r[0], 'count': r[1]} for r in results]
    
    def get_level_stats(self) -> List[Dict]:
        """获取各故障级别的统计"""
        from sqlalchemy import func
        
        results = self.db.query(
            FaultCase.fault_level,
            func.count(FaultCase.id).label('count')
        ).filter(
            FaultCase.is_deleted == False
        ).group_by(
            FaultCase.fault_level
        ).all()
        
        return [{'level': r[0].value if r[0] else None, 'count': r[1]} for r in results]
    
    def get_status_stats(self) -> List[Dict]:
        """获取各故障状态的统计"""
        from sqlalchemy import func
        
        results = self.db.query(
            FaultCase.fault_status,
            func.count(FaultCase.id).label('count')
        ).filter(
            FaultCase.is_deleted == False
        ).group_by(
            FaultCase.fault_status
        ).all()
        
        return [{'status': r[0].value if r[0] else None, 'count': r[1]} for r in results]
    
    def get_timeline(self, days: int = 30) -> List[Dict]:
        """获取故障时间线"""
        from sqlalchemy import func
        
        start_time = datetime.now() - datetime.timedelta(days=days)
        
        results = self.db.query(
            func.date(FaultCase.occurrence_time).label('date'),
            func.count(FaultCase.id).label('count')
        ).filter(
            FaultCase.is_deleted == False,
            FaultCase.occurrence_time >= start_time
        ).group_by(
            func.date(FaultCase.occurrence_time)
        ).order_by(
            func.date(FaultCase.occurrence_time)
        ).all()
        
        return [{'date': str(r[0]), 'count': r[1]} for r in results]
    
    def get_similar_cases(self, case_id: int, top_n: int = 5) -> List[FaultCase]:
        """
        获取相似案例(基于故障分类和关键词)
        
        Args:
            case_id: 案例ID
            top_n: 返回数量
            
        Returns:
            相似案例列表
        """
        fault_case = self.get_by_id(case_id)
        if not fault_case:
            return []
        
        query = self.db.query(FaultCase).filter(
            FaultCase.is_deleted == False,
            FaultCase.id != case_id
        )
        
        # 相同故障分类
        if fault_case.fault_category:
            query = query.filter(FaultCase.fault_category == fault_case.fault_category)
        
        # 相同故障级别
        if fault_case.fault_level:
            query = query.filter(FaultCase.fault_level == fault_case.fault_level)
        
        return query.order_by(FaultCase.created_at.desc()).limit(top_n).all()


class FaultCategoryManager:
    """故障分类管理器"""
    
    # 预设的故障分类
    DEFAULT_CATEGORIES = [
        {'code': 'hardware', 'name': '硬件故障', 'icon': 'cpu'},
        {'code': 'software', 'name': '软件故障', 'icon': 'code'},
        {'code': 'network', 'name': '网络故障', 'icon': 'network'},
        {'code': 'database', 'name': '数据库故障', 'icon': 'database'},
        {'code': 'security', 'name': '安全故障', 'icon': 'security'},
        {'code': 'application', 'name': '应用故障', 'icon': 'app'},
        {'code': 'configuration', 'name': '配置错误', 'icon': 'settings'},
        {'code': 'performance', 'name': '性能问题', 'icon': 'chart'},
        {'code': 'capacity', 'name': '容量问题', 'icon': 'storage'},
        {'code': 'other', 'name': '其他', 'icon': 'more'},
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def init_default_categories(self) -> List[Category]:
        """初始化默认分类"""
        categories = []
        for cat in self.DEFAULT_CATEGORIES:
            existing = self.db.query(Category).filter(
                Category.code == cat['code']
            ).first()
            
            if not existing:
                category = Category(
                    name=cat['name'],
                    code=cat['code'],
                    icon=cat['icon'],
                    doc_type='fault_case'
                )
                self.db.add(category)
                categories.append(category)
        
        try:
            self.db.commit()
            return categories
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def list(self) -> List[Category]:
        """获取所有故障分类"""
        return self.db.query(Category).filter(
            Category.doc_type == 'fault_case',
            Category.is_active == True
        ).order_by(Category.sort_order, Category.name).all()
    
    def create(self, name: str, code: str, **kwargs) -> Category:
        """创建分类"""
        category = Category(
            name=name,
            code=code,
            doc_type='fault_case',
            **kwargs
        )
        
        try:
            self.db.add(category)
            self.db.commit()
            return category
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
