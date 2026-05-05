"""
创建工单相关表
"""

SQL_UP = """
-- 工单表
CREATE TABLE IF NOT EXISTS `work_orders` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `order_no` VARCHAR(64) NOT NULL COMMENT '工单编号',
    `order_type` ENUM('fault', 'change', 'inspection', 'security', 'demand', 'question', 'other') NOT NULL COMMENT '工单类型',
    `priority` ENUM('P1', 'P2', 'P3', 'P4') DEFAULT 'P3' COMMENT '优先级',
    `title` VARCHAR(256) NOT NULL COMMENT '标题',
    `description` TEXT COMMENT '描述',
    `device_id` INT COMMENT '关联设备ID',
    `device_name` VARCHAR(128) COMMENT '关联设备名称',
    `device_ip` VARCHAR(64) COMMENT '关联设备IP',
    `alert_id` INT COMMENT '关联告警ID',
    `business_id` INT COMMENT '业务系统ID',
    `business_name` VARCHAR(128) COMMENT '业务系统名称',
    `status` ENUM('pending', 'processing', 'pending_approval', 'approved', 'rejected', 'resolved', 'closed', 'cancelled') DEFAULT 'pending' COMMENT '状态',
    `impact` VARCHAR(32) COMMENT '影响范围',
    `urgency` VARCHAR(32) COMMENT '紧急程度',
    `expected_start` DATETIME COMMENT '期望开始时间',
    `expected_end` DATETIME COMMENT '期望结束时间',
    `actual_start` DATETIME COMMENT '实际开始时间',
    `actual_end` DATETIME COMMENT '实际结束时间',
    `sla_response_time` INT COMMENT 'SLA响应时间(分钟)',
    `sla_resolve_time` INT COMMENT 'SLA解决时间(分钟)',
    `sla_response_at` DATETIME COMMENT '响应时间',
    `sla_resolved_at` DATETIME COMMENT '解决时间',
    `creator` VARCHAR(64) NOT NULL COMMENT '创建人',
    `creator_email` VARCHAR(128) COMMENT '创建人邮箱',
    `assignee` VARCHAR(64) COMMENT '处理人',
    `assignee_email` VARCHAR(128) COMMENT '处理人邮箱',
    `approver` VARCHAR(64) COMMENT '审批人',
    `change_type` VARCHAR(64) COMMENT '变更类型',
    `change_impact` TEXT COMMENT '变更影响',
    `rollback_plan` TEXT COMMENT '回滚方案',
    `test_plan` TEXT COMMENT '测试计划',
    `approval_status` VARCHAR(32) COMMENT '审批状态',
    `approval_history` TEXT COMMENT '审批历史JSON',
    `handling_progress` TEXT COMMENT '处理进度JSON',
    `resolution` TEXT COMMENT '解决方案',
    `root_cause` TEXT COMMENT '根本原因',
    `improvement` TEXT COMMENT '改进措施',
    `satisfaction` INT COMMENT '满意度评分(1-5)',
    `feedback` TEXT COMMENT '反馈意见',
    `attachments` TEXT COMMENT '附件列表JSON',
    `tags` VARCHAR(256) COMMENT '标签',
    `remark` TEXT COMMENT '备注',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `closed_at` DATETIME COMMENT '关闭时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_order_no` (`order_no`),
    INDEX `idx_order_type` (`order_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_priority` (`priority`),
    INDEX `idx_order_status_priority` (`status`, `priority`),
    INDEX `idx_order_creator_time` (`creator`, `created_at`),
    INDEX `idx_order_assignee_status` (`assignee`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单表';

-- 工单流程记录表
CREATE TABLE IF NOT EXISTS `work_order_flows` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `work_order_id` INT NOT NULL COMMENT '工单ID',
    `step_name` VARCHAR(64) NOT NULL COMMENT '步骤名称',
    `step_order` INT COMMENT '步骤顺序',
    `operator` VARCHAR(64) COMMENT '操作人',
    `operator_email` VARCHAR(128) COMMENT '操作人邮箱',
    `action` VARCHAR(32) COMMENT '操作类型',
    `from_status` VARCHAR(32) COMMENT '原状态',
    `to_status` VARCHAR(32) COMMENT '新状态',
    `comment` TEXT COMMENT '意见/备注',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    PRIMARY KEY (`id`),
    INDEX `idx_flow_workorder` (`work_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单流程记录表';

-- 流程实例表
CREATE TABLE IF NOT EXISTS `flow_instances` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `instance_id` VARCHAR(64) NOT NULL COMMENT '流程实例ID',
    `work_order_id` INT NOT NULL COMMENT '工单ID',
    `flow_id` VARCHAR(64) NOT NULL COMMENT '流程定义ID',
    `flow_version` VARCHAR(32) COMMENT '流程版本',
    `flow_name` VARCHAR(128) COMMENT '流程名称',
    `current_node_id` VARCHAR(64) COMMENT '当前节点ID',
    `current_node_name` VARCHAR(128) COMMENT '当前节点名称',
    `status` VARCHAR(32) DEFAULT 'running' COMMENT '状态',
    `context_data` TEXT COMMENT '上下文数据JSON',
    `started_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_instance_id` (`instance_id`),
    INDEX `idx_flow_workorder` (`work_order_id`),
    INDEX `idx_flow_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='流程实例表';

-- 流程历史记录表
CREATE TABLE IF NOT EXISTS `flow_history` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `instance_id` INT NOT NULL COMMENT '流程实例ID',
    `work_order_id` INT NOT NULL COMMENT '工单ID',
    `node_id` VARCHAR(64) COMMENT '节点ID',
    `node_name` VARCHAR(128) COMMENT '节点名称',
    `node_type` VARCHAR(32) COMMENT '节点类型',
    `action` VARCHAR(32) COMMENT '操作类型',
    `operator` VARCHAR(64) COMMENT '操作人',
    `input_data` TEXT COMMENT '输入数据JSON',
    `output_data` TEXT COMMENT '输出数据JSON',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    PRIMARY KEY (`id`),
    INDEX `idx_history_instance` (`instance_id`),
    INDEX `idx_history_workorder` (`work_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='流程历史记录表';

-- 审批记录表
CREATE TABLE IF NOT EXISTS `approval_records` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `work_order_id` INT NOT NULL COMMENT '工单ID',
    `flow_instance_id` INT COMMENT '流程实例ID',
    `approval_node_id` VARCHAR(64) COMMENT '审批节点ID',
    `approver` VARCHAR(64) COMMENT '审批人',
    `approver_email` VARCHAR(128) COMMENT '审批人邮箱',
    `approver_role` VARCHAR(64) COMMENT '审批人角色',
    `mode` VARCHAR(16) DEFAULT 'one' COMMENT '审批模式',
    `status` VARCHAR(32) DEFAULT 'pending' COMMENT '审批状态',
    `action` VARCHAR(16) COMMENT '操作类型',
    `comment` TEXT COMMENT '审批意见',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `expires_at` DATETIME COMMENT '过期时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `delegated_from` VARCHAR(64) COMMENT '委托人',
    `delegated_to` VARCHAR(64) COMMENT '被委托人',
    PRIMARY KEY (`id`),
    INDEX `idx_approval_workorder` (`work_order_id`),
    INDEX `idx_approval_approver` (`approver`),
    INDEX `idx_approval_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审批记录表';

-- 审批代理配置表
CREATE TABLE IF NOT EXISTS `approval_delegations` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `delegator` VARCHAR(64) NOT NULL COMMENT '委托人',
    `delegator_email` VARCHAR(128) COMMENT '委托人邮箱',
    `delegate` VARCHAR(64) NOT NULL COMMENT '被委托人',
    `delegate_email` VARCHAR(128) COMMENT '被委托人邮箱',
    `start_time` DATETIME COMMENT '代理开始时间',
    `end_time` DATETIME COMMENT '代理结束时间',
    `reason` TEXT COMMENT '代理原因',
    `scope` TEXT COMMENT '代理范围JSON',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否生效',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_delegation_delegator` (`delegator`),
    INDEX `idx_delegation_delegate` (`delegate`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审批代理配置表';

-- 变更记录表
CREATE TABLE IF NOT EXISTS `change_records` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `change_no` VARCHAR(64) NOT NULL COMMENT '变更编号',
    `work_order_id` INT NOT NULL COMMENT '工单ID',
    `title` VARCHAR(256) NOT NULL COMMENT '变更标题',
    `change_type` VARCHAR(64) COMMENT '变更类型',
    `category` VARCHAR(64) COMMENT '变更类别',
    `risk_level` VARCHAR(32) COMMENT '风险等级',
    `impact` TEXT COMMENT '影响范围',
    `rollback_plan` TEXT COMMENT '回滚方案',
    `test_plan` TEXT COMMENT '测试计划',
    `scheduled_start` DATETIME COMMENT '计划开始时间',
    `scheduled_end` DATETIME COMMENT '计划结束时间',
    `actual_start` DATETIME COMMENT '实际开始时间',
    `actual_end` DATETIME COMMENT '实际结束时间',
    `maintenance_window` VARCHAR(128) COMMENT '维护窗口',
    `implementor` VARCHAR(64) COMMENT '实施人',
    `implementor_email` VARCHAR(128) COMMENT '实施人邮箱',
    `status` VARCHAR(32) DEFAULT 'draft' COMMENT '变更状态',
    `review_board` VARCHAR(64) COMMENT '评审委员会',
    `reviewers` TEXT COMMENT '评审人列表JSON',
    `review_comments` TEXT COMMENT '评审意见JSON',
    `implementation_steps` TEXT COMMENT '实施步骤JSON',
    `implementation_log` TEXT COMMENT '实施日志JSON',
    `verification_result` TEXT COMMENT '验证结果',
    `verification_by` VARCHAR(64) COMMENT '验证人',
    `verification_at` DATETIME COMMENT '验证时间',
    `rollback_reason` TEXT COMMENT '回滚原因',
    `rollback_at` DATETIME COMMENT '回滚时间',
    `rollback_by` VARCHAR(64) COMMENT '回滚人',
    `approval_status` VARCHAR(32) COMMENT '审批状态',
    `approvers` TEXT COMMENT '审批人JSON',
    `approval_history` TEXT COMMENT '审批历史JSON',
    `related_devices` TEXT COMMENT '关联设备JSON',
    `related_services` TEXT COMMENT '关联服务JSON',
    `related_configs` TEXT COMMENT '关联配置JSON',
    `attachments` TEXT COMMENT '附件列表JSON',
    `applicant` VARCHAR(64) NOT NULL COMMENT '申请人',
    `applicant_email` VARCHAR(128) COMMENT '申请人邮箱',
    `applicant_dept` VARCHAR(128) COMMENT '申请部门',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_change_no` (`change_no`),
    INDEX `idx_change_workorder` (`work_order_id`),
    INDEX `idx_change_status` (`status`),
    INDEX `idx_change_applicant` (`applicant`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='变更记录表';
"""

SQL_DOWN = """
DROP TABLE IF EXISTS `change_records`;
DROP TABLE IF EXISTS `approval_delegations`;
DROP TABLE IF EXISTS `approval_records`;
DROP TABLE IF EXISTS `flow_history`;
DROP TABLE IF EXISTS `flow_instances`;
DROP TABLE IF EXISTS `work_order_flows`;
DROP TABLE IF EXISTS `work_orders`;
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
