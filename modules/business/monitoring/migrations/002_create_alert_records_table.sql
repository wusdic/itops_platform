-- BM-01 监控告警模块
-- 告警记录表

CREATE TABLE IF NOT EXISTS alert_records (
    id VARCHAR(128) PRIMARY KEY COMMENT '告警ID',
    rule_id VARCHAR(64) NOT NULL COMMENT '规则ID',
    rule_name VARCHAR(255) NOT NULL COMMENT '规则名称',
    severity VARCHAR(16) NOT NULL COMMENT '严重级别',
    state VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/firing/resolved/suppressed',
    
    -- 告警信息
    device_id VARCHAR(64) NOT NULL COMMENT '设备ID',
    metric_name VARCHAR(128) NOT NULL COMMENT '指标名称',
    value DECIMAL(20, 4) NOT NULL COMMENT '当前值',
    threshold_value DECIMAL(20, 4) NOT NULL COMMENT '阈值',
    message TEXT COMMENT '告警消息',
    
    -- 指纹和分组
    fingerprint VARCHAR(64) COMMENT '去重指纹',
    group_key VARCHAR(256) COMMENT '分组键',
    
    -- 时间信息
    fired_at TIMESTAMP NULL COMMENT '触发时间',
    resolved_at TIMESTAMP NULL COMMENT '恢复时间',
    last_eval_time TIMESTAMP NULL COMMENT '最后评估时间',
    
    -- 标签和注释 (JSON)
    labels TEXT COMMENT '标签JSON',
    annotations TEXT COMMENT '注释JSON',
    
    -- 更新信息
    update_count INT DEFAULT 0 COMMENT '更新次数',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 关联
    ticket_id VARCHAR(64) COMMENT '关联工单ID',
    
    -- 索引
    INDEX idx_rule_id (rule_id),
    INDEX idx_device_id (device_id),
    INDEX idx_severity (severity),
    INDEX idx_state (state),
    INDEX idx_fired_at (fired_at),
    INDEX idx_resolved_at (resolved_at),
    INDEX idx_fingerprint (fingerprint),
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_device_state (device_id, state),
    INDEX idx_rule_state (rule_id, state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='告警记录表';

-- 告警状态变更历史表
CREATE TABLE IF NOT EXISTS alert_state_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    alert_id VARCHAR(128) NOT NULL COMMENT '告警ID',
    from_state VARCHAR(16) COMMENT '原状态',
    to_state VARCHAR(16) NOT NULL COMMENT '新状态',
    reason TEXT COMMENT '变更原因',
    operator VARCHAR(64) COMMENT '操作人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_alert_id (alert_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='告警状态变更历史表';
