"""
AI Copilot Remediation Module

基于SOP知识库匹配生成告警处置步骤
"""

import re
import logging
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RemediationStep:
    """处置步骤"""
    step_id: int
    action: str
    description: str
    command: str | None = None
    rationale: str | None = None
    estimated_duration: str | None = None
    auto_executable: bool = False


@dataclass
class SOPMatch:
    """SOP匹配结果"""
    sop_id: str
    sop_name: str
    match_score: float
    matched_keywords: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    steps: list[RemediationStep] = field(default_factory=list)


@dataclass
class RemediationPlan:
    """处置方案"""
    alert_id: str
    alert_type: str
    alert_level: str
    matched_sops: list[SOPMatch]
    generated_steps: list[RemediationStep]
    summary: str
    estimated_total_time: str | None = None
    risk_level: str = "medium"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SOPKnowledgeBase:
    """SOP知识库"""
    
    # 预定义的SOP库
    SOP_LIB = {
        "sop_001": {
            "name": "服务器CPU使用率过高处置",
            "keywords": ["cpu", "high cpu", "cpu使用率", "cpu飙高", "服务器CPU", "cpu spike", "load average"],
            "alert_types": ["cpu_high", "system_load"],
            "prerequisites": ["确认监控数据准确性", "检查是否有计划内活动"],
            "steps": [
                {"step_id": 1, "action": "收集现场信息", "description": "获取CPU使用率趋势、进程列表", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 2, "action": "定位高CPU进程", "description": "使用top/htop定位占用CPU最高的进程", "command": "top -bn1 | head -20", "rationale": "确定是哪个进程导致CPU过高", "estimated_duration": "1分钟", "auto_executable": True},
                {"step_id": 3, "action": "分析进程性质", "description": "判断进程是正常业务还是异常进程", "rationale": "确定后续处理方式", "estimated_duration": "3分钟", "auto_executable": False},
                {"step_id": 4, "action": "执行处置", "description": "如果是异常进程，考虑重启或隔离", "command": "systemctl restart <service>", "estimated_duration": "5分钟", "auto_executable": True},
                {"step_id": 5, "action": "验证效果", "description": "确认CPU使用率恢复正常", "command": "uptime", "estimated_duration": "2分钟", "auto_executable": True},
            ]
        },
        "sop_002": {
            "name": "内存使用率过高处置",
            "keywords": ["memory", "high memory", "内存使用率", "内存不足", "oom", "out of memory"],
            "alert_types": ["memory_high", "oom"],
            "prerequisites": ["确认内存监控数据", "检查可用交换空间"],
            "steps": [
                {"step_id": 1, "action": "检查内存使用详情", "description": "查看内存使用情况和进程列表", "command": "free -h && ps aux --sort=-%mem | head -10", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 2, "action": "识别内存泄漏", "description": "检查是否存在内存持续增长的进程", "rationale": "判断是否为内存泄漏问题", "estimated_duration": "5分钟", "auto_executable": False},
                {"step_id": 3, "action": "释放缓存", "description": "执行缓存清理释放内存", "command": "sync && echo 3 > /proc/sys/vm/drop_caches", "estimated_duration": "1分钟", "auto_executable": True},
                {"step_id": 4, "action": "处置问题进程", "description": "重启异常服务或杀掉内存占用高的进程", "command": "systemctl restart <service>", "estimated_duration": "5分钟", "auto_executable": True},
                {"step_id": 5, "action": "监控恢复情况", "description": "持续观察内存使用情况", "command": "watch -n 2 'free -h'", "estimated_duration": "10分钟", "auto_executable": True},
            ]
        },
        "sop_003": {
            "name": "磁盘空间不足处置",
            "keywords": ["disk", "disk full", "磁盘空间", "磁盘不足", "no space", "storage", "文件系统"],
            "alert_types": ["disk_full", "disk_space"],
            "prerequisites": ["确认磁盘分区情况", "识别可清理目录"],
            "steps": [
                {"step_id": 1, "action": "分析磁盘使用", "description": "查看各分区使用情况", "command": "df -h", "estimated_duration": "1分钟", "auto_executable": True},
                {"step_id": 2, "action": "定位大文件", "description": "查找占用空间大的目录和文件", "command": "du -sh /* 2>/dev/null | sort -rh | head -10", "estimated_duration": "3分钟", "auto_executable": True},
                {"step_id": 3, "action": "清理日志", "description": "清理过期日志文件", "command": "find /var/log -type f -name '*.log' -mtime +7 -delete", "rationale": "释放日志占用的空间", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 4, "action": "清理临时文件", "description": "删除临时文件和缓存", "command": "rm -rf /tmp/* 2>/dev/null", "estimated_duration": "1分钟", "auto_executable": True},
                {"step_id": 5, "action": "确认清理效果", "description": "再次检查磁盘空间", "command": "df -h", "estimated_duration": "1分钟", "auto_executable": True},
            ]
        },
        "sop_004": {
            "name": "网络连接数异常处置",
            "keywords": ["network", "connection", "网络连接", "连接数", "socket", "端口", "网络异常"],
            "alert_types": ["network_connection", "connection_high"],
            "prerequisites": ["确认网络监控指标", "检查防火墙规则"],
            "steps": [
                {"step_id": 1, "action": "查看连接统计", "description": "查看当前网络连接状态", "command": "netstat -an | awk '/^tcp/ {s[$NF]++} END {for(k in s) print k, s[k]}'", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 2, "action": "定位异常IP", "description": "查找连接数异常的来源IP", "command": "netstat -an | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 3, "action": "检查服务端口", "description": "确认是哪个服务端口被大量连接", "command": "ss -s", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 4, "action": "防护处置", "description": "如确认攻击，启用防护或限制连接", "command": "iptables -A INPUT -s <malicious_ip> -j DROP", "estimated_duration": "5分钟", "auto_executable": True},
                {"step_id": 5, "action": "持续监控", "description": "监控网络连接恢复正常", "command": "watch -n 2 'netstat -an | wc -l'", "estimated_duration": "10分钟", "auto_executable": True},
            ]
        },
        "sop_005": {
            "name": "服务不可用处置",
            "keywords": ["service down", "服务不可用", "服务宕机", "服务停止", "service unavailable", "服务异常", "service error"],
            "alert_types": ["service_down", "service_unavailable"],
            "prerequisites": ["确认服务配置", "准备服务重启脚本"],
            "steps": [
                {"step_id": 1, "action": "验证服务状态", "description": "检查服务进程和端口状态", "command": "systemctl status <service> && netstat -tlnp | grep <port>", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 2, "action": "查看日志", "description": "查看服务错误日志", "command": "journalctl -u <service> --no-pager -n 50", "rationale": "了解服务失败原因", "estimated_duration": "3分钟", "auto_executable": True},
                {"step_id": 3, "action": "尝试重启服务", "description": "重启服务并观察启动日志", "command": "systemctl restart <service>", "estimated_duration": "5分钟", "auto_executable": True},
                {"step_id": 4, "action": "检查依赖", "description": "确认服务依赖的其他服务是否正常", "rationale": "可能是下游服务导致", "estimated_duration": "3分钟", "auto_executable": False},
                {"step_id": 5, "action": "验证服务恢复", "description": "确认服务恢复正常访问", "command": "curl -I http://localhost:<port>/health", "estimated_duration": "2分钟", "auto_executable": True},
            ]
        },
        "sop_006": {
            "name": "数据库连接池满处置",
            "keywords": ["database", "db", "连接池", "数据库连接", "connection pool", "db connection", "数据库异常"],
            "alert_types": ["db_connection_pool", "database_high"],
            "prerequisites": ["确认数据库服务状态", "准备连接池配置信息"],
            "steps": [
                {"step_id": 1, "action": "检查数据库状态", "description": "查看数据库服务状态和连接数", "command": "SHOW STATUS LIKE 'Threads_connected';", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 2, "action": "查看当前连接", "description": "列出所有数据库连接", "command": "SHOW PROCESSLIST;", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 3, "action": "识别阻塞查询", "description": "查找长时间运行的查询", "rationale": "阻塞查询可能导致连接堆积", "estimated_duration": "3分钟", "auto_executable": False},
                {"step_id": 4, "action": "终止异常连接", "description": "Kill掉异常的连接", "command": "KILL <process_id>", "estimated_duration": "1分钟", "auto_executable": True},
                {"step_id": 5, "action": "调整连接池配置", "description": "适当增大连接池大小或优化连接复用", "rationale": "从根本上解决连接池压力", "estimated_duration": "10分钟", "auto_executable": False},
            ]
        },
        "sop_007": {
            "name": "API响应超时处置",
            "keywords": ["api timeout", "api响应慢", "接口超时", "response time", "api延迟", "timeout", "接口异常"],
            "alert_types": ["api_timeout", "api_slow"],
            "prerequisites": ["确认是API问题而非网络问题", "准备API监控日志"],
            "steps": [
                {"step_id": 1, "action": "检查API健康状态", "description": "测试API基础响应", "command": "curl -o /dev/null -s -w '%{time_total}' http://api/health", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 2, "action": "查看API日志", "description": "检查API请求日志和错误信息", "command": "tail -100 /var/log/api.log", "estimated_duration": "3分钟", "auto_executable": True},
                {"step_id": 3, "action": "检查依赖服务", "description": "验证下游服务(数据库/缓存)是否正常", "rationale": "API延迟通常是下游服务问题", "estimated_duration": "3分钟", "auto_executable": True},
                {"step_id": 4, "action": "检查资源使用", "description": "查看CPU/内存/网络是否成为瓶颈", "command": "free -h && df -h", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 5, "action": "扩容或优化", "description": "根据情况扩容实例或优化API代码", "rationale": "根本性解决方案", "estimated_duration": "30分钟", "auto_executable": False},
            ]
        },
        "sop_008": {
            "name": "证书到期告警处置",
            "keywords": ["certificate", "ssl", "证书到期", "证书过期", "ssl证书", "tls证书", "cert expire"],
            "alert_types": ["certificate_expiry", "ssl_expiry"],
            "prerequisites": ["准备新证书", "确认证书部署方式"],
            "steps": [
                {"step_id": 1, "action": "检查证书详情", "description": "查看证书到期时间", "command": "openssl s_client -connect <host>:443 -servername <domain> 2>/dev/null | openssl x509 -noout -dates", "estimated_duration": "2分钟", "auto_executable": True},
                {"step_id": 2, "action": "准备新证书", "description": "从CA获取新证书或续期证书", "rationale": "需要提前准备", "estimated_duration": "30分钟", "auto_executable": False},
                {"step_id": 3, "action": "备份旧证书", "description": "备份现有证书文件", "command": "cp -r /etc/ssl/certs /etc/ssl/certs.bak", "estimated_duration": "1分钟", "auto_executable": True},
                {"step_id": 4, "action": "部署新证书", "description": "替换为新证书并更新配置", "command": "systemctl reload nginx", "estimated_duration": "5分钟", "auto_executable": True},
                {"step_id": 5, "action": "验证证书有效性", "description": "确认新证书已生效", "command": "openssl s_client -connect <host>:443 2>/dev/null | openssl x509 -noout -dates", "estimated_duration": "2分钟", "auto_executable": True},
            ]
        },
    }
    
    def search_sops(self, alert_info: dict) -> list[SOPMatch]:
        """根据告警信息搜索匹配的SOP"""
        alert_type = alert_info.get("alert_type", "")
        alert_message = alert_info.get("message", alert_info.get("alert_name", ""))
        alert_level = alert_info.get("level", "")
        
        # 合并所有文本用于关键词匹配
        combined_text = f"{alert_type} {alert_message} {alert_level}".lower()
        
        matched_sops = []
        
        for sop_id, sop in self.SOP_LIB.items():
            score = 0.0
            matched_keywords = []
            
            # 检查告警类型匹配
            if alert_type.lower() in [t.lower() for t in sop.get("alert_types", [])]:
                score += 0.5
            
            # 检查关键词匹配
            for keyword in sop.get("keywords", []):
                if keyword.lower() in combined_text:
                    score += 0.15
                    matched_keywords.append(keyword)
            
            # 检查告警消息中的关键词匹配(更灵活)
            for keyword in sop.get("keywords", []):
                keyword_lower = keyword.lower()
                # 支持部分匹配
                if any(part in combined_text for part in keyword_lower.split()):
                    if keyword not in matched_keywords:
                        score += 0.1
                        matched_keywords.append(keyword)
            
            if score > 0:
                # 构建RemediationStep列表
                steps = []
                for step_data in sop.get("steps", []):
                    step = RemediationStep(
                        step_id=step_data["step_id"],
                        action=step_data["action"],
                        description=step_data["description"],
                        command=step_data.get("command"),
                        rationale=step_data.get("rationale"),
                        estimated_duration=step_data.get("estimated_duration"),
                        auto_executable=step_data.get("auto_executable", False)
                    )
                    steps.append(step)
                
                sop_match = SOPMatch(
                    sop_id=sop_id,
                    sop_name=sop["name"],
                    match_score=min(score, 1.0),  # 最高1.0
                    matched_keywords=matched_keywords,
                    prerequisites=sop.get("prerequisites", []),
                    steps=steps
                )
                matched_sops.append(sop_match)
        
        # 按匹配分数排序
        matched_sops.sort(key=lambda x: x.match_score, reverse=True)
        
        return matched_sops


class RemediationEngine:
    """AI处置建议引擎"""
    
    def __init__(self):
        self.sop_knowledge_base = SOPKnowledgeBase()
        self._alert_level_risk = {
            "critical": "high",
            "high": "high", 
            "medium": "medium",
            "low": "low",
            "info": "low"
        }
    
    def analyze_alert(self, alert_id: str, alert_data: dict) -> RemediationPlan:
        """
        分析告警并生成处置方案
        
        Args:
            alert_id: 告警ID
            alert_data: 告警详情数据
            
        Returns:
            RemediationPlan: 处置方案
        """
        alert_type = alert_data.get("alert_type", "unknown")
        alert_level = alert_data.get("level", "medium")
        alert_name = alert_data.get("alert_name", alert_data.get("name", ""))
        alert_message = alert_data.get("message", alert_data.get("description", ""))
        
        # 构造告警信息用于SOP匹配
        alert_info = {
            "alert_type": alert_type,
            "message": f"{alert_name} {alert_message}",
            "level": alert_level
        }
        
        # 匹配SOP
        matched_sops = self.sop_knowledge_base.search_sops(alert_info)
        
        # 生成处置步骤
        generated_steps = self._generate_remediation_steps(matched_sops, alert_data)
        
        # 计算预估时间
        total_time = self._estimate_total_time(generated_steps)
        
        # 生成摘要
        summary = self._generate_summary(alert_name, matched_sops, generated_steps)
        
        # 确定风险等级
        risk_level = self._calculate_risk_level(alert_level, matched_sops)
        
        return RemediationPlan(
            alert_id=alert_id,
            alert_type=alert_type,
            alert_level=alert_level,
            matched_sops=matched_sops,
            generated_steps=generated_steps,
            summary=summary,
            estimated_total_time=total_time,
            risk_level=risk_level
        )
    
    def _generate_remediation_steps(self, matched_sops: list[SOPMatch], alert_data: dict) -> list[RemediationStep]:
        """根据匹配的SOP生成处置步骤"""
        steps = []
        step_counter = 1
        
        if not matched_sops:
            # 无匹配SOP时生成通用步骤
            steps.append(RemediationStep(
                step_id=step_counter,
                action="收集告警信息",
                description="收集告警详情，确定告警原因",
                auto_executable=False
            ))
            step_counter += 1
            steps.append(RemediationStep(
                step_id=step_counter,
                action="联系相关人员",
                description="根据告警类型联系相关负责人",
                auto_executable=False
            ))
            step_counter += 1
            steps.append(RemediationStep(
                step_id=step_counter,
                action="手动处理",
                description="根据实际情况进行手动处置",
                auto_executable=False
            ))
        else:
            # 从最佳匹配SOP获取步骤
            best_match = matched_sops[0]
            
            # 如果有前置条件，先添加前置条件检查
            if best_match.prerequisites:
                for i, prereq in enumerate(best_match.prerequisites[:2], 1):
                    steps.append(RemediationStep(
                        step_id=step_counter,
                        action=f"检查前置条件 ({i}/{len(best_match.prerequisites)})",
                        description=prereq,
                        auto_executable=False
                    ))
                    step_counter += 1
            
            # 添加SOP步骤
            for step in best_match.steps:
                new_step = RemediationStep(
                    step_id=step_counter,
                    action=step.action,
                    description=step.description,
                    command=step.command,
                    rationale=step.rationale,
                    estimated_duration=step.estimated_duration,
                    auto_executable=step.auto_executable
                )
                # 如果是自动执行的命令，添加告警上下文的变量替换
                if new_step.command and "<" in new_step.command:
                    new_step.command = self._substitute_variables(new_step.command, alert_data)
                
                steps.append(new_step)
                step_counter += 1
        
        return steps
    
    def _substitute_variables(self, command: str, alert_data: dict) -> str:
        """替换命令中的变量"""
        # 简单变量替换 - 实际实现可以从alert_data中提取
        replacements = {
            "<service>": alert_data.get("service_name", "your-service"),
            "<port>": str(alert_data.get("port", 80)),
            "<host>": alert_data.get("host", "localhost"),
            "<domain>": alert_data.get("domain", "example.com"),
            "<malicious_ip>": alert_data.get("source_ip", "<source_ip>"),
            "<process_id>": alert_data.get("pid", "<pid>"),
        }
        
        result = command
        for var, value in replacements.items():
            result = result.replace(var, value)
        
        return result
    
    def _estimate_total_time(self, steps: list[RemediationStep]) -> str:
        """估算总处置时间"""
        total_minutes = 0
        for step in steps:
            duration = step.estimated_duration
            if duration:
                # 解析时间字符串，如 "5分钟", "30分钟"
                match = re.search(r'(\d+)\s*分钟', duration)
                if match:
                    total_minutes += int(match.group(1))
        
        if total_minutes == 0:
            return "未知"
        elif total_minutes < 60:
            return f"约{total_minutes}分钟"
        else:
            hours = total_minutes // 60
            mins = total_minutes % 60
            return f"约{hours}小时{mins}分钟" if mins > 0 else f"约{hours}小时"
    
    def _generate_summary(self, alert_name: str, matched_sops: list[SOPMatch], steps: list[RemediationStep]) -> str:
        """生成处置摘要"""
        if not matched_sops:
            return f"针对告警「{alert_name}」，未找到完全匹配的SOP流程，建议联系运维人员手动处理。"
        
        best_sop = matched_sops[0]
        auto_steps = sum(1 for s in steps if s.auto_executable)
        
        summary = f"针对「{alert_name}」告警，匹配SOP「{best_sop.sop_name}」(匹配度: {best_sop.match_score:.0%})，"
        summary += f"生成了 {len(steps)} 个处置步骤"
        if auto_steps > 0:
            summary += f"，其中 {auto_steps} 个可自动执行"
        summary += "。"
        
        if len(matched_sops) > 1:
            summary += f"同时检测到 {len(matched_sops)-1} 个相关SOP可能适用。"
        
        return summary
    
    def _calculate_risk_level(self, alert_level: str, matched_sops: list[SOPMatch]) -> str:
        """计算处置风险等级"""
        base_risk = self._alert_level_risk.get(alert_level.lower(), "medium")
        
        # 如果有多个高匹配度的SOP，风险降低
        if len(matched_sops) >= 2 and matched_sops[0].match_score > 0.5:
            risk_mapping = {"high": "medium", "medium": "low", "low": "low"}
            return risk_mapping.get(base_risk, base_risk)
        
        return base_risk
    
    def to_dict(self, plan: RemediationPlan) -> dict:
        """将处置方案转换为字典格式"""
        return {
            "alert_id": plan.alert_id,
            "alert_type": plan.alert_type,
            "alert_level": plan.alert_level,
            "risk_level": plan.risk_level,
            "summary": plan.summary,
            "estimated_total_time": plan.estimated_total_time,
            "matched_sops": [
                {
                    "sop_id": sop.sop_id,
                    "sop_name": sop.sop_name,
                    "match_score": sop.match_score,
                    "matched_keywords": sop.matched_keywords,
                    "prerequisites": sop.prerequisites
                }
                for sop in plan.matched_sops
            ],
            "steps": [
                {
                    "step_id": step.step_id,
                    "action": step.action,
                    "description": step.description,
                    "command": step.command,
                    "rationale": step.rationale,
                    "estimated_duration": step.estimated_duration,
                    "auto_executable": step.auto_executable
                }
                for step in plan.generated_steps
            ],
            "created_at": plan.created_at
        }