<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">性能监控</h1>
        <p class="page-subtitle">实时监控系统性能指标</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadData">
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
          <div class="stat-value">{{ metrics.cpu }}%</div>
          <div class="stat-title">CPU使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8ffea">
          <el-icon size="24" color="#00b42a"><Tickets /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ metrics.memory }}%</div>
          <div class="stat-title">内存使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff7e6">
          <el-icon size="24" color="#ff7d00"><FolderOpened /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ metrics.disk }}%</div>
          <div class="stat-title">磁盘使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff1f0">
          <el-icon size="24" color="#f53f3f"><Connection /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ metrics.network }} Mbps</div>
          <div class="stat-title">网络带宽</div>
        </div>
      </div>
    </div>

    <!-- 性能图表 -->
    <div class="performance-grid">
      <div class="card">
        <div class="card-header">
          <span class="card-title">CPU使用率趋势</span>
        </div>
        <div class="card-body">
          <div ref="cpuChartRef" class="chart-container"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">内存使用率趋势</span>
        </div>
        <div class="card-body">
          <div ref="memoryChartRef" class="chart-container"></div>
        </div>
      </div>
    </div>

    <!-- 性能排行榜 -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">资源使用排行</span>
        <el-radio-group v-model="rankType" size="small">
          <el-radio-button value="cpu">CPU</el-radio-button>
          <el-radio-button value="memory">内存</el-radio-button>
          <el-radio-button value="disk">磁盘</el-radio-button>
        </el-radio-group>
      </div>
      <div class="card-body">
        <el-table :data="rankList" style="width: 100%">
          <el-table-column type="index" label="排名" width="80" />
          <el-table-column prop="name" label="设备名称" />
          <el-table-column prop="ip" label="IP地址" width="140" />
          <el-table-column :prop="rankType" label="使用率" width="200">
            <template #default="{ row }">
              <el-progress :percentage="row[rankType]" :color="getProgressColor(row[rankType])" :stroke-width="8" />
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { Cpu, FolderOpened, Connection, Refresh } from '@element-plus/icons-vue'
import { performance, devices } from '@/api'
import { ElMessage } from 'element-plus'

const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
let cpuChart = null
let memoryChart = null
let refreshTimer = null

const rankType = ref('cpu')
const metrics = reactive({ cpu: 0, memory: 0, disk: 0, network: 0 })
const rankList = ref([])
const currentDevice = ref('Web服务器-01')  // 默认设备，实际应从设备列表选择
const deviceList = ref([])
const loading = ref(false)

// 获取设备列表
const fetchDeviceList = async () => {
  try {
    const res = await devices.getList({ page: 1, page_size: 100 })
    if (res && res.items) {
      deviceList.value = res.items
      // 选择第一个有状态的设备
      const onlineDevice = res.items.find(d => d.status === 'online')
      if (onlineDevice) {
        currentDevice.value = onlineDevice.name
      } else if (res.items.length > 0) {
        currentDevice.value = res.items[0].name
      }
    }
  } catch (e) {
    console.error('获取设备列表失败:', e)
  }
}

// 获取设备实时指标
const fetchDeviceMetrics = async () => {
  try {
    const res = await performance.getDeviceMetrics(currentDevice.value)
    if (res && res.metrics) {
      const m = res.metrics
      // CPU
      if (m.cpu && m.cpu.usage !== undefined) {
        metrics.cpu = Math.round(m.cpu.usage)
      }
      // 内存
      if (m.memory) {
        if (m.memory.usage_percent !== undefined) {
          metrics.memory = Math.round(m.memory.usage_percent)
        } else if (m.memory.used_mb && m.memory.total_mb) {
          metrics.memory = Math.round((m.memory.used_mb / m.memory.total_mb) * 100)
        }
      }
      // 磁盘
      if (m.disks && m.disks.length > 0) {
        const disk = m.disks.find(d => d.usage_percent !== undefined) || m.disks[0]
        if (disk.usage_percent !== undefined) {
          metrics.disk = Math.round(disk.usage_percent)
        }
      }
      // 网络
      if (m.network && m.network.bandwidth_mbps !== undefined) {
        metrics.network = Math.round(m.network.bandwidth_mbps)
      }
    }
  } catch (e) {
    console.error('获取设备指标失败:', e)
  }
}

// 获取图表历史数据
const fetchChartData = async (metricType) => {
  try {
    const res = await performance.getDeviceMetricsHistory(currentDevice.value, metricType, 24)
    if (res && res.points && res.points.length > 0) {
      return res.points.map(p => ({
        timestamp: p.timestamp,
        value: p.value
      }))
    }
  } catch (e) {
    console.error(`获取${metricType}历史数据失败:`, e)
  }
  return []
}

// 初始化图表
const initCharts = async () => {
  // 获取过去24小时的数据
  const cpuData = await fetchChartData('cpu')
  const memoryData = await fetchChartData('memory')
  
  // 生成24小时时间标签
  const hours = cpuData.length > 0 
    ? cpuData.map(p => {
        const d = new Date(p.timestamp)
        return `${d.getHours().toString().padStart(2, '0')}:00`
      })
    : Array.from({ length: 24 }, (_, i) => `${i}:00`)
  
  // 使用真实数据，如果没有则用当前指标值填充
  const cpuValues = cpuData.length > 0 
    ? cpuData.map(p => p.value)
    : Array.from({ length: 24 }, () => metrics.cpu)
  
  const memoryValues = memoryData.length > 0 
    ? memoryData.map(p => p.value)
    : Array.from({ length: 24 }, () => metrics.memory)

  if (cpuChartRef.value) {
    cpuChart = echarts.init(cpuChartRef.value)
    cpuChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: hours, boundaryGap: false },
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: cpuValues,
        lineStyle: { color: '#165dff' },
        itemStyle: { color: '#165dff' }
      }]
    })
  }

  if (memoryChartRef.value) {
    memoryChart = echarts.init(memoryChartRef.value)
    memoryChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: hours, boundaryGap: false },
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: memoryValues,
        lineStyle: { color: '#00b42a' },
        itemStyle: { color: '#00b42a' }
      }]
    })
  }

  window.addEventListener('resize', handleResize)
}

// 更新图表数据
const updateCharts = async () => {
  if (!cpuChart || !memoryChart) return
  
  try {
    const cpuData = await fetchChartData('cpu')
    const memoryData = await fetchChartData('memory')
    
    if (cpuData.length > 0) {
      const hours = cpuData.map(p => {
        const d = new Date(p.timestamp)
        return `${d.getHours().toString().padStart(2, '0')}:00`
      })
      cpuChart.setOption({
        xAxis: { data: hours },
        series: [{ data: cpuData.map(p => p.value) }]
      })
    }
    
    if (memoryData.length > 0) {
      memoryChart.setOption({
        series: [{ data: memoryData.map(p => p.value) }]
      })
    }
  } catch (e) {
    console.error('更新图表失败:', e)
  }
}

// 获取设备排行榜
const fetchRankList = async () => {
  try {
    const res = await devices.getList({ page: 1, page_size: 50 })
    if (res && res.items) {
      const list = []
      for (const device of res.items) {
        try {
          const metricsRes = await performance.getDeviceMetrics(device.name)
          if (metricsRes && metricsRes.metrics) {
            const m = metricsRes.metrics
            let cpu = 0, memory = 0, disk = 0
            if (m.cpu && m.cpu.usage !== undefined) cpu = m.cpu.usage
            if (m.memory) {
              memory = m.memory.usage_percent || 
                (m.memory.used_mb && m.memory.total_mb ? (m.memory.used_mb / m.memory.total_mb) * 100 : 0)
            }
            if (m.disks && m.disks.length > 0) {
              const d = m.disks.find(d => d.usage_percent !== undefined) || m.disks[0]
              disk = d.usage_percent || 0
            }
            list.push({
              name: device.name,
              ip: device.ip_address,
              cpu: Math.round(cpu),
              memory: Math.round(memory),
              disk: Math.round(disk)
            })
          }
        } catch (e) {
          // 忽略单个设备失败
        }
      }
      // 按指定类型排序
      rankList.value = list.sort((a, b) => b[rankType.value] - a[rankType.value]).slice(0, 10)
    }
  } catch (e) {
    console.error('获取排行列表失败:', e)
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await fetchDeviceList()
    await fetchDeviceMetrics()
    await initCharts()
    await fetchRankList()
    startRefresh()
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  stopRefresh()
  cpuChart?.dispose()
  memoryChart?.dispose()
})

const startRefresh = () => {
  refreshTimer = setInterval(async () => {
    await fetchDeviceMetrics()
    await updateCharts()
  }, 5000)
}

const stopRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

const handleResize = () => {
  cpuChart?.resize()
  memoryChart?.resize()
}

const loadData = async () => {
  loading.value = true
  try {
    await fetchDeviceMetrics()
    await updateCharts()
    await fetchRankList()
  } finally {
    loading.value = false
  }
}

// 设备切换时重新加载数据
watch(currentDevice, async () => {
  await fetchDeviceMetrics()
  await initCharts()
  await fetchRankList()
})

const getProgressColor = (value) => {
  if (value >= 90) return '#f53f3f'
  if (value >= 70) return '#ff7d00'
  return '#00b42a'
}
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
  height: 300px;
}

:deep(.el-table) {
  .el-table__header th {
    background: #f7f8fa;
  }
}
</style>
