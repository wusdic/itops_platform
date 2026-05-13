"""
工单管理API路由
提供工单创建、查询、审批、处理等接口
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.foundation.db_models.workorder import (
    WorkOrder, WorkOrderFlow, WorkOrderType, WorkOrderStatus, WorkOrderPriority
)
from modules.business.workorder.workorder import WorkOrderCore
from modules.business.report_generator.excel_exporter import WorkOrderExporter, ExportFormat

router = APIRouter()


# ============== 请求/响应模型 ==============

class WorkOrderCreate(BaseModel):
    """创建工单请求"""
    order_type: str = Field(..., description="工单类型: fault, change, inspection, security, demand, question")
    title: str = Field(..., max_length=256, description="工单标题")
    description: Optional[str] = Field(None, description="工单描述")
    priority: str = Field("P3", description="优先级: P1, P2, P3, P4")
    device_id: Optional[int] = Field(None, description="关联设备ID")
    device_name: Optional[str] = Field(None, description="关联设备名称")
    device_ip: Optional[str] = Field(None, description="关联设备IP")
    assignee: Optional[str] = Field(None, description="处理人")
    expected_end: Optional[datetime] = Field(None, description="期望完成时间")
    impact: Optional[str] = Field(None, description="影响范围")
    tags: Optional[str] = Field(None, description="标签")
    attachments: Optional[List[dict]] = Field(None, description="附件列表")


class WorkOrderUpdate(BaseModel):
    """更新工单请求"""
    title: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    expected_end: Optional[datetime] = None
    tags: Optional[str] = None
    resolution: Optional[str] = None
    root_cause: Optional[str] = None
    improvement: Optional[str] = None


class WorkOrderFlowCreate(BaseModel):
    """创建工单流程记录"""
    action: str = Field(..., description="操作: assign, approve, reject, resolve, close, cancel")
    comment: Optional[str] = Field(None, description="意见/备注")
    to_status: Optional[str] = Field(None, description="新状态")


class WorkOrderDraftSave(BaseModel):
    """保存工单草稿请求"""
    draft_id: Optional[str] = Field(None, description="草稿ID(更新时传入)")
    order_type: Optional[str] = Field(None, description="工单类型")
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    priority: Optional[str] = Field("P3", description="优先级")
    device_id: Optional[int] = Field(None, description="设备ID")
    device_name: Optional[str] = Field(None, description="设备名称")
    device_ip: Optional[str] = Field(None, description="设备IP")
    assignee: Optional[str] = Field(None, description="处理人")
    expected_end: Optional[datetime] = Field(None, description="期望完成时间")
    impact: Optional[str] = Field(None, description="影响范围")
    tags: Optional[List[str]] = Field(None, description="标签")
    attachments: Optional[List[dict]] = Field(None, description="附件")
    is_auto_save: bool = Field(False, description="是否自动保存")


class WorkOrderResponse(BaseModel):
    """工单响应"""
    id: int
    order_no: str
    order_type: str
    priority: str
    title: str
    description: Optional[str] = None
    status: str
    device_name: Optional[str] = None
    device_ip: Optional[str] = None
    creator: str
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime


def _build_workorder_core(db: Session) -> WorkOrderCore:
    """构建工单核心实例"""
    return WorkOrderCore(db)


def _map_order_type(order_type: str) -> WorkOrderType:
    """映射工单类型字符串到枚举"""
    mapping = {
        'fault': WorkOrderType.FAULT,
        'change': WorkOrderType.CHANGE,
        'inspection': WorkOrderType.INSPECTION,
        'security': WorkOrderType.SECURITY,
        'demand': WorkOrderType.DEMAND,
        'question': WorkOrderType.QUESTION,
        'other': WorkOrderType.OTHER,
    }
    return mapping.get(order_type, WorkOrderType.OTHER)


def _map_priority(priority: str) -> WorkOrderPriority:
    """映射优先级字符串到枚举"""
    mapping = {
        'P1': WorkOrderPriority.P1,
        'P2': WorkOrderPriority.P2,
        'P3': WorkOrderPriority.P3,
        'P4': WorkOrderPriority.P4,
    }
    return mapping.get(priority, WorkOrderPriority.P3)


def _map_status(status: str) -> WorkOrderStatus:
    """映射状态字符串到枚举"""
    mapping = {
        'pending': WorkOrderStatus.PENDING,
        'processing': WorkOrderStatus.PROCESSING,
        'pending_approval': WorkOrderStatus.PENDING_APPROVAL,
        'approved': WorkOrderStatus.APPROVED,
        'rejected': WorkOrderStatus.REJECTED,
        'resolved': WorkOrderStatus.RESOLVED,
        'closed': WorkOrderStatus.CLOSED,
        'cancelled': WorkOrderStatus.CANCELLED,
    }
    return mapping.get(status, WorkOrderStatus.PENDING)


def _workorder_to_dict(wo: WorkOrder) -> dict:
    """工单模型转字典"""
    return {
        'id': wo.id,
        'order_no': wo.order_no,
        'order_type': wo.order_type.value if wo.order_type else None,
        'priority': wo.priority.value if wo.priority else None,
        'title': wo.title,
        'description': wo.description,
        'status': wo.status.value if wo.status else None,
        'device_id': wo.device_id,
        'device_name': wo.device_name,
        'device_ip': wo.device_ip,
        'creator': wo.creator,
        'assignee': wo.assignee,
        'created_at': wo.created_at.isoformat() if wo.created_at else None,
        'updated_at': wo.updated_at.isoformat() if wo.updated_at else None,
    }


# ============== 工单接口 ==============

@router.get("/", summary="获取工单列表")
async def get_workorders(
    status_filter: Optional[str] = Query(None, alias="status", description="状态过滤"),
    order_type: Optional[str] = Query(None, description="工单类型过滤"),
    priority: Optional[str] = Query(None, description="优先级过滤"),
    assignee: Optional[str] = Query(None, description="处理人过滤"),
    creator: Optional[str] = Query(None, description="创建人过滤"),
    device_id: Optional[int] = Query(None, description="设备ID过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    start_date: Optional[datetime] = Query(None, description="创建时间开始"),
    end_date: Optional[datetime] = Query(None, description="创建时间结束"),
    pagination: PaginationParams = Depends(PaginationParams),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取工单列表
    支持多条件过滤和分页
    """
    core = _build_workorder_core(db)
    
    # 映射过滤参数
    status_enum = _map_status(status_filter) if status_filter else None
    type_enum = _map_order_type(order_type) if order_type else None
    priority_enum = _map_priority(priority) if priority else None
    
    # 查询工单列表
    workorders, total = core.list(
        status=status_enum,
        order_type=type_enum,
        priority=priority_enum,
        creator=creator,
        assignee=assignee,
        start_time=start_date,
        end_time=end_date,
        page=pagination.page,
        page_size=pagination.page_size
    )
    
    return {
        "items": [_workorder_to_dict(wo) for wo in workorders],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/export", summary="导出工单")
async def export_workorders(
    status: Optional[str] = Query(None, description="状态过滤"),
    priority: Optional[str] = Query(None, description="优先级过滤"),
    start_date: Optional[datetime] = Query(None, description="创建时间开始"),
    end_date: Optional[datetime] = Query(None, description="创建时间结束"),
    format: Optional[str] = Query("excel", description="导出格式: excel/csv"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    导出工单到Excel或CSV文件
    支持按状态、优先级、时间范围过滤
    """
    core = _build_workorder_core(db)
    
    # 映射过滤参数
    status_enum = _map_status(status) if status else None
    priority_enum = _map_priority(priority) if priority else None
    
    # 查询工单列表 (不分页，获取所有)
    workorders, total = core.list(
        status=status_enum,
        priority=priority_enum,
        start_time=start_date,
        end_time=end_date,
        page=1,
        page_size=10000  # 最大导出10000条
    )
    
    if not workorders:
        return {"data": [], "code": 0, "message": "没有可导出的工单"}
    
    # 转换为字典
    workorder_dicts = [_workorder_to_dict(wo) for wo in workorders]
    
    # 导出
    exporter = WorkOrderExporter()
    export_format = ExportFormat.CSV if format == 'csv' else ExportFormat.XLSX
    
    file_bytes, content_type = exporter.export(workorder_dicts, format=export_format)
    
    from fastapi.responses import StreamingResponse
    import io
    
    filename = f"workorders_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format == 'csv':
        filename += ".csv"
        media_type = "text/csv; charset=utf-8-sig"
    else:
        filename += ".xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


@router.get("/export/{workorder_id}", summary="导出单个工单")
async def export_single_workorder(
    workorder_id: int,
    format: Optional[str] = Query("excel", description="导出格式: excel/csv"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    导出单个工单到Excel或CSV文件
    """
    core = _build_workorder_core(db)
    
    # 获取工单
    wo = core.get_by_id(workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    # 转换为字典
    wo_dict = _workorder_to_dict(wo)
    
    # 导出
    exporter = WorkOrderExporter()
    export_format = ExportFormat.CSV if format == 'csv' else ExportFormat.XLSX
    
    file_bytes, content_type = exporter.export_single(wo_dict, format=export_format)
    
    from fastapi.responses import StreamingResponse
    import io
    
    filename = f"workorder_{wo.order_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format == 'csv':
        filename += ".csv"
        media_type = "text/csv; charset=utf-8-sig"
    else:
        filename += ".xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


@router.post("/", summary="创建工单")
async def create_workorder(
    workorder: WorkOrderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建新的工单
    自动生成工单编号
    """
    core = _build_workorder_core(db)
    
    # 创建工单
    wo = core.create(
        title=workorder.title,
        order_type=_map_order_type(workorder.order_type),
        creator=current_user.username,
        description=workorder.description,
        priority=_map_priority(workorder.priority),
        device_id=workorder.device_id,
        device_name=workorder.device_name,
        device_ip=workorder.device_ip,
        assignee=workorder.assignee,
        expected_end=workorder.expected_end,
        impact=workorder.impact,
        tags=workorder.tags.split(',') if workorder.tags else None,
        attachments=workorder.attachments,
    )
    
    return _workorder_to_dict(wo)


# ============== 工单辅助接口（必须在 /{workorder_id} 之前定义）==============

@router.get("/categories", summary="获取工单分类列表")
async def get_workorder_categories(
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取工单分类列表"""
    return {
        "items": [
            {"id": 1, "name": "故障处理", "code": "fault", "count": 0},
            {"id": 2, "name": "变更申请", "code": "change", "count": 0},
            {"id": 3, "name": "数据处理", "code": "data", "count": 0},
            {"id": 4, "name": "权限申请", "code": "permission", "count": 0},
            {"id": 5, "name": "其他", "code": "other", "count": 0},
        ]
    }


@router.get("/priorities", summary="获取工单优先级列表")
async def get_workorder_priorities(
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取工单优先级列表"""
    return {
        "items": [
            {"id": 1, "name": "P1 - 紧急", "code": "P1", "level": 1, "color": "red"},
            {"id": 2, "name": "P2 - 高", "code": "P2", "level": 2, "color": "orange"},
            {"id": 3, "name": "P3 - 中", "code": "P3", "level": 3, "color": "blue"},
            {"id": 4, "name": "P4 - 低", "code": "P4", "level": 4, "color": "green"},
        ]
    }


@router.get("/stats/summary", summary="获取工单统计摘要")
async def get_workorder_stats(
    start_date: Optional[datetime] = Query(None, description="统计开始日期"),
    end_date: Optional[datetime] = Query(None, description="统计结束日期"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工单统计摘要"""
    core = _build_workorder_core(db)
    
    # 统计各状态工单数量
    workorders, total = core.list(page=1, page_size=10000)
    
    stats = {
        'total': total,
        'pending': 0,
        'processing': 0,
        'resolved': 0,
        'closed': 0,
        'by_priority': {'P1': 0, 'P2': 0, 'P3': 0, 'P4': 0},
        'by_type': {'fault': 0, 'change': 0, 'inspection': 0, 'security': 0, 'demand': 0, 'question': 0, 'other': 0},
    }
    
    for wo in workorders:
        if wo.status == WorkOrderStatus.PENDING:
            stats['pending'] += 1
        elif wo.status == WorkOrderStatus.PROCESSING:
            stats['processing'] += 1
        elif wo.status == WorkOrderStatus.RESOLVED:
            stats['resolved'] += 1
        elif wo.status == WorkOrderStatus.CLOSED:
            stats['closed'] += 1
            
        if wo.priority:
            stats['by_priority'][wo.priority.value] = stats['by_priority'].get(wo.priority.value, 0) + 1
        
        if wo.order_type:
            stats['by_type'][wo.order_type.value] = stats['by_type'].get(wo.order_type.value, 0) + 1
    
    return stats


@router.get("/stats/trend", summary="获取工单趋势")
async def get_workorder_trend(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工单趋势数据"""
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    core = _build_workorder_core(db)
    workorders, _ = core.list(start_time=start_date, end_time=end_date, page=1, page_size=10000)
    
    # 按日期分组
    dates_set = set()
    created_dict = {}
    resolved_dict = {}
    
    for wo in workorders:
        if wo.created_at:
            date_str = wo.created_at.strftime('%Y-%m-%d')
            dates_set.add(date_str)
            created_dict[date_str] = created_dict.get(date_str, 0) + 1
        
        if wo.status == WorkOrderStatus.RESOLVED and wo.updated_at:
            date_str = wo.updated_at.strftime('%Y-%m-%d')
            dates_set.add(date_str)
            resolved_dict[date_str] = resolved_dict.get(date_str, 0) + 1
        elif wo.status == WorkOrderStatus.CLOSED and wo.updated_at:
            date_str = wo.updated_at.strftime('%Y-%m-%d')
            dates_set.add(date_str)
            resolved_dict[date_str] = resolved_dict.get(date_str, 0) + 1
    
    dates = sorted(list(dates_set))
    created = [created_dict.get(d, 0) for d in dates]
    resolved = [resolved_dict.get(d, 0) for d in dates]
    
    return {
        "dates": dates,
        "created": created,
        "resolved": resolved,
    }


# ============== 工单详情接口 ==============

@router.get("/{workorder_id}", summary="获取工单详情")
async def get_workorder(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工单的详细信息"""
    core = _build_workorder_core(db)
    wo = core.get_by_id(workorder_id)
    
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    return _workorder_to_dict(wo)


@router.put("/{workorder_id}/draft", summary="保存工单草稿")
async def save_workorder_draft(
    workorder_id: int,
    draft: WorkOrderDraftSave,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    保存工单草稿(WKO-008)
    
    - 不更新updated_at
    - 不记录操作历史
    - 状态保持draft
    - 只更新: title, description, priority, draft_data, draft_saved_at
    """
    core = _build_workorder_core(db)
    
    # 获取工单
    wo = core.get_by_id(workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    # 草稿保存只更新指定字段
    if draft.title is not None:
        wo.title = draft.title
    if draft.description is not None:
        wo.description = draft.description
    if draft.priority is not None:
        wo.priority = _map_priority(draft.priority)
    
    # 构建草稿数据快照
    draft_data = {
        'order_type': draft.order_type or (wo.order_type.value if wo.order_type else None),
        'title': draft.title if draft.title is not None else wo.title,
        'description': draft.description if draft.description is not None else wo.description,
        'priority': draft.priority if draft.priority is not None else (wo.priority.value if wo.priority else 'P3'),
        'device_id': draft.device_id if draft.device_id is not None else wo.device_id,
        'device_name': draft.device_name if draft.device_name is not None else wo.device_name,
        'device_ip': draft.device_ip if draft.device_ip is not None else wo.device_ip,
        'assignee': draft.assignee if draft.assignee is not None else wo.assignee,
        'expected_end': draft.expected_end.isoformat() if draft.expected_end else (wo.expected_end.isoformat() if wo.expected_end else None),
        'impact': draft.impact if draft.impact is not None else wo.impact,
        'tags': draft.tags if draft.tags is not None else (wo.tags.split(',') if wo.tags else []),
        'attachments': draft.attachments if draft.attachments is not None else [],
    }
    
    wo.draft_data = draft_data
    wo.draft_saved_at = datetime.now()
    
    # 注意：不更新updated_at，不记录操作历史
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="草稿保存失败")
    
    return {
        "code": 0,
        "message": "草稿保存成功",
        "data": _workorder_to_dict(wo)
    }


@router.put("/{workorder_id}", summary="更新工单")
async def update_workorder(
    workorder_id: int,
    workorder: WorkOrderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新工单信息"""
    core = _build_workorder_core(db)
    
    # 构建更新数据
    update_data = {}
    if workorder.title is not None:
        update_data['title'] = workorder.title
    if workorder.description is not None:
        update_data['description'] = workorder.description
    if workorder.priority is not None:
        update_data['priority'] = _map_priority(workorder.priority)
    if workorder.status is not None:
        update_data['status'] = _map_status(workorder.status)
    if workorder.assignee is not None:
        update_data['assignee'] = workorder.assignee
    if workorder.expected_end is not None:
        update_data['expected_end'] = workorder.expected_end
    if workorder.tags is not None:
        update_data['tags'] = workorder.tags
    if workorder.resolution is not None:
        update_data['resolution'] = workorder.resolution
    if workorder.root_cause is not None:
        update_data['root_cause'] = workorder.root_cause
    if workorder.improvement is not None:
        update_data['improvement'] = workorder.improvement
    
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    
    success = core.update(workorder_id, **update_data)
    
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    return {"status": "success", "message": "工单更新成功"}


@router.delete("/{workorder_id}", summary="删除工单")
async def delete_workorder(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除工单（软删除）
    仅管理员或创建人可以删除
    """
    core = _build_workorder_core(db)
    
    # 获取工单检查权限
    wo = core.get_by_id(workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    # 只有管理员或创建人可以删除
    if not current_user.is_admin() and wo.creator != current_user.username:
        raise HTTPException(status_code=403, detail="无权限删除此工单")
    
    success = core.delete(workorder_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    return {"status": "success", "message": "工单删除成功"}


# ============== 工单流程接口 ==============

@router.get("/{workorder_id}/flows", summary="获取工单流程历史")
async def get_workorder_flows(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工单的处理流程历史"""
    flows = db.query(WorkOrderFlow).filter(
        WorkOrderFlow.work_order_id == workorder_id
    ).order_by(WorkOrderFlow.created_at.asc()).all()
    
    return {
        "items": [
            {
                "id": f.id,
                "step_name": f.step_name,
                "action": f.action,
                "from_status": f.from_status,
                "to_status": f.to_status,
                "operator": f.operator,
                "comment": f.comment,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in flows
        ]
    }


@router.post("/{workorder_id}/flows", summary="添加工单流程记录")
async def create_workorder_flow(
    workorder_id: int,
    flow: WorkOrderFlowCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    添加工单流程记录
    包括状态变更、审批、操作等
    """
    # 验证工单存在
    core = _build_workorder_core(db)
    wo = core.get_by_id(workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    # 映射action到状态
    action_to_status = {
        'assign': WorkOrderStatus.PROCESSING,
        'approve': WorkOrderStatus.APPROVED,
        'reject': WorkOrderStatus.REJECTED,
        'resolve': WorkOrderStatus.RESOLVED,
        'close': WorkOrderStatus.CLOSED,
        'cancel': WorkOrderStatus.CANCELLED,
    }
    
    new_status = action_to_status.get(flow.action, flow.to_status)
    
    # 创建流程记录
    wo_flow = WorkOrderFlow(
        work_order_id=workorder_id,
        step_name=_get_step_name(flow.action),
        action=flow.action,
        from_status=wo.status.value if wo.status else None,
        to_status=new_status.value if isinstance(new_status, WorkOrderStatus) else new_status,
        operator=current_user.username,
        comment=flow.comment,
    )
    
    db.add(wo_flow)
    
    # 更新工单状态
    if new_status:
        wo.status = new_status if isinstance(new_status, WorkOrderStatus) else _map_status(new_status)
    
    db.commit()
    
    return {
        "id": wo_flow.id,
        "workorder_id": workorder_id,
        "action": flow.action,
        "operator": current_user.username,
        "created_at": wo_flow.created_at.isoformat() if wo_flow.created_at else None,
    }


def _get_step_name(action: str) -> str:
    """获取步骤名称"""
    names = {
        'create': '创建工单',
        'assign': '分配处理人',
        'approve': '审批通过',
        'reject': '审批拒绝',
        'resolve': '解决工单',
        'close': '关闭工单',
        'cancel': '取消工单',
    }
    return names.get(action, action)


# ============== AI分析接口 ==============

@router.post("/analyze/root-cause", summary="AI根因分析")
async def analyze_root_cause(
    title: str = Query(..., description="工单标题"),
    description: Optional[str] = Query(None, description="工单描述"),
    device_info: Optional[str] = Query(None, description="设备信息(JSON)"),
    alert_info: Optional[str] = Query(None, description="告警信息(JSON)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    AI根因分析
    根据工单信息分析并返回可能的根本原因
    """
    from modules.business.workorder.root_cause import RootCauseAnalyzer
    
    analyzer = RootCauseAnalyzer()
    result = analyzer.analyze(
        title=title,
        description=description or "",
        device_info=device_info,
        alert_info=alert_info
    )
    
    return result.to_dict()


@router.post("/analyze/remediation", summary="AI修复建议")
async def suggest_remediation(
    title: str = Query(..., description="工单标题"),
    description: Optional[str] = Query(None, description="工单描述"),
    root_cause: Optional[str] = Query(None, description="根本原因"),
    category: Optional[str] = Query(None, description="原因分类"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    AI修复建议
    根据工单信息和根因分析返回修复建议
    """
    from modules.business.workorder.remediation import RemediationAdvisor
    
    advisor = RemediationAdvisor()
    result = advisor.suggest(
        title=title,
        description=description or "",
        root_cause=root_cause,
        category=category
    )
    
    return result.to_dict()


# ============== 工单草稿接口 ==============

class WorkOrderDraftResponse(BaseModel):
    """工单草稿响应"""
    draft_id: str
    user_id: str
    username: str
    order_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: str
    status: str
    created_at: str
    updated_at: str


@router.post("/draft/save", summary="保存工单草稿")
async def save_draft(
    draft: WorkOrderDraftSave,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    保存工单草稿
    支持手动保存和自动保存
    """
    from modules.business.workorder.workorder_draft import WorkOrderDraftManager
    
    draft_manager = WorkOrderDraftManager()
    
    draft_data = draft.dict(exclude_none=True) if draft else {}
    if draft_data.get('is_auto_save'):
        # Auto-save doesn't include certain fields
        draft_data.pop('is_auto_save', None)
    
    draft_id, saved_draft = draft_manager.save_draft(
        user_id=str(current_user.user_id),
        username=current_user.username,
        draft_id=draft.draft_id,
        draft_data=draft_data,
        is_auto_save=draft.is_auto_save
    )
    
    return {
        "status": "success",
        "draft_id": draft_id,
        "message": "草稿保存成功" if not draft.is_auto_save else "自动保存成功",
        "is_auto_save": draft.is_auto_save
    }


@router.get("/draft/list", summary="获取草稿列表")
async def list_drafts(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取当前用户的草稿列表
    """
    from modules.business.workorder.workorder_draft import WorkOrderDraftManager
    
    draft_manager = WorkOrderDraftManager()
    drafts = draft_manager.list_drafts(str(current_user.user_id))
    
    return {
        "items": [d.to_dict() for d in drafts],
        "total": len(drafts)
    }


@router.get("/draft/{draft_id}", summary="获取草稿详情")
async def get_draft(
    draft_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取指定草稿的详细信息
    """
    from modules.business.workorder.workorder_draft import WorkOrderDraftManager
    
    draft_manager = WorkOrderDraftManager()
    draft = draft_manager.get_draft(str(current_user.user_id), draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    return draft.to_dict()


@router.delete("/draft/{draft_id}", summary="删除草稿")
async def delete_draft(
    draft_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    删除指定的草稿
    """
    from modules.business.workorder.workorder_draft import WorkOrderDraftManager
    
    draft_manager = WorkOrderDraftManager()
    success = draft_manager.delete_draft(str(current_user.user_id), draft_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    return {"status": "success", "message": "草稿已删除"}


# ============== SLA管理接口 (WKO-021/022) ==============

@router.get("/{workorder_id}/sla", summary="获取工单SLA状态")
async def get_workorder_sla_status(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取工单的SLA状态(WKO-021)
    
    返回:
    - remaining_seconds: 剩余秒数(负数表示已超时)
    - deadline: 截止时间
    - sla_level: SLA级别(P1-P4)
    - breach_warning: 是否警告
    - is_breached: 是否已超时
    - escalation_level: 当前升级级别(0-4)
    """
    from modules.business.workorder.sla_manager import SLAManager
    
    # 构建SLAManager
    sla_manager = SLAManager(db_session=db)
    
    # 获取工单信息验证存在
    core = _build_workorder_core(db)
    wo = core.get_by_id(workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    # 计算SLA状态
    status = sla_manager.compute_sla_status(workorder_id)
    
    return {"code": 0, "data": status}


@router.post("/{workorder_id}/sla/refresh", summary="刷新SLA状态")
async def refresh_sla_status(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    重新计算SLA状态(WKO-021)
    
    重新计算工单的SLA状态并检查是否需要升级
    """
    from modules.business.workorder.sla_manager import SLAManager
    
    # 构建SLAManager
    sla_manager = SLAManager(db_session=db)
    
    # 获取工单信息验证存在
    core = _build_workorder_core(db)
    wo = core.get_by_id(workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    # 重新计算SLA状态
    status = sla_manager.compute_sla_status(workorder_id)
    
    # 检查并触发升级
    escalations = sla_manager.check_escalation(workorder_id)
    
    return {
        "code": 0,
        "data": {
            "sla_status": status,
            "escalations": escalations
        }
    }


@router.get("/{workorder_id}/sla/history", summary="获取SLA升级历史")
async def get_sla_escalation_history(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取工单的SLA升级历史记录
    """
    from modules.business.workorder.sla_manager import SLAManager
    
    sla_manager = SLAManager(db_session=db)
    
    # 验证工单存在
    core = _build_workorder_core(db)
    wo = core.get_by_id(workorder_id)
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    history = sla_manager.get_escalation_history(workorder_id)
    
    return {"code": 0, "data": history}


@router.post("/{workorder_id}/sla/timer/start", summary="启动SLA计时器")
async def start_sla_timer(
    workorder_id: int,
    sla_type: str = Query("response", description="SLA类型: response/resolve"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    启动SLA计时器(WKO-021)
    
    为工单启动响应或解决SLA计时
    """
    from modules.business.workorder.sla_manager import SLAManager
    
    core = _build_workorder_core(db)
    wo = core.get_by_id(workorder_id)
    
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    sla_manager = SLAManager(db_session=db)
    timer_info = sla_manager.start_sla_timer(
        workorder_id=workorder_id,
        priority=wo.priority.value if wo.priority else 'P3',
        sla_type=sla_type
    )
    
    return {"code": 0, "data": timer_info}


# ============== 旧的SLA接口(兼容) ==============

@router.get("/sla/{workorder_id}", summary="[兼容]获取SLA状态")
async def get_sla_status_old(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    [兼容接口]获取工单的SLA状态
    """
    from modules.business.workorder.sla_manager import SLAManager
    
    sla_manager = SLAManager(db_session=db)
    core = _build_workorder_core(db)
    wo = core.get_by_id(workorder_id)
    
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    status = sla_manager.compute_sla_status(workorder_id)
    
    return {
        "workorder_id": workorder_id,
        "priority": wo.priority.value if wo.priority else 'P3',
        "response": status.get('response_timer'),
        "resolve": status.get('resolve_timer')
    }


@router.get("/sla/summary", summary="[兼容]获取SLA汇总")
async def get_sla_summary_old(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    [兼容接口]获取SLA状态汇总
    """
    from modules.business.workorder.workorder_draft import SLATracker
    
    sla_tracker = SLATracker()
    summary = sla_tracker.get_sla_summary()
    
    return summary


@router.post("/sla/{workorder_id}/start", summary="[兼容]启动SLA计时")
async def start_sla_timer_old(
    workorder_id: int,
    sla_type: str = Query("response", description="SLA类型: response/resolve"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    [兼容接口]启动SLA计时器
    """
    from modules.business.workorder.workorder_draft import SLATracker
    
    core = _build_workorder_core(db)
    wo = core.get_by_id(workorder_id)
    
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    sla_tracker = SLATracker()
    timer_info = sla_tracker.start_sla_timer(
        workorder_id=workorder_id,
        priority=wo.priority.value if wo.priority else 'P3',
        sla_type=sla_type
    )
    
    return {"status": "success", "timer": timer_info}


# ============== 工单导出接口 ==============

@router.get("/export", summary="导出工单")
async def export_workorders(
    status: Optional[str] = Query(None, description="状态过滤"),
    order_type: Optional[str] = Query(None, description="工单类型"),
    priority: Optional[str] = Query(None, description="优先级"),
    start_date: Optional[datetime] = Query(None, description="创建时间开始"),
    end_date: Optional[datetime] = Query(None, description="创建时间结束"),
    format: Optional[str] = Query("xlsx", description="导出格式: xlsx, csv"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    导出工单列表到Excel或CSV
    """
    from fastapi.responses import Response
    from modules.business.workorder.workorder_export import WorkOrderExporter, ExportFormat
    
    # Query work orders
    core = _build_workorder_core(db)
    
    status_enum = _map_status(status) if status else None
    type_enum = _map_order_type(order_type) if order_type else None
    priority_enum = _map_priority(priority) if priority else None
    
    workorders, total = core.list(
        status=status_enum,
        order_type=type_enum,
        priority=priority_enum,
        start_time=start_date,
        end_time=end_date,
        page=1,
        page_size=10000
    )
    
    # Convert to dict format
    wo_list = []
    for wo in workorders:
        wo_dict = {
            'order_no': wo.order_no,
            'order_type': wo.order_type.value if wo.order_type else None,
            'title': wo.title,
            'priority': wo.priority.value if wo.priority else None,
            'status': wo.status.value if wo.status else None,
            'creator': wo.creator,
            'assignee': wo.assignee,
            'device_name': wo.device_name,
            'device_ip': wo.device_ip,
            'created_at': wo.created_at,
            'updated_at': wo.updated_at,
            'expected_end': wo.expected_end,
            'actual_end': wo.actual_end,
            'sla_response_time': wo.sla_response_time,
            'sla_resolve_time': wo.sla_resolve_time,
            'description': wo.description,
            'resolution': wo.resolution,
            'root_cause': wo.root_cause,
            'improvement': wo.improvement,
            'impact': wo.impact,
            'tags': wo.tags.split(',') if wo.tags else [],
            'closed_at': wo.closed_at,
        }
        
        # Calculate SLA breach
        if wo.sla_resolve_time and wo.created_at:
            resolve_deadline = wo.created_at + timedelta(minutes=wo.sla_resolve_time)
            if wo.status not in [WorkOrderStatus.RESOLVED, WorkOrderStatus.CLOSED]:
                wo_dict['sla_breached'] = datetime.now() > resolve_deadline
            else:
                wo_dict['sla_breached'] = wo.sla_resolved_at and wo.sla_resolved_at > resolve_deadline
        else:
            wo_dict['sla_breached'] = False
        
        wo_list.append(wo_dict)
    
    # Export
    exporter = WorkOrderExporter()
    export_format = ExportFormat.CSV if format == 'csv' else ExportFormat.XLSX
    
    filename = f"workorders_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    file_bytes, content_type = exporter.export(wo_list, filename, export_format)
    
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}.{format}"
        }
    )


# ============== 工单操作接口 ==============

@router.post("/{workorder_id}/assign", summary="分配工单")
async def assign_workorder(
    workorder_id: int,
    assignee: str = Query(..., description="处理人"),
    comment: Optional[str] = Query(None, description="分配说明"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分配工单给指定处理人"""
    core = _build_workorder_core(db)
    success = core.assign(workorder_id, assignee, current_user.username, comment)
    
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    return {"status": "success", "message": f"工单已分配给 {assignee}"}


@router.post("/{workorder_id}/approve", summary="审批工单")
async def approve_workorder(
    workorder_id: int,
    approved: bool = Query(..., description="是否批准"),
    comment: Optional[str] = Query(None, description="审批意见"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """审批工单"""
    core = _build_workorder_core(db)
    
    if approved:
        success = core.approve(workorder_id, current_user.username, comment)
    else:
        success = core.reject(workorder_id, current_user.username, comment)
    
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    action = "审批通过" if approved else "审批拒绝"
    return {"status": "success", "message": f"工单{action}"}


@router.post("/{workorder_id}/resolve", summary="解决工单")
async def resolve_workorder(
    workorder_id: int,
    resolution: str = Query(..., description="解决方案"),
    root_cause: Optional[str] = Query(None, description="根本原因"),
    improvement: Optional[str] = Query(None, description="改进措施"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解决工单"""
    core = _build_workorder_core(db)
    success = core.resolve(workorder_id, resolution, current_user.username, root_cause, improvement)
    
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    return {"status": "success", "message": "工单已解决"}


@router.post("/{workorder_id}/close", summary="关闭工单")
async def close_workorder(
    workorder_id: int,
    satisfaction: Optional[int] = Query(None, ge=1, le=5, description="满意度评分"),
    feedback: Optional[str] = Query(None, description="反馈意见"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """关闭工单"""
    core = _build_workorder_core(db)
    success = core.close(workorder_id, current_user.username, satisfaction, feedback)
    
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    return {"status": "success", "message": "工单已关闭"}


@router.post("/{workorder_id}/cancel", summary="取消工单")
async def cancel_workorder(
    workorder_id: int,
    reason: str = Query(..., description="取消原因"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消工单"""
    core = _build_workorder_core(db)
    success = core.cancel(workorder_id, reason, current_user.username)
    
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    return {"status": "success", "message": "工单已取消"}
