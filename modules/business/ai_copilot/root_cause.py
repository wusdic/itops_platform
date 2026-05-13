"""
BM-05 AI Copilot - Root Cause Analyzer
AI告警根因分析模块
"""

import logging
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class RootCauseResult:
    """根因分析结果"""
    alert_id: int
    success: bool
    root_cause: str = ""
    confidence: float = 0.0
    possible_causes: List[Dict] = field(default_factory=list)
    related_alerts: List[Dict] = field(default_factory=list)
    analysis_steps: List[Dict] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "success": self.success,
            "root_cause": self.root_cause,
            "confidence": self.confidence,
            "possible_causes": self.possible_causes,
            "related_alerts": self.related_alerts,
            "analysis_steps": self.analysis_steps,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
            "error": self.error
        }


class RootCauseAnalyzer:
    """
    AI告警根因分析器
    
    分析告警的根本原因，支持:
    - 基于时间序列的关联分析
    - 基于症状的推理分析
    - 基于历史案例的匹配
    - 基于知识库的问答
    """

    # 常见的根因模式和对应的分析规则
    ROOT_CAUSE_PATTERNS = {
        "cpu_high": {
            "symptoms": ["cpu", "负载", "load", "占用高", "usage"],
            "possible_causes": [
                {"cause": "CPU密集型任务", "probability": 0.3, "indicators": ["top", "ps aux"]},
                {"cause": "恶意软件/挖矿程序", "probability": 0.2, "indicators": ["malware", "crypto"]},
                {"cause": "系统更新/后台任务", "probability": 0.25, "indicators": ["update", "yum", "apt"]},
                {"cause": "异常进程/死循环", "probability": 0.25, "indicators": ["infinite loop", " runaway"]},
            ],
            "steps": [
                {"order": 1, "action": "查看CPU使用情况", "command": "top -bn1 | head -20"},
                {"order": 2, "action": "检查定时任务", "command": "crontab -l"},
                {"order": 3, "action": "查看系统负载", "command": "uptime"},
            ],
            "recommendations": [
                "检查是否有异常进程占用CPU",
                "查看定时任务是否正常",
                "考虑扩容或优化代码"
            ]
        },
        "memory_high": {
            "symptoms": ["内存", "memory", "oom", "溢出", "leak"],
            "possible_causes": [
                {"cause": "内存泄漏", "probability": 0.35, "indicators": ["leak", "valgrind"]},
                {"cause": "大内存操作导致OOM", "probability": 0.3, "indicators": ["oom", "kill"]},
                {"cause": "缓存未释放", "probability": 0.25, "indicators": ["cache", "buffer"]},
                {"cause": "进程数量过多", "probability": 0.1, "indicators": ["process count"]},
            ],
            "steps": [
                {"order": 1, "action": "查看内存使用", "command": "free -h"},
                {"order": 2, "action": "查看内存占用最高的进程", "command": "ps aux --sort=-%mem | head -10"},
                {"order": 3, "action": "检查OOM日志", "command": "dmesg | grep -i oom"},
            ],
            "recommendations": [
                "使用valgrind检测内存泄漏",
                "优化缓存管理",
                "考虑增加内存或限制进程资源"
            ]
        },
        "disk_full": {
            "symptoms": ["磁盘", "disk", "空间", "满", "inodes"],
            "possible_causes": [
                {"cause": "日志文件过大", "probability": 0.35, "indicators": ["log", "/var/log"]},
                {"cause": "临时文件未清理", "probability": 0.25, "indicators": ["tmp", "temp"]},
                {"cause": "大文件占用", "probability": 0.25, "indicators": ["du", "large file"]},
                {"cause": "数据目录膨胀", "probability": 0.15, "indicators": ["data", "database"]},
            ],
            "steps": [
                {"order": 1, "action": "查看磁盘使用", "command": "df -h"},
                {"order": 2, "action": "查找大文件", "command": "du -sh /* 2>/dev/null | sort -rh | head -10"},
                {"order": 3, "action": "检查日志目录", "command": "ls -lh /var/log"},
            ],
            "recommendations": [
                "清理过期日志文件",
                "删除临时文件",
                "考虑扩容磁盘"
            ]
        },
        "network_issue": {
            "symptoms": ["网络", "network", "连接", "不通", "timeout", "connection"],
            "possible_causes": [
                {"cause": "网络连接故障", "probability": 0.3, "indicators": ["ping", "network"]},
                {"cause": "防火墙阻断", "probability": 0.25, "indicators": ["firewall", "iptables"]},
                {"cause": "DNS解析问题", "probability": 0.2, "indicators": ["dns", "resolve"]},
                {"cause": "端口不通", "probability": 0.25, "indicators": ["port", "ss", "netstat"]},
            ],
            "steps": [
                {"order": 1, "action": "检查网络连通性", "command": "ping -c 4 8.8.8.8"},
                {"order": 2, "action": "检查端口监听", "command": "ss -tlnp"},
                {"order": 3, "action": "检查DNS解析", "command": "nslookup google.com"},
            ],
            "recommendations": [
                "检查网络配置和路由",
                "检查防火墙规则",
                "验证DNS配置"
            ]
        },
        "service_down": {
            "symptoms": ["服务", "service", "启动", "运行", "down", "unavailable"],
            "possible_causes": [
                {"cause": "服务未启动", "probability": 0.3, "indicators": ["systemctl status"]},
                {"cause": "服务配置错误", "probability": 0.3, "indicators": ["config", "error"]},
                {"cause": "依赖服务异常", "probability": 0.25, "indicators": ["dependency", "requirement"]},
                {"cause": "端口被占用", "probability": 0.15, "indicators": ["port", "bind"]},
            ],
            "steps": [
                {"order": 1, "action": "检查服务状态", "command": "systemctl status <service_name>"},
                {"order": 2, "action": "查看服务日志", "command": "journalctl -u <service_name> -n 50"},
                {"order": 3, "action": "检查端口占用", "command": "netstat -tlnp | grep <port>"},
            ],
            "recommendations": [
                "检查服务配置是否正确",
                "检查依赖服务状态",
                "查看服务启动日志"
            ]
        },
        "process_crash": {
            "symptoms": ["崩溃", "crash", "core dump", "segfault", "panic"],
            "possible_causes": [
                {"cause": "程序bug", "probability": 0.35, "indicators": ["bug", "exception"]},
                {"cause": "内存越界", "probability": 0.25, "indicators": ["segfault", "memory"]},
                {"cause": "资源耗尽", "probability": 0.2, "indicators": ["resource", "limit"]},
                {"cause": "外部依赖问题", "probability": 0.2, "indicators": ["dependency", "library"]},
            ],
            "steps": [
                {"order": 1, "action": "查看崩溃日志", "command": "dmesg | tail -100"},
                {"order": 2, "action": "检查core文件", "command": "ls -la /var/crash"},
                {"order": 3, "action": "分析堆栈信息", "command": "coredumpctl info"},
            ],
            "recommendations": [
                "分析core dump文件",
                "检查程序日志",
                "修复代码bug"
            ]
        }
    }

    def __init__(self, llm_client=None, rag_service=None):
        """
        初始化根因分析器
        
        Args:
            llm_client: LLM客户端(可选)
            rag_service: RAG服务(可选)
        """
        self.llm_client = llm_client
        self.rag_service = rag_service

    def _detect_pattern(self, alert_title: str, alert_message: str, metric_name: str = None) -> Optional[str]:
        """
        检测告警匹配的模式
        
        Args:
            alert_title: 告警标题
            alert_message: 告警消息
            metric_name: 指标名称
            
        Returns:
            匹配的模式key或None
        """
        combined_text = f"{alert_title} {alert_message} {metric_name or ''}".lower()
        
        for pattern_key, pattern_info in self.ROOT_CAUSE_PATTERNS.items():
            for symptom in pattern_info["symptoms"]:
                if symptom in combined_text:
                    return pattern_key
        
        return None

    def _analyze_with_pattern(self, pattern_key: str) -> Dict[str, Any]:
        """
        使用已知模式进行分析
        
        Args:
            pattern_key: 模式key
            
        Returns:
            分析结果
        """
        pattern = self.ROOT_CAUSE_PATTERNS.get(pattern_key, {})
        
        # 按概率排序可能的原因
        possible_causes = sorted(
            pattern.get("possible_causes", []),
            key=lambda x: x.get("probability", 0),
            reverse=True
        )
        
        return {
            "possible_causes": possible_causes[:5],
            "analysis_steps": pattern.get("steps", []),
            "recommendations": pattern.get("recommendations", []),
            "pattern_matched": pattern_key
        }

    def _analyze_with_llm(self, alert_data: Dict, related_history: List[Dict] = None) -> Dict[str, Any]:
        """
        使用LLM进行根因分析
        
        Args:
            alert_data: 告警数据
            related_history: 相关历史告警
            
        Returns:
            分析结果
        """
        if not self.llm_client:
            return {
                "llm_analysis": None,
                "error": "LLM client not available"
            }
        
        # 构建分析提示词
        prompt = self._build_analysis_prompt(alert_data, related_history)
        
        # 调用LLM分析 - 同步调用
        try:
            result = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的IT运维AI助手，擅长分析告警根因。请用中文简洁分析根因。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2048
            )
            
            if result.get("done") and result.get("content"):
                return {
                    "llm_analysis": result["content"],
                    "raw_response": result
                }
            else:
                return {
                    "llm_analysis": None,
                    "error": "LLM分析失败"
                }
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return {
                "llm_analysis": None,
                "error": str(e)
            }

    def _build_analysis_prompt(self, alert_data: Dict, related_history: List[Dict] = None) -> str:
        """构建分析提示词"""
        prompt_parts = [
            f"请分析以下告警的根本原因:",
            f"",
            f"告警标题: {alert_data.get('title', 'N/A')}",
            f"告警级别: {alert_data.get('level', 'N/A')}",
            f"告警消息: {alert_data.get('message', 'N/A')}",
            f"设备名称: {alert_data.get('device_name', 'N/A')}",
            f"设备IP: {alert_data.get('device_ip', 'N/A')}",
            f"指标名称: {alert_data.get('metric_name', 'N/A')}",
            f"指标值: {alert_data.get('metric_value', 'N/A')}",
            f"阈值: {alert_data.get('threshold', 'N/A')}",
        ]
        
        if related_history:
            prompt_parts.append("")
            prompt_parts.append("相关历史告警:")
            for i, hist in enumerate(related_history[:3], 1):
                prompt_parts.append(f"{i}. {hist.get('title', 'N/A')} - {hist.get('message', 'N/A')}")
        
        prompt_parts.append("")
        prompt_parts.append("请分析:")
        prompt_parts.append("1. 最可能的根本原因是什么?")
        prompt_parts.append("2. 支持这个结论的证据有哪些?")
        prompt_parts.append("3. 应该按什么步骤排查?")
        prompt_parts.append("4. 如何预防再次发生?")
        
        return "\n".join(prompt_parts)

    def _find_related_alerts(self, db: Session, alert_id: int, device_id: int = None, 
                             time_window_minutes: int = 60) -> List[Dict]:
        """
        查找相关的告警
        
        Args:
            db: 数据库会话
            alert_id: 当前告警ID
            device_id: 设备ID
            time_window_minutes: 时间窗口(分钟)
            
        Returns:
            相关告警列表
        """
        from datetime import timedelta
        from modules.foundation.db_models.alert import Alert
        
        # 计算时间窗口
        time_threshold = datetime.now() - timedelta(minutes=time_window_minutes)
        
        # 构建查询
        query = db.query(Alert).filter(
            Alert.id != alert_id,
            Alert.occurred_at >= time_threshold
        )
        
        # 如果有设备ID，优先查找同设备的告警
        if device_id:
            query = query.filter(Alert.device_id == device_id)
        
        # 按时间排序获取最近的告警
        related = query.order_by(Alert.occurred_at.desc()).limit(10).all()
        
        return [
            {
                "id": a.id,
                "title": a.title,
                "message": a.message,
                "level": a.level.value if a.level else None,
                "occurred_at": a.occurred_at.isoformat() if a.occurred_at else None,
                "same_device": a.device_id == device_id if device_id else False
            }
            for a in related
        ]

    def _find_similar_cases(self, db: Session, alert_title: str, alert_message: str = None) -> List[Dict]:
        """
        查找相似的历史案例
        
        Args:
            db: 数据库会话
            alert_title: 告警标题
            alert_message: 告警消息
            
        Returns:
            相似案例列表
        """
        from modules.business.knowledge_base.models import FaultCase
        
        # 构建搜索条件
        search_term = alert_title
        if alert_message and len(alert_message) > 20:
            # 如果消息较长，也加入搜索
            search_term = f"{alert_title} {alert_message[:100]}"
        
        # 搜索相似案例
        query = db.query(FaultCase).filter(
            FaultCase.is_deleted == False,
            FaultCase.fault_status.in_(["resolved", "closed"])
        )
        
        # 多字段模糊匹配
        query = query.filter(
            (FaultCase.title.ilike(f"%{search_term}%")) |
            (FaultCase.symptom.ilike(f"%{search_term}%")) |
            (FaultCase.root_cause.ilike(f"%{search_term}%"))
        )
        
        cases = query.order_by(FaultCase.view_count.desc()).limit(5).all()
        
        return [
            {
                "id": c.id,
                "case_no": c.case_no,
                "title": c.title,
                "symptom": c.symptom[:200] if c.symptom else None,
                "root_cause": c.root_cause,
                "solution": c.solution,
                "similarity": 0.8  # 简化计算
            }
            for c in cases
        ]

    async def analyze(self, alert_id: int, db: Session, include_llm: bool = True,
                      include_history: bool = True, include_cases: bool = True) -> RootCauseResult:
        """
        执行根因分析
        
        Args:
            alert_id: 告警ID
            db: 数据库会话
            include_llm: 是否使用LLM分析
            include_history: 是否包含关联告警
            include_cases: 是否包含相似案例
            
        Returns:
            RootCauseResult: 根因分析结果
        """
        result = RootCauseResult(alert_id=alert_id, success=False)
        start_time = datetime.now()
        
        try:
            # 1. 获取告警信息
            from modules.foundation.db_models.alert import Alert
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            
            if not alert:
                result.error = f"告警 {alert_id} 不存在"
                return result
            
            alert_data = alert.to_dict()
            result.metadata["alert_data"] = alert_data
            
            # 2. 检测匹配的模式
            pattern_key = self._detect_pattern(
                alert.title,
                alert.message,
                alert.metric_name
            )
            
            if pattern_key:
                pattern_result = self._analyze_with_pattern(pattern_key)
                result.possible_causes = pattern_result["possible_causes"]
                result.analysis_steps = pattern_result["analysis_steps"]
                result.recommendations = pattern_result["recommendations"]
                result.metadata["pattern_matched"] = pattern_result["pattern_matched"]
                result.confidence = 0.6
                result.root_cause = pattern_result["possible_causes"][0]["cause"] if pattern_result["possible_causes"] else "未知"
            
            # 3. 查找关联告警
            if include_history:
                related_alerts = self._find_related_alerts(
                    db, alert_id, alert.device_id, time_window_minutes=60
                )
                result.related_alerts = related_alerts
                result.evidence["related_alerts_count"] = len(related_alerts)
            
            # 4. 查找相似案例
            if include_cases:
                similar_cases = self._find_similar_cases(
                    db, alert.title, alert.message
                )
                result.evidence["similar_cases"] = similar_cases
                
                # 如果有相似案例且有根因，更新结果
                if similar_cases and similar_cases[0].get("root_cause") and result.confidence < 0.7:
                    result.metadata["similar_case_found"] = True
                    # 轻度参考，但不直接采用
                    result.metadata["case_reference"] = similar_cases[0].get("case_no")
            
            # 5. 使用LLM进行深度分析
            if include_llm and self.llm_client:
                llm_result = self._analyze_with_llm(alert_data, result.related_alerts[:3])
                if llm_result.get("llm_analysis"):
                    result.metadata["llm_analysis"] = llm_result["llm_analysis"]
                    result.confidence = max(result.confidence, 0.75)
            
            # 6. 生成最终结论
            if not result.root_cause and result.possible_causes:
                result.root_cause = result.possible_causes[0].get("cause", "未能确定根因")
            
            if not result.root_cause:
                result.root_cause = "需要进一步分析"
                result.metadata["needs_manual_review"] = True
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Root cause analysis error for alert {alert_id}: {e}")
            result.error = str(e)
            result.metadata["exception"] = True
        
        # 记录分析时间
        result.metadata["analysis_duration_ms"] = (datetime.now() - start_time).total_seconds() * 1000
        
        return result

    def analyze_sync(self, alert_id: int, db: Session, include_llm: bool = True,
                     include_history: bool = True, include_cases: bool = True) -> RootCauseResult:
        """
        同步版本的根因分析（用于非异步上下文）
        
        与async analyze方法相同，但为同步调用
        """
        # 对于同步版本，暂时跳过LLM调用（需要事件循环）
        return self.analyze(
            alert_id=alert_id,
            db=db,
            include_llm=False,  # 同步模式不支持LLM
            include_history=include_history,
            include_cases=include_cases
        )


# 全局实例管理
_root_cause_analyzer: Optional[RootCauseAnalyzer] = None


def get_root_cause_analyzer() -> RootCauseAnalyzer:
    """获取全局根因分析器实例"""
    global _root_cause_analyzer
    if _root_cause_analyzer is None:
        _root_cause_analyzer = RootCauseAnalyzer()
    return _root_cause_analyzer


def init_root_cause_analyzer(llm_client=None, rag_service=None) -> RootCauseAnalyzer:
    """初始化全局根因分析器"""
    global _root_cause_analyzer
    _root_cause_analyzer = RootCauseAnalyzer(
        llm_client=llm_client,
        rag_service=rag_service
    )
    return _root_cause_analyzer