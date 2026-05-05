-- FM-04 权限管理模块 - 审计日志表迁移
-- Migration: 003_create_audit_logs_table.sql

-- 创建审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(36),
    username VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    level VARCHAR(20) NOT NULL DEFAULT 'info',
    request_method VARCHAR(10),
    request_path VARCHAR(255),
    request_body TEXT,
    response_status INT,
    error_message TEXT,
    duration_ms INT,
    metadata JSON,
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_user_id (timestamp),
    INDEX idx_username (username),
    INDEX idx_action (action),
    INDEX idx_resource (resource_type, resource_id),
    INDEX idx_status (status),
    INDEX idx_level (level),
    INDEX idx_ip_address (ip_address),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建审计日志表分区（按月分区，用于大数据量场景）
-- 注意：MySQL 8.0+ 支持此语法
-- ALTER TABLE audit_logs PARTITION BY RANGE (UNIX_TIMESTAMP(timestamp)) (
--     PARTITION p_2024_01 VALUES LESS THAN (UNIX_TIMESTAMP('2024-02-01')),
--     PARTITION p_2024_02 VALUES LESS THAN (UNIX_TIMESTAMP('2024-03-01')),
--     -- 添加更多月份分区
-- );

-- 创建审计配置表
CREATE TABLE IF NOT EXISTS audit_configs (
    id VARCHAR(36) PRIMARY KEY,
    config_key VARCHAR(50) UNIQUE NOT NULL,
    config_value JSON NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认审计配置
INSERT INTO audit_configs (id, config_key, config_value, description) VALUES
    (UUID(), 'retention_days', '90', '审计日志保留天数'),
    (UUID(), 'log_level', '"info"', '日志记录级别'),
    (UUID(), 'log_failed_login', 'true', '是否记录失败登录'),
    (UUID(), 'log_sensitive_actions', 'true', '是否记录敏感操作');
