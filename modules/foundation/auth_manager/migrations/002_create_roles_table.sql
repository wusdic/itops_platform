-- FM-04 权限管理模块 - 角色表迁移
-- Migration: 002_create_roles_table.sql

-- 创建角色表
CREATE TABLE IF NOT EXISTS roles (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    parent_role_id VARCHAR(36),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    metadata JSON,
    
    INDEX idx_name (name),
    INDEX idx_is_system (is_system),
    FOREIGN KEY (parent_role_id) REFERENCES roles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建权限表
CREATE TABLE IF NOT EXISTS permissions (
    id VARCHAR(36) PRIMARY KEY,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    
    UNIQUE KEY uk_resource_action (resource, action),
    INDEX idx_resource (resource),
    INDEX idx_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建角色-权限关联表
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id VARCHAR(36) NOT NULL,
    permission_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建用户-角色关联表
CREATE TABLE IF NOT EXISTS user_roles (
    user_id VARCHAR(36) NOT NULL,
    role_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认角色
INSERT INTO roles (id, name, description, is_system) VALUES
    ('role_admin', 'admin', '系统管理员，拥有所有权限', TRUE),
    ('role_operator', 'operator', '运维操作员，拥有资源管理权限', TRUE),
    ('role_viewer', 'viewer', '只读用户，仅能查看资源', TRUE);

-- 插入默认权限
INSERT INTO permissions (id, resource, action, description) VALUES
    ('perm_user_manage', 'user', 'manage', '管理用户'),
    ('perm_user_read', 'user', 'read', '查看用户'),
    ('perm_role_manage', 'role', 'manage', '管理角色'),
    ('perm_role_read', 'role', 'read', '查看角色'),
    ('perm_audit_read', 'audit', 'read', '查看审计日志'),
    ('perm_system_manage', 'system', 'manage', '管理系统'),
    ('perm_system_read', 'system', 'read', '查看系统'),
    ('perm_system_execute', 'system', 'execute', '执行系统操作'),
    ('perm_config_read', 'config', 'read', '查看配置'),
    ('perm_config_update', 'config', 'update', '修改配置'),
    ('perm_config_delete', 'config', 'delete', '删除配置');

-- 为admin角色分配所有权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_admin', id FROM permissions;

-- 为operator角色分配部分权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_operator', id FROM permissions 
WHERE resource IN ('user', 'system', 'config') 
AND action IN ('read', 'update', 'execute');

-- 为viewer角色分配读取权限
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_viewer', id FROM permissions 
WHERE action = 'read';
