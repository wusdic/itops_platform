<template>
  <div class="page-container">
    <!-- 统计卡片 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" class="stats-grid">
      <n-gi v-for="stat in stats" :key="stat.key">
        <div class="stat-card" :style="{ borderLeftColor: stat.color }">
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

    <!-- 图表区域 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-grid">
      <n-gi>
        <div class="card">
          <div class="card-header">
            <span class="card-title">告警趋势</span>
          </div>
          <div class="card-body">
            <div ref="alertChartRef" class="chart-container"></div>
          </div>
        </div>
      </n-gi>
      <n-gi>
        <div class="card">
          <div class="card-header">
            <span class="card-title">工单趋势</span>
          </div>
          <div class="card-body">
            <div ref="workorderChartRef" class="chart-container"></div>
          </div>
        </div>
      </n-gi>
    </n-grid>

    <!-- 表格区域 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" class="table-grid">
      <n-gi>
        <div class="card">
          <div class="card-header">
            <span class="card-title">最新告警</span>
            <n-button type="primary" text @click="$router.push('/monitoring/alerts')">查看更多</n-button>
          </div>
          <div class="card-body">
            <n-data-table :columns="alertColumns" :data="recentAlerts" :bordered="false" size="small" />
          </div>
        </div>
      </n-gi>
      <n-gi>
        <div class="card">
          <div class="card-header">
            <span class="card-title">待处理工单</span>
            <n-button type="primary" text @click="$router.push('/workorder/list')">查看更多</n-button>
          </div>
          <div class="card-body">
            <n-data-table :columns="workorderColumns" :data="pendingOrders" :bordered="false" size="small" />
          </div>
        </div>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, h } from 'vue'
import * as echarts from 'echarts'
import { NGrid, NGi, NIcon, NButton, NDataTable, NTag, NProgress } from 'naive-ui'
import {
  DesktopOutline,
  AlertCircleOutline,
  TicketOutline,
  CheckmarkCircleOutline
} from '@vicons/ionicons5'
import { devices, alerts, workorder } from '@/api'

const alertChartRef = ref(null)
const workorderChartRef = ref(null)
let alertChart = null
let workorderChart = null

const stats = reactive([
  { key: 'total', label: '设备总数', value: 0, icon: DesktopOutline, color: '#165dff', bgColor: '#e8f0ff' },
  { key: 'online', label: '在线设备', value: 0, icon: CheckmarkCircleOutline, color: '#00b42a', bgColor: '#e8ffea' },
  { key: 'alert', label: '告警数量', value: 0, icon: AlertCircleOutline, color: '#ff7d00', bgColor: '#fff7e6' },
  { key: 'workorder', label: '待办工单', value: 0, icon: TicketOutline, color: '#f53f3f', bgColor: '#fff1f0' }
])

const recentAlerts = ref([])
const pendingOrders = ref([])

const alertColumns = [
  {
    title: '级别',
    key: 'severity',
    width: 80,
    render(row) {
      const typeMap = { critical: 'error', high: 'warning', medium: 'info', low: 'default' }
      const textMap = { critical: '严重', high: '高', medium: '中', low: '低' }
      return h(NTag, { type: typeMap[row.severity] || 'default', size: 'small' }, () => textMap[row.severity] || row.severity)
    }
  },
  { title: '告警信息', key: 'message', ellipsis: { tooltip: true } },
  {
    title: '时间',
    key: 'created_at',
    width: 160,
    render(row) {
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
      const typeMap = { urgent: 'error', high: 'warning', medium: 'info', low: 'default' }
      const textMap = { urgent: '紧急', high: '高', medium: '中', low: '低' }
      return h(NTag, { type: typeMap[row.priority] || 'default', size: 'small' }, () => textMap[row.priority] || row.priority)
    }
  },
  { title: '工单标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      const typeMap = { pending: 'warning', processing: 'info', resolved: 'success' }
      const textMap = { pending: '待处理', processing: '处理中', resolved: '已解决' }
      return h(NTag, { type: typeMap[row.status] || 'default', size: 'small' }, () => textMap[row.status] || row.status)
    }
  }
]

const loadDashboard = async () => {
  const results = await Promise.allSettled([
    devices.getStats().catch(() => ({ total: 0, online: 0, offline: 0, alert: 0 })),
    alerts.getList({ page: 1, page_size: 10 }).catch(() => ({ items: [], total: 0 })),
    workorder.getList({ page: 1, page_size: 10, status: 'pending' }).catch(() => ({ items: [], total: 0 }))
  ])

  const [statsRes, alertRes, workorderRes] = results

  if (statsRes.status === 'fulfilled') {
    stats[0].value = statsRes.value.total || 0
    stats[1].value = statsRes.value.online || 0
    stats[2].value = statsRes.value.alert || 0
  }

  if (alertRes.status === 'fulfilled') {
    recentAlerts.value = alertRes.value.items || []
  }

  if (workorderRes.status === 'fulfilled') {
    pendingOrders.value = workorderRes.value.items || []
    stats[3].value = workorderRes.value.total || 0
  }
}

const initCharts = () => {
  if (alertChartRef.value) {
    alertChart = echarts.init(alertChartRef.value)
    alertChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      },
      yAxis: { type: 'value' },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: [12, 8, 15, 6, 10, 5, 8],
        lineStyle: { color: '#ff7d00' },
        itemStyle: { color: '#ff7d00' }
      }]
    })
  }

  if (workorderChartRef.value) {
    workorderChart = echarts.init(workorderChartRef.value)
    workorderChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      },
      yAxis: { type: 'value' },
      series: [{
        type: 'bar',
        data: [5, 8, 6, 10, 12, 3, 7],
        itemStyle: { color: '#165dff', borderRadius: [4, 4, 0, 0] }
      }]
    })
  }
}

const handleResize = () => {
  alertChart?.resize()
  workorderChart?.resize()
}

onMounted(async () => {
  await loadDashboard()
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  alertChart?.dispose()
  workorderChart?.dispose()
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
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
  border-left: 4px solid;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  .stat-icon-wrap {
    width: 48px;
    height: 48px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .stat-content {
    flex: 1;

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
  }
}

.chart-grid,
.table-grid {
  margin-bottom: 20px;
}

.card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  .card-header {
    padding: 16px 20px;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .card-title {
      font-size: 16px;
      font-weight: 500;
      color: #1d2129;
    }
  }

  .card-body {
    padding: 16px 20px;
  }
}

.chart-container {
  width: 100%;
  height: 280px;
}
</style>
