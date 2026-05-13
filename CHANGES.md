# CHANGES - ITOps Platform

## 全局修改记录

| 时间 | 修改内容 | 影响模块 | 原因 | 状态 |
|------|----------|----------|------|------|
| 2026-05-13 | **Phase 2 完成：AI根因分析+处置建议+会话持久化 (C1/C2/C3)** | AI模块 | AI辅助运维决策核心功能 | ✅ 已验证 |
| 2026-05-13 | **Phase 2 完成：API Key认证 + 设备发现+采集+通知配置 (B1/B2/B3/B4)** | 后端P0缺口 | 基础设施完善 | ✅ 已验证 |
| 2026-05-13 | **Phase 2 完成：SLA计时器+升级+草稿保存+回滚机制 (D2/D3/D4)** | 工单+自动化 | 高级工单功能 | ✅ 已验证 |
| 2026-05-13 | **Phase 2 完成：工单Excel导出+巡检报告+批量导入+仪表盘 (E1/A3/A4/E2)** | 报告+前端 | 报告生成和前端完善 | ✅ 已验证 |
| 2026-05-13 | **Phase 3 完成：前端5个页面完善，npm build 全部通过 (A1/A2/A3/A4/E2)** | 前端 | System/Scheduler/Report/Dashboard/Devices | ✅ 已验证 |
| 2026-05-13 | **新增约 316 个单元测试，100% 通过率** | 测试 | 覆盖所有新功能 | ✅ 已验证 |
| 2026-05-12 | 修复重复Base问题，统一使用主Base | 知识库、测试 | 3个declarative_base()导致表创建不完整 | ✅ 已验证 |
| 2026-05-12 | conftest.py导入所有模型 | 测试基础设施 | Base.metadata缺少表定义 | ✅ 已验证 |
| 2026-05-12 | device_api router添加prefix | 设备API | FastAPI路径冲突校验 | ✅ 已验证 |
| 2026-05-12 | SQLite线程安全修复（4个测试文件） | API测试 | check_same_thread=False+StaticPool缺失 | ⚠️ 部分验证 |
| 2026-05-12 | IP/SNMP扫描器修复 | 设备发现 | _parse_target()和版本号正则 | ✅ 已验证 |
| 2026-05-12 | NotificationTargetRule完整API | 通知模块 | CFG-026功能实现 | ✅ 已验证 |
| 2026-05-12 | DeviceMetricConfig采集项开关 | 采集配置 | CFG-013功能实现 | ✅ 已验证 |
| 2026-05-12 | MON-028 告警审计日志 | 监控模块 | 完整审计日志记录和查询功能 | ✅ 已验证 |
| 2026-05-12 | WKO-008 工单草稿保存TDD测试 | 工单模块 | DataFactory + 24个TDD测试用例 | ✅ 已验证 |
| 2026-05-12 | WKO-021 SLA计时器TDD测试 | 工单模块 | DataFactory + 9个测试用例 | ✅ 已验证 |
| 2026-05-12 | WKO-022 SLA自动升级TDD测试 | 工单模块 | DataFactory + 9个测试用例 | ✅ 已验证 |
| 2026-05-12 | WKO-033 工单导出TDD测试 | 工单模块 | DataFactory + 20个TDD测试用例 | ✅ 已验证 |
| 2026-05-12 | workorder_export.py Font修复 | 工单导出 | Font color需aRGB格式 | ✅ 已验证 |
| 2026-05-12 | MON-032 自定义仪表盘布局TDD测试 | 监控模块 | DataFactory + 46个TDD测试用例 | ✅ 已验证 |
| 2026-05-12 | AUTO-020 告警触发自动化DataFactory | 监控模块 | 修复表达式评估bug + trigger_rule/event工厂 | ✅ 已验证 |
| 2026-05-13 | Docker SDK v7 兼容性修复 | 采集模块 | `docker.Client` → `docker.APIClient` | ✅ 已验证 |
| 2026-05-13 | 新增 DEPLOYMENT_ISSUES.md | 文档 | 记录部署问题、网络限制、依赖坑点 | ✅ 已完成 |

## 部署问题（2026-05-13）

### 环境限制记录
| 问题 | 影响 | 状态 |
|------|------|------|
| GitHub 直连超时（git clone/push） | 代码同步 | ⚠️ 待解决 |
| HuggingFace 直连超时 | LLM 模型下载 | ✅ 用 hf-mirror.com 绕过 |
| Docker Hub 直连超时 | 镜像拉取 | ✅ 用 DaoCloud 镜像站 |
| sudo 频繁超时 | docker 操作 | ✅ 用 `sg docker -c` 替代 |
| TDengine 3.x REST API 认证格式 | 数据库写入 | ✅ 已确认正确格式 |
| TDengine 超级表写入需子表名 | 数据库写入 | ⚠️ 方案确定，待实施 |
| 蒲公英网关 SNMP 未开放 | 网络设备监控 | ⚠️ 待获取凭证 |

## 模块级修改日志

### 测试基础设施
| 时间 | 修改 | 原因 |
|------|------|------|
| 2026-05-12 | conftest.py - 导入all_models解决表缺失 | knowledge_base/models.py有独立Base |
| 2026-05-12 | test_alert_audit_log.py - DataFactory测试数据工厂 | 遵循数据工厂原则，避免硬编码测试数据 |
| 2026-05-12 | conftest.py - trigger_rule + trigger_event DataFactory方法 | AUTO-020 告警触发自动化测试数据工厂 |

### 监控模块
| 时间 | 修改 | 原因 |
|------|------|------|
| 2026-05-12 | alert_audit_service.py - 新增服务层 | MON-028审计日志服务 |
| 2026-05-12 | monitoring.py - 告警API集成审计日志 | 创建/确认/解决/删除自动记录 |
| 2026-05-12 | test_dashboard_layout_mon032.py - TDD测试 | MON-032自定义仪表盘布局测试 |
| 2026-05-12 | conftest.py - dashboard布局DataFactory方法 | MON-032测试数据工厂 |
| 2026-05-12 | alert_trigger.py - evaluate_expression修复 | 修复下划线`_`不被允许的bug |

### 设备管理
| 时间 | 修改 | 原因 |
|------|------|------|
| 2026-05-12 | device_api.py - router加prefix | path=""与include_router冲突 |

### 通知模块
| 时间 | 修改 | 原因 |
|------|------|------|
| 2026-05-12 | notification.py - target-rules CRUD | CFG-026新功能 |

### 工单模块
| 时间 | 修改 | 原因 |
|------|------|------|
| 2026-05-12 | test_workorder_draft_wko008.py - WKO-008 TDD测试 | 工单草稿保存功能测试 |
| 2026-05-12 | conftest.py - draft/draft_list DataFactory方法 | 遵循数据工厂原则 |
| 2026-05-12 | test_workorder.py - StaticPool导入修复 | 测试基础设施修复 |
