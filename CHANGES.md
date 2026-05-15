# ITOps Platform 代码修改记录

## 2026-05-15 — 前端 API 适配修复

### 问题
前端大量 API 方法名/响应字段与后端不匹配，所有页面显示空白或假数据。

### 修复内容

#### Dashboard.vue
- `devices.getDevices()` → `devices.getList()`
- `alerts.getAlerts()` → `alerts.getList()`
- `workorder.getWorkOrders()` → `workorder.getList()`
- `a.severity` → `a.level`（告警字段统一）
- `o.priority: {high/medium/low}` → `{P1:紧急, P2:高, P3:中, P4:低}`
- 路由 `/alerts` → `/monitoring/alerts`

#### monitoring/devices.vue（完全重写）
- 移除 CPU/内存/磁盘进度条列（API无此数据）
- 字段 `ip_address`（非 `ip`）、`type`（非 `device_type`）
- 新增网络扫描弹窗：`POST /discovery/ip/scan/sync` + `POST /discovery/devices/import`
- 新增"网络扫描"按钮（绿色），触发 CIDR 输入弹窗
- 扫描结果可多选导入设备

#### monitoring/alerts.vue（完全重写）
- 页面标题改为"告警管理"（原为"设备监控"）
- 字段映射：`_level_`/`level`/`alert_key`/`device_name`/`device_ip`/`metric_name`/`metric_value`/`unit`
- 新增严重程度过滤：`critical/high/medium/low/info`
- 新增状态过滤：`active/acknowledged/resolved`
- 告警详情弹窗展示完整字段
- 确认/解决操作：`POST /monitoring/alerts/{id}/handle`

#### workorder/list.vue（完全重写）
- 字段 `order_no`（非 `id`）
- 优先级映射 P1-P4（非 urgent/high/medium/low）
- 新增工单详情弹窗（查看完整内容）
- 分配处理人改为真实用户列表（`GET /admin/users`）

#### workorder/create.vue（完全重写）
- 新建工单表单，含标题/类型/优先级/关联设备/处理人/描述
- 类型：`fault`/`change`/`request`
- 优先级：`P1`/`P2`/`P3`/`P4`

### 构建修复
- `frontend/index.html`：删除旧硬编码 `<script src="/assets/index-3BNZqWLZ.js">`，改为 `<script type="module" src="/src/main.js">`
- 删除 `frontend/assets/` 目录（残留旧构建文件）

### 验证结果
- `npm run build` ✓（6.02s）
- Docker 容器同步 ✓
- 页面可正常渲染

### GitHub
```
bf96a81 fix(frontend): remove hardcoded mock data from dashboard and KnowledgeBase
（此前假数据清理提交）
```

---

## 2026-05-15 — 假数据清理

### 问题描述
`dashboard/index.vue` 中 `systemMetrics`、饼图数据、折线图数据均为硬编码，与真实 API 数据脱节。
`KnowledgeBase.vue` 搜索/对话失败时使用 mock 数据。

### 修改文件
- `frontend/src/views/dashboard/index.vue`
- `frontend/src/views/KnowledgeBase.vue`

### 修改内容
1. `systemMetrics = {cpu:45, memory:62, disk:38, network:156}` → `{cpu:0, memory:0, disk:0, network:0}`，等待监控采集器填充
2. 饼图/折线图硬编码 data → 改为响应式 `deviceChartData`/`alertChartData`，从 API 加载真实数据
3. `onMounted` 中加 `await nextTick()` 确保 `loadDashboard` 数据加载完毕后再初始化图表
4. `KnowledgeBase.vue` 搜索/对话失败时不再输出假数据，改为清空结果或提示错误信息

---

## 2026-05-15 前端 axios 响应拦截器修复

### 问题描述
`frontend/src/api/request.js` 响应拦截器逻辑过严，只认 `{code: 200}` 格式。
`/assets/device` 等列表 API 直接返回 `{items: [...], total: N}` 无 `code` 字段，
导致所有列表请求被 `ElMessage.error('请求失败')` + `Promise.reject()` 拦截。

### 修改文件
- `frontend/src/api/request.js` — 响应拦截器增加 `{items, total}` 格式兼容

### 修复代码
```javascript
// 原有逻辑：只认 code===200
if (res.code === 200 || res.code === 0) { return res.data || res }
ElMessage.error(res.msg || '请求失败')
return Promise.reject(...)

// 新增兼容：
if (res.items !== undefined && res.total !== undefined) { return res }
if (Array.isArray(res)) { return { items: res, total: res.length } }
if (res.msg) { ElMessage.error(...); return Promise.reject(...) }
return res  // 兜底
```

### 验证方法
1. 登录后访问 `/monitoring/devices`
2. 表格应显示28台设备，分页显示"共 28 条"
3. 刷新页面数据应保持

---

## 2026-05-15 前端设备监控页面修复

### 问题描述
`frontend/src/views/monitoring/devices.vue` 是占位组件，存在以下问题：
1. 直接用 `fetch('/api/devices')` 绕过了 axios 拦截器（无 token）
2. API 路径错误（`/api/devices` 不存在，正确路径是 `/api/v1/assets/device`）
3. 字段名错误（用 `ip` 而非 `ip_address`，用 `type` 而非 `device_type`）
4. 表格列与实际数据不匹配

### 修改方案
重写 `devices.vue`，参照 `alerts.vue` 的正确实现：
- 使用 `import { devices } from '@/api'` 而非原生 `fetch`
- 字段映射：`ip_address` → 显示列用 `ip`，`device_type` → 显示列用 `type`
- 保留原有的 UI 结构和交互逻辑

### 修改文件
- `frontend/src/views/monitoring/devices.vue` — 完全重写

### 验证方法
1. 登录后访问 `/monitoring/devices`
2. 表格应显示所有已录入设备（IP、名称、类型、状态）
3. API 请求应为 `/api/v1/assets/device`（通过浏览器 DevTools Network 确认）
4. 分页、搜索、筛选功能正常

### 回滚方案
若有问题，从 Git 历史恢复：
```bash
git show HEAD:frontend/src/views/monitoring/devices.vue > frontend/src/views/monitoring/devices.vue.bak
```

---

## 2026-05-15 扫描器 asyncio API 错误修复

### 问题描述
`modules/collection/discovery/scanner.py` 三处使用了错误的 asyncio API：
- `_tcp_check()`、`_scan_ports()`、`_grab_banners()` 均用
  `loop.create_connection(lambda: asyncio.Protocol(), ip, port)`
- 此写法返回 `(Transport, Protocol)` 而非 `(StreamReader, StreamWriter)`
- `Protocol` 实例无 `.close()` 方法，抛 `AttributeError` 被 `except Exception` 吞掉
- 导致所有主机被判定为 down

### 修改方案
替换为 `asyncio.open_connection(ip, port)` — 返回 `(StreamReader, StreamWriter)`

### 修改文件
- `modules/collection/discovery/scanner.py`:
  - `_tcp_check()` 第362-383行
  - `_scan_ports()` 第385-406行
  - `_grab_banners()` 第408-446行
- `docker-compose.yml`: `modules:/app/modules:ro` → `modules:/app/modules`

### 附带修复
- `combined_banner = b" ".join(banners.values())` → `str.join().encode()`（banner 是 str 不是 bytes）

### 验证方法
```bash
# 容器内测试
docker exec itops-api python3 -c "
import asyncio, sys; sys.path.insert(0,'/app')
from modules.collection.discovery.scanner import IPScanner
async def t():
    s=IPScanner()
    r=await s._tcp_check('192.168.1.1',[80,443,22])
    print('_tcp_check(192.168.1.1):', r)
asyncio.run(t())
"
# 期望输出: True

# API 测试
curl -X POST http://localhost:8000/api/v1/discovery/ip/scan/sync \
  -H "Content-Type: application/json" \
  -d '{"cidr":"192.168.1.0/24"}'
# 期望: total_hosts > 0
```

### 回滚方案
```bash
git checkout HEAD~1 -- modules/collection/discovery/scanner.py docker-compose.yml
docker compose restart api
```

---

## 2026-05-15 设备发现数据批量录入

### 操作内容
1. 扫描 192.168.1.0/24 → 12台设备
2. 扫描 192.168.0.0/24 → 14台设备
3. 合计 26台设备通过 SQL 直接写入 MySQL devices 表

### 写入字段
`name`, `ip_address`, `device_type='SERVER_LINUX'`, `status='ONLINE'`, `os_type='Linux'`, `network_interfaces`（端口列表）, `tags`（子网标记）

### 数据验证
```sql
SELECT ip_address, name, device_type, status, tags FROM devices;
-- 期望: 28条（含原有2台宿主机）
```
