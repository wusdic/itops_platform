<template>
  <div>
    <!-- 统计卡片 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" responsive="screen">
      <n-grid-item v-for="s in stats" :key="s.label">
        <n-card :bordered="false" size="small" class="stat-card">
          <div class="stat-icon" :style="{ background: s.color }">
            <n-icon size="24" color="#fff"><component :is="s.icon" /></n-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 趋势图表 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" style="margin-top:16px">
      <n-grid-item>
        <n-card title="告警趋势（近7天）" :bordered="false" size="small" content-style="padding:0">
          <div ref="alertChartRef" style="height:260px;padding:8px"></div>
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card title="工单趋势（近7天）" :bordered="false" size="small" content-style="padding:0">
          <div ref="woChartRef" style="height:260px;padding:8px"></div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 最新告警 + 待处理工单 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" style="margin-top:16px">
      <n-grid-item>
        <n-card title="最新告警" :bordered="false" size="small" content-style="padding:0">
          <n-data-table
            size="small"
            :columns="alertColumns"
            :data="recentAlerts"
            :pagination="false"
            :max-height="220"
          />
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card title="待处理工单" :bordered="false" size="small" content-style="padding:0">
          <n-data-table
            size="small"
            :columns="woColumns"
            :data="pendingWo"
            :pagination="false"
            :max-height="220"
          />
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 快捷入口 + 系统状态 -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" style="margin-top:16px">
      <n-grid-item>
        <n-card title="快捷入口" :bordered="false" size="small">
          <div class="quick-grid">
            <n-button
              v-for="q in quickEntries"
              :key="q.path"
              @click="router.push(q.path)"
              class="quick-btn"
              block
            >
              <template #icon><n-icon size="18"><component :is="q.icon" /></n-icon></template>
              {{ q.label }}
            </n-button>
          </div>
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card title="系统健康" :bordered="false" size="small">
          <div class="health-list">
            <div v-for="h in healthItems" :key="h.label" class="health-item">
              <span class="health-label">{{ h.label }}</span>
              <n-tag :type="h.status === 'success' ? 'success' : 'warning'" size="small" :bordered="false">
                {{ h.status === 'success' ? '运行中' : '无数据' }}
              </n-tag>
            </div>
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { NTag } from 'naive-ui'
import {
  DesktopOutline, CheckmarkDoneOutline, AlertCircleOutline, TicketOutline,
  ServerOutline, FlashOutline, BookOutline, BarChartOutline
} from '@vicons/ionicons5'
import { getDeviceStats } from '@/api/device'
import { getAlerts } from '@/api/monitoring'
import { getWoStats, getWorkorders } from '@/api/workorder'

const router = useRouter()
const loading = ref(false)
const alertChartRef = ref(null)
const woChartRef = ref(null)
let alertChartInst = null
let woChartInst = null

const deviceStats = ref({ total: 0, online: 0 })

const stats = ref([
  { label: '设备总数', value: 0, icon: DesktopOutline, color: '#2080f0' },
  { label: '在线', value: 0, icon: CheckmarkDoneOutline, color: '#18a058' },
  { label: '活跃告警', value: 0, icon: AlertCircleOutline, color: '#d03050' },
  { label: '待处理工单', value: 0, icon: TicketOutline, color: '#f0a020' }
])

const recentAlerts = ref([])
const pendingWo = ref([])

const healthItems = computed(() => [
  { label: 'API 服务', status: 'success' },
  { label: '数据库', status: 'success' },
  { label: '设备采集', status: deviceStats.value.online > 0 ? 'success' : 'warning' },
  { label: '告警引擎', status: 'success' }
])

function levelTag(level) {
  const m = { critical: { type:'error', text:'严重' }, high:{type:'error',text:'高'}, medium:{type:'warning',text:'中'}, low:{type:'info',text:'低'}, info:{type:'default',text:'信息'} }
  return m[level] || { type:'default', text: level }
}

const alertColumns = [
  { title: '级别', key: 'level', width: 64, render: r => { const c = levelTag(r.level); return c } },
  { title: '设备', key: 'device_name', ellipsis: { tooltip: true } },
  { title: '摘要', key: 'title', ellipsis: { tooltip: true } },
  { title: '时间', key: 'occurred_at', width: 130 },
]

const woColumns = [
  { title: '编号', key: 'order_no', width: 108 },
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  { title: '优先级', key: 'priority', width: 60, render: r => {
    const m = { P1:{type:'error'}, P2:{type:'warning'}, P3:{type:'info'}, P4:{type:'default'} }
    return m[r.priority] || { type:'default' }
  }},
  { title: '状态', key: 'status', width: 70 },
]

const quickEntries = [
  { label: '设备管理', path: '/assets', icon: DesktopOutline },
  { label: '告警管理', path: '/monitoring/alerts', icon: AlertCircleOutline },
  { label: '工单列表', path: '/workorders', icon: TicketOutline },
  { label: '设备扫描', path: '/discovery/scan', icon: FlashOutline },
  { label: '知识库', path: '/knowledge/docs', icon: BookOutline },
  { label: '报表中心', path: '/reports/list', icon: BarChartOutline },
]

async function loadData() {
  loading.value = true
  try {
    const [devRes, alertRes, woRes, woListRes] = await Promise.allSettled([
      getDeviceStats(),
      getAlerts({ page: 1, page_size: 5, status: 'active' }),
      getWoStats(),
      getWorkorders({ page: 1, page_size: 5, status: 'pending' })
    ])

    if (devRes.status === 'fulfilled') {
      const d = devRes.value.data || {}
      deviceStats.value = { total: d.total || 0, online: d.online || 0 }
      stats.value[0].value = d.total || 0
      stats.value[1].value = d.online || 0
    }
    if (alertRes.status === 'fulfilled') {
      const items = alertRes.value.data?.items || []
      stats.value[2].value = Array.isArray(items) ? items.length : 0
      recentAlerts.value = Array.isArray(items) ? items : []
    }
    if (woRes.status === 'fulfilled') {
      const w = woRes.value.data || {}
      stats.value[3].value = w.pending || 0
    }
    if (woListRes.status === 'fulfilled') {
      const items = woListRes.value.data?.items || []
      pendingWo.value = Array.isArray(items) ? items : []
    }
  } catch (e) {
    console.error('Dashboard error:', e)
  } finally {
    loading.value = false
  }

  nextTick(() => {
    if (alertChartRef.value) {
      if (alertChartInst) alertChartInst.dispose()
      alertChartInst = echarts.init(alertChartRef.value)
      alertChartInst.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 40, right: 16, top: 8, bottom: 24 },
        xAxis: { type: 'category', data: ['周一','周二','周三','周四','周五','周六','周日'], axisLabel: { fontSize: 11 } },
        yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
        series: [{
          name: '告警数', type: 'line', smooth: true, symbol: 'circle', symbolSize: 6,
          data: [12, 8, 15, 6, 20, 5, 10],
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(208,48,80,0.25)' }, { offset: 1, color: 'rgba(208,48,80,0.02)' }] } },
          lineStyle: { width: 2 }, itemStyle: { color: '#d03050' }
        }]
      })
    }
    if (woChartRef.value) {
      if (woChartInst) woChartInst.dispose()
      woChartInst = echarts.init(woChartRef.value)
      woChartInst.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 40, right: 16, top: 8, bottom: 24 },
        xAxis: { type: 'category', data: ['周一','周二','周三','周四','周五','周六','周日'], axisLabel: { fontSize: 11 } },
        yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
        series: [{
          name: '工单数', type: 'bar', barWidth: 22,
          data: [5, 8, 3, 12, 7, 2, 6],
          itemStyle: { color: '#2080f0', borderRadius: [4, 4, 0, 0] }
        }]
      })
    }
  })
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.stat-card { display: flex; align-items: center; gap: 14px; }
.stat-icon { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.stat-value { font-size: 24px; font-weight: 700; color: #1a1a1a; line-height: 1.2; }
.stat-label { font-size: 13px; color: #8c8c8c; margin-top: 2px; }
.quick-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.quick-btn { height: 44px; font-size: 13px; }
.health-list { display: flex; flex-direction: column; gap: 8px; }
.health-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.health-item:last-child { border-bottom: none; }
.health-label { font-size: 13px; color: #555; }
</style>
