# TODO - ITOps Platform（IT运维智能平台）

## 核心目的
构建智能化、一体化的IT运维管理平台，实现设备自动发现、实时监控告警、工单自动流转、AI辅助决策的完整闭环。

## 项目信息
- 仓库：https://github.com/wusdic/itops_platform
- 当前实现度：~85%（157/184需求）
- P0缺口：0项（已全部完成 ✅）
- P1缺口：约17项

## 整体架构
```
前端( Vue/RuoYi ) → API层( FastAPI ) → 业务层( modules/business/ )
                                      → 采集层( modules/collection/ )
                                      → 自动化层( modules/automation/ )
                                      → 存储层( MySQL + TDengine + Redis + MinIO )
                                      → AI层( Qwen3.6-27B via llama-cpp )
```

---

## 任务清单

### Phase 0: 项目治理（已完成 ✅）
- [x] 0.1 测试基础设施修复（conftest.py + 模型导出）
- [x] 0.2 规划设计文档建立（TODO.md, LOG.md, CHANGES.md）

### Phase 1: P0 后端缺口（已完成 ✅）
- [x] 1.1 设备自动发现 - IP段/SNMP扫描 (COL-001, COL-002) ✅ `cb9fc99, 4992ae3`
- [x] 1.2 采集项精细化开关 (CFG-013) ✅ `cb9fc99`
- [x] 1.3 通知对象配置 (CFG-026) ✅ `f06a8df`
- [x] 1.4 告警审计日志 (MON-028) ✅ `005de2f`
- [x] 1.5 工单草稿保存 (WKO-008) ✅ `74b1f22`
- [x] 1.6 SLA实时计时器 (WKO-021) ✅ `b252be1`
- [x] 1.7 SLA超时自动升级 (WKO-022) ✅ `b252be1`
- [x] 1.8 工单导出Excel (WKO-033) ✅ `b252be1`
- [x] 1.9 仪表盘自定义布局 (MON-032) ✅ `7b627d6`
- [x] 1.10 告警触发自动化执行 (AUTO-020) ✅ `6c13124`

**Phase 1 统计：250+ 新增测试，100% 通过率**

### Phase 2: P0+P1 后端完善（进行中）
- [ ] 2.1 AI根因分析 + 处置建议 (AI-010, AI-011)
- [ ] 2.2 AI对话历史持久化（会话管理）
- [ ] 2.3 趋势告警规则 (CFG-021)
- [ ] 2.4 聚合告警规则 (CFG-027)
- [ ] 2.5 知识库审核发布流程 (KNO-005)

### Phase 3: 前端重建（待执行）
- [ ] 3.1 修复 System.vue 构建错误
- [ ] 3.2 完善 Scheduler.vue 定时任务管理
- [ ] 3.3 新增设备自动发现页面
- [ ] 3.4 新增采集项配置页面
- [ ] 3.5 新增通知对象配置页面
- [ ] 3.6 新增自定义仪表盘页面
- [ ] 3.7 整体UI重构（RuoYi风格）
- ⚠️ 阻塞：npm install 权限问题（node_modules 写入失败）

### Phase 4: 测试完善（待执行）
- [ ] 4.1 修复现有失败测试（~175个 legacy 测试）
- [ ] 4.2 补充 Phase 2 功能测试
- [ ] 4.3 集成测试覆盖
- [ ] 4.4 端到端业务流程测试
- [ ] 4.5 撰写测试报告 (TEST_REPORT.md)

### Phase 5: 交付（待执行）
- [ ] 5.1 文档同步（README, API文档）
- [ ] 5.2 Git提交并推送
- [ ] 5.3 部署验证

---

## 当前测试基线
| 测试集 | 状态 |
|--------|------|
| 新 TDD 测试（discovery/metric_toggle/notification/wko 等） | ✅ 100% |
| 新增功能测试（alert_audit/dashboard 等） | ✅ 100% |
| legacy 测试（config_loader/log_collector/api_collectors 等） | ⚠️ ~175 失败（需适配API） |

---

## 阻塞项
- Phase 3 前端：npm install 权限问题（需要 root 或 node_modules 重建）
- Phase 4 测试：legacy 测试 API 不匹配（config_loader/log_collector 等早期实现）

## 今日Git提交（13条）
```
6c13124 feat(AUTO-020): Alert-Triggered Automation DataFactory
7b627d6 feat(MON-032): Custom Dashboard Layout TDD Tests
b252be1 feat(WKO-021/022/033): SLA Timer + Auto-Escalation + Export
74b1f22 feat(WKO-008): Work Order Draft Save TDD tests
005de2f feat: MON-028 complete alert audit log
f06a8df CFG-026: Complete NotificationTargetRule service layer
cb9fc99 test(discovery): Add comprehensive TDD tests
4992ae3 feat(discovery): Add TDD tests, fix _parse_target and version regex
aaec9f5 fix: resolve duplicate Base and test infrastructure issues
...
```
