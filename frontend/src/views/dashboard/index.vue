<template>
  <div class="page-container">
    <!-- Loading State -->
    <n-spin :show="loading" description="加载数据中...">
      <!-- 统计卡片 -->
      <n-grid :cols="4" :x-gap="16" :y-gap="16" class="stats-grid" responsive="screen" :item-responsive="true">
        <n-gi v-for="stat in stats" :key="stat.key" span="24:6">
          <div class="stat-card" :style="{ borderLeftColor: stat.color }" @click="handleStatClick(stat.key)">
            <div class="stat-icon-wrap" :style="{ background: stat.bgColor }">
              <n-icon :component="stat.icon" :size="24" :color="stat.color" />
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </n-gi>
      </n-grid>

      <!-- 系统健康状态 -->
      <div class="health-card" v-if="systemHealth">
        <div class="health-header">
          <span class="card-title">系统健康状态</span>
          <n-tag :type="healthType" size="small">{{ healthText }}</n-tag>
        </div>
        <div class="health-body">
          <n-space justify="space-between">
            <div class="health-item">
              <span class="health-label">CPU使用率</span>
              <n-progress type="line" :percentage="systemHealth.cpu" :indicator-placement="'inside'" :status="getProgressStatus(systemHealth.cpu)" />
            </div>
            <div class="health-item">
              <span class="health-label">内存使用率</span>
              <n-progress type="line" :percentage="systemHealth.memory" :indicator-placement="'inside'" :status="getProgressStatus(systemHealth.memory)" />
            </div>
            <div class="health-item">
              <span class="health-label">磁盘使用率</span>
              <n-progress type="line" :percentage="systemHealth.disk" :indicator-placement="'inside'" :status="getProgressStatus(systemHealth.disk)" />
            </div>
          </n-space>
        </div>
      </div>

      <!-- 图表区域 -->
      <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-grid" responsive="screen" :item-responsive="true">
        <n-gi span="24:12">
          <div class="card">
            <div class="card-header">
              <span class="card-title">告警统计</span>
              <n-space>
                <n-tag type="error" size="small">严重 {{ alertStats.critical }}</n-tag>
                <n-tag type="warning" size="small">警告 {{ alertStats.warning }}</n-tag>
                <n-tag type="info" size="small">提示 {{ alertStats.info }}</n-tag>
              </n-space>
            </div>
            <div class="card-body">
              <div ref="alertChartRef" class="chart-container"></div>
            </div>
          </div>
        </n-gi>
        <n-gi span="24:12">
          <div class="card">
            <div class="card-header">
              <span class="card-title">设备状态</span>
              <n-space>
                <n-tag type="success" size="small">在线 {{ deviceStats.online }}</n-tag>
                <n-tag type="default" size="small">离线 {{ deviceStats.offline }}</n-tag>
                <n-tag type="warning" size="small">告警 {{ deviceStats.warning }}</n-tag>
              </n-space>
            </div>
            <div class="card-body">
              <div ref="deviceChartRef" class="chart-container"></div>
            </div>
          </div>
        </n-gi>
      </n-grid>

      <!-- 表格区域 -->
      <n-grid :cols="2" :x-gap="16" :y-gap="16" class="table-grid" responsive="screen" :item-responsive="true">
        <n-gi span="24:12">
          <div class="card">
            <div class="card-header">
              <span class="card-title">最新告警</span>
              <n-button type="primary" text @click="$router.push('/monitoring/alerts')">查看更多</n-button>
            </div>
            <div class="card-body">
              <n-data-table :columns="alertColumns" :data="recentAlerts" :bordered="false" size="small" :loading="alertsLoading" />
              <n-empty v-if="!alertsLoading && recentAlerts.length === 0" description="暂无告警数据" />
            </div>
          </div>
        </n-gi>
        <n-gi span="24:12">
          <div class="card">
            <div class="card-header">
              <span class="card-title">待处理工单</span>
              <n-button type="primary" text @click="$router.push('/workorder/list')">查看更多</n-button>
            </div>
            <div class="card-body">
              <n-data-table :columns="workorderColumns" :data="pendingOrders" :bordered="false" size="small" :loading="workordersLoading" />
              <n-empty v-if="!workordersLoading && pendingOrders.length === 0" description="暂无待处理工单" />
            </div>
          </div>
        </n-gi>
      </n-grid>
    </n-spin>

    <!-- Error State -->
    <div v-if="error && !loading" class="error-state">
      <n-result status="error" title="加载失败" :description="error">
        <template #footer>
          <n-button @click="loadDashboard">重试</n-button>
        </template>
      </n-result>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, h, computed } from 'vue'
import * as echarts from 'echarts'
import {
  NGrid, NGi, NIcon, NButton, NDataTable, NTag, NProgress,
  NSpin, NEmpty, NResult, NSpace, useMessage
} from 'naive-ui'
import {
  DesktopOutline,
  AlertCircleOutline,
  TicketOutline,
  CheckmarkCircleOutline,
  CloudOfflineOutline,
  WarningOutline
} from '@vicons/ionicons5'
import { devices, alerts, workorder } from '@/api'

const message = useMessage()
const alertChartRef = ref(null)
const deviceChartRef = ref(null)
let alertChart = null
let deviceChart = null

// Loading states
const loading = ref(false)
const alertsLoading = ref(false)
const workordersLoading = ref(false)

// Error handling
const error = ref(null)

// Stats data
const stats = reactive([
  { key: 'total', label: '设备总数', value: 0, icon: DesktopOutline, color: '#165dff', bgColor: '#e8f0ff' },
  { key: 'online', label: '在线设备', value: 0, icon: CheckmarkCircleOutline, color: '#00b42a', bgColor: '#e8ffea' },
  { key: 'alert', label: '告警数量', value: 0, icon: AlertCircleOutline, color: '#ff7d00', bgColor: '#fff7e6' },
  { key: 'workorder', label: '待办工单', value: 0, icon: TicketOutline, color: '#f53f3f', bgColor: '#fff1f0' }
])

// Alert statistics
const alertStats = reactive({ critical: 0, warning: 0, info: 0 })

// Device statistics
const deviceStats = reactive({ online: 0, offline: 0, warning: 0 })

// System health
const systemHealth = ref(null)

// Tables data
const recentAlerts = ref([])
const pendingOrders = ref([])

// Alert severity type map
const severityTypeMap = { critical: 'error', high: 'error', medium: 'warning', low: 'info', info: 'info' }
const severityTextMap = { critical: '严重', high: '高', medium: '中', low: '低', info: '提示' }
const severityOrder = ['critical', 'high', 'medium', 'low', 'info']

// Workorder priority type map
const priorityTypeMap = { urgent: 'error', high: 'warning', medium: 'info', low: 'default' }
const priorityTextMap = { urgent: '紧急', high: '高', medium: '中', low: '低' }

const alertColumns = [
  {
    title: '级别',
    key: 'severity',
    width: 80,
    render(row) {
      const type = severityTypeMap[row.severity] || 'default'
      const text = severityTextMap[row.severity] || row.severity || '未知'
      return h(NTag, { type, size: 'small' }, () => text)
    }
  },
  { title: '告警信息', key: 'message', ellipsis: { tooltip: true } },
  {
    title: '时间',
    key: 'created_at',
    width: 160,
    render(row) {
      if (!row.created_at) return '-'
      return new Date(row.created_at).toLocaleString('zh-CN')
    }
  }
]

const workorderColumns = [
  {
    title: '优先级',
    key: 'priority',
    width: 80,
    render(row) {
      const type = priorityTypeMap[row.priority] || 'default'
      const text = priorityTextMap[row.priority] || row.priority || '普通'
      return h(NTag, { type, size: 'small' }, () => text)
    }
  },
  { title: '工单标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      const statusMap = {
        pending: { type: 'warning', text: '待处理' },
        processing: { type: 'info', text: '处理中' },
        resolved: { type: 'success', text: '已解决' },
        closed: { type: 'default', text: '已关闭' }
      }
      const status = statusMap[row.status] || { type: 'default', text: row.status || '-' }
      return h(NTag, { type: status.type, size: 'small' }, () => status.text)
    }
  }
]

// Health status helpers
const getProgressStatus = (value) => {
  if (value >= 90) return 'error'
  if (value >= 70) return 'warning'
  return 'success'
}

const healthType = computed(() => {
  if (!systemHealth.value) return 'default'
  const { cpu, memory, disk } = systemHealth.value
  if (cpu >= 90 || memory >= 90 || disk >= 90) return 'error'
  if (cpu >= 70 || memory >= 70 || disk >= 70) return 'warning'
  return 'success'
})

const healthText = computed(() => {
  if (!systemHealth.value) return '未知'
  const { cpu, memory, disk } = systemHealth.value
  if (cpu >= 90 || memory >= 90 || disk >= 90) return '危险'
  if (cpu >= 70 || memory >= 70 || disk >= 70) return '警告'
  return '正常'
})

// API call with 3-level error handling
const fetchWithErrorHandling = async (apiCall, fallback = null, showError = true) => {
  try {
    const result = await apiCall()
    return result
  } catch (err) {
    // Level 1: Network/server errors
    if (err.response) {
      // Level 2: HTTP errors
      const status = err.response.status
      if (status === 401) {
        message.warning('登录已过期，请重新登录')
        localStorage.removeItem('token')
        window.location.href = '/login'
        return fallback
      }
      if (status === 403) {
        message.warning('没有权限访问')
        return fallback
      }
      if (showError && err.response.data?.msg) {
        message.error(err.response.data.msg)
      }
    } else if (err.request) {
      // Level 3: Network connectivity errors
      if (showError) {
        message.error('网络连接失败，请检查网络')
      }
    }
    return fallback
  }
}

const loadDashboard = async () => {
  loading.value = true
  error.value = null

  try {
    // Load all data in parallel with error handling
    const [statsRes, alertRes, workorderRes, healthRes] = await Promise.allSettled([
      fetchWithErrorHandling(() => devices.getStats(), { total: 0, online: 0, offline: 0, warning: 0 }),
      fetchWithErrorHandling(() => alerts.getList({ page: 1, page_size: 10 }), { items: [], total: 0 }),
      fetchWithErrorHandling(() => workorder.getList({ page: 1, page_size: 10, status: 'pending' }), { items: [], total: 0 }),
      fetchWithErrorHandling(() => devices.getStats(), null, false) // Silent fail for health
    ])

    // Process device stats - devices.getStats() returns {total, online, offline, unknown}
    // stats[2] = 告警数量 should show active alerts count, not device warning
    if (statsRes.status === 'fulfilled' && statsRes.value) {
      const data = statsRes.value
      if (typeof data.total === 'number') {
        stats[0].value = data.total
        stats[1].value = data.online || 0
        // stats[2] (告警) 从 alerts 数据填充，见下方
        deviceStats.online = data.online || 0
        deviceStats.offline = data.offline || 0
        // deviceStats.warning 从告警列表计算
      }
    } else if (statsRes.reason) {
      console.warn('Failed to load device stats:', statsRes.reason)
    }

    // Process alerts - Level 3 error handling
    if (alertRes.status === 'fulfilled' && alertRes.value) {
      const data = alertRes.value
      const items = Array.isArray(data) ? data : (data.items || [])
      recentAlerts.value = items.slice(0, 10)

      // Calculate alert statistics by severity
      alertStats.critical = items.filter(a => ['critical', 'high'].includes(a.severity)).length
      alertStats.warning = items.filter(a => ['medium', 'warning'].includes(a.severity)).length
      alertStats.info = items.filter(a => ['low', 'info'].includes(a.severity)).length
      stats[2].value = items.length
      deviceStats.warning = items.length
    } else {
      recentAlerts.value = []
    }

    // Process workorders - Level 3 error handling
    if (workorderRes.status === 'fulfilled' && workorderRes.value) {
      const data = workorderRes.value
      const items = Array.isArray(data) ? data : (data.items || [])
      pendingOrders.value = items.slice(0, 10)
      stats[3].value = data.total || items.length
    } else {
      pendingOrders.value = []
    }

    // Process system health (optional, don't fail if missing)
    if (healthRes.status === 'fulfilled' && healthRes.value) {
      const data = healthRes.value
      // Try to extract health data from various possible structures
      if (data.cpu !== undefined) {
        systemHealth.value = { cpu: data.cpu, memory: data.memory, disk: data.disk }
      } else if (data.metrics) {
        systemHealth.value = {
          cpu: data.metrics.cpu || 0,
          memory: data.metrics.memory || 0,
          disk: data.metrics.disk || 0
        }
      }
    }

    // Initialize charts after data is loaded
    await nextTick()
    initCharts()

  } catch (err) {
    // Critical error - show error state
    error.value = '加载仪表盘数据失败，请稍后重试'
    message.error('加载仪表盘数据失败')
    console.error('Dashboard load error:', err)
  } finally {
    loading.value = false
  }
}

const initCharts = () => {
  // Alert trend chart
  if (alertChartRef.value) {
    alertChart = echarts.init(alertChartRef.value)
    const alertData = generateTrendData(recentAlerts.value, 'created_at')
    alertChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: alertData.dates
      },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: alertData.values,
        lineStyle: { color: '#ff7d00' },
        itemStyle: { color: '#ff7d00' }
      }]
    })
  }

  // Device status pie chart
  if (deviceChartRef.value) {
    deviceChart = echarts.init(deviceChartRef.value)
    deviceChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: '5%', left: 'center' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: [
          { value: deviceStats.online, name: '在线', itemStyle: { color: '#00b42a' } },
          { value: deviceStats.offline, name: '离线', itemStyle: { color: '#8c8c8c' } },
          { value: deviceStats.warning, name: '告警', itemStyle: { color: '#ff7d00' } }
        ].filter(d => d.value > 0)
      }]
    })
  }
}

// Generate trend data from items
const generateTrendData = (items, dateField) => {
  const now = new Date()
  const dates = []
  const values = []

  // Generate last 7 days
  for (let i = 6; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    const dateStr = `${date.getMonth() + 1}/${date.getDate()}`
    dates.push(dateStr)

    // Count items for this day
    const dayStart = new Date(date.setHours(0, 0, 0, 0))
    const dayEnd = new Date(date.setHours(23, 59, 59, 999))

    const count = items.filter(item => {
      if (!item[dateField]) return false
      const itemDate = new Date(item[dateField])
      return itemDate >= dayStart && itemDate <= dayEnd
    }).length

    values.push(count)
  }

  return { dates, values }
}

const handleResize = () => {
  alertChart?.resize()
  deviceChart?.resize()
}

function handleStatClick(key) {
  const routes = { total: '/monitoring/devices', online: '/monitoring/devices', alert: '/monitoring/alerts', workorder: '/workorder/list' }
  if (routes[key]) window.location.hash = routes[key]
}

// Dashboard polling timer
let pollTimer = null

function startPoll() {
  stopPoll()
  pollTimer = setInterval(() => {
    loadDashboard()
  }, 30000) // 每30秒刷新一次
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  await loadDashboard()
  startPoll()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  stopPoll()
  window.removeEventListener('resize', handleResize)
  alertChart?.dispose()
  deviceChart?.dispose()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
  min-height: calc(100vh - 40px);
}
.stats-grid {
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.1);
}
.stat-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-content {
  flex: 1;
  min-width: 0;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1d2129;
  line-height: 1;
}
.stat-label {
  font-size: 13px;
  color: #86909c;
  margin-top: 4px;
}
.health-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}
.health-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-title {
  font-size: 16px;
  font-weight: 500;
  color: #1d2129;
}
.health-body {
  padding: 16px 20px;
}
.health-item {
  flex: 1;
  padding: 0 12px;
}
.health-label {
  display: block;
  font-size: 13px;
  color: #86909c;
  margin-bottom: 8px;
}
.chart-grid,
.table-grid {
  margin-bottom: 20px;
}
.card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-body {
  padding: 16px 20px;
  min-height: 200px;
}
.chart-container {
  width: 100%;
  height: 280px;
}
.error-state {
  padding: 60px 20px;
  text-align: center;
}
@media (max-width: 768px) {
  .page-container {
    padding: 12px;
  }
  .stat-card {
    padding: 16px;
  }
  .stat-icon-wrap {
    width: 40px;
    height: 40px;
  }
  .stat-value {
    font-size: 20px;
  }
  .health-body {
    flex-direction: column;
  }
  .health-item {
    padding: 8px 0;
  }
}
</style>
