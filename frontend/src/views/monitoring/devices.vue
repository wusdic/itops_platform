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
        @row-click="handleRowClick"
      />
    </n-card>

    <!-- 设备详情抽屉 -->
    <n-drawer v-model:show="drawerVisible" :width="500" placement="right">
      <n-drawer-content :title="selectedDevice?.name || '设备详情'" closable>
        <template #header>
          <div class="drawer-header">
            <span>{{ selectedDevice?.name || '设备详情' }}</span>
            <n-button size="small" @click="drawerVisible = false">关闭</n-button>
          </div>
        </template>

        <n-spin :show="metricsLoading">
          <!-- 设备基本信息 -->
          <div class="device-info">
            <h4>基本信息</h4>
            <div class="info-grid">
              <div class="info-item"><span class="label">IP地址:</span> {{ selectedDevice?.ip_address || '-' }}</div>
              <div class="info-item"><span class="label">操作系统:</span> {{ selectedDevice?.os_type || '-' }} {{ selectedDevice?.os_version || '' }}</div>
              <div class="info-item"><span class="label">设备类型:</span> {{ selectedDevice?.device_type || '-' }}</div>
              <div class="info-item"><span class="label">位置:</span> {{ selectedDevice?.location || '-' }}</div>
              <div class="info-item">
                <span class="label">状态:</span>
                <n-tag :type="statusType(selectedDevice?.status)" size="small">{{ statusText(selectedDevice?.status) }}</n-tag>
              </div>
            </div>
          </div>

          <!-- 性能图表 -->
          <div class="metrics-charts" v-if="metricsData">
            <h4>性能指标 (近48小时)</h4>

            <div class="chart-section">
              <div class="chart-label">CPU 使用率</div>
              <div class="chart-bar-container">
                <div class="chart-bar" :style="{ width: (metricsData.cpu || 0) + '%', backgroundColor: '#18a058' }"></div>
              </div>
              <div class="chart-value">{{ metricsData.cpu?.toFixed(1) || '0' }}%</div>
            </div>

            <div class="chart-section">
              <div class="chart-label">内存使用率</div>
              <div class="chart-bar-container">
                <div class="chart-bar" :style="{ width: (metricsData.memory || 0) + '%', backgroundColor: '#2080f0' }"></div>
              </div>
              <div class="chart-value">{{ metricsData.memory?.toFixed(1) || '0' }}%</div>
            </div>

            <div class="chart-section">
              <div class="chart-label">磁盘使用率</div>
              <div class="chart-bar-container">
                <div class="chart-bar" :style="{ width: (metricsData.disk || 0) + '%', backgroundColor: '#f0a020' }"></div>
              </div>
              <div class="chart-value">{{ metricsData.disk?.toFixed(1) || '0' }}%</div>
            </div>
          </div>

          <!-- 无数据提示 -->
          <div v-else-if="!metricsLoading && metricsError" class="no-data">
            <n-result status="error" title="加载失败" :description="metricsError">
              <template #footer>
                <n-button size="small" @click="loadMetrics">重试</n-button>
              </template>
            </n-result>
          </div>
          <div v-else-if="!metricsLoading" class="no-data">
            <n-empty description="暂无性能数据" />
          </div>
        </n-spin>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NGrid, NGi, NCard, NButton, NDataTable, NTag, NIcon, NSpace, NTooltip, useMessage, NDrawer, NDrawerContent, NSpin, NEmpty, NResult } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const deviceList = ref([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

// 抽屉相关
const drawerVisible = ref(false)
const selectedDevice = ref(null)
const metricsLoading = ref(false)
const metricsData = ref(null)
const metricsError = ref(null)

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
  { title: '最近采集', key: 'last_collect_time', width: 160, render: (r) => r.last_collect_time ? new Date(r.last_collect_time).toLocaleString('zh-CN') : '-' }
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

function handleRowClick(row) {
  selectedDevice.value = row
  drawerVisible.value = true
  loadMetrics(row)
}

async function loadMetrics(device) {
  if (!device?.id) return
  metricsLoading.value = true
  metricsError.value = null
  metricsData.value = null

  try {
    const token = localStorage.getItem('token')
    const now = new Date()
    const startTime = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString()
    const endTime = now.toISOString()

    // 并行请求 CPU、内存、磁盘指标
    const [cpuRes, memRes, diskRes] = await Promise.all([
      fetch('/api/v1/monitoring/metrics/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ device_id: device.id, metric_type: 'cpu', start_time: startTime, end_time: endTime })
      }),
      fetch('/api/v1/monitoring/metrics/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ device_id: device.id, metric_type: 'memory', start_time: startTime, end_time: endTime })
      }),
      fetch('/api/v1/monitoring/metrics/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ device_id: device.id, metric_type: 'disk', start_time: startTime, end_time: endTime })
      })
    ])

    if (!cpuRes.ok || !memRes.ok || !diskRes.ok) {
      throw new Error(`HTTP ${cpuRes.status || memRes.status || diskRes.status}`)
    }

    const [cpuData, memData, diskData] = await Promise.all([cpuRes.json(), memRes.json(), diskRes.json()])

    // 计算平均值
    const calcAvg = (data) => {
      if (!data?.data?.values || data.data.values.length === 0) return 0
      const sum = data.data.values.reduce((acc, v) => acc + (v.value ?? 0), 0)
      return sum / data.data.values.length
    }

    metricsData.value = {
      cpu: calcAvg(cpuData),
      memory: calcAvg(memData),
      disk: calcAvg(diskData)
    }
  } catch (e) {
    metricsError.value = e.message
    message.error(`加载性能指标失败: ${e.message}`)
    console.error('[devices] loadMetrics error:', e)
  } finally {
    metricsLoading.value = false
  }
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

/* 抽屉样式 */
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

/* 设备信息 */
.device-info {
  margin-bottom: 24px;
}
.device-info h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #1d2129;
}
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.info-item {
  font-size: 13px;
  color: #4b4b4b;
}
.info-item .label {
  color: #86909c;
}

/* 性能图表 */
.metrics-charts {
  margin-top: 16px;
}
.metrics-charts h4 {
  margin: 16px 0 12px 0;
  font-size: 14px;
  color: #1d2129;
}
.chart-section {
  margin-bottom: 20px;
}
.chart-label {
  font-size: 13px;
  color: #4b4b4b;
  margin-bottom: 6px;
}
.chart-bar-container {
  height: 20px;
  background-color: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}
.chart-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.chart-value {
  font-size: 13px;
  color: #1d2129;
  font-weight: 500;
  margin-top: 4px;
}

/* 无数据 */
.no-data {
  padding: 24px 0;
  text-align: center;
}
</style>
