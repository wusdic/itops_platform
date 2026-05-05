"""
工单管理API路由
提供工单创建、查询、审批、处理等接口
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from sqlalchemy.orm import Session

router = APIRouter()


# ============== 请求/响应模型 ==============

class WorkOrderCreate(BaseModel):
    """创建工单请求"""
    order_type: str = Field(..., description="工单类型: fault, change, inspection, security, demand, question")
    title: str = Field(..., max_length=256, description="工单标题")
    description: str = Field(None, description="工单描述")
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
    # TODO: 构建查询条件并查询数据库
    # from modules.foundation.db_models.workorder import WorkOrder
    # query = db.query(WorkOrder)
    # ...
    
    return {
        "items": [
            {
                "id": 1,
                "order_no": "WO-20240101-0001",
                "order_type": "fault",
                "priority": "P2",
                "title": "服务器无法连接",
                "status": "processing",
                "device_name": "server-01",
                "device_ip": "192.168.1.101",
                "creator": "zhangsan",
                "assignee": "lisi",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        ],
        "total": 1,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


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
    # 生成工单编号
    order_no = f"WO-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"

    # TODO: 保存到数据库
    # from modules.foundation.db_models.workorder import WorkOrder
    # db_workorder = WorkOrder(
    #     order_no=order_no,
    #     order_type=workorder.order_type,
    #     ...
    # )
    # db.add(db_workorder)
    # db.commit()

    return {
        "id": 1,
        "order_no": order_no,
        "order_type": workorder.order_type,
        "title": workorder.title,
        "status": "pending",
        "priority": workorder.priority,
        "creator": current_user.username,
        "created_at": datetime.now().isoformat(),
    }


# ============== 工单辅助接口（必须在 /{workorder_id} 之前定义）==============

@router.get("/categories", summary="获取工单分类列表")
async def get_workorder_categories(
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取工单分类列表"""
    return {
        "items": [
            {"id": 1, "name": "故障处理", "code": "fault", "count": 45},
            {"id": 2, "name": "变更申请", "code": "change", "count": 30},
            {"id": 3, "name": "数据处理", "code": "data", "count": 20},
            {"id": 4, "name": "权限申请", "code": "permission", "count": 15},
            {"id": 5, "name": "其他", "code": "other", "count": 10},
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
    # TODO: 从数据库统计工单数据

    return {
        "total": 100,
        "pending": 10,
        "processing": 20,
        "resolved": 60,
        "closed": 10,
        "by_priority": {
            "P1": 5,
            "P2": 15,
            "P3": 60,
            "P4": 20,
        },
        "by_type": {
            "fault": 40,
            "change": 30,
            "data": 20,
            "permission": 10,
        },
    }


@router.get("/stats/trend", summary="获取工单趋势")
async def get_workorder_trend(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工单趋势数据"""
    # TODO: 从数据库统计工单趋势
    return {
        "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "created": [10, 15, 8],
        "resolved": [8, 12, 10],
    }


# ============== 工单详情接口 ==============

@router.get("/{workorder_id}", summary="获取工单详情")
async def get_workorder(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工单的详细信息"""
    # TODO: 从数据库获取工单详情
    return {
        "id": workorder_id,
        "order_no": "WO-20240101-0001",
        "order_type": "fault",
        "priority": "P2",
        "title": "服务器无法连接",
        "description": "服务器192.168.1.101无法Ping通",
        "status": "processing",
        "device_id": 1,
        "device_name": "server-01",
        "device_ip": "192.168.1.101",
        "creator": "zhangsan",
        "assignee": "lisi",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@router.put("/{workorder_id}", summary="更新工单")
async def update_workorder(
    workorder_id: int,
    workorder: WorkOrderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新工单信息"""
    # TODO: 更新数据库中的工单
    
    return {
        "status": "success",
        "message": "WorkOrder updated successfully",
    }


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
    # TODO: 软删除工单
    return {
        "status": "success",
        "message": "WorkOrder deleted successfully",
    }


# ============== 工单流程接口 ==============

@router.get("/{workorder_id}/flows", summary="获取工单流程历史")
async def get_workorder_flows(
    workorder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工单的处理流程历史"""
    # TODO: 从数据库获取流程历史
    return {
        "items": [
            {
                "id": 1,
                "step_name": "创建工单",
                "action": "create",
                "from_status": None,
                "to_status": "pending",
                "operator": "zhangsan",
                "comment": None,
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": 2,
                "step_name": "分配处理人",
                "action": "assign",
                "from_status": "pending",
                "to_status": "processing",
                "operator": "admin",
                "comment": "分配给运维人员处理",
                "created_at": datetime.now().isoformat(),
            },
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
    # TODO: 保存流程记录到数据库
    
    return {
        "id": 3,
        "workorder_id": workorder_id,
        "action": flow.action,
        "operator": current_user.username,
        "created_at": datetime.now().isoformat(),
    }


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
    # TODO: 更新工单分配信息
    
    return {
        "status": "success",
        "message": f"WorkOrder assigned to {assignee}",
    }


@router.post("/{workorder_id}/approve", summary="审批工单")
async def approve_workorder(
    workorder_id: int,
    approved: bool = Query(..., description="是否批准"),
    comment: Optional[str] = Query(None, description="审批意见"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """审批工单"""
    # TODO: 更新工单审批状态
    
    action = "approved" if approved else "rejected"
    return {
        "status": "success",
        "message": f"WorkOrder {action}",
    }


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
    # TODO: 更新工单状态为已解决
    
    return {
        "status": "success",
        "message": "WorkOrder resolved",
    }


@router.post("/{workorder_id}/close", summary="关闭工单")
async def close_workorder(
    workorder_id: int,
    satisfaction: Optional[int] = Query(None, ge=1, le=5, description="满意度评分"),
    feedback: Optional[str] = Query(None, description="反馈意见"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """关闭工单"""
    # TODO: 更新工单状态为已关闭
    
    return {
        "status": "success",
        "message": "WorkOrder closed",
    }


@router.post("/{workorder_id}/cancel", summary="取消工单")
async def cancel_workorder(
    workorder_id: int,
    reason: str = Query(..., description="取消原因"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消工单"""
    # TODO: 更新工单状态为已取消
    
    return {
        "status": "success",
        "message": "WorkOrder cancelled",
    }


# 原有工单流程接口保持不变
@router.post("/{workorder_id}/flows", summary="添加工单流程记录")
async def add_workorder_flow(
    workorder_id: int,
    flow: WorkOrderFlowCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加工单流程记录"""
    return {
        "id": 1,
        "workorder_id": workorder_id,
        "action": flow.action,
        "operator": current_user.username,
        "created_at": datetime.now().isoformat(),
    }
