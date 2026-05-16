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
          <div class="stat-value">{{ loading ? '-' : stat.value }}</div>
          <div class="stat-title">{{ stat.title }}</div>
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
          <div v-if="loading" class="chart-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
          <div v-else ref="deviceChartRef" class="chart-container"></div>
        </div>
      </div>

      <div class="card chart-card">
        <div class="card-header">
          <span class="card-title">告警趋势（最近7天）</span>
        </div>
        <div class="card-body">
          <div v-if="loading" class="chart-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
          <div v-else ref="alertChartRef" class="chart-container"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">最近告警</span>
          <el-button type="primary" link @click="$router.push('/monitoring/alerts')">查看更多</el-button>
        </div>
        <div class="card-body">
          <div v-if="loading" class="table-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
          <el-table v-else :data="recentAlerts" style="width: 100%" :show-header="true">
            <el-table-column prop="level" label="级别" width="80">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.level)" size="small">{{ getSeverityText(row.level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="告警信息" />
            <el-table-column prop="occurred_at" label="时间" width="160">
              <template #default="{ row }">
                {{ formatTime(row.occurred_at) }}
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
          <div v-if="loading" class="table-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
          <el-table v-else :data="pendingOrders" style="width: 100%">
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
        <div v-if="loadingSystem" class="system-metrics">
          <div class="metric-item" v-for="i in 4" :key="i">
            <el-skeleton :rows="0" animated />
          </div>
        </div>
        <div v-else class="system-metrics">
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
import { Monitor, Bell, Tickets, Loading } from '@element-plus/icons-vue'
import { formatTime } from '@/utils/date'
import { getSeverityType, getSeverityText, getPriorityType, getPriorityText, getWorkOrderStatusType, getWorkOrderStatusText } from '@/utils/status'
import { performance, alerts, workorder } from '@/api'

const deviceChartRef = ref(null)
const alertChartRef = ref(null)
let deviceChart = null
let alertChart = null

const loading = ref(true)
const loadingSystem = ref(true)
const error = ref(null)

const stats = reactive([
  { title: '设备总数', value: 0, icon: Monitor, color: '#165dff', bg: '#e8f0ff' },
  { title: '在线设备', value: 0, icon: Monitor, color: '#00b42a', bg: '#e8ffea' },
  { title: '活跃告警', value: 0, icon: Bell, color: '#ff7d00', bg: '#fff7e6' },
  { title: '严重告警', value: 0, icon: Bell, color: '#f53f3f', bg: '#fff1f0' },
  { title: '待办工单', value: 0, icon: Tickets, color: '#722ed1', bg: '#f9f0ff' }
])

const recentAlerts = ref([])
const pendingOrders = ref([])
const systemMetrics = reactive({ cpu: 0, memory: 0, disk: 0, network: 0 })

// 图表数据
const deviceChartData = ref([])
const alertChartData = ref([])

onMounted(async () => {
  await Promise.all([
    loadDashboardStats(),
    loadRecentAlerts(),
    loadPendingOrders(),
    loadSystemMetrics()
  ])
  loading.value = false
  await nextTick()
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  deviceChart?.dispose()
  alertChart?.dispose()
})

// 加载仪表盘核心统计数据
const loadDashboardStats = async () => {
  try {
    const res = await performance.getDashboardStats()
    if (res) {
      stats[0].value = res.devices?.total || 0
      stats[1].value = res.devices?.online || 0
      stats[2].value = res.alerts?.active || 0
      stats[3].value = res.alerts?.critical || 0
      stats[4].value = res.workorders?.pending || 0

      // 设备状态分布
      deviceChartData.value = [
        { value: res.devices?.online || 0, name: '在线', itemStyle: { color: '#00b42a' } },
        { value: res.devices?.offline || 0, name: '离线', itemStyle: { color: '#86909c' } },
        { value: res.devices?.maintenance || 0, name: '维护', itemStyle: { color: '#ff7d00' } }
      ]

      // 告警趋势
      alertChartData.value = (res.alerts?.trend || []).map(item => item.count)
    }
  } catch (err) {
    console.error('加载仪表盘统计失败:', err)
    error.value = '加载仪表盘统计失败'
  }
}

// 加载最近告警列表
const loadRecentAlerts = async () => {
  try {
    const res = await alerts.getList({ page: 1, page_size: 5, status: 'active' })
    recentAlerts.value = res?.items || []
  } catch (err) {
    console.error('加载告警列表失败:', err)
    recentAlerts.value = []
  }
}

// 加载待处理工单列表
const loadPendingOrders = async () => {
  try {
    // 查询 pending 和 processing 状态的工单
    const res = await workorder.getList({ 
      page: 1, 
      page_size: 5,
      status: 'pending'
    })
    // 如果 pending 为空，尝试 processing
    if (!res?.items || res.items.length === 0) {
      const processingRes = await workorder.getList({
        page: 1,
        page_size: 5,
        status: 'processing'
      })
      pendingOrders.value = processingRes?.items || []
    } else {
      pendingOrders.value = res?.items || []
    }
  } catch (err) {
    console.error('加载工单列表失败:', err)
    pendingOrders.value = []
  }
}

// 加载系统监控指标（从有数据的设备聚合）
const loadSystemMetrics = async () => {
  loadingSystem.value = true
  try {
    const res = await performance.getMetrics({ limit: 100 })
    if (res?.metrics && res.metrics.length > 0) {
      // 简单聚合：取所有设备指标的平均值
      let cpuSum = 0, memSum = 0, diskSum = 0, netSum = 0
      let cpuCount = 0, memCount = 0, diskCount = 0, netCount = 0
      
      for (const metric of res.metrics) {
        const points = metric.points || []
        if (points.length === 0) continue
        
        // 取最新值
        const latestValue = points[0].value
        
        if (metric.metric === 'cpu_usage' || metric.metric === 'cpu') {
          cpuSum += latestValue
          cpuCount++
        } else if (metric.metric === 'memory_usage_percent' || metric.metric === 'memory') {
          memSum += latestValue
          memCount++
        } else if (metric.metric === 'disk_usage' || metric.metric === 'disk') {
          diskSum += latestValue
          diskCount++
        } else if (metric.metric === 'network_bandwidth' || metric.metric === 'network') {
          netSum += latestValue
          netCount++
        }
      }
      
      systemMetrics.cpu = cpuCount > 0 ? Math.round(cpuSum / cpuCount) : 0
      systemMetrics.memory = memCount > 0 ? Math.round(memSum / memCount) : 0
      systemMetrics.disk = diskCount > 0 ? Math.round(diskSum / diskCount) : 0
      systemMetrics.network = netCount > 0 ? Math.round(netSum / netCount) : 0
    } else {
      // 无监控数据时显示占位数据
      systemMetrics.cpu = 0
      systemMetrics.memory = 0
      systemMetrics.disk = 0
      systemMetrics.network = 0
    }
  } catch (err) {
    console.error('加载系统监控指标失败:', err)
    // 出错时使用默认值
    systemMetrics.cpu = 0
    systemMetrics.memory = 0
    systemMetrics.disk = 0
    systemMetrics.network = 0
  } finally {
    loadingSystem.value = false
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
    const days = alertChartData.value.length === 7 
      ? ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      : ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    alertChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: days },
      yAxis: { type: 'value' },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: alertChartData.value.length > 0 ? alertChartData.value : Array(7).fill(0),
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
  grid-template-columns: repeat(5, 1fr);
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
    position: relative;
  }
}

.chart-loading, .table-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #86909c;
  font-size: 24px;
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