# -*- coding: utf-8 -*-
"""
ITOps Platform - Report Generator
报告生成器
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ReportFormat(Enum):
    """报告格式"""
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"
    MARKDOWN = "markdown"


@dataclass
class ReportTemplate:
    """报告模板"""
    id: str
    name: str
    description: str = ""
    template_type: str = "daily"  # daily, weekly, monthly, custom
    content_template: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self._templates: Dict[str, ReportTemplate] = {}
        self._default_template = self._create_default_template()
    
    def _create_default_template(self) -> ReportTemplate:
        """创建默认模板"""
        return ReportTemplate(
            id="default",
            name="默认报告模板",
            description="通用的运维报告模板",
            content_template="""
# {title}

**生成时间**: {generated_at}
**报告周期**: {period}

## 概述

{summary}

## 统计数据

| 指标 | 数值 |
|------|------|
| 总告警数 | {total_alerts} |
| 活跃告警 | {active_alerts} |
| 已解决告警 | {resolved_alerts} |
| 工单总数 | {total_workorders} |
| 已处理工单 | {processed_workorders} |

## 详细信息

{content}

## 建议

{recommendations}

---
*此报告由ITOps平台自动生成*
"""
        )
    
    def register_template(self, template: ReportTemplate):
        """注册模板"""
        self._templates[template.id] = template
    
    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """获取模板"""
        return self._templates.get(template_id) or self._default_template
    
    async def generate(
        self,
        title: str,
        data: Dict[str, Any],
        template_id: str = "default",
        format: ReportFormat = ReportFormat.HTML
    ) -> Dict[str, Any]:
        """生成报告"""
        template = self.get_template(template_id)
        
        # 准备变量
        variables = {
            "title": title,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "period": data.get("period", ""),
            "summary": data.get("summary", ""),
            "content": data.get("content", ""),
            "recommendations": data.get("recommendations", ""),
            "total_alerts": data.get("alerts", {}).get("total", 0),
            "active_alerts": data.get("alerts", {}).get("active", 0),
            "resolved_alerts": data.get("alerts", {}).get("resolved", 0),
            "total_workorders": data.get("workorders", {}).get("total", 0),
            "processed_workorders": data.get("workorders", {}).get("processed", 0),
        }
        
        # 渲染模板
        content = template.content_template.format(**variables)
        
        # 根据格式生成
        if format == ReportFormat.MARKDOWN:
            return {"status": "success", "content": content, "format": "markdown"}
        
        elif format == ReportFormat.HTML:
            html = self._render_html(title, content)
            return {"status": "success", "content": html, "format": "html"}
        
        elif format == ReportFormat.PDF:
            # PDF需要额外处理
            return {"status": "success", "content": content, "format": "pdf"}
        
        elif format == ReportFormat.EXCEL:
            # Excel需要额外处理
            return {"status": "success", "content": content, "format": "excel"}
        
        return {"status": "error", "error": "Unknown format"}
    
    def _render_html(self, title: str, content: str) -> str:
        """渲染HTML"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #007bff; color: white; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    {content}
    <div class="footer">
        <p>此报告由ITOps平台自动生成 | 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
</body>
</html>
"""
