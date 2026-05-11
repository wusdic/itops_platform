# ITOps Platform 完整开发计划

**项目**: IT运维智能平台  
**制定日期**: 2026-05-12  
**目标**: 完成全部 P0+P1 缺口，开发完整前端，完整的单元+集成测试

---

## 一、总体开发策略

### 1.1 核心原则

- **前端优先**: 先建立完整的前端框架，后端 API 配合补充
- **测试驱动**: 每开发一个功能点，同步编写单元测试和集成测试
- **增量提交**: 每完成一个小模块立即提交 Git，保持可回滚
- **禁止 Mock 数据写死**: 所有测试数据通过 DB seed scripts 或工厂类生成

### 1.2 技术栈

| 层级 | 技术选型 |
|------|---------|
| 前端框架 | Vue 3 + Element Plus（若依风格） |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | MySQL 8.0 |
| 缓存 | Redis 7 |
| 时序DB | TDengine 3.2 |
| 向量DB | Qdrant 1.7 |
| 对象存储 | MinIO |
| AI | llama.cpp + Qwen3.6-27B |
| 容器 | Docker Compose |
| 测试 | pytest + pytest-asyncio + httpx |

---

## 二、开发阶段总览

```
Phase 1 (Week 1-2): 后端P0缺口 — 数据采集与安全
Phase 2 (Week 3-4): 后端P0缺口 — AI/工单/通知
Phase 3 (Week 5-6): 前端重构 — 若依风格主框架
Phase 4 (Week 7-9): 前端业务页面 — 全部14个页面
Phase 5 (Week 10-11): 测试体系 — 单元+集成测试
Phase 6 (Week 12): 联调+部署+文档
```

---

## 三、Phase 1 — 后端P0缺口：数据采集与安全（第1-2周）

### Week 1 Day 1-2: 设备自动发现（COL-001, COL-002, COL-007）

#### 任务 1.1: IP段扫描发现
```
文件: modules/collection/discovery/scanner.py (新建)
功能: 
  - scan_ip_range(cidr: str) -> List[DiscoveredHost]
  - parallel ping sweep
  - TCP banner grabbing
  - fingerprint OS detection
测试: tests/unit/test_discovery.py
```

#### 任务 1.2: SNMP网络扫描
```
文件: modules/collection/discovery/snmp_scanner.py (新建)
功能:
  - snmp_walk_network(target: str, community: str)
  - 发现 SNMP 设备并读取 sysDescr
测试: tests/unit/test_snmp_scanner.py
```

#### 任务 1.3: 增量发现调度
```
修改: modules/automation/task_scheduler/scheduler.py
新增: 定时增量发现任务
```

### Week 1 Day 3-4: WMI/WinRM + API采集增强（COL-012, COL-013, COL-014）

#### 任务 1.4: WMI采集器
```
文件: modules/collection/wmi_collector/client.py (新建)
功能:
  - WinRM HTTP/HTTPS 连接
  - WMI Query (CPU/内存/磁盘/进程)
  - CIM_ComputerSystem 等类读取
测试: tests/unit/test_wmi_collector.py
```

#### 任务 1.5: API采集增强
```
修改: modules/collection/api_collector/http_client.py
新增:
  - Zabbix API 完整对接 (get_items, get_trends, get_history)
  - Prometheus metrics 拉取
  - Kubernetes API 发现
测试: tests/unit/test_api_collector.py
```

#### 任务 1.6: 日志采集完善
```
修改: modules/collection/log_collector/file_reader.py
新增:
  - tail -F 实时跟踪
  - 多编码支持 (utf-8/gb18030)
  - 日志分割检测 (logrotate)
测试: tests/unit/test_log_collector.py
```

### Week 1 Day 5: 采集项精细化开关 + 通知对象配置（CFG-013, CFG-026）

#### 任务 1.7: 采集项单项开关
```
修改: modules/collection/device_manager.py
新增:
  - DeviceMetricConfig model (device_id, metric_name, enabled, interval, params)
  - API: PATCH /api/v1/devices/{id}/metrics/{metric}
  - 前端: 设备详情页采集项开关
测试: tests/unit/test_device_manager.py (补充)
```

#### 任务 1.8: 通知对象配置
```
文件: modules/business/notification/target_config.py (新建)
功能:
  - 告警类型 → 通知对象映射表
  - 告警级别 → 通知对象映射表
  - 设备分组 → 通知对象映射表
DB Model: NotificationTargetRule
API: /api/v1/notifications/rules
测试: tests/unit/test_notification_target.py
```

### Week 2 Day 1-2: API Key认证 + 告警审计日志（SYS-012, MON-028）

#### 任务 1.9: API Key认证
```
修改: api/dependencies.py
实现:
  - verify_api_key() -> APIKey model
  - APIKey generation (uuid + hash)
  - API Key 管理 API: /api/v1/admin/api-keys
DB Model: APIKey (key_hash, name, scopes, expires_at, created_by)
测试: tests/integration/test_auth.py
```

#### 任务 1.10: 告警审计日志
```
修改: modules/foundation/db_models/alert.py
新增: AlertAuditLog model
  - alert_id, action, operator, before_state, after_state, timestamp
API: /api/v1/monitoring/alerts/{id}/audit
测试: tests/unit/test_alert_audit.py
```

### Week 2 Day 3-4: 告警触发自动化 + 对话历史持久化（AUTO-020, AI-003）

#### 任务 1.11: 告警触发自动执行
```
文件: modules/automation/alert_trigger/trigger.py (新建)
功能:
  - AlertRule → ActionBinding (script_id / task_id)
  - 触发条件: alert_level >= X
  - 执行策略: confirm_first / auto_execute
  - 执行结果反馈到告警记录
DB Model: AlertAction, AlertTriggerRule
API: /api/v1/automation/trigger-rules
测试: tests/integration/test_alert_trigger.py
```

#### 任务 1.12: 对话历史持久化
```
修改: modules/business/ai_copilot/llm_client.py
新增:
  - ConversationHistory DB model
  - save_conversation(conv_id, messages) -> DB
  - load_conversation(conv_id) -> List[Message]
  - list_conversations(user_id) -> List[ConversationSummary]
API: /api/v1/ai/conversations (CRUD)
测试: tests/integration/test_ai_conversation.py
```

### Week 2 Day 5: 安全扫描完善 + 通知渠道测试（AUTO-005, NOT-006）

#### 任务 1.13: 安全扫描任务完善
```
修改: modules/automation/script_executor/library.py
新增:
  - nmap 端口扫描任务
  - SSL证书检查任务
  - CVE漏洞检测任务 (基于版本比对)
```

#### 任务 1.14: 通知渠道测试
```
修改: modules/business/notification/notification_service.py
新增:
  - test_channel(channel_id) -> {sent: bool, response_time: float, error: str}
API: POST /api/v1/notifications/channels/{id}/test
```

---

## 四、Phase 2 — 后端P0缺口：AI/工单/通知（第3-4周）

### Week 3 Day 1-3: AI根因分析 + 处置建议（AI-010, AI-011）

#### 任务 2.1: 告警根因分析
```
文件: modules/business/ai_copilot/root_cause.py (新建)
功能:
  - 基于知识库的故障传播图
  - 时间线分析 (同一设备关联告警)
  - 模式匹配 (历史故障案例比对)
  - LLM 综合推理 (调用本地Qwen3.6)
API: POST /api/v1/ai/analyze/{alert_id}/root-cause
测试: tests/integration/test_root_cause.py
```

#### 任务 2.2: 处置建议生成
```
文件: modules/business/ai_copilot/remediation.py (新建)
功能:
  - 基于 SOP 知识库匹配
  - 生成 Step-by-Step 处置指令
  - 风险评估 (影响范围/可回滚性)
  - 预估修复时间
API: POST /api/v1/ai/analyze/{alert_id}/remediation
测试: tests/integration/test_remediation.py
```

### Week 3 Day 4-5: 工单草稿 + SLA计时器（WKO-008, WKO-021, WKO-022）

#### 任务 2.3: 工单草稿保存
```
修改: modules/business/workorder/workorder.py
新增:
  - WorkOrder.is_draft 字段
  - 保存草稿 API: PUT /api/v1/workorders/{id}/draft
  - 自动草稿 (每5分钟)
前端: 草稿状态标签 + 自动保存提示
```

#### 任务 2.4: SLA实时计时器 + 超时升级
```
修改: modules/business/workorder/workorder.py
新增:
  - SLA deadline 计算 (响应SLA + 处理SLA)
  - 实时剩余时间查询: GET /api/v1/workorders/{id}/sla
  - 超时自动升级: 检查线程 (每分钟)
  - 升级记录到 WorkOrderFlow
测试: tests/unit/test_workorder_sla.py
```

### Week 4 Day 1-2: 工单导出Excel + 文档多级审核（KNO-005, WKO-033）

#### 任务 2.5: 工单Excel导出
```
文件: modules/business/report_generator/excel_exporter.py (新建)
功能:
  - 导出工单列表 (字段可选)
  - 导出工单详情 (含时间线)
  - 支持自定义列配置
API: GET /api/v1/workorders/export?format=excel&fields=...
测试: tests/unit/test_excel_exporter.py
```

#### 任务 2.6: 文档多级审核
```
修改: modules/business/knowledge_base/document.py
新增:
  - DocumentReviewFlow model
  - 多级审核节点 (reviewer_levels: List[ReviewLevel])
  - 审核状态: draft → pending_level1 → pending_level2 → approved/rejected
  - 审核催办 (超时提醒)
API: 
  POST /api/v1/knowledge/documents/{id}/submit-review
  POST /api/v1/knowledge/documents/{id}/approve
  POST /api/v1/knowledge/documents/{id}/reject
测试: tests/unit/test_document_review.py
```

### Week 4 Day 3-4: 数据备份恢复 + 告警完整串联（MON-028, SYS-006, AUTO-020）

#### 任务 2.7: 平台层备份恢复
```
文件: modules/business/backup/backup_manager.py (新建)
功能:
  - DB 全量备份 (mysqldump)
  - MinIO 文件备份
  - 配置备份 (config目录)
  - 备份策略: daily/weekly/monthly
  - 恢复 API: POST /api/v1/admin/backup/{id}/restore
DB Model: BackupRecord (enhanced)
测试: tests/integration/test_backup.py
```

### Week 4 Day 5: 查漏补缺

- 完善所有 P0 缺口单元测试
- 集成测试补充

---

## 五、Phase 3 — 前端重构：若依风格主框架（第5-6周）

### Week 5 Day 1-2: 脚手架 + 项目结构

#### 任务 3.1: 前端项目初始化
```
删除原有前端，重新初始化:
vue create itops-vue --preset element-plus
或手动搭建:
- Vue 3 + Vite
- Element Plus (按需引入)
- Pinia (状态管理)
- Vue Router 4
- Axios (HTTP)
- 封装 request.js (响应拦截/Token刷新)
```

#### 任务 3.2: 若依风格布局组件
```
目录: src/layout/
- Layout.vue (主布局: 侧边栏 + 顶栏 + 内容区)
- Sidebar.vue (可折叠侧边菜单)
- Topbar.vue (顶栏: 面包屑 + 用户信息 + 通知)
- TagsView.vue (多标签页)
- RightPanel.vue (右侧设置面板)
```

#### 任务 3.3: 权限系统
```
目录: src/permission.js
- 路由守卫 (权限+Token检查)
- 动态路由生成 (从后端获取权限菜单)
- 页面级权限指令 v-permission
```

### Week 5 Day 3-5: 公共组件 + 样式规范

#### 任务 3.4: 公共业务组件
```
src/components/
- Pagination.vue (分页)
- FileUpload.vue (文件上传)
- ImagePreview.vue (图片预览)
- DialogForm.vue (表格弹窗表单)
- StatusTag.vue (状态标签)
- Timeline.vue (时间线)
- CountTo.vue (数字动画)
```

#### 任务 3.5: 全局样式规范
```
src/styles/
- variables.scss (主题色/字体/间距)
- mixins.scss (常用mixin)
- element-plus.scss (覆盖Element默认样式)
- layout.scss (布局相关样式)
- transition.scss (动画过渡)
```

---

## 六、Phase 4 — 前端业务页面（第7-9周）

### Week 7 Day 1-2: 登录 + 仪表盘

#### 任务 4.1: 登录页
```
页面: src/views/login/index.vue
功能:
  - 用户名/密码登录
  - 记住登录状态
  - 登录失败错误提示
  - 动态背景
```

#### 任务 4.2: 仪表盘
```
页面: src/views/dashboard/index.vue
组件:
  - OverviewCards.vue (设备数/告警数/工单数/服务健康)
  - AlertTrendChart.vue (告警趋势图)
  - DeviceHealthPie.vue (设备健康度饼图)
  - RecentAlerts.vue (最新告警列表)
  - WorkOrderStats.vue (工单统计)
  - ServiceStatusGrid.vue (服务状态网格)
```

### Week 7 Day 3-5: 设备管理 + 设备发现

#### 任务 4.3: 设备列表页
```
页面: src/views/device/index.vue
功能:
  - 设备列表 (分页/筛选/搜索)
  - 设备状态指示 (在线/离线/告警)
  - 批量操作 (删除/分组/标签)
  - 导出
```

#### 任务 4.4: 设备详情页
```
页面: src/views/device/detail.vue
组件:
  - DeviceInfoCard.vue (基本信息)
  - MetricTogglePanel.vue (采集项开关)
  - DeviceMetricsChart.vue (指标图表)
  - DeviceAlerts.vue (关联告警)
  - DeviceWorkOrders.vue (关联工单)
```

#### 任务 4.5: 设备发现页 (新建)
```
页面: src/views/discovery/index.vue
功能:
  - IP段输入 (CIDR格式)
  - 扫描进度条
  - 发现结果表格 (IP/主机名/OS/厂商)
  - 批量添加到设备库
```

### Week 8 Day 1-2: 告警中心

#### 任务 4.6: 告警列表
```
页面: src/views/alert/index.vue
功能:
  - 实时告警列表 (WebSocket推送)
  - 多条件筛选 (级别/状态/时间/设备)
  - 告警确认/处理/转派
  - 告警屏蔽 (维护窗口配置)
  - 关联工单
```

#### 任务 4.7: 告警规则配置
```
页面: src/views/alert/rules.vue
功能:
  - 告警规则 CRUD
  - 阈值/趋势/聚合规则配置
  - 规则测试 (用历史数据模拟)
```

### Week 8 Day 3-4: 工单管理

#### 任务 4.8: 工单列表
```
页面: src/views/workorder/index.vue
功能:
  - 工单列表 (状态tab/类型tab)
  - SLA倒计时显示
  - 创建/编辑/关闭
  - 草稿自动保存
```

#### 任务 4.9: 工单详情
```
页面: src/views/workorder/detail.vue
组件:
  - WorkOrderTimeline.vue (处理时间线)
  - ApprovalFlow.vue (审批流程可视化)
  - SLAProgress.vue (SLA进度条)
  - RelatedAlerts.vue (关联告警)
  - AttachmentPanel.vue (附件)
```

### Week 8 Day 5: 知识库

#### 任务 4.10: 知识库管理
```
页面: src/views/knowledge/index.vue
功能:
  - 文档列表 (分类树+列表)
  - 富文本编辑器 (SOP编写)
  - 多级审核流程
  - 版本历史对比
  - 智能搜索 (全文+RAG)
```

### Week 9 Day 1-2: 报表 + 自动化

#### 任务 4.11: 报表中心
```
页面: src/views/report/index.vue
功能:
  - 报表模板管理
  - 报表生成 (立即/定时)
  - PDF/Excel 导出
  - 报表订阅 (邮件)
```

#### 任务 4.12: 自动化页面
```
页面: src/views/automation/task-list.vue
页面: src/views/automation/task-create.vue
页面: src/views/automation/script-library.vue
页面: src/views/automation/trigger-rules.vue
功能:
  - 任务 CRUD
  - 脚本库管理
  - 告警触发规则配置
  - 执行日志查看
```

### Week 9 Day 3-5: 通知 + 系统设置

#### 任务 4.13: 通知管理
```
页面: src/views/notification/index.vue
功能:
  - 渠道配置 (邮件/钉钉/飞书)
  - 通知对象规则配置
  - 渠道测试
  - 发送记录查询
```

#### 任务 4.14: 系统设置
```
页面: src/views/system/user.vue (用户管理)
页面: src/views/system/role.vue (角色权限)
页面: src/views/system/api-key.vue (API Key管理)
页面: src/views/system/backup.vue (备份管理)
页面: src/views/system/log.vue (操作日志)
页面: src/views/system/license.vue (License管理)
```

---

## 七、Phase 5 — 测试体系（第10-11周）

### Week 10: 单元测试重构

#### 任务 5.1: 测试数据工厂
```
目录: tests/factories/
文件:
- device_factory.py (创建设备测试数据)
- alert_factory.py (创建告警测试数据)
- workorder_factory.py (创建工单测试数据)
- user_factory.py (创建用户测试数据)
- knowledge_factory.py (创建知识文档测试数据)
所有测试必须通过 factories 生成数据，不允许硬编码。
```

#### 任务 5.2: 采集模块单元测试
```
tests/unit/collection/
- test_snmp_scanner.py
- test_wmi_collector.py
- test_log_collector.py
- test_device_discovery.py
- test_api_collector.py
```

#### 任务 5.3: 业务模块单元测试
```
tests/unit/business/
- test_workorder_sla.py
- test_workorder_flow.py
- test_notification_target.py
- test_document_review.py
- test_alert_audit.py
```

#### 任务 5.4: AI模块单元测试
```
tests/unit/ai/
- test_root_cause.py
- test_remediation.py
- test_conversation_persistence.py
```

### Week 11: 集成测试

#### 任务 5.5: API集成测试
```
tests/integration/api/
- test_device_api.py (CRUD + 发现)
- test_alert_api.py (创建→确认→处理→关闭)
- test_workorder_api.py (创建→审批→关闭完整流程)
- test_knowledge_api.py (文档CRUD + 审核)
- test_ai_api.py (对话 + RAG + 分析)
- test_notification_api.py (渠道配置 + 发送)
- test_report_api.py (生成 + 导出)
```

#### 任务 5.6: E2E业务流程测试
```
tests/e2e/
- test_device_discovery_flow.py (扫描→发现→添加→监控)
- test_alert_to_workorder_flow.py (告警→转工单→审批→解决)
- test_knowledge_publish_flow.py (编写→提交→审核→发布)
- test_automation_trigger_flow.py (配置规则→触发→执行→记录)
```

#### 任务 5.7: 安全测试
```
tests/security/
- test_auth.py (JWT/ApiKey)
- test_sql_injection.py
- test_xss.py
- test_csrf.py
- test_permission_boundary.py
```

---

## 八、Phase 6 — 联调 + 部署 + 文档（第12周）

### Week 12 Day 1-2: 前后端联调

- 对接所有 API 接口
- WebSocket 告警推送
- 文件上传下载
- SSO/LDAP 登录

### Week 12 Day 3-4: 部署验证

- Docker Compose 完整验证
- 数据迁移脚本
- 生产环境配置
- 备份恢复演练

### Week 12 Day 5: 文档

- 更新 SRS 文档
- API 接口文档 (Swagger → md)
- 部署文档
- 用户手册目录

---

## 九、已识别的重要技术决策

1. **前端架构**: Vue 3 + Element Plus 若依风格, 删除 Streamlit, 用 Vue Router 替代
2. **前端状态**: Pinia + LocalStorage (Token), 路由守卫统一鉴权
3. **后端测试数据**: 通过 pytest fixtures + factory_boy 生成, 不写死数据
4. **告警推送**: WebSocket (FastAPI websocket + Vue SockJS)
5. **前端构建**: Vite 4, 按需引入 Element Plus 组件

---

## 十、风险与依赖

| 风险 | 影响 | 缓解 |
|------|------|------|
| 前端工作量大 (6周) | 时间延期 | 拆成并行业务组 |
| AI根因分析不确定性 | 功能难达标 | 先做接口框架，算法后续迭代 |
| 测试数据工厂复杂度 | 测试不稳定 | 严格事务回滚 (每个test一个transaction) |
| 6人团队并行 | 沟通成本 | 每日站会 + Git PR review |
