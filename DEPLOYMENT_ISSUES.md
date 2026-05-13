# 部署问题记录 - ITOps Platform

## 目的
本文档记录在实际部署、运行过程中发现的依赖问题、配置坑、网络限制、兼容性问题等，供后续部署参考。

---

## 一、环境依赖问题

### 1. Python docker SDK v7 兼容性
- **问题**：`docker.Client` 已被移除，使用 `docker.APIClient` 代替
- **影响文件**：`modules/collection/api_collector/docker_client.py` 第87行
- **修复**：
  ```python
  # 错误
  client = docker.Client(base_url='unix:///var/run/docker.sock')
  # 正确
  client = docker.APIClient(base_url='unix:///var/run/docker.sock')
  ```
- **验证**：`python3 -c "import docker; print(docker.__version__)"` 确认版本 ≥ 7.0.0

### 2. TDengine REST API 认证格式
- **问题**：TDengine 3.x REST API 需要 `Content-Type: text/plain`，不能用 `application/json`
- **正确调用方式**：
  ```python
  requests.post(
      'http://127.0.0.1:6041/rest/sql',
      auth=('root', 'taosdata'),
      data=sql,  # 注意是 data= 不是 json=
      headers={'Content-Type': 'text/plain'},
      timeout=10
  )
  ```
- **原因**：TDengine 3.x 内部使用 taosAdapter，协议与 2.x 不同

### 3. TDengine 超级表写入必须指定子表名（tbname）
- **问题**：错误码 512 - `tbname column can not be null`
- **说明**：TDengine 超级表要求数据必须插入到具体的**子表**中，不能直接插入到超级表
- **正确流程**：
  1. 先创建超级表（含 TAGS）
  2. 插入数据时必须指定 `tbname` 值（即子表名）
  ```sql
  CREATE STABLE itops_docker.docker_metrics (...) TAGS (container_name BINARY(64), container_status BINARY(32));
  INSERT INTO itops_docker.mysql_container (ts, cpu_pct, ...) VALUES (NOW, 0.5, ...) -- 子表名
  ```
- **替代方案**：不用超级表，直接建普通表，按容器名区分
  ```sql
  CREATE TABLE itops_docker.docker_mysql (ts TIMESTAMP, cpu_pct FLOAT, ...);
  ```

---

## 二、网络与环境限制

### 4. GitHub 直连超时
- **问题**：`git push` / `git clone` 直连 github.com 超时（600s+）
- **现象**：GitHub API 可通（`api.github.com`），但 git clone/push 流量超时
- **状态**：Ollama 模型下载也无法完成（文件流量超时）
- **临时方案**：
  - 使用 Gitee/Gitea 镜像
  - 或使用 GitHub token 通过 API 操作（`gh` CLI）

### 5. HuggingFace 直连超时
- **问题**：`huggingface.co` 直连超时
- **方案**：使用镜像站 `https://hf-mirror.com`
  ```bash
  export HF_ENDPOINT="https://hf-mirror.com"
  huggingface-cli download ...
  ```
- **已验证**：ModelScope CDN 可用，速度 ~11MB/s

### 6. Docker Hub 直连超时
- **问题**：官方 `docker.io` 超时
- **方案**：配置国内镜像加速
  ```bash
  # DaoCloud（实测可用）
  docker.m.daocloud.io
  
  # 阿里云（需登录获取加速地址）
  registry.cn-*.aliyuncs.com
  
  # 清华
  docker.mirrors.tuna.tsinghua.edu.cn
  ```
- **配置**：在 `/etc/docker/daemon.json` 中配置 `registry-mirrors`

### 7. sudo 命令频繁超时
- **问题**：`sudo` 在部分环境中超时
- **方案**：使用 `sg docker -c "docker ..."` 代替 `sudo docker ...`

---

## 三、已确认的可用的服务版本

| 服务 | 版本 | 端口 | 备注 |
|------|------|------|------|
| MySQL | 8.0 | 3306 | Docker |
| Redis | 7.2 | 6379 | Docker |
| TDengine | 3.x | 6030/6041 | Docker REST: 6041 |
| Qdrant | 1.7+ | 6333 | Docker |
| MinIO | - | 9000 | Docker |
| API (FastAPI) | - | 8000 | Docker |
| LLM (Qwen3.5-9B) | Q8_0 | 11435 | llama-cpp-python |

---

## 四、蒲公英SD-WAN网关 (10.168.1.1) 接入

### 8. 设备信息
- **IP**: 10.168.1.1
- **类型**: 蒲公英/OrayBox SD-WAN 路由器
- **Web管理**: http://10.168.1.1（登录页面）
- **架构**: 基于 OpenWrt

### 9. 已知接口
- `http://10.168.1.1/` - Web 登录页（可能需认证）
- `http://10.168.1.1/cgi-bin/luci` - LuCI (OpenWrt Web UI)
- 常见默认密码：admin/admin, admin/oraybox, root/admin

### 10. SNMP 探测结果
- SNMP 未开放或不支持（系统描述不含 SNMP）
- 需要通过 Web API 或 SSH 采集

### 11. 后续行动
- [ ] 获取网关登录凭证
- [ ] 通过 Web 登录获取实时流量 API
- [ ] 或通过 `ssh root@10.168.1.1` 采集 `ifconfig`/`ip addr`

---

## 五、容器监控当前状态

### 12. 指标采集状态
| 容器 | CPU% | Memory% | Net I/O | Block I/O | TDengine写入 |
|------|------|---------|---------|-----------|-------------|
| itops-mysql | ✅ | ✅ | ❌ | ❌ | ❌ |
| itops-redis | ✅ | ✅ | ❌ | ❌ | ❌ |
| itops-tdengine | ✅ | ✅ | ❌ | ❌ | ❌ |
| itops-qdrant | ✅ | ✅ | ❌ | ❌ | ❌ |
| itops-minio | ✅ | ✅ | ❌ | ❌ | ❌ |
| itops-api | ✅ | ✅ | ❌ | ❌ | ❌ |

### 13. TDengine 数据库状态
- **数据库**: `itops_docker`
- **超级表**: `docker_metrics`（已建，但写入需子表）
- **当前状态**: 指标采集正常，写入 TDengine 待修复

---

## 六、快速启动检查清单

### 部署前确认
- [ ] 系统 Python 版本 `python3 --version` (需要 3.8+)
- [ ] Docker 已安装并运行 `docker ps`
- [ ] Docker 网络可访问 `docker exec itops-api curl http://host.docker.internal:8000/health`
- [ ] 所有容器日志无 ERROR：`docker-compose logs --tail=50`

### 必装依赖
```bash
pip install docker>=7.0.0 requests taospy-opentsdb  # 核心采集依赖
pip install taifex  # TDengine Python客户端（如用 REST 可不装）
```

### 网络监控前提
- [ ] 确认网络设备 SNMP 端口（UDP 161）开放
- [ ] 或获取网关 Web API 访问凭证
- [ ] 添加设备到 `config/devices/devices.yaml`

---

## 七、GitHub 同步

当文档更新后，执行以下命令同步到 GitHub：

```bash
cd ~/.hermes/projects/itops_platform
git add DEPLOYMENT_ISSUES.md CHANGES.md LOG.md
git commit -m "docs: update deployment issues from production run"
git push origin main
```

> **注意**：如遇 GitHub 连接超时，使用 `ssh -T git@github.com` 测试，或改用 Gitee 镜像。

---

*最后更新：2026-05-13*
