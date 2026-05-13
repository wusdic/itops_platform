# ITOps Intelligence Platform - 开发任务清单

> ⚠️ **文档更新日期**: 2026-05-13
> 本文档已根据实际代码实现状态重新校准。表格中状态标记与实际不符者，以本节说明为准。

---

## 实际项目规模

```
Python 后端:   114 个模块文件
前端:          38 个 Vue 视图文件
API 路由:      21 个路由模块
测试用例:      1712 个（65 个测试文件）
代码行数:      ~95,000 行（后端）
技术栈:        FastAPI + Vue3 + SQLAlchemy + TDengine/Qdrant/MinIO/Redis
```

---

## 一、基础设施层（Foundation）

| 任务ID | 模块 | 文件 | 状态 | 说明 |
|-------|------|------|------|------|
| T-01 | FM-01 配置管理 | config.py / loader.py / validator.py | ✅ | 支持YAML/JSON/ENV, 敏感信息加密, 配置验证 |
| T-02 | FM-02 日志管理 | logger.py / handlers.py / formatter.py | ✅ | 日志管理器, 结构化日志, JSON/Text格式 |
| T-03 | FM-03 数据库模型 | base.py / device.py / alert.py / workorder.py | ✅ | SQLAlchemy模型, 设备/告警/工单/审计 |
| T-04 | FM-04 权限管理 | auth.py / rbac.py / audit.py | ✅ | JWT认证, RBAC, LDAP, 操作审计 |

---

## 二、数据采集层（Collection）

| 任务ID | 模块 | 文件 | 状态 | 说明 |
|-------|------|------|------|------|
| T-05 | CM-01 SNMP采集 | snmp_client.py / mib_parser.py / trap_receiver.py | ✅ | SNMP v1/v2c/v3, MIB解析, Trap接收 |
| T-06 | CM-02 API采集 | prometheus_client.py / zabbix_client.py / http_client.py | ✅ | Prometheus/Zabbix HTTP采集, Kubernetes |
| T-07 | CM-03 浏览器自动化 | browser_driver.py / script_recorder.py / task_executor.py | ✅ | Playwright封装, 7种设备适配器 |
| T-08 | CM-04 SSH采集 | ssh_client.py / winrm_client.py / config_deployer.py | ✅ | SSH/WinRM, Linux/Windows/麒麟采集 |
| T-09 | CM-05 日志采集 | file_reader.py / syslog_receiver.py / forwarder.py | ✅ | 文件日志/Syslog/Windows事件/转发 |
| T-10 | CM-06 IPMI采集 | ipmi_client.py | ✅ | IPMI带外采集 |
| T-11 | CM-07 安全扫描 | security_scanner.py | ✅ | 漏洞扫描 |
| T-12 | CM-08 设备发现 | scanner.py / snmp_scanner.py | ✅ | 自动发现 |

---

## 三、数据存储层（Storage）

| 任务ID | 模块 | 文件 | 状态 | 说明 |
|-------|------|------|------|------|
| T-13 | SM-01 时序数据库 | client.py / writer.py / query.py | ✅ | TDengine/InfluxDB客户端, 批量写入 |
| T-14 | SM-02 向量数据库 | client.py / indexer.py / searcher.py | ✅ | Qdrant客户端, RAG语义检索 |
| T-15 | SM-03 文件存储 | storage.py / backup.py / exporter.py | ✅ | 本地/MinIO, 备份管理, PDF/Excel导出 |
| T-16 | SM-04 缓存管理 | redis_client.py / cache.py | ✅ | Redis, 缓存装饰器 |

---

## 四、业务功能层（Business）

| 任务ID | 模块 | 文件 | 状态 | 说明 |
|-------|------|------|------|------|
| T-17 | BM-01 监控告警 | monitor.py / alerter.py / rules.py / notification.py | ✅ | 指标监控, 告警触发/抑制, 多渠道通知 |
| T-18 | BM-02 工单管理 | workorder.py / flow.py / approval.py / stats.py | ✅ | 工单CRUD, 流程引擎, 多级审批, KPI |
| T-19 | BM-03 知识库 | sop.py / case.py / document.py / search.py | ✅ | SOP知识库, 故障案例, 文档, AI辅助 |
| T-20 | BM-04 报告生成 | generator.py / daily_report.py / templates.py | ✅ | 日周月报, RCA报告, PDF/Excel导出 |
| T-21 | BM-05 AI助手 | llm_client.py / prompt_engine.py / rag.py / scenarios.py | ✅ | 本地LLM集成(Ollama llama-cpp-python), RAG, 运维场景 |
| T-22 | BM-06 资产管理 | asset.py / lifecycle.py / risk.py / assessment.py | ✅ | 资产台账, 生命周期, 风险评估 |
| T-23 | BM-07 备份管理 | backup_manager.py | ✅ | 备份策略与恢复 |

---

## 五、自动化层（Automation）

| 任务ID | 模块 | 文件 | 状态 | 说明 |
|-------|------|------|------|------|
| T-24 | AM-01 任务调度 | scheduler.py / task.py / monitor.py / executor.py | ✅ | 分布式定时任务, Cron, 任务链 |
| T-25 | AM-02 告警自愈 | detector.py / healer.py / playbook.py | ✅ | 故障检测, 根因分析, 自动恢复, 剧本管理 |
| T-26 | AM-03 脚本执行 | executor.py / library.py / remote.py | ✅ | 本地/远程脚本执行, 脚本库 |

---

## 六、前端展示层（Frontend）

| 任务ID | 模块 | 文件 | 状态 | 说明 |
|-------|------|------|------|------|
| T-27 | 前端框架 | Vue3 + Vite + Element Plus + Pinia | ✅ | 项目初始化, 路由守卫, 状态管理 |
| T-28 | 监控仪表盘 | dashboard/index.vue / performance.vue | ✅ | 实时监控大屏, 性能指标 |
| T-29 | 告警中心 | Alerts.vue / monitoring/alerts.vue | ✅ | 告警列表, 筛选, 规则配置 |
| T-30 | 工单管理 | workorder/list.vue / create.vue / my.vue | ✅ | 工单列表, 创建, 我的工单 |
| T-31 | 知识库 | KnowledgeBase.vue / knowledge/list.vue | ✅ | 知识搜索, 分类, 详情 |
| T-32 | 报告中心 | Reports.vue | ✅ | 报告列表, 预览, 生成 |
| T-33 | AI助手 | AICopilot.vue / ai/copilot.vue | ✅ | AI运维助手, 语义检索, 对话 |
| T-34 | 系统设置 | Settings.vue / system/*.vue | ✅ | 设备/用户/菜单/角色/字典/通知配置 |
| T-35 | 自动化 | automation/script.vue / task.vue / execute.vue | ✅ | 脚本管理, 任务调度, 执行记录 |
| T-36 | 备份 | backup/list.vue / restore.vue | ✅ | 备份列表, 恢复 |

**前端视图共 38 个**，覆盖所有业务模块。

---

## 七、大模型部署（LLM）

> 完成日期: 2026-05-13

| 项目 | 详情 |
|------|------|
| 模型 | Qwen3.5-9B-DeepSeek-V4-Flash-Q8_0.gguf |
| 大小 | 9.53 GB |
| 下载来源 | ModelScope (Jackrong/Pwnrong/Qwen3.5-9B-DeepSeek-V4-Flash-GGUF) |
| 推理引擎 | llama-cpp-python 0.3.22 (conda环境) |
| 启动脚本 | start_llm_server_35.sh |
| 服务端口 | 11435 |
| API端点 | POST /api/v1/ai/chat |
| 状态 | ✅ 运行中, 健康 |

---

## 当前开发状态

```
后端模块:   ✅ 114 个文件全部实现
前端视图:   ✅ 38 个 Vue 文件全部实现
测试用例:   ⏳ 运行中 (1712 个)
LLM部署:   ✅ 完成
整体进度:   ████████████████████████  ~95%
```

---

## 依赖关系图

```
FM-01 ─┬─→ FM-02
       │
       ├─→ CM-01 ─→ SM-01 ─→ BM-01 ─→ AM-01
       │                   │
       ├─→ CM-02 ──────────┴─→ BM-02
       │                   │
       ├─→ CM-03 ──→ SM-02 ─→ BM-03 ─→ BM-05
       │
       ├─→ CM-04 ──→ SM-03 ─→ BM-04
       │
       └─→ CM-05 ──→ SM-04

FM-03 ─→ BM-02, BM-06

FM-04 ─→ 所有业务模块
```

---

## 下一步行动

### 高优先级
1. **修复测试失败** — 部分API和客户端测试因mock/依赖问题失败（见测试报告）
2. **前端构建验证** — npm run build 确认无编译错误
3. **系统集成测试** — AI助手端到端联动测试

### 中优先级
4. **TASK_PLAN.md 更新** — 本文档已同步最新状态
5. **Docker 部署完善** — docker-compose 优化
6. **API 文档** — OpenAPI/swagger 补充

### 低优先级
7. **systemd 服务化** — LLM服务注册为系统服务
8. **性能优化** — LLM推理加速, 缓存策略
