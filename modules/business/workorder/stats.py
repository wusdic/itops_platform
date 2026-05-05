"""
统计分析模块
提供工单量统计、处理时效统计、满意度统计、趋势分析、KPI报表等功能
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from sqlalchemy import func, and_, or_

from modules.foundation.db_models.workorder import (
    WorkOrder, WorkOrderType, WorkOrderStatus, WorkOrderPriority
)


class WorkOrderStats:
    """
    工单统计分析类
    
    提供工单量统计、处理时效统计、满意度统计、趋势分析、KPI报表等功能
    """
    
    def __init__(self, db_session):
        """
        初始化统计分析
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
    
    def get_workorder_count(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        order_type: Optional[WorkOrderType] = None,
        status: Optional[WorkOrderStatus] = None,
        group_by: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        获取工单数量统计
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            order_type: 工单类型
            status: 工单状态
            group_by: 分组方式: day, week, month, type, status
            
        Returns:
            统计数据列表
        """
        query = self.db.query(WorkOrder).filter(WorkOrder.is_deleted == False)
        
        if start_time:
            query = query.filter(WorkOrder.created_at >= start_time)
        if end_time:
            query = query.filter(WorkOrder.created_at <= end_time)
        if order_type:
            query = query.filter(WorkOrder.order_type == order_type)
        if status:
            query = query.filter(WorkOrder.status == status)
        
        if group_by == 'type':
            # 按类型分组
            results = self.db.query(
                WorkOrder.order_type,
                func.count(WorkOrder.id).label('count')
            ).filter(
                WorkOrder.is_deleted == False
            )
            if start_time:
                results = results.filter(WorkOrder.created_at >= start_time)
            if end_time:
                results = results.filter(WorkOrder.created_at <= end_time)
            
            return [
                {'type': r.order_type.value, 'count': r.count}
                for r in results.group_by(WorkOrder.order_type).all()
            ]
        
        elif group_by == 'status':
            # 按状态分组
            results = self.db.query(
                WorkOrder.status,
                func.count(WorkOrder.id).label('count')
            ).filter(
                WorkOrder.is_deleted == False
            )
            if start_time:
                results = results.filter(WorkOrder.created_at >= start_time)
            if end_time:
                results = results.filter(WorkOrder.created_at <= end_time)
            
            return [
                {'status': r.status.value, 'count': r.count}
                for r in results.group_by(WorkOrder.status).all()
            ]
        
        elif group_by == 'priority':
            # 按优先级分组
            results = self.db.query(
                WorkOrder.priority,
                func.count(WorkOrder.id).label('count')
            ).filter(
                WorkOrder.is_deleted == False
            )
            if start_time:
                results = results.filter(WorkOrder.created_at >= start_time)
            if end_time:
                results = results.filter(WorkOrder.created_at <= end_time)
            
            return [
                {'priority': r.priority.value, 'count': r.count}
                for r in results.group_by(WorkOrder.priority).all()
            ]
        
        else:
            # 按时间分组
            date_format = {
                'day': '%Y-%m-%d',
                'week': '%Y-%W',
                'month': '%Y-%m'
            }.get(group_by, '%Y-%m-%d')
            
            # 获取所有工单用于手动分组
            workorders = query.all()
            
            grouped = defaultdict(int)
            for wo in workorders:
                if group_by == 'day':
                    key = wo.created_at.strftime('%Y-%m-%d')
                elif group_by == 'week':
                    key = f"{wo.created_at.year}-W{wo.created_at.strftime('%W')}"
                elif group_by == 'month':
                    key = wo.created_at.strftime('%Y-%m')
                else:
                    key = wo.created_at.strftime('%Y-%m-%d')
                grouped[key] += 1
            
            return [
                {'period': k, 'count': v}
                for k, v in sorted(grouped.items())
            ]
    
    def get_processing_time_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        order_type: Optional[WorkOrderType] = None
    ) -> Dict[str, Any]:
        """
        获取处理时效统计
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            order_type: 工单类型
            
        Returns:
            处理时效统计数据
        """
        query = self.db.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.status.in_([
                WorkOrderStatus.RESOLVED.value,
                WorkOrderStatus.CLOSED.value
            ]),
            WorkOrder.actual_start.isnot(None),
            WorkOrder.actual_end.isnot(None)
        )
        
        if start_time:
            query = query.filter(WorkOrder.created_at >= start_time)
        if end_time:
            query = query.filter(WorkOrder.created_at <= end_time)
        if order_type:
            query = query.filter(WorkOrder.order_type == order_type)
        
        workorders = query.all()
        
        if not workorders:
            return {
                'count': 0,
                'avg_response_minutes': 0,
                'avg_resolve_minutes': 0,
                'max_response_minutes': 0,
                'max_resolve_minutes': 0
            }
        
        response_times = []
        resolve_times = []
        
        for wo in workorders:
            # 响应时间
            if wo.sla_response_at and wo.created_at:
                response_minutes = (wo.sla_response_at - wo.created_at).total_seconds() / 60
                response_times.append(response_minutes)
            
            # 解决时间
            if wo.actual_end and wo.created_at:
                resolve_minutes = (wo.actual_end - wo.created_at).total_seconds() / 60
                resolve_times.append(resolve_minutes)
        
        return {
            'count': len(workorders),
            'avg_response_minutes': round(sum(response_times) / len(response_times), 2) if response_times else 0,
            'avg_resolve_minutes': round(sum(resolve_times) / len(resolve_times), 2) if resolve_times else 0,
            'max_response_minutes': round(max(response_times), 2) if response_times else 0,
            'max_resolve_minutes': round(max(resolve_times), 2) if resolve_times else 0,
            'min_response_minutes': round(min(response_times), 2) if response_times else 0,
            'min_resolve_minutes': round(min(resolve_times), 2) if resolve_times else 0
        }
    
    def get_sla_compliance_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取SLA合规率统计
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            SLA合规统计数据
        """
        query = self.db.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.status.in_([
                WorkOrderStatus.RESOLVED.value,
                WorkOrderStatus.CLOSED.value
            ])
        )
        
        if start_time:
            query = query.filter(WorkOrder.created_at >= start_time)
        if end_time:
            query = query.filter(WorkOrder.created_at <= end_time)
        
        workorders = query.all()
        total = len(workorders)
        
        if total == 0:
            return {
                'total': 0,
                'response_compliant': 0,
                'resolve_compliant': 0,
                'response_rate': 0,
                'resolve_rate': 0,
                'full_compliant': 0,
                'full_rate': 0
            }
        
        response_compliant = 0
        resolve_compliant = 0
        full_compliant = 0
        
        for wo in workorders:
            response_ok = False
            resolve_ok = False
            
            # 检查响应SLA
            if wo.sla_response_at and wo.sla_response_time:
                response_deadline = wo.created_at + timedelta(minutes=wo.sla_response_time)
                response_ok = wo.sla_response_at <= response_deadline
            
            # 检查解决SLA
            if wo.sla_resolved_at and wo.sla_resolve_time:
                resolve_deadline = wo.created_at + timedelta(minutes=wo.sla_resolve_time)
                resolve_ok = wo.sla_resolved_at <= resolve_deadline
            
            if response_ok:
                response_compliant += 1
            if resolve_ok:
                resolve_compliant += 1
            if response_ok and resolve_ok:
                full_compliant += 1
        
        return {
            'total': total,
            'response_compliant': response_compliant,
            'resolve_compliant': resolve_compliant,
            'response_rate': round(response_compliant / total * 100, 2),
            'resolve_rate': round(resolve_compliant / total * 100, 2),
            'full_compliant': full_compliant,
            'full_rate': round(full_compliant / total * 100, 2)
        }
    
    def get_satisfaction_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取满意度统计
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            满意度统计数据
        """
        query = self.db.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.satisfaction.isnot(None)
        )
        
        if start_time:
            query = query.filter(WorkOrder.created_at >= start_time)
        if end_time:
            query = query.filter(WorkOrder.created_at <= end_time)
        
        workorders = query.all()
        total = len(workorders)
        
        if total == 0:
            return {
                'total': 0,
                'avg_satisfaction': 0,
                'satisfaction_distribution': {}
            }
        
        scores = [wo.satisfaction for wo in workorders if wo.satisfaction]
        distribution = defaultdict(int)
        
        for score in scores:
            distribution[f'P{score}'] += 1
        
        return {
            'total': total,
            'avg_satisfaction': round(sum(scores) / len(scores), 2) if scores else 0,
            'satisfaction_distribution': dict(distribution),
            'satisfaction_rate': round(
                (scores.count(5) + scores.count(4)) / len(scores) * 100, 2
            ) if scores else 0
        }
    
    def get_assignee_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        获取处理人工作量统计
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            处理人统计数据
        """
        results = self.db.query(
            WorkOrder.assignee,
            func.count(WorkOrder.id).label('total'),
            func.sum(
                func.case(
                    (WorkOrder.status == WorkOrderStatus.RESOLVED, 1),
                    (WorkOrder.status == WorkOrderStatus.CLOSED, 1),
                    else_=0
                )
            ).label('completed')
        ).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.assignee.isnot(None)
        )
        
        if start_time:
            results = results.filter(WorkOrder.created_at >= start_time)
        if end_time:
            results = results.filter(WorkOrder.created_at <= end_time)
        
        stats = results.group_by(WorkOrder.assignee).all()
        
        return [
            {
                'assignee': s.assignee,
                'total': s.total,
                'completed': s.completed or 0,
                'completion_rate': round((s.completed or 0) / s.total * 100, 2)
            }
            for s in stats
        ]
    
    def get_trend_analysis(
        self,
        metric: str = 'count',
        period: str = 'week',
        periods: int = 12
    ) -> List[Dict[str, Any]]:
        """
        获取趋势分析数据
        
        Args:
            metric: 指标类型: count, response_time, resolve_time, satisfaction
            period: 时间周期: day, week, month
            periods: 历史周期数
            
        Returns:
            趋势数据列表
        """
        end_time = datetime.now()
        
        if period == 'day':
            start_time = end_time - timedelta(days=periods)
            date_format = '%Y-%m-%d'
        elif period == 'week':
            start_time = end_time - timedelta(weeks=periods)
            date_format = '%Y-W%W'
        else:  # month
            start_time = end_time - timedelta(days=periods * 30)
            date_format = '%Y-%m'
        
        query = self.db.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.created_at >= start_time,
            WorkOrder.created_at <= end_time
        )
        
        workorders = query.all()
        
        # 按时间段分组统计
        grouped = defaultdict(lambda: {'count': 0, 'response_total': 0, 'resolve_total': 0, 'satisfaction_total': 0, 'satisfaction_count': 0})
        
        for wo in workorders:
            if period == 'day':
                key = wo.created_at.strftime('%Y-%m-%d')
            elif period == 'week':
                key = f"{wo.created_at.year}-W{wo.created_at.strftime('%W')}"
            else:
                key = wo.created_at.strftime('%Y-%m')
            
            grouped[key]['count'] += 1
            
            if wo.sla_response_at and wo.created_at:
                grouped[key]['response_total'] += (wo.sla_response_at - wo.created_at).total_seconds() / 60
            
            if wo.actual_end and wo.created_at:
                grouped[key]['resolve_total'] += (wo.actual_end - wo.created_at).total_seconds() / 60
            
            if wo.satisfaction:
                grouped[key]['satisfaction_total'] += wo.satisfaction
                grouped[key]['satisfaction_count'] += 1
        
        trend_data = []
        for period_key in sorted(grouped.keys()):
            data = grouped[period_key]
            item = {
                'period': period_key,
                'count': data['count']
            }
            
            if data['count'] > 0:
                item['avg_response_time'] = round(data['response_total'] / data['count'], 2)
                item['avg_resolve_time'] = round(data['resolve_total'] / data['count'], 2)
            
            if data['satisfaction_count'] > 0:
                item['avg_satisfaction'] = round(data['satisfaction_total'] / data['satisfaction_count'], 2)
            
            trend_data.append(item)
        
        return trend_data
    
    def get_kpi_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取KPI报表
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            KPI报表数据
        """
        if not start_time:
            start_time = datetime.now() - timedelta(days=30)
        if not end_time:
            end_time = datetime.now()
        
        # 工单量统计
        total_count = self.db.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.created_at >= start_time,
            WorkOrder.created_at <= end_time
        ).count()
        
        # 状态统计
        status_counts = {}
        for status in WorkOrderStatus:
            count = self.db.query(WorkOrder).filter(
                WorkOrder.is_deleted == False,
                WorkOrder.status == status,
                WorkOrder.created_at >= start_time,
                WorkOrder.created_at <= end_time
            ).count()
            status_counts[status.value] = count
        
        # 类型统计
        type_counts = {}
        for order_type in WorkOrderType:
            count = self.db.query(WorkOrder).filter(
                WorkOrder.is_deleted == False,
                WorkOrder.order_type == order_type,
                WorkOrder.created_at >= start_time,
                WorkOrder.created_at <= end_time
            ).count()
            type_counts[order_type.value] = count
        
        # SLA合规率
        sla_stats = self.get_sla_compliance_stats(start_time, end_time)
        
        # 处理时效
        time_stats = self.get_processing_time_stats(start_time, end_time)
        
        # 满意度
        satisfaction_stats = self.get_satisfaction_stats(start_time, end_time)
        
        # 环比变化(与上一周期相比)
        period_days = (end_time - start_time).days
        prev_start = start_time - timedelta(days=period_days)
        prev_end = start_time
        
        prev_count = self.db.query(WorkOrder).filter(
            WorkOrder.is_deleted == False,
            WorkOrder.created_at >= prev_start,
            WorkOrder.created_at < prev_end
        ).count()
        
        chain_change = 0
        if prev_count > 0:
            chain_change = round((total_count - prev_count) / prev_count * 100, 2)
        
        return {
            'report_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'days': period_days
            },
            'total_workorders': total_count,
            'status_distribution': status_counts,
            'type_distribution': type_counts,
            'sla_compliance': {
                'response_rate': sla_stats['response_rate'],
                'resolve_rate': sla_stats['resolve_rate'],
                'full_rate': sla_stats['full_rate']
            },
            'processing_efficiency': {
                'avg_response_minutes': time_stats['avg_response_minutes'],
                'avg_resolve_minutes': time_stats['avg_resolve_minutes'],
                'avg_resolve_hours': round(time_stats['avg_resolve_minutes'] / 60, 2)
            },
            'satisfaction': {
                'avg_score': satisfaction_stats['avg_satisfaction'],
                'satisfaction_rate': satisfaction_stats['satisfaction_rate']
            },
            'chain_comparison': {
                'prev_period_count': prev_count,
                'current_count': total_count,
                'change_rate': chain_change
            }
        }
    
    def get_category_breakdown(
        self,
        category: str = 'type',
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取分类统计排行
        
        Args:
            category: 分类维度: type, priority, assignee, device
            top_n: 返回前N条
            
        Returns:
            分类统计数据
        """
        if category == 'type':
            results = self.db.query(
                WorkOrder.order_type,
                func.count(WorkOrder.id).label('count')
            ).filter(
                WorkOrder.is_deleted == False
            ).group_by(WorkOrder.order_type).order_by(
                func.count(WorkOrder.id).desc()
            ).limit(top_n).all()
            
            return [
                {'name': r.order_type.value, 'count': r.count}
                for r in results
            ]
        
        elif category == 'priority':
            results = self.db.query(
                WorkOrder.priority,
                func.count(WorkOrder.id).label('count')
            ).filter(
                WorkOrder.is_deleted == False
            ).group_by(WorkOrder.priority).order_by(
                func.count(WorkOrder.id).desc()
            ).limit(top_n).all()
            
            return [
                {'name': r.priority.value, 'count': r.count}
                for r in results
            ]
        
        elif category == 'assignee':
            results = self.db.query(
                WorkOrder.assignee,
                func.count(WorkOrder.id).label('count')
            ).filter(
                WorkOrder.is_deleted == False,
                WorkOrder.assignee.isnot(None)
            ).group_by(WorkOrder.assignee).order_by(
                func.count(WorkOrder.id).desc()
            ).limit(top_n).all()
            
            return [
                {'name': r.assignee, 'count': r.count}
                for r in results
            ]
        
        elif category == 'device':
            results = self.db.query(
                WorkOrder.device_name,
                func.count(WorkOrder.id).label('count')
            ).filter(
                WorkOrder.is_deleted == False,
                WorkOrder.device_name.isnot(None)
            ).group_by(WorkOrder.device_name).order_by(
                func.count(WorkOrder.id).desc()
            ).limit(top_n).all()
            
            return [
                {'name': r.device_name, 'count': r.count}
                for r in results
            ]
        
        return []
