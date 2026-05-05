-- FM-04 权限管理模块 - LDAP同步表迁移
-- Migration: 004_create_ldap_sync_table.sql

-- 创建LDAP同步记录表
CREATE TABLE IF NOT EXISTS ldap_sync_history (
    id VARCHAR(36) PRIMARY KEY,
    sync_type VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    users_synced INT DEFAULT 0,
    groups_synced INT DEFAULT 0,
    errors JSON,
    metadata JSON,
    
    INDEX idx_sync_type (sync_type),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建LDAP用户映射表
CREATE TABLE IF NOT EXISTS ldap_user_mapping (
    id VARCHAR(36) PRIMARY KEY,
    ldap_dn VARCHAR(255) UNIQUE NOT NULL,
    ldap_username VARCHAR(100) NOT NULL,
    local_user_id VARCHAR(36),
    last_sync TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    metadata JSON,
    
    INDEX idx_ldap_username (ldap_username),
    INDEX idx_local_user_id (local_user_id),
    FOREIGN KEY (local_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建LDAP组映射表
CREATE TABLE IF NOT EXISTS ldap_group_mapping (
    id VARCHAR(36) PRIMARY KEY,
    ldap_dn VARCHAR(255) UNIQUE NOT NULL,
    ldap_group_name VARCHAR(100) NOT NULL,
    local_role_id VARCHAR(36),
    last_sync TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    metadata JSON,
    
    INDEX idx_ldap_group_name (ldap_group_name),
    INDEX idx_local_role_id (local_role_id),
    FOREIGN KEY (local_role_id) REFERENCES roles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建LDAP配置表
CREATE TABLE IF NOT EXISTS ldap_configs (
    id VARCHAR(36) PRIMARY KEY,
    config_name VARCHAR(50) UNIQUE NOT NULL,
    server VARCHAR(255) NOT NULL,
    port INT NOT NULL DEFAULT 389,
    use_ssl BOOLEAN NOT NULL DEFAULT FALSE,
    start_tls BOOLEAN NOT NULL DEFAULT FALSE,
    bind_dn VARCHAR(255),
    bind_password_encrypted TEXT,
    base_dn VARCHAR(255) NOT NULL,
    user_filter VARCHAR(255),
    group_filter VARCHAR(255),
    user_search_base VARCHAR(255),
    group_search_base VARCHAR(255),
    username_attr VARCHAR(50) DEFAULT 'sAMAccountName',
    email_attr VARCHAR(50) DEFAULT 'mail',
    display_name_attr VARCHAR(50) DEFAULT 'displayName',
    group_member_attr VARCHAR(50) DEFAULT 'member',
    sync_interval INT DEFAULT 3600,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_config_name (config_name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入示例LDAP配置（需要根据实际环境修改）
INSERT INTO ldap_configs (id, config_name, server, port, base_dn, user_filter, group_filter, is_active) VALUES
    (UUID(), 'default', 'ldap.example.com', 389, 'dc=example,dc=com', 
     '(objectClass=user)', '(objectClass=group)', TRUE);
