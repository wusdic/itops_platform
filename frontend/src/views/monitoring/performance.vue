<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">性能监控</h1>
        <p class="page-subtitle">实时监控系统性能指标</p>
      </div>
      <div class="page-actions">
        <n-button @click="loadDevices" :loading="loading">
          <template #icon>
            <n-icon><Refresh /></n-icon>
          </template>
          刷新
        </n-button>
      </div>
    </div>

    <!-- 设备选择 -->
    <n-card title="选择设备" class="mb-4">
      <n-space align="center" :wrap="true" :size="12">
        <n-select
          v-model:value="selectedDeviceId"
          :options="deviceOptions"
          placeholder="请选择设备"
          filterable
          style="width: 300px"
          @update:value="handleDeviceChange"
        />
        <n-date-picker
          v-model:value="timeRange"
          type="datetimerange"
          clearable
          style="width: 380px"
          @update:value="loadMetrics"
        />
        <n-button type="primary" @click="loadMetrics" :loading="loading">
          查询
        </n-button>
      </n-space>
    </n-card>

    <!-- 性能概览 -->
    <div v-if="selectedDeviceId" class="stats-grid stats-grid-4">
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8f0ff">
          <n-icon size="24" color="#165dff"><HardwareChipOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value" :class="{ loading: loading }">
            {{ loading ? '-' : metrics.cpu }}%
          </div>
          <div class="stat-title">CPU使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8ffea">
          <n-icon size="24" color="#00b42a"><Tickets /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value" :class="{ loading: loading }">
            {{ loading ? '-' : metrics.memory }}%
          </div>
          <div class="stat-title">内存使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff7e6">
          <n-icon size="24" color="#ff7d00"><FolderOpenOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value" :class="{ loading: loading }">
            {{ loading ? '-' : metrics.disk }}%
          </div>
          <div class="stat-title">磁盘使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff1f0">
          <n-icon size="24" color="#f53f3f"><CloudOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value" :class="{ loading: loading }">
            {{ loading ? '-' : metrics.network }}
          </div>
          <div class="stat-title">网络带宽 (Mbps)</div>
        </div>
      </div>
    </div>

    <!-- 空状态：未选择设备 -->
    <n-card v-if="!selectedDeviceId" class="empty-state-card">
      <div class="empty-state">
        <n-icon size="64" color="#c0c4cc"><ServerOutline /></n-icon>
        <p class="empty-title">请选择设备</p>
        <p class="empty-desc">从上方下拉框选择一个设备，即可查看其性能指标和历史趋势</p>
      </div>
    </n-card>

    <!-- 性能图表 -->
    <div v-if="selectedDeviceId" class="performance-grid">
      <n-card title="CPU使用率趋势">
        <template #header-extra>
          <span v-if="lastUpdateTime" class="update-time">更新于 {{ lastUpdateTime }}</span>
        </template>
        <div ref="cpuChartRef" class="chart-container"></div>
      </n-card>
      <n-card title="内存使用率趋势">
        <template #header-extra>
          <span v-if="lastUpdateTime" class="update-time">更新于 {{ lastUpdateTime }}</span>
        </template>
        <div ref="memoryChartRef" class="chart-container"></div>
      </n-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { NIcon, useMessage } from 'naive-ui'
import * as echarts from 'echarts'
import {
  HardwareChipOutline, FolderOpenOutline, CloudOutline, Refresh, ServerOutline
} from '@vicons/ionicons5'

const message = useMessage()

const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
let cpuChart = null
let memoryChart = null
let refreshTimer = null

const loading = ref(false)
const selectedDeviceId = ref(null)
const timeRange = ref(null)
const deviceList = ref([])
const deviceOptions = ref([])
const lastUpdateTime = ref('')

const metrics = reactive({ cpu: 0, memory: 0, disk: 0, network: 0 })

const columns = [
  { title: '序号', type: 'index', width: 60 },
  { title: '设备名称', key: 'name', width: 150 },
  { title: 'IP地址', key: 'ip_address', width: 140 },
  { title: '操作系统', key: 'os_type', width: 100 },
  { title: '系统版本', key: 'os_version', width: 120 },
  { title: '厂商', key: 'manufacturer', width: 120 },
  { title: '型号', key: 'model', width: 120 },
  { title: '状态', key: 'status', width: 100,
    render: (row) => {
      const statusMap = { online: '在线', offline: '离线', warning: '告警' }
      return statusMap[row.status] || row.status
    }
  },
  { title: '最后采集', key: 'last_collect_time', width: 180 },
  { title: '位置', key: 'location', width: 150 }
]

onMounted(() => {
  loadDevices()
  startRefresh()
})

onUnmounted(() => {
  stopRefresh()
  cpuChart?.dispose()
  memoryChart?.dispose()
  window.removeEventListener('resize', handleResize)
})

const loadDevices = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/assets/device?page=1&page_size=100', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    deviceList.value = data.items || data.data?.items || []
    deviceOptions.value = deviceList.value.map(d => ({
      label: `${d.name} (${d.ip_address})`,
      value: d.id
    }))
  } catch (e) {
    message.error(`加载设备失败: ${e.message}`)
    console.error('[performance] loadDevices error:', e)
    deviceList.value = []
  } finally {
    loading.value = false
  }
}

const handleDeviceChange = (value) => {
  selectedDeviceId.value = value
  // Reset metrics display
  metrics.cpu = 0
  metrics.memory = 0
  metrics.disk = 0
  metrics.network = 0
  lastUpdateTime.value = ''
  loadMetrics()
}

const loadMetrics = async () => {
  if (!selectedDeviceId.value) return

  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const body = {
      device_id: selectedDeviceId.value,
      metrics: ['cpu', 'memory', 'disk', 'network'],
      start_time: timeRange.value ? timeRange.value[0] : Date.now() - 3600000,
      end_time: timeRange.value ? timeRange.value[1] : Date.now()
    }
    const res = await fetch('/api/v1/monitoring/metrics/query', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')

    metrics.cpu = data.cpu ?? 0
    metrics.memory = data.memory ?? 0
    metrics.disk = data.disk ?? 0
    metrics.network = data.network ?? 0

    lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

    updateCharts(data)
  } catch (e) {
    message.error(`加载指标失败: ${e.message}`)
    console.error('[performance] loadMetrics error:', e)
  } finally {
    loading.value = false
  }
}

const updateCharts = (data) => {
  // Generate time labels from actual data length
  const dataLen = (data.cpu_history || []).length || 24
  const hours = Array.from({ length: dataLen }, (_, i) => {
    const totalPoints = dataLen
    const timeSpan = timeRange.value
      ? (timeRange.value[1] - timeRange.value[0]) / 3600000
      : 24
    const hour = new Date(timeRange.value ? timeRange.value[0] : Date.now() - 3600000)
    hour.setHours(hour.getHours() + Math.floor((i / totalPoints) * timeSpan))
    return `${hour.getHours().toString().padStart(2, '0')}:00`
  })

  const cpuData = data.cpu_history || []
  const memData = data.memory_history || []

  if (cpuChartRef.value) {
    if (!cpuChart) cpuChart = echarts.init(cpuChartRef.value)
    cpuChart.setOption({
      tooltip: { trigger: 'axis', formatter: (params) => {
        const p = params[0]
        return `${p.axisValue}<br/>${p.marker} CPU: ${p.value}%`
      }},
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: hours, boundaryGap: false },
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: cpuData,
        lineStyle: { color: '#165dff' },
        itemStyle: { color: '#165dff' },
        showSymbol: cpuData.length < 20,
        emphasis: { focus: 'series' }
      }]
    })
  }

  if (memoryChartRef.value) {
    if (!memoryChart) memoryChart = echarts.init(memoryChartRef.value)
    memoryChart.setOption({
      tooltip: { trigger: 'axis', formatter: (params) => {
        const p = params[0]
        return `${p.axisValue}<br/>${p.marker} 内存: ${p.value}%`
      }},
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: hours, boundaryGap: false },
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: memData,
        lineStyle: { color: '#00b42a' },
        itemStyle: { color: '#00b42a' },
        showSymbol: memData.length < 20,
        emphasis: { focus: 'series' }
      }]
    })
  }
}

const handleResize = () => {
  cpuChart?.resize()
  memoryChart?.resize()
}

window.addEventListener('resize', handleResize)

const startRefresh = () => {
  refreshTimer = setInterval(() => {
    if (selectedDeviceId.value) loadMetrics()
  }, 30000)
}

const stopRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}
</script>


<style lang="scss" scoped>
.mb-4 { margin-bottom: 16px; }
.stats-grid-4 { grid-template-columns: repeat(4, 1fr); }
.performance-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin: 20px 0;
}
.chart-container { width: 100%; height: 300px; }

.empty-state-card {
  margin: 20px 0;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}
.empty-title {
  margin-top: 16px;
  font-size: 16px;
  color: #606266;
  font-weight: 500;
}
.empty-desc {
  margin-top: 8px;
  font-size: 14px;
  color: #909399;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  transition: color 0.3s;
  &.loading {
    color: #c0c4cc;
  }
}

.update-time {
  font-size: 12px;
  color: #909399;
}
</style>
