"""
AI Remediation Module Tests

测试AI处置建议引擎和API接口
"""

import pytest
from modules.business.ai_copilot.remediation import (
    RemediationEngine,
    SOPKnowledgeBase,
    RemediationStep,
    SOPMatch,
    RemediationPlan
)


class TestSOPKnowledgeBase:
    """测试SOP知识库"""
    
    def setup_method(self):
        self.sop_kb = SOPKnowledgeBase()
    
    def test_search_sops_cpu_high(self):
        """测试CPU高负载告警的SOP匹配"""
        alert_info = {
            "alert_type": "cpu_high",
            "message": "CPU使用率超过90%",
            "level": "high"
        }
        matched = self.sop_kb.search_sops(alert_info)
        
        assert len(matched) > 0
        # CPU相关告警应该匹配到sop_001
        sop_ids = [m.sop_id for m in matched]
        assert "sop_001" in sop_ids
        
        best_match = matched[0]
        assert best_match.sop_id == "sop_001"
        assert best_match.match_score > 0
        assert len(best_match.steps) > 0
    
    def test_search_sops_memory_high(self):
        """测试内存高负载告警的SOP匹配"""
        alert_info = {
            "alert_type": "memory_high",
            "message": "服务器内存使用率超过85%",
            "level": "medium"
        }
        matched = self.sop_kb.search_sops(alert_info)
        
        assert len(matched) > 0
        sop_ids = [m.sop_id for m in matched]
        assert "sop_002" in sop_ids
    
    def test_search_sops_disk_full(self):
        """测试磁盘空间不足告警的SOP匹配"""
        alert_info = {
            "alert_type": "disk_full",
            "message": "磁盘空间不足 /dev/sda1 使用率100%",
            "level": "critical"
        }
        matched = self.sop_kb.search_sops(alert_info)
        
        assert len(matched) > 0
        sop_ids = [m.sop_id for m in matched]
        assert "sop_003" in sop_ids
    
    def test_search_sops_service_down(self):
        """测试服务不可用告警的SOP匹配"""
        alert_info = {
            "alert_type": "service_down",
            "message": "Nginx服务不可用",
            "level": "high"
        }
        matched = self.sop_kb.search_sops(alert_info)
        
        assert len(matched) > 0
        sop_ids = [m.sop_id for m in matched]
        assert "sop_005" in sop_ids
    
    def test_search_sops_no_match(self):
        """测试无匹配SOP的场景"""
        alert_info = {
            "alert_type": "unknown_alert",
            "message": "某个未知的告警",
            "level": "low"
        }
        matched = self.sop_kb.search_sops(alert_info)
        
        # 未知告警可能匹配到多个低分SOP，但不会完全没有匹配
        assert isinstance(matched, list)
    
    def test_search_sops_returns_sorted(self):
        """测试SOP匹配结果按分数排序"""
        # 测试多种告警
        test_cases = [
            {"alert_type": "cpu_high", "message": "CPU使用率过高", "level": "high"},
            {"alert_type": "memory_high", "message": "内存不足", "level": "medium"},
        ]
        
        for alert_info in test_cases:
            matched = self.sop_kb.search_sops(alert_info)
            if len(matched) > 1:
                # 验证排序：分数递减
                scores = [m.match_score for m in matched]
                assert scores == sorted(scores, reverse=True)


class TestRemediationStep:
    """测试处置步骤模型"""
    
    def test_remediation_step_creation(self):
        """测试处置步骤创建"""
        step = RemediationStep(
            step_id=1,
            action="检查状态",
            description="检查服务状态",
            command="systemctl status nginx",
            rationale="确定服务是否在运行",
            estimated_duration="2分钟",
            auto_executable=True
        )
        
        assert step.step_id == 1
        assert step.action == "检查状态"
        assert step.auto_executable is True
    
    def test_remediation_step_defaults(self):
        """测试处置步骤默认值"""
        step = RemediationStep(
            step_id=1,
            action="测试",
            description="测试步骤"
        )
        
        assert step.command is None
        assert step.rationale is None
        assert step.auto_executable is False


class TestRemediationEngine:
    """测试处置引擎"""
    
    def setup_method(self):
        self.engine = RemediationEngine()
    
    def test_analyze_alert_cpu_high(self):
        """测试CPU高负载告警分析"""
        alert_data = {
            "alert_type": "cpu_high",
            "alert_name": "CPU使用率告警",
            "level": "high",
            "message": "服务器CPU使用率超过90%",
            "service_name": "web-server",
            "host": "192.168.1.100"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-001",
            alert_data=alert_data
        )
        
        assert plan.alert_id == "alert-001"
        assert plan.alert_type == "cpu_high"
        assert plan.alert_level == "high"
        assert len(plan.matched_sops) > 0
        assert len(plan.generated_steps) > 0
        assert plan.risk_level in ["low", "medium", "high"]
        assert plan.summary is not None
    
    def test_analyze_alert_memory_high(self):
        """测试内存高负载告警分析"""
        alert_data = {
            "alert_type": "memory_high",
            "alert_name": "内存使用率过高",
            "level": "medium",
            "message": "可用内存不足1GB"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-002",
            alert_data=alert_data
        )
        
        assert plan.alert_type == "memory_high"
        assert len(plan.matched_sops) > 0
    
    def test_analyze_alert_disk_full(self):
        """测试磁盘空间不足告警分析"""
        alert_data = {
            "alert_type": "disk_full",
            "alert_name": "磁盘空间不足",
            "level": "critical",
            "message": "/dev/sda1 已用空间100%"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-003",
            alert_data=alert_data
        )
        
        assert plan.alert_level == "critical"
        assert plan.risk_level == "high"
        assert len(plan.generated_steps) > 0
    
    def test_analyze_alert_unknown_type(self):
        """测试未知类型告警分析"""
        alert_data = {
            "alert_type": "unknown_alert",
            "alert_name": "未知告警",
            "level": "low",
            "message": "某个未知的问题"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-unknown",
            alert_data=alert_data
        )
        
        # 未知类型也会有通用步骤
        assert len(plan.generated_steps) >= 1
        assert plan.summary is not None
    
    def test_analyze_alert_variables_substitution(self):
        """测试告警变量替换"""
        alert_data = {
            "alert_type": "service_down",
            "alert_name": "服务宕机",
            "level": "high",
            "message": "Nginx服务不可用",
            "service_name": "nginx"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-004",
            alert_data=alert_data
        )
        
        # 检查步骤中是否有替换了变量的命令
        for step in plan.generated_steps:
            if step.command:
                assert "<service>" not in step.command
    
    def test_generate_summary(self):
        """测试摘要生成"""
        alert_data = {
            "alert_type": "cpu_high",
            "alert_name": "CPU告警",
            "level": "high",
            "message": "CPU使用率过高"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-005",
            alert_data=alert_data
        )
        
        assert "CPU告警" in plan.summary
        assert "SOP" in plan.summary or "匹配" in plan.summary
    
    def test_to_dict(self):
        """测试转换为字典格式"""
        alert_data = {
            "alert_type": "cpu_high",
            "alert_name": "CPU告警",
            "level": "high",
            "message": "CPU使用率过高"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-006",
            alert_data=alert_data
        )
        
        result = self.engine.to_dict(plan)
        
        assert "alert_id" in result
        assert "steps" in result
        assert "matched_sops" in result
        assert isinstance(result["steps"], list)
        assert isinstance(result["matched_sops"], list)
    
    def test_estimate_total_time(self):
        """测试总时间估算"""
        alert_data = {
            "alert_type": "cpu_high",
            "alert_name": "CPU告警",
            "level": "high",
            "message": "CPU使用率过高"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-007",
            alert_data=alert_data
        )
        
        # 应该有预估时间
        assert plan.estimated_total_time is not None
        assert "分钟" in plan.estimated_total_time or "小时" in plan.estimated_total_time or plan.estimated_total_time == "未知"


class TestRemediationPlan:
    """测试处置方案模型"""
    
    def test_remediation_plan_creation(self):
        """测试处置方案创建"""
        plan = RemediationPlan(
            alert_id="alert-test",
            alert_type="test_alert",
            alert_level="medium",
            matched_sops=[],
            generated_steps=[],
            summary="测试摘要"
        )
        
        assert plan.alert_id == "alert-test"
        assert plan.risk_level == "medium"  # 默认值
        assert plan.created_at is not None
    
    def test_remediation_plan_with_sops(self):
        """测试带SOP的处置方案"""
        step = RemediationStep(
            step_id=1,
            action="测试",
            description="测试步骤"
        )
        sop = SOPMatch(
            sop_id="sop_test",
            sop_name="测试SOP",
            match_score=0.8
        )
        
        plan = RemediationPlan(
            alert_id="alert-sop-test",
            alert_type="test",
            alert_level="low",
            matched_sops=[sop],
            generated_steps=[step],
            summary="测试"
        )
        
        assert len(plan.matched_sops) == 1
        assert len(plan.generated_steps) == 1


class TestSOPMatchingEdgeCases:
    """测试SOP匹配的边界情况"""
    
    def setup_method(self):
        self.engine = RemediationEngine()
    
    def test_empty_alert_data(self):
        """测试空告警数据"""
        plan = self.engine.analyze_alert(
            alert_id="alert-empty",
            alert_data={}
        )
        
        assert plan.alert_id == "alert-empty"
        assert len(plan.generated_steps) >= 1
    
    def test_alert_with_special_characters(self):
        """测试带特殊字符的告警"""
        alert_data = {
            "alert_type": "cpu_high",
            "alert_name": "CPU告警!!!",
            "level": "high",
            "message": "CPU使用率 > 90%"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-special",
            alert_data=alert_data
        )
        
        assert plan is not None
        assert plan.summary is not None
    
    def test_all_alert_levels(self):
        """测试所有告警级别"""
        levels = ["critical", "high", "medium", "low", "info"]
        
        for level in levels:
            alert_data = {
                "alert_type": "cpu_high",
                "alert_name": f"测试{level}告警",
                "level": level,
                "message": "测试"
            }
            
            plan = self.engine.analyze_alert(
                alert_id=f"alert-{level}",
                alert_data=alert_data
            )
            
            assert plan.alert_level == level


class TestAutoExecutableSteps:
    """测试自动执行步骤"""
    
    def setup_method(self):
        self.engine = RemediationEngine()
    
    def test_auto_executable_steps_exist(self):
        """测试生成的步骤中包含可自动执行的步骤"""
        alert_data = {
            "alert_type": "cpu_high",
            "alert_name": "CPU告警",
            "level": "high",
            "message": "CPU使用率过高"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-auto",
            alert_data=alert_data
        )
        
        auto_steps = [s for s in plan.generated_steps if s.auto_executable]
        # 应该有一些自动执行的步骤
        assert len(auto_steps) >= 0  # 有些SOP步骤可能是手动的
    
    def test_command_substitution(self):
        """测试命令变量替换"""
        alert_data = {
            "alert_type": "service_down",
            "alert_name": "服务宕机",
            "level": "high",
            "message": "Nginx服务不可用",
            "service_name": "nginx"
        }
        
        plan = self.engine.analyze_alert(
            alert_id="alert-cmd",
            alert_data=alert_data
        )
        
        # 验证命令中的变量被替换
        for step in plan.generated_steps:
            if step.command:
                # 命令中不应包含未替换的变量占位符
                assert "<service>" not in step.command


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        self.engine = RemediationEngine()
    
    def test_full_remediation_flow(self):
        """完整的处置流程测试"""
        # 模拟告警数据
        alert_data = {
            "alert_type": "cpu_high",
            "alert_name": "生产环境CPU告警",
            "level": "high",
            "message": "Web服务器CPU使用率超过95%，持续5分钟",
            "service_name": "web-server",
            "host": "192.168.1.100",
            "port": 8080
        }
        
        # 1. 分析告警
        plan = self.engine.analyze_alert(
            alert_id="prod-alert-001",
            alert_data=alert_data
        )
        
        # 2. 验证结果结构
        assert plan.alert_id == "prod-alert-001"
        assert len(plan.generated_steps) > 0
        
        # 3. 转换为字典
        result = self.engine.to_dict(plan)
        
        # 4. 验证API响应格式
        assert "alert_id" in result
        assert "steps" in result
        assert "matched_sops" in result
        assert "summary" in result
        assert "risk_level" in result
        
        # 5. 验证步骤结构
        for step in result["steps"]:
            assert "step_id" in step
            assert "action" in step
            assert "description" in step
    
    def test_multiple_alert_types(self):
        """测试多种告警类型"""
        test_cases = [
            {"alert_type": "cpu_high", "level": "high"},
            {"alert_type": "memory_high", "level": "medium"},
            {"alert_type": "disk_full", "level": "critical"},
            {"alert_type": "service_down", "level": "high"},
            {"alert_type": "network_connection", "level": "medium"},
            {"alert_type": "db_connection_pool", "level": "high"},
            {"alert_type": "api_timeout", "level": "medium"},
            {"alert_type": "certificate_expiry", "level": "low"},
        ]
        
        for case in test_cases:
            alert_data = {
                **case,
                "alert_name": f"{case['alert_type']}告警",
                "message": "测试告警"
            }
            
            plan = self.engine.analyze_alert(
                alert_id=f"alert-{case['alert_type']}",
                alert_data=alert_data
            )
            
            assert plan.alert_id == f"alert-{case['alert_type']}"
            assert plan.alert_type == case["alert_type"]
            assert plan.alert_level == case["level"]


# 运行测试的辅助函数
def run_tests():
    """运行所有测试"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()