<template>
  <div>
    <div class="page-header">
      <h2>设备监控</h2>
      <n-space>
        <n-button type="primary" @click="handleCollectAll">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          批量采集
        </n-button>
      </n-space>
    </div>

    <!-- 统计卡片 -->
    <n-grid cols="4 m:2 s:1" responsive="screen" :x-gap="16" :y-gap="16" style="margin-bottom:16px">
      <n-gi v-for="item in statsCards" :key="item.label">
        <div class="stat-card" :style="{ borderLeft: `4px solid ${item.color}` }">
          <div>
            <div class="stat-value">{{ item.value }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
          <n-icon size="32" :color="item.color"><component :is="item.icon" /></n-icon>
        </div>
      </n-gi>
    </n-grid>

    <!-- 设备列表 -->
    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
        remote
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, h, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  RefreshOutline, DesktopOutline, CheckmarkDoneOutline, CloseCircleOutline,
  HelpCircleOutline, StatsChartOutline, BarChartOutline, DiscOutline,
  PlayOutline, SpeedometerOutline
} from '@vicons/ionicons5'
import { getDeviceList, getDeviceStats, collectDevice, collectAll } from '@/api/device'
import dayjs from 'dayjs'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const collecting = ref({})

const statsCards = ref([
  { label: '设备总数', value: 0, icon: DesktopOutline, color: '#2080f0' },
  { label: '在线', value: 0, icon: CheckmarkDoneOutline, color: '#18a058' },
  { label: '离线', value: 0, icon: CloseCircleOutline, color: '#d03050' },
  { label: '未知', value: 0, icon: HelpCircleOutline, color: '#909090' }
])

const tableData = ref([])
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const statusTypeMap = { online: 'success', offline: 'error', maintenance: 'warning', unknown: 'default' }
const statusLabelMap = { online: '在线', offline: '离线', maintenance: '维护中', unknown: '未知' }

const columns = [
  { title: '名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '主机名', key: 'hostname', ellipsis: { tooltip: true } },
  { title: 'IP', key: 'ip', width: 140 },
  {
    title: '状态', key: 'status', width: 100,
    render: row => h('n-tag', { type: statusTypeMap[row.status] || 'default', size: 'small' }, { default: () => statusLabelMap[row.status] || row.status })
  },
  {
    title: 'CPU', key: 'cpu', width: 140,
    render: row => {
      const val = row.cpu_usage ?? row.cpu ?? 0
      const type = val > 80 ? 'error' : val > 60 ? 'warning' : 'success'
      return h('n-progress', { type: 'line', percentage: Math.min(val, 100), showIndicator: true, color: type === 'error' ? '#d03050' : type === 'warning' ? '#f0a020' : '#18a050', height: '8px', indicatorPlacement: 'inside', style: 'width:120px' })
    }
  },
  {
    title: '内存', key: 'memory', width: 140,
    render: row => {
      const val = row.memory_usage ?? row.memory ?? 0
      const type = val > 80 ? 'error' : val > 60 ? 'warning' : 'success'
      return h('n-progress', { type: 'line', percentage: Math.min(val, 100), showIndicator: true, color: type === 'error' ? '#d03050' : type === 'warning' ? '#f0a020' : '#18a050', height: '8px', indicatorPlacement: 'inside', style: 'width:120px' })
    }
  },
  {
    title: '磁盘', key: 'disk', width: 140,
    render: row => {
      const val = row.disk_usage ?? row.disk ?? 0
      const type = val > 80 ? 'error' : val > 60 ? 'warning' : 'success'
      return h('n-progress', { type: 'line', percentage: Math.min(val, 100), showIndicator: true, color: type === 'error' ? '#d03050' : type === 'warning' ? '#f0a020' : '#18a050', height: '8px', indicatorPlacement: 'inside', style: 'width:120px' })
    }
  },
  {
    title: '采集时间', key: 'last_collect_time', width: 170,
    render: row => row.last_collect_time ? dayjs(row.last_collect_time).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 220, fixed: 'right',
    render: row => h('n-space', null, { default: () => [
      h('n-button', { size: 'small', quaternary: true, type: 'primary', loading: collecting.value[row.id], onClick: () => handleCollect(row) }, { icon: () => h('n-icon', null, { default: () => h(PlayOutline) }), default: () => '采集' }),
      h('n-button', { size: 'small', quaternary: true, type: 'info', onClick: () => router.push(`/devices/${row.hostname || row.name}`) }, { icon: () => h('n-icon', null, { default: () => h(SpeedometerOutline) }), default: () => '详情' }),
      h('n-button', { size: 'small', quaternary: true, onClick: () => router.push('/devices/metrics') }, { icon: () => h('n-icon', null, { default: () => h(StatsChartOutline) }), default: () => '指标' })
    ]})
  }
]

async function loadStats() {
  try {
    const res = await getDeviceStats()
    const d = res.data || res || {}
    statsCards.value[0].value = d.total || 0
    statsCards.value[1].value = d.online || 0
    statsCards.value[2].value = d.offline || 0
    statsCards.value[3].value = d.unknown || 0
  } catch (e) {
    console.error(e)
  }
}

async function loadData(page) {
  if (page) pagination.page = page
  loading.value = true
  try {
    const res = await getDeviceList({ page: pagination.page, page_size: pagination.pageSize })
    tableData.value = res.items || res.data?.items || []
    pagination.itemCount = res.total || res.data?.total || 0
  } catch (e) {
    message.error('加载设备列表失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handlePageChange(p) { loadData(p) }
function handlePageSizeChange(ps) { pagination.pageSize = ps; pagination.page = 1; loadData() }

async function handleCollect(row) {
  collecting.value[row.id] = true
  try {
    await collectDevice({ device_id: row.id })
    message.success('采集成功')
    loadData()
  } catch (e) {
    message.error('采集失败')
    console.error(e)
  } finally {
    collecting.value[row.id] = false
  }
}

async function handleCollectAll() {
  try {
    await collectAll({})
    message.success('批量采集已发起')
    loadData()
  } catch (e) {
    message.error('批量采集失败')
    console.error(e)
  }
}

let refreshTimer = null
onMounted(() => {
  loadStats()
  loadData()
  refreshTimer = setInterval(() => { loadStats(); loadData() }, 30000)
})
onBeforeUnmount(() => { if (refreshTimer) clearInterval(refreshTimer) })
</script>

<style scoped>
.stat-card { display:flex; align-items:center; justify-content:space-between; padding:20px; background:#fff; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
.stat-value { font-size:28px; font-weight:700; color:#1a1a1a; }
.stat-label { font-size:13px; color:#999; margin-top:4px; }
</style>
