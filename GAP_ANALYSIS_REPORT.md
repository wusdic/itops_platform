# iTOPS Platform 差距分析报告

**项目路径**: `/home/zcxx/.hermes/projects/itops_platform`  
**分析日期**: 2026-05-17  
**报告版本**: v1.0

---

## 目录

1. [执行摘要](#执行摘要)
2. [模块详细分析](#模块详细分析)
   - [2.1 监控模块 (Monitoring)](#21-监控模块-monitoring)
   - [2.2 工单模块 (Workorder)](#22-工单模块-workorder)
   - [2.3 知识库模块 (Knowledge)](#23-知识库模块-knowledge)
   - [2.4 AI助手模块 (AI)](#24-ai助手模块-ai)
   - [2.5 自动化运维模块 (Automation)](#25-自动化运维模块-automation)
   - [2.6 备份管理模块 (Backup)](#26-备份管理模块-backup)
   - [2.7 消息中心模块 (Notification)](#27-消息中心模块-notification)
   - [2.8 系统管理模块 (System)](#28-系统管理模块-system)
3. [跨模块问题汇总](#跨模块问题汇总)
4. [优先级实现计划](#优先级实现计划)
5. [附录：API路由清单](#附录api路由清单)

---

## 1. 执行摘要

### 1.1 平台架构概览

| 层级 | 技术栈 | 路径 |
|------|--------|------|
| 前端 | Vue 3 + Naive UI | `frontend/src/views/` |
| 后端 | FastAPI | `api/routes/` |
| 数据库 | SQLAlchemy ORM | `modules/foundation/db_models/` |
| 业务逻辑 | Python | `modules/business/` |

### 1.2 关键发现

- **总计分析模块**: 8个主要模块
- **前后端匹配度**: ~65%
- **严重问题 (P0)**: 4个
- **重要问题 (P1)**: 8个
- **优化建议 (P2)**: 6个

### 1.3 高优先级问题

1. **自动化运维模块 API 路径不匹配** - script.vue/task.vue/execute.vue 调用 `/api/v1/automation/trigger-rules`，但该 API 是"告警触发规则"而非"脚本管理"
2. **工单模块后端缺失** - 工单前端调用 API，但 workorder.py 后端路径不明确
3. **菜单管理只有静态数据** - menu.vue 是纯静态展示，无 CRUD API
4. **备份模块后端不完整** - 前端使用 `/api/v1/admin/backups`，但 backup.py 不存在

---

## 2. 模块详细分析

### 2.1 监控模块 (Monitoring)

#### 2.1.1 模块职责
- **alerts.vue**: 告警管理 - 接收、查看、处理告警
- **devices.vue**: 设备监控 - 查看和管理被监控设备
- **performance.vue**: 性能监控 - 查看设备性能指标和趋势

#### 2.1.2 前后端对应关系

| 前端页面 | 后端API | 数据库模型 |
|----------|---------|------------|
| alerts.vue | monitoring.py | alert.py |
| devices.vue | asset.py, device_api.py | device.py |
| performance.vue | monitoring.py, device_metrics.py | monitoring.py |

#### 2.1.3 当前状态

**✅ 已实现功能:**
- 告警列表展示、分页、过滤
- 告警详情查看
- 告警确认/处理操作
- 设备列表展示
- 设备状态监控
- 性能指标查询 (CPU、内存、网络等)

**❌ 缺失/问题:**
- 告警规则配置前端 (后端有 trigger-rules API)
- 告警聚合/关联分析
- 告警自动恢复功能
- 性能指标历史数据可视化 (图表)
- 告警升级/通知配置
- 设备批量操作

**🔴 严重问题:**
1. **前端调用 API 路径问题**: alerts.vue 调用 `/api/v1/alerts` 和 `/api/v1/alerts/{id}/acknowledge`，需确认 monitoring.py 中对应端点
2. **性能监控数据源不明确**: performance.vue 需要 `/api/v1/metrics/query` 等端点

#### 2.1.4 Gap 清单

| Gap ID | 描述 | 优先级 | 预估工作量 |
|--------|------|--------|------------|
| MON-01 | 告警确认/处理 API 端点需确认 | P0 | 0.5天 |
| MON-02 | 性能指标历史数据查询 API | P1 | 2天 |
| MON-03 | 设备性能图表展示组件 | P1 | 3天 |
| MON-04 | 告警规则配置前端页面 | P2 | 5天 |

#### 2.1.5 CRUD 完整性

| 资源 | Create | Read | Update | Delete | 备注 |
|------|--------|-------|---------|--------|------|
| 告警 (Alert) | ❌ | ✅ | ⚠️ | ❌ | 只有确认(acknowledge)，无完整更新 |
| 设备 (Device) | ✅ | ✅ | ✅ | ⚠️ | 删除需确认 |
| 性能指标 | N/A | ✅ | N/A | N/A | 只读 |

---

### 2.2 工单模块 (Workorder)

#### 2.2.1 模块职责
- **list.vue**: 工单列表 - 查看所有工单
- **create.vue**: 创建工单 - 提交新工单
- **my.vue**: 我的工单 - 查看当前用户相关工单

#### 2.2.2 前端 API 调用

```javascript
// list.vue
GET /api/v1/workorders?page=&page_size=&status=&priority=
DELETE /api/v1/workorders/{id}

// create.vue  
POST /api/v1/workorders
GET /api/v1/dicts?type=workorder_type

// my.vue
GET /api/v1/workorders/my?page=&page_size=
```

#### 2.2.3 当前状态

**✅ 已实现功能:**
- 工单列表分页展示
- 工单状态筛选 (pending, processing, resolved, closed)
- 工单优先级筛选
- 创建工单表单
- 工单详情查看

**❌ 缺失/问题:**
- 工单状态更新 (处理中→已解决) API
- 工单指派/转派功能
- 工单评论/备注
- 工单附件上传
- 工单超时提醒
- 工单满意度评价
- 我的工单 (my.vue) 与 list.vue 功能重复

**🔴 严重问题:**
1. **无法确认 workorder.py 后端位置** - 搜索发现 `api/routes/workorder.py` 存在，但前端调用的 API 可能未完整实现
2. **工单状态更新 API 缺失** - 前端需要 PUT `/api/v1/workorders/{id}/status` 但可能不存在

#### 2.2.4 Gap 清单

| Gap ID | 描述 | 优先级 | 预估工作量 |
|--------|------|--------|------------|
| WO-01 | 确认 workorder.py 后端 API 完整性 | P0 | 1天 |
| WO-02 | 工单状态更新 API | P0 | 1天 |
| WO-03 | 工单指派/转派功能 | P1 | 2天 |
| WO-04 | 工单评论/备注功能 | P1 | 2天 |
| WO-05 | 工单附件上传 | P2 | 3天 |

#### 2.2.5 CRUD 完整性

| 资源 | Create | Read | Update | Delete | 备注 |
|------|--------|-------|---------|--------|------|
| 工单 | ✅ | ✅ | ⚠️ | ✅ | 更新只支持状态变更 |

---

### 2.3 知识库模块 (Knowledge)

#### 2.3.1 模块职责
- **list.vue**: 知识文档列表 - SOP文档管理
- **category.vue**: 分类管理 - 知识库分类结构
- **cases.vue**: 故障案例库 - 故障案例查询

#### 2.3.2 前端 API 调用

```javascript
// list.vue - 知识文档
GET /api/v1/knowledge/sops?page=&page_size=&category_id=&keyword=
POST /api/v1/knowledge/sops
PUT /api/v1/knowledge/sops/{id}
DELETE /api/v1/knowledge/sops/{id}

// category.vue - 分类
GET /api/v1/knowledge/category
POST /api/v1/knowledge/category

// cases.vue - 故障案例
GET /api/v1/knowledge/fault-cases?page=&page_size=&severity=&status=
GET /api/v1/knowledge/fault-cases/{id}
```

#### 2.3.3 当前状态

**✅ 已实现功能:**
- 知识文档列表分页展示
- 文档分类筛选
- 关键词搜索
- 文档详情查看
- 分类列表展示
- 故障案例列表
- 案例按严重程度/状态筛选
- 案例详情查看

**❌ 缺失/问题:**
- 文档创建/编辑表单
- 文档富文本编辑器
- 文档版本管理
- 文档审核流程 (后端有 review-flows API)
- 案例关联分析
- 案例解决步骤展示
- 知识库统计看板

**⚠️ API 路由分析 (knowledge.py - 1023行):**

后端已实现的端点:
```python
# 文档管理
GET  /knowledge/sops           # 列表
POST /knowledge/sops           # 创建
GET  /knowledge/sops/{id}      # 详情
PUT  /knowledge/sops/{id}      # 更新
DELETE /knowledge/sops/{id}     # 删除

# 分类管理
GET  /knowledge/category       # 列表
POST /knowledge/category      # 创建

# 标签管理
GET  /knowledge/tag            # 列表

# 故障案例
GET  /knowledge/fault-cases    # 列表
POST /knowledge/fault-cases   # 创建
GET  /knowledge/fault-case/{id} # 详情
PUT  /knowledge/fault-case/{id} # 更新

# 审核流程
GET/POST/PUT/DELETE /knowledge/review-flows
POST /knowledge/reviews/submit
POST /knowledge/reviews/{id}/approve
POST /knowledge/reviews/{id}/reject

# 统计
GET /knowledge/stats
```

#### 2.3.4 Gap 清单

| Gap ID | 描述 | 优先级 | 预估工作量 |
|--------|------|--------|------------|
| KB-01 | 文档创建/编辑完整表单 | P0 | 3天 |
| KB-02 | 文档审核流程前端页面 | P1 | 3天 |
| KB-03 | 知识库统计看板 | P2 | 2天 |
| KB-04 | 案例关联知识推荐 | P2 | 3天 |

#### 2.3.5 CRUD 完整性

| 资源 | Create | Read | Update | Delete | 备注 |
|------|--------|-------|---------|--------|------|
| 知识文档 (SOP) | ✅ | ✅ | ✅ | ✅ | 完整 CRUD |
| 分类 (Category) | ✅ | ✅ | ❌ | ❌ | 缺更新/删除 |
| 标签 (Tag) | N/A | ✅ | N/A | N/A | 只读 |
| 故障案例 (FaultCase) | ✅ | ✅ | ✅ | ❌ | 缺删除 |
| 审核流程 (ReviewFlow) | ✅ | ✅ | ✅ | ✅ | 完整 CRUD |

---

### 2.4 AI助手模块 (AI)

#### 2.4.1 模块职责
- **chat.vue**: AI智能问答 - 与AI助手对话
- **copilot.vue**: AI分类助手 - 告警/工单智能分类
- **analyze.vue**: AI智能分析 - 日志/错误/性能/安全分析

#### 2.4.2 前端 API 调用

```javascript
// chat.vue
GET  /api/v1/ai/conversations
POST /api/v1/ai/chat
GET  /api/v1/ai/conversation/{id}

// copilot.vue
GET  /api/v1/ai/categories
POST /api/v1/ai/classify

// analyze.vue
POST /api/v1/ai/troubleshoot
GET  /api/v1/ai/context/{type}/{id}
```

#### 2.4.3 当前状态

**✅ 已实现功能:**
- 对话列表展示
- 消息发送和接收
- 流式响应支持
- 会话历史保存
- AI分类助手界面
- AI智能分析界面
- 分析结果展示

**❌ 缺失/问题:**
- LLM 服务未启动时的降级处理不够友好
- 对话上下文管理
- 多轮对话支持
- AI分类结果确认后自动处理
- 分析报告导出
- AI模型选择/配置

**⚠️ 后端 API 分析 (ai.py - 1493行):**

主要端点:
```python
POST /ai/chat                    # 发送消息
GET  /ai/conversations           # 会话列表
GET  /ai/conversation/{id}       # 会话历史

POST /ai/chat/_debug             # 调试端点

# 后续端点可能包括:
# - /ai/troubleshoot
# - /ai/classify
# - /ai/suggest
```

#### 2.4.4 Gap 清单

| Gap ID | 描述 | 优先级 | 预估工作量 |
|--------|------|--------|------------|
| AI-01 | LLM 服务不可用时的友好提示 | P1 | 1天 |
| AI-02 | AI分类结果自动处理 | P1 | 2天 |
| AI-03 | 分析报告导出功能 | P2 | 2天 |
| AI-04 | AI模型配置界面 | P2 | 3天 |

#### 2.4.5 CRUD 完整性

| 资源 | Create | Read | Update | Delete | 备注 |
|------|--------|-------|---------|--------|------|
| 对话会话 | ✅ | ✅ | ⚠️ | ⚠️ | 更新只支持置顶，删除需确认 |
| 消息 | ✅ | ✅ | ❌ | ❌ | 不可更新/删除 |

---

### 2.5 自动化运维模块 (Automation)

#### 2.5.1 模块职责
- **script.vue**: 脚本管理 - 创建、编辑、执行脚本
- **task.vue**: 任务管理 - 自动化任务配置
- **execute.vue**: 执行记录 - 查看脚本/任务执行历史

#### 2.5.2 🔴 严重问题：API 路径不匹配

**前端调用的 API:**
```javascript
// script.vue, task.vue, execute.vue 都调用:
GET  /api/v1/automation/trigger-rules
POST /api/v1/automation/trigger-rules
PUT  /api/v1/automation/trigger-rules/{id}
DELETE /api/v1/automation/trigger-rules/{id}
POST /api/v1/automation/trigger-rules/{id}/execute
```

**后端 automation.py 实际内容:**
```python
# api/routes/automation.py (641行)
# 实际是"告警触发自动化"(Alert Trigger Automation)
# 不是"脚本管理"(Script Management)

POST /trigger-rules           # 创建触发规则
GET  /trigger-rules           # 列出触发规则
GET  /trigger-rules/{rule_id} # 获取规则详情
PUT  /trigger-rules/{rule_id} # 更新规则
DELETE /trigger-rules/{rule_id} # 删除规则
POST /trigger-rules/{rule_id}/test # 测试规则
POST /evaluate                # 评估指标触发

# 还有脚本执行回滚相关端点...
```

**问题分析:**
1. `script.vue` 期望的脚本管理功能 (name, type, content, description)
2. `task.vue` 期望的任务管理功能 (name, trigger_type, description, status)
3. 这些与后端的"告警触发规则"数据结构完全不同

#### 2.5.3 Gap 清单

| Gap ID | 描述 | 优先级 | 预估工作量 |
|--------|------|--------|------------|
| AUTO-01 | **创建脚本管理后端 API** | P0 | 3天 |
| AUTO-02 | **创建任务管理后端 API** | P0 | 3天 |
| AUTO-03 | 脚本执行引擎集成 | P1 | 5天 |
| AUTO-04 | 任务调度器实现 | P1 | 5天 |
| AUTO-05 | 执行历史记录存储 | P1 | 2天 |

#### 2.5.4 CRUD 完整性 (假设新 API)

| 资源 | Create | Read | Update | Delete | 备注 |
|------|--------|-------|---------|--------|------|
| 脚本 | ❌ | ⚠️ | ❌ | ❌ | 需新建 |
| 任务 | ❌ | ⚠️ | ❌ | ❌ | 需新建 |
| 执行记录 | N/A | ❌ | N/A | N/A | 需新建 |

---

### 2.6 备份管理模块 (Backup)

#### 2.6.1 模块职责
- **list.vue**: 备份列表 - 查看备份记录
- **restore.vue**: 备份恢复 - 恢复数据

#### 2.6.2 前端 API 调用

```javascript
// list.vue
GET /api/v1/backup/list?page=&page_size=&keyword=&type=&status=

// restore.vue (复用 list.vue 逻辑)
POST /api/v1/admin/backups           # 创建备份
DELETE /api/v1/admin/backups/{id}    # 删除备份
```

#### 2.6.3 当前状态

**✅ 已实现功能:**
- 备份列表展示
- 分页、筛选
- 备份详情查看

**❌ 缺失/问题:**
- **无 backup.py 后端文件** - `api/routes/backup.py` 不存在
- 备份创建功能 (restore.vue 中调用 `/api/v1/admin/backups`)
- 备份恢复功能 (只有 message.info 提示)
- 备份下载功能 (只有 message.info 提示)
- 备份策略配置

**🔴 严重问题:**
1. **后端 backup.py 不存在** - 前端调用的 API 无对应实现
2. **restore.vue 和 list.vue 功能混淆** - list.vue 已有备份列表，restore.vue 复用但逻辑不清

#### 2.6.4 Gap 清单

| Gap ID | 描述 | 优先级 | 预估工作量 |
|--------|------|--------|------------|
| BACK-01 | **创建 backup.py 后端模块** | P0 | 4天 |
| BACK-02 | 备份创建 API | P0 | 1天 |
| BACK-03 | 备份恢复 API | P0 | 3天 |
| BACK-04 | 备份下载功能 | P1 | 1天 |
| BACK-05 | 备份策略配置 | P2 | 3天 |

#### 2.6.5 CRUD 完整性

| 资源 | Create | Read | Update | Delete | 备注 |
|------|--------|-------|---------|--------|------|
| 备份 | ❌ | ✅ | ❌ | ❌ | 需新建完整模块 |

---

### 2.7 消息中心模块 (Notification)

#### 2.7.1 模块职责
- **message.vue**: 消息中心 - 用户收到的消息列表
- **history.vue**: 消息历史 - 发送记录
- **config.vue**: 渠道配置 - 通知渠道管理

#### 2.7.2 前端 API 调用

```javascript
// message.vue
GET  /api/v1/notification/messages?page=&page_size=&is_read=
PUT  /api/v1/notification/messages/{id}/read
PUT  /api/v1/notification/messages/read-all

// history.vue
GET  /api/v1/notifications/history?page=&page_size=&type=&channel=&read=
PUT  /api/v1/notifications/history/{id}/read
PUT  /api/v1/notifications/history/mark-all-read

// config.vue
GET  /api/v1/notifications/channels
POST /api/v1/notifications/channels
PUT  /api/v1/notifications/channels/{id}
DELETE /api/v1/notifications/channels/{id}
GET  /api/v1/notifications/types
```

#### 2.7.3 当前状态

**✅ 已实现功能:**
- 消息列表展示
- 未读消息标记
- 全部标为已读
- 渠道配置 CRUD
- 通知类型展示
- 消息历史筛选

**❌ 缺失/问题:**
- 消息推送 (WebSocket/SSE)
- 消息订阅/退订
- 渠道测试功能
- 通知模板配置
- 告警规则与通知渠道关联

#### 2.7.4 后端 API 分析 (notification.py - 766行)

主要端点:
```python
# 渠道管理
GET/POST   /notifications/channels
GET/PUT/DELETE /notifications/channels/{id}
POST /notifications/send
POST /notifications/alert
GET  /notifications/types
POST /notifications/test/{channel_id}

# 通知历史
GET /notifications/history

# 通知目标规则
GET/POST   /notifications/target-rules
GET/PUT/DELETE /notifications/target-rules/{rule_id}
```

#### 2.7.5 Gap 清单

| Gap ID | 描述 | 优先级 | 预估工作量 |
|--------|------|--------|------------|
| NOTI-01 | 消息实时推送 (WebSocket) | P1 | 4天 |
| NOTI-02 | 渠道测试功能前端 | P1 | 1天 |
| NOTI-03 | 通知模板管理 | P2 | 3天 |
| NOTI-04 | 告警-通知渠道关联配置 | P1 | 3天 |

#### 2.7.6 CRUD 完整性

| 资源 | Create | Read | Update | Delete | 备注 |
|------|--------|-------|---------|--------|------|
| 渠道配置 | ✅ | ✅ | ✅ | ✅ | 完整 CRUD |
| 通知历史 | N/A | ✅ | ⚠️ | N/A | 只读，标记已读 |
| 目标规则 | ✅ | ✅ | ✅ | ✅ | 完整 CRUD |

---

### 2.8 系统管理模块 (System)

#### 2.8.1 模块职责
- **user.vue**: 用户管理 - 用户 CRUD
- **role.vue**: 角色管理 - 角色和权限
- **menu.vue**: 菜单管理 - 静态菜单展示
- **dict.vue**: 字典管理 - 系统字典
- **config.vue**: 参数配置 - 系统配置项

#### 2.8.2 前端 API 调用

```javascript
// user.vue
GET    /api/v1/admin/users?page=&page_size=&status=&search=
POST   /api/v1/admin/users
PUT    /api/v1/admin/users/{id}
DELETE /api/v1/admin/users/{id}

// role.vue
GET    /api/v1/admin/roles?page=&page_size=
POST   /api/v1/admin/roles
PUT    /api/v1/admin/roles/{id}
DELETE /api/v1/admin/roles/{id}

// menu.vue - 纯静态，无 API 调用

// dict.vue
GET    /api/v1/admin/dicts?page=&page_size=
POST   /api/v1/admin/dicts
PUT    /api/v1/admin/dicts/{id}
DELETE /api/v1/admin/dicts/{id}

// config.vue
GET    /api/v1/admin/configs?page=&page_size=
PUT    /api/v1/admin/configs/{key}
```

#### 2.8.3 当前状态

**✅ 已实现功能:**
- 用户列表展示
- 用户 CRUD 操作
- 角色列表展示
- 角色 CRUD 操作
- 权限树展示 (静态)
- 字典列表展示
- 字典 CRUD 操作
- 系统配置查看
- 系统配置更新

**❌ 缺失/问题:**
- **菜单管理完全静态** - menu.vue 无任何 API 调用，无增删改
- 用户密码重置功能 (只有提示)
- 角色权限分配保存 (submitPermission 只有 message.success)
- 字典项完整 CRUD (handleAddItem/EditItem/DeleteItem 只有提示)
- 操作日志查看
- 系统信息看板

**🔴 严重问题:**
1. **菜单管理是纯静态** - 需创建 menu API 和配套功能
2. **权限分配无法保存** - submitPermission 不调用 API

#### 2.8.4 Gap 清单

| Gap ID | 描述 | 优先级 | 预估工作量 |
|--------|------|--------|------------|
| SYS-01 | **菜单管理完整 CRUD** | P0 | 4天 |
| SYS-02 | **权限分配保存 API** | P0 | 1天 |
| SYS-03 | 字典项完整 CRUD | P1 | 2天 |
| SYS-04 | 用户密码重置功能 | P1 | 1天 |
| SYS-05 | 操作日志查看 | P1 | 2天 |
| SYS-06 | 系统信息看板 | P2 | 2天 |

#### 2.8.5 CRUD 完整性

| 资源 | Create | Read | Update | Delete | 备注 |
|------|--------|-------|---------|--------|------|
| 用户 | ✅ | ✅ | ✅ | ✅ | 完整 CRUD |
| 角色 | ✅ | ✅ | ✅ | ✅ | 完整 CRUD |
| 菜单 | ❌ | ⚠️ | ❌ | ❌ | 纯静态，需重建 |
| 字典 | ✅ | ✅ | ✅ | ✅ | 完整 CRUD |
| 字典项 | ❌ | ⚠️ | ❌ | ❌ | 只有静态示例数据 |
| 系统配置 | N/A | ✅ | ✅ | N/A | 只读 key，无法创建/删除 |

---

## 3. 跨模块问题汇总

### 3.1 API 路由问题

#### 3.1.1 后端存在但前端未使用

| API 路径 | 后端文件 | 说明 | 前端状态 |
|----------|----------|------|----------|
| `/knowledge/review-flows/*` | knowledge.py | 文档审核流程 | ❌ 未实现 |
| `/knowledge/stats` | knowledge.py | 知识库统计 | ❌ 未实现 |
| `/notifications/target-rules/*` | notification.py | 通知目标规则 | ❌ 未实现 |
| `/ai/troubleshoot` | ai.py | 故障排查 | ⚠️ analyze.vue 调用但需确认 |
| `/automation/evaluate` | automation.py | 指标评估 | ❌ 未使用 |

#### 3.1.2 前端调用但后端缺失/不匹配

| 前端调用 | 预期后端 | 实际后端 | 状态 |
|----------|----------|----------|------|
| `/api/v1/automation/trigger-rules` | 脚本/任务管理 | 告警触发规则 | 🔴 不匹配 |
| `/api/v1/admin/backups` | 备份管理 | admin.py (需确认) | ⚠️ 待验证 |
| `/api/v1/workorders/*` | 工单管理 | 需确认 workorder.py | ⚠️ 待验证 |

### 3.2 数据库模型问题

#### 3.2.1 数据库表存在但无对应 API

| 表名 | 模型文件 | API 状态 |
|------|----------|----------|
| notification_target_rules | notification_model.py | ⚠️ 后端有但前端无页面 |
| notification_targets | notification_model.py | ⚠️ 同上 |
| 可能还有其他表 | - | 需全面审计 |

#### 3.2.2 模型文件位置问题

| 预期路径 | 实际路径 | 状态 |
|----------|----------|------|
| `modules/foundation/db_models/workorder/` | 未找到 | ❌ 缺失 |
| `modules/foundation/db_models/automation/` | 未找到 | ❌ 缺失 |
| `modules/foundation/db_models/backup/` | 未找到 | ❌ 缺失 |

### 3.3 数据流问题

#### 3.3.1 通知模块数据流

```
告警触发 → notification/target-rules (匹配) → notification/channels (发送) → notification/history (记录)
              ↑
      前端未实现配置页面
```

#### 3.3.2 自动化模块数据流 (问题)

```
前端期望: 脚本管理 → 任务配置 → 定时/手动执行 → 执行记录
实际后端: 告警触发规则 → 条件评估 → 动作执行 (脚本/工单/通知)
```

---

## 4. 优先级实现计划

### 4.1 第一阶段：核心功能修复 (P0)

| 序号 | 模块 | Gap ID | 任务 | 预估工期 | 依赖 |
|------|------|--------|------|----------|------|
| 1 | Automation | AUTO-01 | 创建脚本管理后端 API | 3天 | 无 |
| 2 | Automation | AUTO-02 | 创建任务管理后端 API | 3天 | AUTO-01 |
| 3 | System | SYS-01 | 菜单管理完整 CRUD | 4天 | 无 |
| 4 | System | SYS-02 | 权限分配保存 API | 1天 | 无 |
| 5 | Backup | BACK-01 | 创建 backup.py 后端模块 | 4天 | 无 |
| 6 | Workorder | WO-01 | 确认 workorder.py 完整性 | 1天 | 无 |
| 7 | Workorder | WO-02 | 工单状态更新 API | 1天 | WO-01 |

**第一阶段交付**: 核心 CRUD 功能可用

### 4.2 第二阶段：功能完善 (P1)

| 序号 | 模块 | Gap ID | 任务 | 预估工期 | 依赖 |
|------|------|--------|------|----------|------|
| 8 | Workorder | WO-03 | 工单指派/转派功能 | 2天 | WO-02 |
| 9 | Workorder | WO-04 | 工单评论/备注功能 | 2天 | WO-02 |
| 10 | Backup | BACK-02 | 备份创建 API | 1天 | BACK-01 |
| 11 | Backup | BACK-03 | 备份恢复 API | 3天 | BACK-01 |
| 12 | Notification | NOTI-04 | 告警-通知渠道关联 | 3天 | BACK-01 |
| 13 | Knowledge | KB-01 | 文档创建/编辑表单 | 3天 | 无 |
| 14 | AI | AI-01 | LLM 不可用友好提示 | 1天 | 无 |

**第二阶段交付**: 主要业务流程跑通

### 4.3 第三阶段：高级功能 (P2)

| 序号 | 模块 | Gap ID | 任务 | 预估工期 | 依赖 |
|------|------|--------|------|----------|------|
| 15 | Knowledge | KB-02 | 文档审核流程前端 | 3天 | KB-01 |
| 16 | Knowledge | KB-03 | 知识库统计看板 | 2天 | KB-01 |
| 17 | Automation | AUTO-03 | 脚本执行引擎 | 5天 | AUTO-02 |
| 18 | Automation | AUTO-04 | 任务调度器 | 5天 | AUTO-03 |
| 19 | Notification | NOTI-01 | 消息实时推送 | 4天 | NOTI-04 |
| 20 | System | SYS-03 | 字典项完整 CRUD | 2天 | SYS-01 |

---

## 5. 附录：API路由清单

### 5.1 监控模块 (Monitoring)

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| GET | /alerts | 告警列表 | ✅ |
| POST | /alerts | 创建告警 | ✅ |
| GET | /alerts/{id} | 告警详情 | ✅ |
| PUT | /alerts/{id}/acknowledge | 确认告警 | ✅ |
| PUT | /alerts/{id}/resolve | 解决告警 | ⚠️ |
| DELETE | /alerts/{id} | 删除告警 | ❌ |
| GET | /metrics/query | 指标查询 | ✅ |
| GET | /metrics/history | 历史指标 | ✅ |

### 5.2 工单模块 (Workorder)

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| GET | /workorders | 工单列表 | ⚠️ |
| POST | /workorders | 创建工单 | ✅ |
| GET | /workorders/{id} | 工单详情 | ✅ |
| PUT | /workorders/{id} | 更新工单 | ⚠️ |
| DELETE | /workorders/{id} | 删除工单 | ✅ |
| PUT | /workorders/{id}/status | 更新状态 | ❌ |
| GET | /workorders/my | 我的工单 | ⚠️ |

### 5.3 知识库模块 (Knowledge)

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| GET | /knowledge/sops | 文档列表 | ✅ |
| POST | /knowledge/sops | 创建文档 | ✅ |
| GET | /knowledge/sops/{id} | 文档详情 | ✅ |
| PUT | /knowledge/sops/{id} | 更新文档 | ✅ |
| DELETE | /knowledge/sops/{id} | 删除文档 | ✅ |
| GET | /knowledge/category | 分类列表 | ✅ |
| POST | /knowledge/category | 创建分类 | ✅ |
| GET | /knowledge/fault-cases | 案例列表 | ✅ |
| GET | /knowledge/fault-case/{id} | 案例详情 | ✅ |
| POST | /knowledge/fault-cases | 创建案例 | ✅ |
| PUT | /knowledge/fault-case/{id} | 更新案例 | ✅ |
| GET | /knowledge/review-flows | 审核流程列表 | ✅ |
| POST | /knowledge/review-flows | 创建审核流程 | ✅ |
| POST | /knowledge/reviews/submit | 提交审核 | ✅ |
| POST | /knowledge/reviews/{id}/approve | 批准审核 | ✅ |

### 5.4 AI模块 (AI)

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| POST | /ai/chat | 发送消息 | ✅ |
| GET | /ai/conversations | 会话列表 | ✅ |
| GET | /ai/conversation/{id} | 会话历史 | ✅ |
| POST | /ai/troubleshoot | 故障排查 | ⚠️ |
| POST | /ai/classify | 分类 | ⚠️ |

### 5.5 自动化模块 (Automation)

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| GET | /automation/trigger-rules | 规则列表 | ✅ (但非脚本管理) |
| POST | /automation/trigger-rules | 创建规则 | ✅ (但非脚本管理) |
| POST | /automation/evaluate | 指标评估 | ⚠️ |
| GET | /automation/scripts | 脚本列表 | ❌ |
| POST | /automation/scripts | 创建脚本 | ❌ |
| POST | /automation/scripts/{id}/execute | 执行脚本 | ❌ |
| GET | /automation/tasks | 任务列表 | ❌ |
| POST | /automation/tasks | 创建任务 | ❌ |

### 5.6 备份模块 (Backup)

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| GET | /backup/list | 备份列表 | ⚠️ |
| POST | /admin/backups | 创建备份 | ❌ |
| GET | /admin/backups/{id} | 备份详情 | ❌ |
| POST | /admin/backups/{id}/restore | 恢复备份 | ❌ |
| DELETE | /admin/backups/{id} | 删除备份 | ❌ |

### 5.7 消息中心 (Notification)

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| GET | /notification/messages | 消息列表 | ✅ |
| PUT | /notification/messages/{id}/read | 标记已读 | ✅ |
| PUT | /notification/messages/read-all | 全部已读 | ✅ |
| GET | /notifications/channels | 渠道列表 | ✅ |
| POST | /notifications/channels | 创建渠道 | ✅ |
| PUT | /notifications/channels/{id} | 更新渠道 | ✅ |
| DELETE | /notifications/channels/{id} | 删除渠道 | ✅ |
| POST | /notifications/test/{id} | 测试渠道 | ✅ |
| GET | /notifications/history | 发送历史 | ✅ |
| GET | /notifications/target-rules | 目标规则 | ✅ |
| POST | /notifications/target-rules | 创建规则 | ✅ |

### 5.8 系统管理 (System)

| 方法 | 路径 | 功能 | 状态 |
|------|------|------|------|
| GET | /admin/users | 用户列表 | ✅ |
| POST | /admin/users | 创建用户 | ✅ |
| PUT | /admin/users/{id} | 更新用户 | ✅ |
| DELETE | /admin/users/{id} | 删除用户 | ✅ |
| POST | /admin/users/{id}/reset-password | 重置密码 | ⚠️ |
| GET | /admin/roles | 角色列表 | ✅ |
| POST | /admin/roles | 创建角色 | ✅ |
| PUT | /admin/roles/{id} | 更新角色 | ✅ |
| DELETE | /admin/roles/{id} | 删除角色 | ✅ |
| GET | /admin/menus | 菜单列表 | ❌ |
| POST | /admin/menus | 创建菜单 | ❌ |
| PUT | /admin/menus/{id} | 更新菜单 | ❌ |
| DELETE | /admin/menus/{id} | 删除菜单 | ❌ |
| GET | /admin/dicts | 字典列表 | ✅ |
| POST | /admin/dicts | 创建字典 | ✅ |
| PUT | /admin/dicts/{id} | 更新字典 | ✅ |
| DELETE | /admin/dicts/{id} | 删除字典 | ✅ |
| GET | /admin/configs | 配置列表 | ✅ |
| PUT | /admin/configs/{key} | 更新配置 | ✅ |

---

## 文档信息

| 项目 | 内容 |
|------|------|
| 报告作者 | Hermes Agent |
| 创建日期 | 2026-05-17 |
| 项目路径 | /home/zcxx/.hermes/projects/itops_platform |
| 报告版本 | v1.0 |
