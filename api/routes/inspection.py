"""
巡检管理API路由
提供巡检任务、巡检结果、巡检报告等接口
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
import io

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.inspection import (
    InspectionTask, InspectionResult, InspectionCheckItem,
    InspectionStatus as DBInspectionStatus
)
from modules.business.report_generator.inspection_report import InspectionReportGenerator


router = APIRouter(prefix="", tags=["巡检管理"])


# ============== 请求/响应模型 ==============

class InspectionTaskCreate(BaseModel):
    """创建巡检任务请求"""
    name: str = Field(..., description="巡检任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    inspection_type: str = Field("routine", description="巡检类型: routine/maintenance/emergency")
    target_type: str = Field("device", description="巡检对象类型: device/group/all")
    target_ids: Optional[List[int]] = Field(None, description="巡检对象ID列表")
    check_items: Optional[List[dict]] = Field(None, description="巡检项定义")
    schedule_type: str = Field("manual", description="调度类型: manual/scheduled/auto")


class InspectionReportResponse(BaseModel):
    """巡检报告响应"""
    task_info: dict
    statistics: dict
    devices: List[dict]
    suggestions: List[dict]
    history_comparison: dict
    health_score: float
    health_level: dict
    generated_at: str


# ============== 巡检任务接口 ==============

@router.get("/tasks", summary="获取巡检任务列表")
async def get_inspection_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    inspection_type: Optional[str] = Query(None, description="巡检类型过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取巡检任务列表"""
    query = db.query(InspectionTask)
    
    if status:
        query = query.filter(InspectionTask.status == status)
    if inspection_type:
        query = query.filter(InspectionTask.inspection_type == inspection_type)
    
    total = query.count()
    tasks = query.order_by(InspectionTask.created_at.desc()).offset(pagination.offset).limit(pagination.limit).all()
    
    items = []
    for task in tasks:
        items.append({
            'id': task.id,
            'task_no': task.task_no,
            'name': task.name,
            'description': task.description,
            'inspection_type': task.inspection_type,
            'target_type': task.target_type,
            'status': task.status,
            'progress': task.progress,
            'total_devices': task.total_devices,
            'healthy_devices': task.healthy_devices,
            'warning_devices': task.warning_devices,
            'critical_devices': task.critical_devices,
            'offline_devices': task.offline_devices,
            'health_score': task.health_score,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'executor': task.executor,
            'created_at': task.created_at.isoformat() if task.created_at else None,
        })
    
    return {"data": items, "total": total, "code": 0}


@router.get("/tasks/{task_id}", summary="获取巡检任务详情")
async def get_inspection_task(
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取巡检任务详细信息"""
    task = db.query(InspectionTask).filter(InspectionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="巡检任务不存在")
    
    return {
        "data": {
            'id': task.id,
            'task_no': task.task_no,
            'name': task.name,
            'description': task.description,
            'inspection_type': task.inspection_type,
            'target_type': task.target_type,
            'target_ids': task.target_ids,
            'config': task.config,
            'check_items': task.check_items,
            'status': task.status,
            'progress': task.progress,
            'total_items': task.total_items,
            'completed_items': task.completed_items,
            'total_devices': task.total_devices,
            'healthy_devices': task.healthy_devices,
            'warning_devices': task.warning_devices,
            'critical_devices': task.critical_devices,
            'offline_devices': task.offline_devices,
            'health_score': task.health_score,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'executor': task.executor,
            'created_at': task.created_at.isoformat() if task.created_at else None,
        },
        "code": 0
    }


@router.post("/tasks", summary="创建巡检任务")
async def create_inspection_task(
    request: InspectionTaskCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的巡检任务"""
    task_no = f"INS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    db_task = InspectionTask(
        task_no=task_no,
        name=request.name,
        description=request.description,
        inspection_type=request.inspection_type,
        target_type=request.target_type,
        target_ids=request.target_ids,
        check_items=request.check_items,
        schedule_type=request.schedule_type,
        status=DBInspectionStatus.PENDING,
        created_by=current_user.username,
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return {
        "data": {
            'id': db_task.id,
            'task_no': db_task.task_no,
            'name': db_task.name,
            'status': db_task.status,
        },
        "code": 0,
        "message": "巡检任务创建成功"
    }


# ============== 巡检报告接口 ==============

@router.get("/reports/{task_id}", summary="获取巡检报告")
async def get_inspection_report(
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取巡检报告数据
    
    基于巡检任务ID生成包含以下内容的报告：
    - 设备健康度评分
    - 异常统计
    - 建议措施
    - 历史对比
    """
    # 验证任务存在
    task = db.query(InspectionTask).filter(InspectionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="巡检任务不存在")
    
    # 生成报告
    try:
        generator = InspectionReportGenerator(db_session=db)
        report_data = generator.generate_report(task_id)
        
        return {
            "data": report_data,
            "code": 0,
            "message": "报告生成成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")


@router.get("/reports/{task_id}/export", summary="导出巡检报告")
async def export_inspection_report(
    task_id: int,
    format: str = Query("html", description="导出格式: html/pdf"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    导出巡检报告为HTML或PDF格式
    """
    # 验证任务存在
    task = db.query(InspectionTask).filter(InspectionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="巡检任务不存在")
    
    try:
        generator = InspectionReportGenerator(db_session=db)
        
        if format.lower() == "pdf":
            content, content_type = generator.export_pdf(task_id)
            filename = f"inspection_report_{task.task_no}.pdf"
        else:
            content, content_type = generator.export_html(task_id)
            filename = f"inspection_report_{task.task_no}.html"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
    except ImportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告导出失败: {str(e)}")


@router.get("/reports/template", summary="获取巡检报告模板")
async def get_report_template(
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取巡检报告模板配置"""
    generator = InspectionReportGenerator()
    template = generator.get_report_template()
    
    return {
        "data": template,
        "code": 0
    }


# ============== 巡检结果接口 ==============

@router.get("/results/{task_id}", summary="获取巡检结果列表")
async def get_inspection_results(
    task_id: int,
    device_id: Optional[int] = Query(None, description="设备ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取巡检结果列表"""
    query = db.query(InspectionResult).filter(InspectionResult.task_id == task_id)
    
    if device_id:
        query = query.filter(InspectionResult.device_id == device_id)
    if status:
        query = query.filter(InspectionResult.status == status)
    
    total = query.count()
    results = query.offset(pagination.offset).limit(pagination.limit).all()
    
    items = []
    for r in results:
        items.append({
            'id': r.id,
            'device_id': r.device_id,
            'device_name': r.device_name,
            'device_ip': r.device_ip,
            'device_type': r.device_type,
            'check_item_id': r.check_item_id,
            'check_item_name': r.check_item_name,
            'check_category': r.check_category,
            'status': r.status,
            'result_value': r.result_value,
            'result_message': r.result_message,
            'expected_value': r.expected_value,
            'severity': r.severity,
            'suggestion': r.suggestion,
            'checked_at': r.checked_at.isoformat() if r.checked_at else None,
        })
    
    return {"data": items, "total": total, "code": 0}


@router.get("/statistics/summary", summary="获取巡检统计摘要")
async def get_inspection_summary(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取巡检统计摘要"""
    total_tasks = db.query(InspectionTask).count()
    completed_tasks = db.query(InspectionTask).filter(
        InspectionTask.status == DBInspectionStatus.COMPLETED
    ).count()
    running_tasks = db.query(InspectionTask).filter(
        InspectionTask.status == DBInspectionStatus.RUNNING
    ).count()
    
    # 最近一次巡检的平均健康度
    latest_task = db.query(InspectionTask).filter(
        InspectionTask.status == DBInspectionStatus.COMPLETED,
        InspectionTask.health_score.isnot(None)
    ).order_by(InspectionTask.completed_at.desc()).first()
    
    return {
        "data": {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'running_tasks': running_tasks,
            'latest_health_score': latest_task.health_score if latest_task else None,
            'latest_task_no': latest_task.task_no if latest_task else None,
        },
        "code": 0
    }
