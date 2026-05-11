# ITOps Intelligence Platform

> 内网本地化AI辅助运维管理平台 - 完全本地化，不依赖互联网

[English](README_en.md) | 简体中文

## 项目简介

ITOps Platform 是一款专为内网环境设计的智能化运维管理平台。基于开源技术栈开发，支持Windows服务器、国产化麒麟Linux、华为网络设备以及天融信、绿盟、启明星辰、深信服等网络安全设备的监控管理。

**核心特性**：
- 🔒 完全内网运行，无互联网依赖
- 🤖 本地AI助手，基于Qwen3.5-9B-DeepSeek-V4-Flash-Q8_0大模型
- 📊 全面的监控告警能力
- 📝 智能报告生成
- 📚 知识库+RAG智能检索
- 🔧 自动化运维与自愈

## 支持的设备类型

### 操作系统
- Windows Server 2012+ (WinRM/PowerShell)
- 麒麟Linux (Kylin OS)
- CentOS / Rocky Linux
- Ubuntu / Debian

### 网络设备
- 华为交换机、路由器、防火墙、AC、AP
- 天融信防火墙
- 绿盟防火墙、IDS、IPS
- 启明星辰防火墙、IDS
- 深信服防火墙、AD、AC

### 采集方式
- SNMP v1/v2c/v3
- SSH (Linux麒麟系统)
- WinRM (Windows系统)
- API (Zabbix/Prometheus)
- 日志 (Syslog/文件/Windows Event)
- 浏览器自动化 (无API设备)

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    前端展示层 (Vue3 + Element Plus)         │
├─────────────────────────────────────────────────────────────┤
│                    API网关层 (FastAPI)                      │
├──────────┬──────────────┬───────────────┬──────────────────┤
│ 监控告警  │   工单管理    │   知识库      │    AI助手        │
├──────────┴──────────────┴───────────────┴──────────────────┤
│                    业务功能层                                │
│  报告生成 │ 资产管理 │ 告警自愈 │ 脚本执行 │ 任务调度        │
├─────────────────────────────────────────────────────────────┤
│                    存储层                                    │
│  PostgreSQL │ TDengine │ Qdrant │ Redis │ MinIO            │
├─────────────────────────────────────────────────────────────┤
│                    采集层                                    │
│  SNMP │ SSH │ API │ 日志 │ 浏览器自动化                      │
├─────────────────────────────────────────────────────────────┤
│                    基础层                                    │
│         配置管理 │ 日志管理 │ 权限管理 (RBAC/LDAP)           │
├─────────────────────────────────────────────────────────────┤
│                    AI推理层                                  │
│              Qwen3.5-9B-DeepSeek-V4-Flash-Q8_0 (本地大模型)                 │
└─────────────────────────────────────────────────────────────┘
```

## 功能模块

### 基础层
| 模块 | 说明 |
|------|------|
| 配置管理 | YAML/JSON/ENV配置，敏感信息加密 |
| 日志管理 | 结构化日志，多输出，JSON/Text格式 |
| 数据库模型 | 设备、告警、工单、用户模型 |
| 权限管理 | RBAC、LDAP集成、操作审计 |

### 采集层
| 模块 | 说明 |
|------|------|
| SNMP采集 | v1/v2c/v3、Get/Walk、MIB解析 |
| API采集 | Zabbix、Prometheus、通用HTTP |
| SSH采集 | Paramiko、WinRM、麒麟Linux |
| 日志采集 | Syslog、Windows Event、文件 |
| 浏览器自动化 | Playwright、Web界面采集 |

### 存储层
| 模块 | 说明 |
|------|------|
| 时序库 | TDengine、InfluxDB客户端 |
| 向量库 | Qdrant客户端、RAG检索 |
| 文件存储 | MinIO/本地统一接口 |
| 缓存 | Redis多数据类型 |

### 业务层
| 模块 | 说明 |
|------|------|
| 监控告警 | 告警规则、触发、通知、仪表盘 |
| 工单管理 | 工单流程、审批、变更、统计 |
| 知识库 | SOP库、故障库、RAG、AI录入 |
| 报告生成 | 日报、周报、月报、RCA报告 |
| AI助手 | Qwen3.5-9B-DeepSeek-V4-Flash-Q8_0、RAG增强 |
| 资产管理 | CMDB、生命周期、风险评估 |

### 自动化层
| 模块 | 说明 |
|------|------|
| 任务调度 | APScheduler、任务链、分布式 |
| 告警自愈 | 故障检测、根因分析、恢复策略 |
| 脚本执行 | 脚本库、远程执行、批量执行 |

## 快速开始

### 环境要求

| 组件 | 要求 |
|------|------|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker | 20.10+ |
| Docker Compose | 2.0+ |

### 方式1: Docker部署 (推荐)

```bash
# 克隆项目
git clone https://github.com/wusdic/itops_platform.git
cd itops_platform

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填写实际配置（必填项见下文）
vim .env

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api

# 访问服务
# 前端: http://localhost:3000
# API: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

### 方式2: 本地开发

```bash
# 克隆项目
git clone https://github.com/wusdic/itops_platform.git
cd itops_platform

# 1. 确保本地运行以下服务（Docker 启动）
docker-compose up -d mysql redis tdengine qdrant minio

# 2. 复制环境变量模板
cp .env.example .env
vim .env  # 填写实际配置

# 3. 安装后端依赖
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 安装前端依赖
cd frontend
npm install
cd ..

# 5. 启动后端
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 6. 启动前端（新终端）
cd frontend
npm run dev
```

---

## 配置说明

### 必填配置清单

部署前必须配置以下内容（编辑 `.env` 文件）：

#### 1. 安全密钥（必须修改）

```bash
# 应用加密密钥（至少32字符）
SECRET_KEY=your-secret-key-at-least-32-characters

# JWT 签名密钥
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars

# Session 加密密钥
SESSION_SECRET_KEY=your-session-secret-key
```

#### 2. 数据库密码

```bash
# MySQL 密码
ITOPS_DB_PASSWORD=your-secure-db-password
```

#### 3. AI 配置（如需 AI 功能）

```bash
# Ollama 服务地址（Docker 环境使用 host.docker.internal）
AI_MODEL=qwen2.5:7b

# 或使用 OpenAI（需要互联网）
# OPENAI_API_KEY=sk-your-openai-key
```

详细配置说明请参考 [CONFIG_GUIDE.md](CONFIG_GUIDE.md)。

---

### 配置文件结构

```
itops_platform/
├── .env                    # 环境变量（敏感信息）
├── .env.example            # 环境变量模板
├── config/
│   ├── dev.yaml            # 开发环境配置
│   ├── prod.yaml           # 生产环境配置
│   └── devices/            # 设备配置文件
├── docker-compose.yml      # Docker 服务编排
└── Dockerfile             # API 容器镜像
```

### 配置加载优先级

配置加载顺序（后者覆盖前者）：

1. `config/default.yaml`
2. `config/{environment}.yaml` (dev/prod)
3. `config/local.yaml` (本地覆盖)
4. 环境变量 `.env`

---

### Docker Compose 服务依赖

```
api (FastAPI)
├── mysql (MySQL 8.0) - 等待健康检查
├── redis (Redis 7) - 等待健康检查
├── tdengine (TDengine 3.2) - 等待健康检查
├── qdrant (Qdrant v1.7) - 等待健康检查
└── minio (MinIO latest) - 等待健康检查

frontend (Node 18 - Vite dev server)
└── api
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 3000 | Vue3 开发服务器 |
| API | 8000 | FastAPI 应用 |
| MySQL | 3306 | 关系数据库 |
| Redis | 6379 | 缓存 |
| TDengine | 6030 | 时序数据库 |
| Qdrant | 6333 | 向量数据库 |
| MinIO API | 9000 | 对象存储 |
| MinIO Console | 9001 | 管理界面 |

---

### AI 模型配置

#### 本地 Ollama（推荐，内网使用）

```bash
# 1. 安装 Ollama
# https://ollama.ai/

# 2. 拉取模型
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 3. 验证
ollama list
```

#### 云端 OpenAI（需要互联网）

```bash
# .env 中配置
OPENAI_API_KEY=sk-your-key
```

---

### 告警通知配置（可选）

#### 钉钉

```bash
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN
DINGTALK_SECRET=YOUR_SECRET
```

#### 飞书

```bash
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK
FEISHU_SECRET=YOUR_SECRET
```

#### 邮件

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-smtp-password
FROM_ADDRESS=alerts@example.com
```

---

### 设备接入配置

设备配置位于 `config/devices/` 目录：

```bash
# 查看支持的设备类型
cat config/devices/devices.yaml

# 支持的设备类型：
# - Linux 服务器 (SSH)
# - Windows 服务器 (WinRM)
# - 华为网络设备 (SNMP/SSH)
# - 天融信防火墙 (API)
# - 绿盟防火墙 (API)
# - 启明星辰 (API)
# - 深信服 (API)
# - IPMI 硬件监控
```

---

### 前端配置页面

系统提供可视化配置界面，无需手动编辑配置文件：

访问 `http://localhost:3000` → 系统设置

可在前端页面配置：
- 基本信息（系统名称、描述、时区）
- 监控配置（数据源、存储策略）
- 告警配置（规则、通知渠道）
- 用户管理
- 系统日志
- 安全设置

---

## 常见问题

### Q: Docker 环境下如何访问宿主机服务？

A: 使用 `host.docker.internal`（已在 docker-compose.yml 中配置）：

```yaml
# 示例：Ollama 配置
ai:
  base_url: http://host.docker.internal:11434
```

### Q: 如何启用 InfluxDB 替代 TDengine？

A: 取消 `docker-compose.yml` 中 InfluxDB 服务的注释，并修改配置：

```yaml
# config/dev.yaml
timeseries:
  type: influxdb
  host: localhost
  port: 8086
  token: "your-influxdb-token"
  org: "itops"
  bucket: "metrics"
```

### Q: 服务启动后 API 返回 503？

A: 检查依赖服务是否健康：
```bash
docker-compose ps
docker-compose logs mysql redis tdengine
```

### Q: 如何查看完整配置？

A: 访问 API 端点：
```bash
curl http://localhost:8000/api/v1/admin/config
```
```

## API文档

启动服务后访问 Swagger 文档：

- 开发环境: http://localhost:8000/docs
- 生产环境: http://your-domain.com/docs

### 主要API端点

| 模块 | 路径 | 说明 |
|------|------|------|
| 监控管理 | `/api/v1/monitoring` | 指标查询、告警管理 |
| 工单管理 | `/api/v1/workorder` | 工单CRUD、审批流程 |
| 知识库 | `/api/v1/knowledge` | 文档管理、搜索、RAG |
| 报告管理 | `/api/v1/report` | 报告模板、生成、下载 |
| 资产管理 | `/api/v1/asset` | 设备管理、生命周期 |
| AI助手 | `/api/v1/ai` | 对话、RAG增强 |
| 系统管理 | `/api/v1/admin` | 用户、角色、配置 |

## 项目结构

```
itops_platform/
├── api/                     # API网关层
│   ├── main.py             # FastAPI入口
│   ├── dependencies.py      # 依赖注入
│   ├── middleware/          # 中间件
│   └── routes/              # API路由
├── modules/                 # 核心模块
│   ├── foundation/           # 基础层
│   │   ├── config_manager/  # 配置管理
│   │   ├── log_manager/     # 日志管理
│   │   ├── db_models/       # 数据库模型
│   │   └── auth_manager/    # 权限管理 (RBAC/LDAP)
│   ├── collection/           # 采集层
│   │   ├── snmp_collector/  # SNMP采集
│   │   ├── ssh_collector/   # SSH采集
│   │   ├── api_collector/   # API采集
│   │   ├── log_collector/   # 日志采集
│   │   ├── ipmi_collector/  # IPMI采集
│   │   └── browser_automation/  # 浏览器自动化
│   ├── storage/             # 存储层
│   │   ├── tdengine/       # TDengine客户端
│   │   ├── influxdb/        # InfluxDB客户端
│   │   ├── qdrant/          # Qdrant向量库
│   │   ├── redis_client/    # Redis客户端
│   │   └── minio/           # MinIO文件存储
│   ├── business/            # 业务层
│   │   ├── monitoring/      # 监控告警
│   │   ├── workorder/       # 工单管理
│   │   ├── knowledge_base/  # 知识库
│   │   ├── report_generator/ # 报告生成
│   │   ├── ai_copilot/      # AI助手
│   │   ├── asset_management/ # 资产管理
│   │   ├── notification/    # 通知服务
│   │   └── scheduler/        # 任务调度
│   └── automation/          # 自动化层
│       ├── task_scheduler/   # 任务调度
│       ├── self_healing/    # 告警自愈
│       └── script_executor/  # 脚本执行
├── frontend/                # 前端界面
│   ├── src/
│   │   ├── views/           # 页面视图
│   │   ├── components/       # 组件
│   │   ├── api/              # API调用
│   │   ├── stores/           # 状态管理
│   │   └── router/           # 路由
│   └── dist/                 # 构建产物
├── config/                   # 配置文件
│   ├── dev.yaml              # 开发环境配置
│   ├── prod.yaml             # 生产环境配置
│   └── devices/              # 设备配置文件
├── core/                     # 核心基础设施
│   ├── config/              # 统一配置
│   ├── log/                 # 统一日志
│   ├── protocols.py         # 协议类型定义
│   └── storage/             # 存储客户端基类
├── tests/                    # 测试
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── simulation/           # 模拟测试
├── docs/                     # 文档
├── .env.example              # 环境变量模板
├── CONFIG_GUIDE.md           # 详细配置指南
├── requirements.txt          # Python依赖
├── Dockerfile
├── docker-compose.yml
└── README.md                # 本文件
```

## 测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定模块测试
pytest tests/unit/test_monitoring.py -v

# 生成覆盖率报告
pytest tests/unit/ --cov=modules --cov-report=html
```

## 开发指南

### 添加新的采集模块

```python
# modules/collection/my_collector/__init__.py
from .collector import MyCollector

__all__ = ['MyCollector']

# modules/collection/my_collector/collector.py
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class MyCollector:
    """自定义采集器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def collect(self, device_id: str) -> List[Dict]:
        # 实现采集逻辑
        return []
```

### 添加新的业务模块

```python
# modules/business/my_module/__init__.py
from .service import MyService

__all__ = ['MyService']
```

## 硬件推荐

针对50台设备规模：

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4核 | 8核+ |
| 内存 | 16GB | 32GB+ |
| 系统盘 | 100GB | 200GB SSD |
| 数据盘 | 300GB | 500GB SSD |
| GPU | - | RTX 3060 12GB (AI推理) |

## 安全特性

- 🔒 完全内网运行，无互联网依赖
- 🔒 敏感配置加密存储
- 🔒 RBAC权限控制
- 🔒 LDAP集成认证
- 🔒 完整操作审计日志
- 🔒 AI输出需人工审核后执行

## 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查PostgreSQL服务是否运行
   - 验证用户名密码配置
   - 检查防火墙端口

2. **前端无法访问API**
   - 检查API服务是否运行在8000端口
   - 检查CORS配置
   - 查看浏览器控制台

3. **AI助手无响应**
   - 确认Ollama服务是否运行
   - 检查模型是否已下载: `ollama list`
   - 验证AI配置中的URL和模型名称

4. **告警不触发**
   - 检查监控采集是否正常
   - 验证告警规则配置
   - 查看日志排查问题

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 项目地址

- GitHub: https://github.com/wusdic/itops_platform
- 详细配置指南: [CONFIG_GUIDE.md](CONFIG_GUIDE.md)

## 联系方式

- Issue: https://github.com/wusdic/itops_platform/issues

---

**ITOps Platform - 让运维更智能、更简单**