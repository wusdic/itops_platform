# ITOps Platform 配置指南

## 目录
- [快速开始](#快速开始)
- [配置文件结构](#配置文件结构)
- [环境变量配置](#环境变量配置)
- [Docker Compose 服务依赖](#docker-compose-服务依赖)
- [各服务配置详情](#各服务配置详情)
- [必填配置清单](#必填配置清单)

---

## 快速开始

### 方式一：Docker Compose 部署（推荐生产环境）

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 填写实际配置
vim .env

# 3. 启动所有服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f api
```

### 方式二：本地开发

```bash
# 1. 确保本地运行以下服务
# - MySQL (localhost:3306)
# - Redis (localhost:6379)
# - TDengine (localhost:6030) 或 InfluxDB (localhost:8086)
# - Qdrant (localhost:6333)
# - LLM 服务 (localhost:11435)

# 2. 复制环境变量模板
cp .env.example .env

# 3. 编辑 .env 填写实际配置

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动开发服务器
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 配置文件结构

```
itops_platform/
├── .env                    # 环境变量（本地敏感信息）
├── .env.example            # 环境变量模板
├── config/
│   ├── dev.yaml            # 开发环境配置
│   ├── prod.yaml           # 生产环境配置
│   ├── devices/            # 设备配置文件
│   │   ├── devices.yaml    # 设备列表
│   │   └── adapters.yaml   # 适配器配置
│   └── templates/          # 配置模板
├── docker-compose.yml      # Docker 服务编排
└── Dockerfile             # API 容器镜像
```

---

## 环境变量配置

### .env 文件说明

复制 `.env.example` 为 `.env`，以下是需要配置的环境变量：

#### 必填项

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `SECRET_KEY` | 应用密钥 | - | `your-secret-key-at-least-32-chars` |
| `ITOPS_DB_PASSWORD` | 数据库密码 | - | `your-secure-db-password` |

#### 数据库配置

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `ITOPS_DB_TYPE` | 数据库类型 | `mysql` | `mysql` |
| `ITOPS_DB_HOST` | 数据库主机 | `localhost` | `mysql` (Docker网络内) |
| `ITOPS_DB_PORT` | 数据库端口 | `3306` | `3306` |
| `ITOPS_DB_USER` | 数据库用户名 | `root` | `itops_user` |
| `ITOPS_DB_NAME` | 数据库名 | `itops_platform` | `itops_platform` |

#### Redis 配置

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `REDIS_HOST` | Redis 主机 | `localhost` | `redis` (Docker网络内) |
| `REDIS_PORT` | Redis 端口 | `6379` | `6379` |
| `REDIS_DB` | Redis 数据库号 | `0` | `0` |

#### AI 配置

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `AI_ENABLED` | 启用 AI 功能 | `true` | `true` |
| `AI_MODEL` | AI 模型名称 | `qwen3.5-9b-deepseek-v4-flash-q8_0` | `qwen3.5-9b-deepseek-v4-flash-q8_0` |
| `AI_BASE_URL` | LLM 服务地址 | `http://127.0.0.1:11435` | `http://127.0.0.1:11435` |

#### 告警通知配置（可选）

**钉钉**

```bash
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN
DINGTALK_SECRET=YOUR_SECRET
```

**飞书**

```bash
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK
FEISHU_SECRET=YOUR_SECRET
```

**邮件**

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-smtp-password
FROM_ADDRESS=alerts@example.com
```

#### 安全配置

```bash
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
SESSION_SECRET_KEY=your-session-secret-key
```

#### MinIO 配置（可选）

```bash
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
```

---

## Docker Compose 服务依赖

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

### 健康检查端点

| 服务 | 健康检查命令 | 端点 |
|------|-------------|------|
| api | `curl -f http://localhost:8000/health` | `/health` |
| mysql | `mysqladmin ping` | - |
| redis | `redis-cli ping` | - |
| tdengine | `taos -s 'show databases;'` | - |
| qdrant | `curl -f http://localhost:6333/health` | `/health` |
| minio | `curl -f http://localhost:9000/minio/health/live` | `/minio/health/live` |
| frontend | `wget --spider -q http://localhost:3000` | - |

---

## 各服务配置详情

### 数据库 (MySQL)

```yaml
# docker-compose.yml
mysql:
  image: mysql:8.0
  environment:
    MYSQL_ROOT_PASSWORD: itops_root_password  # 修改为强密码
    MYSQL_DATABASE: itops_platform
    MYSQL_USER: itops
    MYSQL_PASSWORD: itops_secure_password    # 修改为强密码
```

### 时序数据库 (TDengine)

```yaml
# docker-compose.yml
tdengine:
  image: tdengine/tdengine:3.2.1.0
  ports:
    - "6030:6030"   # TCP 连接
    - "6041:6041"   # RESTful API
```

### 向量数据库 (Qdrant)

```yaml
# docker-compose.yml
qdrant:
  image: qdrant/qdrant:v1.7.0
  ports:
    - "6333:6333"   # gRPC API
    - "6334:6334"   # REST API
```

### 对象存储 (MinIO)

```yaml
# docker-compose.yml
minio:
  image: minio/minio:latest
  environment:
    MINIO_ROOT_USER: minioadmin       # 修改为实际用户
    MINIO_ROOT_PASSWORD: minioadmin123 # 修改为强密码
  ports:
    - "9000:9000"   # API
    - "9001:9001"   # Console
```

### AI 服务 (llama-cpp-python)

本平台使用 llama-cpp-python 直接加载 GGUF 模型，**不依赖 Ollama**。

```bash
# 1. 安装 llama-cpp-python
pip install llama-cpp-python

# 2. 下载 GGUF 模型文件
# 模型：Qwen3.5-9B-DeepSeek-V4-Flash-Q8_0.gguf
mkdir -p /tmp/model_cache_35
# 将模型文件放入上述目录

# 3. 启动 LLM 服务
./start_llm_server_35.sh

# 4. 验证
curl http://127.0.0.1:11435/health
```

---

## 必填配置清单

### 生产环境部署前必须配置

- [ ] **SECRET_KEY** - 应用加密密钥（至少32字符）
- [ ] **ITOPS_DB_PASSWORD** - 数据库密码
- [ ] **JWT_SECRET_KEY** - JWT 签名密钥
- [ ] **SESSION_SECRET_KEY** - Session 加密密钥
- [ ] **MINIO_ROOT_PASSWORD** - MinIO 根密码（如果使用对象存储）
- [ ] **告警 Webhook URL** - 钉钉/飞书机器人（如果使用告警通知）

### 设备接入配置

设备配置位于 `config/devices/` 目录：

```bash
# 编辑设备列表
vim config/devices/devices.yaml

# 支持的设备类型
# - Linux 服务器 (SSH)
# - Windows 服务器 (WinRM)
# - 华为网络设备 (SNMP/SSH)
# - 天融信防火墙 (API)
# - 绿盟防火墙 (API)
# - 启明星辰 (API)
# - 深信服 (API)
# - IPMI 硬件监控
```

### AI 模型配置

本平台使用 **llama-cpp-python** 直接加载 GGUF 模型，无需 Ollama。

```bash
# 1. 下载 GGUF 模型
mkdir -p /tmp/model_cache_35
# 将 Qwen3.5-9B-DeepSeek-V4-Flash-Q8_0.gguf 放入上述目录

# 2. 启动 LLM 服务
./start_llm_server_35.sh

# 3. 环境变量配置
AI_BASE_URL=http://127.0.0.1:11435
AI_MODEL=qwen3.5-9b-deepseek-v4-flash-q8_0
```

### 本地开发（Docker 环境）

Docker Compose 部署时，宿主机 LLM 服务通过 `host.docker.internal` 访问：

```yaml
ai:
  base_url: http://host.docker.internal:11435
  model: qwen3.5-9b-deepseek-v4-flash-q8_0
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
