"""
AI Root Cause Analysis Module
Provides AI-powered root cause analysis for work orders and incidents
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RootCauseConfidence(str, Enum):
    """Root cause confidence level"""
    HIGH = "high"      # >= 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # < 0.5


class RootCauseCategory(str, Enum):
    """Root cause category classification"""
    HARDWARE = "hardware"
    SOFTWARE = "software"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    PROCESS = "process"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


@dataclass
class RootCauseResult:
    """Root cause analysis result"""
    root_cause: str
    confidence: float
    confidence_level: RootCauseConfidence
    category: RootCauseCategory
    evidence: List[str] = field(default_factory=list)
    related_factors: List[str] = field(default_factory=list)
    analysis_details: Dict[str, Any] = field(default_factory=dict)
    suggested_investigation: List[str] = field(default_factory=list)
    similar_cases: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'root_cause': self.root_cause,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level.value,
            'category': self.category.value,
            'evidence': self.evidence,
            'related_factors': self.related_factors,
            'analysis_details': self.analysis_details,
            'suggested_investigation': self.suggested_investigation,
            'similar_cases': self.similar_cases,
            'created_at': self.created_at.isoformat()
        }


class RootCauseAnalyzer:
    """
    AI-powered Root Cause Analyzer
    
    Analyzes work orders, alerts, and incident data to identify root causes
    using pattern matching, correlation analysis, and LLM-powered inference.
    """
    
    # Common root cause patterns
    HARDWARE_PATTERNS = [
        'cpu', 'memory', 'disk', 'raid', 'power', 'temperature', 'fan',
        'hardware', 'physical', 'machine', 'server', 'disk full', 'io error',
        '磁盘', '硬盘', '内存', '电源', '服务器', '硬件', 'raid', '存储'
    ]
    
    SOFTWARE_PATTERNS = [
        'application', 'process', 'service', 'daemon', 'bug', 'crash',
        'exception', 'error', 'fault', 'software', 'upgrade', 'patch',
        '软件', '应用', '服务', '进程', '崩溃', '异常', '错误', 'bug'
    ]
    
    NETWORK_PATTERNS = [
        'network', 'connectivity', 'bandwidth', 'latency', 'firewall',
        'router', 'switch', 'dns', 'dhcp', 'tcp', 'udp', 'packet loss',
        '网络', '连接', '防火墙', '路由', 'dns', '网络连接', '网络中断'
    ]
    
    CONFIG_PATTERNS = [
        'configuration', 'config', 'misconfiguration', 'wrong', 'incorrect',
        'permission', 'privilege', 'access', 'setting',
        '配置', '权限', '权限', '访问', '设置', '配置错误'
    ]
    
    PROCESS_PATTERNS = [
        'procedure', 'process', 'human', 'operation', 'manual',
        '流程', '操作', '人员', '培训', '步骤', '不规范', '失误'
    ]
    
    EXTERNAL_PATTERNS = [
        'external', 'vendor', 'third party', 'upstream', 'internet',
        'provider', 'supplier', 'partner',
        '外部', '第三方', '供应商', '厂商', '外部网络'
    ]
    
    def __init__(self, llm_client=None):
        """
        Initialize Root Cause Analyzer
        
        Args:
            llm_client: Optional LLM client for AI-powered analysis
        """
        self.llm_client = llm_client
    
    def analyze(
        self,
        title: str,
        description: str,
        order_type: str = None,
        device_info: Dict[str, Any] = None,
        alert_info: Dict[str, Any] = None,
        metrics: Dict[str, Any] = None,
        historical_cases: List[Dict[str, Any]] = None,
        error_logs: str = None
    ) -> RootCauseResult:
        """
        Analyze work order or incident to identify root cause
        
        Args:
            title: Work order/incident title
            description: Detailed description
            order_type: Work order type (fault, change, etc.)
            device_info: Related device information
            alert_info: Related alert information
            metrics: System metrics if available
            historical_cases: Similar historical cases
            error_logs: Error logs if available
            
        Returns:
            RootCauseResult with analysis findings
        """
        # Combine all text for analysis
        combined_text = self._combine_text(title, description, error_logs)
        
        # Identify category based on patterns
        category = self._identify_category(combined_text)
        
        # Find evidence in text
        evidence = self._extract_evidence(combined_text, category)
        
        # Identify related factors
        related_factors = self._identify_related_factors(
            combined_text, device_info, alert_info, metrics
        )
        
        # Find similar cases
        similar_cases = self._find_similar_cases(
            historical_cases, title, description, category
        ) if historical_cases else []
        
        # Calculate confidence based on evidence and matches
        confidence = self._calculate_confidence(
            evidence, related_factors, similar_cases, category
        )
        
        # Determine root cause based on analysis
        root_cause = self._determine_root_cause(
            title, description, category, evidence, related_factors
        )
        
        # Generate investigation suggestions
        investigation = self._generate_investigation_steps(
            category, root_cause, device_info
        )
        
        return RootCauseResult(
            root_cause=root_cause,
            confidence=confidence,
            confidence_level=self._get_confidence_level(confidence),
            category=category,
            evidence=evidence,
            related_factors=related_factors,
            analysis_details=self._build_analysis_details(
                title, description, device_info, alert_info, metrics
            ),
            suggested_investigation=investigation,
            similar_cases=similar_cases[:5]  # Limit to top 5 similar cases
        )
    
    def _combine_text(
        self,
        title: str,
        description: str,
        error_logs: str = None
    ) -> str:
        """Combine all text sources for analysis"""
        parts = [title or '', description or '']
        if error_logs:
            parts.append(error_logs)
        return ' '.join(parts).lower()
    
    def _identify_category(self, text: str) -> RootCauseCategory:
        """Identify root cause category based on text patterns"""
        scores = {
            RootCauseCategory.HARDWARE: 0,
            RootCauseCategory.SOFTWARE: 0,
            RootCauseCategory.NETWORK: 0,
            RootCauseCategory.CONFIGURATION: 0,
            RootCauseCategory.PROCESS: 0,
            RootCauseCategory.EXTERNAL: 0,
        }
        
        for pattern in self.HARDWARE_PATTERNS:
            if pattern in text:
                scores[RootCauseCategory.HARDWARE] += 1
        
        for pattern in self.SOFTWARE_PATTERNS:
            if pattern in text:
                scores[RootCauseCategory.SOFTWARE] += 1
        
        for pattern in self.NETWORK_PATTERNS:
            if pattern in text:
                scores[RootCauseCategory.NETWORK] += 1
        
        for pattern in self.CONFIG_PATTERNS:
            if pattern in text:
                scores[RootCauseCategory.CONFIGURATION] += 1
        
        for pattern in self.PROCESS_PATTERNS:
            if pattern in text:
                scores[RootCauseCategory.PROCESS] += 1
        
        for pattern in self.EXTERNAL_PATTERNS:
            if pattern in text:
                scores[RootCauseCategory.EXTERNAL] += 1
        
        # Return category with highest score
        if max(scores.values()) == 0:
            return RootCauseCategory.UNKNOWN
        
        return max(scores, key=scores.get)
    
    def _extract_evidence(self, text: str, category: RootCauseCategory) -> List[str]:
        """Extract supporting evidence from text"""
        evidence = []
        
        # Category-specific evidence extraction
        if category == RootCauseCategory.HARDWARE:
            for pattern in self.HARDWARE_PATTERNS:
                if pattern in text:
                    evidence.append(f"检测到硬件相关关键词: {pattern}")
        
        elif category == RootCauseCategory.SOFTWARE:
            for pattern in self.SOFTWARE_PATTERNS:
                if pattern in text:
                    evidence.append(f"检测到软件相关关键词: {pattern}")
        
        elif category == RootCauseCategory.NETWORK:
            for pattern in self.NETWORK_PATTERNS:
                if pattern in text:
                    evidence.append(f"检测到网络相关关键词: {pattern}")
        
        elif category == RootCauseCategory.CONFIGURATION:
            for pattern in self.CONFIG_PATTERNS:
                if pattern in text:
                    evidence.append(f"检测到配置相关关键词: {pattern}")
        
        elif category == RootCauseCategory.PROCESS:
            for pattern in self.PROCESS_PATTERNS:
                if pattern in text:
                    evidence.append(f"检测到流程相关关键词: {pattern}")
        
        elif category == RootCauseCategory.EXTERNAL:
            for pattern in self.EXTERNAL_PATTERNS:
                if pattern in text:
                    evidence.append(f"检测到外部因素关键词: {pattern}")
        
        # Extract numbers that might indicate thresholds/limits
        import re
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            evidence.append(f"文本中包含数字: {', '.join(set(numbers[:10]))}")
        
        return evidence[:10]  # Limit evidence items
    
    def _identify_related_factors(
        self,
        text: str,
        device_info: Dict[str, Any] = None,
        alert_info: Dict[str, Any] = None,
        metrics: Dict[str, Any] = None
    ) -> List[str]:
        """Identify factors contributing to the incident"""
        factors = []
        
        # Time-based factors
        hour = datetime.now().hour
        if 9 <= hour < 11 or 14 <= hour < 16:
            factors.append("发生在业务高峰期")
        elif 22 <= hour or hour < 6:
            factors.append("发生在非工作时间")
        
        # Device info factors
        if device_info:
            if device_info.get('age_days', 0) > 365 * 3:
                factors.append("设备使用超过3年，可能老化")
            if device_info.get('load_percent', 0) > 80:
                factors.append("设备负载过高")
            if device_info.get('cpu_usage', 0) > 90:
                factors.append("CPU使用率异常高")
            if device_info.get('memory_usage', 0) > 90:
                factors.append("内存使用率异常高")
            if device_info.get('disk_usage', 0) > 90:
                factors.append("磁盘使用率过高")
        
        # Alert info factors
        if alert_info:
            severity = alert_info.get('severity', '').lower()
            if severity in ['critical', 'fatal', 'p1']:
                factors.append("关联告警为严重级别")
            elif severity in ['warning', 'major', 'p2']:
                factors.append("关联告警为警告级别")
            
            duration = alert_info.get('duration_minutes', 0)
            if duration > 60:
                factors.append(f"告警持续时间较长: {duration}分钟")
        
        # Metrics factors
        if metrics:
            if metrics.get('error_rate', 0) > 0.05:
                factors.append("错误率异常升高")
            if metrics.get('response_time_ms', 0) > 1000:
                factors.append("响应时间超时")
        
        return factors[:5]  # Limit factors
    
    def _find_similar_cases(
        self,
        historical_cases: List[Dict[str, Any]],
        title: str,
        description: str,
        category: RootCauseCategory
    ) -> List[Dict[str, Any]]:
        """Find similar historical cases"""
        if not historical_cases:
            return []
        
        similar = []
        title_lower = title.lower()
        desc_lower = description.lower()
        
        for case in historical_cases:
            score = 0
            
            # Match title keywords
            case_title = case.get('title', '').lower()
            for word in title_lower.split():
                if len(word) > 3 and word in case_title:
                    score += 2
            
            # Match description keywords
            case_desc = case.get('description', '').lower()
            for word in desc_lower.split():
                if len(word) > 3 and word in case_desc:
                    score += 1
            
            # Match category
            if case.get('category') == category.value:
                score += 5
            
            # Match device
            if case.get('device_ip') and description and case.get('device_ip') in description:
                score += 3
            
            if score > 0:
                similar.append({
                    'case_id': case.get('id'),
                    'title': case.get('title'),
                    'root_cause': case.get('root_cause'),
                    'resolution': case.get('resolution'),
                    'similarity_score': score
                })
        
        # Sort by similarity and return top matches
        similar.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similar
    
    def _calculate_confidence(
        self,
        evidence: List[str],
        related_factors: List[str],
        similar_cases: List[Dict[str, Any]],
        category: RootCauseCategory
    ) -> float:
        """Calculate confidence score for the analysis"""
        confidence = 0.5  # Base confidence
        
        # Adjust based on evidence count
        if len(evidence) >= 3:
            confidence += 0.2
        elif len(evidence) >= 1:
            confidence += 0.1
        
        # Adjust based on similar cases
        if len(similar_cases) >= 3:
            confidence += 0.15
        elif len(similar_cases) >= 1:
            confidence += 0.1
        
        # Adjust based on category certainty
        if category != RootCauseCategory.UNKNOWN:
            confidence += 0.1
        
        # Adjust based on related factors
        if len(related_factors) >= 3:
            confidence += 0.05
        
        return min(confidence, 0.99)  # Cap at 0.99
    
    def _get_confidence_level(self, confidence: float) -> RootCauseConfidence:
        """Get confidence level from score"""
        if confidence >= 0.8:
            return RootCauseConfidence.HIGH
        elif confidence >= 0.5:
            return RootCauseConfidence.MEDIUM
        else:
            return RootCauseConfidence.LOW
    
    def _determine_root_cause(
        self,
        title: str,
        description: str,
        category: RootCauseCategory,
        evidence: List[str],
        related_factors: List[str]
    ) -> str:
        """Determine the root cause based on analysis"""
        text = f"{title or ''} {description or ''}".lower()
        
        # Hardware causes
        if category == RootCauseCategory.HARDWARE:
            if any(p in text for p in ['disk', 'raid', '存储', '磁盘', '硬盘', 'io error']):
                return "存储设备故障导致服务不可用"
            if any(p in text for p in ['power', '电源', 'ups']):
                return "电源系统故障导致设备关机"
            if any(p in text for p in ['memory', 'mem', '内存']):
                return "内存故障或内存不足导致系统异常"
            if any(p in text for p in ['cpu']):
                return "cpu过载或cpu硬件故障"
            if any(p in text for p in ['server', '服务器', 'machine', '物理机']):
                return "服务器硬件故障导致服务异常"
            return "硬件设备故障导致服务异常"
        
        # Software causes
        elif category == RootCauseCategory.SOFTWARE:
            if any(p in text for p in ['crash', '崩溃', 'panic']):
                return "应用程序崩溃导致服务中断"
            if any(p in text for p in ['exception', '异常', 'bug', '缺陷', 'error', '错误']):
                return "软件异常导致功能不可用"
            if any(p in text for p in ['update', 'upgrade', '升级', '更新', 'patch']):
                return "软件升级/更新引入的问题"
            if any(p in text for p in ['service', '服务', '进程', 'daemon']):
                return "服务进程异常导致功能不可用"
            return "软件问题导致服务异常"
        
        # Network causes
        elif category == RootCauseCategory.NETWORK:
            if any(p in text for p in ['dns']):
                return "dns解析失败导致服务不可达"
            if any(p in text for p in ['firewall', '防火墙']):
                return "防火墙规则阻止导致连接失败"
            if any(p in text for p in ['bandwidth', '带宽', '网络']):
                return "网络带宽不足导致响应缓慢"
            if any(p in text for p in ['connectivity', '连接', '网络中断']):
                return "网络连接中断导致服务不可用"
            return "网络问题导致通信异常"
        
        # Configuration causes
        elif category == RootCauseCategory.CONFIGURATION:
            if any(p in text for p in ['permission', '权限', 'access', '访问']):
                return "权限配置错误导致访问被拒绝"
            if any(p in text for p in ['port', '端口']):
                return "端口配置错误导致服务无法启动"
            if any(p in text for p in ['timeout', '超时']):
                return "超时配置不当导致请求失败"
            return "配置错误导致系统行为异常"
        
        # Process causes
        elif category == RootCauseCategory.PROCESS:
            if any(p in text for p in ['步骤', '流程', '操作']):
                return "操作流程不规范导致问题发生"
            if any(p in text for p in ['人员', 'human', '培训', '失误']):
                return "人员操作失误或培训不足"
            return "流程问题导致服务异常"
        
        # External causes
        elif category == RootCauseCategory.EXTERNAL:
            if any(p in text for p in ['vendor', '厂商', 'supplier', '供应商']):
                return "第三方供应商服务异常"
            if any(p in text for p in ['internet', '网络', '外部网络']):
                return "外部网络环境异常"
            return "外部因素导致服务异常"
        
        # Unknown
        return "根本原因待进一步分析"
    
    def _generate_investigation_steps(
        self,
        category: RootCauseCategory,
        root_cause: str,
        device_info: Dict[str, Any] = None
    ) -> List[str]:
        """Generate suggested investigation steps"""
        steps = []
        
        # Category-specific investigation steps
        if category == RootCauseCategory.HARDWARE:
            steps.extend([
                "1. 检查设备硬件状态指示灯和日志",
                "2. 查看硬件健康监控数据",
                "3. 检查系统日志中的硬件错误",
                "4. 如有需要，联系硬件供应商支持"
            ])
        
        elif category == RootCauseCategory.SOFTWARE:
            steps.extend([
                "1. 检查应用进程状态和资源使用",
                "2. 查看应用日志中的错误信息",
                "3. 检查最近的应用变更记录",
                "4. 分析错误堆栈和异常信息"
            ])
        
        elif category == RootCauseCategory.NETWORK:
            steps.extend([
                "1. 检查网络连通性和延迟",
                "2. 查看防火墙和安全组规则",
                "3. 检查DNS解析是否正常",
                "4. 分析网络流量和带宽使用"
            ])
        
        elif category == RootCauseCategory.CONFIGURATION:
            steps.extend([
                "1. 对比最近配置变更记录",
                "2. 检查相关配置文件语法",
                "3. 验证权限和访问控制设置",
                "4. 回滚可疑的配置变更"
            ])
        
        elif category == RootCauseCategory.PROCESS:
            steps.extend([
                "1. 梳理问题发生时的操作步骤",
                "2. 访谈相关操作人员",
                "3. 检查操作记录和审计日志",
                "4. 完善操作流程和 Checklist"
            ])
        
        elif category == RootCauseCategory.EXTERNAL:
            steps.extend([
                "1. 确认外部服务提供商状态",
                "2. 检查第三方接口调用日志",
                "3. 评估外部依赖的健康状态",
                "4. 准备备用方案或降级策略"
            ])
        
        else:
            steps.extend([
                "1. 收集完整的故障现场信息",
                "2. 分析相关监控和日志数据",
                "3. 复现问题场景",
                "4. 确定需要进一步分析的维度"
            ])
        
        return steps
    
    def _build_analysis_details(
        self,
        title: str,
        description: str,
        device_info: Dict[str, Any] = None,
        alert_info: Dict[str, Any] = None,
        metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Build detailed analysis context"""
        details = {
            'title_length': len(title or ''),
            'description_length': len(description or ''),
            'has_device_info': device_info is not None,
            'has_alert_info': alert_info is not None,
            'has_metrics': metrics is not None,
        }
        
        if device_info:
            details['device_name'] = device_info.get('name')
            details['device_type'] = device_info.get('type')
        
        if alert_info:
            details['alert_severity'] = alert_info.get('severity')
            details['alert_name'] = alert_info.get('name')
        
        return details
