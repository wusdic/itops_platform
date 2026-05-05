"""
报告模板管理API路由
提供报告模板的CRUD操作
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.base import Base
from modules.foundation.db_models.report_template import (
    ReportTemplate, ReportTemplateType, ReportFormat, Report
)
from modules.business.report_generator.generator import (
    ReportGenerator, BUILTIN_TEMPLATES
)


router = APIRouter(tags=["报告模板管理"])


# ============== 枚举定义 ==============

class TemplateTypeEnum(str, Enum):
    """模板类型枚举"""
    DEVICE_STATUS = "device_status"
    ALERT_SUMMARY = "alert_summary"
    PERFORMANCE_TREND = "performance_trend"
    CUSTOM = "custom"


# ============== 请求/响应模型 ==============

class TemplateCreate(BaseModel):
    """创建模板请求"""
    name: str = Field(..., description="模板名称", min_length=1, max_length=200)
    template_type: TemplateTypeEnum = Field(..., description="模板类型")
    description: Optional[str] = Field(None, description="模板描述")
    content: Optional[str] = Field(None, description="模板内容(Jinja2)")
    config: Optional[dict] = Field(None, description="模板配置")


class TemplateUpdate(BaseModel):
    """更新模板请求"""
    name: Optional[str] = Field(None, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    content: Optional[str] = Field(None, description="模板内容(Jinja2)")
    config: Optional[dict] = Field(None, description="模板配置")
    is_active: Optional[bool] = Field(None, description="是否启用")


class TemplateResponse(BaseModel):
    """模板响应"""
    id: int
    name: str
    template_type: str
    description: Optional[str]
    content: Optional[str]
    config: Optional[dict]
    is_builtin: bool
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============== API接口 ==============

@router.get("/", summary="获取模板列表")
async def list_templates(
    template_type: Optional[TemplateTypeEnum] = Query(None, description="模板类型过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    pagination: PaginationParams = Depends(PaginationParams),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取报告模板列表
    
    - **template_type**: 按模板类型过滤
    - **keyword**: 关键词搜索(名称/描述)
    - **is_active**: 是否启用状态
    """
    query = db.query(ReportTemplate)
    
    if template_type:
        query = query.filter(ReportTemplate.template_type == template_type.value)
    
    if keyword:
        query = query.filter(
            ReportTemplate.name.contains(keyword) | 
            ReportTemplate.description.contains(keyword)
        )
    
    if is_active is not None:
        query = query.filter(ReportTemplate.is_active == is_active)
    
    total = query.count()
    items = query.offset((pagination.page - 1) * pagination.page_size)\
                  .limit(pagination.page_size)\
                  .all()
    
    return {
        "items": [TemplateResponse.model_validate(t) for t in items],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/builtin", summary="获取内置模板")
async def list_builtin_templates(
    template_type: Optional[TemplateTypeEnum] = Query(None, description="模板类型过滤"),
):
    """获取系统内置模板列表"""
    if template_type:
        templates = {template_type.value: BUILTIN_TEMPLATES.get(template_type.value)}
    else:
        templates = BUILTIN_TEMPLATES
    
    return {
        "items": [
            {
                "type": t_type,
                "name": t_type.replace("_", " ").title(),
                "preview": content[:500] + "..." if len(content) > 500 else content
            }
            for t_type, content in templates.items() if content
        ]
    }


@router.get("/{template_id}", summary="获取模板详情")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取报告模板的详细信息"""
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return TemplateResponse.model_validate(template)


@router.post("/", summary="创建模板", status_code=201)
async def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    创建新的报告模板
    
    - **name**: 模板名称(必填)
    - **template_type**: 模板类型(必填)
    - **description**: 模板描述
    - **content**: Jinja2模板内容(如果不提供，将使用内置模板)
    - **config**: 模板配置
    """
    # 如果没有提供内容，使用内置模板
    content = template_data.content
    if not content and template_data.template_type.value in BUILTIN_TEMPLATES:
        content = BUILTIN_TEMPLATES[template_data.template_type.value]
    
    template = ReportTemplate(
        name=template_data.name,
        template_type=template_data.template_type.value,
        description=template_data.description,
        content=content,
        config=template_data.config or {},
        is_active=True,
        created_by=current_user.username
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {
        "id": template.id,
        "name": template.name,
        "message": "Template created successfully"
    }


@router.put("/{template_id}", summary="更新模板")
async def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    更新报告模板
    
    - **name**: 模板名称
    - **description**: 模板描述
    - **content**: Jinja2模板内容
    - **config**: 模板配置
    - **is_active**: 是否启用
    """
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if template.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot modify builtin templates")
    
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    template.updated_by = current_user.username
    template.updated_at = datetime.now()
    
    db.commit()
    
    return {"message": "Template updated successfully"}


@router.delete("/{template_id}", summary="删除模板")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """删除报告模板"""
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if template.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot delete builtin templates")
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template deleted successfully"}


@router.post("/{template_id}/duplicate", summary="复制模板")
async def duplicate_template(
    template_id: int,
    new_name: str = Query(..., description="新模板名称"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """复制现有模板创建新模板"""
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    new_template = ReportTemplate(
        name=new_name,
        template_type=template.template_type,
        description=template.description,
        content=template.content,
        config=template.config,
        is_active=True,
        created_by=current_user.username
    )
    
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return {
        "id": new_template.id,
        "name": new_template.name,
        "message": "Template duplicated successfully"
    }


@router.post("/preview", summary="预览模板")
async def preview_template(
    template_type: TemplateTypeEnum = Query(..., description="模板类型"),
    content: Optional[str] = Query(None, description="自定义模板内容"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
):
    """
    预览模板渲染结果
    
    - **template_type**: 模板类型
    - **content**: 自定义模板内容(可选，默认使用内置模板)
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    generator = ReportGenerator()
    
    # 获取模板内容
    template_content = content if content else BUILTIN_TEMPLATES.get(template_type.value, "")
    
    if not template_content:
        raise HTTPException(status_code=400, detail="Template content not provided")
    
    # 设置默认日期
    if not start_date:
        start_date = datetime.now()
    if not end_date:
        end_date = datetime.now()
    
    try:
        result = generator.generate(
            template_content=template_content,
            template_type=template_type.value,
            start_date=start_date,
            end_date=end_date,
            format="pdf"
        )
        return {
            "status": "success",
            "preview_url": f"/api/v1/report/files/{result['file_name']}",
            "file_name": result["file_name"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")