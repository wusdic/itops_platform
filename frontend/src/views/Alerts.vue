<template>
  <div class="alerts-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">
          告警中心
        </h2>
        <p class="page-subtitle">
          实时监控告警，支持多级别告警管理和自动化处理
        </p>
      </div>
      <div class="page-header-actions">
        <el-button @click="handleExport">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button
          type="primary"
          @click="showRuleDialog = true"
        >
          <el-icon><Setting /></el-icon>
          告警规则
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div 
        v-for="(stat, index) in statsData" 
        :key="stat.key"
        class="stat-card"
        :class="{ active: stat.active }"
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
          v-if="stat.key === 'critical'"
          class="stat-pulse"
        />
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-input
          v-model="searchText"
          placeholder="搜索告警内容、主机..."
          style="width: 260px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button
              :icon="Search"
              @click="handleSearch"
            />
          </template>
        </el-input>

        <el-select
          v-model="levelFilter"
          placeholder="告警级别"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="严重"
            value="critical"
          >
            <div class="level-option">
              <span class="level-dot critical" />
              <span>严重</span>
            </div>
          </el-option>
          <el-option
            label="警告"
            value="warning"
          >
            <div class="level-option">
              <span class="level-dot warning" />
              <span>警告</span>
            </div>
          </el-option>
          <el-option
            label="信息"
            value="info"
          >
            <div class="level-option">
              <span class="level-dot info" />
              <span>信息</span>
            </div>
          </el-option>
        </el-select>

        <el-select
          v-model="statusFilter"
          placeholder="告警状态"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="未处理"
            value="active"
          >
            <span class="status-dot active" />
            未处理
          </el-option>
          <el-option
            label="已确认"
            value="acknowledged"
          >
            <span class="status-dot acknowledged" />
            已确认
          </el-option>
          <el-option
            label="已解决"
            value="resolved"
          >
            <span class="status-dot resolved" />
            已解决
          </el-option>
        </el-select>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
          @change="handleFilterChange"
        />
      </div>

      <div class="filter-right">
        <el-checkbox
          v-model="autoRefresh"
          @change="handleAutoRefresh"
        >
          自动刷新
        </el-checkbox>
        <el-select
          v-model="refreshInterval"
          style="width: 100px"
          :disabled="!autoRefresh"
        >
          <el-option
            label="10秒"
            :value="10"
          />
          <el-option
            label="30秒"
            :value="30"
          />
          <el-option
            label="1分钟"
            :value="60"
          />
        </el-select>
        <el-divider direction="vertical" />
        <el-button
          text
          :loading="loading"
          @click="handleRefresh"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 告警列表 -->
    <div class="alerts-container">
      <!-- 未处理告警高亮区 -->
      <div
        v-if="activeAlerts.length > 0"
        class="active-alerts"
      >
        <div class="active-header">
          <el-badge
            :value="activeAlerts.length"
            type="danger"
          >
            <span class="active-title">待处理告警</span>
          </el-badge>
          <el-button
            text
            size="small"
            @click="handleBatchAck"
          >
            <el-icon><Check /></el-icon>
            批量确认
          </el-button>
        </div>
        <div class="active-list">
          <div 
            v-for="alert in activeAlerts" 
            :key="alert.id"
            class="alert-card"
            :class="alert.level"
          >
            <div
              class="alert-indicator"
              :class="alert.level"
            />
            <div class="alert-main">
              <div class="alert-header">
                <el-tag
                  size="small"
                  :type="getLevelTagType(alert.level)"
                  effect="dark"
                >
                  {{ getLevelText(alert.level) }}
                </el-tag>
                <span class="alert-host">{{ alert.host }}</span>
                <span class="alert-time">{{ alert.time }}</span>
              </div>
              <div class="alert-message">
                {{ alert.message }}
              </div>
              <div class="alert-metrics">
                <span class="metric-tag">指标: {{ alert.metric }}</span>
                <span class="metric-value">当前值: {{ alert.value }}</span>
                <span class="metric-threshold">阈值: {{ alert.threshold }}</span>
              </div>
            </div>
            <div class="alert-actions">
              <el-button
                size="small"
                type="primary"
                @click="handleAcknowledge(alert)"
              >
                确认
              </el-button>
              <el-button
                size="small"
                @click="handleSilence(alert)"
              >
                静默
              </el-button>
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleAlertCommand(cmd, alert)"
              >
                <el-button
                  size="small"
                  text
                >
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="view">
                      <el-icon><View /></el-icon>
                      查看详情
                    </el-dropdown-item>
                    <el-dropdown-item command="create-ticket">
                      <el-icon><Document /></el-icon>
                      创建工单
                    </el-dropdown-item>
                    <el-dropdown-item command="link-knowledge">
                      <el-icon><Guide /></el-icon>
                      关联知识库
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="resolve"
                      divided
                    >
                      <el-icon><CircleCheck /></el-icon>
                      标记已解决
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </div>

      <!-- 全部告警表格 -->
      <div class="table-card">
        <el-table
          v-loading="loading"
          :data="alertsData"
          stripe
          class="alerts-table"
          row-key="id"
          @selection-change="handleSelectionChange"
        >
          <el-table-column
            type="selection"
            width="50"
          />

          <el-table-column
            label="级别"
            width="90"
          >
            <template #default="{ row }">
              <div class="level-cell">
                <span
                  class="level-indicator"
                  :class="row.level"
                />
                <el-tag
                  size="small"
                  :type="getLevelTagType(row.level)"
                  effect="light"
                >
                  {{ getLevelText(row.level) }}
                </el-tag>
              </div>
            </template>
          </el-table-column>

          <el-table-column
            label="告警信息"
            min-width="250"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <div class="alert-info-cell">
                <span class="alert-message">{{ row.message }}</span>
                <span class="alert-metric">{{ row.metric }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column
            label="主机"
            width="140"
          >
            <template #default="{ row }">
              <span class="host-text">{{ row.host }}</span>
            </template>
          </el-table-column>

          <el-table-column
            label="当前值"
            width="100"
          >
            <template #default="{ row }">
              <span
                class="value-text"
                :class="row.level"
              >
                {{ row.value }}
              </span>
            </template>
          </el-table-column>

          <el-table-column
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="getStatusTagType(row.status)"
                effect="light"
              >
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column
            label="发生时间"
            width="160"
            sortable
          >
            <template #default="{ row }">
              <span class="time-text">{{ row.time }}</span>
            </template>
          </el-table-column>

          <el-table-column
            label="持续时间"
            width="110"
          >
            <template #default="{ row }">
              <span
                class="duration-text"
                :class="{ active: row.status === 'active' }"
              >
                {{ row.duration }}
              </span>
            </template>
          </el-table-column>

          <el-table-column
            label="操作"
            width="160"
            fixed="right"
          >
            <template #default="{ row }">
              <div class="action-buttons">
                <el-tooltip
                  v-if="row.status === 'active'"
                  content="确认告警"
                  placement="top"
                >
                  <el-button
                    text
                    type="primary"
                    size="small"
                    @click="handleAcknowledge(row)"
                  >
                    <el-icon><Check /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip
                  content="查看详情"
                  placement="top"
                >
                  <el-button
                    text
                    type="primary"
                    size="small"
                    @click="handleViewDetail(row)"
                  >
                    <el-icon><View /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip
                  content="处理记录"
                  placement="top"
                >
                  <el-button
                    text
                    size="small"
                    @click="handleViewHistory(row)"
                  >
                    <el-icon><Clock /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-dropdown
                  trigger="click"
                  @command="(cmd) => handleAlertCommand(cmd, row)"
                >
                  <el-button
                    text
                    size="small"
                  >
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="view">
                        查看详情
                      </el-dropdown-item>
                      <el-dropdown-item command="silence">
                        静默此告警
                      </el-dropdown-item>
                      <el-dropdown-item command="create-ticket">
                        创建工单
                      </el-dropdown-item>
                      <el-dropdown-item command="link-knowledge">
                        关联知识库
                      </el-dropdown-item>
                      <el-dropdown-item
                        command="resolve"
                        divided
                      >
                        标记已解决
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
            共 {{ total }} 条记录，待处理 {{ activeCount }} 条
          </div>
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            layout="sizes, prev, pager, next, total"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>

    <!-- 告警详情抽屉 -->
    <el-drawer
      v-model="showDetailDrawer"
      :title="currentAlert?.message"
      size="650px"
    >
      <div
        v-if="currentAlert"
        class="alert-detail"
      >
        <div
          class="detail-header"
          :class="currentAlert.level"
        >
          <el-tag
            :type="getLevelTagType(currentAlert.level)"
            size="large"
            effect="dark"
          >
            {{ getLevelText(currentAlert.level) }}
          </el-tag>
          <el-tag
            :type="getStatusTagType(currentAlert.status)"
            size="large"
          >
            {{ getStatusText(currentAlert.status) }}
          </el-tag>
        </div>

        <el-descriptions
          :column="2"
          border
          class="detail-descriptions"
        >
          <el-descriptions-item label="告警主机">
            {{ currentAlert.host }}
          </el-descriptions-item>
          <el-descriptions-item label="监控指标">
            {{ currentAlert.metric }}
          </el-descriptions-item>
          <el-descriptions-item label="当前值">
            <span
              class="value-text large"
              :class="currentAlert.level"
            >{{ currentAlert.value }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="阈值">
            {{ currentAlert.threshold }}
          </el-descriptions-item>
          <el-descriptions-item
            label="发生时间"
            :span="2"
          >
            {{ currentAlert.time }}
          </el-descriptions-item>
          <el-descriptions-item
            label="持续时间"
            :span="2"
          >
            {{ currentAlert.duration }}
          </el-descriptions-item>
          <el-descriptions-item
            label="告警详情"
            :span="2"
          >
            {{ currentAlert.message }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">
          处理记录
        </el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="(item, index) in currentAlert.history"
            :key="index"
            :timestamp="item.time"
            :type="item.type"
          >
            <p>{{ item.action }}</p>
            <p class="history-operator">
              {{ item.operator }}
            </p>
          </el-timeline-item>
        </el-timeline>

        <el-divider content-position="left">
          处理操作
        </el-divider>
        <div class="detail-actions">
          <el-button
            v-if="currentAlert.status === 'active'"
            type="primary"
            @click="handleAcknowledge(currentAlert)"
          >
            确认告警
          </el-button>
          <el-button @click="handleCreateTicket(currentAlert)">
            创建工单
          </el-button>
          <el-button @click="handleSilence(currentAlert)">
            静默告警
          </el-button>
          <el-button
            type="success"
            @click="handleResolve(currentAlert)"
          >
            标记已解决
          </el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 告警规则配置对话框 -->
    <el-dialog
      v-model="showRuleDialog"
      title="告警规则配置"
      width="700px"
    >
      <el-form
        :model="ruleForm"
        label-width="100px"
      >
        <el-form-item label="规则名称">
          <el-input
            v-model="ruleForm.name"
            placeholder="请输入规则名称"
          />
        </el-form-item>
        <el-form-item label="监控指标">
          <el-select
            v-model="ruleForm.metric"
            style="width: 100%"
          >
            <el-option
              label="CPU使用率"
              value="cpu"
            />
            <el-option
              label="内存使用率"
              value="memory"
            />
            <el-option
              label="磁盘使用率"
              value="disk"
            />
            <el-option
              label="网络延迟"
              value="ping"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值条件">
          <el-row :gutter="10">
            <el-col :span="6">
              <el-select v-model="ruleForm.operator">
                <el-option
                  label="大于"
                  value=">"
                />
                <el-option
                  label="小于"
                  value="<"
                />
                <el-option
                  label="等于"
                  value="="
                />
              </el-select>
            </el-col>
            <el-col :span="8">
              <el-input-number
                v-model="ruleForm.threshold"
                :min="0"
                :max="100"
              />
            </el-col>
            <el-col :span="4">
              <span class="unit-text">%</span>
            </el-col>
          </el-row>
        </el-form-item>
        <el-form-item label="告警级别">
          <el-radio-group v-model="ruleForm.level">
            <el-radio label="critical">
              严重
            </el-radio>
            <el-radio label="warning">
              警告
            </el-radio>
            <el-radio label="info">
              信息
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="通知方式">
          <el-checkbox-group v-model="ruleForm.notifyChannels">
            <el-checkbox label="email">
              邮件
            </el-checkbox>
            <el-checkbox label="sms">
              短信
            </el-checkbox>
            <el-checkbox label="webhook">
              Webhook
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRuleDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSaveRule"
        >
          保存规则
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Download, Setting, Check, View, Clock, MoreFilled,
  Document, Guide, CircleCheck, WarningFilled, Bell, InfoFilled, CircleCheckFilled
} from '@element-plus/icons-vue'
import { alerts } from '@/api'

// 状态
const loading = ref(false)
const alertsData = ref([])
const selectedRows = ref([])
const showDetailDrawer = ref(false)
const showRuleDialog = ref(false)
const currentAlert = ref(null)

// 筛选
const levelFilter = ref('')
const statusFilter = ref('')
const searchText = ref('')
const dateRange = ref(null)
const autoRefresh = ref(false)
const refreshInterval = ref(30)

// 分页
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
let refreshTimer = null

// 统计
const statsData = reactive([
  { key: 'critical', title: '严重告警', value: 0, icon: 'WarningFilled', active: false },
  { key: 'warning', title: '警告告警', value: 0, icon: 'Warning', active: false },
  { key: 'info', title: '信息告警', value: 0, icon: 'InfoFilled', active: false },
  { key: 'total', title: '告警总数', value: 0, icon: 'Bell', active: false }
])

const activeCount = computed(() => {
  return alertsData.value.filter(a => a.status === 'active').length
})

const activeAlerts = computed(() => {
  return alertsData.value.filter(a => a.status === 'active').slice(0, 5)
})

// 规则表单
const ruleForm = reactive({
  name: '',
  metric: 'cpu',
  operator: '>',
  threshold: 80,
  level: 'warning',
  notifyChannels: ['email']
})

// 辅助函数
const getLevelText = (level) => {
  const texts = { critical: '严重', warning: '警告', info: '信息' }
  return texts[level] || level
}

const getLevelTagType = (level) => {
  const types = { critical: 'danger', warning: 'warning', info: 'info' }
  return types[level] || 'info'
}

const getStatusText = (status) => {
  const texts = { active: '未处理', acknowledged: '已确认', resolved: '已解决' }
  return texts[status] || status
}

const getStatusTagType = (status) => {
  const types = { active: 'danger', acknowledged: 'warning', resolved: 'success' }
  return types[status] || 'info'
}

// 加载告警数据
const loadAlerts = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value,
      level: levelFilter.value,
      status: statusFilter.value,
      search: searchText.value,
      startDate: dateRange.value ? dateRange.value[0] : null,
      endDate: dateRange.value ? dateRange.value[1] : null
    }
    const res = await alerts.getAlerts(params)
    alertsData.value = res.data.list || res.data
    total.value = res.data.total || alertsData.value.length
    updateStats()
  } catch (error) {
    console.error('Failed to load alerts:', error)
    ElMessage.error('加载告警列表失败')
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  statsData[0].value = alertsData.value.filter(a => a.level === 'critical' && a.status === 'active').length
  statsData[1].value = alertsData.value.filter(a => a.level === 'warning' && a.status === 'active').length
  statsData[2].value = alertsData.value.filter(a => a.level === 'info' && a.status === 'active').length
  statsData[3].value = total.value
}

// 事件处理
const handleFilterChange = () => {
  currentPage.value = 1
  loadAlerts()
}

const handleSearch = () => {
  currentPage.value = 1
  loadAlerts()
}

const handleRefresh = () => {
  loadAlerts()
  ElMessage.success('刷新成功')
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadAlerts()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  loadAlerts()
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const handleAcknowledge = async (alert) => {
  alert.status = 'acknowledged'
  ElMessage.success(`已确认告警: ${alert.message}`)
}

const handleBatchAck = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要确认的告警')
    return
  }
  selectedRows.value.forEach(a => {
    if (a.status === 'active') a.status = 'acknowledged'
  })
  ElMessage.success(`已确认 ${selectedRows.value.length} 条告警`)
}

const handleViewDetail = (alert) => {
  currentAlert.value = alert
  showDetailDrawer.value = true
}

const handleViewHistory = (alert) => {
  currentAlert.value = alert
  showDetailDrawer.value = true
}

const handleSilence = (alert) => {
  ElMessage.info('静默告警: ' + alert.message)
}

const handleCreateTicket = (alert) => {
  ElMessage.success(`正在为告警「${alert.message}」创建工单...`)
}

const handleResolve = async (alert) => {
  alert.status = 'resolved'
  alert.duration = '已解决'
  ElMessage.success('告警已标记为已解决')
}

const handleAlertCommand = (command, alert) => {
  switch (command) {
    case 'view': handleViewDetail(alert); break
    case 'silence': handleSilence(alert); break
    case 'create-ticket': handleCreateTicket(alert); break
    case 'resolve': handleResolve(alert); break
  }
}

const handleSaveRule = () => {
  ElMessage.success('告警规则保存成功')
  showRuleDialog.value = false
}

const handleExport = () => {
  ElMessage.success('导出成功')
}

const handleAutoRefresh = (checked) => {
  if (checked) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  refreshTimer = setInterval(() => {
    loadAlerts()
  }, refreshInterval.value * 1000)
}

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 初始化
onMounted(() => {
  loadAlerts()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.alerts-page {
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

  &.active .stat-icon {
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

  &.critical { background: linear-gradient(135deg, #f53f3f, #ff7875); }
  &.warning { background: linear-gradient(135deg, #ff7d00, #ff9d00); }
  &.info { background: linear-gradient(135deg, #6370f5, #8b93f7); }
  &.total { background: linear-gradient(135deg, #165dff, #4080ff); }
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
  background: radial-gradient(circle, rgba($danger, 0.2) 0%, transparent 70%);
  animation: pulse-wave 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes pulse-wave {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; }
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

.level-option {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .level-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.critical { background: $danger; }
    &.warning { background: $warning; }
    &.info { background: $info; }
  }
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;

  &.active { background: $danger; box-shadow: 0 0 6px $danger; }
  &.acknowledged { background: $warning; }
  &.resolved { background: $success; }
}

// ========== 告警容器 ==========
.alerts-container {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

// ========== 未处理告警区 ==========
.active-alerts {
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.active-header {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  background: rgba($danger, 0.05);
  border-bottom: 1px solid $border-light;

  .active-title {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $text-primary;
  }
}

.active-list {
  padding: $spacing-md;
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.alert-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;
  transition: all 0.2s ease;

  &:hover {
    background: rgba($primary, 0.04);
  }

  &.critical {
    border-left: 4px solid $danger;
    background: rgba($danger, 0.02);
  }

  &.warning {
    border-left: 4px solid $warning;
  }
}

.alert-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;

  &.critical { background: $danger; box-shadow: 0 0 8px $danger; }
  &.warning { background: $warning; }
  &.info { background: $info; }
}

.alert-main {
  flex: 1;
  min-width: 0;

  .alert-header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: 4px;

    .alert-host {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .alert-time {
      font-size: $font-size-xs;
      color: $text-placeholder;
      margin-left: auto;
    }
  }

  .alert-message {
    font-size: $font-size-sm;
    color: $text-regular;
    @include multi-ellipsis(1);
  }

  .alert-metrics {
    display: flex;
    gap: $spacing-md;
    margin-top: 4px;

    .metric-tag, .metric-value, .metric-threshold {
      font-size: $font-size-xs;
      color: $text-secondary;
    }

    .metric-value {
      color: $danger;
      font-weight: $font-weight-medium;
    }
  }
}

.alert-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

// ========== 表格 ==========
.table-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.alerts-table {
  :deep(.el-table__header th) {
    background: $bg-page !important;
    color: $text-secondary;
    font-weight: $font-weight-semibold;
  }
}

.level-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .level-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.critical { background: $danger; box-shadow: 0 0 6px $danger; }
    &.warning { background: $warning; }
    &.info { background: $info; }
  }
}

.alert-info-cell {
  display: flex;
  flex-direction: column;

  .alert-message {
    font-size: $font-size-sm;
    color: $text-primary;
  }

  .alert-metric {
    font-size: $font-size-xs;
    color: $text-placeholder;
  }
}

.host-text {
  font-size: $font-size-sm;
  color: $text-regular;
}

.value-text {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;

  &.critical { color: $danger; }
  &.warning { color: $warning; }
  &.info { color: $info; }
  &.large { font-size: $font-size-md; }
}

.time-text, .duration-text {
  font-size: $font-size-sm;
  color: $text-secondary;

  &.active { color: $danger; }
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

// ========== 告警详情 ==========
.alert-detail {
  .detail-header {
    display: flex;
    gap: $spacing-md;
    margin-bottom: $spacing-xl;

    &.critical { color: $danger; }
    &.warning { color: $warning; }
    &.info { color: $info; }
  }

  .detail-actions {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-sm;
  }
}

.history-operator {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin: 4px 0 0 0;
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

    .filter-left {
      flex-wrap: wrap;
    }
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>