<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">性能监控</h1>
        <p class="page-subtitle">实时监控系统性能指标</p>
      </div>
      <div class="page-actions">
        <el-select v-model="currentDevice" placeholder="选择设备" size="default" style="width: 200px; margin-right: 12px;" :loading="deviceLoading" @change="handleDeviceChange">
          <el-option v-for="device in deviceList" :key="device.id || device.name" :label="device.name" :value="device.name" />
        </el-select>
        <el-select v-model="chartMetricType" placeholder="指标类型" size="default" style="width: 140px; margin-right: 12px;">
          <el-option label="CPU" value="cpu" />
          <el-option label="内存" value="memory" />
          <el-option label="磁盘" value="disk" />
          <el-option label="网络" value="network" />
        </el-select>
        <el-button @click="loadData" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 性能概览 -->
    <div class="stats-grid stats-grid-4">
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8f0ff">
          <el-icon size="24" color="#165dff"><Cpu /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ currentMetrics.cpu }}%</div>
          <div class="stat-title">CPU使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8ffea">
          <el-icon size="24" color="#00b42a"><Tickets /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ currentMetrics.memory }}%</div>
          <div class="stat-title">内存使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff7e6">
          <el-icon size="24" color="#ff7d00"><FolderOpened /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ currentMetrics.disk }}%</div>
          <div class="stat-title">磁盘使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff1f0">
          <el-icon size="24" color="#f53f3f"><Connection /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ currentMetrics.network }} Mbps</div>
          <div class="stat-title">网络带宽</div>
        </div>
      </div>
    </div>

    <!-- 实时图表区域 -->
    <div class="performance-grid">
      <div class="card">
        <div class="card-header">
          <span class="card-title">{{ metricTypeLabel }}使用率趋势</span>
          <el-tag type="info">过去24小时</el-tag>
        </div>
        <div class="card-body">
          <div ref="mainChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 性能排行榜 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">性能排行 Top10</span>
          <el-radio-group v-model="rankType" size="small" @change="handleRankTypeChange">
            <el-radio-button value="cpu">CPU</el-radio-button>
            <el-radio-button value="memory">内存</el-radio-button>
            <el-radio-button value="disk">磁盘</el-radio-button>
          </el-radio-group>
        </div>
        <div class="card-body">
          <div v-if="rankList.length === 0 && !rankLoading" class="empty-tip">
            <el-empty description="暂无排行数据" />
          </div>
          <el-table v-else :data="rankList" style="width: 100%" v-loading="rankLoading">
            <el-table-column type="index" label="排名" width="60" />
            <el-table-column prop="name" label="设备名称" min-width="120" show-overflow-tooltip />
            <el-table-column prop="ip" label="IP地址" width="130" />
            <el-table-column :prop="rankType" label="使用率" width="160">
              <template #default="{ row }">
                <el-progress :percentage="row[rankType]" :color="getProgressColor(row[rankType])" :stroke-width="8" />
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- 辅助图表：其他指标趋势 -->
    <div class="performance-grid" v-if="chartMetricType !== 'cpu'">
      <div class="card">
        <div class="card-header">
          <span class="card-title">CPU使用率趋势</span>
          <el-tag type="info">过去24小时</el-tag>
        </div>
        <div class="card-body">
          <div ref="cpuChartRef" class="chart-container"></div>
        </div>
      </div>
      <div class="card" v-if="chartMetricType !== 'memory'">
        <div class="card-header">
          <span class="card-title">内存使用率趋势</span>
          <el-tag type="info">过去24小时</el-tag>
        </div>
        <div class="card-body">
          <div ref="memoryChartRef" class="chart-container"></div>
        </div>
      </div>
      <div class="card" v-if="chartMetricType !== 'disk'">
        <div class="card-header">
          <span class="card-title">磁盘使用率趋势</span>
          <el-tag type="info">过去24小时</el-tag>
        </div>
        <div class="card-body">
          <div ref="diskChartRef" class="chart-container"></div>
        </div>
      </div>
      <div class="card" v-if="chartMetricType !== 'network'">
        <div class="card-header">
          <span class="card-title">网络带宽趋势</span>
          <el-tag type="info">过去24小时</el-tag>
        </div>
        <div class="card-body">
          <div ref="networkChartRef" class="chart-container"></div>
        </div>
      </div>
    </div>

    <!-- 全指标图表（当选择了特定指标时显示其他三个） -->
    <div class="performance-grid" v-else>
      <div class="card">
        <div class="card-header">
          <span class="card-title">内存使用率趋势</span>
          <el-tag type="info">过去24小时</el-tag>
        </div>
        <div class="card-body">
          <div ref="memoryChartRef" class="chart-container"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">磁盘使用率趋势</span>
          <el-tag type="info">过去24小时</el-tag>
        </div>
        <div class="card-body">
          <div ref="diskChartRef" class="chart-container"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">网络带宽趋势</span>
          <el-tag type="info">过去24小时</el-tag>
        </div>
        <div class="card-body">
          <div ref="networkChartRef" class="chart-container"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Cpu, FolderOpened, Connection, Refresh, Tickets } from '@element-plus/icons-vue'
import { performance, devices } from '@/api'
import { ElMessage } from 'element-plus'

// Chart refs
const mainChartRef = ref(null)
const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
const diskChartRef = ref(null)
const networkChartRef = ref(null)

let mainChart = null
let cpuChart = null
let memoryChart = null
let diskChart = null
let networkChart = null
let refreshTimer = null

// State
const loading = ref(false)
const deviceLoading = ref(false)
const rankLoading = ref(false)
const deviceList = ref([])
const rankList = ref([])
const currentDevice = ref('')
const chartMetricType = ref('cpu')
const rankType = ref('cpu')

// Current device metrics
const currentMetrics = reactive({ cpu: 0, memory: 0, disk: 0, network: 0 })

// Metric type label mapping
const metricTypeLabel = computed(() => {
  const labels = { cpu: 'CPU', memory: '内存', disk: '磁盘', network: '网络' }
  return labels[chartMetricType.value] || chartMetricType.value
})

// Chart color mapping
const chartColors = {
  cpu: '#165dff',
  memory: '#00b42a',
  disk: '#ff7d00',
  network: '#f53f3f'
}

// Get device list
const fetchDeviceList = async () => {
  deviceLoading.value = true
  try {
    const res = await devices.getList({ page: 1, page_size: 100 })
    if (res && res.items && res.items.length > 0) {
      deviceList.value = res.items
      // Select first device by default if not set
      if (!currentDevice.value) {
        currentDevice.value = res.items[0].name
      }
    } else {
      deviceList.value = []
      ElMessage.warning('未获取到设备列表')
    }
  } catch (e) {
    console.error('获取设备列表失败:', e)
    ElMessage.error('获取设备列表失败')
    deviceList.value = []
  } finally {
    deviceLoading.value = false
  }
}

// Fetch real-time metrics for current device
const fetchDeviceMetrics = async () => {
  if (!currentDevice.value) return
  
  try {
    const res = await performance.getDeviceMetrics(currentDevice.value)
    if (res && res.metrics) {
      const m = res.metrics
      // CPU
      if (m.cpu && m.cpu.usage !== undefined) {
        currentMetrics.cpu = Math.round(m.cpu.usage)
      } else if (m.cpu && m.cpu.usage_percent !== undefined) {
        currentMetrics.cpu = Math.round(m.cpu.usage_percent)
      }
      
      // Memory
      if (m.memory) {
        if (m.memory.usage_percent !== undefined) {
          currentMetrics.memory = Math.round(m.memory.usage_percent)
        } else if (m.memory.used_percent !== undefined) {
          currentMetrics.memory = Math.round(m.memory.used_percent)
        } else if (m.memory.used_mb && m.memory.total_mb) {
          currentMetrics.memory = Math.round((m.memory.used_mb / m.memory.total_mb) * 100)
        }
      }
      
      // Disk
      if (m.disks && m.disks.length > 0) {
        const disk = m.disks.find(d => d.usage_percent !== undefined) || m.disks[0]
        if (disk.usage_percent !== undefined) {
          currentMetrics.disk = Math.round(disk.usage_percent)
        } else if (disk.used_percent !== undefined) {
          currentMetrics.disk = Math.round(disk.used_percent)
        }
      } else if (m.disk) {
        if (m.disk.usage_percent !== undefined) {
          currentMetrics.disk = Math.round(m.disk.usage_percent)
        } else if (m.disk.used_percent !== undefined) {
          currentMetrics.disk = Math.round(m.disk.used_percent)
        }
      }
      
      // Network (bandwidth in Mbps)
      if (m.network) {
        if (m.network.bandwidth_mbps !== undefined) {
          currentMetrics.network = Math.round(m.network.bandwidth_mbps)
        } else if (m.network.speed_mbps !== undefined) {
          currentMetrics.network = Math.round(m.network.speed_mbps)
        } else if (m.network.usage_mbps !== undefined) {
          currentMetrics.network = Math.round(m.network.usage_mbps)
        }
      }
    } else if (res && res.cpu !== undefined) {
      // Alternative response format
      currentMetrics.cpu = Math.round(res.cpu)
      currentMetrics.memory = Math.round(res.memory || 0)
      currentMetrics.disk = Math.round(res.disk || 0)
      currentMetrics.network = Math.round(res.network || 0)
    }
  } catch (e) {
    console.error('获取设备指标失败:', e)
  }
}

// Fetch history data for a specific metric type
const fetchMetricHistory = async (metricType, hours = 24) => {
  if (!currentDevice.value) return []
  
  try {
    const res = await performance.getDeviceMetricsHistory(currentDevice.value, metricType, hours)
    if (res && res.points && res.points.length > 0) {
      return res.points.map(p => ({
        timestamp: p.timestamp,
        value: typeof p.value === 'number' ? p.value : parseFloat(p.value) || 0
      }))
    } else if (res && Array.isArray(res)) {
      return res.map(p => ({
        timestamp: p.timestamp || p.time,
        value: typeof p.value === 'number' ? p.value : parseFloat(p.value) || 0
      }))
    }
  } catch (e) {
    console.error(`获取${metricType}历史数据失败:`, e)
  }
  return []
}

// Create chart options
const createChartOption = (data, color, yAxisMax = 100, unit = '%') => {
  const hours = data.length > 0 
    ? data.map(p => {
        const d = new Date(p.timestamp)
        return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
      })
    : []
  
  const values = data.length > 0 
    ? data.map(p => p.value)
    : []

  return {
    tooltip: { 
      trigger: 'axis',
      formatter: (params) => {
        if (params && params[0]) {
          return `${params[0].name}<br/>${params[0].value}${unit}`
        }
        return ''
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: { 
      type: 'category', 
      data: hours, 
      boundaryGap: false,
      axisLabel: { interval: Math.floor(hours.length / 6) }
    },
    yAxis: { 
      type: 'value', 
      max: yAxisMax, 
      axisLabel: { formatter: `{value}${unit}` } 
    },
    series: [{
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.3 },
      data: values,
      lineStyle: { color },
      itemStyle: { color },
      symbol: 'circle',
      symbolSize: 4
    }]
  }
}

// Initialize or update a chart
const initOrUpdateChart = (chartInstance, chartRef, data, color, yAxisMax, unit) => {
  if (!chartRef.value) return
  
  if (!chartInstance) {
    const chart = echarts.init(chartRef.value)
    chart.setOption(createChartOption(data, color, yAxisMax, unit))
    return chart
  } else {
    chartInstance.setOption(createChartOption(data, color, yAxisMax, unit), true)
    return chartInstance
  }
}

// Load all charts
const loadCharts = async () => {
  if (!currentDevice.value) return
  
  try {
    // Fetch all metric history data in parallel
    const [cpuData, memoryData, diskData, networkData] = await Promise.all([
      fetchMetricHistory('cpu'),
      fetchMetricHistory('memory'),
      fetchMetricHistory('disk'),
      fetchMetricHistory('network')
    ])

    // Main chart based on selected type
    mainChart = initOrUpdateChart(mainChart, mainChartRef, 
      chartMetricType.value === 'cpu' ? cpuData : 
      chartMetricType.value === 'memory' ? memoryData :
      chartMetricType.value === 'disk' ? diskData : networkData,
      chartColors[chartMetricType.value])

    // Other charts
    cpuChart = initOrUpdateChart(cpuChart, cpuChartRef, cpuData, chartColors.cpu)
    memoryChart = initOrUpdateChart(memoryChart, memoryChartRef, memoryData, chartColors.memory)
    diskChart = initOrUpdateChart(diskChart, diskChartRef, diskData, chartColors.disk)
    networkChart = initOrUpdateChart(networkChart, networkChartRef, networkData, chartColors.network, 1000, ' Mbps')
  } catch (e) {
    console.error('加载图表失败:', e)
  }
}

// Fetch rank list (top 10 devices by specified metric)
const fetchRankList = async () => {
  rankLoading.value = true
  try {
    // Get all devices
    const res = await devices.getList({ page: 1, page_size: 50 })
    if (!res || !res.items || res.items.length === 0) {
      rankList.value = []
      return
    }

    // Fetch metrics for each device in parallel
    const deviceMetricsPromises = res.items.slice(0, 20).map(async (device) => {
      try {
        const metricsRes = await performance.getDeviceMetrics(device.name)
        if (metricsRes && metricsRes.metrics) {
          const m = metricsRes.metrics
          let cpu = 0, memory = 0, disk = 0
          
          if (m.cpu) {
            cpu = m.cpu.usage ?? m.cpu.usage_percent ?? 0
          }
          if (m.memory) {
            memory = m.memory.usage_percent ?? m.memory.used_percent ?? 0
            if (!memory && m.memory.used_mb && m.memory.total_mb) {
              memory = (m.memory.used_mb / m.memory.total_mb) * 100
            }
          }
          if (m.disks && m.disks.length > 0) {
            const d = m.disks.find(d => d.usage_percent !== undefined) || m.disks[0]
            disk = d.usage_percent ?? d.used_percent ?? 0
          } else if (m.disk) {
            disk = m.disk.usage_percent ?? m.disk.used_percent ?? 0
          }
          
          return {
            name: device.name,
            ip: device.ip_address || device.ip || '-',
            cpu: Math.round(cpu),
            memory: Math.round(memory),
            disk: Math.round(disk)
          }
        }
      } catch (e) {
        // Skip failed devices
      }
      return null
    })

    const results = await Promise.allSettled(deviceMetricsPromises)
    const validResults = results
      .filter(r => r.status === 'fulfilled' && r.value)
      .map(r => r.value)

    // Sort by rank type and take top 10
    rankList.value = validResults
      .sort((a, b) => b[rankType.value] - a[rankType.value])
      .slice(0, 10)
  } catch (e) {
    console.error('获取排行列表失败:', e)
    rankList.value = []
  } finally {
    rankLoading.value = false
  }
}

// Handle window resize
const handleResize = () => {
  mainChart?.resize()
  cpuChart?.resize()
  memoryChart?.resize()
  diskChart?.resize()
  networkChart?.resize()
}

// Start auto refresh (every 5 seconds)
const startRefresh = () => {
  stopRefresh()
  refreshTimer = setInterval(async () => {
    await fetchDeviceMetrics()
  }, 5000)
}

// Stop auto refresh
const stopRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// Load all data
const loadData = async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchDeviceMetrics(),
      loadCharts(),
      fetchRankList()
    ])
  } catch (e) {
    console.error('加载数据失败:', e)
  } finally {
    loading.value = false
  }
}

// Handle device change
const handleDeviceChange = async () => {
  await Promise.all([
    fetchDeviceMetrics(),
    loadCharts()
  ])
}

// Handle rank type change
const handleRankTypeChange = () => {
  // Just re-sort the existing list
  if (rankList.value.length > 0) {
    rankList.value = [...rankList.value].sort((a, b) => b[rankType.value] - a[rankType.value])
  }
}

// Get progress color based on value
const getProgressColor = (value) => {
  if (value >= 90) return '#f53f3f'
  if (value >= 70) return '#ff7d00'
  return '#00b42a'
}

// Lifecycle
onMounted(async () => {
  await fetchDeviceList()
  if (currentDevice.value) {
    await loadData()
    startRefresh()
  }
  
  nextTick(() => {
    window.addEventListener('resize', handleResize)
  })
})

onUnmounted(() => {
  stopRefresh()
  window.removeEventListener('resize', handleResize)
  
  mainChart?.dispose()
  cpuChart?.dispose()
  memoryChart?.dispose()
  diskChart?.dispose()
  networkChart?.dispose()
})
</script>

<style lang="scss" scoped>
.stats-grid-4 {
  grid-template-columns: repeat(4, 1fr);
}

.performance-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-container {
  width: 100%;
  height: 280px;
}

.empty-tip {
  padding: 40px 0;
  text-align: center;
}

:deep(.el-table) {
  .el-table__header th {
    background: #f7f8fa;
  }
}

.page-actions {
  display: flex;
  align-items: center;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
