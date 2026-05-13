"""
仪表盘布局持久化模块
MON-031/MON-032: 仪表盘自定义列 - 后端布局持久化 + 前端拖拽配置

提供用户自定义仪表盘布局的存储和加载功能
支持拖拽排序、显示/隐藏列、自定义列宽
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index
from sqlalchemy.sql import func

from modules.foundation.db_models.base import Base


logger = logging.getLogger(__name__)


# ============== SQLAlchemy 模型 ==============

class DashboardLayout(Base):
    """
    仪表盘布局模型
    保存用户自定义布局配置
    """
    __tablename__ = "dashboard_layouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 用户标识
    user_id = Column(String(64), nullable=False, index=True)
    
    # 布局基本信息
    layout_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), default="默认布局")
    description = Column(String(512))
    
    # 布局配置 (JSON格式)
    config = Column(Text, default="{}")  # JSON: {columns, rowHeight, gridSize}
    
    # 布局项列表 (JSON格式) - 包含widgets和positions
    items = Column(Text, default="[]")  # JSON数组
    
    # 列配置 (JSON格式) - 显示/隐藏、宽度等
    column_config = Column(Text, default="[]")  # JSON数组: [{columnId, visible, width}]
    
    # 主题
    theme = Column(String(32), default="default")
    
    # 状态
    is_default = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    
    # 版本控制
    version = Column(Integer, default=1)
    parent_version = Column(Integer, nullable=True)
    
    # 快照数据 (JSON格式)
    snapshot_data = Column(Text, nullable=True)
    
    # 标签 (JSON格式)
    tags = Column(Text, default="[]")
    
    # 审计字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(64))
    updated_by = Column(String(64))
    
    # 索引
    __table_args__ = (
        Index('idx_user_layout', 'user_id', 'layout_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'layout_id': self.layout_id,
            'name': self.name,
            'description': self.description,
            'config': json.loads(self.config) if self.config else {},
            'items': json.loads(self.items) if self.items else [],
            'column_config': json.loads(self.column_config) if self.column_config else [],
            'theme': self.theme,
            'is_default': self.is_default,
            'is_shared': self.is_shared,
            'version': self.version,
            'parent_version': self.parent_version,
            'tags': json.loads(self.tags) if self.tags else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
        }
    
    def __repr__(self):
        return f"<DashboardLayout(user={self.user_id}, name={self.name}, version={self.version})>"


class DashboardLayoutSnapshot(Base):
    """
    仪表盘布局快照模型
    用于布局版本管理和回滚
    """
    __tablename__ = "dashboard_layout_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联布局
    layout_id = Column(String(64), nullable=False, index=True)
    
    # 快照版本
    version = Column(Integer, nullable=False)
    
    # 快照数据 (完整布局JSON)
    snapshot_data = Column(Text, nullable=False)
    
    # 快照说明
    comment = Column(String(256))
    
    # 创建信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(64))
    
    # 索引
    __table_args__ = (
        Index('idx_layout_version', 'layout_id', 'version'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'layout_id': self.layout_id,
            'version': self.version,
            'snapshot_data': json.loads(self.snapshot_data) if self.snapshot_data else {},
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
        }


# ============== 数据类 ==============

@dataclass
class LayoutPosition:
    """布局位置"""
    x: int = 0
    y: int = 0
    width: int = 2
    height: int = 2
    min_width: int = 1
    min_height: int = 1
    z_index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutPosition':
        return cls(
            x=data.get('x', 0),
            y=data.get('y', 0),
            width=data.get('width', 2),
            height=data.get('height', 2),
            min_width=data.get('min_width', 1),
            min_height=data.get('min_height', 1),
            z_index=data.get('z_index', 0),
        )


@dataclass
class LayoutWidget:
    """布局组件"""
    widget_id: str
    widget_type: str
    title: str
    metric_names: List[str] = field(default_factory=list)
    device_filter: Optional[str] = None
    time_range: str = "24h"
    refresh_interval: int = 60
    config: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutWidget':
        return cls(
            widget_id=data.get('widget_id', ''),
            widget_type=data.get('widget_type', 'stat_card'),
            title=data.get('title', ''),
            metric_names=data.get('metric_names', []),
            device_filter=data.get('device_filter'),
            time_range=data.get('time_range', '24h'),
            refresh_interval=data.get('refresh_interval', 60),
            config=data.get('config', {}),
            tags=data.get('tags', []),
            description=data.get('description', ''),
        )


@dataclass
class LayoutItem:
    """布局项（组件+位置）"""
    item_id: str
    widget: LayoutWidget
    position: LayoutPosition
    visibility: bool = True
    locked: bool = False
    collapsed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'item_id': self.item_id,
            'widget': self.widget.to_dict() if isinstance(self.widget, LayoutWidget) else self.widget,
            'position': self.position.to_dict() if isinstance(self.position, LayoutPosition) else self.position,
            'visibility': self.visibility,
            'locked': self.locked,
            'collapsed': self.collapsed,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutItem':
        widget_data = data.get('widget', {})
        position_data = data.get('position', {})
        
        widget = widget_data if isinstance(widget_data, dict) else {}
        position = position_data if isinstance(position_data, dict) else {}
        
        return cls(
            item_id=data.get('item_id', ''),
            widget=LayoutWidget.from_dict(widget) if isinstance(widget, dict) else widget,
            position=LayoutPosition.from_dict(position) if isinstance(position, dict) else position,
            visibility=data.get('visibility', True),
            locked=data.get('locked', False),
            collapsed=data.get('collapsed', False),
        )


@dataclass
class ColumnConfig:
    """列配置"""
    column_id: str
    visible: bool = True
    width: int = 200
    order: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColumnConfig':
        return cls(
            column_id=data.get('column_id', ''),
            visible=data.get('visible', True),
            width=data.get('width', 200),
            order=data.get('order', 0),
        )


@dataclass
class DashboardLayoutData:
    """仪表盘布局数据"""
    layout_id: str
    user_id: str
    name: str = "默认布局"
    description: str = ""
    version: int = 1
    parent_version: Optional[int] = None
    grid_size: str = "medium"  # small, medium, large, xlarge
    columns: int = 12
    row_height: int = 80
    items: List[LayoutItem] = field(default_factory=list)
    column_config: List[ColumnConfig] = field(default_factory=list)
    theme: str = "default"
    is_default: bool = False
    is_shared: bool = False
    tags: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'layout_id': self.layout_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'parent_version': self.parent_version,
            'grid_size': self.grid_size,
            'columns': self.columns,
            'row_height': self.row_height,
            'items': [item.to_dict() if isinstance(item, LayoutItem) else item for item in self.items],
            'column_config': [c.to_dict() if isinstance(c, ColumnConfig) else c for c in self.column_config],
            'theme': self.theme,
            'is_default': self.is_default,
            'is_shared': self.is_shared,
            'tags': self.tags,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DashboardLayoutData':
        items = [
            LayoutItem.from_dict(item) if isinstance(item, dict) else item 
            for item in data.get('items', [])
        ]
        column_config = [
            ColumnConfig.from_dict(c) if isinstance(c, dict) else c
            for c in data.get('column_config', [])
        ]
        
        return cls(
            layout_id=data.get('layout_id', ''),
            user_id=data.get('user_id', ''),
            name=data.get('name', '默认布局'),
            description=data.get('description', ''),
            version=data.get('version', 1),
            parent_version=data.get('parent_version'),
            grid_size=data.get('grid_size', 'medium'),
            columns=data.get('columns', 12),
            row_height=data.get('row_height', 80),
            items=items,
            column_config=column_config,
            theme=data.get('theme', 'default'),
            is_default=data.get('is_default', False),
            is_shared=data.get('is_shared', False),
            tags=data.get('tags', []),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            created_by=data.get('created_by'),
            updated_by=data.get('updated_by'),
        )
    
    @classmethod
    def from_db_model(cls, db_layout: DashboardLayout) -> 'DashboardLayoutData':
        """从数据库模型创建"""
        items_data = json.loads(db_layout.items) if db_layout.items else []
        items = [LayoutItem.from_dict(item) for item in items_data]
        
        column_config_data = json.loads(db_layout.column_config) if db_layout.column_config else []
        column_config = [ColumnConfig.from_dict(c) for c in column_config_data]
        
        config_data = json.loads(db_layout.config) if db_layout.config else {}
        
        return cls(
            layout_id=db_layout.layout_id,
            user_id=db_layout.user_id,
            name=db_layout.name,
            description=db_layout.description or '',
            version=db_layout.version,
            parent_version=db_layout.parent_version,
            grid_size=config_data.get('grid_size', 'medium'),
            columns=config_data.get('columns', 12),
            row_height=config_data.get('row_height', 80),
            items=items,
            column_config=column_config,
            theme=db_layout.theme,
            is_default=db_layout.is_default,
            is_shared=db_layout.is_shared,
            tags=json.loads(db_layout.tags) if db_layout.tags else [],
            created_at=db_layout.created_at.isoformat() if db_layout.created_at else None,
            updated_at=db_layout.updated_at.isoformat() if db_layout.updated_at else None,
            created_by=db_layout.created_by,
            updated_by=db_layout.updated_by,
        )


# ============== 默认列配置 ==============

DEFAULT_COLUMNS = [
    {'column_id': 'device_status', 'visible': True, 'width': 120, 'order': 0},
    {'column_id': 'cpu_usage', 'visible': True, 'width': 100, 'order': 1},
    {'column_id': 'memory_usage', 'visible': True, 'width': 100, 'order': 2},
    {'column_id': 'disk_usage', 'visible': True, 'width': 100, 'order': 3},
    {'column_id': 'network_traffic', 'visible': True, 'width': 120, 'order': 4},
    {'column_id': 'alert_count', 'visible': True, 'width': 80, 'order': 5},
    {'column_id': 'online_time', 'visible': True, 'width': 120, 'order': 6},
]


# ============== 布局服务 ==============

class DashboardLayoutService:
    """
    仪表盘布局服务
    提供布局的CRUD操作
    """
    
    def __init__(self, db_session=None):
        """
        初始化布局服务
        
        Args:
            db_session: SQLAlchemy数据库会话
        """
        self._db_session = db_session
        self.logger = logging.getLogger(__name__)
    
    def _get_session(self):
        """获取数据库会话"""
        if self._db_session:
            return self._db_session
        from modules.foundation.db_models.base import _db_manager
        return _db_manager.get_session()
    
    def get_user_layout(self, user_id: str, layout_id: Optional[str] = None) -> Optional[DashboardLayoutData]:
        """
        获取用户布局
        
        Args:
            user_id: 用户ID
            layout_id: 布局ID（可选，为空则返回用户默认布局）
            
        Returns:
            布局数据或None
        """
        session = self._get_session()
        try:
            query = session.query(DashboardLayout).filter(DashboardLayout.user_id == user_id)
            
            if layout_id:
                query = query.filter(DashboardLayout.layout_id == layout_id)
            else:
                query = query.filter(DashboardLayout.is_default == True)
            
            db_layout = query.first()
            if db_layout:
                return DashboardLayoutData.from_db_model(db_layout)
            return None
        except Exception as e:
            self.logger.error(f"获取布局失败: {e}")
            return None
        finally:
            if not self._db_session:
                session.close()
    
    def save_layout(
        self,
        user_id: str,
        layout_data: DashboardLayoutData,
        created_by: Optional[str] = None
    ) -> DashboardLayoutData:
        """
        保存用户布局（创建或更新）
        
        Args:
            user_id: 用户ID
            layout_data: 布局数据
            created_by: 创建者
            
        Returns:
            保存后的布局数据
        """
        session = self._get_session()
        try:
            # 查找现有布局
            existing = session.query(DashboardLayout).filter(
                DashboardLayout.user_id == user_id,
                DashboardLayout.layout_id == layout_data.layout_id
            ).first()
            
            if existing:
                # 更新
                existing.name = layout_data.name
                existing.description = layout_data.description
                existing.config = json.dumps({
                    'grid_size': layout_data.grid_size,
                    'columns': layout_data.columns,
                    'row_height': layout_data.row_height,
                })
                existing.items = json.dumps([
                    item.to_dict() if isinstance(item, LayoutItem) else item 
                    for item in layout_data.items
                ])
                existing.column_config = json.dumps([
                    c.to_dict() if isinstance(c, ColumnConfig) else c 
                    for c in layout_data.column_config
                ])
                existing.theme = layout_data.theme
                existing.is_default = layout_data.is_default
                existing.is_shared = layout_data.is_shared
                existing.tags = json.dumps(layout_data.tags)
                existing.version = existing.version + 1
                existing.updated_at = datetime.now()
                existing.updated_by = created_by
                
                db_layout = existing
            else:
                # 创建
                config = {
                    'grid_size': layout_data.grid_size,
                    'columns': layout_data.columns,
                    'row_height': layout_data.row_height,
                }
                
                db_layout = DashboardLayout(
                    user_id=user_id,
                    layout_id=layout_data.layout_id,
                    name=layout_data.name,
                    description=layout_data.description,
                    config=json.dumps(config),
                    items=json.dumps([
                        item.to_dict() if isinstance(item, LayoutItem) else item 
                        for item in layout_data.items
                    ]),
                    column_config=json.dumps([
                        c.to_dict() if isinstance(c, ColumnConfig) else c 
                        for c in layout_data.column_config
                    ]),
                    theme=layout_data.theme,
                    is_default=layout_data.is_default,
                    is_shared=layout_data.is_shared,
                    tags=json.dumps(layout_data.tags),
                    version=1,
                    created_by=created_by,
                    updated_by=created_by,
                )
                session.add(db_layout)
            
            session.commit()
            session.refresh(db_layout)
            
            return DashboardLayoutData.from_db_model(db_layout)
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存布局失败: {e}")
            raise
        finally:
            if not self._db_session:
                session.close()
    
    def delete_layout(self, user_id: str, layout_id: str) -> bool:
        """
        删除用户布局
        
        Args:
            user_id: 用户ID
            layout_id: 布局ID
            
        Returns:
            是否删除成功
        """
        session = self._get_session()
        try:
            result = session.query(DashboardLayout).filter(
                DashboardLayout.user_id == user_id,
                DashboardLayout.layout_id == layout_id
            ).delete()
            session.commit()
            return result > 0
        except Exception as e:
            session.rollback()
            self.logger.error(f"删除布局失败: {e}")
            return False
        finally:
            if not self._db_session:
                session.close()
    
    def list_user_layouts(self, user_id: str) -> List[DashboardLayoutData]:
        """
        列出用户所有布局
        
        Args:
            user_id: 用户ID
            
        Returns:
            布局列表
        """
        session = self._get_session()
        try:
            layouts = session.query(DashboardLayout).filter(
                DashboardLayout.user_id == user_id
            ).order_by(DashboardLayout.updated_at.desc()).all()
            
            return [DashboardLayoutData.from_db_model(layout) for layout in layouts]
        except Exception as e:
            self.logger.error(f"列出布局失败: {e}")
            return []
        finally:
            if not self._db_session:
                session.close()
    
    def create_snapshot(
        self,
        layout_id: str,
        version: int,
        snapshot_data: DashboardLayoutData,
        created_by: Optional[str] = None,
        comment: Optional[str] = None
    ) -> bool:
        """
        创建布局快照
        
        Args:
            layout_id: 布局ID
            version: 版本号
            snapshot_data: 快照数据
            created_by: 创建者
            comment: 快照说明
            
        Returns:
            是否创建成功
        """
        session = self._get_session()
        try:
            snapshot = DashboardLayoutSnapshot(
                layout_id=layout_id,
                version=version,
                snapshot_data=json.dumps(snapshot_data.to_dict()),
                comment=comment,
                created_by=created_by,
            )
            session.add(snapshot)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"创建快照失败: {e}")
            return False
        finally:
            if not self._db_session:
                session.close()
    
    def get_snapshot(self, layout_id: str, version: int) -> Optional[DashboardLayoutData]:
        """
        获取布局快照
        
        Args:
            layout_id: 布局ID
            version: 版本号
            
        Returns:
            快照数据或None
        """
        session = self._get_session()
        try:
            snapshot = session.query(DashboardLayoutSnapshot).filter(
                DashboardLayoutSnapshot.layout_id == layout_id,
                DashboardLayoutSnapshot.version == version
            ).first()
            
            if snapshot:
                data = json.loads(snapshot.snapshot_data)
                return DashboardLayoutData.from_dict(data)
            return None
        except Exception as e:
            self.logger.error(f"获取快照失败: {e}")
            return None
        finally:
            if not self._db_session:
                session.close()
    
    def create_default_layout(self, user_id: str) -> DashboardLayoutData:
        """
        为用户创建默认布局
        
        Args:
            user_id: 用户ID
            
        Returns:
            默认布局数据
        """
        import uuid
        
        # 检查是否已有默认布局
        existing = self.get_user_layout(user_id)
        if existing:
            return existing
        
        # 创建默认布局
        default_layout = DashboardLayoutData(
            layout_id=f"default_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            name="默认布局",
            description="系统默认布局",
            version=1,
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
                    visibility=True,
                ),
                LayoutItem(
                    item_id=f"item_{uuid.uuid4().hex[:8]}",
                    widget=LayoutWidget(
                        widget_id=f"widget_{uuid.uuid4().hex[:8]}",
                        widget_type="alert_count",
                        title="告警数量",
                        metric_names=["alert_count"],
                    ),
                    position=LayoutPosition(x=3, y=0, width=3, height=2),
                    visibility=True,
                ),
            ],
            column_config=[ColumnConfig.from_dict(c) for c in DEFAULT_COLUMNS],
            is_default=True,
        )
        
        return self.save_layout(user_id, default_layout, created_by="system")
