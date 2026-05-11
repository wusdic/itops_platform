<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">智能分析</h1>
        <p class="page-subtitle">AI驱动的数据分析和决策支持</p>
      </div>
    </div>

    <div class="analyze-grid">
      <div class="card">
        <div class="card-header">
          <span class="card-title">系统健康度分析</span>
        </div>
        <div class="card-body">
          <div ref="healthChartRef" class="chart-container"></div>
          <div class="health-score">
            <span class="score-label">综合健康度</span>
            <span class="score-value">85</span>
            <span class="score-unit">分</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">异常检测</span>
        </div>
        <div class="card-body">
          <el-table :data="anomalyList" style="width: 100%">
            <el-table-column prop="type" label="异常类型" />
            <el-table-column prop="device" label="设备" />
            <el-table-column prop="level" label="等级" width="80">
              <template #default="{ row }">
                <el-tag :type="row.level === 'high' ? 'danger' : 'warning'" size="small">{{ row.level === 'high' ? '高' : '中' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="发现时间" width="160" />
          </el-table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">容量预测</span>
        </div>
        <div class="card-body">
          <div ref="forecastChartRef" class="chart-container"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">优化建议</span>
        </div>
        <div class="card-body">
          <div class="suggestion-list">
            <div v-for="(s, i) in suggestions" :key="i" class="suggestion-item">
              <el-icon :color="s.type === 'warning' ? '#ff7d00' : '#165dff'" size="20"><Warning v-if="s.type === 'warning'" /><InfoFilled v-else /></el-icon>
              <div class="suggestion-content">
                <div class="suggestion-title">{{ s.title }}</div>
                <div class="suggestion-desc">{{ s.desc }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { Warning, InfoFilled } from '@element-plus/icons-vue'

const healthChartRef = ref(null)
const forecastChartRef = ref(null)
let healthChart = null
let forecastChart = null

const anomalyList = reactive([
  { type: 'CPU使用率异常', device: 'Web Server 01', level: 'high', time: '2024-01-15 14:30' },
  { type: '内存使用率偏高', device: 'DB Server 01', level: 'medium', time: '2024-01-15 13:20' },
  { type: '磁盘IO延迟', device: 'Storage Server 01', level: 'medium', time: '2024-01-15 12:15' }
])

const suggestions = reactive([
  { type: 'warning', title: '建议扩容Web集群', desc: '当前CPU使用率持续超过80%，建议增加Web服务器节点' },
  { type: 'info', title: '数据库索引优化', desc: '检测到慢查询，建议优化索引以提升查询性能' },
  { type: 'info', title: '备份策略调整', desc: '当前备份频率较低，建议增加增量备份频率' }
])

onMounted(() => {
  initCharts()
})

onUnmounted(() => {
  healthChart?.dispose()
  forecastChart?.dispose()
})

const initCharts = () => {
  if (healthChartRef.value) {
    healthChart = echarts.init(healthChartRef.value)
    healthChart.setOption({
      series: [{
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        splitNumber: 10,
        radius: '100%',
        axisLine: { lineStyle: { width: 20, color: [[0.6, '#00b42a'], [0.8, '#ff7d00'], [1, '#f53f3f']] } },
        pointer: { itemStyle: { color: '#165dff' }, width: 4 },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: { show: false },
        data: [{ value: 85 }]
      }]
    })
  }

  if (forecastChartRef.value) {
    forecastChart = echarts.init(forecastChartRef.value)
    forecastChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
      yAxis: { type: 'value' },
      series: [
        { name: '实际', type: 'bar', data: [65, 72, 68, 75, 80, 78, 82], itemStyle: { color: '#165dff' } },
        { name: '预测', type: 'line', data: [82, 85, 88, 90, 92, 94, 95], smooth: true, lineStyle: { color: '#ff7d00', type: 'dashed' } }
      ]
    })
  }

  window.addEventListener('resize', handleResize)
}

const handleResize = () => {
  healthChart?.resize()
  forecastChart?.resize()
}
</script>

<style lang="scss" scoped>
.analyze-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-container { width: 100%; height: 250px; }
.health-score { text-align: center; margin-top: 20px; .score-label { font-size: 14px; color: #86909c; } .score-value { font-size: 48px; font-weight: 600; color: #00b42a; margin: 0 8px; } .score-unit { font-size: 14px; color: #86909c; } }
.suggestion-list { display: flex; flex-direction: column; gap: 16px; }
.suggestion-item { display: flex; gap: 12px; align-items: flex-start; }
.suggestion-content { .suggestion-title { font-size: 14px; font-weight: 500; color: #1d2129; } .suggestion-desc { font-size: 13px; color: #86909c; margin-top: 4px; } }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
