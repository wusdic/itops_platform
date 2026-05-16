<template>
  <div class="devices-container">
    <!-- 统计卡片 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" class="stats-grid">
      <n-gi v-for="stat in stats" :key="stat.key">
        <n-card class="stat-card" :style="{ borderLeft: `3px solid ${stat.color}` }" content-style="padding: 16px;">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 设备列表 -->
    <n-card title="设备列表" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="loadDevices" :loading="loading">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新
        </n-button>
      </template>
      <n-data-table
        :columns="columns"
        :data="deviceList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, h } from 'vue'
import { NGrid, NGi, NCard, NButton, NDataTable, NTag, NIcon, NSpace, NTooltip, useMessage } from 'naive-ui'
import { RefreshOutline, InformationCircleOutline, SpeedometerOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const deviceList = ref([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const stats = reactive([
  { key: 'total', label: '设备总数', value: 0, color: '#18a058' },
  { key: 'online', label: '在线', value: 0, color: '#00b42a' },
  { key: 'offline', label: '离线', value: 0, color: '#86909c' },
  { key: 'unknown', label: '未知', value: 0, color: '#ff7d00' }
])

const statusType = (s) => ({ online: 'success', offline: 'warning', unknown: 'default' })[s] || 'default'
const statusText = (s) => ({ online: '在线', offline: '离线', unknown: '未知' })[s] || s

const columns = [
  { title: '名称', key: 'name', ellipsis: { tooltip: true } },
  { title: 'IP地址', key: 'ip_address', width: 140 },
  { title: '系统', key: 'os_type', width: 80, render: (r) => r.os_type || '-' },
  { title: '系统版本', key: 'os_version', width: 160, ellipsis: { tooltip: true } },
  { title: '厂商/型号', key: 'manufacturer', width: 120, render: (r) => r.manufacturer ? `${r.manufacturer} ${r.model || ''}` : '-' },
  { title: '状态', key: 'status', width: 90, render: (r) => h(NTag, { type: statusType(r.status), size: 'small' }, () => statusText(r.status)) },
  { title: '位置', key: 'location', width: 130, ellipsis: { tooltip: true } },
  { title: '最近采集', key: 'last_collect_time', width: 160, render: (r) => r.last_collect_time ? new Date(r.last_collect_time).toLocaleString('zh-CN') : '-' },
  {
    title: '操作', key: 'actions', width: 120, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NTooltip, null, { trigger: () => h(NButton, { size: 'small', quaternary: true, onClick: () => handleMetrics(row) }, () => h(NIcon, null, { default: () => '指标' })), default: () => '查看指标' }),
        h(NTooltip, null, { trigger: () => h(NButton, { size: 'small', quaternary: true, onClick: () => handleDetail(row) }, () => h(NIcon, null, { default: () => '详情' })), default: () => '设备详情' })
      ])
    }
  }
]

async function loadDevices() {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/v1/assets/device?page=${pagination.page}&page_size=${pagination.pageSize}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')

    deviceList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0

    // 统计：从当前页推算（实际应从 stats API 获取）
    stats[0].value = data.total || 0
    const onlineCount = (data.items || []).filter(d => d.status === 'online').length
    const offlineCount = (data.items || []).filter(d => d.status === 'offline').length
    // 保持总数准确，在线/离线按比例估算
    stats[1].value = Math.round(stats[0].value * (onlineCount / Math.max(data.items?.length || 1, 1)))
    stats[2].value = stats[0].value - stats[1].value
  } catch (e) {
    message.error(`加载设备列表失败: ${e.message}`)
    deviceList.value = []
    console.error('[devices] loadDevices error:', e)
  } finally {
    loading.value = false
  }
}

function handleDetail(row) {
  message.info(`设备详情: ${row.name} (${row.ip_address})`)
}

function handleMetrics(row) {
  window.location.hash = `#/monitoring/performance?device=${encodeURIComponent(row.name)}`
  message.info(`跳转性能监控: ${row.name}`)
}

function handlePageChange(page) {
  pagination.page = page
  loadDevices()
}
function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadDevices()
}

onMounted(loadDevices)
</script>

<style scoped>
.devices-container { padding: 16px; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #1d2129; }
.stat-label { font-size: 13px; color: #86909c; margin-top: 4px; }
</style>
