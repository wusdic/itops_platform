# iTOPS Platform API 审计报告

## 一、后端API路由清单

### 1. auth (prefix: /api/v1/auth)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /captcha | 获取验证码 | ✅ |
| POST | /login | 用户登录 | ✅ |
| POST | /logout | 用户登出 | ✅ |
| POST | /register | 用户注册 | ✅ |
| GET | /userinfo | 获取用户信息 | ✅ |
| POST | /refresh | 刷新Token | ✅ |
| PUT | /password | 修改密码 | ✅ |

### 2. assets (prefix: /api/v1/assets)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /device | 获取设备列表 | ✅ |
| POST | /device | 创建设备 | ✅ |
| GET | /device/{device_id} | 获取设备详情 | ✅ |
| PUT | /device/{device_id} | 更新设备 | ✅ |
| DELETE | /device/{device_id} | 删除设备 | ✅ |
| POST | /device/{device_id}/maintain | 设备维护状态 | ✅ |
| POST | /device/{device_id}/decommission | 退役设备 | ✅ |
| GET | /group | 获取设备分组 | ✅ |
| GET | /group/{group_id}/devices | 获取分组下设备 | ✅ |
| GET | /config | 获取配置项列表 | ✅ |
| POST | /config/snapshot | 创建设备配置快照 | ✅ |
| PUT | /config/{config_id} | 更新配置项 | ✅ |
| DELETE | /config/{config_id} | 删除配置项 | ✅ |
| POST | /config/sync/{device_id} | 同步设备配置 | ✅ |
| GET | /business | 获取业务系统列表 | ✅ |
| GET | /business/{business_id} | 获取业务系统详情 | ✅ |
| GET | /business/{business_id}/devices | 获取业务系统关联设备 | ✅ |
| GET | /stats | 获取资产统计 | ✅ |

### 3. monitoring (prefix: /api/v1/monitoring)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /metrics | 查询监控指标 | ✅ |
| POST | /metrics/collect | 手动采集设备指标 | ✅ |
| GET | /metrics/hosts | 获取已监控主机列表 | ✅ |
| GET | /metrics/available | 获取可用指标列表 | ✅ |
| POST | /metrics/query | PromQL风格查询 | ✅ |
| GET | /alerts | 获取告警列表 | ✅ |
| POST | /alerts | 创建告警 | ✅ |
| GET | /alerts/{alert_id} | 获取告警详情 | ✅ |
| PUT | /alerts/{alert_id}/acknowledge | 确认告警 | ✅ |
| PUT | /alerts/{alert_id}/resolve | 解决告警 | ✅ |
| DELETE | /alerts/{alert_id} | 删除告警 | ✅ |
| GET | /alerts/{alert_id}/audit-logs | 获取告警审计日志 | ✅ |
| POST | /alerts/{alert_id}/audit-logs | 创建告警审计日志 | ✅ |
| GET | /audit-logs | 获取告警审计日志列表 | ✅ |
| GET | /rules | 获取告警规则列表 | ✅ |
| GET | /rules/{rule_id} | 获取告警规则详情 | ✅ |
| GET | /dashboards | 获取监控仪表盘列表 | ✅ |
| GET | /dashboards/{dashboard_id} | 获取仪表盘配置 | ✅ |
| GET | /trigger-rules | 获取触发规则列表 | ✅ |
| POST | /trigger-rules | 创建触发规则 | ✅ |
| GET | /trigger-rules/{rule_id} | 获取触发规则详情 | ✅ |
| PUT | /trigger-rules/{rule_id} | 更新触发规则 | ✅ |
| DELETE | /trigger-rules/{rule_id} | 删除触发规则 | ✅ |
| POST | /trigger-rules/{rule_id}/test | 测试触发规则 | ✅ |
| GET | /trigger-events | 获取触发事件列表 | ✅ |
| POST | /trigger/evaluate | 评估指标触发条件 | ✅ |
| GET | /metric-configs | 获取设备采集项配置列表 | ✅ |
| GET | /metric-configs/{config_id} | 获取采集项配置详情 | ✅ |
| POST | /metric-configs | 创建设备采集项配置 | ✅ |
| PATCH | /metric-configs/{config_id} | 更新采集项配置 | ✅ |

### 4. workorders (prefix: /api/v1/workorders)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | / | 获取工单列表 | ✅ |
| GET | /export | 导出工单 | ✅ |
| GET | /export/{workorder_id} | 导出单个工单 | ✅ |
| POST | / | 创建工单 | ✅ |
| GET | /categories | 获取工单分类列表 | ✅ |
| GET | /priorities | 获取工单优先级列表 | ✅ |
| GET | /stats/summary | 获取工单统计摘要 | ✅ |
| GET | /stats/trend | 获取工单趋势 | ✅ |
| GET | /{workorder_id} | 获取工单详情 | ✅ |
| PUT | /{workorder_id}/draft | 保存工单草稿 | ✅ |
| PUT | /{workorder_id} | 更新工单 | ✅ |
| DELETE | /{workorder_id} | 删除工单 | ✅ |
| GET | /{workorder_id}/flows | 获取工单流程历史 | ✅ |
| POST | /{workorder_id}/flows | 添加工单流程记录 | ✅ |
| POST | /{workorder_id}/assign | 分配工单 | ✅ |
| POST | /{workorder_id}/approve | 审批工单 | ✅ |
| POST | /{workorder_id}/analyze/root-cause | AI根因分析 | ✅ |
| POST | /{workorder_id}/analyze/remediation | AI修复建议 | ✅ |
| POST | /draft/save | 保存工单草稿 | ✅ |
| GET | /draft/list | 获取草稿列表 | ✅ |
| GET | /draft/{draft_id} | 获取草稿详情 | ✅ |
| DELETE | /draft/{draft_id} | 删除草稿 | ✅ |
| GET | /{workorder_id}/sla | 获取工单SLA状态 | ✅ |
| POST | /{workorder_id}/sla/refresh | 刷新SLA状态 | ✅ |
| GET | /{workorder_id}/sla/history | 获取SLA升级历史 | ✅ |
| POST | /{workorder_id}/sla/timer/start | 启动SLA计时器 | ✅ |

### 5. knowledge (prefix: /api/v1/knowledge)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /search | 知识库搜索 | ✅ |
| GET | /sop | 获取SOP文档列表 | ✅ |
| POST | /sop | 创建SOP文档 | ✅ |
| GET | /sop/{doc_id} | 获取SOP文档详情 | ✅ |
| PUT | /sop/{doc_id} | 更新SOP文档 | ✅ |
| DELETE | /sop/{doc_id} | 删除SOP文档 | ✅ |
| POST | /sop/{doc_id}/review | 提交SOP文档审核 | ✅ |
| POST | /sop/{doc_id}/approve | 批准SOP文档 | ✅ |
| GET | /fault-case | 获取故障案例列表 | ✅ |
| POST | /fault-case | 创建故障案例 | ✅ |
| GET | /fault-case/{case_id} | 获取故障案例详情 | ✅ |
| PUT | /fault-case/{case_id} | 更新故障案例 | ✅ |
| GET | /category | 获取分类列表 | ✅ |
| POST | /category | 创建分类 | ✅ |
| GET | /tag | 获取标签列表 | ✅ |
| GET | /stats | 获取知识库统计 | ✅ |
| GET | /review-flows | 获取审核流程列表 | ✅ |
| POST | /review-flows | 创建审核流程 | ✅ |
| GET | /review-flows/{flow_id} | 获取审核流程详情 | ✅ |
| PUT | /review-flows/{flow_id} | 更新审核流程 | ✅ |
| DELETE | /review-flows/{flow_id} | 删除审核流程 | ✅ |
| POST | /reviews/submit | 提交文档审核 | ✅ |
| GET | /reviews | 获取审核记录列表 | ✅ |
| GET | /reviews/{review_id} | 获取审核记录详情 | ✅ |
| POST | /reviews/{review_id}/approve | 批准审核 | ✅ |
| POST | /reviews/{review_id}/reject | 拒绝审核 | ✅ |
| POST | /reviews/{review_id}/request-revision | 要求修订 | ✅ |
| POST | /reviews/{review_id}/withdraw | 撤回审核 | ✅ |
| POST | /reviews/{review_id}/resubmit | 重新提交审核 | ✅ |
| GET | /reviews/pending | 获取待审核列表 | ✅ |

### 6. ai (prefix: /api/v1/ai)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| POST | /chat | 发送消息 | ✅ |
| POST | /chat/_debug | 调试流式接口 | ✅ |
| GET | /conversation/{conversation_id} | 获取会话历史 | ✅ |
| GET | /conversations | 获取会话列表 | ✅ |
| DELETE | /conversation/{conversation_id} | 删除会话 | ✅ |
| PUT | /conversation/{conversation_id}/pin | 置顶/取消置顶会话 | ✅ |
| POST | /conversation/{conversation_id}/messages | 保存消息到会话 | ✅ |
| POST | /troubleshoot | 智能故障排查 | ✅ |
| POST | /troubleshoot/auto | 自动故障诊断 | ✅ |
| POST | /suggest | 生成优化建议 | ✅ |
| POST | /interpret/report | 解读报表 | ✅ |
| POST | /analyze/logs | 分析日志 | ✅ |
| POST | /qa | 知识问答 | ✅ |
| GET | /stats | 获取AI助手统计 | ✅ |

### 7. automation (prefix: /api/v1/automation)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /trigger-rules | 列出触发规则 | ✅ |
| POST | /trigger-rules | 创建触发规则 | ✅ |
| GET | /trigger-rules/{rule_id} | 获取触发规则 | ✅ |
| PUT | /trigger-rules/{rule_id} | 更新触发规则 | ✅ |
| DELETE | /trigger-rules/{rule_id} | 删除触发规则 | ✅ |
| POST | /trigger-rules/{rule_id}/test | 测试触发规则 | ✅ |
| POST | /evaluate | 评估指标触发 | ✅ |
| POST | /executions/{execution_id}/rollback | 执行回滚 | ✅ |
| POST | /executions/{execution_id}/checkpoint | 保存检查点 | ✅ |
| GET | /executions/{execution_id}/snapshot | 获取快照 | ✅ |
| GET | /rollback-history | 获取回滚历史 | ✅ |

### 8. admin (prefix: /api/v1/admin)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /users | 获取用户列表 | ✅ |
| POST | /users | 创建用户 | ✅ |
| GET | /users/{user_id} | 获取用户详情 | ✅ |
| PUT | /users/{user_id} | 更新用户 | ✅ |
| DELETE | /users/{user_id} | 删除用户 | ✅ |
| POST | /users/{user_id}/reset-password | 重置密码 | ✅ |
| GET | /roles | 获取角色列表 | ✅ |
| POST | /roles | 创建角色 | ✅ |
| PUT | /roles/{role_id} | 更新角色 | ✅ |
| DELETE | /roles/{role_id} | 删除角色 | ✅ |
| GET | /permissions | 获取权限列表 | ✅ |
| GET | /config | 获取系统配置 | ✅ |
| PUT | /config/{config_key} | 更新系统配置 | ✅ |
| GET | /info | 获取系统信息 | ✅ |
| GET | /metrics | 获取系统指标 | ✅ |
| GET | /logs | 获取操作日志 | ✅ |
| GET | /backup | 获取备份列表 | ✅ |
| POST | /backup | 创建备份 | ✅ |
| POST | /backup/{backup_id}/restore | 恢复备份 | ✅ |
| POST | /cache/clear | 清空缓存 | ✅ |
| GET | /health | 系统健康检查 | ✅ |
| GET | /api-keys | 获取API Key列表 | ✅ |
| POST | /api-keys | 创建API Key | ✅ |
| GET | /api-keys/{key_id} | 获取API Key详情 | ✅ |
| PUT | /api-keys/{key_id} | 更新API Key | ✅ |
| DELETE | /api-keys/{key_id} | 删除API Key | ✅ |
| POST | /api-keys/{key_id}/revoke | 撤销API Key | ✅ |
| POST | /api-keys/{key_id}/activate | 激活API Key | ✅ |
| POST | /api-keys/{key_id}/rotate | 轮换API Key | ✅ |
| GET | /backups | 获取备份列表(别名) | ✅ |

### 9. notification (prefix: /api/v1/notifications)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /channels | 获取所有通知渠道 | ✅ |
| GET | /channels/{channel_id} | 获取单个通知渠道 | ✅ |
| POST | /channels | 创建通知渠道 | ✅ |
| PUT | /channels/{channel_id} | 更新通知渠道 | ✅ |
| DELETE | /channels/{channel_id} | 删除通知渠道 | ✅ |
| POST | /send | 发送通知 | ✅ |
| POST | /alert | 发送告警通知 | ✅ |
| GET | /types | 获取通知类型列表 | ✅ |
| POST | /test/{channel_id} | 测试通知渠道 | ✅ |
| GET | /history | 获取通知历史 | ✅ |
| GET | /target-rules | 获取通知目标规则列表 | ✅ |
| POST | /target-rules | 创建通知目标规则 | ✅ |
| GET | /target-rules/{rule_id} | 获取通知目标规则详情 | ✅ |
| PUT | /target-rules/{rule_id} | 更新通知目标规则 | ✅ |
| DELETE | /target-rules/{rule_id} | 删除通知目标规则 | ✅ |
| POST | /target-rules/{rule_id}/toggle | 启用/禁用通知目标规则 | ✅ |
| GET | /target-rules/match | 匹配通知目标规则 | ✅ |
| GET | /targets | 获取通知对象配置列表 | ✅ |
| POST | /targets | 创建通知对象配置 | ✅ |
| GET | /targets/{target_id} | 获取通知对象配置详情 | ✅ |
| DELETE | /targets/{target_id} | 删除通知对象配置 | ✅ |

### 10. discovery (prefix: /api/v1/discovery)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| POST | /ip/scan | 启动IP范围扫描 | ✅ |
| GET | /ip/scan/{task_id}/results | 获取IP扫描结果 | ✅ |
| POST | /ip/scan/sync | 同步IP范围扫描 | ✅ |
| GET | /ip/hosts | 获取扫描发现的主机列表 | ✅ |
| POST | /snmp/scan | 启动SNMP扫描 | ✅ |
| GET | /snmp/scan/{task_id}/results | 获取SNMP扫描结果 | ✅ |
| POST | /snmp/scan/sync | 同步SNMP扫描 | ✅ |
| POST | /snmp/discover | SNMP设备发现 | ✅ |
| GET | /snmp/devices | 获取SNMP设备列表 | ✅ |
| POST | /devices/import | 导入发现的设备 | ✅ |
| POST | /scan | 启动设备扫描 | ✅ |
| GET | /scan/{task_id}/status | 获取扫描任务状态 | ✅ |
| GET | /hosts | 获取发现的主机列表 | ✅ |
| POST | /import | 导入发现的主机 | ✅ |
| POST | /tasks | 创建设备发现任务 | ✅ |
| GET | /tasks | 获取发现任务列表 | ✅ |

### 11. device_api (prefix: /api/v1/devices)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | / | 获取设备列表 | ✅ |
| GET | /stats | 获取设备统计 | ✅ |
| GET | /{device_name} | 获取设备详情 | ✅ |
| POST | /collect | 采集设备指标 | ✅ |
| POST | /collect/all | 采集所有设备 | ✅ |
| GET | /{device_name}/status | 获取设备状态 | ✅ |
| GET | /{device_name}/metrics | 获取设备指标 | ✅ |
| PATCH | /{device_id}/metrics/{metric} | 更新设备指标采集配置 | ✅ |
| GET | /{device_id}/metrics/{metric}/config | 获取设备指标配置 | ✅ |
| GET | /{device_id}/metrics/configs | 获取设备所有指标配置 | ✅ |
| GET | /adapters/list | 获取支持的适配器列表 | ✅ |
| GET | /adapters/protocols | 获取支持的协议列表 | ✅ |
| POST | /config/reload | 重新加载配置 | ✅ |
| GET | /config/stats | 获取配置统计 | ✅ |

### 12. device_metrics (prefix: /api/v1/device-metrics)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /{device_id}/metrics | 获取设备所有指标配置 | ✅ |
| PATCH | /{device_id}/metrics | 更新设备指标配置 | ✅ |
| GET | /{device_id}/metrics/categories | 获取设备支持的指标类别 | ✅ |
| POST | /{device_id}/metrics/bulk | 批量更新设备指标配置 | ✅ |
| GET | /name/{device_name}/metrics | 通过设备名获取指标配置 | ✅ |
| PATCH | /name/{device_name}/metrics | 通过设备名更新指标配置 | ✅ |

### 13. device_import (prefix: /api/v1/devices/import)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /template | 下载设备导入模板 | ✅ |
| POST | /validate | 验证导入数据 | ✅ |
| POST | / | 批量导入设备 | ✅ |
| POST | /simple | 简单批量导入(直接传数据) | ✅ |

### 14. inspection (prefix: /api/v1/inspection)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /tasks | 获取巡检任务列表 | ✅ |
| GET | /tasks/{task_id} | 获取巡检任务详情 | ✅ |
| POST | /tasks | 创建巡检任务 | ✅ |
| GET | /reports/{task_id} | 获取巡检报告 | ✅ |
| GET | /reports/{task_id}/export | 导出巡检报告 | ✅ |
| GET | /reports/template | 获取巡检报告模板 | ✅ |
| GET | /results/{task_id} | 获取巡检结果列表 | ✅ |
| GET | /statistics/summary | 获取巡检统计摘要 | ✅ |

### 15. report (prefix: /api/v1/report)
| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | /template | 获取报表模板列表 | ✅ |
| GET | /template/{template_id} | 获取报表模板详情 | ✅ |
| POST | /template | 创建报表模板 | ✅ |
| PUT | /template/{template_id} | 更新报表模板 | ✅ |
| DELETE | /template/{template_id} | 删除报表模板 | ✅ |
| POST | /generate | 生成报表 | ✅ |
| POST | /generate/async | 异步生成报表 | ✅ |
| GET | / | 获取报表列表 | ✅ |
| GET | /stats | 获取报表统计 | ✅ |
| GET | /{report_id} | 获取报表详情 | ✅ |
| DELETE | /{report_id} | 删除报表 | ✅ |
| GET | /{report_id}/download | 下载报表 | ✅ |
| GET | /files/{filename} | 获取报表文件 | ✅ |
| GET | /schedule | 获取定时报表列表 | ✅ |
| POST | /schedule | 创建定时报表 | ✅ |
| PUT | /schedule/{schedule_id} | 更新定时报表 | ✅ |
| DELETE | /schedule/{schedule_id} | 删除定时报表 | ✅ |
| POST | /schedule/{schedule_id}/toggle | 启用/禁用定时报表 | ✅ |

---

## 二、前端API调用与后端不匹配清单

### 不匹配项汇总

#### 1. system.js (应使用 admin 路由)
| 前端调用 | 问题 |
|---|---|
| `/system/user/list` | 应为 `/admin/users` |
| `/system/role/list` | 应为 `/admin/roles` |
| `/system/menu/list` | 路由缺失 |
| `/system/dict/list` | 路由缺失 |
| `/system/config/list` | 应为 `/admin/config` |
| `/system/user` (POST) | 应为 `/admin/users` |
| `/system/user/{id}` | 应为 `/admin/users/{user_id}` |
| `/system/role/{id}` | 应为 `/admin/roles/{role_id}` |
| `/system/menu` | 路由缺失 |
| `/system/dict` | 路由缺失 |
| `/system/config/{key}` | 应为 `/admin/config/{config_key}` |

#### 2. notification API
| 前端调用 | 问题 |
|---|---|
| `/notifications/messages` | 应为 `/notifications/history` |
| `/notifications/messages/unread-count` | 缺失，需新增 |
| `/notifications/messages/{id}/read` | 缺失，需新增 |
| `/notifications/messages/read-all` | 缺失，需新增 |

#### 3. backup API
| 前端调用 | 问题 |
|---|---|
| `/admin/backups` | 应为 `/admin/backups` 或 `/admin/backup` |

#### 4. monitoring API
| 前端调用 | 问题 |
|---|---|
| `/monitoring/alerts/{id}/handle` | 应使用 acknowledge |
| `/monitoring/alerts/statistics` | 缺失 |
| `/monitoring/metrics/history` | 缺失 |
| `/monitoring/metrics/top/{type}` | 缺失 |

#### 5. automation API
| 前端调用 | 问题 |
|---|---|
| `/automation/scripts` | 后端无 scripts，使用 trigger-rules |
| `/automation/scripts/{id}/execute` | 后端无此接口 |
| `/automation/executions` | 部分存在但路径不完整 |

#### 6. assets.js
| 前端调用 | 问题 |
|---|---|
| `/assets/list` | 后端无此端点，应为 `/assets/device` |
| `/assets/{id}` | 后端无此端点 |

#### 7. scheduler.js
| 前端调用 | 问题 |
|---|---|
| `/scheduler/task/list` | 后端无此路由 |
| `/scheduler/task` | 后端无此路由 |
| `/report/list` | 应为 `/report/` |

#### 8. AI API
| 前端调用 | 问题 |
|---|---|
| `/ai/analyze/{alertId}/{type}` | 后端无此端点 |

---

## 三、功能缺失清单

### 后端缺失功能
1. **消息通知模块** - 前端需要 `GET /notifications/messages`, `POST /notifications/messages/{id}/read`, `POST /notifications/messages/read-all`, `GET /notifications/messages/unread-count`
2. **系统管理模块** - 字典数据 /menu 路由缺失

### 前端缺失功能
1. **网络扫描配置页面** - 核心功能，完全缺失
2. **AI分析页面** (`/ai/analyze`) - 30行占位
3. **工单SLA页面** - 完全缺失
4. **巡检任务页面** - 完全缺失
5. **报表管理页面** - 不完整
6. **系统配置页面** - 不完整

### 前端页面缺失/不完整
1. monitoring/alerts.vue - 告警确认/解决功能
2. workorder/list.vue - 工单处理人硬编码
3. ai/copilot.vue - 需要完全重写
4. knowledge/list.vue, category.vue - 内容极少
5. automation/script.vue, task.vue, execute.vue - 功能简陋
6. backup/list.vue, restore.vue - 功能简陋
7. notification/message.vue, config.vue - 功能简陋
8. system/user.vue, role.vue, menu.vue, dict.vue, config.vue - 功能简陋
