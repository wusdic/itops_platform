"""
BM-06 资产管理模块
提供资产台账、生命周期管理、寿命评估、风险评估等功能
"""

from .asset import Asset, AssetCategory, AssetStatus, AssetRelation, AssetManager
from .lifecycle import LifecycleManager, LifecycleEvent, PurchaseRecord, MaintenanceRecord
from .assessment import AssessmentEngine, HealthScore, LifespanPrediction
from .risk import RiskAssessor, RiskLevel, RiskItem, ReplacementPlan

__all__ = [
    'Asset', 'AssetCategory', 'AssetStatus', 'AssetRelation', 'AssetManager',
    'LifecycleManager', 'LifecycleEvent', 'PurchaseRecord', 'MaintenanceRecord',
    'AssessmentEngine', 'HealthScore', 'LifespanPrediction',
    'RiskAssessor', 'RiskLevel', 'RiskItem', 'ReplacementPlan',
]
__version__ = '1.0.0'
