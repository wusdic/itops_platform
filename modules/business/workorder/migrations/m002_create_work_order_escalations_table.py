"""
创建工单升级记录表
用于存储SLA超时升级记录
"""

SQL_UP = """
-- 工单升级记录表
CREATE TABLE IF NOT EXISTS `work_order_escalations` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `work_order_id` INT NOT NULL COMMENT '工单ID',
    `escalation_level` INT NOT NULL COMMENT '升级级别(1-4)',
    `notified_roles` TEXT COMMENT '通知角色JSON',
    `breach_duration_minutes` INT COMMENT '超时时长(分钟)',
    `sla_type` VARCHAR(32) COMMENT 'SLA类型: response/resolve',
    `is_notified` BOOLEAN DEFAULT FALSE COMMENT '是否已通知',
    `notified_at` DATETIME COMMENT '通知时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_escalation_workorder` (`work_order_id`),
    INDEX `idx_escalation_level` (`escalation_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单升级记录表';
"""

SQL_DOWN = """
DROP TABLE IF EXISTS `work_order_escalations`;
"""


def migrate_up(db_connection):
    """执行迁移"""
    cursor = db_connection.cursor()
    for statement in SQL_UP.split(';'):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
    db_connection.commit()


def migrate_down(db_connection):
    """回滚迁移"""
    cursor = db_connection.cursor()
    for statement in SQL_DOWN.split(';'):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
    db_connection.commit()