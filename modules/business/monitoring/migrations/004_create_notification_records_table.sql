-- BM-01 监控告警模块
-- 通知记录表

CREATE TABLE IF NOT EXISTS notification_records (
    id VARCHAR(64) PRIMARY KEY COMMENT '通知ID',
    channel VARCHAR(32) NOT NULL COMMENT '渠道: in_app/email/wechat_work/dingtalk/sms/webhook',
    priority INT DEFAULT 2 COMMENT '优先级: 1-4',
    
    -- 接收者
    recipients TEXT NOT NULL COMMENT '接收者列表JSON',
    
    -- 内容
    title VARCHAR(512) NOT NULL COMMENT '标题',
    content TEXT COMMENT '内容',
    
    -- 来源信息
    source_type VARCHAR(32) COMMENT '来源类型: alert/ticket/system',
    source_id VARCHAR(128) COMMENT '来源ID',
    
    -- 上下文
    context TEXT COMMENT '上下文JSON',
    
    -- 状态
    status VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/sending/sent/failed/rate_limited',
    delivery_status VARCHAR(64) COMMENT '投递状态',
    error_message TEXT COMMENT '错误消息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL COMMENT '发送时间',
    read_at TIMESTAMP NULL COMMENT '阅读时间',
    scheduled_at TIMESTAMP NULL COMMENT '计划发送时间',
    
    -- 模板信息
    template_id VARCHAR(64) COMMENT '模板ID',
    template_name VARCHAR(128) COMMENT '模板名称',
    
    -- 索引
    INDEX idx_channel (channel),
    INDEX idx_status (status),
    INDEX idx_source_type (source_type),
    INDEX idx_source_id (source_id),
    INDEX idx_created_at (created_at),
    INDEX idx_sent_at (sent_at),
    INDEX idx_recipients (recipients(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='通知记录表';

-- 通知回执表
CREATE TABLE IF NOT EXISTS notification_receipts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    notification_id VARCHAR(64) NOT NULL COMMENT '通知ID',
    recipient VARCHAR(128) NOT NULL COMMENT '接收者',
    channel VARCHAR(32) NOT NULL COMMENT '渠道',
    status VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '状态',
    delivered_at TIMESTAMP NULL COMMENT '投递时间',
    read_at TIMESTAMP NULL COMMENT '阅读时间',
    click_at TIMESTAMP NULL COMMENT '点击时间',
    error_message TEXT COMMENT '错误消息',
    metadata TEXT COMMENT '元数据JSON',
    
    INDEX idx_notification_id (notification_id),
    INDEX idx_recipient (recipient),
    INDEX idx_status (status),
    INDEX idx_delivered_at (delivered_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='通知回执表';

-- 用户通知设置表
CREATE TABLE IF NOT EXISTS user_notification_settings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    
    -- 渠道开关
    in_app_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT TRUE,
    wechat_enabled BOOLEAN DEFAULT FALSE,
    dingtalk_enabled BOOLEAN DEFAULT FALSE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    
    -- 联系方式
    email VARCHAR(255) COMMENT '邮箱',
    phone VARCHAR(32) COMMENT '手机号',
    wechat_userid VARCHAR(64) COMMENT '企业微信UserID',
    dingtalk_webhook VARCHAR(512) COMMENT '钉钉Webhook',
    
    -- 免打扰配置
    quiet_hours_enabled BOOLEAN DEFAULT FALSE,
    quiet_hours_start TIME COMMENT '免打扰开始时间',
    quiet_hours_end TIME COMMENT '免打扰结束时间',
    timezone VARCHAR(32) DEFAULT 'Asia/Shanghai',
    
    -- 订阅配置
    subscribed_rules TEXT COMMENT '订阅的规则ID列表JSON',
    min_severity VARCHAR(16) DEFAULT 'warning' COMMENT '最小接收严重级别',
    
    -- 通知频率限制
    max_daily_notifications INT DEFAULT 100 COMMENT '每日最大通知数',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='用户通知设置表';

-- 通知静默表
CREATE TABLE IF NOT EXISTS notification_silences (
    id VARCHAR(64) PRIMARY KEY COMMENT '静默ID',
    key VARCHAR(256) NOT NULL COMMENT '静默键',
    rule_id VARCHAR(64) COMMENT '规则ID',
    device_id VARCHAR(64) COMMENT '设备ID',
    
    -- 静默范围
    match_labels TEXT COMMENT '匹配的标签JSON',
    
    -- 静默时间
    start_at TIMESTAMP NOT NULL COMMENT '开始时间',
    end_at TIMESTAMP NOT NULL COMMENT '结束时间',
    
    -- 创建信息
    created_by VARCHAR(64) NOT NULL COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT COMMENT '静默原因',
    
    INDEX idx_key (key),
    INDEX idx_rule_id (rule_id),
    INDEX idx_device_id (device_id),
    INDEX idx_time_range (start_at, end_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='通知静默表';
