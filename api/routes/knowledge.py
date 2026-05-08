"""
知识库API路由
提供SOP文档、故障案例、文档管理等接口
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.business.knowledge_base.models import (
    SOPDocument, FaultCase, Category, Tag,
    DocumentStatus, FaultLevel, FaultStatus, ReviewStatus
)


router = APIRouter()


# ============== 请求/响应模型 ==============

class SOPDocumentCreate(BaseModel):
    """创建SOP文档请求"""
    title: str = Field(..., max_length=200, description="文档标题")
    content: str = Field(..., description="文档内容(Markdown)")
    category_id: Optional[int] = Field(None, description="分类ID")
    tags: Optional[str] = Field(None, description="标签，逗号分隔")
    author: Optional[str] = Field(None, description="作者")


class SOPDocumentUpdate(BaseModel):
    """更新SOP文档请求"""
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[str] = None
    status: Optional[str] = None


class FaultCaseCreate(BaseModel):
    """创建故障案例请求"""
    title: str = Field(..., max_length=200, description="案例标题")
    fault_level: str = Field("P3", description="故障级别: p1, p2, p3, p4")
    fault_category: Optional[str] = Field(None, description="故障分类")
    symptom: str = Field(..., description="故障现象")
    root_cause: Optional[str] = Field(None, description="根本原因")
    solution: Optional[str] = Field(None, description="解决方案")
    prevention: Optional[str] = Field(None, description="预防措施")
    tags: Optional[str] = Field(None, description="标签")
    category_id: Optional[int] = Field(None, description="分类ID")


class FaultCaseUpdate(BaseModel):
    """更新故障案例请求"""
    title: Optional[str] = Field(None, max_length=200)
    fault_level: Optional[str] = None
    fault_status: Optional[str] = None
    fault_category: Optional[str] = None
    symptom: Optional[str] = None
    root_cause: Optional[str] = None
    solution: Optional[str] = None
    prevention: Optional[str] = None
    tags: Optional[str] = None


class CategoryCreate(BaseModel):
    """创建分类请求"""
    name: str = Field(..., max_length=100, description="分类名称")
    parent_id: Optional[int] = Field(None, description="父分类ID")
    code: Optional[str] = Field(None, max_length=50, description="分类编码")
    doc_type: Optional[str] = Field(None, description="文档类型")
    description: Optional[str] = Field(None, description="描述")


def _sop_to_dict(sop: SOPDocument) -> dict:
    """SOP文档转字典"""
    return {
        'id': sop.id,
        'doc_no': sop.doc_no,
        'title': sop.title,
        'content': sop.content,
        'category_id': sop.category_id,
        'tags': sop.tags.split(',') if sop.tags else [],
        'version': sop.version,
        'status': sop.status.value if sop.status else 'draft',
        'author': sop.author,
        'reviewer': sop.reviewer,
        'approver': sop.approver,
        'review_status': sop.review_status.value if sop.review_status else None,
        'effective_date': sop.effective_date.isoformat() if sop.effective_date else None,
        'view_count': sop.view_count,
        'like_count': sop.like_count,
        'created_at': sop.created_at.isoformat() if sop.created_at else None,
        'updated_at': sop.updated_at.isoformat() if sop.updated_at else None,
    }


def _case_to_dict(case: FaultCase) -> dict:
    """故障案例转字典"""
    return {
        'id': case.id,
        'case_no': case.case_no,
        'title': case.title,
        'fault_level': case.fault_level.value if case.fault_level else None,
        'fault_status': case.fault_status.value if case.fault_status else None,
        'fault_category': case.fault_category,
        'symptom': case.symptom,
        'root_cause': case.root_cause,
        'solution': case.solution,
        'prevention': case.prevention,
        'affected_systems': case.affected_systems or [],
        'user_impact': case.user_impact,
        'business_impact': case.business_impact,
        'duration': case.duration,
        'tags': case.tags.split(',') if case.tags else [],
        'occurrence_time': case.occurrence_time.isoformat() if case.occurrence_time else None,
        'resolution_time': case.resolution_time.isoformat() if case.resolution_time else None,
        'author': case.author,
        'view_count': case.view_count,
        'created_at': case.created_at.isoformat() if case.created_at else None,
        'updated_at': case.updated_at.isoformat() if case.updated_at else None,
    }


def _category_to_dict(cat: Category, include_children: bool = False) -> dict:
    """分类转字典"""
    result = {
        'id': cat.id,
        'name': cat.name,
        'parent_id': cat.parent_id,
        'code': cat.code,
        'doc_type': cat.doc_type.value if cat.doc_type else None,
        'description': cat.description,
        'sort_order': cat.sort_order,
        'icon': cat.icon,
        'is_active': cat.is_active,
    }
    if include_children:
        result['children'] = [_category_to_dict(c, True) for c in cat.children if c.is_active]
    return result


def _tag_to_dict(tag: Tag) -> dict:
    """标签转字典"""
    return {
        'id': tag.id,
        'name': tag.name,
        'color': tag.color,
        'category_id': tag.category_id,
        'description': tag.description,
        'usage_count': tag.usage_count,
    }


# ============== 搜索接口 ==============

@router.get("/search", summary="知识库搜索")
async def search_knowledge(
    query: Optional[str] = Query(None, description="搜索关键词(query的别名)"),
    keyword: Optional[str] = Query(None, description="搜索关键词(keyword)"),
    search_type: str = Query("hybrid", description="搜索类型: fulltext, semantic, hybrid"),
    doc_type: Optional[str] = Query(None, description="文档类型过滤"),
    category_id: Optional[int] = Query(None, description="分类ID过滤"),
    tags: Optional[str] = Query(None, description="标签过滤"),
    limit: int = Query(20, le=100, description="返回数量限制"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    知识库全文/向量搜索
    支持关键词搜索和语义搜索
    """
    search_query = keyword or query or ""
    
    if not search_query:
        return {"query": "", "items": [], "total": 0}
    
    results = []
    
    # 搜索SOP文档
    if not doc_type or doc_type == "sop":
        sop_query = db.query(SOPDocument).filter(
            SOPDocument.is_deleted == False,
            SOPDocument.status == DocumentStatus.APPROVED
        )
        if search_query:
            sop_query = sop_query.filter(
                or_(
                    SOPDocument.title.ilike(f"%{search_query}%"),
                    SOPDocument.content.ilike(f"%{search_query}%"),
                )
            )
        if category_id:
            sop_query = sop_query.filter(SOPDocument.category_id == category_id)
        sops = sop_query.limit(limit).all()
        for sop in sops:
            results.append({
                "id": sop.id,
                "type": "sop",
                "title": sop.title,
                "snippet": (sop.content[:200] + "...") if sop.content and len(sop.content) > 200 else (sop.content or ""),
                "score": 1.0,
            })
    
    # 搜索故障案例
    if not doc_type or doc_type == "fault_case":
        case_query = db.query(FaultCase).filter(FaultCase.is_deleted == False)
        if search_query:
            case_query = case_query.filter(
                or_(
                    FaultCase.title.ilike(f"%{search_query}%"),
                    FaultCase.symptom.ilike(f"%{search_query}%"),
                    FaultCase.root_cause.ilike(f"%{search_query}%"),
                )
            )
        if category_id:
            case_query = case_query.filter(FaultCase.category_id == category_id)
        cases = case_query.limit(limit).all()
        for case in cases:
            results.append({
                "id": case.id,
                "type": "fault_case",
                "title": case.title,
                "snippet": (case.symptom[:200] + "...") if case.symptom and len(case.symptom) > 200 else (case.symptom or ""),
                "score": 1.0,
            })
    
    return {
        "query": search_query,
        "search_type": search_type,
        "items": results[:limit],
        "total": len(results),
    }


# ============== SOP文档接口 ==============

@router.get("/sop", summary="获取SOP文档列表")
async def get_sop_documents(
    status: Optional[str] = Query(None, description="状态过滤"),
    category_id: Optional[int] = Query(None, description="分类ID过滤"),
    tags: Optional[str] = Query(None, description="标签过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取SOP文档列表"""
    query = db.query(SOPDocument).filter(SOPDocument.is_deleted == False)
    
    if status:
        try:
            status_enum = DocumentStatus(status)
            query = query.filter(SOPDocument.status == status_enum)
        except ValueError:
            pass
    
    if category_id:
        query = query.filter(SOPDocument.category_id == category_id)
    
    if tags:
        tag_list = [t.strip() for t in tags.split(',')]
        for tag in tag_list:
            query = query.filter(SOPDocument.tags.ilike(f"%{tag}%"))
    
    if keyword:
        query = query.filter(
            or_(
                SOPDocument.title.ilike(f"%{keyword}%"),
                SOPDocument.content.ilike(f"%{keyword}%"),
            )
        )
    
    total = query.count()
    sops = query.order_by(SOPDocument.updated_at.desc()).offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [_sop_to_dict(s) for s in sops],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/sop", summary="创建SOP文档")
async def create_sop_document(
    document: SOPDocumentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的SOP文档"""
    doc_no = f"SOP-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%m%d%H%M%S')}"
    
    db_sop = SOPDocument(
        doc_no=doc_no,
        title=document.title,
        content=document.content,
        category_id=document.category_id,
        tags=document.tags,
        author=document.author or current_user.username,
        status=DocumentStatus.DRAFT,
    )
    
    db.add(db_sop)
    db.commit()
    db.refresh(db_sop)
    
    return _sop_to_dict(db_sop)


@router.get("/sop/{doc_id}", summary="获取SOP文档详情")
async def get_sop_document(
    doc_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取SOP文档的详细信息"""
    sop = db.query(SOPDocument).filter(SOPDocument.id == doc_id, SOPDocument.is_deleted == False).first()
    
    if not sop:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 增加查看次数
    sop.view_count += 1
    db.commit()
    
    return _sop_to_dict(sop)


@router.put("/sop/{doc_id}", summary="更新SOP文档")
async def update_sop_document(
    doc_id: int,
    document: SOPDocumentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新SOP文档"""
    sop = db.query(SOPDocument).filter(SOPDocument.id == doc_id, SOPDocument.is_deleted == False).first()
    
    if not sop:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    update_data = document.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'status' and value:
            setattr(sop, key, DocumentStatus(value))
        else:
            setattr(sop, key, value)
    
    sop.updated_at = datetime.now()
    db.commit()
    db.refresh(sop)
    
    return _sop_to_dict(sop)


@router.delete("/sop/{doc_id}", summary="删除SOP文档")
async def delete_sop_document(
    doc_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除SOP文档（软删除）"""
    sop = db.query(SOPDocument).filter(SOPDocument.id == doc_id, SOPDocument.is_deleted == False).first()
    
    if not sop:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    sop.is_deleted = True
    sop.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "Document deleted successfully"}


@router.post("/sop/{doc_id}/review", summary="提交SOP文档审核")
async def submit_sop_review(
    doc_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交SOP文档进行审核"""
    sop = db.query(SOPDocument).filter(SOPDocument.id == doc_id, SOPDocument.is_deleted == False).first()
    
    if not sop:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    sop.status = DocumentStatus.PENDING_REVIEW
    sop.review_status = ReviewStatus.PENDING
    sop.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "Document submitted for review"}


@router.post("/sop/{doc_id}/approve", summary="批准SOP文档")
async def approve_sop_document(
    doc_id: int,
    comment: Optional[str] = Query(None, description="审核意见"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批准SOP文档"""
    sop = db.query(SOPDocument).filter(SOPDocument.id == doc_id, SOPDocument.is_deleted == False).first()
    
    if not sop:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    sop.status = DocumentStatus.APPROVED
    sop.review_status = ReviewStatus.APPROVED
    sop.review_comment = comment
    sop.approver = current_user.username
    sop.approval_date = datetime.now()
    sop.effective_date = datetime.now()
    sop.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "Document approved"}


# ============== 故障案例接口 ==============

@router.get("/fault-case", summary="获取故障案例列表")
async def get_fault_cases(
    fault_level: Optional[str] = Query(None, description="故障级别过滤"),
    fault_status: Optional[str] = Query(None, description="故障状态过滤"),
    fault_category: Optional[str] = Query(None, description="故障分类过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取故障案例列表"""
    query = db.query(FaultCase).filter(FaultCase.is_deleted == False)
    
    if fault_level:
        try:
            level_enum = FaultLevel(fault_level.lower())
            query = query.filter(FaultCase.fault_level == level_enum)
        except ValueError:
            pass
    
    if fault_status:
        try:
            status_enum = FaultStatus(fault_status)
            query = query.filter(FaultCase.fault_status == status_enum)
        except ValueError:
            pass
    
    if fault_category:
        query = query.filter(FaultCase.fault_category == fault_category)
    
    if keyword:
        query = query.filter(
            or_(
                FaultCase.title.ilike(f"%{keyword}%"),
                FaultCase.symptom.ilike(f"%{keyword}%"),
                FaultCase.root_cause.ilike(f"%{keyword}%"),
            )
        )
    
    total = query.count()
    cases = query.order_by(FaultCase.updated_at.desc()).offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [_case_to_dict(c) for c in cases],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/fault-case", summary="创建故障案例")
async def create_fault_case(
    case: FaultCaseCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的故障案例"""
    case_no = f"CASE-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%m%d%H%M%S')}"
    
    try:
        level_enum = FaultLevel(case.fault_level.lower())
    except ValueError:
        level_enum = FaultLevel.P3
    
    db_case = FaultCase(
        case_no=case_no,
        title=case.title,
        fault_level=level_enum,
        fault_status=FaultStatus.OPEN,
        fault_category=case.fault_category,
        symptom=case.symptom,
        root_cause=case.root_cause,
        solution=case.solution,
        prevention=case.prevention,
        tags=case.tags,
        category_id=case.category_id,
        author=current_user.username,
    )
    
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    
    return _case_to_dict(db_case)


@router.get("/fault-case/{case_id}", summary="获取故障案例详情")
async def get_fault_case(
    case_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取故障案例的详细信息"""
    case = db.query(FaultCase).filter(FaultCase.id == case_id, FaultCase.is_deleted == False).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")
    
    # 增加查看次数
    case.view_count += 1
    db.commit()
    
    return _case_to_dict(case)


@router.put("/fault-case/{case_id}", summary="更新故障案例")
async def update_fault_case(
    case_id: int,
    case: FaultCaseUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新故障案例"""
    db_case = db.query(FaultCase).filter(FaultCase.id == case_id, FaultCase.is_deleted == False).first()
    
    if not db_case:
        raise HTTPException(status_code=404, detail="案例不存在")
    
    update_data = case.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'fault_level' and value:
            try:
                setattr(db_case, key, FaultLevel(value.lower()))
            except ValueError:
                pass
        elif key == 'fault_status' and value:
            try:
                setattr(db_case, key, FaultStatus(value))
            except ValueError:
                pass
        else:
            setattr(db_case, key, value)
    
    db_case.updated_at = datetime.now()
    db.commit()
    db.refresh(db_case)
    
    return _case_to_dict(db_case)


# ============== 分类接口 ==============

@router.get("/category", summary="获取分类列表")
async def get_categories(
    doc_type: Optional[str] = Query(None, description="文档类型过滤"),
    parent_id: Optional[int] = Query(None, description="父分类ID"),
    include_children: bool = Query(False, description="是否包含子分类"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取文档分类列表"""
    query = db.query(Category).filter(Category.is_active == True)
    
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    else:
        query = query.filter(Category.parent_id == None)
    
    categories = query.all()
    
    return {
        "items": [_category_to_dict(c, include_children) for c in categories],
        "total": len(categories),
    }


@router.post("/category", summary="创建分类")
async def create_category(
    category: CategoryCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的分类"""
    db_category = Category(
        name=category.name,
        parent_id=category.parent_id,
        code=category.code,
        description=category.description,
    )
    
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    return _category_to_dict(db_category)


# ============== 标签接口 ==============

@router.get("/tag", summary="获取标签列表")
async def get_tags(
    category_id: Optional[int] = Query(None, description="分类ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    limit: int = Query(50, le=200, description="返回数量限制"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取标签列表"""
    query = db.query(Tag)
    
    if category_id:
        query = query.filter(Tag.category_id == category_id)
    
    if keyword:
        query = query.filter(Tag.name.ilike(f"%{keyword}%"))
    
    tags = query.order_by(Tag.usage_count.desc()).limit(limit).all()
    
    return {
        "items": [_tag_to_dict(t) for t in tags],
        "total": len(tags),
    }


# ============== 统计接口 ==============

@router.get("/stats", summary="获取知识库统计")
async def get_knowledge_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取知识库统计信息"""
    total_sops = db.query(SOPDocument).filter(SOPDocument.is_deleted == False).count()
    approved_sops = db.query(SOPDocument).filter(
        SOPDocument.is_deleted == False,
        SOPDocument.status == DocumentStatus.APPROVED
    ).count()
    
    total_cases = db.query(FaultCase).filter(FaultCase.is_deleted == False).count()
    
    total_categories = db.query(Category).filter(Category.is_active == True).count()
    total_tags = db.query(Tag).count()
    
    # 获取查看次数最高的标签
    top_tags = db.query(Tag).order_by(Tag.usage_count.desc()).limit(10).all()
    
    return {
        "total_documents": total_sops + total_cases,
        "sop_count": total_sops,
        "approved_sop_count": approved_sops,
        "fault_case_count": total_cases,
        "category_count": total_categories,
        "tag_count": total_tags,
        "top_tags": [{"name": t.name, "count": t.usage_count} for t in top_tags],
    }
