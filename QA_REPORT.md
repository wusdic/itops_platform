# iTOPS Platform 体验走查报告

**日期**: 2026-05-16
**审计视角**: 运维新人第一天上班体验
**严重程度等级**: P0(致命) > P1(严重) > P2(一般) > P3(提示)

---

## 目录
1. [工单管理流程](#1-工单管理流程)
2. [设备监控流程](#2-设备监控流程)
3. [知识库流程](#3-知识库流程)
4. [AI助手流程](#4-ai助手流程)
5. [自动化脚本流程](#5-自动化脚本流程)
6. [通用/其他问题](#6-通用其他问题)

---

## 1. 工单管理流程

### 链路: 工单列表 → 创建工单 → 分配处理人

**前端调用链**:
- `workorder/list.vue` → `workorder.getList()` → `GET /api/v1/workorders/`
- `workorder/create.vue` → `workorder.create()` → `POST /api/v1/workorders/`
- `workorder/list.vue` → `workorder.assign()` → `POST /api/v1/workorders/:id/assign`

**后端路由**: `api/routes/workorder.py` → 挂载在 `/api/v1/workorders`

#### ❌ P0: `assign` 分配接口不存在

**问题**: 前端调用 `workorder.assign(id, data)` → `POST /api/v1/workorders/:id/assign`，但 `workorder.py` 中**没有**定义 `/assign` 端点。

**现象**: 点击"分配"按钮后端返回 404，前端显示"分配失败"，无明确错误提示。

**定位**: `api/routes/workorder.py` 中搜索不到 `assign` 路由。WorkOrderCore 类中也没有 assign 方法。

#### ⚠️ P1: `order_no` 字段后端未返回，前端列表显示空白

**问题**: 工单列表表格第一列显示工单号 `order_no`，但 `_workorder_to_dict()` 返回的字典中没有 `order_no` 键（虽然模型有该字段）。

**对比**:
- 后端 `_workorder_to_dict()` 返回: `{id, order_no, ...}` ✅ 包含
- 但前端 `list.vue` 显示 `order_no` 列，**实际表格有数据但列宽 160px 空白**
- 原因：后端数据库中该字段可能为 NULL，但前端期望显示工单号

#### ⚠️ P1: 创建工单时 assignee 空字符串问题

**问题**: `create.vue` 的 form.assignee 初始值为 `''`（空字符串），当用户未选择处理人时，后端收到 `"assignee": ""`，而 WorkOrderCreate 模型期望 `Optional[str]`，空字符串可能被当作有效值处理。

**现象**: 未选处理人的工单，后端显示 assignee 为空，但前端"分配"操作会触发 404。

#### ⚠️ P2: 工单状态值不完整

**问题**: 后端 WorkOrderStatus 枚举有 8 种状态（pending, processing, pending_approval, approved, rejected, resolved, closed, cancelled），但前端 `list.vue` 只支持 4 种筛选（pending, processing, completed, closed）。

**影响**: 筛选"处理中"状态的工单时，`processing` 可以正常筛选，但 resolved（已解决）状态没有对应的筛选选项，用户无法在列表中快速找到已解决但未关闭的工单。

---

## 2. 设备监控流程

### 链路: 设备列表 → 添加设备 → 查看详情 → 采集指标

**前端调用链**:
- `monitoring/devices.vue` → `devices.getList()` → `GET /api/v1/assets/device`
- `devices.vue` → `devices.create()` → `POST /api/v1/assets/device`
- `devices.vue` → `devices.delete(row.name)` → `DELETE /api/v1/assets/device/:id`
- `devices.vue` → `devices.collect()` → `POST /api/v1/devices/collect`

**后端路由**: 
- 资产设备: `api/routes/asset.py` → `/api/v1/assets`
- 监控设备: `api/routes/device_api.py` → `/api/v1/devices`

#### ❌ P0: 删除设备传错参数

**代码** (`devices.vue` 第 478 行):
```javascript
await devices.delete(row.name)  // ❌ 传入 name
```
但 `api/routes/asset.py` 的删除接口定义为:
```python
@router.delete("/device/{device_id}")  # 期望 id (int)
```
**现象**: `delete("server-01")` 会被当作 `device_id=0`（类型转换失败），后端 404。

#### ❌ P0: 设备编辑时 id 设置错误

**代码** (`devices.vue` 第 436 行):
```javascript
Object.assign(deviceForm, {
  id: row.name,  // ❌ 把 name 当作 id
  name: row.name,
  ...
})
```
`deviceForm.id = row.name` 会导致更新时用字符串作为设备 ID，后端期望整数。

#### ⚠️ P1: 设备列表 API 与监控采集 API 混淆

**问题**: 前端 `monitoring.js` 的 `devices` 对象同时调用两套后端:
- `/assets/device` (资产设备, asset.py) - 获取设备列表
- `/devices/collect` (监控设备, device_api.py) - 采集指标

两套系统的设备标识不同（资产用 id/hostname，监控用 device_name），导致：
- 添加的设备在"设备监控"页面可能看不到（如果只写入了资产表）
- 采集指标时用 hostname 查询可能找不到设备

#### ⚠️ P1: 设备筛选字段缺失

**问题**: `devices.vue` 筛选栏有 `filterVendor`（厂商筛选），但 API 调用时传的是 `params.vendor`，而后端 `asset.py` 的 `/device` 接口只支持 `device_type`、`status`、`idc`、`business_id`、`keyword` 筛选，**没有 vendor 筛选参数**。

#### ⚠️ P2: 设备查看详情字段不匹配

**问题**: `viewDialogVisible` 详情弹窗显示的字段：
- `ip_address` ✅ 后端返回有
- `device_type` ✅ 有类型映射
- `status` ✅ 有
- `manufacturer` ✅ 有
- `os_type` ✅ 有
- `last_collect_time` ⚠️ 如果从未采集过会显示 "Invalid Date"

---

## 3. 知识库流程

### 链路: 知识文档列表 → 创建文档 → 提交审核 → 发布

**前端调用链**:
- `knowledge/list.vue` → `knowledge.getSopList()` → `GET /api/v1/knowledge/sop`
- `knowledge.vue` → `knowledge.createSop()` → `POST /api/v1/knowledge/sop`
- 提交审核: `knowledge.submitSopReview()` → `POST /api/v1/knowledge/sop/:id/review`
- 审核通过: `knowledge.approveSop()` → `POST /api/v1/knowledge/sop/:id/approve`

#### ⚠️ P1: 知识库列表 API 响应字段缺失

**问题**: 后端 `_sop_to_dict()` 返回完整字段，但前端列表可能只显示部分字段。

**对比**:
- 后端返回: `{id, doc_no, title, content, category_id, tags: [], version, status, author, reviewer, approver, review_status, effective_date, view_count, like_count, created_at, updated_at}`
- 前端期望: `{id, title, content, category_id, tags, ...}`

如果 `created_at` 格式不对，前端的 `formatTime` 会显示 "Invalid Date"。

#### ⚠️ P2: 审核流程无反馈提示

**问题**: 提交审核和审核通过操作没有明确的成功/失败提示。`submit_sop_review` 和 `approve_sop_document` 接口成功后只返回 `{"status": "success", "message": "..."}`，前端没有 `ElMessage` 提示用户。

---

## 4. AI助手流程

### 链路: 智能问答 → 发送消息 → 查看历史记录 → 多轮对话

**前端调用链**:
- `ai/copilot.vue` → `fetch('/api/v1/ai/chat', ...)` → 流式 POST
- `ai/copilot.vue` → `fetch('/api/v1/ai/conversations', ...)` → 获取历史
- `ai/copilot.vue` → `fetch('/api/v1/ai/conversation/${id}', ...)` → 获取详情

#### ⚠️ P1: 对话历史记录接口返回格式不匹配

**问题**: `copilot.vue` 的 `loadConversations` 直接用 fetch，期望响应格式:
```javascript
const data = await res.json()
conversations.value = data.items || []
```

**后端实际返回** (`ai.py` 第 491-502 行):
```python
return {
    "items": [...],
    "total": total,
    # 可能缺少 total 字段
}
```
后端在 `get_conversations` 中返回了 `total`，但 `items` 里面的对象结构是否与前端期望的一致？前端期望: `{id, title}`，后端返回: `{conversation_id, title, summary, ...}` — **id 字段名不匹配！**

#### ⚠️ P1: AI 服务不可用时无感知

**问题**: `ai.py` 的 `chat` 接口在 LLM 不可用时会降级返回:
```python
return {
    "conversation_id": conversation_id,
    "message": "AI服务暂不可用，请检查LLM服务是否启动。",
    "suggestions": [...],
    "metadata": {"mode": "llm_unavailable"}
}
```
前端收到后只显示 AI 的回复消息为"AI服务暂不可用..."，但**没有明显的告警提示**用户 AI 实际未生效。用户可能以为 AI 在思考。

#### ⚠️ P2: 流式响应解析错误静默失败

**问题**: `copilot.vue` 第 133-148 行解析 SSE 数据:
```javascript
const lines = chunk.split('\n')
for (const line of lines) {
  if (line.startsWith('data: ')) {
    try {
      const data = JSON.parse(line.slice(6))
      // ...
    } catch (e) { /* 忽略解析错误 */ }
  }
}
```
如果后端返回的 JSON 格式不对（如 `{type: 'content', content}` 但某处多了换行），错误被静默忽略，AI 回复不完整。

---

## 5. 自动化脚本流程

### 链路: 脚本管理 → 创建脚本 → 执行脚本 → 查看执行记录

**前端调用链**:
- `automation/script.vue` → localStorage (纯前端存储，无后端)
- `script.vue` 执行: `fetch('/api/automation/script/execute', ...)`
- `automation/execute.vue` → `automation.getRollbackHistory()` → `GET /api/v1/automation/rollback-history`

#### ❌ P0: 脚本执行接口 404

**问题**: `script.vue` 第 289 行:
```javascript
const res = await fetch('/api/automation/script/execute', {...})
```
但 `automation.py`（`api/routes/automation.py`）挂载在 `/api/v1/automation`，其路由定义中没有 `/script/execute`。

**实际可能存在的端点**: 搜索 `automation.py` 发现只有 `trigger-rules`、`trigger-events`、`evaluate`，**没有脚本执行相关路由**。

#### ⚠️ P1: 脚本管理纯前端 localStorage，无后端同步

**问题**: `script.vue` 的脚本数据完全存储在 localStorage 中:
```javascript
const getScriptsFromStorage = () => {
  const data = localStorage.getItem(STORAGE_KEY)  // 'automation_scripts'
  return data ? JSON.parse(data) : []
}
```
- 刷新页面数据会保留，但不同浏览器/用户之间数据不互通
- 无版本管理、无权限控制
- 无法与其他运维工具集成

#### ⚠️ P1: 执行记录接口 getRollbackHistory 返回值处理错误

**问题**: `execute.vue` 第 105-111 行:
```javascript
const res = await automation.getRollbackHistory().catch(() => [])
executionList.value = (Array.isArray(res) ? res : []).map(item => ({...}))
pagination.total = res.total || 0
```
`automation.getRollbackHistory()` 来自 `api/index.js` 的 `automation` 对象:
```javascript
export const automation = {
  getRollbackHistory: () => request.get('/automation/rollback-history'),
  ...
}
```
但 `automation.py` 中没有 `rollback-history` 路由定义。如果接口返回空数组，前端不会报错，但数据永远为空。

---

## 6. 通用/其他问题

#### ⚠️ P1: 用户列表接口路径硬编码

**问题**: 多个页面直接用 `fetch('/api/v1/admin/users')` 而不是使用封装好的 `user.getList()`：
- `workorder/list.vue` 第 142 行
- `workorder/create.vue` 第 101 行

如果 admin 路由路径变了，所有调用都要改。

#### ⚠️ P2: 消息通知 badge 硬编码为 3

**问题**: `App.vue` 第 128 行:
```html
<el-badge :value="3" :max="99" class="navbar-item">
```
badge 值硬编码为 3，应该调用通知接口获取未读消息数。

#### ⚠️ P2: 分页参数名不一致

**问题**: 
- 前端分页用: `page`, `pageSize`
- API 接收: `page`, `page_size`（下划线）
- 部分组件内部用: `pagination.page`，但传给 API 时没有统一转换

#### ⚠️ P3: 错误处理静默失败

**问题**: 多个 `.catch(() => {})` 静默吞掉错误：
```javascript
// devices.vue
const res = await devices.getList(params).catch(() => ({ items: [], total: 0 }))
// script.vue
const res = await fetch(...).catch(() => [])  // 静默失败
```
用户不知道操作失败了，也不知道为什么失败。

#### ⚠️ P3: 时间格式化显示 "Invalid Date"

**问题**: 如果后端返回的 `created_at` / `updated_at` 为 `null` 或格式不对，前端的 `formatTime` 函数会显示 "Invalid Date"：
```javascript
const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
```
如果 time 是 "2024-01-01T00:00:00" 格式应该正常，但如果是时间戳（毫秒）会出错。

---

## 问题优先级汇总

### 🔴 P0 - 致命（直接导致功能不可用）

| # | 功能 | 问题 | 文件 |
|---|------|------|------|
| 1 | 工单管理 | `assign` 分配接口 404 | frontend/src/api/index.js, api/routes/workorder.py |
| 2 | 设备监控 | 删除设备传错参数（传 name 而非 id） | frontend/src/views/monitoring/devices.vue:478 |
| 3 | 设备监控 | 编辑设备时 id 被设为 name | frontend/src/views/monitoring/devices.vue:436 |
| 4 | 自动化 | 脚本执行接口 `/api/automation/script/execute` 404 | frontend/src/views/automation/script.vue:289 |

### 🟠 P1 - 严重（功能受损或数据错误）

| # | 功能 | 问题 | 文件 |
|---|------|------|------|
| 5 | 工单管理 | 工单号 `order_no` 显示可能为空 | backend: `_workorder_to_dict` vs 前端期望 |
| 6 | 设备监控 | 资产设备与监控设备 API 混淆使用 | frontend/src/api/monitoring.js |
| 7 | 设备监控 | 厂商筛选参数 `vendor` 后端不支持 | frontend vs backend |
| 8 | AI助手 | 对话历史记录字段名不匹配 `id` vs `conversation_id` | ai.py vs copilot.vue |
| 9 | AI助手 | AI 服务不可用时无明显告警提示 | ai.py 降级模式处理 |
| 10 | 自动化 | 执行记录接口可能不存在 | api/routes/automation.py |
| 11 | 工单管理 | assignee 空字符串 vs null 处理不一致 | create.vue vs workorder.py |

### 🟡 P2 - 一般（体验问题）

| # | 功能 | 问题 | 文件 |
|---|------|------|------|
| 12 | 工单管理 | 工单状态筛选只有 4 种，后端有 8 种 | list.vue vs workorder.py |
| 13 | 知识库 | 审核操作无成功/失败提示 | knowledge.py 缺少 ElMessage |
| 14 | AI助手 | SSE 流式响应解析错误静默忽略 | copilot.vue:144-146 |
| 15 | 自动化 | 脚本数据存 localStorage 无后端同步 | script.vue:151-162 |
| 16 | 系统 | 通知 badge 硬编码为 3 | App.vue:128 |
| 17 | 系统 | 用户列表接口硬编码 fetch 路径 | list.vue, create.vue |
| 18 | 系统 | 分页参数名 `pageSize` vs `page_size` 不统一 | 多个文件 |

### 🔵 P3 - 提示（潜在问题）

| # | 功能 | 问题 | 文件 |
|---|------|------|------|
| 19 | 全局 | 多个 `.catch(() => {})` 静默吞错误 | 多个文件 |
| 20 | 全局 | 时间格式化可能显示 "Invalid Date" | 多个 formatTime 调用 |
| 21 | 设备监控 | 设备详情 `last_collect_time` 可能为 null | devices.vue |

---

## 修复建议优先级

### 第一批（P0 必须修复）

1. **工单 assign 接口**: 在 `workorder.py` 中实现 `/assign` 端点
2. **设备删除参数**: 改为传 `row.id` 而非 `row.name`
3. **设备编辑 id 错误**: 改为 `id: row.id`
4. **脚本执行接口**: 实现 `/automation/script/execute` 路由或修改前端调用正确端点

### 第二批（P1 尽快修复）

5. 统一设备管理 API（资产 vs 监控）
6. 修复厂商筛选参数支持
7. AI 对话历史记录字段名统一
8. AI 服务不可用时显示明显警告

### 第三批（P2 计划修复）

9. 补充工单状态筛选选项
10. 知识库审核操作加提示
11. 脚本管理后端化
12. 统一分页参数名
13. 统一用户列表 API 调用方式
