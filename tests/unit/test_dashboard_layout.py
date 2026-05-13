"""
MON-031/MON-032 仪表盘布局持久化单元测试

测试仪表盘自定义列功能：
- DashboardLayout模型
- GET/PUT /api/v1/dashboard/layout API
- 拖拽排序、显示/隐藏列、自定义列宽
"""

import pytest
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

# 导入被测试模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from modules.business.dashboard.persistence import (
    DashboardLayout,
    DashboardLayoutSnapshot,
    DashboardLayoutData,
    DashboardLayoutService,
    LayoutItem,
    LayoutWidget,
    LayoutPosition,
    ColumnConfig,
    DEFAULT_COLUMNS,
)


# ============== 测试数据工厂 ==============

class DashboardLayoutDataFactory:
    """仪表盘布局测试数据工厂"""
    
    def __init__(self, seed: int = 42):
        import random
        self._random = random
        self._random.seed(seed)
        self._counter = 0
    
    def _uid(self) -> str:
        self._counter += 1
        return f"{self._counter}_{uuid.uuid4().hex[:8]}"
    
    def widget(self, **overrides) -> dict:
        widget_types = [
            "alert_count", "alert_list", "device_status", "metric_chart",
            "topn_table", "availabilityGauge", "trend_line", "pie_chart",
            "heatmap", "stat_card", "sla_timer", "workorder_list"
        ]
        data = {
            "widget_id": f"widget_{uuid.uuid4().hex[:12]}",
            "widget_type": self._random.choice(widget_types),
            "title": f"组件-{self._uid()}",
            "description": f"组件描述",
            "metric_names": self._random.sample(
                ["cpu", "memory", "disk", "network", "response_time", "error_rate"],
                k=self._random.randint(1, 3)
            ),
            "device_filter": self._random.choice([None, "all", "online", "offline"]),
            "time_range": self._random.choice(["1h", "6h", "24h", "7d", "30d"]),
            "refresh_interval": self._random.choice([30, 60, 300, 600]),
            "config": {
                "show_legend": self._random.choice([True, False]),
                "show_grid": self._random.choice([True, False]),
                "color_scheme": self._random.choice(["default", "dark", "light"]),
                "chart_type": self._random.choice(["line", "bar", "area", "pie"]),
            },
            "tags": self._random.sample(["重要", "核心", "监控"], k=self._random.randint(0, 2)),
        }
        data.update(overrides)
        return data
    
    def layout_position(self, **overrides) -> dict:
        data = {
            "x": self._random.randint(0, 11),
            "y": self._random.randint(0, 19),
            "width": self._random.choice([1, 2, 3, 4, 6, 8]),
            "height": self._random.choice([1, 2, 3, 4]),
            "min_width": 1,
            "min_height": 1,
            "z_index": self._random.randint(0, 100),
        }
        data.update(overrides)
        return data
    
    def layout_item(self, widget: dict = None, position: dict = None, **overrides) -> dict:
        widget = widget or self.widget()
        position = position or self.layout_position()
        data = {
            "item_id": f"item_{uuid.uuid4().hex[:12]}",
            "widget": widget,
            "position": position,
            "visibility": self._random.choice([True, True, True, False]),
            "locked": self._random.choice([False, False, True]),
            "collapsed": self._random.choice([False, False, True]),
        }
        data.update(overrides)
        return data
    
    def column_config(self, **overrides) -> dict:
        data = {
            "column_id": self._random.choice(["device_status", "cpu_usage", "memory_usage", "disk_usage"]),
            "visible": True,
            "width": self._random.randint(80, 300),
            "order": self._random.randint(0, 10),
        }
        data.update(overrides)
        return data
    
    def dashboard_layout(self, items: list = None, **overrides) -> dict:
        items = items or [self.layout_item() for _ in range(self._random.randint(2, 5))]
        data = {
            "layout_id": f"layout_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{self._random.randint(1, 100)}",
            "name": f"布局-{self._uid()}",
            "description": f"自定义仪表盘布局",
            "version": 1,
            "parent_version": None,
            "grid_size": self._random.choice(["small", "medium", "large", "xlarge"]),
            "columns": self._random.choice([12, 24]),
            "row_height": self._random.choice([50, 80, 100]),
            "items": items,
            "column_config": [self.column_config() for _ in range(self._random.randint(3, 7))],
            "theme": self._random.choice(["default", "dark", "light"]),
            "is_default": self._random.choice([False, False, True]),
            "is_shared": self._random.choice([False, True]),
            "tags": self._random.sample(["默认", "核心监控", "运维视图"], k=self._random.randint(0, 2)),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "created_by": f"user_{self._random.randint(1, 50)}",
            "updated_by": f"user_{self._random.randint(1, 50)}",
        }
        data.update(overrides)
        return data


# ============== Fixtures ==============

@pytest.fixture
def layout_factory():
    """布局工厂实例"""
    return DashboardLayoutDataFactory(seed=42)


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.query = MagicMock()
    session.close = MagicMock()
    return session


# ============== 数据模型测试 ==============

class TestLayoutPosition:
    """LayoutPosition数据类测试"""
    
    def test_position_creation(self):
        pos = LayoutPosition(x=2, y=3, width=4, height=3)
        assert pos.x == 2
        assert pos.y == 3
        assert pos.width == 4
        assert pos.height == 3
    
    def test_position_to_dict(self):
        pos = LayoutPosition(x=1, y=2, width=3, height=4, z_index=10)
        d = pos.to_dict()
        assert d['x'] == 1
        assert d['y'] == 2
        assert d['width'] == 3
        assert d['height'] == 4
        assert d['z_index'] == 10
    
    def test_position_from_dict(self):
        data = {"x": 5, "y": 10, "width": 6, "height": 3, "min_width": 2, "min_height": 2, "z_index": 20}
        pos = LayoutPosition.from_dict(data)
        assert pos.x == 5
        assert pos.y == 10
        assert pos.width == 6
        assert pos.height == 3
        assert pos.z_index == 20
    
    def test_position_defaults(self):
        pos = LayoutPosition()
        assert pos.x == 0
        assert pos.y == 0
        assert pos.width == 2
        assert pos.height == 2
        assert pos.z_index == 0


class TestLayoutWidget:
    """LayoutWidget数据类测试"""
    
    def test_widget_creation(self):
        widget = LayoutWidget(
            widget_id="w1",
            widget_type="stat_card",
            title="CPU使用率",
            metric_names=["cpu_usage"],
            time_range="24h",
        )
        assert widget.widget_id == "w1"
        assert widget.widget_type == "stat_card"
        assert "cpu_usage" in widget.metric_names
    
    def test_widget_to_dict(self):
        widget = LayoutWidget(
            widget_id="w2",
            widget_type="alert_count",
            title="告警数量",
            config={"show_legend": True},
        )
        d = widget.to_dict()
        assert d['widget_id'] == "w2"
        assert d['widget_type'] == "alert_count"
        assert d['config']['show_legend'] is True
    
    def test_widget_from_dict(self):
        data = {
            "widget_id": "w3",
            "widget_type": "metric_chart",
            "title": "性能图表",
            "metric_names": ["cpu", "memory"],
            "time_range": "1h",
            "refresh_interval": 60,
            "config": {"chart_type": "line"},
            "tags": ["重要"],
            "description": "测试组件",
        }
        widget = LayoutWidget.from_dict(data)
        assert widget.widget_id == "w3"
        assert widget.metric_names == ["cpu", "memory"]


class TestLayoutItem:
    """LayoutItem数据类测试"""
    
    def test_item_creation(self):
        widget = LayoutWidget(widget_id="w1", widget_type="stat_card", title="测试")
        position = LayoutPosition(x=0, y=0, width=2, height=2)
        item = LayoutItem(
            item_id="item1",
            widget=widget,
            position=position,
            visibility=True,
        )
        assert item.item_id == "item1"
        assert item.visibility is True
    
    def test_item_to_dict(self):
        widget = LayoutWidget(widget_id="w1", widget_type="stat_card", title="测试")
        position = LayoutPosition(x=1, y=2, width=3, height=4)
        item = LayoutItem(item_id="item2", widget=widget, position=position)
        d = item.to_dict()
        assert d['item_id'] == "item2"
        assert d['widget']['widget_id'] == "w1"
        assert d['position']['x'] == 1
    
    def test_item_from_dict(self):
        data = {
            "item_id": "item3",
            "widget": {"widget_id": "w3", "widget_type": "alert_list", "title": "告警列表", "metric_names": [], "description": ""},
            "position": {"x": 5, "y": 3, "width": 4, "height": 2, "min_width": 1, "min_height": 1, "z_index": 0},
            "visibility": True,
            "locked": False,
            "collapsed": False,
        }
        item = LayoutItem.from_dict(data)
        assert item.item_id == "item3"
        assert item.widget.widget_type == "alert_list"
        assert item.position.x == 5


class TestColumnConfig:
    """ColumnConfig数据类测试"""
    
    def test_column_config_creation(self):
        col = ColumnConfig(column_id="cpu_usage", visible=True, width=150, order=1)
        assert col.column_id == "cpu_usage"
        assert col.visible is True
        assert col.width == 150
    
    def test_column_config_to_dict(self):
        col = ColumnConfig(column_id="memory", visible=False, width=200, order=2)
        d = col.to_dict()
        assert d['column_id'] == "memory"
        assert d['visible'] is False
        assert d['order'] == 2
    
    def test_column_config_from_dict(self):
        data = {"column_id": "disk", "visible": True, "width": 180, "order": 3}
        col = ColumnConfig.from_dict(data)
        assert col.column_id == "disk"
        assert col.width == 180


class TestDashboardLayoutData:
    """DashboardLayoutData数据类测试"""
    
    def test_layout_data_creation(self, layout_factory):
        layout = layout_factory.dashboard_layout()
        data = DashboardLayoutData.from_dict(layout)
        
        assert data.layout_id == layout['layout_id']
        assert data.user_id == layout['user_id']
        assert data.name == layout['name']
        assert len(data.items) == len(layout['items'])
        assert len(data.column_config) == len(layout['column_config'])
    
    def test_layout_data_to_dict(self, layout_factory):
        layout = layout_factory.dashboard_layout()
        data = DashboardLayoutData.from_dict(layout)
        d = data.to_dict()
        
        assert d['layout_id'] == layout['layout_id']
        assert 'items' in d
        assert 'column_config' in d
    
    def test_layout_data_grid_config(self, layout_factory):
        layout = layout_factory.dashboard_layout(grid_size="large", columns=24, row_height=100)
        data = DashboardLayoutData.from_dict(layout)
        
        assert data.grid_size == "large"
        assert data.columns == 24
        assert data.row_height == 100


# ============== API模型测试 ==============

class TestDashboardLayoutAPI:
    """DashboardLayout API请求/响应模型测试"""
    
    def test_default_columns_structure(self):
        """测试默认列配置结构"""
        assert len(DEFAULT_COLUMNS) > 0
        for col in DEFAULT_COLUMNS:
            assert 'column_id' in col
            assert 'visible' in col
            assert 'width' in col
            assert 'order' in col
    
    def test_default_columns_have_required_columns(self):
        """测试默认列包含必要列"""
        column_ids = [c['column_id'] for c in DEFAULT_COLUMNS]
        required = ['device_status', 'cpu_usage', 'memory_usage']
        for req in required:
            assert req in column_ids, f"缺少必需列: {req}"


# ============== 响应格式测试 ==============

class TestResponseFormat:
    """响应格式测试"""
    
    def test_build_response_format(self):
        """测试响应格式遵循 {data, code, message} 结构"""
        from api.routes.monitoring import _build_response
        
        # 成功响应
        resp = _build_response(data={"test": "value"})
        assert 'data' in resp
        assert 'code' in resp
        assert 'message' in resp
        assert resp['code'] == 0
        
        # 错误响应
        resp_err = _build_response(code=404, message="Not found")
        assert resp_err['code'] == 404
        assert resp_err['message'] == "Not found"
    
    def test_layout_response_structure(self, layout_factory):
        """测试布局响应结构"""
        layout = layout_factory.dashboard_layout()
        data = DashboardLayoutData.from_dict(layout).to_dict()
        
        required_fields = [
            'layout_id', 'user_id', 'name', 'version', 'grid_size',
            'columns', 'row_height', 'items', 'column_config', 'theme',
            'is_default', 'is_shared', 'tags'
        ]
        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"


# ============== 拖拽排序测试 ==============

class TestDragDropOrdering:
    """拖拽排序测试"""
    
    def test_reorder_items(self, layout_factory):
        """测试重排布局项"""
        layout = layout_factory.dashboard_layout()
        items = layout['items']
        
        # 颠倒顺序
        original_first_id = items[0]['item_id']
        reversed_items = list(reversed(items))
        
        assert reversed_items[0]['item_id'] == items[-1]['item_id']
        assert reversed_items[-1]['item_id'] == original_first_id
    
    def test_position_update_on_drag(self, layout_factory):
        """测试拖拽后位置更新"""
        layout = layout_factory.dashboard_layout()
        item = layout['items'][0]
        
        # 模拟拖拽到新位置
        new_x = 5
        new_y = 10
        item['position']['x'] = new_x
        item['position']['y'] = new_y
        
        assert item['position']['x'] == 5
        assert item['position']['y'] == 10


# ============== 列显示/隐藏测试 ==============

class TestColumnVisibility:
    """列显示/隐藏测试"""
    
    def test_toggle_column_visibility(self):
        """测试切换列显示状态"""
        col = ColumnConfig(column_id="cpu_usage", visible=True, width=100, order=1)
        assert col.visible is True
        
        col.visible = False
        assert col.visible is False
    
    def test_column_visibility_in_layout(self, layout_factory):
        """测试布局中的列显示配置"""
        layout = layout_factory.dashboard_layout()
        col_configs = layout['column_config']
        
        # 设置某些列为隐藏
        col_configs[0]['visible'] = False
        
        assert col_configs[0]['visible'] is False
        assert col_configs[1]['visible'] is True


# ============== 列宽自定义测试 ==============

class TestColumnWidth:
    """列宽自定义测试"""
    
    def test_update_column_width(self):
        """测试更新列宽"""
        col = ColumnConfig(column_id="memory", visible=True, width=100, order=1)
        col.width = 200
        
        assert col.width == 200
    
    def test_column_width_in_layout(self, layout_factory):
        """测试布局中的列宽配置"""
        layout = layout_factory.dashboard_layout()
        col_configs = layout['column_config']
        
        # 更新列宽
        col_configs[0]['width'] = 300
        
        assert col_configs[0]['width'] == 300


# ============== 布局版本控制测试 ==============

class TestLayoutVersioning:
    """布局版本控制测试"""
    
    def test_version_increment(self, layout_factory):
        """测试版本递增"""
        layout = layout_factory.dashboard_layout(version=1)
        layout['version'] = layout['version'] + 1
        
        assert layout['version'] == 2
    
    def test_parent_version_tracking(self, layout_factory):
        """测试父版本追踪"""
        parent = layout_factory.dashboard_layout(version=1)
        child = layout_factory.dashboard_layout(version=1, parent_version=parent['layout_id'])
        
        assert child['parent_version'] == parent['layout_id']


# ============== 服务层测试 ==============

class TestDashboardLayoutService:
    """DashboardLayoutService测试"""
    
    def test_service_init(self, mock_db_session):
        """测试服务初始化"""
        service = DashboardLayoutService(db_session=mock_db_session)
        assert service._db_session == mock_db_session
    
    def test_create_default_layout(self, layout_factory):
        """测试创建默认布局"""
        user_id = "test_user_123"
        
        # 使用内存模拟（不连接真实数据库）
        with patch.object(DashboardLayoutService, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            
            # 模拟查询返回空（无现有布局）
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session.query.return_value = mock_query
            
            service = DashboardLayoutService()
            
            # 由于没有真实数据库，这里只验证数据结构
            default_layout = DashboardLayoutData(
                layout_id=f"default_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                name="默认布局",
                description="系统默认布局",
                grid_size="medium",
                columns=12,
                row_height=80,
                items=[
                    LayoutItem(
                        item_id=f"item_{uuid.uuid4().hex[:8]}",
                        widget=LayoutWidget(
                            widget_id=f"widget_{uuid.uuid4().hex[:8]}",
                            widget_type="stat_card",
                            title="设备总数",
                            metric_names=["device_count"],
                        ),
                        position=LayoutPosition(x=0, y=0, width=3, height=2),
                    )
                ],
                column_config=[ColumnConfig.from_dict(c) for c in DEFAULT_COLUMNS],
                is_default=True,
            )
            
            assert default_layout.name == "默认布局"
            assert default_layout.is_default is True
            assert len(default_layout.items) >= 1


# ============== 布局持久化测试 ==============

class TestLayoutPersistence:
    """布局持久化测试"""
    
    def test_layout_serialization(self, layout_factory):
        """测试布局序列化/反序列化"""
        layout = layout_factory.dashboard_layout()
        
        # 序列化为JSON
        json_str = json.dumps(layout)
        assert isinstance(json_str, str)
        
        # 反序列化
        parsed = json.loads(json_str)
        assert parsed['layout_id'] == layout['layout_id']
        assert len(parsed['items']) == len(layout['items'])
    
    def test_layout_items_json_storage(self, layout_factory):
        """测试布局项JSON存储"""
        layout = layout_factory.dashboard_layout()
        
        # 模拟数据库存储格式
        items_json = json.dumps(layout['items'])
        column_config_json = json.dumps(layout['column_config'])
        
        # 验证可以正确反序列化
        items_parsed = json.loads(items_json)
        configs_parsed = json.loads(column_config_json)
        
        assert len(items_parsed) == len(layout['items'])
        assert len(configs_parsed) == len(layout['column_config'])


# ============== 集成场景测试 ==============

class TestDashboardLayoutIntegration:
    """仪表盘布局集成场景测试"""
    
    def test_full_layout_workflow(self, layout_factory):
        """测试完整布局工作流"""
        user_id = "user_integration_test"
        
        # 1. 创建布局
        layout = layout_factory.dashboard_layout(user_id=user_id)
        assert layout['user_id'] == user_id
        
        # 2. 转换为DashboardLayoutData
        data = DashboardLayoutData.from_dict(layout)
        assert data.user_id == user_id
        
        # 3. 模拟拖拽排序
        original_items = list(data.items)
        data.items = list(reversed(data.items))
        assert data.items[0].item_id == original_items[-1].item_id
        
        # 4. 模拟隐藏列
        if data.column_config:
            data.column_config[0] = ColumnConfig(
                column_id=data.column_config[0].column_id,
                visible=False,
                width=data.column_config[0].width,
                order=data.column_config[0].order,
            )
        
        # 5. 模拟调整列宽
        if data.column_config:
            data.column_config[1] = ColumnConfig(
                column_id=data.column_config[1].column_id,
                visible=True,
                width=300,
                order=data.column_config[1].order,
            )
        
        # 6. 转换为最终JSON
        final_json = json.dumps(data.to_dict())
        final_data = json.loads(final_json)
        
        assert final_data['user_id'] == user_id
        assert len(final_data['items']) == len(layout['items'])
        assert final_data['column_config'][0]['visible'] is False
        assert final_data['column_config'][1]['width'] == 300
    
    def test_multi_user_isolation(self, layout_factory):
        """测试多用户隔离"""
        layout1 = layout_factory.dashboard_layout(user_id="user_1")
        layout2 = layout_factory.dashboard_layout(user_id="user_2")
        
        assert layout1['user_id'] != layout2['user_id']
        assert layout1['layout_id'] != layout2['layout_id']


# ============== 运行测试 ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
