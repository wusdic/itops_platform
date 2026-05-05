# ITOps Platform 架构文档

## 1. 平台概述

ITOps Platform 是一个智能化运维平台，支持内网本地化部署，使用 Qwen2.5 本地 LLM 辅助运维决策。

### 1.1 技术栈

- **后端**: Python 3.11+ / FastAPI
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **时序库**: TDengine / InfluxDB
- **向量库**: Qdrant
- **对象存储**: MinIO
- **缓存**: Redis
- **前端**: React + TypeScript + TailwindCSS

### 1.2 设计原则

1. **配置驱动** - 设备/协议配置与代码分离
2. **模块化** - 模块独立，可复用
3. **工厂模式** - 采集器通过工厂统一创建
4. **适配器模式** - 支持多厂商设备

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway (FastAPI)                     │
│  /devices  /assets  /monitoring  /reports  /workorders  /ai     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  AI Copilot   │  │   Business    │  │   Services    │
│  (LLM+RAG)    │  │   Modules     │  │   Layer       │
└───────────────┘  └───────────────┘  └───────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Collection    │  │   Storage     │  │  Foundation   │
│  Module        │  │   Module      │  │  Services     │
└───────────────┘  └───────────────┘  └───────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Core Layer   │  │   Storage     │  │   Database   │
│  (Shared)     │  │   Clients     │  │   Models     │
└───────────────┘  └───────────────┘  └───────────────┘
```

---

## 3. 核心模块

### 3.1 Core Layer (core/)

| 模块 | 文件 | 职责 |
|------|------|------|
| **protocols** | `core/protocols.py` | 统一协议类型定义 (ProtocolType, DeviceCategory, MetricType) |
| **config** | `core/config/manager.py` | 配置加载、验证、热更新 |
| **db** | `core/db/base.py` | SQLAlchemy 基础模型 |
| **storage** | `core/storage/client.py` | 存储客户端基类 |
| **log** | `core/log/manager.py` | 日志管理 |

### 3.2 Collection Module (modules/collection/)

**核心组件:**

| 组件 | 文件 | 职责 |
|------|------|------|
| **ConfigLoader** | `config_loader.py` | 加载设备配置 (YAML) |
| **DeviceManager** | `device_manager.py` | 设备状态管理、采集调度 |
| **CollectorFactory** | `collector_factory.py` | 根据协议创采集器 |
| **AdapterRegistry** | `adapter_registry.py` | 采集适配器注册表 |

**采集器实现:**

| 采集器 | 路径 | 支持协议 |
|--------|------|----------|
| SNMP | `snmp_collector/` | SNMP v1/v2c/v3 |
| SSH | `ssh_collector/` | SSH, Telnet, WinRM |
| HTTP | `api_collector/` | REST API, Zabbix, Prometheus |
| IPMI | `ipmi_collector/` | IPMI v1.5/v2.0 |
| K8s | `api_collector/` | Kubernetes API |
| Docker | `api_collector/` | Docker Engine API |

### 3.3 Business Module (modules/business/)

| 子模块 | 路径 | 职责 |
|--------|------|------|
| **ai_copilot** | `ai_copilot/` | LLM对话、RAG检索、提示引擎 |
| **asset_management** | `asset_management/` | 资产管理、生命周期、风险评估 |
| **knowledge_base** | `knowledge_base/` | 知识库、文档、SOP |
| **monitoring** | `monitoring/` | 监控告警、仪表板、规则 |
| **notification** | `notification/` | 通知服务 |
| **report_generator** | `report_generator/` | 报告生成 |
| **workorder** | `workorder/` | 工单管理 |

### 3.4 Storage Module (modules/storage/)

| 存储类型 | 路径 | 用途 |
|----------|------|------|
| **TDengine** | `tdengine/` | 时序数据存储 |
| **InfluxDB** | `influxdb/` | 时序数据存储 |
| **Qdrant** | `qdrant/` | 向量数据库 (RAG) |
| **MinIO** | `minio/` | 对象存储 (文件/图片) |
| **Redis** | `redis_client/` | 缓存/会话 |

### 3.5 Foundation Module (modules/foundation/)

| 子模块 | 路径 | 职责 |
|--------|------|------|
| **auth_manager** | `auth_manager/` | 认证授权、LDAP、RBAC、审计 |
| **db_models** | `db_models/` | SQLAlchemy 数据模型 |

---

## 4. 数据采集流程

```
1. 配置加载
   ConfigLoader.load() → 读取 config/devices/*.yaml
         ↓
2. 设备注册
   DeviceManager.register_device() → 注册到设备列表
         ↓
3. 协议选择
   DeviceManager.collect_device() → 选择 primary/fallback 协议
         ↓
4. 采集器创建
   CollectorFactory.create_collector() → 根据协议创建采集器
         ↓
5. 数据采集
   采集器.collect() → 执行采集获取指标
         ↓
6. 指标返回
   DeviceMetrics → 返回给回调函数
```

### 4.1 采集器选择逻辑

```python
# 设备配置示例
device:
  name: "Web服务器-01"
  type: server
  protocols:
    primary: ssh      # 主协议
    fallback: snmp    # 备用协议

# 采集流程
1. 尝试 primary 协议 (ssh)
2. 失败则尝试 fallback 协议 (snmp)
3. 都失败则返回 OFFLINE 状态
```

---

## 5. API 路由结构

| 路由前缀 | 路径 | 职责 |
|----------|------|------|
| `/api/v1/devices` | `routes/device_api.py` | 设备管理 |
| `/api/v1/assets` | `routes/asset.py` | 资产管理 |
| `/api/v1/monitoring` | `routes/monitoring.py` | 监控告警 |
| `/api/v1/reports` | `routes/report*.py` | 报告管理 |
| `/api/v1/workorders` | `routes/workorder.py` | 工单管理 |
| `/api/v1/knowledge` | `routes/knowledge.py` | 知识库 |
| `/api/v1/ai` | `routes/ai.py` | AI 助手 |
| `/api/v1/notification` | `routes/notification.py` | 通知管理 |

---

## 6. 配置管理

### 6.1 配置文件结构

```
config/
├── dev.yaml              # 开发环境配置
├── prod.yaml             # 生产环境配置
├── devices/
│   ├── devices.yaml      # 设备主配置
│   ├── adapters.yaml     # 适配器配置
│   └── templates/        # 设备配置模板
│       ├── linux_server.yaml
│       ├── windows_server.yaml
│       ├── cisco_router.yaml
│       └── ...
└── examples/
    └── production.yaml   # 生产环境完整示例
```

### 6.2 环境变量覆盖

```bash
# 优先级: 环境变量 > 配置文件 > 默认值
export DATABASE_URL=postgresql://user:pass@host/db
export REDIS_URL=redis://localhost:6379
export CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## 7. 设备配置示例

```yaml
# config/devices/templates/linux_server.yaml
device_type: server
category: Linux服务器

protocols:
  primary: ssh
  fallback: snmp

metrics:
  - cpu
  - memory
  - disk
  - network
  - process

commands:
  cpu: "top -bn1 | grep 'Cpu(s)'"
  memory: "free -m"
  disk: "df -h"
```

---

## 8. 版本信息

- 当前版本: v1.0.0
- 最后更新: 2026-05-06
