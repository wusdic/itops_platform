-- BM-01 监控告警模块
-- 告警工单表

CREATE TABLE IF NOT EXISTS alert_tickets (
    id VARCHAR(64) PRIMARY KEY COMMENT '工单ID',
    alert_id VARCHAR(128) NOT NULL COMMENT '告警ID',
    rule_id VARCHAR(64) NOT NULL COMMENT '规则ID',
    rule_name VARCHAR(255) NOT NULL COMMENT '规则名称',
    severity VARCHAR(16) NOT NULL COMMENT '严重级别',
    status VARCHAR(16) NOT NULL DEFAULT 'open' COMMENT '状态: open/acknowledged/assigned/in_progress/resolved/closed',
    
    -- 基本信息
    device_id VARCHAR(64) NOT NULL COMMENT '设备ID',
    metric_name VARCHAR(128) NOT NULL COMMENT '指标名称',
    value DECIMAL(20, 4) NOT NULL COMMENT '当前值',
    threshold_value DECIMAL(20, 4) NOT NULL COMMENT '阈值',
    message TEXT COMMENT '消息',
    
    -- 时间和用户
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP NULL COMMENT '确认时间',
    acknowledged_by VARCHAR(64) COMMENT '确认人',
    resolved_at TIMESTAMP NULL COMMENT '解决时间',
    resolved_by VARCHAR(64) COMMENT '解决人',
    closed_at TIMESTAMP NULL COMMENT '关闭时间',
    closed_by VARCHAR(64) COMMENT '关闭人',
    
    -- 分配信息
    assignee VARCHAR(64) COMMENT '分配人',
    assignee_group VARCHAR(64) COMMENT '分配组',
    
    -- 升级信息
    escalation_level INT DEFAULT 0 COMMENT '升级级别',
    escalation_count INT DEFAULT 0 COMMENT '升级次数',
    last_escalated_at TIMESTAMP NULL COMMENT '最后升级时间',
    
    -- 解决方案
    resolution TEXT COMMENT '解决方案',
    
    -- 标签和注释 (JSON)
    labels TEXT COMMENT '标签JSON',
    annotations TEXT COMMENT '注释JSON',
    
    -- 关联信息
    related_tickets TEXT COMMENT '关联工单ID列表，逗号分隔',
    linked_incidents TEXT COMMENT '关联事件ID列表，逗号分隔',
    
    -- 索引
    INDEX idx_alert_id (alert_id),
    INDEX idx_rule_id (rule_id),
    INDEX idx_device_id (device_id),
    INDEX idx_severity (severity),
    INDEX idx_status (status),
    INDEX idx_assignee (assignee),
    INDEX idx_assignee_group (assignee_group),
    INDEX idx_created_at (created_at),
    INDEX idx_closed_at (closed_at),
    INDEX idx_escalation_level (escalation_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='告警工单表';

-- 工单备注表
CREATE TABLE IF NOT EXISTS ticket_notes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(64) NOT NULL COMMENT '工单ID',
    content TEXT NOT NULL COMMENT '备注内容',
    user VARCHAR(64) NOT NULL COMMENT '用户',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='工单备注表';

-- 工单历史表
CREATE TABLE IF NOT EXISTS ticket_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(64) NOT NULL COMMENT '工单ID',
    action VARCHAR(64) NOT NULL COMMENT '动作',
    details TEXT COMMENT '详情JSON',
    operator VARCHAR(64) COMMENT '操作人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='工单历史表';
