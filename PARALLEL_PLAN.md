# ITOps Platform 并行开发计划

## 一、架构依赖分析

```
[DB Models] ←——— API Routes ————————————————————→ [Vue Frontend]
                    ↑
        ┌───────────┼───────────┐
   [Collection] [Business Logic] [LLM Client]
        ↑           ↑            ↑
   [Scanner]  [AI Core]   [Qwen3.5-9B]
```

**独立并行层（无依赖）**：
- `api/routes/` — 每个 route 独立，通过 DB model 交互
- `modules/storage/` — MySQL/TDengine/Qdrant 存储层
- `frontend/src/views/*` — 各自独立，通过 API 与后端交互

**依赖链（串行）**：
- 设备发现：后端 scanner 模块 → device API → 前端 discovery 页面
- AI 对话：后端 llm_client → ai routes → 前端 AICopilot
- 告警触发：后端 alerter → executor → 前端 alerts 页面

---

## 二、并行工作流设计

```
┌─────────────────────────────────────────────────────────────┐
│  Track 0: 架构基础设施（单次，奠定基础）                      │
│  · API 路由约定文档                                          │
│  · DB Model 扩展（统一 schema）                              │
│  · docker-compose volumes 映射                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
    ┌─────────────────────┼─────────────────────┐
    ↓                     ↓                     ↓
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Track A      │  │  Track B      │  │  Track C      │
│  前端优先     │  │  后端P0缺口   │  │  AI核心       │
│  · System修复  │  │  · 设备发现   │  │  · 对话历史   │
│  · Scheduler  │  │  · 采集精细化  │  │  · 根因分析   │
│  · 发现页面   │  │  · 通知配置   │  │  · 处置建议   │
│  · 仪表盘增强 │  │  · API Key    │  │  · RAG完善    │
└───────────────┘  └───────────────┘  └───────────────┘
                          ↓                     ↓
                    ┌─────────────┐         ┌─────────────┐
                    │  Track D    │         │  Track E    │
                    │  自动化+安全 │         │  工单+SLA   │
                    │  · 告警触发  │         │  · 草稿保存 │
                    │  · SLA计时器 │         │  · SLA升级  │
                    │  · 回滚机制  │         │  · Excel导出│
                    └─────────────┘         └─────────────┘
```

---

## 三、各 Track 详细任务

### Track A: 前端基础设施与新页面
**前置条件**：API 路由约定文档

#### A1: System.vue 构建修复（~2h）
- 路由已拆分：user/role/menu/dict/config.vue 都存在
- 只需要入口组件或路由修正
- 验证：`npm run build` 通过

#### A2: Scheduler.vue 完善（~1d）
- 当前 60%，缺少：任务执行历史、立即执行按钮
- 依赖后端：`/api/v1/scheduler/tasks` 接口

#### A3: 设备发现页面（~1d）
- 新建 `/views/discovery/index.vue`
- 依赖 Track B 后端

#### A4: 仪表盘增强（~0.5d）
- 按设备/分组查看（MON-031）
- 自定义布局（MON-032）

---

### Track B: 后端 P0 缺口 — 数据采集与配置
**前置条件**：无，可立即开始

#### B1: 设备自动发现（COL-001/002）~3d
```
modules/collection/discovery/
├── __init__.py
├── scanner.py          # IP段扫描
├── snmp_scanner.py     # SNMP扫描
├── host.py             # DiscoveredHost model
└── scheduler.py        # 定时增量发现
```
**接口约定**：
- `POST /api/v1/discovery/scan` → `{ip_range, snmp_enabled}`
- `GET /api/v1/discovery/hosts` → `List[DiscoveredHost]`
- `POST /api/v1/discovery/import` → `{host_ids}`

#### B2: 采集项精细化开关（CFG-013）~1d
```
modules/collection/device_manager.py  # 新增 per-metric enable
modules/foundation/db_models/monitoring.py  # DeviceMetricConfig
```
**接口约定**：
- `GET /api/v1/devices/{id}/metrics` → `List[MetricConfig]`
- `PATCH /api/v1/devices/{id}/metrics/{metric}` → `{enabled, interval}`

#### B3: 通知对象配置（CFG-026）~2d
```
modules/business/notification/target_config.py  # 新文件
modules/foundation/db_models/notification.py  # NotificationTargetRule
api/routes/notification.py  # 新增 /targets 路由
```
**接口约定**：
- `GET /api/v1/notifications/targets` → `List[TargetRule]`
- `POST /api/v1/notifications/targets` → `TargetRule`
- `DELETE /api/v1/notifications/targets/{id}`

#### B4: API Key 认证（SYS-012）~1d
```
modules/foundation/db_models/system.py  # APIKey model
api/dependencies.py  # 实现 verify_api_key()
api/routes/admin.py  # 新增 /api-keys CRUD
```

---

### Track C: AI 核心 — 让 AI 真正辅助运维
**前置条件**：LLM 服务已在 `localhost:11435` 运行

#### C1: 对话历史持久化（AI-003）~1d
```
modules/business/ai_copilot/conversation_store.py  # 新文件
modules/foundation/db_models/ai.py  # Conversation, Message models
api/routes/ai.py  # 新增 /conversations CRUD
```
**接口约定**：
- `GET /api/v1/ai/conversations` → `List[ConversationSummary]`
- `GET /api/v1/ai/conversations/{id}/messages` → `List[Message]`
- `DELETE /api/v1/ai/conversations/{id}`

#### C2: 告警根因分析（AI-010）~3d
```
modules/business/ai_copilot/root_cause.py  # 新文件
modules/business/ai_copilot/knowledge_graph.py  # 故障传播图
```
**接口约定**：
- `POST /api/v1/ai/analyze/{alert_id}/root-cause` → `{root_cause, confidence, evidence}`

#### C3: 处置建议生成（AI-011）~2d
```
modules/business/ai_copilot/remediation.py  # 新文件
modules/business/knowledge_base/sop_matcher.py  # SOP 匹配
```
**接口约定**：
- `POST /api/v1/ai/analyze/{alert_id}/remediation` → `{steps, risk, estimated_time}`

#### C4: 告警智能分析场景编排 ~1d
```
modules/business/ai_copilot/scenarios.py  # 实现 NotImplementedError 部分
```
统一根因分析 + 处置建议的编排逻辑

---

### Track D: 自动化与 SLA
#### D1: 告警触发自动执行（AUTO-020）~2d
```
modules/automation/alert_trigger/
├── __init__.py
├── trigger.py        # AlertActionBinding
├── executor.py       # 执行器
└── models.py         # AlertTriggerRule, AlertAction
api/routes/automation.py  # 新增 /trigger-rules
```

#### D2: SLA 实时计时器 + 超时升级（WKO-021/022）~1.5d
```
modules/business/workorder/sla_manager.py  # 新文件
modules/business/workorder/workorder.py  # 集成
api/routes/workorder.py  # 新增 /workorders/{id}/sla
```

#### D3: 工单草稿保存（WKO-008）~0.5d
```
api/routes/workorder.py  # 新增 PUT /workorders/{id}/draft
```

#### D4: 执行失败自动回滚（AUTO-023）~2d
```
modules/automation/script_executor/rollback.py  # 新文件
modules/automation/script_executor/executor.py  # 集成
```

---

### Track E: 工单增强与导出
#### E1: 工单 Excel 导出（WKO-033）~0.5d
```
modules/business/report_generator/excel_exporter.py  # 新文件
api/routes/report.py  # 新增 /workorders/export
```

#### E2: 文档多级审核（KNO-005）~1.5d
```
modules/business/knowledge_base/review_flow.py  # 新文件
modules/foundation/db_models/knowledge.py  # DocumentReviewFlow
api/routes/knowledge.py  # 新增 review 相关路由
```

---

## 四、接口契约文档（各 Track 必须遵循）

### 统一响应格式
```python
# 成功
{"data": ..., "code": 0, "message": "success"}
# 错误
{"data": null, "code": <error_code>, "message": "..."}
```

### 关键 API 路由约定

| 路由 | 方法 | Track | 输入 | 输出 |
|------|------|-------|------|------|
| `/api/v1/discovery/scan` | POST | B1 | `{ip_range, snmp_enabled}` | `{task_id}` |
| `/api/v1/discovery/hosts` | GET | B1 | `?task_id=` | `List[Host]` |
| `/api/v1/discovery/import` | POST | B1 | `{host_ids}` | `{imported}` |
| `/api/v1/devices/{id}/metrics` | GET/PATCH | B2 | - | `List[MetricConfig]` |
| `/api/v1/notifications/targets` | GET/POST/DELETE | B3 | TargetRule | `List[TargetRule]` |
| `/api/v1/admin/api-keys` | GET/POST/DELETE | B4 | APIKey | `List[APIKey]` |
| `/api/v1/ai/conversations` | GET/DELETE | C1 | `?user_id=` | `List[ConvSummary]` |
| `/api/v1/ai/conversations/{id}/messages` | GET | C1 | - | `List[Message]` |
| `/api/v1/ai/analyze/{alert_id}/root-cause` | POST | C2 | - | `{root_cause, evidence}` |
| `/api/v1/ai/analyze/{alert_id}/remediation` | POST | C3 | - | `{steps, risk}` |
| `/api/v1/automation/trigger-rules` | GET/POST/DELETE | D1 | TriggerRule | `List[TriggerRule]` |
| `/api/v1/workorders/{id}/sla` | GET | D2 | - | `{remaining, deadline}` |
| `/api/v1/workorders/{id}/draft` | PUT | D3 | WorkOrderDraft | WorkOrder |
| `/api/v1/workorders/export` | GET | E1 | `?format=excel` | file |

---

## 五、执行策略

### 阶段 1（第1周）：并行基础设施
- **Track A(A1)** + **Track B(B4)** + **Track C(C1)** 并行
- 产出：前端可完整构建、API Key 可用、对话历史可持久化

### 阶段 2（第2-3周）：核心功能
- **Track B(B1/B2)** + **Track C(C2/C3)** + **Track D(D1)** 并行
- 产出：设备可自动发现、AI 真正能分析告警、告警可触发自动修复

### 阶段 3（第4周）：完善
- **Track A(A3/A4)** + **Track D(D2/D3)** + **Track E(E1/E2)** 并行
- 产出：完整的前端页面、SLA 完整、工单可导出

---

## 六、并发约束

1. **DB Model 变更**需要先完成，其他 Track 才能引用
2. **docker-compose.yml** 挂载 `./api` 和 `./modules`，无需重建镜像
3. **前端 API 调用**约定由 Track A 维护，其他 Track 不得修改 `frontend/src/api/` 外的代码
4. **每个新模块**必须包含单元测试（`tests/unit/test_<module>.py`）
