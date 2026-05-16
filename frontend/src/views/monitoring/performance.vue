<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">性能监控</h1>
        <p class="page-subtitle">实时监控系统性能指标</p>
      </div>
      <div class="page-actions">
        <n-button @click="loadData">
          <n-icon><RefreshOutline /></n-icon> 刷新
        </n-button>
      </div>
    </div>
    <!-- 性能概览 -->
    <div class="stats-grid stats-grid-4">
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8f0ff">
          <n-icon size="24" color="#18a058"><CpuOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ metrics.cpu }}%</div>
          <div class="stat-title">CPU使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8ffea">
          <n-icon size="24" color="#00b42a"><DocumentsOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ metrics.memory }}%</div>
          <div class="stat-title">内存使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff7e6">
          <n-icon size="24" color="#ff7d00"><FolderOpenOutline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ metrics.disk }}%</div>
          <div class="stat-title">磁盘使用率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff1f0">
          <n-icon size="24" color="#f53f3f"><WifiOutline /></n-icon>
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
        <n-radio-group v-model="rankType" size="small">
          <n-radio-button value="cpu">CPU</n-radio-button>
          <n-radio-button value="memory">内存</n-radio-button>
          <n-radio-button value="disk">磁盘</n-radio-button>
        </n-radio-group>
      </div>
      <div class="card-body">
        <n-data-table :data="rankList" style="width: 100%">
          <n-data-table-column type="index" label="排名" width="80" />
          <n-data-table-column prop="name" label="设备名称" />
          <n-data-table-column prop="ip" label="IP地址" width="140" />
          <n-data-table-column :prop="rankType" label="使用率" width="200">
            <template #default="{ row }">
              <n-progress :percentage="row[rankType]" :color="getProgressColor(row[rankType])" :stroke-width="8" />
            </template>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { performance } from '@/api'
const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
let cpuChart = null
let memoryChart = null
let refreshTimer = null
const rankType = ref('cpu')
const metrics = reactive({ cpu: 45, memory: 62, disk: 38, network: 156 })
const rankList = ref([
  { name: 'Web Server 01', ip: '192.168.1.10', cpu: 85, memory: 72, disk: 45 },
  { name: 'DB Server 01', ip: '192.168.1.11', cpu: 78, memory: 88, disk: 62 },
  { name: 'App Server 01', ip: '192.168.1.12', cpu: 65, memory: 55, disk: 38 },
  { name: 'Cache Server 01', ip: '192.168.1.13', cpu: 52, memory: 45, disk: 28 },
  { name: 'Storage Server 01', ip: '192.168.1.14', cpu: 48, memory: 35, disk: 92 }
])
onMounted(() => {
  initCharts()
  startRefresh()
})
onUnmounted(() => {
  stopRefresh()
  cpuChart?.dispose()
  memoryChart?.dispose()
})
const initCharts = () => {
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
  const data = () => Array.from({ length: 24 }, () => Math.floor(Math.random() * 40 + 30))
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
        data: data(),
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
        data: data(),
        lineStyle: { color: '#00b42a' },
        itemStyle: { color: '#00b42a' }
      }]
    })
  }
  window.addEventListener('resize', handleResize)
}
const startRefresh = () => {
  refreshTimer = setInterval(() => {
    metrics.cpu = Math.floor(Math.random() * 30 + 40)
    metrics.memory = Math.floor(Math.random() * 20 + 55)
    metrics.disk = Math.floor(Math.random() * 10 + 35)
    metrics.network = Math.floor(Math.random() * 100 + 100)
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
  // 实际项目中加载数据
}
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
