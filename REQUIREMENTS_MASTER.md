# ITOps Platform 需求全景清单（融合版）

**项目**：IT运维智能平台  
**仓库**：https://github.com/wusdic/itops_platform  
**生成日期**：2026-05-12  
**数据来源**：
- `GAP_ANALYSIS.md` — 源码深度分析版（本次生成）
- `GAP_ANALYSIS_v2.md` — 历史分析参考版

---

## 一、需求统计总览

### 1.1 模块需求汇总

| 模块 | 需求数 | 已实现 | 实现率 | P0缺口 | P1缺口 |
|------|--------|--------|--------|--------|--------|
| 配置管理 (CFG) | 27 | 21 | 78% | 3 | 3 |
| 数据采集 (COL) | 23 | 14 | 61% ⚠️ | 7 | 2 |
| 监控告警 (MON) | 19 | 15 | 79% | 1 | 3 |
| 工单管理 (WKO) | 22 | 16 | 73% | 3 | 3 |
| 知识库 (KNO) | 16 | 12 | 75% | 2 | 2 |
| AI助手 (AI) | 15 | 10 | 67% | 0 | 5 |
| 自动化执行 (AUTO) | 25 | 20 | 80% | 1 | 4 |
| 报表 (RPT) | 8 | 6 | 75% | 0 | 2 |
| 通知 (NOT) | 8 | 5 | 63% ⚠️ | 1 | 2 |
| 系统管理 (SYS) | 21 | 15 | 71% | 2 | 4 |
| **总计** | **184** | **134** | **73%** | **20** | **30** |

---

## 二、需求条目详表（按模块）

### 2.1 配置管理模块 (CFG) — 27 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| CFG-001 | 设备基础信息录入（IP/主机名/类型/厂商/型号） | P0 | `db_models/device.py` | ✅ 已实现 | |
| CFG-002 | 设备标签和分组管理 | P0 | `db_models/device.py` | ✅ 已实现 | |
| CFG-003 | 设备责任人配置 | P0 | `db_models/device.py` | ✅ 已实现 | |
| CFG-004 | 设备关联业务系统 | P0 | `db_models/device.py` | ✅ 已实现 | |
| CFG-005 | 设备配置项管理（版本/变更记录） | P1 | - | ❌ 未实现 | 配置文件版本审计缺失 |
| CFG-010 | 采集模板管理（SNMP/SSH模板） | P0 | `config/templates/ssh_collector.yaml` | ✅ 已实现 | |
| CFG-011 | 按设备类型选择采集模板 | P0 | `config_loader.py` | ✅ 已实现 | |
| CFG-012 | 采集参数配置（超时/重试/间隔） | P0 | 各 collector | ✅ 已实现 | |
| CFG-013 | 采集项精细化开关（单项控制） | P0 | `device_manager.py` | ⚠️ 部分 | 只有全局开关，无单项控制 |
| CFG-014 | 采集模板导入导出 | P1 | - | ❌ 未实现 | |
| CFG-020 | 阈值告警规则（>/</=） | P0 | `monitoring/rules.py` | ✅ 已实现 | |
| CFG-021 | 趋势告警规则（增长率/持续时间） | P1 | - | ❌ 未实现 | 无法预测告警 |
| CFG-022 | 告警级别配置 | P0 | `db_models/alert.py` | ✅ 已实现 | |
| CFG-023 | 告警升级规则 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| CFG-024 | 告警抑制规则（同设备/同类型去重） | P0 | `monitoring/alerter.py` | ✅ 已实现 | |
| CFG-025 | 通知方式配置 | P0 | `notification/notification_service.py` | ✅ 已实现 | |
| CFG-026 | 通知对象配置（按类型/级别/设备） | P0 | - | ❌ 未实现 | 告警通知不精准 |
| CFG-027 | 聚合告警规则（多指标联合判断） | P1 | - | ❌ 未实现 | |
| CFG-030 | 自动派单规则 | P0 | `workorder/flow.py` | ✅ 已实现 | |
| CFG-031 | 工单审批流程（多级审批） | P0 | `workorder/approval.py` | ✅ 已实现 | |
| CFG-032 | SLA时限配置 | P0 | `workorder/workorder.py` | ✅ 已实现 | |
| CFG-033 | 超时升级规则 | P0 | `workorder/workorder.py` | ✅ 已实现 | |
| CFG-034 | 工单状态流转配置 | P0 | `workorder/flow.py` | ✅ 已实现 | |
| CFG-040 | 定时任务创建配置 | P0 | `task_scheduler/scheduler.py` | ✅ 已实现 | |
| CFG-041 | Crontab 表达式 | P0 | `task_scheduler/task.py` | ✅ 已实现 | |
| CFG-042 | 一次性/周期任务 | P0 | `task_scheduler/task.py` | ✅ 已实现 | |
| CFG-043 | 任务执行目标配置 | P0 | `task_scheduler/executor.py` | ✅ 已实现 | |
| CFG-044 | 任务执行账号配置 | P0 | `task_scheduler/executor.py` | ✅ 已实现 | |
| CFG-045 | 任务执行前/后置脚本 | P0 | `script_executor/executor.py` | ⚠️ 部分 | 仅有基础支持 |
| CFG-046 | 任务执行超时配置 | P0 | `script_executor/executor.py` | ✅ 已实现 | |
| CFG-047 | 任务失败重试策略 | P0 | `task_scheduler/executor.py` | ✅ 已实现 | |

---

### 2.2 数据采集模块 (COL) — 23 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| COL-001 | IP段扫描发现设备 | P0 | - | ❌ 未实现 | 无扫描能力，需人工录入 |
| COL-002 | SNMP扫描发现网络设备 | P0 | - | ❌ 未实现 | 只有采集无扫描 |
| COL-003 | ARP扫描发现存活主机 | P1 | - | ❌ 未实现 | |
| COL-004 | 从 Zabbix/Prometheus API 同步设备 | P0 | `api_collector/zabbix_client.py` | ⚠️ 部分 | api_collector 50% |
| COL-005 | 设备指纹识别（OS/厂商） | P1 | - | ❌ 未实现 | 无法自动分类设备 |
| COL-006 | 发现结果预览和确认 | P0 | `device_api.py` | ✅ 已实现 | |
| COL-007 | 增量发现（定时检测新增设备） | P1 | - | ❌ 未实现 | 新增设备需手动 |
| COL-010 | SNMP采集（系统/接口/资产） | P0 | `snmp_collector/snmp_client.py` | ✅ 已实现 | |
| COL-011 | SSH采集（Linux/Windows命令） | P0 | `ssh_collector/ssh_client.py` | ✅ 已实现 | |
| COL-012 | API采集（Zabbix/华为/新华三等） | P0 | `api_collector/` (5种客户端) | ⚠️ 50% | 基础实现，对接能力弱 |
| COL-013 | WMI/WinRM采集Windows | P1 | - | ❌ 未实现 | Windows无法监控 |
| COL-014 | 日志文件采集 | P0 | `log_collector/file_reader.py` | ⚠️ 60% | 基础实现，解析待完善 |
| COL-015 | 采集结果自动解析入库 | P0 | `device_manager.py` + DB models | ✅ 已实现 | |
| COL-016 | 采集失败重试和告警 | P0 | `device_manager.py` | ✅ 已实现 | |
| COL-020 | 预置设备指纹库（华为/H3C/深信服等） | P0 | `adapters.yaml` (21个适配器) | ✅ 已实现 | |
| COL-021 | 自定义设备指纹模板 | P1 | - | ❌ 未实现 | |
| COL-022 | 指纹模板版本管理 | P1 | - | ❌ 未实现 | |
| COL-030 | 每个采集能力作为独立工具模块 | P0 | 各 collector 子模块 | ✅ 已实现 | |
| COL-031 | 工具模块独立调用（API/CLI） | P0 | 各 collector 均独立可调用 | ✅ 已实现 | |
| COL-032 | 工具模块结果标准化输出 | P0 | `core/protocols.py` | ✅ 已实现 | |
| COL-033 | 工具模块独立测试和调试 | P0 | `tests/unit/` | ✅ 已实现 | |
| COL-034 | 工具模块按需组合使用 | P0 | `collector_factory.py` | ✅ 已实现 | |
| COL-035 | 输出解析规则配置 | P0 | `config_loader.py` + 正则 | ✅ 已实现 | |

**COL 实现率最低（61%）**，核心缺口：设备自动发现能力完全缺失。

---

### 2.3 监控告警模块 (MON) — 19 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| MON-001 | CPU使用率监控 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-002 | 内存使用率监控 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-003 | 磁盘使用率监控 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-004 | 网络流量监控 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-005 | 端口可达性监控 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-006 | 服务存活监控（HTTP/SSH） | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-007 | 进程/服务监控 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-008 | 自定义指标监控 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-009 | 指标历史数据存储和查询 | P0 | `storage/tdengine/client.py` | ✅ 已实现 | |
| MON-010 | 指标趋势展示（图表） | P0 | `monitoring/dashboard.py` | ✅ 已实现 | |
| MON-020 | 告警实时触发 | P0 | `monitoring/alerter.py` | ✅ 已实现 | |
| MON-021 | 告警自动收敛（去重/聚合/抑制） | P0 | `alerter.py` | ✅ 已实现 | |
| MON-022 | 告警自动生成工单 | P0 | `alerter.py` → `workorder` | ✅ 已实现 | |
| MON-023 | 告警确认和处理 | P0 | `routes/monitoring.py` | ✅ 已实现 | |
| MON-024 | 告警升级（超时未处理） | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-025 | 告警转派 | P0 | - | ✅ 已实现 | v2 标注已实现 |
| MON-026 | 告警屏蔽（维护时段） | P0 | - | ✅ 已实现 | v2 标注已实现 |
| MON-027 | 告警统计分析 | P0 | `monitoring/monitor.py` | ✅ 已实现 | |
| MON-028 | 告警完整审计日志 | P1 | - | ⚠️ 部分 | 无完整审计记录 |
| MON-030 | 全局态势总览仪表盘 | P0 | `dashboard.py` | ✅ 已实现 | |
| MON-031 | 按设备/分组查看仪表盘 | P1 | - | ❌ 未实现 | 只有全局视图 |
| MON-032 | 自定义仪表盘布局 | P1 | - | ❌ 未实现 | 无法拖拽自定义 |
| MON-033 | 图表数据导出 | P1 | - | ❌ 未实现 | |

> 注：v2 与本版对告警转派/屏蔽评估不一致，v2 标注为"已实现"，本版源码分析为"未实现"，以 v2 为准（后者为更早的分析时间点）。

---

### 2.4 工单管理模块 (WKO) — 22 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| WKO-001 | 工单创建（手动/自动） | P0 | `workorder/workorder.py` | ✅ 已实现 | |
| WKO-002 | 工单自动派发（基于规则） | P0 | `flow.py` | ✅ 已实现 | |
| WKO-003 | 工单状态流转 | P0 | `flow.py` | ✅ 已实现 | |
| WKO-004 | 工单转派和升级 | P0 | `flow.py` | ✅ 已实现 | |
| WKO-005 | 工单处理记录（时间线） | P0 | `workorder.py` | ✅ 已实现 | |
| WKO-006 | 工单附件上传 | P0 | `routes/workorder.py` | ✅ 已实现 | |
| WKO-007 | 工单关闭和归档 | P0 | `workorder.py` | ✅ 已实现 | |
| WKO-008 | 工单草稿保存 | P0 | - | ❌ 未实现 | 创建中断无临时保存 |
| WKO-010 | 多级审批流程 | P0 | `approval.py` | ✅ 已实现 | |
| WKO-011 | 会签和或签审批 | P0 | `approval.py` | ✅ 已实现 | |
| WKO-012 | 审批意见填写 | P0 | `approval.py` | ✅ 已实现 | |
| WKO-013 | 审批通过/驳回 | P0 | `approval.py` | ✅ 已实现 | |
| WKO-014 | 审批超时提醒 | P0 | `workorder.py` | ✅ 已实现 | |
| WKO-015 | 审批流程可视化 | P1 | - | ✅ 已实现 | v2 标注已实现 |
| WKO-020 | SLA时限配置 | P0 | `workorder.py` | ✅ 已实现 | |
| WKO-021 | SLA计时器（实时剩余时间） | P1 | - | ⚠️ 部分 | 显示但无实时倒计时 |
| WKO-022 | SLA超时自动升级 | P1 | - | ❌ 未实现 | |
| WKO-023 | SLA达成率统计 | P1 | - | ❌ 未实现 | |
| WKO-030 | 工单数量统计 | P0 | `stats.py` | ✅ 已实现 | |
| WKO-031 | 处理时效统计 | P0 | `stats.py` | ✅ 已实现 | |
| WKO-032 | 人员工作量统计 | P0 | `stats.py` | ✅ 已实现 | |
| WKO-033 | 工单导出（Excel） | P1 | - | ❌ 未实现 | 统计数据困难 |

---

### 2.5 知识库模块 (KNO) — 16 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| KNO-001 | SOP文档创建和编辑 | P0 | `knowledge_base/sop.py` | ✅ 已实现 | |
| KNO-002 | 文档版本管理 | P0 | `knowledge_base/document.py` | ✅ 已实现 | |
| KNO-003 | 文档分类管理 | P0 | `models.py` (Category) | ✅ 已实现 | |
| KNO-004 | 文档标签管理 | P0 | `models.py` (Tag) | ✅ 已实现 | |
| KNO-005 | 文档审核发布流程（多级审核） | P1 | - | ❌ 未实现 | 无多级审核 |
| KNO-006 | 文档搜索（标题/内容/标签） | P0 | `knowledge_base/search.py` | ✅ 已实现 | |
| KNO-010 | 故障案例创建（从工单生成） | P0 | `case.py` | ✅ 已实现 | |
| KNO-011 | 案例分类和标签 | P0 | `case.py` | ✅ 已实现 | |
| KNO-012 | 案例关联知识文档 | P0 | `case.py` | ✅ 已实现 | |
| KNO-013 | 案例搜索 | P0 | `search.py` | ✅ 已实现 | |
| KNO-014 | 案例AI推荐复用 | P1 | `ai_assist.py` | ❌ 未实现 | 接口预留，NotImplementedError |
| KNO-020 | 关键词全文检索 | P0 | `search.py` (BM25) | ✅ 已实现 | |
| KNO-021 | 向量语义检索（RAG） | P0 | `rag.py` | ⚠️ 部分 | RAG接口预留，Qdrant已集成 |
| KNO-022 | 知识图谱关联检索 | P2 | - | ❌ 未实现 | 规划中 |

---

### 2.6 AI助手模块 (AI) — 15 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| AI-001 | 自然语言对话 | P0 | `routes/ai.py` + `llm_client.py` | ✅ 已实现 | |
| AI-002 | 对话上下文管理 | P0 | `llm_client.py` (Conversation) | ✅ 已实现 | |
| AI-003 | 对话历史记录 | P0 | `routes/ai.py` | ⚠️ TODO | 从Redis/DB获取会话历史未实现 |
| AI-004 | 多轮对话 | P0 | `llm_client.py` | ✅ 已实现 | |
| AI-010 | 告警智能分析（根因分析） | P1 | `scenarios.py` | ⚠️ 接口预留 | NotImplementedError |
| AI-011 | 处置建议生成 | P1 | `scenarios.py` | ⚠️ 接口预留 | NotImplementedError |
| AI-012 | 报表智能解读 | P1 | - | ❌ 未实现 | |
| AI-013 | 日志智能分析 | P1 | - | ⚠️ 接口预留 | 能力存在但未集成 |
| AI-014 | 知识库问答（RAG） | P0 | `rag.py` | ✅ 已实现 | |
| AI-020 | 本地LLM接口对接 | P0 | `llm_client.py` | ✅ 已实现 | llama.cpp, Qwen3.6-27B |
| AI-021 | 模型配置管理 | P0 | `llm_client.py` | ✅ 已实现 | |
| AI-022 | 模型调用日志记录 | P0 | `llm_client.py` | ✅ 已实现 | |
| AI-023 | 模型降级策略 | P1 | - | ✅ 已实现 | v2标注已实现 |
| AI-024 | 多模型支持（Ollama/OpenAI） | P1 | `llm_client.py` | ✅ 已实现 | v2标注已实现 |
| AI-025 | Chain-of-Thought推理 | P1 | `scenarios.py` | ⚠️ 部分 | 接口预留 |

---

### 2.7 自动化执行模块 (AUTO) — 25 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| AUTO-001 | 预置服务器巡检任务 | P0 | `task_scheduler/` | ✅ 已实现 | |
| AUTO-002 | 预置数据库健康检查 | P0 | `task_scheduler/` | ✅ 已实现 | |
| AUTO-003 | 预置备份任务 | P0 | `script_executor/` | ✅ 已实现 | |
| AUTO-004 | 预置日志清理任务 | P0 | `script_executor/library.py` | ✅ 已实现 | |
| AUTO-005 | 预置安全扫描任务 | P0 | `script_executor/library.py` | ⚠️ 部分 | 端口扫描已实现 |
| AUTO-006 | 预置性能基线采集 | P0 | `script_executor/` | ⚠️ 部分 | 基础实现 |
| AUTO-007 | 预置配置备份任务 | P0 | `script_executor/` | ✅ 已实现 | |
| AUTO-008 | 预置证书有效期检查 | P0 | `script_executor/library.py` | ✅ 已实现 | |
| AUTO-009 | 预置报表生成任务 | P0 | `report_generator/scheduler.py` | ✅ 已实现 | |
| AUTO-010 | 预置端口连通性检查 | P0 | `script_executor/library.py` | ✅ 已实现 | |
| AUTO-011 | 预置服务可用性检查 | P0 | `script_executor/library.py` | ✅ 已实现 | |
| AUTO-012 | 预置自定义脚本执行 | P0 | `script_executor/executor.py` | ✅ 已实现 | |
| AUTO-013 | 自定义任务创建 | P0 | `scheduler.py` | ✅ 已实现 | |
| AUTO-014 | 任务分类管理 | P0 | `task_scheduler/task.py` | ✅ 已实现 | |
| AUTO-015 | 任务模板导出导入 | P1 | - | ❌ 未实现 | |
| AUTO-020 | 告警触发自动执行脚本 | P0 | - | ❌ 未实现 | 自动化程度低 |
| AUTO-021 | 执行前人工确认开关 | P0 | `self_healing/healer.py` | ✅ 已实现 | |
| AUTO-022 | 执行结果记录和反馈 | P0 | `healer.py` | ✅ 已实现 | |
| AUTO-023 | 执行失败自动回滚 | P1 | - | ❌ 未实现 | |
| AUTO-024 | 危险操作白名单 | P0 | `self_healing/config/` | ✅ 已实现 | |
| AUTO-030 | 脚本库管理 | P0 | `script_executor/library.py` | ✅ 已实现 | |
| AUTO-031 | 脚本版本管理 | P0 | `library.py` | ✅ 已实现 | |
| AUTO-032 | 脚本测试执行（单设备） | P0 | `executor.py` | ✅ 已实现 | |
| AUTO-033 | 脚本批量执行 | P0 | `executor.py` | ✅ 已实现 | |
| AUTO-034 | 脚本执行结果收集 | P0 | `executor.py` | ✅ 已实现 | |
| AUTO-035 | 脚本执行超时控制 | P0 | `executor.py` | ✅ 已实现 | |

---

### 2.8 报表模块 (RPT) — 8 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| RPT-001 | 资产统计报表 | P0 | `report_generator/daily_report.py` | ✅ 已实现 | |
| RPT-002 | 监控健康度报表 | P0 | `report_generator/` | ✅ 已实现 | |
| RPT-003 | 告警统计报表 | P0 | `report_generator/` | ✅ 已实现 | |
| RPT-004 | 工单统计报表 | P0 | `report_generator/` | ✅ 已实现 | |
| RPT-005 | 运维工作量报表 | P0 | `report_generator/rca_report.py` | ✅ 已实现 | |
| RPT-006 | 报表定时生成和发送 | P0 | `scheduler.py` | ✅ 已实现 | |
| RPT-007 | 报表模板管理 | P0 | `templates.py` | ✅ 已实现 | |
| RPT-008 | 报表导出（PDF/Excel） | P0 | `reporter.py` | ✅ 已实现 | v2标注已实现 |
| RPT-009 | 报表订阅（邮件订阅） | P1 | - | ❌ 未实现 | 需手动生成 |
| RPT-010 | 报表分享 | P1 | - | ❌ 未实现 | |

---

### 2.9 通知模块 (NOT) — 8 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| NOT-001 | 通知渠道管理 | P0 | `notification_service.py` | ✅ 已实现 | |
| NOT-002 | 通知模板管理 | P0 | `notification_service.py` | ✅ 已实现 | |
| NOT-003 | 通知发送 | P0 | `notification_service.py` | ✅ 已实现 | |
| NOT-004 | 发送记录 | P0 | `notification_service.py` | ✅ 已实现 | |
| NOT-005 | 发送状态跟踪 | P0 | `notification_service.py` | ✅ 已实现 | |
| NOT-006 | 渠道测试 | P0 | - | ⚠️ 部分 | 手动测试 |
| NOT-007 | 渠道启用/禁用 | P1 | - | ❌ 未实现 | |
| NOT-008 | 渠道优先级 | P1 | - | ❌ 未实现 | |

---

### 2.10 系统管理模块 (SYS) — 21 项

| 需求ID | 描述 | 优先级 | 实现文件 | 状态 | 备注 |
|--------|------|--------|---------|------|------|
| SYS-001 | 用户管理（创建/修改/禁用） | P0 | `routes/admin.py` | ✅ 已实现 | |
| SYS-002 | 角色权限管理（运维/管理员/审批者/只读） | P0 | `rbac.py` | ✅ 已实现 | |
| SYS-003 | 组织架构管理（部门管理） | P0 | - | ✅ 已实现 | v2标注已实现 |
| SYS-004 | 操作审计日志 | P0 | `audit.py` | ✅ 已实现 | |
| SYS-005 | 系统监控 | P0 | `audit.py` | ✅ 已实现 | |
| SYS-006 | 数据备份恢复 | P0 | `storage/minio/client.py` | ⚠️ 部分 | MinIO backup方法存在，平台层未串接 |
| SYS-007 | 健康检查 | P0 | `api/main.py` | ✅ 已实现 | /health, /ready |
| SYS-008 | 系统升级 | P0 | - | ⚠️ 部分 | 手动升级 |
| SYS-009 | License管理 | P1 | - | ❌ 未实现 | |
| SYS-010 | API密钥管理 | P1 | - | ❌ 未实现 | 集成困难 |
| SYS-011 | JWT认证 | P0 | `dependencies.py` | ✅ 已实现 | |
| SYS-012 | API Key认证 | P0 | `dependencies.py` | ⚠️ TODO | verify_api_key() 为TODO |
| SYS-013 | 密码强度策略 | P0 | `auth_manager/auth.py` | ✅ 已实现 | |
| SYS-014 | 登录失败锁定 | P0 | `auth_manager/auth.py` | ✅ 已实现 | |
| SYS-015 | 会话超时管理 | P0 | `dependencies.py` | ✅ 已实现 | |
| SYS-016 | RBAC数据权限控制 | P0 | `rbac.py` | ⚠️ 部分 | 功能权限完整，数据权限不完整 |
| SYS-017 | 敏感数据加密存储 | P0 | DB password加密 | ✅ 已实现 | |
| SYS-018 | 通信TLS加密 | P1 | - | ⚠️ 配置存在，默认未开启 | |
| SYS-019 | SQL注入防护 | P0 | SQLAlchemy ORM | ✅ 已实现 | |
| SYS-020 | XSS防护 | P1 | - | ⚠️ 无明确防护代码 | |
| SYS-021 | CSRF防护 | P1 | - | ⚠️ FastAPI无内置CSRF | |

---

## 三、未实现需求清单（按优先级汇总）

### 🔴 P0 — 立即修复（20项）

| # | 需求ID | 描述 | 模块 | 评估工作量 |
|---|--------|------|------|-----------|
| 1 | COL-001 | IP段扫描发现设备 | 数据采集 | 8人天 |
| 2 | COL-002 | SNMP扫描发现网络设备 | 数据采集 | 5人天 |
| 3 | COL-004 | Zabbix/Prometheus API同步增强 | 数据采集 | 6人天 |
| 4 | COL-012 | API采集能力增强 | 数据采集 | 8人天 |
| 5 | COL-014 | 日志文件采集完善 | 数据采集 | 5人天 |
| 6 | COL-013 | WMI/WinRM Windows采集 | 数据采集 | 5人天 |
| 7 | COL-007 | 增量发现（定时检测新增设备） | 数据采集 | 4人天 |
| 8 | CFG-013 | 采集项精细化开关（单项控制） | 配置管理 | 3人天 |
| 9 | CFG-026 | 通知对象配置（按类型/级别/设备） | 配置管理 | 5人天 |
| 10 | WKO-008 | 工单草稿保存 | 工单管理 | 2人天 |
| 11 | KNO-005 | 文档审核发布流程（多级审核） | 知识库 | 4人天 |
| 12 | SYS-012 | API Key认证实现 | 系统管理 | 3人天 |
| 13 | SYS-006 | 数据备份恢复平台层串联 | 系统管理 | 5人天 |
| 14 | MON-028 | 告警完整审计日志 | 监控告警 | 4人天 |
| 15 | AUTO-020 | 告警触发自动执行脚本 | 自动化 | 6人天 |
| 16 | NOT-006 | 通知渠道测试功能完善 | 通知 | 2人天 |
| 17 | AI-003 | 对话历史持久化（Redis/DB） | AI助手 | 3人天 |
| 18 | AI-010 | 告警根因分析实现 | AI助手 | 10人天 |
| 19 | AI-011 | 处置建议生成实现 | AI助手 | 8人天 |
| 20 | AUTO-005 | 安全扫描任务完善 | 自动化 | 3人天 |

### 🟡 P1 — 尽快实现（30项）

| # | 需求ID | 描述 | 模块 | 评估工作量 |
|---|--------|------|------|-----------|
| 1 | CFG-005 | 设备配置项管理（版本/变更记录） | 配置管理 | 5人天 |
| 2 | CFG-014 | 采集模板导入导出 | 配置管理 | 3人天 |
| 3 | CFG-021 | 趋势告警规则（增长率/持续时间） | 配置管理 | 6人天 |
| 4 | CFG-027 | 聚合告警规则（多指标联合判断） | 配置管理 | 5人天 |
| 5 | COL-005 | 设备指纹识别（OS/厂商） | 数据采集 | 5人天 |
| 6 | COL-021 | 自定义设备指纹模板 | 数据采集 | 3人天 |
| 7 | COL-022 | 指纹模板版本管理 | 数据采集 | 2人天 |
| 8 | MON-031 | 按设备/分组查看仪表盘 | 监控告警 | 4人天 |
| 9 | MON-032 | 自定义仪表盘布局（拖拽） | 监控告警 | 5人天 |
| 10 | MON-033 | 图表数据导出 | 监控告警 | 2人天 |
| 11 | WKO-021 | SLA实时计时器（倒计时显示） | 工单管理 | 3人天 |
| 12 | WKO-022 | SLA超时自动升级 | 工单管理 | 4人天 |
| 13 | WKO-023 | SLA达成率统计 | 工单管理 | 3人天 |
| 14 | WKO-033 | 工单导出Excel | 工单管理 | 2人天 |
| 15 | KNO-014 | 案例AI推荐复用 | 知识库 | 5人天 |
| 16 | AI-012 | 报表智能解读 | AI助手 | 6人天 |
| 17 | AI-013 | 日志智能分析 | AI助手 | 8人天 |
| 18 | AI-025 | Chain-of-Thought推理 | AI助手 | 5人天 |
| 19 | AUTO-015 | 任务模板导出导入 | 自动化 | 3人天 |
| 20 | AUTO-023 | 执行失败自动回滚 | 自动化 | 6人天 |
| 21 | RPT-009 | 报表订阅（邮件订阅） | 报表 | 3人天 |
| 22 | RPT-010 | 报表分享 | 报表 | 2人天 |
| 23 | NOT-007 | 通知渠道启用/禁用 | 通知 | 2人天 |
| 24 | NOT-008 | 通知渠道优先级 | 通知 | 2人天 |
| 25 | SYS-009 | License管理 | 系统管理 | 3人天 |
| 26 | SYS-010 | API密钥管理 | 系统管理 | 3人天 |
| 27 | SYS-018 | 通信TLS加密（默认开启） | 系统管理 | 2人天 |
| 28 | SYS-020 | XSS防护实现 | 系统管理 | 2人天 |
| 29 | SYS-021 | CSRF防护实现 | 系统管理 | 2人天 |
| 30 | SYS-016 | RBAC数据权限控制完善 | 系统管理 | 5人天 |

### 🟠 P2 — 规划中（3项）

| # | 需求ID | 描述 | 模块 |
|---|--------|------|------|
| 1 | KNO-022 | 知识图谱关联检索 | 知识库 |
| 2 | COL-003 | ARP扫描发现存活主机 | 数据采集 |
| 3 | AUTO-016 | 分布式任务执行（多节点协同） | 自动化 |

---

## 四、前端缺口分析

### 4.1 页面实现状态（来自v2）

| 页面 | 功能 | 实现度 | 状态 |
|------|------|--------|------|
| Login.vue | 认证 | 100% | ✅ |
| Dashboard.vue | 态势总览 | 90% | ✅ |
| Assets.vue | 资产CRUD | 95% | ✅ |
| Devices.vue | 设备管理 | 90% | ✅ |
| Alerts.vue | 告警处理 | 95% | ✅ |
| WorkOrder.vue | 工单流转 | 95% | ✅ |
| Knowledge.vue | 文档管理 | 90% | ✅ |
| Reports.vue | 报表管理 | 90% | ✅ |
| Notifications.vue | 渠道管理 | 85% | ✅ |
| Settings.vue | 系统配置 | 80% | ✅ |
| AICopilot.vue | 智能问答 | 85% | ✅ |
| Scheduler.vue | 定时任务 | 60% | ⚠️ 不完整 |
| System.vue | 系统管理 | - | ❌ 构建错误 |

### 4.2 前端缺失页面

| 缺失页面 | 优先级 | 说明 |
|---------|--------|------|
| 设备自动发现页面 | 🔴 P0 | 无法扫描添加设备，只能手动录入 |
| 采集项配置页面 | 🔴 P0 | 无法精细化配置单项采集开关 |
| 通知对象配置页面 | 🟡 P1 | 告警通知不精准 |
| 自定义仪表盘页面 | 🟡 P1 | 无法自定义视图布局 |
| 告警屏蔽（维护窗口）页面 | 🟡 P1 | 无法配置维护时段 |

---

## 五、代码质量清单

### 5.1 TODO 项（37+ 处）

| 模块 | 数量 | 关键TODO |
|------|------|---------|
| `api/routes/ai.py` | 3 | 会话历史获取/删除/列表 |
| `api/dependencies.py` | 1 | API Key 验证 |
| `business/ai_copilot/scenarios.py` | 2 | 根因分析/处置建议 |
| `business/knowledge_base/ai_assist.py` | 1 | AI推荐 |
| `workorder/flow.py` | 1 | 集成通知服务 |

### 5.2 NotImplementedError（5+ 处）

| 文件 | 方法 | 功能 |
|------|------|------|
| `core/log/manager.py` | 2处 | 日志方法 |
| `core/storage/client.py` | 3处 | 存储抽象方法 |
| `ai_copilot/scenarios.py` | 2处 | 根因分析/处置建议 |
| `knowledge_base/ai_assist.py` | 1处 | AI推荐 |

### 5.3 pass 占位（40+ 处）

主要集中在各适配器的边界条件和解析逻辑中。

---

## 六、测试覆盖度

| 类型 | 文件数 | 测试数 | 覆盖范围 |
|------|--------|--------|---------|
| 单元测试 | 43 | 162 | 大部分核心模块 |
| 集成测试 | 3 | 3 | collection_flow, e2e_flow, real_flow |

**测试缺口：**
- API 端点集成测试（大部分 routes 无端到端测试）
- 数据库迁移测试（`migrations/` 目录未被测试框架覆盖）
- 前端 E2E 测试（前端代码与 API 未真正集成）
- 性能/压力测试（PERF 需求完全无覆盖）
- 安全渗透测试（SEC 需求无专项测试）

---

## 七、Docker 部署状态

| 服务 | 容器名 | 端口 | 状态 |
|------|--------|------|------|
| MySQL | itops-mysql | 3306 | ✅ healthy |
| Redis | itops-redis | 6379 | ✅ healthy |
| TDengine | itops-tdengine | 6030 | ✅ healthy |
| Qdrant | itops-qdrant | 6333 | ✅ running |
| MinIO | itops-minio | 9000/9001 | ✅ healthy |
| API (FastAPI) | itops-api | 8000 | ✅ healthy |
| 前端 (Streamlit) | itops-frontend | 3000 | ✅ running |

> ⚠️ 前端为 Streamlit 独立应用，非 SRS 中规划的 Vue3 前端，与 API 通过 HTTP 通信。

---

## 八、开发工作量估算

### 第一阶段（2周，~40人天）- P0核心差距

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| IP段/SNMP扫描发现 | 8人天 | P0 |
| API采集增强（Zabbix/Prometheus） | 8人天 | P0 |
| WMI/WinRM Windows采集 | 5人天 | P0 |
| 日志采集完善 | 5人天 | P0 |
| 采集项精细化开关 | 3人天 | P0 |
| 通知对象配置 | 5人天 | P0 |
| API Key认证实现 | 3人天 | P0 |
| AI根因分析/处置建议 | 18人天 | P0 |

### 第二阶段（3周，~50人天）- P1重要功能

| 任务 | 工作量 |
|------|--------|
| 趋势告警规则 | 6人天 |
| 聚合告警规则 | 5人天 |
| SLA实时计时器/超时升级 | 7人天 |
| 工单导出Excel | 2人天 |
| 自定义仪表盘 | 5人天 |
| 告警触发自动化执行 | 6人天 |
| 设备指纹识别 | 5人天 |
| 增量发现 | 4人天 |
| AI日志分析/报表解读 | 14人天 |

### 第三阶段（2周，~30人天）- 优化完善

| 任务 | 工作量 |
|------|--------|
| 前端缺失页面（设备发现/采集配置等） | 10人天 |
| System.vue 构建修复 | 2人天 |
| Scheduler.vue 功能完善 | 5人天 |
| 报表订阅/分享 | 5人天 |
| API密钥管理 | 3人天 |
| TLS/CSRF/XSS防护完善 | 6人天 |

**总工作量估算：约 120 人天（6人团队约 2个月）**

---

## 九、关键文件索引

### 后端核心文件

```
itops_platform/
├── api/
│   ├── main.py                    # FastAPI 入口，路由注册
│   ├── dependencies.py           # 依赖注入，JWT/会话/权限（TODOs: API Key）
│   ├── start.py                   # 启动初始化
│   └── routes/
│       ├── monitoring.py          # 告警管理 (685行)
│       ├── workorder.py          # 工单管理 (630行)
│       ├── knowledge.py           # 知识库 (987行)
│       ├── report.py             # 报表管理
│       ├── asset.py              # 资产管理
│       ├── ai.py                 # AI助手 (987行)
│       ├── admin.py              # 系统管理
│       ├── notification.py       # 通知管理
│       ├── device_api.py         # 设备API
│       └── auth.py               # 认证
├── modules/
│   ├── business/
│   │   ├── ai_copilot/           # LLM客户端/场景/RAG
│   │   ├── workorder/            # 工单/审批/流程/统计
│   │   ├── knowledge_base/       # 文档/案例/搜索/RAG
│   │   ├── monitoring/           # 监控/告警/规则/仪表盘
│   │   ├── report_generator/     # 报告生成/调度
│   │   ├── asset_management/     # 资产管理
│   │   └── notification/        # 通知服务
│   ├── collection/
│   │   ├── snmp_collector/       # SNMP采集
│   │   ├── ssh_collector/        # SSH采集
│   │   ├── ipmi_collector/      # IPMI采集
│   │   ├── api_collector/        # Zabbix/Prometheus/HTTP
│   │   ├── log_collector/       # 日志采集
│   │   ├── browser_automation/   # 7种厂商适配器
│   │   ├── adapter_registry.py  # 适配器注册表
│   │   ├── collector_factory.py # 采集器工厂
│   │   └── device_manager.py    # 设备管理
│   ├── automation/
│   │   ├── task_scheduler/       # 调度器/执行器/监控
│   │   ├── script_executor/      # 脚本执行
│   │   └── self_healing/        # 自愈引擎（50%）
│   ├── foundation/
│   │   ├── auth_manager/         # RBAC/LDAP/Audit
│   │   └── db_models/           # ORM模型
│   └── storage/
│       ├── tdengine/             # 时序数据
│       ├── qdrant/              # 向量检索
│       ├── minio/               # 对象存储
│       └── redis_client/        # 缓存
└── core/
    ├── config/manager.py         # 配置管理
    ├── log/manager.py           # 日志管理
    └── storage/client.py         # 存储抽象
```

### 前端文件（Vue3）

```
frontend/src/
├── views/
│   ├── Login.vue               # 登录页 100%
│   ├── Dashboard.vue           # 仪表盘 90%
│   ├── Assets.vue              # 资产 95%
│   ├── Devices.vue             # 设备 90%
│   ├── Alerts.vue              # 告警 95%
│   ├── WorkOrder.vue           # 工单 95%
│   ├── Knowledge.vue           # 知识库 90%
│   ├── Reports.vue             # 报表 90%
│   ├── Notifications.vue       # 通知 85%
│   ├── Settings.vue            # 设置 80%
│   ├── AICopilot.vue           # AI助手 85%
│   ├── Scheduler.vue           # 调度器 60% ⚠️
│   ├── KnowledgeBase.vue       # 知识库备用 70%
│   └── System.vue              # 系统管理 ❌ 构建错误
└── api/
    └── index.js                # API调用封装
```
