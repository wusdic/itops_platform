"""
定时报告调度API路由
提供定时报告的CRUD操作和执行控制
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
    ReportTemplate, ReportSchedule, ReportTemplateType, ReportFormat
)
from modules.business.report_generator.scheduler import (
    get_scheduler, start_scheduler, stop_scheduler
)
from modules.business.report_generator.generator import ReportGenerator, BUILTIN_TEMPLATES


router = APIRouter(prefix="/schedule", tags=["定时报告管理"])


# ============== 枚举定义 ==============

class DateRangeType(str, Enum):
    """日期范围类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ============== 请求/响应模型 ==============

class ScheduleCreate(BaseModel):
    """创建定时报告请求"""
    name: str = Field(..., description="调度名称", min_length=1, max_length=200)
    template_id: int = Field(..., description="模板ID")
    cron_expression: str = Field(..., description="Cron表达式 (分 时 日 月 周)")
    format: str = Field("pdf", description="输出格式")
    recipients: List[str] = Field(..., description="接收人邮箱列表")
    date_range_type: DateRangeType = Field(DateRangeType.DAILY, description="日期范围类型")
    params: Optional[dict] = Field(None, description="额外参数")
    is_enabled: bool = Field(True, description="是否启用")


class ScheduleUpdate(BaseModel):
    """更新定时报告请求"""
    name: Optional[str] = Field(None, description="调度名称")
    cron_expression: Optional[str] = Field(None, description="Cron表达式")
    format: Optional[str] = Field(None, description="输出格式")
    recipients: Optional[List[str]] = Field(None, description="接收人邮箱列表")
    date_range_type: Optional[DateRangeType] = Field(None, description="日期范围类型")
    params: Optional[dict] = Field(None, description="额外参数")
    is_enabled: Optional[bool] = Field(None, description="是否启用")


class ScheduleResponse(BaseModel):
    """定时报告响应"""
    id: int
    name: str
    template_id: int
    cron_expression: str
    format: str
    recipients: List[str]
    date_range_type: str
    params: Optional[dict]
    is_enabled: bool
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    next_run_at: Optional[datetime]
    created_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ExecuteNowRequest(BaseModel):
    """立即执行请求"""
    schedule_id: int = Field(..., description="调度ID")
    test_mode: bool = Field(False, description="测试模式(仅生成不发邮件)")


# ============== 辅助函数 ==============

def get_date_range(date_range_type: str) -> tuple:
    """根据日期范围类型计算日期范围"""
    now = datetime.now()
    if date_range_type == "daily":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif date_range_type == "weekly":
        # 上周一
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        days_since_monday = now.weekday()
        start_date = start_date - datetime.timedelta(days=days_since_monday)
        end_date = now
    elif date_range_type == "monthly":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    else:
        start_date = now - datetime.timedelta(days=1)
        end_date = now
    
    return start_date, end_date


def generate_scheduled_report(schedule: ReportSchedule):
    """生成定时报告的核心逻辑"""
    try:
        # 获取模板
        template = None
        db_gen = next(get_db())
        template = db_gen.query(ReportTemplate).filter(
            ReportTemplate.id == schedule.template_id
        ).first()
        
        if not template:
            logger.error(f"Template {schedule.template_id} not found")
            return
        
        # 计算日期范围
        start_date, end_date = get_date_range(schedule.date_range_type)
        
        # 生成报告
        generator = ReportGenerator()
        result = generator.generate(
            template_content=template.content,
            template_type=template.template_type,
            start_date=start_date,
            end_date=end_date,
            format=schedule.format,
            params={
                "title": schedule.name,
                **(schedule.params or {})
            }
        )
        
        # 更新执行状态
        schedule.last_run_at = datetime.now()
        schedule.last_run_status = "success"
        
        # 计算下次执行时间
        from modules.business.report_generator.scheduler import get_scheduler
        scheduler = get_scheduler()
        schedule.next_run_at = scheduler.calculate_next_run(schedule.cron_expression)
        
        db_gen.commit()
        
        # TODO: 发送邮件给recipients
        logger.info(f"Report {result['report_no']} generated successfully")
        
    except Exception as e:
        logger.error(f"Failed to generate scheduled report: {e}")
        schedule.last_run_status = f"failed: {str(e)}"
        db_gen.commit()


# ============== API接口 ==============

@router.get("/", summary="获取定时报告列表")
async def list_schedules(
    is_enabled: Optional[bool] = Query(None, description="是否启用"),
    pagination: PaginationParams = Depends(PaginationParams),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取定时报告调度列表"""
    query = db.query(ReportSchedule)
    
    if is_enabled is not None:
        query = query.filter(ReportSchedule.is_enabled == is_enabled)
    
    total = query.count()
    items = query.offset((pagination.page - 1) * pagination.page_size)\
                  .limit(pagination.page_size)\
                  .all()
    
    return {
        "items": [ScheduleResponse.model_validate(s) for s in items],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/{schedule_id}", summary="获取定时报告详情")
async def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取定时报告的详细信息"""
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # 获取关联的模板信息
    template = db.query(ReportTemplate).filter(ReportTemplate.id == schedule.template_id).first()
    
    response = ScheduleResponse.model_validate(schedule)
    
    return {
        **response.model_dump(),
        "template": {
            "id": template.id,
            "name": template.name,
            "template_type": template.template_type
        } if template else None
    }


@router.post("/", summary="创建定时报告", status_code=201)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    创建新的定时报告调度
    
    - **name**: 调度名称(必填)
    - **template_id**: 模板ID(必填)
    - **cron_expression**: Cron表达式，格式: 分 时 日 月 周 (必填)
    - **format**: 输出格式 (pdf/excel)
    - **recipients**: 接收人邮箱列表(必填)
    - **date_range_type**: 日期范围类型 (daily/weekly/monthly)
    - **params**: 额外参数
    - **is_enabled**: 是否启用
    """
    # 验证模板存在
    template = db.query(ReportTemplate).filter(ReportTemplate.id == schedule_data.template_id).first()
    if not template:
        raise HTTPException(status_code=400, detail="Template not found")
    
    # 验证cron表达式格式
    parts = schedule_data.cron_expression.split()
    if len(parts) != 5:
        raise HTTPException(status_code=400, detail="Invalid cron expression format")
    
    # 计算下次执行时间
    scheduler = get_scheduler()
    start_scheduler()  # 确保调度器已启动
    next_run = scheduler.calculate_next_run(schedule_data.cron_expression)
    
    schedule = ReportSchedule(
        name=schedule_data.name,
        template_id=schedule_data.template_id,
        cron_expression=schedule_data.cron_expression,
        format=schedule_data.format,
        recipients=schedule_data.recipients,
        date_range_type=schedule_data.date_range_type.value,
        params=schedule_data.params,
        is_enabled=schedule_data.is_enabled,
        next_run_at=next_run,
        created_by=current_user.username
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    # 添加到调度器
    schedule_id_str = f"report_schedule_{schedule.id}"
    scheduler.add_schedule(
        schedule_id=schedule_id_str,
        cron_expression=schedule_data.cron_expression,
        func=generate_scheduled_report,
        args=(schedule,)
    )
    
    if not schedule_data.is_enabled:
        scheduler.pause_schedule(schedule_id_str)
    
    return {
        "id": schedule.id,
        "name": schedule.name,
        "next_run_at": next_run.isoformat() if next_run else None,
        "message": "Schedule created successfully"
    }


@router.put("/{schedule_id}", summary="更新定时报告")
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    更新定时报告调度配置
    
    - **name**: 调度名称
    - **cron_expression**: Cron表达式
    - **format**: 输出格式
    - **recipients**: 接收人邮箱列表
    - **date_range_type**: 日期范围类型
    - **params**: 额外参数
    - **is_enabled**: 是否启用
    """
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    update_data = schedule_data.model_dump(exclude_unset=True)
    
    # 如果更新了cron表达式
    if "cron_expression" in update_data:
        parts = update_data["cron_expression"].split()
        if len(parts) != 5:
            raise HTTPException(status_code=400, detail="Invalid cron expression format")
    
    for field, value in update_data.items():
        if field == "recipients" and value:
            setattr(schedule, field, value)
        elif field == "date_range_type" and value:
            setattr(schedule, field, value.value)
        elif hasattr(schedule, field):
            setattr(schedule, field, value)
    
    schedule.updated_by = current_user.username
    schedule.updated_at = datetime.now()
    
    db.commit()
    
    # 更新调度器中的任务
    scheduler = get_scheduler()
    schedule_id_str = f"report_schedule_{schedule.id}"
    
    if schedule.is_enabled:
        if scheduler.get_schedule_info(schedule_id_str):
            scheduler.remove_schedule(schedule_id_str)
        scheduler.add_schedule(
            schedule_id=schedule_id_str,
            cron_expression=schedule.cron_expression,
            func=generate_scheduled_report,
            args=(schedule,)
        )
    else:
        scheduler.pause_schedule(schedule_id_str)
    
    return {"message": "Schedule updated successfully"}


@router.delete("/{schedule_id}", summary="删除定时报告")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """删除定时报告调度"""
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # 从调度器移除
    scheduler = get_scheduler()
    schedule_id_str = f"report_schedule_{schedule_id}"
    scheduler.remove_schedule(schedule_id_str)
    
    db.delete(schedule)
    db.commit()
    
    return {"message": "Schedule deleted successfully"}


@router.post("/{schedule_id}/execute", summary="立即执行")
async def execute_schedule_now(
    schedule_id: int,
    test_mode: bool = Query(False, description="测试模式"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    立即执行定时报告
    
    - **test_mode**: 测试模式，仅生成不发邮件
    """
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    try:
        # 执行报告生成
        generate_scheduled_report(schedule)
        
        return {
            "status": "success",
            "message": "Report executed successfully",
            "test_mode": test_mode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/{schedule_id}/enable", summary="启用定时报告")
async def enable_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """启用定时报告调度"""
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if schedule.is_enabled:
        return {"message": "Schedule is already enabled"}
    
    schedule.is_enabled = True
    db.commit()
    
    # 添加到调度器
    scheduler = get_scheduler()
    start_scheduler()
    scheduler.resume_schedule(f"report_schedule_{schedule_id}")
    
    return {"message": "Schedule enabled successfully"}


@router.post("/{schedule_id}/disable", summary="禁用定时报告")
async def disable_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """禁用定时报告调度"""
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if not schedule.is_enabled:
        return {"message": "Schedule is already disabled"}
    
    schedule.is_enabled = False
    db.commit()
    
    # 从调度器暂停
    scheduler = get_scheduler()
    scheduler.pause_schedule(f"report_schedule_{schedule_id}")
    
    return {"message": "Schedule disabled successfully"}


@router.get("/{schedule_id}/status", summary="获取执行状态")
async def get_schedule_status(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取定时报告的执行状态"""
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    scheduler = get_scheduler()
    job_info = scheduler.get_schedule_info(f"report_schedule_{schedule_id}")
    
    return {
        "schedule_id": schedule.id,
        "name": schedule.name,
        "is_enabled": schedule.is_enabled,
        "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        "last_run_status": schedule.last_run_status,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "scheduler_status": job_info
    }