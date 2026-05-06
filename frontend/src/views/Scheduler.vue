<template>
  <div class="scheduler-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">
          任务调度中心
        </h2>
        <p class="page-subtitle">
          自动化任务编排与管理，支持Cron表达式定时执行
        </p>
      </div>
      <div class="page-header-actions">
        <el-button @click="showSchedulerDialog = true">
          <el-icon><Setting /></el-icon>
          调度配置
        </el-button>
        <el-button
          type="primary"
          @click="handleCreateTask"
        >
          <el-icon><Plus /></el-icon>
          创建任务
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div 
        v-for="(stat, index) in statsData" 
        :key="stat.key"
        class="stat-card"
        :style="{ animationDelay: `${index * 0.08}s` }"
      >
        <div
          class="stat-icon"
          :class="stat.key"
        >
          <el-icon><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ stat.value }}
          </div>
          <div class="stat-title">
            {{ stat.title }}
          </div>
        </div>
        <div
          v-if="stat.key === 'running'"
          class="stat-pulse"
        />
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-select
          v-model="typeFilter"
          placeholder="任务类型"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="数据采集"
            value="collection"
          >
            <div class="type-option">
              <span class="type-dot collection" />
              <span>数据采集</span>
            </div>
          </el-option>
          <el-option
            label="报告生成"
            value="report"
          >
            <div class="type-option">
              <span class="type-dot report" />
              <span>报告生成</span>
            </div>
          </el-option>
          <el-option
            label="告警检查"
            value="alert_check"
          >
            <div class="type-option">
              <span class="type-dot alert_check" />
              <span>告警检查</span>
            </div>
          </el-option>
          <el-option
            label="备份任务"
            value="backup"
          >
            <div class="type-option">
              <span class="type-dot backup" />
              <span>备份任务</span>
            </div>
          </el-option>
        </el-select>

        <el-select
          v-model="statusFilter"
          placeholder="任务状态"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="运行中"
            value="running"
          >
            <div class="status-option">
              <span class="status-dot running" />
              <span>运行中</span>
            </div>
          </el-option>
          <el-option
            label="已暂停"
            value="paused"
          >
            <div class="status-option">
              <span class="status-dot paused" />
              <span>已暂停</span>
            </div>
          </el-option>
          <el-option
            label="已完成"
            value="completed"
          >
            <div class="status-option">
              <span class="status-dot completed" />
              <span>已完成</span>
            </div>
          </el-option>
          <el-option
            label="执行失败"
            value="failed"
          >
            <div class="status-option">
              <span class="status-dot failed" />
              <span>执行失败</span>
            </div>
          </el-option>
        </el-select>

        <el-input
          v-model="searchText"
          placeholder="搜索任务名称..."
          style="width: 200px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <div class="filter-right">
        <el-button
          text
          :loading="loading"
          @click="handleRefresh"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="tasksData"
        stripe
        class="tasks-table"
        row-key="id"
      >
        <el-table-column
          label="任务信息"
          min-width="220"
        >
          <template #default="{ row }">
            <div class="task-info-cell">
              <div
                class="task-icon"
                :class="row.type"
              >
                <el-icon><component :is="getTypeIcon(row.type)" /></el-icon>
              </div>
              <div class="task-text">
                <div class="task-name">
                  {{ row.name }}
                </div>
                <div class="task-desc">
                  {{ row.description }}
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="任务类型"
          width="110"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getTypeTagType(row.type)"
              effect="light"
            >
              {{ getTypeText(row.type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="调度规则"
          width="160"
        >
          <template #default="{ row }">
            <div class="cron-cell">
              <span class="cron-text">{{ row.cron }}</span>
              <el-tooltip
                content="查看调度说明"
                placement="top"
              >
                <el-button
                  text
                  size="small"
                  @click="showCronHelp(row.cron)"
                >
                  <el-icon><QuestionFilled /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="下次执行"
          width="160"
        >
          <template #default="{ row }">
            <span
              class="next-run-text"
              :class="{ 'soon': isSoon(row.nextRun) }"
            >
              {{ row.nextRun }}
            </span>
          </template>
        </el-table-column>

        <el-table-column
          label="上次执行"
          width="160"
        >
          <template #default="{ row }">
            <span class="last-run-text">{{ row.lastRun }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="执行耗时"
          width="100"
        >
          <template #default="{ row }">
            <span
              v-if="row.duration"
              class="duration-text"
            >{{ row.duration }}</span>
            <span
              v-else
              class="duration-text muted"
            >-</span>
          </template>
        </el-table-column>

        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <div class="status-cell">
              <span
                class="status-indicator"
                :class="row.status"
              />
              <el-tag
                size="small"
                :type="getStatusTagType(row.status)"
                effect="light"
              >
                {{ getStatusText(row.status) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="220"
          fixed="right"
        >
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip
                v-if="row.status !== 'running'"
                content="立即执行"
                placement="top"
              >
                <el-button
                  text
                  type="success"
                  size="small"
                  @click="handleRunNow(row)"
                >
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                v-if="row.status === 'running'"
                content="暂停任务"
                placement="top"
              >
                <el-button
                  text
                  type="warning"
                  size="small"
                  @click="handlePause(row)"
                >
                  <el-icon><VideoPause /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                v-if="row.status === 'paused'"
                content="恢复任务"
                placement="top"
              >
                <el-button
                  text
                  type="success"
                  size="small"
                  @click="handleResume(row)"
                >
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                content="执行日志"
                placement="top"
              >
                <el-button
                  text
                  type="primary"
                  size="small"
                  @click="handleViewLogs(row)"
                >
                  <el-icon><List /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                content="编辑任务"
                placement="top"
              >
                <el-button
                  text
                  size="small"
                  @click="handleEditTask(row)"
                >
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleTaskCommand(cmd, row)"
              >
                <el-button
                  text
                  size="small"
                >
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="run">
                      立即执行
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="!row.enabled"
                      command="enable"
                    >
                      启用任务
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="row.enabled"
                      command="disable"
                    >
                      禁用任务
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="logs"
                      divided
                    >
                      查看日志
                    </el-dropdown-item>
                    <el-dropdown-item command="delete">
                      删除任务
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="table-footer">
        <div class="table-info">
          共 {{ total }} 个任务，{{ runningCount }} 个运行中
        </div>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 创建/编辑任务对话框 -->
    <el-dialog 
      v-model="showTaskDialog" 
      :title="isEdit ? '编辑任务' : '创建任务'" 
      width="650px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="taskFormRef"
        :model="taskForm"
        label-width="100px"
        :rules="formRules"
      >
        <el-form-item
          label="任务名称"
          prop="name"
        >
          <el-input
            v-model="taskForm.name"
            placeholder="请输入任务名称"
            maxlength="50"
          />
        </el-form-item>

        <el-form-item
          label="任务类型"
          prop="type"
        >
          <el-select
            v-model="taskForm.type"
            placeholder="选择任务类型"
            style="width: 100%"
          >
            <el-option
              label="数据采集"
              value="collection"
            >
              <div class="type-option">
                <span class="type-dot collection" />
                <span>数据采集</span>
              </div>
            </el-option>
            <el-option
              label="报告生成"
              value="report"
            >
              <div class="type-option">
                <span class="type-dot report" />
                <span>报告生成</span>
              </div>
            </el-option>
            <el-option
              label="告警检查"
              value="alert_check"
            >
              <div class="type-option">
                <span class="type-dot alert_check" />
                <span>告警检查</span>
              </div>
            </el-option>
            <el-option
              label="备份任务"
              value="backup"
            >
              <div class="type-option">
                <span class="type-dot backup" />
                <span>备份任务</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item
          label="调度规则"
          prop="cron"
        >
          <div class="cron-input-group">
            <el-input
              v-model="taskForm.cron"
              placeholder="* * * * *"
              style="width: 180px"
            />
            <span class="cron-hint">分 时 日 月 周</span>
            <el-popover
              placement="bottom"
              :width="360"
              trigger="hover"
            >
              <template #reference>
                <el-button
                  type="primary"
                  link
                >
                  <el-icon><QuestionFilled /></el-icon>
                  常用规则
                </el-button>
              </template>
              <div class="cron-presets">
                <div
                  class="preset-item"
                  @click="taskForm.cron = '*/5 * * * *'"
                >
                  <span class="preset-cron">*/5 * * * *</span>
                  <span class="preset-desc">每5分钟</span>
                </div>
                <div
                  class="preset-item"
                  @click="taskForm.cron = '0 * * * *'"
                >
                  <span class="preset-cron">0 * * * *</span>
                  <span class="preset-desc">每小时整点</span>
                </div>
                <div
                  class="preset-item"
                  @click="taskForm.cron = '0 0 * * *'"
                >
                  <span class="preset-cron">0 0 * * *</span>
                  <span class="preset-desc">每天零点</span>
                </div>
                <div
                  class="preset-item"
                  @click="taskForm.cron = '0 8 * * *'"
                >
                  <span class="preset-cron">0 8 * * *</span>
                  <span class="preset-desc">每天早上8点</span>
                </div>
                <div
                  class="preset-item"
                  @click="taskForm.cron = '0 0 * * 0'"
                >
                  <span class="preset-cron">0 0 * * 0</span>
                  <span class="preset-desc">每周一零点</span>
                </div>
                <div
                  class="preset-item"
                  @click="taskForm.cron = '0 0 1 * *'"
                >
                  <span class="preset-cron">0 0 1 * *</span>
                  <span class="preset-desc">每月1号零点</span>
                </div>
                <div
                  class="preset-item"
                  @click="taskForm.cron = '0 */2 * * *'"
                >
                  <span class="preset-cron">0 */2 * * *</span>
                  <span class="preset-desc">每2小时</span>
                </div>
              </div>
            </el-popover>
          </div>
        </el-form-item>

        <el-form-item
          label="执行命令"
          prop="command"
        >
          <el-input
            v-model="taskForm.command"
            type="textarea"
            :rows="3"
            placeholder="请输入要执行的命令或脚本路径"
          />
        </el-form-item>

        <el-form-item label="任务描述">
          <el-input
            v-model="taskForm.description"
            type="textarea"
            :rows="2"
            placeholder="任务描述（可选）"
          />
        </el-form-item>

        <el-form-item label="执行超时">
          <el-input-number
            v-model="taskForm.timeout"
            :min="0"
            :max="86400"
            placeholder="0表示不限制"
          />
          <span class="unit-label">秒</span>
        </el-form-item>

        <el-form-item label="是否启用">
          <el-switch v-model="taskForm.enabled" />
          <span class="enable-hint">{{ taskForm.enabled ? '任务将按调度规则自动执行' : '任务暂停执行' }}</span>
        </el-form-item>

        <el-form-item label="失败重试">
          <el-input-number
            v-model="taskForm.retry"
            :min="0"
            :max="10"
          />
          <span class="unit-label">次</span>
          <span class="retry-hint">执行失败后自动重试的次数</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTaskDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSubmitTask"
        >
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 执行日志抽屉 -->
    <el-drawer
      v-model="showLogsDrawer"
      :title="`执行日志 - ${currentTask?.name}`"
      size="800px"
    >
      <div
        v-if="currentTask"
        class="logs-container"
      >
        <div class="logs-toolbar">
          <div class="logs-info">
            <el-tag :type="getTypeTagType(currentTask.type)">
              {{ getTypeText(currentTask.type) }}
            </el-tag>
            <el-tag :type="getStatusTagType(currentTask.status)">
              {{ getStatusText(currentTask.status) }}
            </el-tag>
          </div>
          <div class="logs-actions">
            <el-select
              v-model="logLevelFilter"
              placeholder="日志级别"
              style="width: 120px"
              clearable
            >
              <el-option
                label="全部"
                value=""
              />
              <el-option
                label="INFO"
                value="info"
              />
              <el-option
                label="WARNING"
                value="warning"
              />
              <el-option
                label="ERROR"
                value="error"
              />
            </el-select>
            <el-button
              size="small"
              @click="handleClearLogs"
            >
              清空日志
            </el-button>
          </div>
        </div>

        <div class="logs-stats">
          <div class="log-stat">
            <span class="stat-label">总执行次数</span>
            <span class="stat-value">{{ taskLogs.length }}</span>
          </div>
          <div class="log-stat success">
            <span class="stat-label">成功</span>
            <span class="stat-value">{{ successCount }}</span>
          </div>
          <div class="log-stat error">
            <span class="stat-label">失败</span>
            <span class="stat-value">{{ errorCount }}</span>
          </div>
        </div>

        <div class="logs-terminal">
          <div class="terminal-header">
            <span class="terminal-dot error" />
            <span class="terminal-dot warning" />
            <span class="terminal-dot success" />
            <span class="terminal-title">{{ currentTask.name }} - 执行日志</span>
          </div>
          <div class="terminal-content">
            <div
              v-for="(log, index) in filteredLogs"
              :key="index"
              class="log-line"
              :class="'log-' + log.level"
            >
              <span class="log-time">[{{ log.time }}]</span>
              <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
            <div
              v-if="filteredLogs.length === 0"
              class="no-logs"
            >
              暂无执行日志
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 调度配置对话框 -->
    <el-dialog
      v-model="showSchedulerDialog"
      title="调度服务配置"
      width="500px"
    >
      <el-form label-width="120px">
        <el-form-item label="调度服务状态">
          <el-tag :type="schedulerStatus === 'running' ? 'success' : 'info'">
            {{ schedulerStatus === 'running' ? '运行中' : '已停止' }}
          </el-tag>
          <el-button
            type="primary"
            size="small"
            style="margin-left: 10px;"
            @click="toggleScheduler"
          >
            {{ schedulerStatus === 'running' ? '停止' : '启动' }}
          </el-button>
        </el-form-item>
        <el-form-item label="调度线程数">
          <el-input-number
            v-model="schedulerConfig.threads"
            :min="1"
            :max="20"
          />
        </el-form-item>
        <el-form-item label="任务超时时间">
          <el-input-number
            v-model="schedulerConfig.taskTimeout"
            :min="0"
            :max="3600"
          />
          <span style="margin-left: 8px; color: #909399;">秒</span>
        </el-form-item>
        <el-form-item label="日志保留天数">
          <el-input-number
            v-model="schedulerConfig.logRetention"
            :min="1"
            :max="365"
          />
          <span style="margin-left: 8px; color: #909399;">天</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSchedulerDialog = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          @click="saveSchedulerConfig"
        >
          保存配置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Plus, Setting, Edit, List, MoreFilled, QuestionFilled,
  VideoPlay, VideoPause, DataLine, Document, Warning, CircleCheck, Clock, Timer
} from '@element-plus/icons-vue'

// 状态
const loading = ref(false)
const tasksData = ref([])
const showTaskDialog = ref(false)
const showLogsDrawer = ref(false)
const showSchedulerDialog = ref(false)
const isEdit = ref(false)
const currentTask = ref(null)
const taskFormRef = ref(null)

// 筛选
const typeFilter = ref('')
const statusFilter = ref('')
const searchText = ref('')
const logLevelFilter = ref('')

// 分页
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 调度配置
const schedulerStatus = ref('running')
const schedulerConfig = reactive({
  threads: 4,
  taskTimeout: 300,
  logRetention: 30
})

// 任务表单
const taskForm = reactive({
  name: '',
  type: 'collection',
  cron: '0 0 * * *',
  command: '',
  description: '',
  timeout: 0,
  enabled: true,
  retry: 0
})

// 表单验证
const formRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  cron: [{ required: true, message: '请输入调度规则', trigger: 'blur' }],
  command: [{ required: true, message: '请输入执行命令', trigger: 'blur' }]
}

// 统计
const statsData = reactive([
  { key: 'running', title: '运行中', value: 0, icon: 'VideoPlay' },
  { key: 'paused', title: '已暂停', value: 0, icon: 'Pause' },
  { key: 'completed', title: '已完成', value: 0, icon: 'CircleCheck' },
  { key: 'failed', title: '执行失败', value: 0, icon: 'Warning' }
])

const runningCount = computed(() => {
  return tasksData.value.filter(t => t.status === 'running').length
})

const successCount = computed(() => {
  return taskLogs.value.filter(l => l.level === 'info' && l.message.includes('成功')).length
})

const errorCount = computed(() => {
  return taskLogs.value.filter(l => l.level === 'error').length
})

// 日志
const taskLogs = ref([])
const filteredLogs = computed(() => {
  if (!logLevelFilter.value) return taskLogs.value
  return taskLogs.value.filter(l => l.level === logLevelFilter.value)
})

// 模拟任务数据
const mockTasks = [
  {
    id: 1, name: '服务器监控数据采集', type: 'collection', cron: '*/5 * * * *',
    nextRun: '2026-05-05 12:05:00', lastRun: '2026-05-05 12:00:00', duration: '12秒',
    status: 'running', command: '/scripts/collect_metrics.sh', description: '每5分钟采集服务器性能指标',
    enabled: true
  },
  {
    id: 2, name: '每日运维报告生成', type: 'report', cron: '0 8 * * *',
    nextRun: '2026-05-06 08:00:00', lastRun: '2026-05-05 08:00:00', duration: '45秒',
    status: 'completed', command: '/scripts/generate_report.py', description: '每天早上8点生成运维日报',
    enabled: true
  },
  {
    id: 3, name: '告警规则健康检查', type: 'alert_check', cron: '0 */30 * * *',
    nextRun: '2026-05-05 12:30:00', lastRun: '2026-05-05 12:00:00', duration: '8秒',
    status: 'running', command: '/scripts/check_alerts.sh', description: '每30分钟检查告警规则配置',
    enabled: true
  },
  {
    id: 4, name: '数据库定时备份', type: 'backup', cron: '0 2 * * *',
    nextRun: '2026-05-06 02:00:00', lastRun: '2026-05-05 02:00:00', duration: '120秒',
    status: 'completed', command: '/scripts/backup_db.sh', description: '每天凌晨2点备份数据库',
    enabled: false
  },
  {
    id: 5, name: '日志文件清理', type: 'collection', cron: '0 3 * * 0',
    nextRun: '2026-05-11 03:00:00', lastRun: '2026-05-04 03:00:00', duration: '失败',
    status: 'failed', command: '/scripts/cleanup_logs.sh', description: '每周日凌晨3点清理过期日志',
    enabled: true
  },
  {
    id: 6, name: '资产数据同步', type: 'collection', cron: '0 */4 * * *',
    nextRun: '2026-05-05 16:00:00', lastRun: '2026-05-05 12:00:00', duration: '25秒',
    status: 'running', command: '/scripts/sync_assets.py', description: '每4小时同步资产数据',
    enabled: true
  }
]

// 模拟日志数据
const mockLogs = [
  { time: '2026-05-05 12:00:00', level: 'info', message: '任务开始执行' },
  { time: '2026-05-05 12:00:01', level: 'info', message: '正在采集服务器性能指标...' },
  { time: '2026-05-05 12:00:05', level: 'info', message: '成功连接到服务器 (192.168.1.101)' },
  { time: '2026-05-05 12:00:08', level: 'info', message: '采集到 CPU: 45%, 内存: 62%, 磁盘: 55%' },
  { time: '2026-05-05 12:00:10', level: 'info', message: '成功连接到服务器 (192.168.1.102)' },
  { time: '2026-05-05 12:00:12', level: 'info', message: '采集到 CPU: 38%, 内存: 71%, 磁盘: 68%' },
  { time: '2026-05-05 12:00:15', level: 'warning', message: '服务器 192.168.1.103 连接超时' },
  { time: '2026-05-05 12:00:18', level: 'info', message: '数据上报到监控系统完成' },
  { time: '2026-05-05 12:00:19', level: 'info', message: '任务执行成功，共采集 15 台服务器指标' }
]

// 辅助函数
const getTypeText = (type) => {
  const texts = { collection: '数据采集', report: '报告生成', alert_check: '告警检查', backup: '备份任务' }
  return texts[type] || type
}

const getTypeIcon = (type) => {
  const icons = { collection: 'DataLine', report: 'Document', alert_check: 'Warning', backup: 'Clock' }
  return icons[type] || 'DataLine'
}

const getTypeTagType = (type) => {
  const types = { collection: 'primary', report: 'success', alert_check: 'warning', backup: 'info' }
  return types[type] || 'info'
}

const getStatusText = (status) => {
  const texts = { running: '运行中', paused: '已暂停', completed: '已完成', failed: '执行失败' }
  return texts[status] || status
}

const getStatusTagType = (status) => {
  const types = { running: 'success', paused: 'warning', completed: 'info', failed: 'danger' }
  return types[status] || 'info'
}

const isSoon = (nextRun) => {
  if (!nextRun || nextRun === '-') return false
  const diff = new Date(nextRun) - new Date()
  return diff > 0 && diff < 3600000 // 1小时内
}

const showCronHelp = (cron) => {
  ElMessage.info(`调度规则: ${cron}`)
}

// 加载任务数据
const loadTasks = async () => {
  loading.value = true
  try {
    tasksData.value = [...mockTasks]
    total.value = mockTasks.length
    updateStats()
  } catch (error) {
    console.error('Failed to load tasks:', error)
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  statsData[0].value = tasksData.value.filter(t => t.status === 'running').length
  statsData[1].value = tasksData.value.filter(t => t.status === 'paused').length
  statsData[2].value = tasksData.value.filter(t => t.status === 'completed').length
  statsData[3].value = tasksData.value.filter(t => t.status === 'failed').length
}

// 事件处理
const handleFilterChange = () => {
  currentPage.value = 1
  loadTasks()
}

const handleSearch = () => {
  currentPage.value = 1
  loadTasks()
}

const handleRefresh = () => {
  loadTasks()
  ElMessage.success('刷新成功')
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadTasks()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  loadTasks()
}

const handleCreateTask = () => {
  isEdit.value = false
  Object.assign(taskForm, {
    name: '', type: 'collection', cron: '0 0 * * *', command: '', description: '',
    timeout: 0, enabled: true, retry: 0
  })
  showTaskDialog.value = true
}

const handleEditTask = (task) => {
  isEdit.value = true
  Object.assign(taskForm, { ...task })
  showTaskDialog.value = true
}

const handleSubmitTask = async () => {
  if (!taskFormRef.value) return

  await taskFormRef.value.validate((valid) => {
    if (valid) {
      if (isEdit.value) {
        const idx = tasksData.value.findIndex(t => t.id === taskForm.id)
        if (idx !== -1) {
          tasksData.value[idx] = { ...tasksData.value[idx], ...taskForm }
        }
        ElMessage.success('任务修改成功')
      } else {
        const newTask = {
          id: mockTasks.length + 1,
          ...taskForm,
          status: taskForm.enabled ? 'paused' : 'paused',
          nextRun: '-',
          lastRun: '-',
          duration: ''
        }
        tasksData.value.unshift(newTask)
        total.value++
        updateStats()
        ElMessage.success('任务创建成功')
      }
      showTaskDialog.value = false
    }
  })
}

const handleRunNow = async (task) => {
  try {
    await ElMessageBox.confirm(`确定要立即执行任务「${task.name}」吗？`, '提示', { type: 'info' })
    task.status = 'running'
    ElMessage.success('任务已开始执行')
    setTimeout(() => {
      task.status = 'completed'
      task.lastRun = new Date().toLocaleString('zh-CN')
      task.duration = '18秒'
      updateStats()
    }, 3000)
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('执行失败')
  }
}

const handlePause = async (task) => {
  task.status = 'paused'
  updateStats()
  ElMessage.success('任务已暂停')
}

const handleResume = async (task) => {
  task.status = 'running'
  updateStats()
  ElMessage.success('任务已恢复')
}

const handleViewLogs = (task) => {
  currentTask.value = task
  taskLogs.value = [...mockLogs]
  showLogsDrawer.value = true
}

const handleClearLogs = () => {
  ElMessageBox.confirm('确定要清空所有日志吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    taskLogs.value = []
    ElMessage.success('日志已清空')
  }).catch(() => {})
}

const handleTaskCommand = (command, task) => {
  switch (command) {
    case 'run': handleRunNow(task); break
    case 'enable': 
      task.enabled = true
      ElMessage.success('任务已启用')
      break
    case 'disable': 
      task.enabled = false
      task.status = 'paused'
      updateStats()
      ElMessage.success('任务已禁用')
      break
    case 'logs': handleViewLogs(task); break
    case 'delete':
      ElMessageBox.confirm('确定要删除任务「' + task.name + '」吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        tasksData.value = tasksData.value.filter(t => t.id !== task.id)
        total.value--
        updateStats()
        ElMessage.success('任务已删除')
      }).catch(() => {})
      break
  }
}

const toggleScheduler = () => {
  schedulerStatus.value = schedulerStatus.value === 'running' ? 'stopped' : 'running'
  ElMessage.success(`调度服务已${schedulerStatus.value === 'running' ? '启动' : '停止'}`)
}

const saveSchedulerConfig = () => {
  ElMessage.success('调度服务配置已保存')
  showSchedulerDialog.value = false
}

// 初始化
onMounted(() => {
  loadTasks()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.scheduler-page {
  animation: fadeIn 0.3s ease;
}

// ========== 页面头部 ==========
.page-header {
  @include flex-between;
  margin-bottom: $spacing-xl;

  .page-header-left {
    .page-title {
      font-size: $font-size-xxl;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin: 0 0 4px 0;
    }

    .page-subtitle {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin: 0;
    }
  }

  .page-header-actions {
    display: flex;
    gap: $spacing-sm;
  }
}

// ========== 统计卡片 ==========
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-lg;
  background: $bg-container;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-sm;
  animation: slideInUp 0.4s ease-out backwards;
  transition: all 0.25s ease;
  overflow: hidden;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-base;
  }

  &.running .stat-icon {
    animation: pulse 2s infinite;
  }
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: $border-radius-md;
  @include flex-center;
  color: #fff;
  font-size: 24px;

  &.running { background: linear-gradient(135deg, #00b42a, #23c343); }
  &.paused { background: linear-gradient(135deg, #ff7d00, #ff9d00); }
  &.completed { background: linear-gradient(135deg, #165dff, #4080ff); }
  &.failed { background: linear-gradient(135deg, #f53f3f, #ff7875); }
}

.stat-content {
  flex: 1;

  .stat-value {
    font-size: $font-size-xxl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    line-height: 1.2;
  }

  .stat-title {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin-top: 2px;
  }
}

.stat-pulse {
  position: absolute;
  top: 0;
  right: 0;
  width: 80px;
  height: 80px;
  background: radial-gradient(circle, rgba($success, 0.2) 0%, transparent 70%);
  animation: pulse-wave 2s infinite;
}

// ========== 筛选工具栏 ==========
.filter-bar {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  background: $bg-container;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-lg;
  box-shadow: $shadow-sm;

  .filter-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    flex: 1;
  }

  .filter-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
}

.type-option, .status-option {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .type-dot, .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.collection { background: $primary; }
    &.report { background: $success; }
    &.alert_check { background: $warning; }
    &.backup { background: $info; }
    &.running { background: $success; box-shadow: 0 0 6px $success; }
    &.paused { background: $warning; }
    &.completed { background: $primary; }
    &.failed { background: $danger; }
  }
}

// ========== 表格 ==========
.table-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.tasks-table {
  :deep(.el-table__header th) {
    background: $bg-page !important;
    color: $text-secondary;
    font-weight: $font-weight-semibold;
  }
}

.task-info-cell {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.task-icon {
  width: 40px;
  height: 40px;
  border-radius: $border-radius-md;
  @include flex-center;
  font-size: 18px;
  color: #fff;
  flex-shrink: 0;

  &.collection { background: linear-gradient(135deg, $primary, #4080ff); }
  &.report { background: linear-gradient(135deg, $success, #23c343); }
  &.alert_check { background: linear-gradient(135deg, $warning, #ff9d00); }
  &.backup { background: linear-gradient(135deg, #86909c, #a6a8b6); }
}

.task-text {
  .task-name {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: 2px;
  }

  .task-desc {
    font-size: $font-size-xs;
    color: $text-secondary;
    @include multi-ellipsis(1);
  }
}

.cron-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .cron-text {
    font-family: 'Monaco', 'Consolas', monospace;
    font-size: $font-size-sm;
    background: $bg-page;
    padding: 4px 8px;
    border-radius: $border-radius-sm;
    color: $text-regular;
  }
}

.next-run-text, .last-run-text {
  font-size: $font-size-sm;
  color: $text-secondary;

  &.soon {
    color: $warning;
    font-weight: $font-weight-medium;
  }
}

.duration-text {
  font-size: $font-size-sm;
  color: $text-regular;

  &.muted {
    color: $text-placeholder;
  }
}

.status-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.running { background: $success; box-shadow: 0 0 6px $success; }
    &.paused { background: $warning; }
    &.completed { background: $primary; }
    &.failed { background: $danger; }
  }
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
}

// ========== 表格底部 ==========
.table-footer {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  border-top: 1px solid $border-light;

  .table-info {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

// ========== 表单 ==========
.cron-input-group {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.cron-hint {
  font-size: $font-size-xs;
  color: $text-placeholder;
}

.enable-hint, .retry-hint {
  margin-left: $spacing-md;
  font-size: $font-size-xs;
  color: $text-secondary;
}

.unit-label {
  margin-left: $spacing-sm;
  font-size: $font-size-sm;
  color: $text-secondary;
}

.cron-presets {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-sm;
  padding: $spacing-sm;

  .preset-item {
    display: flex;
    flex-direction: column;
    padding: $spacing-sm;
    background: $bg-page;
    border-radius: $border-radius-sm;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: $primary;
      color: #fff;
    }

    .preset-cron {
      font-family: 'Monaco', monospace;
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
    }

    .preset-desc {
      font-size: $font-size-xs;
      color: $text-secondary;
      margin-top: 2px;
    }

    &:hover .preset-desc {
      color: rgba(255, 255, 255, 0.8);
    }
  }
}

// ========== 日志 ==========
.logs-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.logs-toolbar {
  @include flex-between;
  margin-bottom: $spacing-lg;

  .logs-info {
    display: flex;
    gap: $spacing-sm;
  }

  .logs-actions {
    display: flex;
    gap: $spacing-sm;
  }
}

.logs-stats {
  display: flex;
  gap: $spacing-lg;
  margin-bottom: $spacing-lg;
  padding: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;

  .log-stat {
    display: flex;
    flex-direction: column;

    .stat-label {
      font-size: $font-size-xs;
      color: $text-secondary;
    }

    .stat-value {
      font-size: $font-size-lg;
      font-weight: $font-weight-bold;
      color: $text-primary;
    }

    &.success .stat-value { color: $success; }
    &.error .stat-value { color: $danger; }
  }
}

.logs-terminal {
  flex: 1;
  background: #1e1e1e;
  border-radius: $border-radius-md;
  overflow: hidden;
}

.terminal-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  background: #2d2d2d;
  border-bottom: 1px solid #3d3d3d;

  .terminal-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;

    &.error { background: #ff5f56; }
    &.warning { background: #ffbd2e; }
    &.success { background: #27c93f; }
  }

  .terminal-title {
    margin-left: $spacing-sm;
    font-size: $font-size-sm;
    color: #858585;
  }
}

.terminal-content {
  height: 400px;
  overflow-y: auto;
  padding: $spacing-md;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: $font-size-sm;
}

.log-line {
  display: flex;
  gap: $spacing-md;
  padding: 4px 0;
  color: #d4d4d4;

  .log-time {
    color: #858585;
    white-space: nowrap;
  }

  .log-level {
    font-weight: bold;
    white-space: nowrap;
  }

  .log-message {
    flex: 1;
    word-break: break-all;
  }

  &.log-info .log-level { color: #3794ff; }
  &.log-warning .log-level { color: #d6a844; }
  &.log-error .log-level { color: #f53f3f; }
}

.no-logs {
  @include flex-center;
  height: 200px;
  color: #858585;
  font-size: $font-size-sm;
}

// ========== 动画 ==========
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes pulse-wave {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; }
}

// ========== 响应式 ==========
@include respond-to('xl') {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@include respond-to('lg') {
  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-md;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>