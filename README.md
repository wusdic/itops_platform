# ITOps Intelligence Platform

> 内网本地化AI辅助运维管理平台 - 完全本地化，不依赖互联网

[English](README_en.md) | 简体中文

## 项目简介

ITOps Platform 是一款专为内网环境设计的智能化运维管理平台。基于开源技术栈开发，支持Windows服务器、国产化麒麟Linux、华为网络设备以及天融信、绿盟、启明星辰、深信服等网络安全设备的监控管理。

**核心特性**：
- 🔒 完全内网运行，无互联网依赖
- 🤖 本地AI助手，基于Qwen3.5大模型
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
│              Ollama + Qwen3.5 (本地大模型)                 │
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
| AI助手 | Ollama/Qwen3.5集成、RAG增强 |
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
| PostgreSQL | 14+ |
| Redis | 6+ |
| TDengine | 3.0+ 或 InfluxDB 2.0+ |
| Qdrant | 1.7+ |

### 方式1: Docker部署 (推荐)

```bash
# 克隆项目
git clone https://github.com/wusdic/itops_platform.git
cd itops_platform

# 启动所有服务
chmod +x docker-run.sh
./docker-run.sh up

# 访问服务
# API: http://localhost:8000
# Swagger: http://localhost:8000/docs
# 前端: http://localhost:3000
```

### 方式2: 传统部署

```bash
# 克隆项目
git clone https://github.com/wusdic/itops_platform.git
cd itops_platform

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..

# 复制并编辑配置（如果 config/dev.yaml 不存在）
if [ ! -f config/dev.yaml ] && [ -f config/templates/dev.yaml ]; then
    cp config/templates/dev.yaml config/dev.yaml
fi
# 编辑 config/dev.yaml 配置数据库、Redis等

# 启动后端 (Linux/Mac)
chmod +x start.sh
./start.sh

# 启动前端 (新终端)
cd frontend
npm run dev
```

## 配置说明

### 基础配置 (config/dev.yaml)

```yaml
# 数据库
database:
  host: localhost
  port: 5432
  name: itops
  user: itops
  password: your_password

# Redis
redis:
  host: localhost
  port: 6379

# TDengine
tdengine:
  host: localhost
  port: 6030

# Qdrant向量库
qdrant:
  host: localhost
  port: 6333

# AI配置 (可选)
ai:
  provider: ollama
  base_url: http://localhost:11434
  model: qwen2.5:7b
```

### 环境变量

也可以通过环境变量覆盖配置：

```bash
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export REDIS_HOST=localhost
export CONFIG_FILE=config/prod.yaml
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
│   └── templates/            # 配置模板
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
├── requirements.txt          # Python依赖
├── Dockerfile
├── docker-compose.yml
├── start.sh                  # 后端启动脚本
├── run.sh                    # 带依赖安装的启动脚本
└── run.bat                   # Windows启动脚本
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
- 文档: (待补充)

## 联系方式

- Issue: https://github.com/wusdic/itops_platform/issues

---

**ITOps Platform - 让运维更智能、更简单**