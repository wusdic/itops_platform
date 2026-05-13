"""
巡检报告自动生成模块
基于设备巡检结果自动生成巡检报告
"""

import io
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

# 尝试导入可选依赖
try:
    from weasyprint import HTML as WeasyHTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


class InspectionReportGenerator:
    """
    巡检报告生成器
    
    基于设备巡检结果，自动生成包含以下内容的巡检报告：
    - 设备健康度评分
    - 异常统计
    - 建议措施
    - 历史对比
    """
    
    # 巡检状态映射
    STATUS_MAP = {
        'ok': '正常',
        'normal': '正常',
        'warning': '警告',
        'critical': '严重',
        'error': '错误',
        'pending': '待检查',
        'running': '检查中',
    }
    
    # 严重程度颜色
    SEVERITY_COLORS = {
        'info': '#1890ff',
        'ok': '#52c41a',
        'warning': '#faad14',
        'critical': '#ff4d4f',
        'error': '#ff4d4f',
    }
    
    # 健康度评分等级
    HEALTH_LEVELS = [
        (90, '优秀', '#52c41a'),
        (80, '良好', '#73d13d'),
        (70, '一般', '#faad14'),
        (60, '较差', '#ff7a45'),
        (0, '危险', '#ff4d4f'),
    ]
    
    def __init__(self, db_session: Session = None):
        """
        初始化巡检报告生成器
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self._report_data = {}
        self._task_info = {}
        self._device_results = {}
        self._statistics = {}
        self._suggestions = []
        self._history_comparison = {}
    
    def generate_report(self, inspection_task_id: int) -> Dict[str, Any]:
        """
        生成巡检报告
        
        Args:
            inspection_task_id: 巡检任务ID
            
        Returns:
            包含报告数据的字典
        """
        logger.info(f"Generating inspection report for task {inspection_task_id}")
        
        # 获取任务信息
        self._load_task_info(inspection_task_id)
        
        # 加载巡检结果
        self._load_inspection_results(inspection_task_id)
        
        # 计算统计数据
        self._calculate_statistics()
        
        # 生成建议措施
        self._generate_suggestions()
        
        # 获取历史对比
        self._load_history_comparison()
        
        # 组装报告数据
        report_data = self._assemble_report()
        
        logger.info(f"Inspection report generated successfully for task {inspection_task_id}")
        return report_data
    
    def _load_task_info(self, task_id: int):
        """加载任务信息"""
        from modules.foundation.db_models.inspection import InspectionTask
        
        task = self.db.query(InspectionTask).filter(
            InspectionTask.id == task_id
        ).first()
        
        if not task:
            raise ValueError(f"Inspection task {task_id} not found")
        
        self._task_info = {
            'id': task.id,
            'task_no': task.task_no,
            'name': task.name,
            'description': task.description,
            'inspection_type': task.inspection_type,
            'status': task.status,
            'progress': task.progress,
            'total_items': task.total_items,
            'completed_items': task.completed_items,
            'total_devices': task.total_devices,
            'healthy_devices': task.healthy_devices,
            'warning_devices': task.warning_devices,
            'critical_devices': task.critical_devices,
            'offline_devices': task.offline_devices,
            'health_score': task.health_score,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'executor': task.executor,
            'created_at': task.created_at.isoformat() if task.created_at else None,
        }
    
    def _load_inspection_results(self, task_id: int):
        """加载巡检结果"""
        from modules.foundation.db_models.inspection import InspectionResult
        
        results = self.db.query(InspectionResult).filter(
            InspectionResult.task_id == task_id
        ).all()
        
        # 按设备分组
        self._device_results = {}
        for result in results:
            device_key = f"{result.device_id}_{result.device_ip}"
            if device_key not in self._device_results:
                self._device_results[device_key] = {
                    'device_id': result.device_id,
                    'device_name': result.device_name,
                    'device_ip': result.device_ip,
                    'device_type': result.device_type,
                    'items': [],
                    'status_counts': {'ok': 0, 'warning': 0, 'critical': 0, 'error': 0},
                }
            
            self._device_results[device_key]['items'].append({
                'check_item_id': result.check_item_id,
                'check_item_name': result.check_item_name,
                'check_category': result.check_category,
                'status': result.status,
                'result_value': result.result_value,
                'result_message': result.result_message,
                'expected_value': result.expected_value,
                'severity': result.severity,
                'suggestion': result.suggestion,
                'checked_at': result.checked_at.isoformat() if result.checked_at else None,
            })
            
            # 统计状态计数
            status = result.status or 'ok'
            if status in self._device_results[device_key]['status_counts']:
                self._device_results[device_key]['status_counts'][status] += 1
    
    def _calculate_statistics(self):
        """计算统计数据"""
        total_devices = len(self._device_results)
        
        status_summary = {
            'total': total_devices,
            'healthy': 0,
            'warning': 0,
            'critical': 0,
            'offline': 0,
        }
        
        category_stats = {}
        check_item_stats = {}
        
        for device_key, device_data in self._device_results.items():
            # 计算设备健康状态
            critical_count = device_data['status_counts'].get('critical', 0)
            warning_count = device_data['status_counts'].get('warning', 0)
            error_count = device_data['status_counts'].get('error', 0)
            
            if critical_count > 0 or error_count > 0:
                status_summary['critical'] += 1
            elif warning_count > 0:
                status_summary['warning'] += 1
            else:
                status_summary['healthy'] += 1
            
            # 按分类统计
            for item in device_data['items']:
                category = item.get('check_category', 'other')
                if category not in category_stats:
                    category_stats[category] = {'total': 0, 'ok': 0, 'warning': 0, 'critical': 0}
                
                category_stats[category]['total'] += 1
                status = item.get('status', 'ok')
                if status in category_stats[category]:
                    category_stats[category][status] += 1
                
                # 检查项统计
                item_name = item.get('check_item_name', 'unknown')
                if item_name not in check_item_stats:
                    check_item_stats[item_name] = {'total': 0, 'ok': 0, 'warning': 0, 'critical': 0}
                check_item_stats[item_name]['total'] += 1
                if status in check_item_stats[item_name]:
                    check_item_stats[item_name][status] += 1
        
        self._statistics = {
            'status_summary': status_summary,
            'category_stats': category_stats,
            'check_item_stats': check_item_stats,
            'total_check_items': sum(1 for d in self._device_results.values() for _ in d['items']),
        }
    
    def _generate_suggestions(self):
        """生成建议措施"""
        self._suggestions = []
        
        # 按设备生成建议
        for device_key, device_data in self._device_results.items():
            critical_items = []
            warning_items = []
            
            for item in device_data['items']:
                status = item.get('status', 'ok')
                if status == 'critical' or status == 'error':
                    critical_items.append(item)
                elif status == 'warning':
                    warning_items.append(item)
            
            # 严重问题优先
            if critical_items:
                suggestion = {
                    'device_name': device_data['device_name'],
                    'device_ip': device_data['device_ip'],
                    'priority': 'critical',
                    'issues': [
                        {
                            'check_item': item['check_item_name'],
                            'message': item.get('result_message', ''),
                            'value': item.get('result_value', ''),
                            'suggestion': item.get('suggestion', '请立即处理'),
                        }
                        for item in critical_items
                    ]
                }
                self._suggestions.append(suggestion)
            
            # 然后是警告
            if warning_items:
                suggestion = {
                    'device_name': device_data['device_name'],
                    'device_ip': device_data['device_ip'],
                    'priority': 'warning',
                    'issues': [
                        {
                            'check_item': item['check_item_name'],
                            'message': item.get('result_message', ''),
                            'value': item.get('result_value', ''),
                            'suggestion': item.get('suggestion', '建议关注'),
                        }
                        for item in warning_items
                    ]
                }
                self._suggestions.append(suggestion)
        
        # 按优先级排序
        self._suggestions.sort(key=lambda x: 0 if x['priority'] == 'critical' else 1)
    
    def _load_history_comparison(self):
        """加载历史对比数据"""
        from modules.foundation.db_models.inspection import InspectionTask
        
        task_no = self._task_info.get('task_no', '')
        if not task_no:
            self._history_comparison = {}
            return
        
        # 提取任务编号前缀查找历史任务
        prefix = task_no.rsplit('-', 1)[0] if '-' in task_no else task_no
        
        # 查询最近5次历史任务
        historical_tasks = self.db.query(InspectionTask).filter(
            InspectionTask.task_no.like(f"{prefix}%"),
            InspectionTask.id != self._task_info.get('id'),
            InspectionTask.status == InspectionStatus.COMPLETED,
        ).order_by(InspectionTask.created_at.desc()).limit(5).all()
        
        self._history_comparison = {
            'history_tasks': [
                {
                    'task_no': t.task_no,
                    'health_score': t.health_score,
                    'healthy_devices': t.healthy_devices,
                    'warning_devices': t.warning_devices,
                    'critical_devices': t.critical_devices,
                    'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in historical_tasks
            ],
            'trend': self._calculate_trend(historical_tasks),
        }
    
    def _calculate_trend(self, historical_tasks: List) -> str:
        """计算趋势"""
        if len(historical_tasks) < 2:
            return 'stable'
        
        scores = [t.health_score for t in historical_tasks if t.health_score]
        if len(scores) < 2:
            return 'stable'
        
        # 比较最近两次的健康度
        if scores[0] > scores[1]:
            return 'improving'
        elif scores[0] < scores[1]:
            return 'declining'
        else:
            return 'stable'
    
    def _assemble_report(self) -> Dict[str, Any]:
        """组装完整报告数据"""
        health_score = self._task_info.get('health_score') or self._calculate_health_score()
        
        return {
            'task_info': self._task_info,
            'statistics': self._statistics,
            'devices': list(self._device_results.values()),
            'suggestions': self._suggestions,
            'history_comparison': self._history_comparison,
            'health_score': health_score,
            'health_level': self._get_health_level(health_score),
            'generated_at': datetime.now().isoformat(),
        }
    
    def _calculate_health_score(self) -> float:
        """计算健康度评分"""
        status = self._statistics.get('status_summary', {})
        total = status.get('total', 0)
        if total == 0:
            return 100.0
        
        healthy = status.get('healthy', 0)
        warning = status.get('warning', 0)
        critical = status.get('critical', 0)
        
        # 加权计算
        score = (healthy * 100 + warning * 70 + critical * 30) / total
        return round(score, 2)
    
    def _get_health_level(self, score: float) -> Dict[str, Any]:
        """获取健康度等级信息"""
        for threshold, name, color in self.HEALTH_LEVELS:
            if score >= threshold:
                return {'score': score, 'level': name, 'color': color}
        return {'score': score, 'level': '危险', 'color': '#ff4d4f'}
    
    def get_report_template(self) -> Dict[str, Any]:
        """获取巡检报告模板配置"""
        return {
            'name': '巡检报告模板',
            'description': '标准巡检报告模板，包含健康度评分、异常统计、建议措施等',
            'sections': [
                {
                    'id': 'summary',
                    'title': '巡检概览',
                    'fields': [
                        {'key': 'task_name', 'label': '任务名称'},
                        {'key': 'task_no', 'label': '任务编号'},
                        {'key': 'inspection_type', 'label': '巡检类型'},
                        {'key': 'executor', 'label': '执行人'},
                        {'key': 'started_at', 'label': '开始时间'},
                        {'key': 'completed_at', 'label': '完成时间'},
                    ]
                },
                {
                    'id': 'health_score',
                    'title': '健康度评分',
                    'fields': [
                        {'key': 'health_score', 'label': '综合评分'},
                        {'key': 'health_level', 'label': '健康等级'},
                    ]
                },
                {
                    'id': 'statistics',
                    'title': '异常统计',
                    'fields': [
                        {'key': 'total_devices', 'label': '设备总数'},
                        {'key': 'healthy_devices', 'label': '正常'},
                        {'key': 'warning_devices', 'label': '警告'},
                        {'key': 'critical_devices', 'label': '严重'},
                    ]
                },
                {
                    'id': 'suggestions',
                    'title': '建议措施',
                    'type': 'list',
                },
                {
                    'id': 'history',
                    'title': '历史对比',
                    'type': 'table',
                }
            ],
            'format_config': {
                'date_format': '%Y-%m-%d %H:%M:%S',
                'datetime_format': '%Y-%m-%d %H:%M:%S',
            }
        }
    
    def export_html(self, inspection_task_id: int) -> Tuple[bytes, str]:
        """
        导出HTML格式报告
        
        Args:
            inspection_task_id: 巡检任务ID
            
        Returns:
            (html_bytes, content_type)
        """
        report_data = self.generate_report(inspection_task_id)
        
        html_content = self._render_html_report(report_data)
        return html_content.encode('utf-8'), 'text/html; charset=utf-8'
    
    def export_pdf(self, inspection_task_id: int) -> Tuple[bytes, str]:
        """
        导出PDF格式报告
        
        Args:
            inspection_task_id: 巡检任务ID
            
        Returns:
            (pdf_bytes, content_type)
        """
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("WeasyPrint is required for PDF export. Install with: pip install weasyprint")
        
        report_data = self.generate_report(inspection_task_id)
        html_content = self._render_html_report(report_data)
        
        pdf_io = io.BytesIO()
        WeasyHTML(string=html_content).write_pdf(pdf_io)
        pdf_io.seek(0)
        
        return pdf_io.getvalue(), 'application/pdf'
    
    def _render_html_report(self, report_data: Dict) -> str:
        """渲染HTML报告"""
        task_info = report_data.get('task_info', {})
        statistics = report_data.get('statistics', {})
        devices = report_data.get('devices', [])
        suggestions = report_data.get('suggestions', [])
        history = report_data.get('history_comparison', {})
        health_level = report_data.get('health_level', {})
        
        # 状态统计
        status_summary = statistics.get('status_summary', {})
        
        # 设备健康状态HTML
        device_cards_html = ''
        for device in devices[:10]:  # 最多显示10个设备
            status_counts = device.get('status_counts', {})
            device_status = 'healthy'
            if status_counts.get('critical', 0) > 0 or status_counts.get('error', 0) > 0:
                device_status = 'critical'
            elif status_counts.get('warning', 0) > 0:
                device_status = 'warning'
            
            device_cards_html += f'''
            <div class="device-card {device_status}">
                <div class="device-header">
                    <span class="device-name">{device.get('device_name', 'Unknown')}</span>
                    <span class="device-ip">{device.get('device_ip', '')}</span>
                </div>
                <div class="device-stats">
                    <span class="stat ok">正常 {status_counts.get('ok', 0)}</span>
                    <span class="stat warning">警告 {status_counts.get('warning', 0)}</span>
                    <span class="stat critical">严重 {status_counts.get('critical', 0)}</span>
                </div>
            </div>
            '''
        
        # 建议措施HTML
        suggestions_html = ''
        for suggestion in suggestions[:20]:  # 最多显示20条
            priority_class = 'critical' if suggestion.get('priority') == 'critical' else 'warning'
            issues_html = ''
            for issue in suggestion.get('issues', []):
                issues_html += f'''
                <div class="issue-item">
                    <div class="issue-title">{issue.get('check_item', '')}</div>
                    <div class="issue-message">{issue.get('message', '')}</div>
                    <div class="issue-suggestion">💡 {issue.get('suggestion', '')}</div>
                </div>
                '''
            
            suggestions_html += f'''
            <div class="suggestion-item {priority_class}">
                <div class="suggestion-header">
                    <span class="device-name">{suggestion.get('device_name', '')}</span>
                    <span class="device-ip">{suggestion.get('device_ip', '')}</span>
                </div>
                {issues_html}
            </div>
            '''
        
        # 历史对比HTML
        history_html = ''
        for hist in history.get('history_tasks', []):
            history_html += f'''
            <tr>
                <td>{hist.get('task_no', '')}</td>
                <td>{hist.get('health_score', 0):.1f}</td>
                <td>{hist.get('healthy_devices', 0)}</td>
                <td>{hist.get('warning_devices', 0)}</td>
                <td>{hist.get('critical_devices', 0)}</td>
                <td>{hist.get('completed_at', '')}</td>
            </tr>
            '''
        
        # 趋势图标
        trend = history.get('trend', 'stable')
        trend_icon = {'improving': '📈', 'declining': '📉', 'stable': '➡️'}.get(trend, '➡️')
        
        html = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>巡检报告 - {task_info.get('name', '')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        /* 头部 */
        .report-header {{ background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .report-header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .report-header .subtitle {{ opacity: 0.9; font-size: 14px; }}
        .report-meta {{ display: flex; gap: 30px; margin-top: 20px; font-size: 14px; }}
        .report-meta span {{ display: flex; align-items: center; gap: 6px; }}
        
        /* 健康度评分 */
        .health-score-card {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; display: flex; align-items: center; gap: 40px; }}
        .score-circle {{ width: 150px; height: 150px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-weight: bold; }}
        .score-value {{ font-size: 48px; }}
        .score-label {{ font-size: 16px; opacity: 0.8; }}
        .score-details {{ flex: 1; }}
        .score-title {{ font-size: 24px; margin-bottom: 20px; }}
        .score-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
        .stat-box {{ text-align: center; padding: 15px; border-radius: 8px; background: #f5f7fa; }}
        .stat-box .value {{ font-size: 28px; font-weight: bold; }}
        .stat-box .label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .stat-box.healthy {{ background: #f6ffed; }} .stat-box.healthy .value {{ color: #52c41a; }}
        .stat-box.warning {{ background: #fffbe6; }} .stat-box.warning .value {{ color: #faad14; }}
        .stat-box.critical {{ background: #fff2f0; }} .stat-box.critical .value {{ color: #ff4d4f; }}
        
        /* 卡片通用 */
        .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; }}
        .card-title {{ font-size: 18px; font-weight: 600; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee; }}
        
        /* 设备列表 */
        .device-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }}
        .device-card {{ border-radius: 8px; padding: 16px; background: #f5f7fa; border-left: 4px solid #52c41a; }}
        .device-card.warning {{ border-left-color: #faad14; }}
        .device-card.critical {{ border-left-color: #ff4d4f; }}
        .device-header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
        .device-name {{ font-weight: 600; }}
        .device-ip {{ color: #666; font-size: 14px; }}
        .device-stats {{ display: flex; gap: 10px; font-size: 13px; }}
        .device-stats .stat {{ padding: 4px 8px; border-radius: 4px; }}
        .device-stats .ok {{ background: #f6ffed; color: #52c41a; }}
        .device-stats .warning {{ background: #fffbe6; color: #faad14; }}
        .device-stats .critical {{ background: #fff2f0; color: #ff4d4f; }}
        
        /* 建议措施 */
        .suggestion-item {{ border-radius: 8px; padding: 16px; margin-bottom: 15px; background: #f5f7fa; border-left: 4px solid #faad14; }}
        .suggestion-item.critical {{ border-left-color: #ff4d4f; background: #fff2f0; }}
        .suggestion-header {{ display: flex; justify-content: space-between; margin-bottom: 12px; }}
        .issue-item {{ padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.05); }}
        .issue-item:last-child {{ border-bottom: none; }}
        .issue-title {{ font-weight: 600; color: #333; }}
        .issue-message {{ color: #666; font-size: 14px; margin: 5px 0; }}
        .issue-suggestion {{ color: #1890ff; font-size: 14px; background: rgba(24,144,255,0.1); padding: 8px 12px; border-radius: 4px; }}
        
        /* 历史对比 */
        .trend-badge {{ display: inline-flex; align-items: center; gap: 5px; padding: 6px 12px; border-radius: 20px; font-size: 14px; }}
        .trend-badge.improving {{ background: #f6ffed; color: #52c41a; }}
        .trend-badge.declining {{ background: #fff2f0; color: #ff4d4f; }}
        .trend-badge.stable {{ background: #f5f7fa; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #fafafa; font-weight: 600; color: #333; }}
        tr:hover {{ background: #fafafa; }}
        
        /* 页脚 */
        .report-footer {{ text-align: center; color: #999; font-size: 12px; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 报告头部 -->
        <div class="report-header">
            <h1>🛡️ {task_info.get('name', '巡检报告')}</h1>
            <div class="subtitle">{task_info.get('description', '设备巡检健康度报告')}</div>
            <div class="report-meta">
                <span>📋 任务编号: {task_info.get('task_no', '')}</span>
                <span>👤 执行人: {task_info.get('executor', '系统')}</span>
                <span>⏰ 执行时间: {task_info.get('started_at', '') or '-'} 至 {task_info.get('completed_at', '') or '-'}</span>
            </div>
        </div>
        
        <!-- 健康度评分 -->
        <div class="health-score-card">
            <div class="score-circle" style="background: {health_level.get('color', '#52c41a')}; color: white;">
                <div class="score-value">{report_data.get('health_score', 0):.1f}</div>
                <div class="score-label">{health_level.get('level', '优秀')}</div>
            </div>
            <div class="score-details">
                <div class="score-title">📊 健康度评分</div>
                <div class="score-stats">
                    <div class="stat-box healthy">
                        <div class="value">{status_summary.get('total', 0)}</div>
                        <div class="label">设备总数</div>
                    </div>
                    <div class="stat-box healthy">
                        <div class="value">{status_summary.get('healthy', 0)}</div>
                        <div class="label">正常</div>
                    </div>
                    <div class="stat-box warning">
                        <div class="value">{status_summary.get('warning', 0)}</div>
                        <div class="label">警告</div>
                    </div>
                    <div class="stat-box critical">
                        <div class="value">{status_summary.get('critical', 0)}</div>
                        <div class="label">严重</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 设备巡检结果 -->
        <div class="card">
            <div class="card-title">📱 设备巡检结果 (显示前10个设备)</div>
            <div class="device-grid">
                {device_cards_html or '<div class="no-data">暂无巡检数据</div>'}
            </div>
        </div>
        
        <!-- 建议措施 -->
        <div class="card">
            <div class="card-title">💡 建议措施</div>
            {suggestions_html or '<div class="no-data">暂无建议措施</div>'}
        </div>
        
        <!-- 历史对比 -->
        <div class="card">
            <div class="card-title">
                📈 历史对比 
                <span class="trend-badge {trend}">{trend_icon} {'改善中' if trend == 'improving' else '下降中' if trend == 'declining' else '稳定'}</span>
            </div>
            {history_html}
            <table>
                <thead>
                    <tr>
                        <th>任务编号</th>
                        <th>健康评分</th>
                        <th>正常</th>
                        <th>警告</th>
                        <th>严重</th>
                        <th>完成时间</th>
                    </tr>
                </thead>
                <tbody>
                    {history_html or '<tr><td colspan="6" style="text-align:center;">暂无历史数据</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <!-- 页脚 -->
        <div class="report-footer">
            <p>报告生成时间: {report_data.get('generated_at', '')}</p>
            <p>ITOps Platform 巡检报告系统</p>
        </div>
    </div>
</body>
</html>
        '''
        return html


# 为了引用历史任务状态的便捷方式
InspectionStatus = type('InspectionStatus', (), {
    'PENDING': 'pending',
    'RUNNING': 'running', 
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled'
})()
