# ITOps Platform 前端完整开发方案 (v3.0)

**核心目标**：让用户从头到尾能走完所有业务流程，每个页面有对应后台功能，每一步都能看到真实数据

---

## 一、完整业务逻辑流程

```
[用户注册/登录] → [仪表盘总览]
                      │
          ┌───────────┼───────────────┐
          ▼           ▼               ▼
     [资产管理]  [设备发现]      [系统管理]
     添加设备    自动扫描发现     用户/角色/配置
          │           │               │
          ▼           ▼               ▼
     [设备监控]  [设备导入]      [API密钥]
     采集指标    批量导入设备
          │           │
          ▼           ▼
     [监控告警]  [通知管理]
     规则/告警   渠道/对象/规则
          │           │
          ▼           ▼
     [自动化]    [巡检管理]
     触发/回滚   任务/报告
          │           │
          ▼           ▼
     [工单管理]  [知识库]
     创建/处理   SOP/案例
          │           │
          ▼           ▼
     [AI助手]    [报表中心]
     问答/分析   生成/定时
          │
          ▼
     [定时任务]
     调度/日志
```

---

## 二、页面清单及功能详解

### 1. 登录页 /login
**后端 API**：auth.py (4 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 显示验证码 | GET /api/v1/auth/captcha | 图形验证码 |
| 用户登录 | POST /api/v1/auth/login | 用户名+密码+验证码 |
| 记住登录 | localStorage | token 持久化 |

**业务流程**：用户输入账号密码→验证验证码→登录成功→保存 token→跳转仪表盘

---

### 2. 仪表盘 /dashboard
**后端 API**：monitoring.py + device_api.py + workorder.py + admin.py
| 功能 | API | 说明 |
|------|-----|------|
| 设备统计 | GET /api/v1/devices/stats | 总数/在线/离线 |
| 资产统计 | GET /api/v1/assets/stats | 各类型设备数 |
| 告警统计 | GET /api/v1/monitoring/alerts | 各等级告警数 |
| 工单统计 | GET /api/v1/workorder/stats/summary | 待处理/处理中 |
| 告警趋势 | GET /api/v1/monitoring/metrics | ECharts 折线图 |
| 工单趋势 | GET /api/v1/workorder/stats/trend | ECharts 柱状图 |
| 最新告警 | GET /api/v1/monitoring/alerts | 时间线展示 |
| 系统健康 | GET /api/v1/admin/health | 服务状态 |
| 系统指标 | GET /api/v1/admin/metrics | CPU/内存/磁盘 |

---

### 3. 设备管理 /assets
**后端 API**：asset.py (18 端点)
| 页面 | 功能 | API |
|------|------|-----|
| 列表 | 设备列表(搜索/筛选/分页) | GET /assets/device |
| | 创建设备 | POST /assets/device |
| | 编辑设备 | PUT /assets/device/{id} |
| | 删除设备 | DELETE /assets/device/{id} |
| | 设置维护 | POST /assets/device/{id}/maintain |
| | 退役设备 | POST /assets/device/{id}/decommission |
| 分组 | 分组列表 | GET /assets/group |
| | 分组下设备 | GET /assets/group/{id}/devices |
| 配置 | 配置项列表 | GET /assets/config |
| | 创建快照 | POST /assets/config/snapshot |
| | 更新配置 | PUT /assets/config/{id} |
| | 删除配置 | DELETE /assets/config/{id} |
| | 同步配置 | POST /assets/config/sync/{id} |
| 业务系统 | 业务系统列表 | GET /assets/business |
| | 业务系统详情 | GET /assets/business/{id} |
| | 关联设备 | GET /assets/business/{id}/devices |
| 统计 | 资产统计 | GET /assets/stats |

**业务流程**：
1. 用户进入设备管理→看到设备列表
2. 点击"新增"→填写设备信息(IP/主机名/类型/厂商/标签)→提交
3. 列表刷新→新设备出现
4. 点击设备→查看详情
5. 可以编辑/删除/设置维护/退役

---

### 4. 设备发现 /discovery
**后端 API**：discovery.py (16 端点)
| 功能 | API | 说明 |
|------|-----|------|
| IP扫描 | POST /discovery/ip/scan | 输入IP范围启动扫描 |
| 扫描结果 | GET /discovery/ip/scan/{task_id}/results | 查看发现的主机 |
| 同步扫描 | POST /discovery/ip/scan/sync | 同步执行 |
| SNMP扫描 | POST /discovery/snmp/scan | SNMP协议扫描 |
| SNMP结果 | GET /discovery/snmp/scan/{task_id}/results | 查看扫描结果 |
| SNMP发现 | POST /discovery/snmp/discover | SNMP设备发现 |
| SNMP设备 | GET /discovery/snmp/devices | SNMP设备列表 |
| 导入设备 | POST /discovery/devices/import | 导入发现的设备到资产 |
| 通用扫描 | POST /discovery/scan | 启动设备扫描 |
| 扫描状态 | GET /discovery/scan/{task_id}/status | 查看进度 |
| 发现主机 | GET /discovery/hosts | 发现的主机列表 |
| 导入主机 | POST /discovery/import | 导入主机 |
| 发现任务 | POST /discovery/tasks | 创建发现任务 |
| 任务列表 | GET /discovery/tasks | 查看所有发现任务 |

**业务流程**：
1. 用户进入设备发现→选择扫描方式(IP/SNMP)
2. 输入扫描参数(IP范围/网段/community)→启动扫描
3. 查看扫描进度→扫描完成
4. 查看发现的主机列表
5. 选择要导入的设备→点击"导入"→设备添加到资产库

---

### 5. 设备导入 /devices/import
**后端 API**：device_import.py (4 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 下载模板 | GET /devices/import/template | Excel 模板 |
| 验证数据 | POST /devices/import/validate | 验证导入数据 |
| 批量导入 | POST /devices/import | 批量导入设备 |
| 简单导入 | POST /devices/import/simple | JSON 直接导入 |

---

### 6. 设备监控 /monitoring/devices
**后端 API**：device_api.py (14 端点) + device_metrics.py (6 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 设备列表 | GET /devices | 设备列表+状态 |
| 设备统计 | GET /devices/stats | 在线/离线统计 |
| 设备详情 | GET /devices/{name} | 详情信息 |
| 设备状态 | GET /devices/{name}/status | 实时状态 |
| 采集指标 | POST /devices/collect | 单设备采集 |
| 采集全部 | POST /devices/collect/all | 全部设备采集 |
| 设备指标 | GET /devices/{name}/metrics | 指标数据 |
| 指标配置 | GET /devices/{id}/metrics/configs | 所有指标配置 |
| 更新配置 | PATCH /devices/{id}/metrics/{metric} | 单项开关 |
| 适配器 | GET /devices/adapters/list | 支持的适配器 |
| 协议 | GET /devices/adapters/protocols | 支持的协议 |
| 重载配置 | POST /devices/config/reload | 重新加载 |
| 配置统计 | GET /devices/config/stats | 配置统计 |

---

### 7. 监控告警 /monitoring/alerts
**后端 API**：monitoring.py (40 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 告警列表 | GET /monitoring/alerts | 搜索/筛选/分页 |
| 告警详情 | GET /monitoring/alerts/{id} | 详情信息 |
| 确认告警 | PUT /monitoring/alerts/{id}/acknowledge | 确认处理 |
| 解决告警 | PUT /monitoring/alerts/{id}/resolve | 标记解决 |
| 删除告警 | DELETE /monitoring/alerts/{id} | 删除 |
| 审计日志 | GET /monitoring/alerts/{id}/audit-logs | 操作记录 |
| 告警规则 | GET /monitoring/rules | 规则列表 |
| 规则详情 | GET /monitoring/rules/{id} | 规则详情 |
| 监控指标 | GET /monitoring/metrics | 指标数据 |
| 手动采集 | POST /monitoring/metrics/collect | 手动采集 |
| 监控主机 | GET /monitoring/metrics/hosts | 主机列表 |
| 可用指标 | GET /monitoring/metrics/available | 指标列表 |
| PromQL查询 | POST /monitoring/metrics/query | PromQL 查询 |
| 仪表盘 | GET /monitoring/dashboards | 仪表盘列表 |
| 仪表盘详情 | GET /monitoring/dashboards/{id} | 仪表盘配置 |
| 触发规则 | GET /monitoring/trigger-rules | 触发规则列表 |
| 创建规则 | POST /monitoring/trigger-rules | 创建规则 |
| 更新规则 | PUT /monitoring/trigger-rules/{id} | 更新规则 |
| 测试规则 | POST /monitoring/trigger-rules/{id}/test | 测试 |
| 触发事件 | GET /monitoring/trigger-events | 触发事件 |
| 指标评估 | POST /monitoring/trigger/evaluate | 评估触发条件 |
| 采集项配置 | GET /monitoring/metric-configs | 配置列表 |
| 创建配置 | POST /monitoring/metric-configs | 创建配置 |
| 更新配置 | PATCH /monitoring/metric-configs/{id} | 更新(单项开关) |
| 切换开关 | PATCH /monitoring/metric-configs/{id}/toggle | 切换 |
| 删除配置 | DELETE /monitoring/metric-configs/{id} | 删除 |
| 仪表盘布局 | GET /monitoring/dashboard/layout | 用户布局 |
| 保存布局 | PUT /monitoring/dashboard/layout | 保存布局 |
| 布局列表 | GET /monitoring/dashboard/layouts | 所有布局 |
| 删除布局 | DELETE /monitoring/dashboard/layout/{id} | 删除 |
| 布局快照 | POST /monitoring/dashboard/layout/snapshot | 创建快照 |
| 获取快照 | GET /monitoring/dashboard/layout/snapshot/{id}/{v} | 获取 |
| 列配置 | GET /monitoring/dashboard/columns | 列配置 |

---

### 8. 自动化执行 /automation
**后端 API**：automation.py (11 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 规则列表 | GET /automation/trigger-rules | 触发规则列表 |
| 创建规则 | POST /automation/trigger-rules | 创建规则 |
| 规则详情 | GET /automation/trigger-rules/{id} | 详情 |
| 更新规则 | PUT /automation/trigger-rules/{id} | 更新 |
| 删除规则 | DELETE /automation/trigger-rules/{id} | 删除 |
| 测试规则 | POST /automation/trigger-rules/{id}/test | 测试 |
| 评估指标 | POST /automation/evaluate | 评估触发 |
| 执行回滚 | POST /automation/executions/{id}/rollback | 回滚 |
| 保存检查点 | POST /automation/executions/{id}/checkpoint | 检查点 |
| 获取快照 | GET /automation/executions/{id}/snapshot | 快照 |
| 回滚历史 | GET /automation/rollback-history | 历史 |

---

### 9. 巡检管理 /inspection
**后端 API**：inspection.py (8 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 任务列表 | GET /inspection/tasks | 巡检任务 |
| 任务详情 | GET /inspection/tasks/{id} | 详情 |
| 创建任务 | POST /inspection/tasks | 创建 |
| 巡检报告 | GET /inspection/reports/{id} | 报告 |
| 导出报告 | GET /inspection/reports/{id}/export | 导出 |
| 报告模板 | GET /inspection/reports/template | 模板 |
| 结果列表 | GET /inspection/results/{id} | 结果 |
| 统计摘要 | GET /inspection/statistics/summary | 统计 |

---

### 10. 工单管理 /workorder
**后端 API**：workorder.py (33 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 工单列表 | GET /workorder/ | 搜索/筛选/分页 |
| 创建工单 | POST /workorder/ | 创建 |
| 工单详情 | GET /workorder/{id} | 详情 |
| 更新工单 | PUT /workorder/{id} | 更新 |
| 删除工单 | DELETE /workorder/{id} | 删除 |
| 保存草稿 | PUT /workorder/{id}/draft | 草稿 |
| 草稿列表 | GET /workorder/draft/list | 草稿 |
| 草稿详情 | GET /workorder/draft/{id} | 详情 |
| 删除草稿 | DELETE /workorder/draft/{id} | 删除 |
| 流程历史 | GET /workorder/{id}/flows | 历史记录 |
| 添加流程 | POST /workorder/{id}/flows | 添加记录 |
| 分配工单 | POST /workorder/{id}/assign | 分配 |
| 审批工单 | POST /workorder/{id}/approve | 审批 |
| 解决工单 | POST /workorder/{id}/resolve | 解决 |
| 关闭工单 | POST /workorder/{id}/close | 关闭 |
| 取消工单 | POST /workorder/{id}/cancel | 取消 |
| 工单分类 | GET /workorder/categories | 分类列表 |
| 工单优先级 | GET /workorder/priorities | 优先级列表 |
| 工单统计 | GET /workorder/stats/summary | 统计摘要 |
| 工单趋势 | GET /workorder/stats/trend | 趋势数据 |
| SLA状态 | GET /workorder/{id}/sla | SLA状态 |
| 刷新SLA | POST /workorder/{id}/sla/refresh | 刷新 |
| SLA历史 | GET /workorder/{id}/sla/history | 升级历史 |
| 启动SLA | POST /workorder/{id}/sla/timer/start | 启动计时 |
| AI根因分析 | POST /workorder/analyze/root-cause | AI分析 |
| AI修复建议 | POST /workorder/analyze/remediation | AI建议 |
| 导出工单 | GET /workorder/export | 批量导出 |
| 导出单个 | GET /workorder/export/{id} | 单个导出 |
| 我的工单 | GET /workorder/ | 分配给我的工单 |

**业务流程**：
1. 用户创建工单→可先保存草稿
2. 提交工单→进入待处理状态
3. 管理员分配工单→指定处理人
4. 处理人接受→开始处理
5. AI根因分析→生成处理建议
6. 处理人解决→提交解决方案
7. 审批人审批→通过/驳回
8. 关闭工单→归档

---

### 11. 知识库 /knowledge
**后端 API**：knowledge.py (30 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 知识搜索 | GET /knowledge/search | 全文搜索 |
| SOP列表 | GET /knowledge/sop | SOP文档列表 |
| 创建SOP | POST /knowledge/sop | 创建文档 |
| SOP详情 | GET /knowledge/sop/{id} | 详情 |
| 更新SOP | PUT /knowledge/sop/{id} | 更新 |
| 删除SOP | DELETE /knowledge/sop/{id} | 删除 |
| 提交审核 | POST /knowledge/sop/{id}/review | 提交 |
| 批准文档 | POST /knowledge/sop/{id}/approve | 批准 |
| 故障案例 | GET /knowledge/fault-case | 案例列表 |
| 创建案例 | POST /knowledge/fault-case | 创建 |
| 案例详情 | GET /knowledge/fault-case/{id} | 详情 |
| 更新案例 | PUT /knowledge/fault-case/{id} | 更新 |
| 分类列表 | GET /knowledge/category | 分类 |
| 创建分类 | POST /knowledge/category | 创建 |
| 标签列表 | GET /knowledge/tag | 标签 |
| 知识库统计 | GET /knowledge/stats | 统计 |
| 审核流程 | GET /knowledge/review-flows | 流程列表 |
| 创建流程 | POST /knowledge/review-flows | 创建 |
| 流程详情 | GET /knowledge/review-flows/{id} | 详情 |
| 更新流程 | PUT /knowledge/review-flows/{id} | 更新 |
| 删除流程 | DELETE /knowledge/review-flows/{id} | 删除 |
| 提交审核 | POST /knowledge/reviews/submit | 提交 |
| 审核列表 | GET /knowledge/reviews | 审核记录 |
| 待审核 | GET /knowledge/reviews/pending | 待审核列表 |
| 批准审核 | POST /knowledge/reviews/{id}/approve | 批准 |
| 拒绝审核 | POST /knowledge/reviews/{id}/reject | 拒绝 |
| 要求修订 | POST /knowledge/reviews/{id}/request-revision | 要求修订 |
| 撤回审核 | POST /knowledge/reviews/{id}/withdraw | 撤回 |
| 重新提交 | POST /knowledge/reviews/{id}/resubmit | 重新提交 |

---

### 12. AI助手 /ai
**后端 API**：ai.py (16 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 智能问答 | POST /ai/chat | 对话(流式) |
| 调试流式 | POST /ai/chat/_debug | 调试模式 |
| 会话历史 | GET /ai/conversation/{id} | 历史消息 |
| 会话列表 | GET /ai/conversations | 所有会话 |
| 删除会话 | DELETE /ai/conversation/{id} | 删除 |
| 置顶会话 | PUT /ai/conversation/{id}/pin | 置顶 |
| 保存消息 | POST /ai/conversation/{id}/messages | 保存 |
| 故障排查 | POST /ai/troubleshoot | 智能排查 |
| 自动诊断 | POST /ai/troubleshoot/auto | 自动诊断 |
| 优化建议 | POST /ai/suggest | 建议生成 |
| 报表解读 | POST /ai/interpret/report | 解读 |
| 日志分析 | POST /ai/analyze/logs | 分析 |
| 知识问答 | POST /ai/qa | RAG 问答 |
| AI统计 | GET /ai/stats | 使用统计 |
| 根因分析 | POST /ai/root-cause | 根因分析 |
| 修复建议 | POST /ai/remediation | 修复建议 |

---

### 13. 报表中心 /reports
**后端 API**：report.py (18 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 模板列表 | GET /report/template | 模板列表 |
| 模板详情 | GET /report/template/{id} | 详情 |
| 创建模板 | POST /report/template | 创建 |
| 更新模板 | PUT /report/template/{id} | 更新 |
| 删除模板 | DELETE /report/template/{id} | 删除 |
| 生成报表 | POST /report/generate | 同步生成 |
| 异步生成 | POST /report/generate/async | 异步 |
| 报表列表 | GET /report/ | 列表 |
| 报表统计 | GET /report/stats | 统计 |
| 报表详情 | GET /report/{id} | 详情 |
| 删除报表 | DELETE /report/{id} | 删除 |
| 下载报表 | GET /report/{id}/download | 下载 |
| 报表文件 | GET /report/files/{filename} | 文件 |
| 定时列表 | GET /report/schedule | 定时列表 |
| 创建定时 | POST /report/schedule | 创建定时 |
| 更新定时 | PUT /report/schedule/{id} | 更新 |
| 删除定时 | DELETE /report/schedule/{id} | 删除 |
| 启用禁用 | POST /report/schedule/{id}/toggle | 切换 |

---

### 14. 通知管理 /notifications
**后端 API**：notification.py (21 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 渠道列表 | GET /notification/channels | 所有渠道 |
| 渠道详情 | GET /notification/channels/{id} | 详情 |
| 创建渠道 | POST /notification/channels | 创建 |
| 更新渠道 | PUT /notification/channels/{id} | 更新 |
| 删除渠道 | DELETE /notification/channels/{id} | 删除 |
| 发送通知 | POST /notification/send | 发送 |
| 发送告警 | POST /notification/alert | 告警通知 |
| 通知类型 | GET /notification/types | 类型列表 |
| 测试渠道 | POST /notification/test/{id} | 测试 |
| 通知历史 | GET /notification/history | 历史记录 |
| 目标规则 | GET /notification/target-rules | 规则列表 |
| 创建规则 | POST /notification/target-rules | 创建 |
| 规则详情 | GET /notification/target-rules/{id} | 详情 |
| 更新规则 | PUT /notification/target-rules/{id} | 更新 |
| 删除规则 | DELETE /notification/target-rules/{id} | 删除 |
| 启用规则 | POST /notification/target-rules/{id}/toggle | 切换 |
| 匹配规则 | GET /notification/target-rules/match | 匹配 |
| 通知对象 | GET /notification/targets | 对象列表 |
| 创建对象 | POST /notification/targets | 创建 |
| 对象详情 | GET /notification/targets/{id} | 详情 |
| 删除对象 | DELETE /notification/targets/{id} | 删除 |

---

### 15. 系统管理 /system
**后端 API**：admin.py (38 端点) + api_keys.py (8 端点)
| 功能 | API | 说明 |
|------|-----|------|
| 用户列表 | GET /admin/users | 用户管理 |
| 创建用户 | POST /admin/users | 创建 |
| 用户详情 | GET /admin/users/{id} | 详情 |
| 更新用户 | PUT /admin/users/{id} | 更新 |
| 删除用户 | DELETE /admin/users/{id} | 删除 |
| 重置密码 | POST /admin/users/{id}/reset-password | 重置 |
| 角色列表 | GET /admin/roles | 角色管理 |
| 创建角色 | POST /admin/roles | 创建 |
| 更新角色 | PUT /admin/roles/{id} | 更新 |
| 删除角色 | DELETE /admin/roles/{id} | 删除 |
| 权限列表 | GET /admin/permissions | 权限 |
| 系统配置 | GET /admin/config | 配置列表 |
| 更新配置 | PUT /admin/config/{key} | 更新 |
| 系统信息 | GET /admin/info | 系统信息 |
| 系统指标 | GET /admin/metrics | 系统指标 |
| 操作日志 | GET /admin/logs | 日志列表 |
| 备份列表 | GET /admin/backups | 备份列表 |
| 创建备份 | POST /admin/backups | 创建备份 |
| 备份详情 | GET /admin/backups/{id} | 详情 |
| 删除备份 | DELETE /admin/backups/{id} | 删除 |
| 恢复备份 | POST /admin/backups/{id}/restore | 恢复 |
| 恢复记录 | GET /admin/restores | 恢复历史 |
| 清理备份 | POST /admin/backups/cleanup | 清理过期 |
| 备份配置 | GET /admin/backup/config | 配置 |
| 清空缓存 | POST /admin/cache/clear | 清缓存 |
| 健康检查 | GET /admin/health | 健康 |
| API密钥 | GET/POST/PUT/DELETE /admin/api-keys | 密钥管理 |
| 撤销密钥 | POST /admin/api-keys/{id}/revoke | 撤销 |
| 激活密钥 | POST /admin/api-keys/{id}/activate | 激活 |
| 轮换密钥 | POST /admin/api-keys/{id}/rotate | 轮换 |

---

### 16. 定时任务 /scheduler
**后端 API**：admin.py 中的定时任务相关
| 功能 | 说明 |
|------|------|
| 任务列表 | 查看所有定时任务 |
| 创建任务 | 创建新的定时任务 |
| 执行日志 | 查看执行历史 |

---

## 三、完整用户旅程

### 场景1：新系统初始配置
```
1. 登录系统 (admin/admin)
2. 进入系统管理 → 创建用户/角色/分配权限
3. 进入资产管理 → 手动添加设备 OR 使用设备发现自动扫描
4. 进入设备导入 → 下载模板 → 批量导入设备
5. 进入设备监控 → 配置采集指标 → 手动采集验证
6. 进入监控告警 → 配置告警规则 → 测试规则
7. 进入通知管理 → 配置通知渠道 → 测试通知 → 配置目标规则
8. 返回仪表盘 → 看到设备/告警/工单统计
```

### 场景2：日常运维
```
1. 登录 → 仪表盘查看系统状态
2. 告警列表 → 查看新告警 → 确认/解决
3. 创建工单 → 关联告警 → AI根因分析 → 分配处理人
4. 处理人处理 → 提交解决方案 → 审批通过 → 关闭
5. 知识库 → 将处理过程沉淀为SOP文档 → 提交审核 → 批准发布
6. 报表中心 → 生成运维报表 → 下载
```

### 场景3：设备上线流程
```
1. 设备发现 → IP扫描 → 发现新设备
2. 选择设备 → 导入到资产库
3. 资产管理 → 编辑设备信息(补充标签/分组/业务系统)
4. 设备监控 → 配置采集指标 → 开始监控
5. 监控告警 → 确认指标正常 → 配置告警规则
6. 通知管理 → 配置该设备的通知渠道
```

---

## 四、开发优先级

### Phase 1 (基础): 核心框架 + 登录 + 仪表盘 + 布局
- 项目配置 (package.json, vite.config.js, index.html)
- Naive UI 集成
- Axios 请求层 + 15 个 API 模块
- 路由守卫 + 登录验证
- 侧边栏布局 + 响应式
- 登录页 (验证码)
- 仪表盘 (统计卡片 + ECharts)
- 用户信息/登出

### Phase 2 (资产+设备): 资产管理 + 设备监控 + 设备发现
- 设备管理 CRUD
- 设备分组
- 配置项管理
- 业务系统
- 设备发现 (IP/SNMP扫描)
- 设备导入
- 设备监控 (指标采集/配置)

### Phase 3 (告警+通知): 监控告警 + 通知管理
- 告警列表/详情/操作
- 告警规则
- 监控指标查询
- 仪表盘布局
- 通知渠道 CRUD
- 通知发送/测试
- 目标规则/通知对象

### Phase 4 (工单+知识): 工单管理 + 知识库
- 工单 CRUD
- 草稿管理
- 工单审批/分配/解决/关闭
- SLA 计时器
- AI 根因分析
- SOP 文档管理
- 故障案例
- 审核流程

### Phase 5 (AI+报表): AI助手 + 报表中心
- AI 智能问答
- 会话管理
- 故障排查
- 报表模板
- 生成/下载报表
- 定时报表

### Phase 6 (系统+自动): 系统管理 + 自动化 + 巡检
- 用户/角色管理
- 系统配置
- 备份恢复
- 操作日志
- API 密钥
- 自动化触发规则
- 巡检任务/报告

---

## 五、技术选型

| 功能 | 技术方案 |
|------|---------|
| UI 框架 | Naive UI |
| 图表 | ECharts 5 |
| 路由 | Vue Router 4 |
| 状态 | Pinia |
| HTTP | Axios |
| 富文本编辑器 | @vueup/vue-quill |
| 日期处理 | dayjs |
| 代码高亮 | highlight.js |
| Markdown渲染 | markdown-it |
| 表格导出 | xlsx |
| 文件上传 | naive-ui upload |
| 图标 | @vicons/ionicons5, @vicons/material |
