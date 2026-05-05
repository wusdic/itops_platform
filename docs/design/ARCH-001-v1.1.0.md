# IT运维智能平台 - 架构设计说明书 (SAD)

**文档编号**: ITOPS-SAD-001  
**当前版本**: v1.1.0  
**编制日期**: 2025-05-02  
**状态**: v1.0 基于需求SRS-001-v1.0.0  

---

## 文档版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0.0 | 2025-05-02 | 初始版本 |
| v1.1.0 | 2025-05-02 | 完善采集模块工具化设计、更新安全架构 |

---

## 1. 设计目标

### 1.1 核心原则
- **小而美起步**：中小用户开箱即用，单机部署
- **大而强扩展**：大型用户可水平扩展，多级管理
- **安全为本**：代码保护、数据安全、操作审计全覆盖
- **工具化设计**：采集模块独立复用，业务模块解耦

### 1.2 设计约束
- 纯内网部署，不依赖互联网
- 所有组件支持离线安装
- 支持MySQL作为主数据库

---

## 2. 系统架构

### 2.1 整体架构图

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                    客户端层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Web管理端   │  │   移动端     │  │   API客户端   │  │   CLI工具    │        │
│  │  (运维人员)   │  │  (审批提醒)  │  │ (自动化集成)  │  │  (批量操作)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                                    网关层                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  身份认证    │  │  权限控制    │  │  流量控制    │  │  请求日志    │        │
│  │  (JWT/APIKey)│  │  (RBAC)     │  │  (限流/熔断) │  │  (审计)      │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                                    服务层                                       │
│                                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                    │
│  │   配置服务      │  │   采集服务      │  │   监控服务      │                    │
│  │   (CFG模块)     │  │   (COL模块)     │  │   (MON模块)     │                    │
│  │ - 设备配置      │  │ - 设备发现      │  │ - 指标采集      │                    │
│  │ - 模板配置      │  │ - 信息采集      │  │ - 告警管理      │                    │
│  │ - 规则配置      │  │ - 工具化模块    │  │ - 仪表盘        │                    │
│  └────────────────┘  └────────────────┘  └────────────────┘                    │
│                                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                    │
│  │   工单服务      │  │   知识库服务    │  │   AI服务       │                    │
│  │   (WKO模块)     │  │   (KNO模块)     │  │   (AI模块)      │                    │
│  │ - 生命周期      │  │ - 文档管理      │  │ - 对话接口     │                    │
│  │ - 审批流程      │  │ - 案例库        │  │ - 诊断辅助     │                    │
│  │ - SLA管理       │  │ - 智能检索      │  │ - 模型管理     │                    │
│  └────────────────┘  └────────────────┘  └────────────────┘                    │
│                                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                    │
│  │   自动化服务    │  │   报告服务      │  │   系统服务      │                    │
│  │   (AUTO模块)   │  │   (RPT模块)     │  │   (SYS模块)     │                    │
│  │ - 定时任务库    │  │ - 资产报告      │  │ - 用户权限      │                    │
│  │ - 自愈处置      │  │ - 统计报表      │  │ - 审计日志      │                    │
│  │ - 脚本管理      │  │ - 报表订阅      │  │ - 系统配置      │                    │
│  └────────────────┘  └────────────────┘  └────────────────┘                    │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                                    数据层                                       │
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │    MySQL     │  │    Redis     │  │   TDengine   │  │    MinIO     │        │
│  │   (主数据库)  │  │  (缓存/会话) │  │  (时序数据)  │  │  (文件存储)  │        │
│  │              │  │              │  │              │  │              │        │
│  │ - 配置数据   │  │ - 会话存储   │  │ - 监控指标   │  │ - 日志文件   │        │
│  │ - 工单数据   │  │ - 缓存       │  │ - 采集数据   │  │ - 备份文件   │        │
│  │ - 用户数据   │  │ - 限流计数   │  │ - 告警记录   │  │ - 报表文件   │        │
│  │ - 知识库     │  │ - 任务队列   │  │ - 历史数据   │  │ - 配置备份   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                                 │
│  ┌──────────────┐                                                              │
│  │   Qdrant     │  (向量数据库，预留)                                          │
│  │  (RAG检索)   │                                                              │
│  └──────────────┘                                                              │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                                    采集层                                       │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │                        采集调度器                                      │      │
│  │   支持定时采集 + 实时触发采集 + API触发采集                            │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│                                      │                                        │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐     │
│  │  SNMP采集工具   │ │  SSH采集工具    │ │  API采集工具    │ │  LOG采集工具   │     │
│  │  ┌───────────┐ │ │  ┌───────────┐ │ │  ┌───────────┐ │ │  ┌───────────┐ │     │
│  │  │ SNMP v1   │ │ │  │ Linux采集 │ │ │  │ Zabbix    │ │ │  │ 文件日志  │ │     │
│  │  │ SNMP v2c  │ │ │  │ Windows   │ │ │  │ Prometheus│ │ │  │ Syslog   │ │     │
│  │  │ SNMP v3   │ │ │  │ 网络设备  │ │ │  │ 华为 IMC  │ │ │  │ 数据库日志│ │     │
│  │  └───────────┘ │ │  └───────────┘ │ │  │ 新华三 IMC │ │ │  └───────────┘ │     │
│  │  ┌───────────┐ │ │  ┌───────────┐ │ │  │ VMware    │ │ │  ┌───────────┐ │     │
│  │  │ 华为设备  │ │ │  │ 麒麟Linux │ │ │  │ 自定义API │ │ │  │ WMI/WinRM │ │     │
│  │  │ H3C设备   │ │ │  │ 飞腾/鲲鹏 │ │ │  └───────────┘ │ │  └───────────┘ │     │
│  │  │ 深信服    │ │ │  └───────────┘ │ │                 │ │               │     │
│  │  │ 天融信    │ │ │               │ │                 │ │               │     │
│  │  │ 绿盟      │ │ │               │ │                 │ │               │     │
│  │  └───────────┘ │ │               │ │                 │ │               │     │
│  └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘     │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │                        解析器层                                        │      │
│  │   统一输出格式：JSON + 标准化字段 + 元数据                            │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                                    目标设备                                    │
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Windows    │  │   Linux       │  │   网络设备    │  │   安全设备    │        │
│  │   服务器      │  │   服务器      │  │   交换机      │  │   防火墙      │        │
│  │              │  │   麒麟        │  │   路由器      │  │   IDS/IPS     │        │
│  │              │  │   统信        │  │   负载均衡    │  │   漏扫        │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                          │
│  │   数据库      │  │   虚拟化      │  │   中间件      │                          │
│  │   MySQL       │  │   VMware     │  │   Nginx       │                          │
│  │   PostgreSQL  │  │   KVM        │  │   Tomcat      │                          │
│  └──────────────┘  └──────────────┘  └──────────────┘                          │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块依赖关系

```
                    ┌─────────────────────────────────┐
                    │          基础服务层               │
                    │  ┌─────────────────────────────┐│
                    │  │  配置管理 │ 日志管理 │ 认证 ││
                    │  └─────────────────────────────┘│
                    └─────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│      采集服务      │     │      存储服务      │     │      消息服务      │
│  ┌─────────────┐  │     │  ┌─────────────┐  │     │  ┌─────────────┐  │
│  │ 采集调度器   │  │     │  │ MySQL客户端 │  │     │  │ Redis Pub/Sub│  │
│  │ 采集工具集  │  │     │  │ TDengine    │  │     │  │ 任务队列    │  │
│  │ 设备发现    │  │     │  │ MinIO客户端 │  │     │  └─────────────┘  │
│  └─────────────┘  │     │  └─────────────┘  │     └───────────────────┘
└───────────────────┘     └───────────────────┘
        │                             │
        └─────────────┬───────────────┘
                      ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         业务服务层                                    │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ 监控服务  │  │ 工单服务  │  │ 知识库   │  │ 自动化   │            │
│  │          │  │          │  │          │  │          │            │
│  │ - 指标处理│  │ - 生命周期│  │ - 文档库 │  │ - 定时任务│            │
│  │ - 告警引擎│  │ - 审批流 │  │ - 案例库 │  │ - 自愈   │            │
│  │ - 通知   │  │ - SLA   │  │ - RAG   │  │ - 脚本   │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│  │ AI服务   │  │ 资产服务  │  │ 报告服务  │                          │
│  │          │  │          │  │          │                          │
│  │ - LLM接口│  │ - 设备管理│  │ - 统计   │                          │
│  │ - 诊断   │  │ - 分组   │  │ - 导出   │                          │
│  │ - 建议   │  │ - 配置项 │  │ - 订阅   │                          │
│  └──────────┘  └──────────┘  └──────────┘                          │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         API网关层                                      │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ 路由分发  │  │ 认证鉴权  │  │ 日志记录  │  │ 限流熔断 │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. 数据架构

### 3.1 数据库选型

| 数据库 | 用途 | 选型原因 |
|--------|------|---------|
| MySQL 8.0 | 主数据库 | 兼容性好，运维熟悉，国产化支持 |
| Redis 7.0 | 缓存/会话/队列 | 高性能，功能丰富 |
| TDengine 3.0 | 时序数据 | 高性能时序，兼容MySQL协议 |
| MinIO | 对象存储 | S3兼容，本地部署 |
| Qdrant | 向量存储 | RAG检索预留 |

### 3.2 MySQL表结构设计（核心）

```sql
-- ========================================
-- 组织架构表（支持多级扩展）
-- ========================================
CREATE TABLE t_org (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    parent_id BIGINT DEFAULT 0,           -- 父级ID，0为根节点
    org_name VARCHAR(100) NOT NULL,        -- 组织名称
    org_code VARCHAR(50) NOT NULL,         -- 组织编码
    org_type TINYINT DEFAULT 1,            -- 1=集团,2=子公司,3=部门
    sort_order INT DEFAULT 0,
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_id),
    INDEX idx_code (org_code)
);

-- ========================================
-- 用户表
-- ========================================
CREATE TABLE t_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    real_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    org_id BIGINT,
    role_id BIGINT,
    status TINYINT DEFAULT 1,
    last_login_at TIMESTAMP,
    login_ip VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_org (org_id),
    INDEX idx_role (role_id)
);

-- ========================================
-- 角色表
-- ========================================
CREATE TABLE t_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_code VARCHAR(50) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    is_system TINYINT DEFAULT 0,          -- 是否系统角色
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 权限表
-- ========================================
CREATE TABLE t_permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    permission_code VARCHAR(100) NOT NULL UNIQUE,
    permission_name VARCHAR(100) NOT NULL,
    module VARCHAR(50),                    -- 所属模块
    action VARCHAR(50),                    -- 操作类型
    parent_id BIGINT DEFAULT 0,
    sort_order INT DEFAULT 0
);

-- ========================================
-- 角色权限关联表
-- ========================================
CREATE TABLE t_role_permission (
    role_id BIGINT,
    permission_id BIGINT,
    PRIMARY KEY (role_id, permission_id)
);

-- ========================================
-- 设备表
-- ========================================
CREATE TABLE t_device (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_code VARCHAR(100) UNIQUE,      -- 设备编码
    hostname VARCHAR(100),                 -- 主机名
    ip_address VARCHAR(50) NOT NULL,
    mac_address VARCHAR(50),
    device_type VARCHAR(50),               -- server/network/security/database
    vendor VARCHAR(100),                   -- 厂商
    model VARCHAR(100),                    -- 型号
    sn VARCHAR(100),                       -- 序列号
    os_type VARCHAR(50),                   -- 操作系统类型
    os_version VARCHAR(100),               -- 操作系统版本
    cpu_model VARCHAR(100),
    cpu_count INT,
    memory_size BIGINT,                    -- 内存大小(字节)
    disk_size BIGINT,                      -- 磁盘大小(字节)
    org_id BIGINT,                         -- 归属组织
    group_id BIGINT,                       -- 归属分组
    admin_id BIGINT,                       -- 管理员
    technician_id BIGINT,                  -- 技术负责人
    status TINYINT DEFAULT 1,              -- 1=在线,2=离线,3=维护,4=退役
    first_found_at TIMESTAMP,
    last_check_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    INDEX idx_ip (ip_address),
    INDEX idx_type (device_type),
    INDEX idx_org (org_id),
    INDEX idx_status (status)
);

-- ========================================
-- 设备分组表
-- ========================================
CREATE TABLE t_device_group (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    group_name VARCHAR(100) NOT NULL,
    parent_id BIGINT DEFAULT 0,
    description VARCHAR(255),
    org_id BIGINT,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 设备标签表
-- ========================================
CREATE TABLE t_device_tag (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tag_name VARCHAR(50) NOT NULL,
    tag_color VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_device_tag_relation (
    device_id BIGINT,
    tag_id BIGINT,
    PRIMARY KEY (device_id, tag_id)
);

-- ========================================
-- 采集项配置表
-- ========================================
CREATE TABLE t_metric_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    metric_code VARCHAR(100) NOT NULL UNIQUE,
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50),              -- snmp/ssh/api/log
    device_type VARCHAR(50),               -- 适用设备类型
    collector_type VARCHAR(50),            -- 采集器类型
    collector_config JSON,                 -- 采集器配置
    parser_type VARCHAR(50),               -- 解析器类型
    parser_config JSON,                    -- 解析器配置
    interval_seconds INT DEFAULT 60,       -- 采集间隔
    enabled TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 设备采集项关联表
-- ========================================
CREATE TABLE t_device_metric (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id BIGINT NOT NULL,
    metric_id BIGINT NOT NULL,
    enabled TINYINT DEFAULT 1,
    custom_config JSON,                   -- 自定义配置
    last_value TEXT,
    last_check_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_device_metric (device_id, metric_id)
);

-- ========================================
-- 指标数据表（TDengine存储，本表仅作参考）
-- ========================================
-- CREATE TABLE t_metric_data (
--     ts TIMESTAMP,                        -- 时间戳
--     device_id BIGINT,                    -- 设备ID
--     metric_id BIGINT,                    -- 指标ID
--     value DOUBLE,                        -- 指标值
--     tags JSON                            -- 附加标签
-- );

-- ========================================
-- 告警规则表
-- ========================================
CREATE TABLE t_alert_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_code VARCHAR(100) NOT NULL UNIQUE,
    rule_name VARCHAR(100) NOT NULL,
    metric_id BIGINT,                      -- 关联指标
    condition_type VARCHAR(50),            -- threshold/trend/duration
    operator VARCHAR(20),                  -- >, <, =, between
    threshold_value VARCHAR(100),          -- 阈值
    duration_seconds INT DEFAULT 0,        -- 持续时间
    severity TINYINT DEFAULT 2,            -- 1=Critical,2=Warning,3=Info
    enabled TINYINT DEFAULT 1,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 告警事件表
-- ========================================
CREATE TABLE t_alert_event (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_id BIGINT,
    device_id BIGINT NOT NULL,
    metric_id BIGINT,
    severity TINYINT,
    title VARCHAR(255),
    content TEXT,
    value TEXT,
    threshold TEXT,
    status TINYINT DEFAULT 1,             -- 1=触发,2=确认,3=恢复,4=关闭
    triggered_at TIMESTAMP,
    confirmed_at TIMESTAMP,
    confirmed_by BIGINT,
    recovered_at TIMESTAMP,
    closed_at TIMESTAMP,
    workorder_id BIGINT,                   -- 关联工单
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device (device_id),
    INDEX idx_status (status),
    INDEX idx_severity (severity),
    INDEX idx_triggered (triggered_at)
);

-- ========================================
-- 工单表
-- ========================================
CREATE TABLE t_workorder (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    order_type TINYINT,                   -- 1=故障,2=变更,3=巡检,4=优化
    priority TINYINT DEFAULT 2,            -- 1=紧急,2=高,3=中,4=低
    status TINYINT DEFAULT 1,               -- 1=待处理,2=处理中,3=待审批,4=已完成,5=已关闭
    source TINYINT DEFAULT 1,               -- 1=手动,2=告警,3=系统
    source_id BIGINT,                       -- 来源ID（告警ID等）
    device_id BIGINT,
    create_user_id BIGINT,
    assign_user_id BIGINT,                 -- 当前处理人
    assign_group_id BIGINT,                -- 处理组
    sla_response_deadline TIMESTAMP,       -- SLA响应时限
    sla_handle_deadline TIMESTAMP,        -- SLA处理时限
    sla_response_at TIMESTAMP,             -- 实际响应时间
    sla_handle_at TIMESTAMP,               -- 实际处理时间
    closed_at TIMESTAMP,
    closed_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_assign (assign_user_id),
    INDEX idx_create (create_user_id),
    INDEX idx_create_time (created_at)
);

-- ========================================
-- 工单处理记录表
-- ========================================
CREATE TABLE t_workorder_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workorder_id BIGINT NOT NULL,
    action TINYINT,                        -- 1=创建,2=派发,3=处理,4=转派,5=审批,6=关闭
    from_user_id BIGINT,
    to_user_id BIGINT,
    content TEXT,
    attachments JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_workorder (workorder_id)
);

-- ========================================
-- 工单审批流定义表
-- ========================================
CREATE TABLE t_workorder_flow (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    flow_name VARCHAR(100) NOT NULL,
    flow_config JSON NOT NULL,            -- 流程配置，包含审批节点
    order_type TINYINT,                   -- 适用工单类型
    enabled TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 知识库文档表
-- ========================================
CREATE TABLE t_document (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    doc_code VARCHAR(100) UNIQUE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    doc_type TINYINT DEFAULT 1,           -- 1=SOP,2=案例,3=手册
    category_id BIGINT,
    tags JSON,
    status TINYINT DEFAULT 1,            -- 1=草稿,2=待审核,3=已发布
    version INT DEFAULT 1,
    author_id BIGINT,
    approver_id BIGINT,
    approved_at TIMESTAMP,
    published_at TIMESTAMP,
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (doc_type),
    INDEX idx_status (status)
);

-- ========================================
-- 知识库分类表
-- ========================================
CREATE TABLE t_doc_category (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL,
    parent_id BIGINT DEFAULT 0,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- 定时任务表
-- ========================================
CREATE TABLE t_schedule_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_code VARCHAR(100) NOT NULL UNIQUE,
    task_name VARCHAR(100) NOT NULL,
    task_type VARCHAR(50),               --巡检/备份/清理/报表/自定义
    script_content TEXT,                  -- 脚本内容或引用
    script_type VARCHAR(20),              -- shell/python/powershell
    target_type VARCHAR(20),             -- device/group/all
    target_ids JSON,                      -- 目标设备ID列表
    cron_expression VARCHAR(100),         -- Cron表达式
    is_enabled TINYINT DEFAULT 1,
    timeout_seconds INT DEFAULT 300,
    retry_count INT DEFAULT 0,
    notification_enabled TINYINT DEFAULT 0,
    notification_config JSON,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_enabled (is_enabled),
    INDEX idx_type (task_type)
);

-- ========================================
-- 定时任务执行记录表
-- ========================================
CREATE TABLE t_schedule_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL,
    task_run_id VARCHAR(50),              -- 本次运行ID
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status TINYINT,                       -- 1=运行中,2=成功,3=失败,4=超时
    result_summary TEXT,
    target_count INT,                     -- 目标数量
    success_count INT,                    -- 成功数量
    fail_count INT,                       -- 失败数量
    output_log LONGTEXT,                  -- 执行日志
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task (task_id),
    INDEX idx_status (status),
    INDEX idx_start (start_time)
);

-- ========================================
-- 脚本库表
-- ========================================
CREATE TABLE t_script (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    script_code VARCHAR(100) NOT NULL UNIQUE,
    script_name VARCHAR(100) NOT NULL,
    script_type VARCHAR(20),             -- shell/python/powershell
    content TEXT NOT NULL,
    version INT DEFAULT 1,
    description TEXT,
    is_dangerous TINYINT DEFAULT 0,       -- 危险脚本标记
    need_approve TINYINT DEFAULT 1,      -- 是否需要审批
    author_id BIGINT,
    status TINYINT DEFAULT 1,             -- 1=草稿,2=已发布,3=已禁用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ========================================
-- 操作审计日志表
-- ========================================
CREATE TABLE t_audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT,
    username VARCHAR(50),
    action VARCHAR(50),                   -- 操作类型
    module VARCHAR(50),                   -- 操作模块
    resource_type VARCHAR(50),            -- 资源类型
    resource_id BIGINT,                   -- 资源ID
    detail JSON,                           -- 操作详情
    ip_address VARCHAR(50),
    user_agent VARCHAR(255),
    result TINYINT,                        -- 1=成功,2=失败
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_module (module),
    INDEX idx_time (created_at)
);

-- ========================================
-- 系统配置表
-- ========================================
CREATE TABLE t_system_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(50),               -- string/number/json/boolean
    config_group VARCHAR(50),             -- 配置分组
    description VARCHAR(255),
    is_encrypted TINYINT DEFAULT 0,        -- 是否加密
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 3.3 分库分表策略（大型用户扩展）

```
┌─────────────────────────────────────────────────────────────────────┐
│                      多租户数据隔离方案                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   方案1：独立数据库（大型集团）                                       │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐                          │
│   │ 集团DB   │ │ 子公司A  │ │ 子公司B  │                          │
│   │ (公共)   │ │ (隔离)   │ │ (隔离)   │                          │
│   └──────────┘ └──────────┘ └──────────┘                          │
│                                                                     │
│   方案2：Schema隔离（中型用户）                                      │
│   ┌──────────────────────────────────────┐                          │
│   │           MySQL实例                   │                          │
│   │  ┌────────┐ ┌────────┐ ┌────────┐  │                          │
│   │  │tenant_a│ │tenant_b│ │tenant_c│  │                          │
│   │  └────────┘ └────────┘ └────────┘  │                          │
│   └──────────────────────────────────────┘                          │
│                                                                     │
│   方案3：行级隔离（小型用户，默认）                                  │
│   ┌──────────────────────────────────────┐                          │
│   │           MySQL实例                   │                          │
│   │  ┌────────────────────────────────┐  │                          │
│   │  │ t_device (org_id 字段隔离)     │  │                          │
│   │  │ t_workorder (org_id 字段隔离)  │  │                          │
│   │  └────────────────────────────────┘  │                          │
│   └──────────────────────────────────────┘                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 采集模块工具化设计

### 4.1 设计原则

1. **独立性**：每个采集能力作为独立模块，可单独调用
2. **标准化**：统一输入输出格式，便于组合使用
3. **可测试**：每个模块可独立测试和调试
4. **可复用**：其他平台可直接引用采集模块

### 4.2 模块结构

```
modules/
├── collectors/
│   ├── __init__.py
│   ├── base.py                    # 采集基类
│   ├── snmp/                      # SNMP采集器
│   │   ├── __init__.py
│   │   ├── snmp_collector.py     # 主采集器
│   │   ├── parsers/              # 解析器
│   │   │   ├── __init__.py
│   │   │   ├── base_parser.py
│   │   │   ├── huawei_parser.py  # 华为设备
│   │   │   ├── h3c_parser.py     # H3C设备
│   │   │   ├── sangfor_parser.py # 深信服
│   │   │   └── generic_parser.py # 通用
│   │   └── templates/            # MIB模板
│   │       ├── __init__.py
│   │       ├── if_mib.py         # 网络接口
│   │       ├── host_mib.py       # 主机资源
│   │       └── vendor/
│   │           ├── huawei.py
│   │           ├── h3c.py
│   │           └── topsec.py
│   ├── ssh/                       # SSH采集器
│   │   ├── __init__.py
│   │   ├── ssh_collector.py
│   │   ├── commands/             # 命令模板
│   │   │   ├── __init__.py
│   │   │   ├── linux_commands.py
│   │   │   ├── windows_commands.py
│   │   │   └── network_commands.py
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── linux_parser.py
│   │       └── windows_parser.py
│   ├── api/                       # API采集器
│   │   ├── __init__.py
│   │   ├── api_collector.py
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   ├── zabbix_client.py
│   │   │   ├── prometheus_client.py
│   │   │   ├── huawei_imc_client.py
│   │   │   └── h3c_imc_client.py
│   │   └── converters/
│   │       ├── __init__.py
│   │       └── metrics_converter.py
│   ├── log/                       # 日志采集器
│   │   ├── __init__.py
│   │   ├── log_collector.py
│   │   ├── sources/
│   │   │   ├── __init__.py
│   │   │   ├── file_source.py
│   │   │   ├── syslog_source.py
│   │   │   └── db_log_source.py
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── text_parser.py
│   │       └── json_parser.py
│   └── browser/                   # 浏览器自动化采集
│       ├── __init__.py
│       ├── browser_collector.py
│       └── templates/
│           ├── __init__.py
│           └── web采集模板.py
├── discovery/                     # 设备发现
│   ├── __init__.py
│   ├── network_scanner.py         # IP段扫描
│   ├── snmp_scanner.py            # SNMP扫描
│   └── arp_scanner.py             # ARP扫描
└── tools/                         # 独立工具
    ├── __init__.py
    ├── ping.py                    # Ping工具
    ├── port_scan.py               # 端口扫描
    ├── traceroute.py              # 路由追踪
    └── dns_lookup.py              # DNS查询
```

### 4.3 统一接口设计

```python
# modules/collectors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

@dataclass
class CollectorResult:
    """采集结果标准格式"""
    success: bool
    device_id: str
    device_ip: str
    collector_type: str  # snmp/ssh/api/log
    timestamp: datetime
    data: Dict[str, Any]  # 采集数据
    raw_data: str  # 原始数据
    error: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_json(self) -> str:
        return json.dumps({
            'success': self.success,
            'device_id': self.device_id,
            'device_ip': self.device_ip,
            'collector_type': self.collector_type,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'raw_data': self.raw_data,
            'error': self.error,
            'metadata': self.metadata or {}
        }, ensure_ascii=False)

class BaseCollector(ABC):
    """采集器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.retry = config.get('retry', 3)
    
    @abstractmethod
    def collect(self, target: str, **kwargs) -> CollectorResult:
        """执行采集"""
        pass
    
    @abstractmethod
    def validate_target(self, target: str) -> bool:
        """验证采集目标"""
        pass
    
    def health_check(self, target: str) -> bool:
        """健康检查"""
        try:
            result = self.collect(target)
            return result.success
        except:
            return False
```

### 4.4 使用示例

```python
# 方式1：单独使用采集工具
from modules.collectors import SNMPCollector, SSHCollector

# SNMP采集
snmp = SNMPCollector({
    'version': 'v2c',
    'community': 'public'
})
result = snmp.collect('192.168.1.1')

# SSH采集
ssh = SSHCollector({
    'username': 'admin',
    'password': 'xxx',
    'port': 22
})
result = ssh.collect('192.168.1.10', commands=['uptime', 'df -h'])

# 方式2：组合使用
from modules.collectors import CollectorFactory

collector = CollectorFactory.create('snmp')
collector.set_vendor('huawei')
result = collector.collect('192.168.1.1')

# 方式3：通过API调用
import requests

response = requests.post('http://localhost:8000/api/v1/collect', json={
    'device_ip': '192.168.1.1',
    'collector_type': 'snmp',
    'vendor': 'huawei'
})
```

---

## 5. 定时任务库设计

### 5.1 预置任务模板

| 任务类别 | 任务名称 | 任务代码 | 说明 |
|---------|---------|---------|------|
| **巡检类** | 服务器巡检 | TSK-SVR-INSPECTION | CPU/内存/磁盘/服务 |
| | 网络设备巡检 | TSK-NET-INSPECTION | 端口/流量/状态 |
| | 数据库巡检 | TSK-DB-INSPECTION | 连接数/缓存/慢查询 |
| **备份类** | 数据库备份 | TSK-DB-BACKUP | MySQL/PostgreSQL备份 |
| | 配置文件备份 | TSK-CFG-BACKUP | 设备配置备份 |
| | 日志备份 | TSK-LOG-BACKUP | 重要日志归档 |
| **清理类** | 日志清理 | TSK-LOG-CLEANUP | 清理过期日志 |
| | 临时文件清理 | TSK-TMP-CLEANUP | 清理临时文件 |
| | 告警清理 | TSK-ALERT-CLEANUP | 清理历史告警 |
| **检查类** | 端口连通性检查 | TSK-PORT-CHECK | 检查指定端口 |
| | 证书有效期检查 | TSK-CERT-CHECK | SSL证书到期检查 |
| | 服务可用性检查 | TSK-SVC-CHECK | HTTP/服务检查 |
| | 磁盘空间检查 | TSK-DISK-CHECK | 磁盘使用率检查 |
| **报表类** | 日报生成 | TSK-REPORT-DAILY | 生成日报 |
| | 周报生成 | TSK-REPORT-WEEKLY | 生成周报 |
| | 月报生成 | TSK-REPORT-MONTHLY | 生成月报 |
| **安全类** | 弱口令扫描 | TSK-SEC-SCANNING | 检查弱口令 |
| | 端口安全扫描 | TSK-SEC-PORT | 检查异常端口 |

### 5.2 任务配置示例

```python
# 预置任务定义
PRESET_TASKS = [
    {
        'task_code': 'TSK-SVR-INSPECTION',
        'task_name': '服务器巡检',
        'task_type': '巡检',
        'script_type': 'shell',
        'script_content': '''#!/bin/bash
# 服务器巡检脚本
echo "=== CPU使用率 ==="
top -bn1 | head -5

echo "=== 内存使用 ==="
free -h

echo "=== 磁盘使用 ==="
df -h

echo "=== 服务状态 ==="
systemctl list-units --type=service --state=running | head -20
''',
        'cron_expression': '0 6 * * *',  # 每天6点
        'description': '定时巡检服务器资源和服务状态',
        'target_type': 'all',
        'timeout_seconds': 300
    },
    {
        'task_code': 'TSK-DB-BACKUP',
        'task_name': '数据库备份',
        'task_type': '备份',
        'script_type': 'shell',
        'script_content': '''#!/bin/bash
# MySQL数据库备份
BACKUP_DIR="/data/backup/mysql"
DATE=$(date +%Y%m%d)
mysqldump --all-databases > $BACKUP_DIR/full_backup_$DATE.sql
find $BACKUP_DIR -mtime +7 -delete  # 删除7天前的备份
''',
        'cron_expression': '0 2 * * *',  # 每天2点
        'description': '全量备份MySQL数据库',
        'target_type': 'group',
        'target_ids': [],  # 指定数据库服务器
        'timeout_seconds': 3600
    }
]
```

---

## 6. 安全架构设计

### 6.1 安全分层

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              边界安全                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ 防火墙   │  │ 入侵检测 │  │ 抗DDoS  │  │ WAF     │                    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                    │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              应用安全                                       │
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ 身份认证 │  │ 权限控制 │  │ 会话管理 │  │ 审计日志 │  │ 数据脱敏 │      │
│  │ JWT/SSO │  │ RBAC     │  │ 超时锁定 │  │ 全量记录 │  │ 敏感隐藏 │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ SQL注入  │  │ XSS防护  │  │ CSRF    │  │ 文件上传 │                    │
│  │ 参数化   │  │ 转义     │  │ Token   │  │ 格式校验 │                    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                    │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              数据安全                                       │
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ 传输加密 │  │ 存储加密 │  │ 备份加密 │  │ 密钥管理 │                    │
│  │ TLS 1.2+ │  │ AES256   │  │ 备份加密 │  │ 分层管理 │                    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                    │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              代码安全                                       │
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ 代码混淆 │  │ 授权验证 │  │ 设备绑定 │  │ 水印追溯 │                    │
│  │ PyArmor  │  │ License   │  │ 指纹     │  │ 动态水印 │                    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                    │
└────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 身份认证设计

```python
# 认证方式
AUTH_METHODS = {
    'password': {
        'enabled': True,
        'password_policy': {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_number': True,
            'require_special': True,
            'password_history': 5,  # 不能使用最近5次密码
            'lockout_threshold': 5,  # 失败5次锁定
            'lockout_duration': 30,  # 锁定30分钟
        }
    },
    'jwt': {
        'enabled': True,
        'algorithm': 'HS256',
        'access_token_expire': 30,  # 30分钟
        'refresh_token_expire': 7,  # 7天
    },
    'api_key': {
        'enabled': True,
        'header_name': 'X-API-Key',
    },
    'ldap': {
        'enabled': False,  # 可选开启
        'server': '',
        'base_dn': '',
    }
}
```

### 6.3 权限控制设计

```python
# 权限模型
PERMISSION_MATRIX = {
    'admin': {
        '*': ['*'],  # 全部权限
    },
    'operator': {
        'device': ['view', 'add', 'edit', 'delete'],
        'monitor': ['view', 'ack'],
        'workorder': ['view', 'create', 'handle'],
        'task': ['view', 'execute'],
    },
    'approver': {
        'workorder': ['view', 'approve', 'reject'],
    },
    'viewer': {
        'device': ['view'],
        'monitor': ['view'],
        'workorder': ['view'],
        'report': ['view'],
    }
}
```

### 6.4 审计日志设计

```python
# 审计日志记录
AUDIT_CONFIG = {
    'log_login': True,           # 记录登录
    'log_operation': True,        # 记录操作
    'log_sensitive': True,       # 记录敏感操作
    'log_export': True,          # 记录数据导出
    
    'sensitive_actions': [
        'device.delete',
        'user.delete',
        'role.modify',
        'config.modify',
        'script.execute',
        'task.execute',
        'data.export',
        'backup.restore',
    ],
    
    'retention_days': 180,        # 保留180天
    
    'log_format': {
        'timestamp': True,
        'user_id': True,
        'username': True,
        'action': True,
        'module': True,
        'resource': True,
        'ip_address': True,
        'user_agent': True,
        'detail': True,
        'result': True,
    }
}
```

### 6.5 代码保护设计

```python
# 代码保护机制
PROTECTION_CONFIG = {
    'obfuscation': {
        'enabled': True,
        'method': 'pyarmor',
        'exclude_files': ['config.py', 'credentials.py'],  # 不混淆的文件
    },
    
    'license': {
        'enabled': True,
        'check_interval': 24,  # 每24小时检查一次
        'grace_period': 72,    # 宽限期72小时
        
        'license_type': {
            'perpetual': '永久授权',
            'subscription': '订阅授权',
            'trial': '试用授权',
        },
        
        'hardware_binding': {
            'cpu_id': True,
            'motherboard_sn': True,
            'disk_sn': True,
            'mac_address': True,
        },
        
        'offline_license': {
            'enabled': True,
            'license_file': 'license.lic',
        }
    },
    
    'watermark': {
        'enabled': True,
        'user_info_in_error': True,  # 错误信息中包含用户信息
        'export_watermark': True,    # 导出的文件添加水印
    },
    
    'anti_debug': {
        'enabled': True,
        'detect_pyinstaller': True,
        'detect_debugger': True,
    }
}
```

---

## 7. 部署架构

### 7.1 小型用户（1-50台）

```
┌────────────────────────────────────────────────────────────────┐
│                        单机部署                                  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Docker Compose                         │  │
│  │                                                          │  │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │  │
│  │   │ MySQL   │  │  Redis  │  │TDengine │  │  MinIO   │   │  │
│  │   │  8.0    │  │   7.0   │  │  3.0    │  │ latest  │   │  │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘   │  │
│  │                                                          │  │
│  │   ┌─────────────────────────────────────────────────┐   │  │
│  │   │                   FastAPI                       │   │  │
│  │   │              (后端服务 + 采集调度)                │   │  │
│  │   └─────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │   ┌─────────────────────────────────────────────────┐   │  │
│  │   │              Vue3 + Nginx (前端)                 │   │  │
│  │   └─────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│   最低配置：4核CPU / 8GB内存 / 100GB磁盘                         │
└────────────────────────────────────────────────────────────────┘
```

### 7.2 中型用户（50-200台）

```
┌────────────────────────────────────────────────────────────────┐
│                        分离部署                                 │
│                                                                │
│  ┌──────────────────┐                                         │
│  │   数据库服务器    │   MySQL主从 + Redis集群                  │
│  │   8C/16G/500G   │                                         │
│  └──────────────────┘                                         │
│         │                                                    │
│  ┌──────┴──────────────────────────────────────────────────┐  │
│  │                    应用服务器                              │  │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │  │
│  │   │ API服务  │  │ 采集服务 │  │ 定时任务 │  │ AI服务   │    │  │
│  │   │ FastAPI │  │ Collector│ │ Scheduler│ │ (预留)  │    │  │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘    │  │
│  │                                                          │  │
│  │   ┌─────────────────────────────────────────────────┐   │  │
│  │   │              Vue3 + Nginx (前端)                 │   │  │
│  │   └─────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│         │                                                    │
│  ┌──────┴──────────────────────┐                            │
│  │        存储服务器            │   TDengine + MinIO          │
│  │        4C/8G/1TB           │                            │
│  └─────────────────────────────┘                            │
│                                                                │
│   推荐配置：8核CPU / 16GB内存 / 500GB磁盘                       │
└────────────────────────────────────────────────────────────────┘
```

### 7.3 大型用户/集团（200-1000+台）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           K8s集群部署                                    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        控制平面                                  │    │
│  │           (Master Node × 3)                                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                    │
│  ┌──────────────────────────────────┼───────────────────────────────┐  │
│  │                            工作节点                             │  │
│  │                                                               │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │  │
│  │  │ API Pod │  │Collector│  │Scheduler│  │ Worker  │           │  │
│  │  │ (×2)    │  │  Pod    │  │  Pod    │  │  Pod    │           │  │
│  │  │         │  │ (×N)    │  │ (×2)    │  │ (×N)    │           │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌──────────────────────────────────┼───────────────────────────────┐  │
│  │                              数据层                               │  │
│  │                                                               │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │  │
│  │  │MySQL集群│  │TDengine │  │  Redis  │  │  MinIO  │           │  │
│  │  │ 集群    │  │  集群   │  │ 集群    │  │  集群   │           │  │
│  │  │         │  │         │  │         │  │         │           │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌──────────────────────────────────┼───────────────────────────────┐  │
│  │                          采集Agent                             │  │
│  │                                                               │  │
│  │     Agent1     Agent2     Agent3     Agent4                    │  │
│  │    (网段A)    (网段B)    (网段C)    (网段D)                    │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   配置：按需扩展，支持1000+台设备                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. 接口设计

### 8.1 API规范

```yaml
# OpenAPI 3.0规范
openapi: 3.0.0
info:
  title: IT运维智能平台 API
  version: 1.0.0

servers:
  - url: http://localhost:8000/api/v1
    description: 本地开发环境
  - url: https://itops.internal/api/v1
    description: 内网生产环境

paths:
  /auth/login:
    post:
      summary: 用户登录
      tags: [认证]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                username: {type: string}
                password: {type: string}
      responses:
        '200':
          description: 登录成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token: {type: string}
                  refresh_token: {type: string}
                  expires_in: {type: integer}

  /devices:
    get:
      summary: 获取设备列表
      tags: [资产管理]
      security:
        - bearerAuth: []
      parameters:
        - name: page
          in: query
          schema: {type: integer, default: 1}
        - name: page_size
          in: query
          schema: {type: integer, default: 20}
        - name: device_type
          in: query
          schema: {type: string}
        - name: status
          in: query
          schema: {type: integer}
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  total: {type: integer}
                  page: {type: integer}
                  page_size: {type: integer}
                  data: {type: array}

  /collect:
    post:
      summary: 采集设备数据
      tags: [数据采集]
      security:
        - bearerAuth: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [device_ip, collector_type]
              properties:
                device_ip: {type: string}
                collector_type: {type: string, enum: [snmp, ssh, api, log]}
                vendor: {type: string}
                metric_ids: {type: array, items: {type: integer}}
      responses:
        '200':
          description: 采集成功
```

---

## 9. 技术栈总结

| 层级 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| **前端** | Vue 3 | 3.4+ | Composition API |
| | Element Plus | 2.5+ | UI组件库 |
| | Vite | 5.0+ | 构建工具 |
| | Pinia | 2.1+ | 状态管理 |
| | Axios | 1.6+ | HTTP客户端 |
| **后端** | Python | 3.11+ | 编程语言 |
| | FastAPI | 0.109+ | Web框架 |
| | SQLAlchemy | 2.0+ | ORM |
| | Pydantic | 2.5+ | 数据验证 |
| | APScheduler | 3.10+ | 定时任务 |
| | Paramiko | 3.4+ | SSH客户端 |
| | pysnmp | 4.4+ | SNMP客户端 |
| | Playwright | 1.40+ | 浏览器自动化 |
| **数据库** | MySQL | 8.0+ | 主数据库 |
| | Redis | 7.0+ | 缓存/会话 |
| | TDengine | 3.0+ | 时序数据库 |
| | MinIO | latest | 对象存储 |
| | Qdrant | 1.7+ | 向量数据库(预留) |
| **部署** | Docker | 24.0+ | 容器化 |
| | Docker Compose | 2.20+ | 编排 |
| | Nginx | 1.25+ | Web服务器 |
| **安全** | PyArmor | 7.x | 代码混淆 |
| | python-jose | 3.3+ | JWT处理 |
| | passlib | 1.7+ | 密码处理 |
| | cryptography | 41.0+ | 加密 |

---

## 10. 文档清单

| 文档编号 | 文档名称 | 状态 |
|---------|---------|------|
| ITOPS-SRS-001 | 需求规格说明书 | 已完成 |
| ITOPS-SAD-001 | 架构设计说明书 | 本文档 |
| ITOPS-HLD-001 | 概要设计说明书 | 待编写 |
| ITOPS-LLD-001 | 详细设计说明书 | 待编写 |
| ITOPS-TST-001 | 测试计划 | 待编写 |
| ITOPS-UGD-001 | 用户手册 | 待编写 |
| ITOPS-IGD-001 | 运维手册 | 待编写 |

---

**文档状态**：已完成

**下一步行动**：
1. [x] 完成需求规格说明书
2. [x] 完成架构设计说明书
3. [ ] 开发团队评审架构设计
4. [ ] 根据反馈修订设计
5. [ ] 开始Phase 1开发