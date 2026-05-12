# CHANGES - ITOps Platform

## 全局修改记录

| 时间 | 修改内容 | 影响模块 | 原因 | 状态 |
|------|----------|----------|------|------|
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
| 2026-05-12 | WKO-033 工单导出TDD测试 | 工单模块 | DataFactory + 20个测试用例 | ✅ 已验证 |
| 2026-05-12 | workorder_export.py Font修复 | 工单导出 | Font color需aRGB格式 | ✅ 已验证 |
| 2026-05-12 | MON-032 自定义仪表盘布局TDD测试 | 监控模块 | DataFactory + 46个TDD测试用例 | ✅ 已验证 |

## 模块级修改日志

### 测试基础设施
| 时间 | 修改 | 原因 |
|------|------|------|
| 2026-05-12 | conftest.py - 导入all_models解决表缺失 | knowledge_base/models.py有独立Base |
| 2026-05-12 | test_alert_audit_log.py - DataFactory测试数据工厂 | 遵循数据工厂原则，避免硬编码测试数据 |

### 监控模块
| 时间 | 修改 | 原因 |
|------|------|------|
| 2026-05-12 | alert_audit_service.py - 新增服务层 | MON-028审计日志服务 |
| 2026-05-12 | monitoring.py - 告警API集成审计日志 | 创建/确认/解决/删除自动记录 |
| 2026-05-12 | test_dashboard_layout_mon032.py - TDD测试 | MON-032自定义仪表盘布局测试 |
| 2026-05-12 | conftest.py - dashboard布局DataFactory方法 | MON-032测试数据工厂 |

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
