# ITOps Intelligence Platform

> 内网本地化AI辅助运维管理平台 - 基于开源技术栈，支持国产化环境

## 项目概述

ITOps Platform 是一款专为内网环境设计的智能化运维管理平台，基于您提供的"AI辅助机房运维管理手册"方案开发。平台完全本地化运行，不依赖互联网，支持Windows服务器、国产化麒麟服务器、华为网络设备以及天融信、绿盟、启明星辰、深信服等网络安全设备的监控管理。

## 核心功能

| 功能模块 | 说明 |
|----------|------|
| **智能监控** | 支持SNMP/SSH/API等多种采集方式，覆盖Windows、Linux麒麟、华为设备等 |
| **告警管理** | 灵活告警规则、告警收敛、告警自愈、多渠道通知 |
| **报告生成** | AI辅助生成日巡检报告、周报、月报、年终总结 |
| **知识库** | SOP知识库、故障案例库、RAG智能检索 |
| **工单管理** | 完整工单流程、变更管理、多级审批 |
| **资产管理** | CMDB配置管理、设备寿命评估、更换计划 |
| **AI助手** | 本地Qwen3.5大模型驱动，RAG增强，完全内网运行 |

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    前端展示层 (Vue3 + Element Plus)         │
├─────────────────────────────────────────────────────────────┤
│                    API网关层 (FastAPI)                       │
├──────────┬──────────────┬───────────────┬──────────────────┤
│ 监控告警  │   工单管理    │   知识库      │    AI助手        │
├──────────┴──────────────┴───────────────┴──────────────────┤
│                    存储层                                    │
│  PostgreSQL │ TDengine │ Qdrant │ Redis │ MinIO            │
├─────────────────────────────────────────────────────────────┤
│                    采集层                                    │
│  SNMP │ SSH │ API │ 日志 │ 浏览器自动化                      │
├─────────────────────────────────────────────────────────────┤
│                    基础层                                    │
│         配置管理 │ 日志管理 │ 权限管理 (RBAC/LDAP)            │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

| 类别 | 技术选型 | 说明 |
|------|----------|------|
| **后端** | Python 3.11+, FastAPI | 高性能异步框架 |
| **数据库** | PostgreSQL | 关系型数据 |
| **时序库** | TDengine | 监控指标存储 |
| **向量库** | Qdrant | RAG知识检索 |
| **缓存** | Redis | 会话与数据缓存 |
| **对象存储** | MinIO | 文件存储 |
| **AI推理** | Ollama + Qwen3.5 | 本地大模型 |
| **前端** | Vue 3 + Element Plus | Web管理界面 |

## 监控兼容性

### 操作系统
- ✅ Windows Server 2012+
- ✅ 麒麟Linux (Kylin OS)
- ✅ CentOS / Rocky Linux
- ✅ Ubuntu / Debian

### 网络设备
- ✅ 华为交换机/路由器
- ✅ 华为防火墙/AC/AP
- ✅ 天融信防火墙
- ✅ 绿盟防火墙/IDS/IPS
- ✅ 启明星辰防火墙/IDS
- ✅ 深信服防火墙/AD/AC

## 项目结构

```
itops_platform/
├── modules/                      # 核心模块
│   ├── foundation/              # 基础层
│   │   ├── config_manager/     # 配置管理
│   │   ├── log_manager/        # 日志管理
│   │   ├── db_models/          # 数据库模型
│   │   └── auth_manager/       # 权限管理
│   ├── collection/              # 采集层
│   │   ├── snmp_collector/     # SNMP采集
│   │   ├── ssh_collector/      # SSH采集
│   │   ├── api_collector/       # API采集 (Zabbix/Prometheus)
│   │   ├── browser_automation/  # 浏览器自动化
│   │   └── log_collector/       # 日志采集
│   ├── storage/                 # 存储层
│   │   ├── tdengine/           # TDengine时序库
│   │   ├── influxdb/           # InfluxDB时序库
│   │   ├── qdrant/             # Qdrant向量库
│   │   ├── redis_client/       # Redis缓存
│   │   └── minio/              # MinIO对象存储
│   ├── business/               # 业务层
│   │   ├── monitoring/         # 监控告警
│   │   ├── workorder/         # 工单管理
│   │   ├── knowledge_base/    # 知识库
│   │   ├── report_generator/  # 报告生成
│   │   ├── ai_copilot/        # AI助手
│   │   └── asset_management/  # 资产管理
│   └── automation/             # 自动化层
│       ├── task_scheduler/     # 任务调度
│       ├── self_healing/       # 告警自愈
│       └── script_executor/    # 脚本执行
├── config/                      # 配置文件
│   ├── dev.yaml               # 开发环境
│   ├── test.yaml              # 测试环境
│   ├── prod.yaml              # 生产环境
│   └── templates/             # 配置模板
├── tests/                      # 测试
│   ├── unit/                  # 单元测试
│   └── integration/           # 集成测试
├── docs/                       # 文档
├── frontend/                   # 前端 (待开发)
└── requirements.txt           # Python依赖
```

## 已完成模块

### 基础层 (Foundation)
- ✅ **FM-01 配置管理** - YAML/JSON/ENV配置，敏感信息加密，配置验证
- ✅ **FM-02 日志管理** - 结构化日志，多输出支持，JSON/Text格式
- ✅ **FM-03 数据库模型** - 设备模型、告警模型、工单模型

### 采集层 (Collection)
- ✅ **CM-01 SNMP采集** - SNMP v1/v2c/v3，Get/Walk操作，MIB解析
- ✅ **CM-02 API采集** - Zabbix API、Prometheus API、通用HTTP客户端

### 存储层 (Storage)
- ✅ **SM-01 时序数据库** - TDengine客户端、InfluxDB客户端
- ✅ **SM-02 向量数据库** - Qdrant客户端、RAG检索支持
- ✅ **SM-03 文件存储** - MinIO/本地统一接口
- ✅ **SM-04 缓存管理** - Redis客户端、多种数据类型支持

### 待开发模块
- ⏳ **FM-04 权限管理** - RBAC、LDAP集成
- ⏳ **CM-03 浏览器自动化** - Playwright封装
- ⏳ **CM-04 SSH采集** - Paramiko封装
- ⏳ **CM-05 日志采集** - Filebeat替代方案
- ⏳ **BM-01~BM-06 业务模块**
- ⏳ **AM-01~AM-03 自动化模块**
- ⏳ **前端界面**

## 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- TDengine 3.0+ 或 InfluxDB 2.0+
- Qdrant 1.7+
- MinIO (可选)
- Ollama (用于AI功能)

### 安装

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/itops_platform.git
cd itops_platform

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp config/dev.yaml.example config/dev.yaml
# 编辑 config/dev.yaml 填入您的配置

# 运行测试
pytest tests/unit/ -v
```

### 使用示例

```python
from modules.foundation.config_manager import ConfigManager
from modules.collection.snmp_collector import SNMPClient
from modules.storage.tdengine import TDengineClient

# 加载配置
config = ConfigManager("config/dev.yaml")

# SNMP采集
snmp = SNMPClient(config.get("snmp"))
result = snmp.get("192.168.1.1", "1.3.6.1.2.1.1.1.0")

# 时序数据写入
td = TDengineClient(config.get("tdengine"))
td.insert("sensors", {"temperature": 25.5, "humidity": 60}, tags={"device": "sensor1"})
```

## 部署方式

### Docker Compose (推荐用于50台设备规模)

```yaml
# docker-compose.yml 示例
services:
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - tdengine
      - qdrant

  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: itops
      POSTGRES_USER: itops
      POSTGRES_PASSWORD: your_password

  tdengine:
    image: tdengine/tdengine:latest

  qdrant:
    image: qdrant/qdrant:latest

  redis:
    image: redis:7-alpine
```

### 硬件推荐 (50台设备规模)

| 组件 | 规格 |
|------|------|
| CPU | 8核+ |
| 内存 | 32GB+ |
| 磁盘 | 500GB+ SSD |
| GPU | 可选 (用于本地AI推理) |

## 安全特性

- 🔒 完全内网运行，无互联网依赖
- 🔒 敏感配置加密存储
- 🔒 RBAC权限控制
- 🔒 完整操作审计日志
- 🔒 AI输出需人工审核后方可执行

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 联系方式

- Issue: https://github.com/YOUR_USERNAME/itops_platform/issues
