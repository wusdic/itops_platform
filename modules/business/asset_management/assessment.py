"""
寿命评估模块
提供运行时间统计、性能趋势分析、故障率统计、寿命预测、健康度评分等功能
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


@dataclass
class HealthScore:
    """健康度评分"""
    asset_id: str = ''
    overall_score: float = 100.0  # 0-100
    
    # 各维度评分
    performance_score: float = 100.0
    reliability_score: float = 100.0
    maintenance_score: float = 100.0
    age_score: float = 100.0
    
    # 详细指标
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # 健康等级
    health_level: str = 'healthy'  # healthy, normal, warning, critical
    
    # 评分时间
    evaluated_at: datetime = field(default_factory=datetime.now)
    
    # 建议
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'asset_id': self.asset_id,
            'overall_score': self.overall_score,
            'performance_score': self.performance_score,
            'reliability_score': self.reliability_score,
            'maintenance_score': self.maintenance_score,
            'age_score': self.age_score,
            'metrics': self.metrics,
            'health_level': self.health_level,
            'evaluated_at': self.evaluated_at.isoformat(),
            'recommendations': self.recommendations,
        }


@dataclass
class LifespanPrediction:
    """寿命预测结果"""
    asset_id: str = ''
    
    # 预测信息
    predicted_eol: Optional[datetime] = None  # End of Life
    predicted_replacement_date: Optional[datetime] = None
    remaining_lifespan_days: int = 0
    remaining_lifespan_months: float = 0.0
    
    # 置信度
    confidence: float = 0.0  # 0-100
    
    # 预测方法
    method: str = 'historical'  # historical, statistical, ml
    
    # 关键因素
    key_factors: List[str] = field(default_factory=list)
    
    # 风险指标
    eol_risk: str = 'low'  # low, medium, high, critical
    
    # 预测时间
    predicted_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'asset_id': self.asset_id,
            'predicted_eol': self.predicted_eol.isoformat() if self.predicted_eol else None,
            'predicted_replacement_date': self.predicted_replacement_date.isoformat() if self.predicted_replacement_date else None,
            'remaining_lifespan_days': self.remaining_lifespan_days,
            'remaining_lifespan_months': self.remaining_lifespan_months,
            'confidence': self.confidence,
            'method': self.method,
            'key_factors': self.key_factors,
            'eol_risk': self.eol_risk,
            'predicted_at': self.predicted_at.isoformat(),
        }


@dataclass
class PerformanceTrend:
    """性能趋势数据"""
    asset_id: str = ''
    metric_name: str = ''
    
    # 趋势分析
    trend: str = 'stable'  # improving, stable, declining
    change_rate: float = 0.0  # 变化率百分比
    
    # 统计值
    current_value: float = 0.0
    avg_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    std_dev: float = 0.0
    
    # 预测
    predicted_value: Optional[float] = None
    
    # 时间范围
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'asset_id': self.asset_id,
            'metric_name': self.metric_name,
            'trend': self.trend,
            'change_rate': self.change_rate,
            'current_value': self.current_value,
            'avg_value': self.avg_value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'std_dev': self.std_dev,
            'predicted_value': self.predicted_value,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
        }


@dataclass
class FaultStatistics:
    """故障统计"""
    asset_id: str = ''
    
    # 故障计数
    total_faults: int = 0
    critical_faults: int = 0
    major_faults: int = 0
    minor_faults: int = 0
    
    # MTBF (Mean Time Between Failures)
    mtbf_days: float = 0.0  # 平均故障间隔时间
    
    # MTTR (Mean Time To Repair)
    mttr_hours: float = 0.0  # 平均修复时间
    
    # 可用性
    availability: float = 100.0  # 可用性百分比
    
    # 故障类型分布
    fault_type_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 故障趋势
    fault_trend: str = 'stable'  # improving, stable, worsening
    
    # 统计周期
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'asset_id': self.asset_id,
            'total_faults': self.total_faults,
            'critical_faults': self.critical_faults,
            'major_faults': self.major_faults,
            'minor_faults': self.minor_faults,
            'mtbf_days': self.mtbf_days,
            'mttr_hours': self.mttr_hours,
            'availability': self.availability,
            'fault_type_distribution': self.fault_type_distribution,
            'fault_trend': self.fault_trend,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
        }


class AssessmentEngine:
    """评估引擎"""
    
    def __init__(self):
        # 历史性能数据 (asset_id -> {metric_name -> [(timestamp, value)]})
        self.performance_data: Dict[str, Dict[str, List[Tuple[datetime, float]]]] = defaultdict(lambda: defaultdict(list))
        
        # 故障记录 (asset_id -> [FaultRecord])
        self.fault_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 健康度缓存
        self.health_scores: Dict[str, HealthScore] = {}
        
        # 预测缓存
        self.predictions: Dict[str, LifespanPrediction] = {}
    
    # ==================== 数据管理 ====================
    
    def record_performance(self, asset_id: str, metric_name: str, value: float, 
                          timestamp: Optional[datetime] = None) -> bool:
        """记录性能数据"""
        try:
            ts = timestamp or datetime.now()
            self.performance_data[asset_id][metric_name].append((ts, value))
            # 清理过期数据（保留最近2年）
            cutoff = datetime.now() - timedelta(days=730)
            self.performance_data[asset_id][metric_name] = [
                (t, v) for t, v in self.performance_data[asset_id][metric_name] if t > cutoff
            ]
            return True
        except Exception as e:
            logger.error(f"Failed to record performance: {e}")
            return False
    
    def record_fault(self, asset_id: str, fault_type: str, severity: str, 
                    start_time: datetime, end_time: Optional[datetime] = None,
                    description: str = '') -> bool:
        """记录故障"""
        try:
            record = {
                'fault_type': fault_type,
                'severity': severity,
                'start_time': start_time,
                'end_time': end_time,
                'duration_hours': (end_time - start_time).total_seconds() / 3600 if end_time else None,
                'description': description,
            }
            self.fault_records[asset_id].append(record)
            return True
        except Exception as e:
            logger.error(f"Failed to record fault: {e}")
            return False
    
    def get_performance_data(self, asset_id: str, metric_name: str, 
                            days: int = 30) -> List[Tuple[datetime, float]]:
        """获取性能数据"""
        cutoff = datetime.now() - timedelta(days=days)
        data = self.performance_data.get(asset_id, {}).get(metric_name, [])
        return [(t, v) for t, v in data if t > cutoff]
    
    # ==================== 运行时间统计 ====================
    
    def calculate_uptime(self, asset_id: str, asset_install_date: Optional[datetime] = None) -> Dict[str, Any]:
        """计算运行时间统计"""
        install_date = asset_install_date or datetime.now()
        uptime = datetime.now() - install_date
        
        # 获取停机记录
        fault_records = self.fault_records.get(asset_id, [])
        total_downtime = sum(
            r.get('duration_hours', 0) or 0 
            for r in fault_records 
            if r.get('end_time') and r.get('start_time')
        )
        
        total_hours = uptime.total_seconds() / 3600
        uptime_hours = total_hours - total_downtime
        uptime_percentage = (uptime_hours / total_hours * 100) if total_hours > 0 else 100.0
        
        return {
            'asset_id': asset_id,
            'install_date': install_date,
            'total_uptime_days': uptime.days,
            'total_uptime_hours': uptime_hours,
            'total_downtime_hours': total_downtime,
            'uptime_percentage': round(uptime_percentage, 2),
            'last_boot_time': self._get_last_boot_time(asset_id),
            'statistics_period_days': (datetime.now() - install_date).days,
        }
    
    def _get_last_boot_time(self, asset_id: str) -> Optional[datetime]:
        """获取最近启动时间"""
        records = self.fault_records.get(asset_id, [])
        if records:
            # 假设最后修复完成后的时间就是启动时间
            for record in reversed(records):
                if record.get('end_time'):
                    return record['end_time']
        return None
    
    # ==================== 性能趋势分析 ====================
    
    def analyze_trend(self, asset_id: str, metric_name: str, days: int = 30) -> PerformanceTrend:
        """分析性能趋势"""
        data = self.get_performance_data(asset_id, metric_name, days)
        
        if not data:
            return PerformanceTrend(asset_id=asset_id, metric_name=metric_name)
        
        timestamps, values = zip(*data)
        
        # 计算统计值
        current_value = values[-1] if values else 0.0
        avg_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)
        
        # 计算标准差
        variance = sum((v - avg_value) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        
        # 计算趋势 (简单线性回归)
        if len(values) >= 2:
            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = avg_value
            
            numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            if denominator != 0:
                slope = numerator / denominator
                # 趋势判断
                if slope > avg_value * 0.01:
                    trend = 'improving'
                elif slope < -avg_value * 0.01:
                    trend = 'declining'
                else:
                    trend = 'stable'
                
                change_rate = (slope / avg_value * 100) if avg_value != 0 else 0.0
                
                # 预测下一个值
                predicted_value = current_value + slope
            else:
                trend = 'stable'
                change_rate = 0.0
                predicted_value = current_value
        else:
            trend = 'stable'
            change_rate = 0.0
            predicted_value = current_value
        
        return PerformanceTrend(
            asset_id=asset_id,
            metric_name=metric_name,
            trend=trend,
            change_rate=round(change_rate, 2),
            current_value=current_value,
            avg_value=round(avg_value, 2),
            min_value=min_value,
            max_value=max_value,
            std_dev=round(std_dev, 2),
            predicted_value=round(predicted_value, 2),
            period_start=min(timestamps),
            period_end=max(timestamps),
        )
    
    def analyze_all_trends(self, asset_id: str, days: int = 30) -> Dict[str, PerformanceTrend]:
        """分析所有指标趋势"""
        trends = {}
        metrics_data = self.performance_data.get(asset_id, {})
        for metric_name in metrics_data.keys():
            trends[metric_name] = self.analyze_trend(asset_id, metric_name, days)
        return trends
    
    # ==================== 故障率统计 ====================
    
    def calculate_fault_statistics(self, asset_id: str, days: int = 365) -> FaultStatistics:
        """计算故障统计"""
        cutoff = datetime.now() - timedelta(days=days)
        records = [r for r in self.fault_records.get(asset_id, []) 
                  if r.get('start_time', datetime.min) > cutoff]
        
        if not records:
            return FaultStatistics(asset_id=asset_id, period_start=cutoff, period_end=datetime.now())
        
        # 统计故障数
        total_faults = len(records)
        critical_faults = len([r for r in records if r.get('severity') == 'critical'])
        major_faults = len([r for r in records if r.get('severity') == 'major'])
        minor_faults = len([r for r in records if r.get('severity') in ['minor', 'warning']])
        
        # 故障类型分布
        fault_type_distribution = defaultdict(int)
        for r in records:
            fault_type_distribution[r.get('fault_type', 'unknown')] += 1
        
        # 计算MTTR
        repair_times = [r.get('duration_hours', 0) or 0 for r in records if r.get('end_time')]
        mttr_hours = sum(repair_times) / len(repair_times) if repair_times else 0.0
        
        # 计算MTBF
        if total_faults > 1:
            # 排序故障记录
            sorted_records = sorted(records, key=lambda x: x.get('start_time', datetime.min))
            intervals = []
            for i in range(1, len(sorted_records)):
                interval = (sorted_records[i]['start_time'] - sorted_records[i-1]['start_time']).days
                intervals.append(interval)
            mtbf_days = sum(intervals) / len(intervals)
        else:
            # 没有故障或只有一个故障，使用运行时间
            mtbf_days = days * 0.9  # 估算
        
        # 计算可用性 (基于MTBF和MTTR)
        total_time = days * 24
        uptime = total_time - sum(repair_times)
        availability = (uptime / total_time * 100) if total_time > 0 else 100.0
        
        # 故障趋势
        fault_trend = self._calculate_fault_trend(records)
        
        return FaultStatistics(
            asset_id=asset_id,
            total_faults=total_faults,
            critical_faults=critical_faults,
            major_faults=major_faults,
            minor_faults=minor_faults,
            mtbf_days=round(mtbf_days, 2),
            mttr_hours=round(mttr_hours, 2),
            availability=round(availability, 2),
            fault_type_distribution=dict(fault_type_distribution),
            fault_trend=fault_trend,
            period_start=cutoff,
            period_end=datetime.now(),
        )
    
    def _calculate_fault_trend(self, records: List[Dict[str, Any]]) -> str:
        """计算故障趋势"""
        if len(records) < 2:
            return 'stable'
        
        # 将记录分为前后两半，比较故障率
        sorted_records = sorted(records, key=lambda x: x.get('start_time', datetime.min))
        mid = len(sorted_records) // 2
        
        if mid == 0:
            return 'stable'
        
        first_half = sorted_records[:mid]
        second_half = sorted_records[mid:]
        
        # 检查趋势
        if len(second_half) < len(first_half) * 0.5:
            return 'improving'
        elif len(second_half) > len(first_half) * 1.5:
            return 'worsening'
        else:
            return 'stable'
    
    # ==================== 寿命预测 ====================
    
    def predict_lifespan(self, asset_id: str, expected_lifespan_months: int = 60,
                        fault_stats: Optional[FaultStatistics] = None) -> LifespanPrediction:
        """预测资产寿命"""
        # 使用故障统计调整预测
        if fault_stats is None:
            fault_stats = self.calculate_fault_statistics(asset_id)
        
        now = datetime.now()
        
        # 基础预测：预期寿命
        remaining_months = expected_lifespan_months
        key_factors = ['预期使用寿命']
        
        # 故障率调整
        if fault_stats.mtbf_days > 0:
            # MTBF越低，寿命越短
            expected_lifetime_days = fault_stats.mtbf_days * 10  # 估算
            expected_lifetime_months = expected_lifetime_days / 30
            if expected_lifetime_months < remaining_months:
                remaining_months = expected_lifetime_months
                key_factors.append(f'MTBF {fault_stats.mtbf_days}天')
        
        # 故障趋势调整
        if fault_stats.fault_trend == 'worsening':
            remaining_months *= 0.7
            key_factors.append('故障率上升')
        elif fault_stats.fault_trend == 'improving':
            remaining_months *= 1.2
            key_factors.append('故障率下降')
        
        # 关键故障调整
        if fault_stats.critical_faults > 0:
            remaining_months *= 0.8
            key_factors.append(f'关键故障 {fault_stats.critical_faults}次')
        
        remaining_months = max(remaining_months, 1)  # 至少1个月
        remaining_days = int(remaining_months * 30)
        predicted_eol = now + timedelta(days=remaining_days)
        predicted_replacement = predicted_eol - timedelta(days=90)  # 提前3个月建议更换
        
        # 计算风险等级
        if remaining_months < 3:
            eol_risk = 'critical'
        elif remaining_months < 6:
            eol_risk = 'high'
        elif remaining_months < 12:
            eol_risk = 'medium'
        else:
            eol_risk = 'low'
        
        # 置信度
        confidence = 70.0
        if fault_stats.total_faults > 5:
            confidence += 10
        if fault_stats.period_start:
            data_days = (now - fault_stats.period_start).days
            if data_days > 180:
                confidence += 15
        
        return LifespanPrediction(
            asset_id=asset_id,
            predicted_eol=predicted_eol,
            predicted_replacement_date=predicted_replacement,
            remaining_lifespan_days=remaining_days,
            remaining_lifespan_months=round(remaining_months, 1),
            confidence=min(confidence, 95),
            method='historical',
            key_factors=key_factors,
            eol_risk=eol_risk,
        )
    
    # ==================== 健康度评分 ====================
    
    def calculate_health_score(self, asset_id: str, expected_lifespan_months: int = 60,
                              uptime_info: Optional[Dict] = None,
                              fault_stats: Optional[FaultStatistics] = None,
                              trends: Optional[Dict[str, PerformanceTrend]] = None) -> HealthScore:
        """计算健康度评分"""
        now = datetime.now()
        recommendations = []
        
        # 1. 年龄评分 (30%)
        age_score = 100.0
        if uptime_info:
            uptime_days = uptime_info.get('total_uptime_days', 0)
            expected_days = expected_lifespan_months * 30
            age_ratio = uptime_days / expected_days if expected_days > 0 else 0
            age_score = max(0, 100 - age_ratio * 100)
            
            if age_ratio > 0.8:
                recommendations.append('资产接近预期使用寿命，建议计划更换')
        
        # 2. 可靠性评分 (30%)
        reliability_score = 100.0
        if fault_stats:
            # 基于MTBF评分
            if fault_stats.mtbf_days > 0:
                # 期望MTBF = 预期寿命，MTBF越接近预期寿命，可靠性越高
                expected_mtbf = expected_lifespan_months * 30
                mtbf_ratio = fault_stats.mtbf_days / expected_mtbf if expected_mtbf > 0 else 1
                reliability_score = min(100, mtbf_ratio * 100)
            
            # 关键故障扣分
            reliability_score -= fault_stats.critical_faults * 20
            reliability_score -= fault_stats.major_faults * 10
            
            if reliability_score < 50:
                recommendations.append('故障率较高，建议进行全面检查')
        
        reliability_score = max(0, reliability_score)
        
        # 3. 维保评分 (20%)
        maintenance_score = 100.0
        if fault_stats:
            # 基于MTTR评分
            if fault_stats.mttr_hours > 0:
                # MTTR越低越好
                if fault_stats.mttr_hours > 24:
                    maintenance_score = 50
                elif fault_stats.mttr_hours > 8:
                    maintenance_score = 75
                elif fault_stats.mttr_hours > 4:
                    maintenance_score = 90
        
        # 4. 性能评分 (20%)
        performance_score = 100.0
        if trends:
            declining_count = sum(1 for t in trends.values() if t.trend == 'declining')
            if declining_count > 0:
                performance_score -= declining_count * 10
                recommendations.append('部分性能指标呈下降趋势')
        
        performance_score = max(0, performance_score)
        
        # 综合评分
        overall_score = (
            age_score * 0.30 +
            reliability_score * 0.30 +
            maintenance_score * 0.20 +
            performance_score * 0.20
        )
        
        # 健康等级
        if overall_score >= 80:
            health_level = 'healthy'
        elif overall_score >= 60:
            health_level = 'normal'
        elif overall_score >= 40:
            health_level = 'warning'
        else:
            health_level = 'critical'
            recommendations.insert(0, '资产健康度严重下降，建议立即安排更换或大修')
        
        return HealthScore(
            asset_id=asset_id,
            overall_score=round(overall_score, 1),
            performance_score=round(performance_score, 1),
            reliability_score=round(reliability_score, 1),
            maintenance_score=round(maintenance_score, 1),
            age_score=round(age_score, 1),
            metrics={
                'uptime_percentage': uptime_info.get('uptime_percentage', 100) if uptime_info else 100,
                'mtbf_days': fault_stats.mtbf_days if fault_stats else 0,
                'mttr_hours': fault_stats.mttr_hours if fault_stats else 0,
                'total_faults': fault_stats.total_faults if fault_stats else 0,
            },
            health_level=health_level,
            evaluated_at=now,
            recommendations=recommendations,
        )
    
    def evaluate_asset(self, asset_id: str, expected_lifespan_months: int = 60) -> Dict[str, Any]:
        """综合评估资产"""
        # 获取各项指标
        uptime_info = self.calculate_uptime(asset_id)
        fault_stats = self.calculate_fault_statistics(asset_id)
        trends = self.analyze_all_trends(asset_id)
        health_score = self.calculate_health_score(
            asset_id, expected_lifespan_months, uptime_info, fault_stats, trends
        )
        lifespan_pred = self.predict_lifespan(asset_id, expected_lifespan_months, fault_stats)
        
        return {
            'asset_id': asset_id,
            'evaluated_at': datetime.now(),
            'uptime': uptime_info,
            'fault_statistics': fault_stats.to_dict(),
            'performance_trends': {k: v.to_dict() for k, v in trends.items()},
            'health_score': health_score.to_dict(),
            'lifespan_prediction': lifespan_pred.to_dict(),
        }
