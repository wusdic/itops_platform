"""
工单相关数据库迁移
"""

from .m001_create_work_orders_table import migrate_up, migrate_down

__all__ = ['migrate_up', 'migrate_down']
