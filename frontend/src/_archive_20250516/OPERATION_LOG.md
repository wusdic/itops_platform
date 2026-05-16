# 归档操作日志
**操作时间**: 2025-05-16 20:xx
**操作人**: hermes agent
**原因**: 清理未使用的死代码文件，缩小项目体积，便于后续维护

---

## 归档文件清单（共11个文件）

### components/ 目录（8个组件，从未在任何页面中使用）

| 文件 | 原因 | 备注 |
|------|------|------|
| `components/AdvancedTable.vue` | 创建后从未被 import | 引入了 EmptyState 但本身无引用方 |
| `components/DataTable.vue` | 创建后从未被 import | - |
| `components/PageCard.vue` | 创建后从未被 import | - |
| `components/ChartCard.vue` | 创建后从未被 import | - |
| `components/LoadingSpinner.vue` | 创建后从未被 import | - |
| `components/FilterBar.vue` | 创建后从未被 import | - |
| `components/StatCard.vue` | 创建后从未被 import | - |
| `components/PageHeader.vue` | 创建后从未被 import | - |

### utils/ 目录（2个工具文件，从未在任何代码中使用）

| 文件 | 原因 | 备注 |
|------|------|------|
| `utils/validate.js` | 定义了 validateIP/validatePort/validateEmail 等工具函数，但无任何文件引用 | 工具函数本身是正确的，只是当前未用到 |
| `utils/index.js` | 空文件（无任何内容） | - |

### api/ 目录（1个备份文件）

| 文件 | 原因 | 备注 |
|------|------|------|
| `api_scheduler.js.bak` | scheduler.js 的完整备份，包含了被删除的 `reports` 死导出（41行） | 归档备份，非生产代码 |

---

## 代码修改记录（同步清理）

### 1. `api/scheduler.js` — 移除死导出 `reports`
- **删除内容**: 第17-41行，`export const reports = { ... }` 共25行
- **保留内容**: `scheduler` 巡检任务相关API（第1-15行）
- **删除原因**: `reports` 导出的所有方法（getList/getById/create/update/delete/download/getTemplates/createTemplate/...）从未被任何页面调用

### 2. `api/index.js` — 移除 `reports` 导入和导出
- **修改1**: 第5行 `import { scheduler, reports } from './scheduler'` → `import { scheduler } from './scheduler'`
- **修改2**: 第110行 `export { ..., reports, notification }` → `export { ..., notification }`

---

## 恢复方法

如需恢复任何文件，从归档目录直接 mv 回原位即可。

```bash
# 恢复单个组件
mv _archive_20250516/components/AdvancedTable.vue components/

# 恢复 validate.js
mv _archive_20250516/validate.js utils/

# 恢复 scheduler.js 完整版（含 reports）
mv _archive_20250516/api_scheduler.js.bak api/scheduler.js
# 然后手动恢复 index.js 中的 reports 导入/导出
```

---

## 保留的有效文件状态

### components/ (当前6个)
- `EmptyState.vue` — 被 AdvancedTable 引用（但 AdvancedTable 已归档）
- `illustrations/` — 5个 SVG 插图文件

### api/ (当前6个)
- `request.js` — 核心HTTP封装，被所有模块引用
- `index.js` — barrel导出
- `monitoring.js` — devices/alerts/performance
- `system.js` — auth/user/role/menu/dict/config/system
- `scheduler.js` — 巡检任务（移除reports后）
- `notification.js` — 通知
- `assets.js` — 资产管理（已导出但页面未接入，属待接入状态）

### utils/ (当前2个)
- `date.js` — 被13个文件引用 ✅
- `status.js` — 被 devices.vue/dashboard/index.vue 引用 ✅
