"""
工单相关数据库迁移
"""

from .m001_create_work_orders_table import migrate_up as migrate_up_001, migrate_down as migrate_down_001
from .m002_create_work_order_escalations_table import migrate_up as migrate_up_002, migrate_down as migrate_down_002

def migrate_up(db_connection):
    """执行所有迁移"""
    migrate_up_001(db_connection)
    migrate_up_002(db_connection)

def migrate_down(db_connection):
    """回滚所有迁移"""
    migrate_down_002(db_connection)
    migrate_down_001(db_connection)

__all__ = ['migrate_up', 'migrate_down']
