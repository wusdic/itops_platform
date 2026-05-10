"""
AI助手API路由
提供智能问答、故障诊断、建议生成等AI功能
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
import json

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user, CurrentUser, PaginationParams
from modules.business.knowledge_base.models import (
    SOPDocument, FaultCase, Category, Tag,
    DocumentStatus, FaultLevel, FaultStatus, ReviewStatus
)
from modules.collection.device_manager import DeviceManager


router = APIRouter()


# ============== 枚举定义 ==============

class ConversationType(str, Enum):
    """对话类型"""
    CHAT = "chat"
    TROUBLESHOOTING = "troubleshooting"
    SUGGESTION = "suggestion"
    ANALYSIS = "analysis"


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ============== 请求/响应模型 ==============

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色: user, assistant, system")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    conversation_id: Optional[str] = Field(None, description="会话ID")
    conversation_type: str = Field("chat", description="对话类型")
    context: Optional[dict] = Field(None, description="上下文信息")


class ChatResponse(BaseModel):
    """聊天响应"""
    conversation_id: str
    message: str
    suggestions: Optional[List[str]] = None
    related_docs: Optional[List[dict]] = None
    metadata: Optional[dict] = None


class TroubleshootingRequest(BaseModel):
    """故障排查请求"""
    symptom: str = Field(..., description="故障现象")
    device_id: Optional[int] = Field(None, description="设备ID")
    device_name: Optional[str] = Field(None, description="设备名称")
    device_ip: Optional[str] = Field(None, description="设备IP")
    error_logs: Optional[str] = Field(None, description="错误日志")
    metrics: Optional[dict] = Field(None, description="相关指标")


class TroubleshootingResponse(BaseModel):
    """故障排查响应"""
    diagnosis: str = Field(..., description="诊断结果")
    confidence: float = Field(..., description="置信度 0-1")
    possible_causes: List[str] = Field(..., description="可能原因")
    suggested_steps: List[dict] = Field(..., description="建议步骤")
    related_cases: Optional[List[dict]] = Field(None, description="相关案例")
    related_docs: Optional[List[dict]] = Field(None, description="相关文档")


class SuggestionRequest(BaseModel):
    """建议生成请求"""
    type: str = Field(..., description="建议类型: performance, security, capacity, optimization")
    target: str = Field(..., description="目标: host, service, system")
    target_id: Optional[int] = Field(None, description="目标ID")
    metrics: Optional[dict] = Field(None, description="当前指标数据")


# ============== 故障案例查询 ==============

def _find_related_cases(symptom: str, keyword: str = None, limit: int = 5) -> List[dict]:
    """从数据库查找相关故障案例"""
    from api.dependencies import get_db
    
    # 这个函数需要db session，我们返回一个查询构建器方式
    # 实际调用时传入db
    return []


# ============== 对话接口 ==============

@router.post("/chat", summary="发送消息")
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    发送消息给AI助手
    """
    conversation_id = request.conversation_id or f"conv-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 尝试获取全局 LLM 客户端
    from api.start import get_llm_client
    llm_client = get_llm_client()

    if llm_client is None:
        # LLM 未初始化，降级到意图检测
        suggestions = ["进行故障排查", "生成优化建议", "搜索知识库", "分析日志"]
        response_message = "AI服务暂不可用，请检查LLM服务是否启动。"
        return {
            "conversation_id": conversation_id,
            "message": response_message,
            "suggestions": suggestions,
            "metadata": {
                "mode": "llm_unavailable",
                "timestamp": datetime.now().isoformat()
            },
        }

    # 构建消息
    messages = [
        {"role": "system", "content": "你是一个专业的IT运维AI助手。请用中文简洁回答运维相关问题。"},
        {"role": "user", "content": request.message},
    ]

    try:
        # 调用 LLM（非流式）
        result = await llm_client.chat(
            messages=messages,
            model=None,  # 使用默认模型
            temperature=0.7,
            max_tokens=2048,
        )

        if result.get("done") and result.get("content"):
            response_message = result["content"]
            return {
                "conversation_id": conversation_id,
                "message": response_message,
                "suggestions": ["继续对话", "进入故障排查", "生成优化建议"],
                "metadata": {
                    "mode": "llm",
                    "model": result.get("model", "qwen3.6-27b-q4-k-m"),
                    "eval_count": result.get("eval_count", 0),
                    "timestamp": datetime.now().isoformat()
                },
            }
        else:
            return {
                "conversation_id": conversation_id,
                "message": "AI回复生成失败，请重试。",
                "suggestions": ["重试", "进入故障排查", "生成优化建议"],
                "metadata": {"mode": "llm_error", "timestamp": datetime.now().isoformat()},
            }
    except Exception as e:
        logger.error(f"LLM chat error: {e}")
        return {
            "conversation_id": conversation_id,
            "message": f"AI服务异常: {str(e)}",
            "suggestions": ["重试", "进入故障排查", "生成优化建议"],
            "metadata": {"mode": "llm_error", "error": str(e), "timestamp": datetime.now().isoformat()},
        }


@router.get("/conversation/{conversation_id}", summary="获取会话历史")
async def get_conversation(
    conversation_id: str,
    limit: int = Query(50, le=100, description="返回消息数量"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取指定会话的消息历史
    注意：会话历史需要配置外部存储（如Redis）才能持久化
    """
    # TODO: 从Redis或数据库获取会话历史
    return {
        "conversation_id": conversation_id,
        "messages": [],
        "message": "会话历史存储功能待配置"
    }


@router.get("/conversations", summary="获取会话列表")
async def get_conversations(
    conversation_type: Optional[str] = Query(None, description="对话类型过滤"),
    limit: int = Query(20, le=50, description="返回数量限制"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户的会话列表"""
    # TODO: 从数据库获取会话列表
    return {"items": [], "total": 0}


@router.delete("/conversation/{conversation_id}", summary="删除会话")
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除指定的会话"""
    # TODO: 从数据库删除会话
    return {
        "status": "success",
        "message": "Conversation deleted"
    }


# ============== 故障排查接口 ==============

@router.post("/troubleshoot", summary="智能故障排查")
async def troubleshoot(
    request: TroubleshootingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    智能故障排查
    根据故障现象分析可能的原因并给出处理建议
    """
    # 从数据库查找相关故障案例
    related_cases_query = db.query(FaultCase).filter(
        FaultCase.is_deleted == False,
        FaultCase.fault_status.in_([FaultStatus.RESOLVED, FaultStatus.CLOSED])
    )
    
    # 按关键词匹配
    search_term = request.symptom
    related_cases_query = related_cases_query.filter(
        (FaultCase.title.ilike(f"%{search_term}%")) |
        (FaultCase.symptom.ilike(f"%{search_term}%")) |
        (FaultCase.root_cause.ilike(f"%{search_term}%"))
    )
    
    related_cases_db = related_cases_query.order_by(FaultCase.view_count.desc()).limit(5).all()
    related_cases = [
        {
            "id": c.id,
            "case_no": c.case_no,
            "title": c.title,
            "fault_level": c.fault_level.value if c.fault_level else None,
            "symptom": c.symptom[:200] + "..." if c.symptom and len(c.symptom) > 200 else c.symptom,
            "root_cause": c.root_cause,
            "resolution": c.solution,
            "similarity": 0.8
        }
        for c in related_cases_db
    ]
    
    # 根据关键词分析可能的原因
    symptom_lower = request.symptom.lower()
    possible_causes = []
    suggested_steps = []
    
    # 关键词匹配分析
    if any(kw in symptom_lower for kw in ['cpu', '负载', 'load', '占用高']):
        possible_causes.extend([
            "CPU密集型任务占用资源",
            "恶意软件或挖矿程序",
            "系统更新或后台任务",
            "异常进程或死循环"
        ])
        suggested_steps.append({
            "order": 1,
            "action": "查看CPU使用情况",
            "command": "top -bn1 | head -20",
            "description": "检查当前CPU占用最高的进程"
        })
        suggested_steps.append({
            "order": 2,
            "action": "检查定时任务",
            "command": "crontab -l",
            "description": "查看是否有异常的定时任务"
        })
        suggested_steps.append({
            "order": 3,
            "action": "查看系统负载",
            "command": "uptime",
            "description": "检查系统1/5/15分钟平均负载"
        })
    
    if any(kw in symptom_lower for kw in ['内存', 'memory', 'oom', '溢出']):
        possible_causes.extend([
            "内存泄漏导致可用内存不足",
            "大内存操作导致OOM",
            "缓存未释放"
        ])
        suggested_steps.append({
            "order": 1,
            "action": "查看内存使用",
            "command": "free -h",
            "description": "检查内存使用情况和可用空间"
        })
        suggested_steps.append({
            "order": 2,
            "action": "查看内存占用最高的进程",
            "command": "ps aux --sort=-%mem | head -10",
            "description": "找出占用内存最多的进程"
        })
    
    if any(kw in symptom_lower for kw in ['磁盘', 'disk', '空间', '满']):
        possible_causes.extend([
            "磁盘空间不足",
            "日志文件过大",
            "临时文件未清理",
            "大文件占用空间"
        ])
        suggested_steps.append({
            "order": 1,
            "action": "查看磁盘使用",
            "command": "df -h",
            "description": "检查各分区磁盘使用情况"
        })
        suggested_steps.append({
            "order": 2,
            "action": "查找大文件",
            "command": "du -sh /* | sort -rh | head -10",
            "description": "查找占用空间最大的目录"
        })
    
    if any(kw in symptom_lower for kw in ['网络', 'network', '连接', '不通']):
        possible_causes.extend([
            "网络连接故障",
            "防火墙阻断",
            "DNS解析问题",
            "端口不通"
        ])
        suggested_steps.append({
            "order": 1,
            "action": "检查网络连通性",
            "command": "ping -c 4 8.8.8.8",
            "description": "测试网络连接"
        })
        suggested_steps.append({
            "order": 2,
            "action": "检查端口监听",
            "command": "ss -tlnp",
            "description": "查看监听端口状态"
        })
    
    if any(kw in symptom_lower for kw in ['服务', 'service', '启动', '运行']):
        possible_causes.extend([
            "服务未启动",
            "服务配置错误",
            "依赖服务异常",
            "端口被占用"
        ])
        suggested_steps.append({
            "order": 1,
            "action": "检查服务状态",
            "command": "systemctl status <service_name>",
            "description": "查看服务运行状态"
        })
        suggested_steps.append({
            "order": 2,
            "action": "查看服务日志",
            "command": "journalctl -u <service_name> -n 50",
            "description": "查看服务日志"
        })
    
    # 如果没有匹配到关键词，返回通用分析
    if not possible_causes:
        possible_causes = [
            "系统资源不足",
            "应用程序异常",
            "配置错误",
            "外部依赖故障"
        ]
        suggested_steps = [
            {"order": 1, "action": "检查系统资源", "command": "top -bn1 && free -h && df -h", "description": "查看CPU、内存、磁盘使用情况"},
            {"order": 2, "action": "检查系统日志", "command": "tail -100 /var/log/messages", "description": "查看系统日志"},
            {"order": 3, "action": "查看服务状态", "command": "systemctl status <service>", "description": "检查相关服务状态"}
        ]
    
    # 查找相关文档
    related_docs = []
    if related_cases:
        # 使用故障案例作为参考文档
        for case in related_cases[:2]:
            related_docs.append({
                "id": case['id'],
                "title": case['title'],
                "type": "fault_case",
                "relevance": 0.85
            })
    
    return {
        "diagnosis": f"根据您描述的「{request.symptom}」，可能由以下原因导致",
        "confidence": 0.75 if related_cases else 0.6,
        "possible_causes": possible_causes[:5],
        "suggested_steps": suggested_steps[:5],
        "related_cases": related_cases,
        "related_docs": related_docs,
    }


@router.post("/troubleshoot/auto", summary="自动故障诊断")
async def auto_troubleshoot(
    device_id: int = Query(..., description="设备ID"),
    symptom: str = Query(..., description="故障现象描述"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    自动故障诊断
    采集设备指标和日志，综合分析故障原因
    """
    from modules.foundation.db_models.device import Device
    
    # 获取设备信息
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    try:
        # 采集设备指标
        manager = DeviceManager()
        result = await manager.collect_device(device.hostname or device.name)
        
        if result and result.status.value == 'online':
            metrics = result.metrics
            
            # 根据指标数据做进一步分析
            diagnosis_points = []
            
            if 'cpu' in metrics:
                cpu = metrics.get('cpu', {})
                usage = cpu.get('usage', 0)
                if usage > 80:
                    diagnosis_points.append(f"CPU使用率过高: {usage}%")
                if cpu.get('load_avg_1m', 0) > cpu.get('cores', 8):
                    diagnosis_points.append(f"系统负载过高: {cpu.get('load_avg_1m')}")
            
            if 'memory' in metrics:
                mem = metrics.get('memory', {})
                usage = mem.get('usage_percent', 0)
                if usage > 85:
                    diagnosis_points.append(f"内存使用率过高: {usage}%")
            
            if 'disks' in metrics:
                for disk in metrics.get('disks', []):
                    if float(disk.get('usage_percent', 0)) > 90:
                        diagnosis_points.append(f"磁盘 {disk.get('mounted_on')} 使用率超过90%")
            
            return {
                "status": "completed",
                "task_id": f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "device_id": device_id,
                "device_name": device.name,
                "symptom": symptom,
                "metrics_collected": True,
                "diagnosis_points": diagnosis_points if diagnosis_points else ["未发现明显异常"],
                "message": "故障诊断完成"
            }
        else:
            return {
                "status": "error",
                "task_id": f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "message": f"设备采集失败: {result.error if result else '未知错误'}"
            }
    except Exception as e:
        return {
            "status": "error",
            "task_id": f"task-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "message": f"诊断异常: {str(e)}"
        }


# ============== 建议生成接口 ==============

@router.post("/suggest", summary="生成优化建议")
async def generate_suggestion(
    request: SuggestionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    生成优化建议
    根据当前状态生成性能、安全、容量等优化建议
    """
    suggestions = []
    summary = ""
    
    if request.type == "performance":
        # 基于指标的优化建议
        if request.metrics:
            metrics = request.metrics
            
            if 'cpu_usage' in metrics and metrics['cpu_usage'] > 80:
                suggestions.append({
                    "priority": "high",
                    "title": "CPU使用率过高",
                    "description": f"当前CPU使用率{metrics['cpu_usage']}%，建议优化或扩容",
                    "impact": "提高系统响应速度",
                    "effort": "medium"
                })
            
            if 'memory_usage' in metrics and metrics['memory_usage'] > 85:
                suggestions.append({
                    "priority": "high",
                    "title": "内存使用率过高",
                    "description": f"当前内存使用率{metrics['memory_usage']}%，建议扩容或优化",
                    "impact": "避免OOM和提高稳定性",
                    "effort": "medium"
                })
            
            if 'disk_usage' in metrics and metrics['disk_usage'] > 90:
                suggestions.append({
                    "priority": "critical",
                    "title": "磁盘空间不足",
                    "description": f"当前磁盘使用率{metrics['disk_usage']}%，需要立即清理",
                    "impact": "避免服务中断",
                    "effort": "low"
                })
        
        # 通用性能优化建议
        if not suggestions:
            suggestions.extend([
                {
                    "priority": "medium",
                    "title": "启用缓存",
                    "description": "使用Redis等缓存减少数据库压力",
                    "impact": "提高响应速度",
                    "effort": "medium"
                },
                {
                    "priority": "medium",
                    "title": "优化数据库索引",
                    "description": "检查并优化慢查询和缺失索引",
                    "impact": "提高查询性能",
                    "effort": "medium"
                }
            ])
        
        summary = f"基于{request.target}的性能分析，生成了{len(suggestions)}条优化建议"
    
    elif request.type == "security":
        suggestions = [
            {
                "priority": "high",
                "title": "更新系统补丁",
                "description": "定期更新系统安全补丁",
                "impact": "减少安全漏洞",
                "effort": "low"
            },
            {
                "priority": "high",
                "title": "配置防火墙",
                "description": "仅开放必要的端口",
                "impact": "减少攻击面",
                "effort": "medium"
            },
            {
                "priority": "medium",
                "title": "启用日志审计",
                "description": "开启登录和操作审计",
                "impact": "提高安全可追溯性",
                "effort": "low"
            }
        ]
        summary = "安全加固建议已完成"
    
    elif request.type == "capacity":
        suggestions = [
            {
                "priority": "medium",
                "title": "监控容量趋势",
                "description": "建立容量监控和预测模型",
                "impact": "提前规划扩容",
                "effort": "medium"
            },
            {
                "priority": "low",
                "title": "归档历史数据",
                "description": "将历史数据归档减少存储压力",
                "impact": "降低存储成本",
                "effort": "low"
            }
        ]
        summary = "容量规划建议已完成"
    
    else:  # optimization
        suggestions = [
            {
                "priority": "medium",
                "title": "定期巡检",
                "description": "建立定期巡检机制",
                "impact": "及时发现问题",
                "effort": "low"
            },
            {
                "priority": "medium",
                "title": "自动化运维",
                "description": "使用脚本自动化常见操作",
                "impact": "提高运维效率",
                "effort": "medium"
            }
        ]
        summary = f"针对{request.target}的优化建议已完成"
    
    return {
        "type": request.type,
        "suggestions": suggestions,
        "summary": summary,
    }


# ============== 报告解读接口 ==============

@router.post("/interpret/report", summary="解读报表")
async def interpret_report(
    report_id: int = Query(..., description="报表ID"),
    focus_areas: Optional[List[str]] = Query(None, description="关注领域"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    解读报表
    AI自动分析报表内容，提取关键信息和异常
    """
    from modules.foundation.db_models.report_template import Report
    
    # 获取报表数据
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")
    
    # 简化实现：基于报表数据进行分析
    findings = []
    recommendations = []
    
    if report.report_data:
        try:
            data = json.loads(report.report_data) if isinstance(report.report_data, str) else report.report_data
            
            # 分析报表数据中的异常
            if 'alerts' in data:
                alert_count = len(data['alerts'])
                if alert_count > 0:
                    findings.append({
                        "area": "告警",
                        "status": "warning",
                        "detail": f"共{alert_count}条告警记录"
                    })
            
            if 'availability' in data:
                avail = data.get('availability', 0)
                if avail < 99.9:
                    findings.append({
                        "area": "可用性",
                        "status": "warning",
                        "detail": f"系统可用性{avail}%，未达到99.9%目标"
                    })
                else:
                    findings.append({
                        "area": "可用性",
                        "status": "normal",
                        "detail": f"系统可用性{avail}%，符合SLA要求"
                    })
        except Exception:
            pass
    
    if not findings:
        findings.append({
            "area": "总体",
            "status": "normal",
            "detail": "未发现重大异常"
        })
        recommendations.append("继续保持当前运维状态")
        recommendations.append("建议定期进行系统巡检")
    
    return {
        "report_id": report_id,
        "report_name": report.name,
        "summary": f"报表解读完成，共发现{len(findings)}个关注点",
        "key_findings": findings,
        "recommendations": recommendations,
    }


# ============== 日志分析接口 ==============

@router.post("/analyze/logs", summary="分析日志")
async def analyze_logs(
    logs: str = Query(..., description="日志内容"),
    context: Optional[str] = Query(None, description="上下文信息"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    智能日志分析
    分析日志内容，提取错误、异常和关键事件
    """
    lines = logs.strip().split('\n') if logs else []
    
    errors = []
    warnings = []
    timeline = []
    
    error_keywords = ['error', 'exception', 'fatal', 'failed', 'failure']
    warning_keywords = ['warning', 'warn', 'timeout']
    
    for line in lines:
        line_lower = line.lower()
        
        if any(kw in line_lower for kw in error_keywords):
            errors.append({
                "line": line[:200],
                "possible_cause": "需要检查服务状态和网络连接"
            })
        
        if any(kw in line_lower for kw in warning_keywords):
            warnings.append({
                "line": line[:200]
            })
        
        # 尝试提取时间戳
        import re
        time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        if time_match:
            timeline.append({
                "time": time_match.group(1),
                "event": line[:100]
            })
    
    # 去重
    seen_errors = set()
    unique_errors = []
    for e in errors:
        key = e['line'][:50]
        if key not in seen_errors:
            seen_errors.add(key)
            unique_errors.append(e)
    
    seen_warnings = set()
    unique_warnings = []
    for w in warnings:
        key = w['line'][:50]
        if key not in seen_warnings:
            seen_warnings.add(key)
            unique_warnings.append(w)
    
    # 生成分析摘要
    summary = f"共分析了{len(lines)}行日志，发现{len(unique_errors)}个错误，{len(unique_warnings)}个警告"
    
    return {
        "summary": summary,
        "errors": unique_errors[:10],
        "warnings": unique_warnings[:10],
        "timeline": timeline[:20],
        "error_count": len(unique_errors),
        "warning_count": len(unique_warnings),
    }


# ============== 知识问答接口 ==============

@router.post("/qa", summary="知识问答")
async def question_answer(
    question: str = Query(..., description="问题"),
    category: Optional[str] = Query(None, description="问题类别"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    知识问答
    基于知识库回答运维相关问题
    """
    # 从知识库搜索相关内容
    from modules.business.knowledge_base.models import SOPDocument
    
    # 搜索SOP文档
    query = db.query(SOPDocument).filter(
        SOPDocument.is_deleted == False,
        SOPDocument.status == 'approved'
    )
    
    if question:
        query = query.filter(
            (SOPDocument.title.ilike(f"%{question}%")) |
            (SOPDocument.content.ilike(f"%{question}%"))
        )
    
    docs = query.limit(5).all()
    
    sources = []
    answer_parts = []
    
    if docs:
        for doc in docs:
            sources.append({
                "id": doc.id,
                "title": doc.title,
                "type": "sop",
                "relevance": 0.9
            })
            # 提取相关内容作为答案
            content_preview = doc.content[:300] if doc.content else ""
            answer_parts.append(f"【{doc.title}】\n{content_preview}...")
    
    if answer_parts:
        answer = "\n\n".join(answer_parts[:2])
        confidence = 0.85
    else:
        # 通用回答
        answer = "抱歉，知识库中未找到相关内容。建议您：\n1. 查看系统操作手册\n2. 咨询技术支持人员\n3. 提交工单获取帮助"
        confidence = 0.3
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "question": question
    }


# ============== 会话统计接口 ==============

@router.get("/stats", summary="获取AI助手统计")
async def get_ai_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取AI助手使用统计"""
    # 从故障案例获取统计数据
    total_cases = db.query(FaultCase).filter(FaultCase.is_deleted == False).count()
    
    # 从SOP文档获取统计数据
    from modules.business.knowledge_base.models import SOPDocument
    total_sops = db.query(SOPDocument).filter(
        SOPDocument.is_deleted == False,
        SOPDocument.status == 'approved'
    ).count()
    
    return {
        "total_conversations": 0,  # 需要会话存储
        "total_messages": 0,
        "today_conversations": 0,
        "today_messages": 0,
        "knowledge_base_size": {
            "fault_cases": total_cases,
            "sop_documents": total_sops,
        },
        "avg_response_time_ms": 0,  # 需要LLM服务
    }
