<template>
  <div class="devices-container">
    <!-- 统计卡片 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" class="stats-grid">
      <n-gi v-for="stat in stats" :key="stat.key">
        <div class="stat-card" :style="{ borderLeftColor: stat.color }">
          <div class="stat-content">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </n-gi>
    </n-grid>

    <!-- 设备列表 -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">设备列表</span>
        <n-button type="primary" @click="handleRefresh">刷新</n-button>
      </div>
      <div class="card-body">
        <n-data-table
          :columns="columns"
          :data="devices"
          :bordered="false"
          :row-key="row => row.id"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, h } from 'vue'
import { NGrid, NGi, NButton, NDataTable, NTag, NProgress, NIcon, NSpace, NTooltip } from 'naive-ui'
import { RefreshOutline, InformationCircleOutline, SpeedometerOutline } from '@vicons/ionicons5'
import { devices } from '@/api'

const devicesData = ref([])
const stats = reactive([
  { key: 'total', label: '设备总数', value: 0, color: '#165dff' },
  { key: 'online', label: '在线', value: 0, color: '#00b42a' },
  { key: 'offline', label: '离线', value: 0, color: '#86909c' },
  { key: 'unknown', label: '未知', value: 0, color: '#ff7d00' }
])

const getProgressColor = (value) => {
  if (value >= 80) return '#f53f3f'
  if (value >= 60) return '#ff7d00'
  return '#00b42a'
}

const getProgressStatus = (value) => {
  if (value >= 80) return 'error'
  if (value >= 60) return 'warning'
  return 'success'
}

const columns = [
  { title: '名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '主机名', key: 'hostname', ellipsis: { tooltip: true } },
  { title: 'IP地址', key: 'ip', width: 140 },
  {
    title: '状态',
    key: 'status',
    width: 200,
    render(row) {
      return h(NSpace, { vertical: true, size: 4 }, () => [
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } }, [
          h('span', { style: { fontSize: '13px', color: '#666' } }, 'CPU'),
          h(NProgress, {
            type: 'line',
            percentage: row.cpu || 0,
            color: getProgressColor(row.cpu || 0),
            railColor: '#f0f0f0',
            showPercentage: false,
            height: 6,
            style: { width: '100px' }
          }),
          h('span', { style: { fontSize: '12px', color: '#999', minWidth: '35px' } }, `${row.cpu || 0}%`)
        ]),
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } }, [
          h('span', { style: { fontSize: '13px', color: '#666' } }, '内存'),
          h(NProgress, {
            type: 'line',
            percentage: row.memory || 0,
            color: getProgressColor(row.memory || 0),
            railColor: '#f0f0f0',
            showPercentage: false,
            height: 6,
            style: { width: '100px' }
          }),
          h('span', { style: { fontSize: '12px', color: '#999', minWidth: '35px' } }, `${row.memory || 0}%`)
        ]),
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } }, [
          h('span', { style: { fontSize: '13px', color: '#666' } }, '磁盘'),
          h(NProgress, {
            type: 'line',
            percentage: row.disk || 0,
            color: getProgressColor(row.disk || 0),
            railColor: '#f0f0f0',
            showPercentage: false,
            height: 6,
            style: { width: '100px' }
          }),
          h('span', { style: { fontSize: '12px', color: '#999', minWidth: '35px' } }, `${row.disk || 0}%`)
        ])
      ])
    }
  },
  {
    title: '采集时间',
    key: 'collected_at',
    width: 160,
    render(row) {
      if (!row.collected_at) return '-'
      return new Date(row.collected_at).toLocaleString('zh-CN')
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NTooltip, () => [
          h(NButton, {
            size: 'small',
            quaternary: true,
            onClick: () => handleCollect(row)
          }, () => h(NIcon, { component: RefreshOutline, size: 16 })),
          { trigger: h('span'), default: () => '采集' }
        ]),
        h(NTooltip, () => [
          h(NButton, {
            size: 'small',
            quaternary: true,
            onClick: () => handleDetail(row)
          }, () => h(NIcon, { component: InformationCircleOutline, size: 16 })),
          { trigger: h('span'), default: () => '详情' }
        ]),
        h(NTooltip, () => [
          h(NButton, {
            size: 'small',
            quaternary: true,
            onClick: () => handleMetrics(row)
          }, () => h(NIcon, { component: SpeedometerOutline, size: 16 })),
          { trigger: h('span'), default: () => '指标' }
        ])
      ])
    }
  }
]

const loadDevices = async () => {
  try {
    const [listRes, statsRes] = await Promise.allSettled([
      devices.getList({ page: 1, page_size: 100 }),
      devices.getStats()
    ])

    if (listRes.status === 'fulfilled') {
      devicesData.value = listRes.value.items || listRes.value || []
    }

    if (statsRes.status === 'fulfilled') {
      stats[0].value = statsRes.value.total || 0
      stats[1].value = statsRes.value.online || 0
      stats[2].value = statsRes.value.offline || 0
      stats[3].value = statsRes.value.unknown || 0
    }
  } catch (error) {
    console.error('Load devices error:', error)
  }
}

const handleRefresh = () => {
  loadDevices()
}

const handleCollect = async (row) => {
  try {
    await devices.collectDevice(row.id)
    window.$message.success('采集任务已下发')
    setTimeout(loadDevices, 1000)
  } catch (error) {
    window.$message.error('采集失败')
  }
}

const handleDetail = (row) => {
  window.$router.push(`/monitoring/device/${row.id}`)
}

const handleMetrics = (row) => {
  window.$router.push(`/monitoring/device/${row.id}/metrics`)
}

let refreshTimer = null

onMounted(() => {
  loadDevices()
  refreshTimer = setInterval(loadDevices, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style lang="scss" scoped>
.devices-container {
  padding: 20px;
}

.stats-grid {
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border-left: 4px solid;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  .stat-content {
    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: #1d2129;
      line-height: 1;
    }

    .stat-label {
      font-size: 13px;
      color: #86909c;
      margin-top: 4px;
    }
  }
}

.card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  .card-header {
    padding: 16px 20px;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .card-title {
      font-size: 16px;
      font-weight: 500;
      color: #1d2129;
    }
  }

  .card-body {
    padding: 16px 20px;
  }
}
</style>
