"""
报表管理API路由
提供报表生成、查询、导出等接口
"""

from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum
import os

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.report_template import (
    ReportTemplate, Report, ReportSchedule,
    ReportTemplateType, ReportFormat as DBReportFormat
)
from modules.business.report_generator.generator import ReportGenerator


router = APIRouter()


# ============== 枚举定义 ==============

class ReportType(str, Enum):
    """报表类型"""
    DAILY = "daily"           # 日报
    WEEKLY = "weekly"         # 周报
    MONTHLY = "monthly"       # 月报
    QUARTERLY = "quarterly"   # 季报
    ANNUAL = "annual"         # 年报
    CUSTOM = "custom"         # 自定义


class ReportFormat(str, Enum):
    """报表格式"""
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


# ============== 请求/响应模型 ==============

class ReportTemplateCreate(BaseModel):
    """创建报表模板"""
    name: str = Field(..., description="模板名称")
    report_type: str = Field(..., description="报表类型")
    description: Optional[str] = Field(None, description="模板描述")
    content: str = Field(..., description="模板内容(Jinja2)")
    config: Optional[dict] = Field(None, description="模板配置")


class ReportGenerateRequest(BaseModel):
    """生成报表请求"""
    template_id: Optional[int] = Field(None, description="模板ID")
    report_type: str = Field(..., description="报表类型")
    name: str = Field(..., description="报表名称")
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    format: str = Field("pdf", description="输出格式")
    filters: Optional[dict] = Field(None, description="筛选条件")
    params: Optional[dict] = Field(None, description="额外参数")


class ReportScheduleCreate(BaseModel):
    """创建定时报表"""
    name: str = Field(..., description="调度名称")
    template_id: int = Field(..., description="模板ID")
    cron_expression: str = Field(..., description="Cron表达式")
    format: str = Field("pdf", description="输出格式")
    date_range_type: str = Field("daily", description="日期范围类型")
    recipients: List[str] = Field(..., description="接收人邮箱列表")
    params: Optional[dict] = Field(None, description="额外参数")


def _map_template_type(report_type: str) -> ReportTemplateType:
    """映射前端报表类型到数据库枚举"""
    mapping = {
        'daily': ReportTemplateType.DEVICE_STATUS,
        'weekly': ReportTemplateType.ALERT_SUMMARY,
        'monthly': ReportTemplateType.PERFORMANCE_TREND,
        'quarterly': ReportTemplateType.PERFORMANCE_TREND,
        'annual': ReportTemplateType.PERFORMANCE_TREND,
        'custom': ReportTemplateType.CUSTOM,
        'device_status': ReportTemplateType.DEVICE_STATUS,
        'alert_summary': ReportTemplateType.ALERT_SUMMARY,
        'performance_trend': ReportTemplateType.PERFORMANCE_TREND,
    }
    return mapping.get(report_type, ReportTemplateType.CUSTOM)


def _map_report_format(fmt: str) -> DBReportFormat:
    """映射前端报表格式到数据库枚举"""
    mapping = {
        'pdf': DBReportFormat.PDF,
        'excel': DBReportFormat.EXCEL,
        'html': DBReportFormat.HTML,
    }
    return mapping.get(fmt, DBReportFormat.PDF)


def _report_to_dict(report: Report) -> dict:
    """报告模型转字典"""
    return {
        'id': report.id,
        'report_no': report.report_no,
        'name': report.name,
        'template_id': report.template_id,
        'template_type': report.template_type.value if report.template_type else None,
        'start_date': report.start_date.isoformat() if report.start_date else None,
        'end_date': report.end_date.isoformat() if report.end_date else None,
        'format': report.format.value if report.format else 'pdf',
        'status': report.status,
        'error_message': report.error_message,
        'file_path': report.file_path,
        'file_name': report.file_name,
        'file_size': report.file_size,
        'created_by': report.created_by,
        'created_at': report.created_at.isoformat() if report.created_at else None,
        'completed_at': report.completed_at.isoformat() if report.completed_at else None,
    }


def _template_to_dict(template: ReportTemplate) -> dict:
    """模板模型转字典"""
    return {
        'id': template.id,
        'name': template.name,
        'template_type': template.template_type.value if template.template_type else None,
        'description': template.description,
        'content': template.content,
        'config': template.config,
        'is_builtin': template.is_builtin,
        'is_active': template.is_active,
        'created_by': template.created_by,
        'created_at': template.created_at.isoformat() if template.created_at else None,
    }


# ============== 报表模板接口 ==============

@router.get("/template", summary="获取报表模板列表")
async def get_report_templates(
    report_type: Optional[str] = Query(None, description="报表类型过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取报表模板列表"""
    query = db.query(ReportTemplate)
    
    if report_type:
        template_type = _map_template_type(report_type)
        query = query.filter(ReportTemplate.template_type == template_type)
    
    if keyword:
        keyword_filter = f"%{keyword}%"
        query = query.filter(
            or_(
                ReportTemplate.name.ilike(keyword_filter),
                ReportTemplate.description.ilike(keyword_filter),
            )
        )
    
    # 只显示启用的模板
    query = query.filter(ReportTemplate.is_active == True)
    
    total = query.count()
    templates = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [_template_to_dict(t) for t in templates],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/template/{template_id}", summary="获取报表模板详情")
async def get_report_template(
    template_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取报表模板详情"""
    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return _template_to_dict(template)


@router.post("/template", summary="创建报表模板")
async def create_report_template(
    template: ReportTemplateCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的报表模板"""
    db_template = ReportTemplate(
        name=template.name,
        template_type=_map_template_type(template.report_type),
        description=template.description,
        content=template.content,
        config=template.config or {},
        created_by=current_user.username,
    )
    
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    
    return _template_to_dict(db_template)


@router.put("/template/{template_id}", summary="更新报表模板")
async def update_report_template(
    template_id: int,
    template: ReportTemplateCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新报表模板"""
    db_template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    
    if not db_template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    db_template.name = template.name
    db_template.template_type = _map_template_type(template.report_type)
    db_template.description = template.description
    db_template.content = template.content
    db_template.config = template.config or {}
    db_template.updated_by = current_user.username
    db_template.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_template)
    
    return _template_to_dict(db_template)


@router.delete("/template/{template_id}", summary="删除报表模板")
async def delete_report_template(
    template_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除报表模板（软删除）"""
    db_template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    
    if not db_template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 软删除：禁用模板
    db_template.is_active = False
    db_template.updated_by = current_user.username
    db_template.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "message": "模板已删除"}


# ============== 报表生成接口 ==============

@router.post("/generate", summary="生成报表")
async def generate_report(
    request: ReportGenerateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成报表"""
    # 获取模板内容
    template_content = None
    if request.template_id:
        template = db.query(ReportTemplate).filter(ReportTemplate.id == request.template_id).first()
        if template:
            template_content = template.content
    
    # 如果没有模板，使用默认内容
    if not template_content:
        template_content = """
        <html>
        <head><title>{{ name }}</title></head>
        <body>
            <h1>{{ name }}</h1>
            <p>报表周期: {{ start_date }} 至 {{ end_date }}</p>
            <p>生成时间: {{ report_date }}</p>
            <p>生成人: {{ generated_by }}</p>
        </body>
        </html>
        """
    
    # 创建报表记录
    report_no = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db_report = Report(
        report_no=report_no,
        name=request.name,
        template_id=request.template_id,
        template_type=_map_template_type(request.report_type),
        start_date=request.start_date,
        end_date=request.end_date,
        format=_map_report_format(request.format),
        filters=request.filters,
        params=request.params,
        status="generating",
        created_by=current_user.username,
    )
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # 调用报表生成器
    try:
        generator = ReportGenerator(output_dir="/tmp/reports")
        result = generator.generate(
            template_content=template_content,
            template_type=request.report_type,
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            filters=request.filters,
            params=request.params,
        )
        
        # 更新报表记录
        db_report.status = "completed"
        db_report.file_path = result.get("file_path")
        db_report.file_name = result.get("file_name")
        db_report.file_size = result.get("file_size")
        db_report.report_data = result.get("data")
        db_report.completed_at = datetime.now()
        db.commit()
        
        return {
            "id": db_report.id,
            "report_no": db_report.report_no,
            "status": "completed",
            "file_path": db_report.file_path,
            "message": "Report generated successfully",
        }
    except Exception as e:
        db_report.status = "failed"
        db_report.error_message = str(e)
        db.commit()
        
        return {
            "id": db_report.id,
            "report_no": db_report.report_no,
            "status": "failed",
            "message": f"Report generation failed: {str(e)}",
        }


@router.post("/generate/async", summary="异步生成报表")
async def generate_report_async(
    request: ReportGenerateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """异步生成报表（实际为同步，返回queued状态）"""
    # 获取模板内容
    template_content = None
    if request.template_id:
        template = db.query(ReportTemplate).filter(ReportTemplate.id == request.template_id).first()
        if template:
            template_content = template.content
    
    # 创建报表记录
    report_no = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db_report = Report(
        report_no=report_no,
        name=request.name,
        template_id=request.template_id,
        template_type=_map_template_type(request.report_type),
        start_date=request.start_date,
        end_date=request.end_date,
        format=_map_report_format(request.format),
        filters=request.filters,
        params=request.params,
        status="queued",
        created_by=current_user.username,
    )
    
    db.add(db_report)
    db.commit()
    
    return {
        "id": db_report.id,
        "report_no": db_report.report_no,
        "status": "queued",
        "message": "Report queued for generation",
    }


# ============== 报表列表接口 ==============

@router.get("/", summary="获取报表列表")
async def get_reports(
    pagination: PaginationParams = Depends(PaginationParams),
    report_type: Optional[str] = Query(None, description="报表类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取报表列表"""
    query = db.query(Report)
    
    if report_type:
        template_type = _map_template_type(report_type)
        query = query.filter(Report.template_type == template_type)
    
    if status:
        query = query.filter(Report.status == status)
    
    if start_date:
        query = query.filter(Report.start_date >= start_date)
    
    if end_date:
        query = query.filter(Report.end_date <= end_date)
    
    total = query.count()
    reports = query.order_by(Report.created_at.desc()).offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [_report_to_dict(r) for r in reports],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/stats", summary="获取报表统计")
async def get_report_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取报表统计信息"""
    total_reports = db.query(Report).count()
    total_size = db.query(Report.file_size).filter(Report.file_size != None).all()
    total_size = sum([r[0] or 0 for r in total_size])
    
    # 按状态统计
    completed_count = db.query(Report).filter(Report.status == "completed").count()
    failed_count = db.query(Report).filter(Report.status == "failed").count()
    generating_count = db.query(Report).filter(Report.status == "generating").count()
    
    # 按格式统计
    pdf_count = db.query(Report).filter(Report.format == DBReportFormat.PDF).count()
    excel_count = db.query(Report).filter(Report.format == DBReportFormat.EXCEL).count()
    html_count = db.query(Report).filter(Report.format == DBReportFormat.HTML).count()
    
    return {
        "total_reports": total_reports,
        "total_size": total_size,
        "by_status": {
            "completed": completed_count,
            "failed": failed_count,
            "generating": generating_count,
        },
        "by_format": {
            "pdf": pdf_count,
            "excel": excel_count,
            "html": html_count,
        },
    }


@router.get("/{report_id}", summary="获取报表详情")
async def get_report(
    report_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取报表的详细信息"""
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")
    
    return _report_to_dict(report)


@router.delete("/{report_id}", summary="删除报表")
async def delete_report(
    report_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除报表"""
    db_report = db.query(Report).filter(Report.id == report_id).first()
    
    if not db_report:
        raise HTTPException(status_code=404, detail="报表不存在")
    
    # 删除文件
    if db_report.file_path and os.path.exists(db_report.file_path):
        try:
            os.remove(db_report.file_path)
        except Exception:
            pass
    
    # 删除数据库记录
    db.delete(db_report)
    db.commit()
    
    return {
        "status": "success",
        "message": "Report deleted successfully",
    }


@router.get("/{report_id}/download", summary="下载报表")
async def download_report(
    report_id: int,
    format: Optional[str] = Query(None, description="下载格式"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """下载报表"""
    db_report = db.query(Report).filter(Report.id == report_id).first()
    
    if not db_report:
        raise HTTPException(status_code=404, detail="报表不存在")
    
    if db_report.status != "completed" or not db_report.file_path:
        raise HTTPException(status_code=400, detail="报表尚未生成完成")
    
    if not os.path.exists(db_report.file_path):
        raise HTTPException(status_code=404, detail="报表文件不存在")
    
    return FileResponse(
        path=db_report.file_path,
        filename=db_report.file_name or f"{db_report.report_no}.pdf",
        media_type="application/pdf" if db_report.format == DBReportFormat.PDF else "application/octet-stream",
    )


@router.get("/files/{filename}", summary="获取报表文件")
async def get_report_file(
    filename: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取报表文件"""
    file_path = f"/tmp/reports/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
    )


# ============== 定时报表接口 ==============

@router.get("/schedule", summary="获取定时报表列表")
async def get_report_schedules(
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取定时报表列表"""
    query = db.query(ReportSchedule)
    total = query.count()
    schedules = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return {
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "template_id": s.template_id,
                "cron_expression": s.cron_expression,
                "timezone": s.timezone,
                "format": s.format.value if s.format else "pdf",
                "recipients": s.recipients,
                "date_range_type": s.date_range_type,
                "is_enabled": s.is_enabled,
                "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                "last_run_status": s.last_run_status,
                "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
                "created_by": s.created_by,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in schedules
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/schedule", summary="创建定时报表")
async def create_report_schedule(
    schedule: ReportScheduleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建定时报表"""
    # 验证模板存在
    template = db.query(ReportTemplate).filter(ReportTemplate.id == schedule.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    db_schedule = ReportSchedule(
        name=schedule.name,
        template_id=schedule.template_id,
        cron_expression=schedule.cron_expression,
        format=_map_report_format(schedule.format),
        date_range_type=schedule.date_range_type,
        recipients=schedule.recipients,
        params=schedule.params,
        created_by=current_user.username,
    )
    
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    
    return {
        "id": db_schedule.id,
        "name": db_schedule.name,
        "cron_expression": db_schedule.cron_expression,
        "is_enabled": db_schedule.is_enabled,
        "created_at": db_schedule.created_at.isoformat() if db_schedule.created_at else None,
    }


@router.put("/schedule/{schedule_id}", summary="更新定时报表")
async def update_report_schedule(
    schedule_id: int,
    schedule: ReportScheduleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新定时报表"""
    db_schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    
    if not db_schedule:
        raise HTTPException(status_code=404, detail="调度不存在")
    
    db_schedule.name = schedule.name
    db_schedule.template_id = schedule.template_id
    db_schedule.cron_expression = schedule.cron_expression
    db_schedule.format = _map_report_format(schedule.format)
    db_schedule.date_range_type = schedule.date_range_type
    db_schedule.recipients = schedule.recipients
    db_schedule.params = schedule.params
    db_schedule.updated_by = current_user.username
    db_schedule.updated_at = datetime.now()
    
    db.commit()
    
    return {
        "id": db_schedule.id,
        "name": db_schedule.name,
        "message": "Schedule updated successfully",
    }


@router.delete("/schedule/{schedule_id}", summary="删除定时报表")
async def delete_report_schedule(
    schedule_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除定时报表"""
    db_schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    
    if not db_schedule:
        raise HTTPException(status_code=404, detail="调度不存在")
    
    db.delete(db_schedule)
    db.commit()
    
    return {"status": "success", "message": "Schedule deleted successfully"}


@router.post("/schedule/{schedule_id}/toggle", summary="启用/禁用定时报表")
async def toggle_report_schedule(
    schedule_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """启用或禁用定时报表"""
    db_schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    
    if not db_schedule:
        raise HTTPException(status_code=404, detail="调度不存在")
    
    db_schedule.is_enabled = not db_schedule.is_enabled
    db_schedule.updated_by = current_user.username
    db_schedule.updated_at = datetime.now()
    db.commit()
    
    return {
        "status": "success",
        "is_enabled": db_schedule.is_enabled,
        "message": f"Schedule {'enabled' if db_schedule.is_enabled else 'disabled'}",
    }
