"""
BM-06 资产管理模块单元测试
"""

import pytest
from datetime import datetime, timedelta
from modules.business.asset_management.asset import (
    Asset, AssetCategory, AssetStatus, AssetType, AssetTag,
    AssetAttribute, AssetRelation, RelationType, AssetManager
)
from modules.business.asset_management.lifecycle import (
    LifecycleManager, LifecycleEvent, LifecycleEventType,
    PurchaseRecord, MaintenanceRecord, ChangeHistory
)
from modules.business.asset_management.assessment import (
    AssessmentEngine, HealthScore, LifespanPrediction,
    PerformanceTrend, FaultStatistics
)
from modules.business.asset_management.risk import (
    RiskAssessor, RiskLevel, RiskCategory, RiskItem,
    ReplacementPlan, MaintenanceRecommendation
)


class TestAsset:
    """资产模型测试"""
    
    def test_create_asset(self):
        """测试创建资产"""
        asset = Asset(
            name='Test Server',
            category=AssetCategory.SERVER,
            asset_type=AssetType.PHYSICAL_SERVER,
            status=AssetStatus.RUNNING,
            manufacturer='Dell',
            model='PowerEdge R740',
            serial_number='SN12345',
            purchase_date=datetime.now() - timedelta(days=365),
        )
        
        assert asset.asset_id is not None
        assert asset.name == 'Test Server'
        assert asset.category == AssetCategory.SERVER
        assert asset.status == AssetStatus.RUNNING
    
    def test_asset_to_dict(self):
        """测试资产转字典"""
        asset = Asset(
            name='Test Server',
            category=AssetCategory.SERVER,
        )
        data = asset.to_dict()
        
        assert 'asset_id' in data
        assert data['name'] == 'Test Server'
        assert data['category'] == 'server'
    
    def test_asset_from_dict(self):
        """测试从字典创建资产"""
        data = {
            'asset_id': 'test-123',
            'name': 'Test Server',
            'category': 'server',
            'asset_type': 'physical_server',
            'status': 'running',
        }
        asset = Asset.from_dict(data)
        
        assert asset.asset_id == 'test-123'
        assert asset.name == 'Test Server'
        assert asset.category == AssetCategory.SERVER
    
    def test_asset_tags(self):
        """测试资产标签管理"""
        asset = Asset(name='Test Server')
        
        # 添加标签
        asset.add_tag('production', category='business', color='#52c41a')
        asset.add_tag('critical')
        
        assert len(asset.tags) == 2
        assert asset.has_tag('production')
        assert not asset.has_tag('nonexistent')
        
        # 移除标签
        asset.remove_tag('critical')
        assert len(asset.tags) == 1
        assert not asset.has_tag('critical')
    
    def test_asset_attributes(self):
        """测试资产属性管理"""
        asset = Asset(name='Test Server')
        
        asset.add_attribute('owner', 'john@example.com', 'string', '资产负责人', is_required=True)
        asset.add_attribute('cost_center', 'IT-001', 'string')
        
        assert 'owner' in asset.attributes
        assert asset.attributes['owner'].is_required
        assert asset.attributes['cost_center'].value == 'IT-001'
    
    def test_asset_uptime_calculation(self):
        """测试运行时间计算"""
        asset = Asset(name='Test Server')
        asset.commissioning_date = datetime.now() - timedelta(days=100)
        
        assert asset.get_uptime() == 100
        
        # 无上线日期
        asset2 = Asset(name='Test Server2')
        assert asset2.get_uptime() == 0
    
    def test_asset_age_months(self):
        """测试资产月龄计算"""
        asset = Asset(name='Test Server')
        asset.purchase_date = datetime.now() - timedelta(days=60)
        
        age_months = asset.get_age_months()
        assert 1 <= age_months <= 3  # 约2个月


class TestAssetManager:
    """资产管理器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.manager = AssetManager()
    
    def test_add_asset(self):
        """测试添加资产"""
        asset = Asset(name='Test Server')
        result = self.manager.add_asset(asset)
        
        assert result is True
        assert asset.asset_id in self.manager.assets
    
    def test_update_asset(self):
        """测试更新资产"""
        asset = Asset(name='Test Server')
        self.manager.add_asset(asset)
        
        asset.name = 'Updated Server'
        self.manager.update_asset(asset)
        
        updated = self.manager.get_asset(asset.asset_id)
        assert updated.name == 'Updated Server'
    
    def test_delete_asset(self):
        """测试删除资产"""
        asset = Asset(name='Test Server')
        self.manager.add_asset(asset)
        
        result = self.manager.delete_asset(asset.asset_id)
        assert result is True
        assert asset.asset_id not in self.manager.assets
    
    def test_get_assets_by_category(self):
        """测试按分类获取资产"""
        server1 = Asset(name='Server1', category=AssetCategory.SERVER)
        server2 = Asset(name='Server2', category=AssetCategory.SERVER)
        network = Asset(name='Switch', category=AssetCategory.NETWORK)
        
        self.manager.add_asset(server1)
        self.manager.add_asset(server2)
        self.manager.add_asset(network)
        
        servers = self.manager.get_assets_by_category(AssetCategory.SERVER)
        assert len(servers) == 2
    
    def test_get_assets_by_status(self):
        """测试按状态获取资产"""
        running = Asset(name='Running', status=AssetStatus.RUNNING)
        maintenance = Asset(name='Maintenance', status=AssetStatus.MAINTENANCE)
        
        self.manager.add_asset(running)
        self.manager.add_asset(maintenance)
        
        running_assets = self.manager.get_assets_by_status(AssetStatus.RUNNING)
        assert len(running_assets) == 1
    
    def test_search_assets(self):
        """测试搜索资产"""
        asset1 = Asset(name='Web Server', manufacturer='Dell', serial_number='SN001')
        asset2 = Asset(name='DB Server', manufacturer='HP', serial_number='SN002')
        
        self.manager.add_asset(asset1)
        self.manager.add_asset(asset2)
        
        results = self.manager.search_assets('Dell')
        assert len(results) == 1
        assert results[0].name == 'Web Server'
    
    def test_asset_relations(self):
        """测试资产关系"""
        asset1 = Asset(name='Server1')
        asset2 = Asset(name='Server2')
        
        self.manager.add_asset(asset1)
        self.manager.add_asset(asset2)
        
        relation = AssetRelation(
            source_asset_id=asset1.asset_id,
            target_asset_id=asset2.asset_id,
            relation_type=RelationType.DEPENDENCY,
            is_critical=True,
        )
        self.manager.add_relation(relation)
        
        relations = self.manager.get_relations(asset1.asset_id)
        assert len(relations) == 1
        
        dependents = self.manager.get_dependent_assets(asset1.asset_id)
        assert asset2.asset_id in dependents
    
    def test_statistics(self):
        """测试统计信息"""
        self.manager.add_asset(Asset(name='S1', category=AssetCategory.SERVER, status=AssetStatus.RUNNING, purchase_price=5000))
        self.manager.add_asset(Asset(name='S2', category=AssetCategory.SERVER, status=AssetStatus.RUNNING, purchase_price=5000))
        self.manager.add_asset(Asset(name='N1', category=AssetCategory.NETWORK, status=AssetStatus.RUNNING, purchase_price=3000))
        
        stats = self.manager.get_statistics()
        
        assert stats['total'] == 3
        assert stats['by_category']['server'] == 2
        assert stats['by_category']['network'] == 1
        assert stats['total_value'] == 13000


class TestLifecycleManager:
    """生命周期管理器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.manager = LifecycleManager()
    
    def test_create_event(self):
        """测试创建生命周期事件"""
        event = LifecycleEvent(
            asset_id='asset-123',
            event_type=LifecycleEventType.ONLINE,
            title='上线',
            description='资产正式上线',
        )
        result = self.manager.create_event(event)
        
        assert result is True
        events = self.manager.get_events('asset-123')
        assert len(events) == 1
    
    def test_purchase_record(self):
        """测试采购记录"""
        record = PurchaseRecord(
            asset_id='asset-123',
            vendor='Dell Inc.',
            product_name='PowerEdge R740',
            total_price=15000,
        )
        result = self.manager.add_purchase_record(record)
        
        assert result is True
        retrieved = self.manager.get_purchase_record('asset-123')
        assert retrieved.vendor == 'Dell Inc.'
    
    def test_maintenance_record(self):
        """测试维保记录"""
        record = MaintenanceRecord(
            asset_id='asset-123',
            title='定期维护',
            maintenance_type='preventive',
            cost=500,
        )
        result = self.manager.add_maintenance_record(record)
        
        assert result is True
        records = self.manager.get_maintenance_records('asset-123')
        assert len(records) == 1
        
        stats = self.manager.get_maintenance_stats('asset-123')
        assert stats['total_count'] == 1
        assert stats['preventive_count'] == 1
    
    def test_change_history(self):
        """测试变更历史"""
        change = ChangeHistory(
            asset_id='asset-123',
            field_name='status',
            old_value='running',
            new_value='maintenance',
            changed_by='admin',
        )
        result = self.manager.record_change(change)
        
        assert result is True
        history = self.manager.get_change_history('asset-123')
        assert len(history) == 1
        assert history[0].field_name == 'status'
    
    def test_warranty_status(self):
        """测试保修状态"""
        record = PurchaseRecord(
            asset_id='asset-123',
            actual_delivery_date=datetime.now() - timedelta(days=300),
        )
        self.manager.add_purchase_record(record)
        
        warranty = self.manager.get_warranty_status('asset-123', record)
        
        assert warranty['has_warranty'] is True
        assert warranty['days_remaining'] < 70
        assert warranty['is_expired'] is False


class TestAssessmentEngine:
    """评估引擎测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.engine = AssessmentEngine()
    
    def test_record_performance(self):
        """测试记录性能数据"""
        asset_id = 'asset-123'
        
        result = self.engine.record_performance(asset_id, 'cpu_usage', 45.5)
        assert result is True
        
        result = self.engine.record_performance(asset_id, 'memory_usage', 60.0)
        assert result is True
    
    def test_record_fault(self):
        """测试记录故障"""
        asset_id = 'asset-123'
        
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        
        result = self.engine.record_fault(
            asset_id=asset_id,
            fault_type='hardware_error',
            severity='major',
            start_time=start,
            end_time=end,
        )
        assert result is True
    
    def test_calculate_uptime(self):
        """测试运行时间统计"""
        asset_id = 'asset-123'
        install_date = datetime.now() - timedelta(days=100)
        
        uptime = self.engine.calculate_uptime(asset_id, install_date)
        
        assert 'total_uptime_days' in uptime
        assert uptime['total_uptime_days'] >= 99
    
    def test_analyze_trend(self):
        """测试趋势分析"""
        asset_id = 'asset-123'
        
        # 记录一些数据
        now = datetime.now()
        for i in range(10):
            self.engine.record_performance(asset_id, 'cpu_usage', 50 + i * 2, now - timedelta(hours=10-i))
        
        trend = self.engine.analyze_trend(asset_id, 'cpu_usage', days=1)
        
        assert trend.trend in ['improving', 'stable', 'declining']
        assert trend.asset_id == asset_id
    
    def test_calculate_fault_statistics(self):
        """测试故障统计"""
        asset_id = 'asset-123'
        
        # 记录多次故障
        for i in range(3):
            self.engine.record_fault(
                asset_id=asset_id,
                fault_type='network_error',
                severity='minor',
                start_time=datetime.now() - timedelta(days=30 * (3-i)),
                end_time=datetime.now() - timedelta(days=30 * (3-i)) + timedelta(hours=2),
            )
        
        stats = self.engine.calculate_fault_statistics(asset_id, days=365)
        
        assert stats.total_faults == 3
        assert stats.mtbf_days > 0
    
    def test_predict_lifespan(self):
        """测试寿命预测"""
        asset_id = 'asset-123'
        
        # 记录一些故障
        for i in range(2):
            self.engine.record_fault(
                asset_id=asset_id,
                fault_type='hardware',
                severity='major',
                start_time=datetime.now() - timedelta(days=30 * (2-i)),
                end_time=datetime.now() - timedelta(days=30 * (2-i)) + timedelta(hours=4),
            )
        
        prediction = self.engine.predict_lifespan(asset_id, expected_lifespan_months=60)
        
        assert prediction.remaining_lifespan_months > 0
        assert prediction.eol_risk in ['low', 'medium', 'high', 'critical']
    
    def test_calculate_health_score(self):
        """测试健康度评分"""
        asset_id = 'asset-123'
        install_date = datetime.now() - timedelta(days=365)
        
        # 记录一些性能数据
        for i in range(5):
            self.engine.record_performance(asset_id, 'cpu_usage', 60 + i * 5)
        
        health = self.engine.calculate_health_score(asset_id, 60)
        
        assert 0 <= health.overall_score <= 100
        assert health.health_level in ['healthy', 'normal', 'warning', 'critical']
    
    def test_evaluate_asset(self):
        """测试综合评估"""
        asset_id = 'asset-123'
        
        # 记录数据
        for i in range(5):
            self.engine.record_performance(asset_id, 'cpu_usage', 50 + i)
        
        result = self.engine.evaluate_asset(asset_id, 60)
        
        assert 'uptime' in result
        assert 'fault_statistics' in result
        assert 'health_score' in result
        assert 'lifespan_prediction' in result


class TestRiskAssessor:
    """风险评估器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.assessor = RiskAssessor()
        self.asset = Asset(
            name='Test Server',
            category=AssetCategory.SERVER,
            warranty_expiry=datetime.now() + timedelta(days=15),
        )
    
    def test_identify_risks(self):
        """测试风险识别"""
        # 提供评估数据以触发风险识别
        health_score = {'health_level': 'warning', 'overall_score': 50}
        lifespan_prediction = {'remaining_lifespan_months': 2, 'eol_risk': 'critical'}
        
        risks = self.assessor.identify_risks(self.asset, health_score, lifespan_prediction)
        
        assert len(risks) > 0
        assert any(r.risk_category == RiskCategory.LIFECYCLE for r in risks)
    
    def test_identify_warranty_risk(self):
        """测试保修风险识别"""
        risks = self.assessor.identify_risks(self.asset)
        
        warranty_risks = [r for r in risks if r.risk_category == RiskCategory.MAINTENANCE]
        assert len(warranty_risks) > 0
    
    def test_generate_replacement_plan(self):
        """测试生成替换计划"""
        risk = RiskItem(
            asset_id=self.asset.asset_id,
            asset_name=self.asset.name,
            risk_level=RiskLevel.HIGH,
            risk_name='寿命到期',
        )
        
        plan = self.assessor.generate_replacement_plan(self.asset, risk)
        
        assert plan is not None
        assert plan.asset_id == self.asset.asset_id
        assert plan.status == 'proposed'
    
    def test_maintenance_recommendations(self):
        """测试维保建议生成"""
        # 提供健康度数据以触发维保建议
        health_score = {'health_level': 'warning', 'overall_score': 50, 'recommendations': []}
        fault_stats = {'mtbf_days': 20, 'mttr_hours': 10}
        
        recs = self.assessor.generate_maintenance_recommendations(self.asset, health_score, fault_stats)
        
        assert len(recs) > 0
    
    def test_risk_report(self):
        """测试风险报告生成"""
        report = self.assessor.generate_risk_report(self.asset)
        
        assert 'risk_summary' in report
        assert 'risks' in report
        assert report['risk_summary']['total_risks'] > 0


# 运行所有测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])