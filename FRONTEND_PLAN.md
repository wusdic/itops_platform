# ITOps Platform 前端可用性完整修复规划

## 一、系统现状分析

### 1.1 页面路由与导航映射（已验证）
```
路由                          组件文件                    状态
─────────────────────────────────────────────────────────
/login                       views/login/index.vue       ✅ 登录正常
/dashboard                   views/dashboard/index.vue  ✅ 可用（从 dashboard/ 调用）
/monitoring/devices          views/monitoring/devices.vue  ⚠️ 基本可用（有重复字段 ip vs ip_address）
/monitoring/alerts           views/monitoring/alerts.vue  ❓ 待验证
/monitoring/performance      views/monitoring/performance.vue ❓ 待验证
/workorder/list              views/workorder/list.vue     ⚠️ 基本可用（handler硬编码）
/workorder/create            views/workorder/create.vue   ⚠️ 基本可用
/workorder/my                views/workorder/my.vue       ⚠️ 基本可用
/knowledge/list              views/knowledge/list.vue     ❌ 页面极少
/knowledge/category          views/knowledge/category.vue ❌ 页面极少
/ai/copilot                  views/ai/copilot.vue         ❌ 30行占位
/ai/analyze                  views/ai/analyze.vue          ❌ 30行占位
/automation/script           views/automation/script.vue   ❌ 157行，功能少
/automation/task             views/automation/task.vue     ❌ 175行，功能少
/automation/execute          views/automation/execute.vue  ❌ 171行，功能少
/backup/list                 views/backup/list.vue         ❌ 112行，功能少
/backup/restore              views/backup/restore.vue     ❌ 128行，功能少
/notification/message        views/notification/message.vue ❌ 72行，功能少
/notification/config         views/notification/config.vue ❌ 112行，功能少
/system/user                 views/system/user.vue         ⚠️ 166行，功能少
/system/role                 views/system/role.vue       ⚠️ 159行，功能少
/system/menu                 views/system/menu.vue         ❌ 141行，功能少
/system/dict                 views/system/dict.vue         ❌ 176行，功能少
/system/config               views/system/config.vue       ❌ 72行，功能少
/settings                    views/Settings.vue            ❌ 3137行，设置页巨大但没有网络扫描目标配置
```

### 1.2 核心问题清单

#### P0 - 阻断性问题（系统无法正常使用）
1. **没有配置网络扫描目标的页面** - 用户无法在界面上添加要扫描的IP段，这是最核心的功能缺失
2. **前端页面路由/后端API严重不匹配**：
   - `monitoring/devices.vue` 的 `devices.getList()` → `/assets/device` ✅ 有数据
   - `monitoring/alerts.vue` 的 `alerts.getList()` → `/monitoring/alerts` ❓ 待验证
   - `workorder/list.vue` 的 `workorder.getList()` → `/workorders/` ❓ 待验证
3. **多个页面的API端点与后端不匹配** - 导致所有数据都加载不出来

#### P1 - 严重问题（功能不可用）
4. **AI助手两个页面（copilot/analyze）只有30行占位代码** - 完全无法使用
5. **知识库页面内容极少** - list.vue只有37行，category只有168行
6. **自动化页面（脚本/任务/执行）功能简陋** - 只有表单没有实际执行逻辑
7. **备份管理页面功能简陋** - 只有表单没有实际备份逻辑

#### P2 - 一般问题（体验不佳）
8. **工单的处理人选择是硬编码的**（张三/李四/王五）而非从用户API加载
9. **设备类型枚举不一致**：
   - `monitoring/devices.vue` 用 `SERVER_LINUX`, `NETWORK_SWITCH`
   - `Devices.vue` 用 `server`, `network`
   - `Assets.vue` 用 `server`, `network`
10. **侧边栏 `/alerts` 链接指向不存在路由**（`$router.push('/alerts')` 应该是 `/monitoring/alerts`）

### 1.3 后端API现状

**已有后端路由（已验证）：**
- `GET  /api/v1/assets/device` → 返回28台设备 ✅
- `GET  /api/v1/assets/stats` → 设备统计 ✅
- `GET  /api/v1/monitoring/alerts` → 告警列表 ❓
- `GET  /api/v1/workorders/` → 工单列表 ❓
- `POST /api/v1/discovery/ip/scan/sync` → 同步IP扫描 ✅（已测试可工作）
- `GET  /api/v1/discovery/hosts` → 获取发现的主机 ❌（返回空）
- `POST /api/v1/discovery/devices/import` → 导入设备 ❓

## 二、用户核心使用流程设计

### 流程1：添加监控目标（最核心，缺失最严重）
```
用户点击「设备管理」
  → 看到已有设备列表（28台，从DB加载）✅
  → 点击「添加设备」→ 手动填写设备信息 ✅（Devices.vue）
  → 问题：没有「扫描网络」入口 ❌
  → 问题：没有「扫描结果导入」入口 ❌
```

**需要新增/修复的页面：**
- 入口位置：在「设备监控」页面增加「网络扫描」按钮
- 新页面：网络扫描配置（输入IP段，触发扫描，查看扫描结果，一键导入）

### 流程2：查看设备状态
```
用户点击「监控中心 → 设备监控」
  → 看到设备列表（IP、类型、状态、CPU、内存、磁盘）
  → 问题：monitoring/devices.vue 显示的是 CPU/内存/磁盘进度条，但后端没有这些数据
  → 需要：要么去掉这些列，要么从 device_metrics API 加载
```

### 流程3：处理告警
```
用户点击「监控中心 → 告警管理」
  → 看到告警列表
  → 点击告警查看详情
  → 问题：monitoring/alerts.vue 的API是否与后端匹配？
```

### 流程4：管理工单
```
用户点击「工单管理 → 工单列表」
  → 看到所有工单
  → 点击「创建工单」→ 填写表单
  → 问题：handler选择是硬编码的，需要从 /system/user 加载真实用户列表
```

## 三、修复执行计划

### 阶段1：核心流程打通（P0）
**目标：让用户能够完成最基本的「网络扫描→发现设备→查看设备」闭环**

#### 1.1 修复设备监控页面（/monitoring/devices）
- 确认 API `devices.getList()` 返回的数据结构
- 修复字段名不匹配（`ip` vs `ip_address`）
- 去掉不存在的指标列（CPU/内存/磁盘），或改为显示「暂无数据」
- 增加「网络扫描」按钮，打开扫描对话框

#### 1.2 创建/修复网络扫描页面（核心缺失功能）
- 在 `monitoring/devices.vue` 中增加「网络扫描」按钮
- 点击后弹出对话框，输入CIDR（如192.168.1.0/24）
- 调用 `POST /api/v1/discovery/ip/scan/sync` 发起扫描
- 显示扫描进度和结果列表
- 结果中可以勾选设备，点击「导入」将选中设备写入 DB
- 导入后刷新设备列表

#### 1.3 验证告警页面（/monitoring/alerts）
- 读取 `monitoring/alerts.vue` 的完整代码
- 确认 API 调用和数据结构
- 如果后端 `/monitoring/alerts` 没有实现，先让页面显示空数据而不是报错

#### 1.4 验证工单页面（/workorder/list）
- 确认 `workorder.getList()` 的 API 端点
- 修复 handler 选择器的硬编码问题（从 `/system/user` 加载用户列表）
- 确认 create/my 页面是否可用

### 阶段2：完善基础功能（P1）
**目标：让主要功能模块都可以显示数据，不报空白错误**

#### 2.1 知识库页面
- `knowledge/list.vue`（37行）→ 加载知识库文章列表
- `knowledge/category.vue`（168行）→ 加载分类列表
- 如果后端支持，对接 API；如果后端不支持，页面显示「功能开发中」

#### 2.2 AI助手页面
- `ai/copilot.vue`（30行）→ 调用 `POST /api/v1/ai/chat`
- `ai/analyze.vue`（30行）→ 调用 `POST /api/v1/ai/analyze/{id}/{type}`
- 如果 LLM 服务未启动，页面显示「AI服务暂不可用」

#### 2.3 自动化页面
- 对接 `automation` 相关 API
- 如果后端不支持，显示「功能开发中」

### 阶段3：细节打磨（P2）
**目标：让系统达到可用状态，无明显错误**

#### 3.1 修复侧边栏错误链接
- Dashboard.vue 中的 `$router.push('/alerts')` → `$router.push('/monitoring/alerts')`

#### 3.2 统一设备类型枚举
- 选定一套类型：`server`, `network`, `security`, `storage`
- 所有页面和后端统一使用这套枚举

#### 3.3 工单处理人动态加载
- 从 `/system/user` API 加载真实用户列表

## 四、修复优先级和分工

### 第一批（立即执行，1-2小时）
1. ✅ 修复 `monitoring/devices.vue` - 让设备列表正常显示
2. ✅ 修复 `monitoring/devices.vue` - 增加网络扫描按钮和扫描对话框
3. ✅ 修复 `Dashboard.vue` 中的错误链接
4. ✅ 验证 `monitoring/alerts.vue` 是否正常

### 第二批（后续执行，2-4小时）
5. 修复工单页面的硬编码处理人
6. 验证知识库页面并对接API
7. 修复 AI 助手页面
8. 修复自动化/备份/通知页面

## 五、技术约束

- **只改前端代码**，不修改后端
- 所有修改记录到 `CHANGES.md`
- 每次修改后构建并同步到容器：`npm run build && docker cp`
- 如果某个 API 调用失败，页面显示友好错误而不是空白
- 所有下拉选项优先从后端加载，如果后端没有则显示「暂无数据」而非硬编码

## 六、验证标准

修复完成后，用户应该能够：
1. ✅ 打开登录页 → 登录 → 进入仪表盘
2. ✅ 点击「设备监控」→ 看到真实设备列表
3. ✅ 点击「网络扫描」→ 输入IP段 → 看到扫描结果 → 导入设备
4. ✅ 点击「告警管理」→ 看到告警列表（或空列表，不报错）
5. ✅ 点击「工单列表」→ 看到工单列表 → 创建工单
6. ✅ 所有页面都能正常打开，不出现白屏或404
