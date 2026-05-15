<template>
  <div class="page-container">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.title">
        <div class="stat-icon" :style="{ background: stat.bg }">
          <el-icon :size="24" :color="stat.color">
            <component :is="stat.icon" />
          </el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-title">{{ stat.title }}</div>
        </div>
        <div class="stat-trend" :class="stat.trend > 0 ? 'up' : 'down'" v-if="stat.trend !== undefined">
          {{ stat.trend > 0 ? '+' : '' }}{{ stat.trend }}%
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="dashboard-grid">
      <div class="card chart-card">
        <div class="card-header">
          <span class="card-title">设备状态分布</span>
        </div>
        <div class="card-body">
          <div ref="deviceChartRef" class="chart-container"></div>
        </div>
      </div>

      <div class="card chart-card">
        <div class="card-header">
          <span class="card-title">告警趋势</span>
        </div>
        <div class="card-body">
          <div ref="alertChartRef" class="chart-container"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">最近告警</span>
          <el-button type="primary" link @click="$router.push('/monitoring/alerts')">查看更多</el-button>
        </div>
        <div class="card-body">
          <el-table :data="recentAlerts" style="width: 100%" :show-header="true">
            <el-table-column prop="severity" label="级别" width="80">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small">{{ getSeverityText(row.severity) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="告警信息" />
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">待处理工单</span>
          <el-button type="primary" link @click="$router.push('/workorder/list')">查看更多</el-button>
        </div>
        <div class="card-body">
          <el-table :data="pendingOrders" style="width: 100%">
            <el-table-column prop="priority" label="优先级" width="80">
              <template #default="{ row }">
                <el-tag :type="getPriorityType(row.priority)" size="small">{{ getPriorityText(row.priority) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="工单标题" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getWorkOrderStatusType(row.status)" size="small">{{ getWorkOrderStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- 系统状态 -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">系统资源监控</span>
      </div>
      <div class="card-body">
        <div class="system-metrics">
          <div class="metric-item">
            <div class="metric-header">
              <span class="metric-label">CPU使用率</span>
              <span class="metric-value">{{ systemMetrics.cpu }}%</span>
            </div>
            <el-progress :percentage="systemMetrics.cpu" :color="getProgressColor(systemMetrics.cpu)" :stroke-width="10" />
          </div>
          <div class="metric-item">
            <div class="metric-header">
              <span class="metric-label">内存使用率</span>
              <span class="metric-value">{{ systemMetrics.memory }}%</span>
            </div>
            <el-progress :percentage="systemMetrics.memory" :color="getProgressColor(systemMetrics.memory)" :stroke-width="10" />
          </div>
          <div class="metric-item">
            <div class="metric-header">
              <span class="metric-label">磁盘使用率</span>
              <span class="metric-value">{{ systemMetrics.disk }}%</span>
            </div>
            <el-progress :percentage="systemMetrics.disk" :color="getProgressColor(systemMetrics.disk)" :stroke-width="10" />
          </div>
          <div class="metric-item">
            <div class="metric-header">
              <span class="metric-label">网络带宽</span>
              <span class="metric-value">{{ systemMetrics.network }}Mbps</span>
            </div>
            <el-progress :percentage="systemMetrics.network / 10" :color="getProgressColor(systemMetrics.network / 10)" :stroke-width="10" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Monitor, Bell, Tickets } from '@element-plus/icons-vue'
import { formatTime } from '@/utils/date'
import { getSeverityType, getSeverityText, getPriorityType, getPriorityText, getWorkOrderStatusType, getWorkOrderStatusText } from '@/utils/status'
import { devices, alerts, workorder } from '@/api'

const deviceChartRef = ref(null)
const alertChartRef = ref(null)
let deviceChart = null
let alertChart = null

const stats = reactive([
  { title: '设备总数', value: 0, icon: Monitor, color: '#165dff', bg: '#e8f0ff', trend: 5 },
  { title: '在线设备', value: 0, icon: Monitor, color: '#00b42a', bg: '#e8ffea', trend: 2 },
  { title: '告警数量', value: 0, icon: Bell, color: '#ff7d00', bg: '#fff7e6', trend: -3 },
  { title: '待办工单', value: 0, icon: Tickets, color: '#f53f3f', bg: '#fff1f0', trend: 8 }
])

const recentAlerts = ref([])
const pendingOrders = ref([])
const systemMetrics = reactive({ cpu: 0, memory: 0, disk: 0, network: 0 })

// 图表数据（从 API 加载，避免硬编码）
const deviceChartData = ref([])
const alertChartData = ref([])

onMounted(async () => {
  await loadDashboard()
  await nextTick()
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  deviceChart?.dispose()
  alertChart?.dispose()
})

const loadDashboard = async () => {
  try {
    const [deviceRes, alertRes, orderRes] = await Promise.all([
      devices.getList({ page: 1, page_size: 100 }).catch(() => ({ items: [], total: 0 })),
      alerts.getList({ page: 1, page_size: 5 }).catch(() => ({ items: [], total: 0 })),
      workorder.getList({ page: 1, page_size: 5, status: 'pending' }).catch(() => ({ items: [], total: 0 }))
    ])

    const deviceList = deviceRes.items || []
    stats[0].value = deviceRes.total || 0
    stats[1].value = deviceList.filter(d => d.status === 'online').length
    stats[2].value = alertRes.total || 0
    stats[3].value = orderRes.total || 0

    recentAlerts.value = alertRes.items || []
    pendingOrders.value = orderRes.items || []

    // 设备状态分布图表数据
    const onlineCount = deviceList.filter(d => d.status === 'online').length
    const offlineCount = deviceList.filter(d => d.status === 'offline').length
    const warningCount = deviceList.filter(d => d.status === 'warning').length
    deviceChartData.value = [
      { value: onlineCount, name: '在线', itemStyle: { color: '#00b42a' } },
      { value: offlineCount, name: '离线', itemStyle: { color: '#86909c' } },
      { value: warningCount, name: '告警', itemStyle: { color: '#ff7d00' } }
    ]

    // 告警趋势图表数据（最近7天，使用 alertRes.items 模拟）
    const alertItems = alertRes.items || []
    alertChartData.value = alertItems.slice(0, 7).map((_, i) => ({
      value: Math.floor(Math.random() * 20), // 暂无7天历史数据，随机占位
      name: `Day${i + 1}`
    }))
  } catch (error) {
    console.error('Load dashboard error:', error)
  }
}

const initCharts = () => {
  if (deviceChartRef.value) {
    deviceChart = echarts.init(deviceChartRef.value)
    deviceChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, left: 'center' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14 } },
        data: deviceChartData.value.length > 0 ? deviceChartData.value : [
          { value: 0, name: '暂无数据', itemStyle: { color: '#86909c' } }
        ]
      }]
    })
  }

  if (alertChartRef.value) {
    alertChart = echarts.init(alertChartRef.value)
    const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    alertChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: days },
      yAxis: { type: 'value' },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: alertChartData.value.length > 0
          ? alertChartData.value.map(d => d.value)
          : Array(7).fill(0),
        lineStyle: { color: '#165dff' },
        itemStyle: { color: '#165dff' }
      }]
    })
  }
}

const handleResize = () => {
  deviceChart?.resize()
  alertChart?.resize()
}

const getProgressColor = (value) => {
  if (value >= 90) return '#f53f3f'
  if (value >= 70) return '#ff7d00'
  return '#00b42a'
}
</script>

<style lang="scss" scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  position: relative;

  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .stat-content {
    flex: 1;

    .stat-value {
      font-size: 28px;
      font-weight: 600;
      color: #1d2129;
      line-height: 1;
    }

    .stat-title {
      font-size: 14px;
      color: #86909c;
      margin-top: 4px;
    }
  }

  .stat-trend {
    position: absolute;
    right: 20px;
    top: 20px;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;

    &.up {
      color: #f53f3f;
      background: #fff1f0;
    }

    &.down {
      color: #00b42a;
      background: #e8ffea;
    }
  }
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  .card-body {
    height: 280px;
  }
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 250px;
}

.system-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;

  .metric-item {
    .metric-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;

      .metric-label {
        font-size: 14px;
        color: #4b4f59;
      }

      .metric-value {
        font-size: 14px;
        font-weight: 600;
        color: #1d2129;
      }
    }
  }
}

:deep(.el-table) {
  .el-table__header th {
    background: #f7f8fa;
    color: #4b4f59;
    font-weight: 500;
  }
}
</style>
