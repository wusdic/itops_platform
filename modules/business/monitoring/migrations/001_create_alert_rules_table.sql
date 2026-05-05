-- BM-01 监控告警模块
-- 告警规则表

CREATE TABLE IF NOT EXISTS alert_rules (
    id VARCHAR(64) PRIMARY KEY COMMENT '规则ID',
    name VARCHAR(255) NOT NULL COMMENT '规则名称',
    rule_type VARCHAR(32) NOT NULL DEFAULT 'threshold' COMMENT '规则类型: threshold/dynamic/trend/compound/health_check',
    enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    severity VARCHAR(16) NOT NULL DEFAULT 'warning' COMMENT '严重级别: info/warning/error/critical',
    
    -- 匹配条件
    metric_name VARCHAR(128) NOT NULL COMMENT '指标名称',
    devices TEXT COMMENT '设备ID列表，逗号分隔，*表示所有设备',
    
    -- 阈值配置 (JSON)
    thresholds TEXT COMMENT '阈值配置JSON数组',
    
    -- 趋势配置
    trend_direction VARCHAR(16) COMMENT '趋势方向: up/down/any',
    change_threshold DECIMAL(20, 4) DEFAULT 0 COMMENT '变化阈值',
    
    -- 复合规则配置
    sub_rules TEXT COMMENT '子规则ID列表，逗号分隔',
    composite_operator VARCHAR(8) DEFAULT 'AND' COMMENT '组合操作符: AND/OR',
    composite_threshold INT DEFAULT 1 COMMENT '触发子规则数量',
    
    -- 时间窗口配置
    duration INT DEFAULT 0 COMMENT '持续时间（秒）',
    evaluation_interval INT DEFAULT 60 COMMENT '评估间隔（秒）',
    
    -- 抑制配置
    suppress_interval INT DEFAULT 300 COMMENT '抑制间隔（秒）',
    deduplicate_key VARCHAR(128) COMMENT '去重键',
    
    -- 收敛配置
    group_by TEXT COMMENT '分组字段，逗号分隔',
    aggregation_window INT DEFAULT 60 COMMENT '聚合窗口（秒）',
    aggregation_func VARCHAR(32) DEFAULT 'count' COMMENT '聚合函数',
    
    -- 标签和注释 (JSON)
    labels TEXT COMMENT '标签JSON',
    annotations TEXT COMMENT '注释JSON',
    
    -- 通知配置
    notify_channels TEXT COMMENT '通知渠道列表，逗号分隔',
    escalate_after INT DEFAULT 0 COMMENT '升级等待时间（秒）',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(64) COMMENT '创建人',
    
    -- 索引
    INDEX idx_enabled (enabled),
    INDEX idx_metric_name (metric_name),
    INDEX idx_severity (severity),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='告警规则表';
