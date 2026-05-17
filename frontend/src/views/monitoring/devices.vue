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

    <!-- 设备详情弹窗 -->
    <n-modal v-model:show="drawerVisible" preset="card" :title="selectedDevice?.name || '设备详情'" :style="{ width: '600px' }" :mask-closable="true">
      <template #header-extra>
        <n-button size="small" @click="drawerVisible = false">关闭</n-button>
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

        <!-- 协议配置Tab -->
        <n-tabs type="line" animated size="small" v-model:value="activeProtocolTab">
          <n-tab-pane name="config" tab="协议配置">
            <div class="protocol-config-form">
              <n-form label-placement="left" label-width="100" size="small">
                <n-form-item label="选择协议">
                  <n-select
                    v-model:value="protocolForm.protocol_type"
                    :options="protocolTypeOptions"
                    placeholder="选择协议类型"
                    style="width: 100%"
                    @update:value="onProtocolTypeChange"
                  />
                </n-form-item>
                <n-form-item label="适配器模板">
                  <n-select
                    v-model:value="protocolForm.adapter_template_id"
                    :options="filteredAdapterOptions"
                    placeholder="选择模板（可选）"
                    style="width: 100%"
                    clearable
                  />
                </n-form-item>
                <n-form-item label="主机地址">
                  <n-input v-model:value="protocolForm.host" placeholder="留空使用设备IP" />
                </n-form-item>
                <n-form-item label="端口">
                  <n-input-number v-model:value="protocolForm.port" :min="1" :max="65535" style="width: 100%" />
                </n-form-item>
                <n-form-item label="用户名">
                  <n-input v-model:value="protocolForm.username" placeholder="协议用户名" />
                </n-form-item>
                <n-form-item label="密码">
                  <n-input v-model:value="protocolForm.password" type="password" placeholder="协议密码" />
                </n-form-item>
                <n-form-item label="超时(秒)">
                  <n-input-number v-model:value="protocolForm.timeout" :min="5" :max="300" style="width: 100%" />
                </n-form-item>
                <n-form-item label="额外参数">
                  <n-input v-model:value="protocolForm.extra_json" type="textarea" placeholder='{"key": "value"}' :rows="2" />
                </n-form-item>
                <n-form-item label="启用">
                  <n-switch v-model:value="protocolForm.enabled" />
                </n-form-item>
                <n-form-item>
                  <n-space>
                    <n-button type="primary" size="small" @click="saveProtocolConfig" :loading="protocolSaving">保存配置</n-button>
                    <n-button size="small" @click="testProtocolConfig" :loading="protocolTesting">测试连接</n-button>
                  </n-space>
                </n-form-item>
              </n-form>

              <!-- 当前配置状态 -->
              <div v-if="deviceProtocols.length > 0" class="protocol-list">
                <h4>已配置协议</h4>
                <n-data-table
                  :columns="protocolListColumns"
                  :data="deviceProtocols"
                  size="small"
                  :row-key="row => row.protocol_type"
                />
              </div>
            </div>
          </n-tab-pane>
        </n-tabs>

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
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, h } from 'vue'
import { NGrid, NGi, NCard, NButton, NDataTable, NTag, NIcon, NSpace, NTooltip, useMessage, NModal, NSpin, NEmpty, NResult, NTabs, NTabPane, NForm, NFormItem, NInput, NInputNumber, NSwitch, NSelect } from 'naive-ui'
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

// 协议配置相关
const activeProtocolTab = ref('config')
const protocolSaving = ref(false)
const protocolTesting = ref(false)
const deviceProtocols = ref([])
const allAdapters = ref([])

const protocolForm = reactive({
  protocol_type: '',
  adapter_template_id: null,
  host: '',
  port: 22,
  username: '',
  password: '',
  timeout: 30,
  extra_json: '',
  enabled: true,
})

const protocolTypeOptions = [
  { label: 'SNMP', value: 'snmp' },
  { label: 'SSH', value: 'ssh' },
  { label: 'HTTP', value: 'http' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgres' },
  { label: 'Redis', value: 'redis' },
  { label: 'RabbitMQ', value: 'rabbitmq' },
  { label: 'Kafka', value: 'kafka' },
  { label: 'Elasticsearch', value: 'elasticsearch' },
  { label: 'VMware', value: 'vmware' },
  { label: 'IPMI', value: 'ipmi' },
  { label: 'WinRM', value: 'winrm' },
  { label: 'Kubernetes', value: 'kubernetes' },
  { label: 'Docker', value: 'docker' },
  { label: 'Zabbix', value: 'zabbix' },
  { label: 'Prometheus', value: 'prometheus' },
  { label: 'Browser', value: 'browser' },
  { label: 'Redfish', value: 'redfish' },
  { label: 'Syslog', value: 'syslog' },
  { label: 'Telnet', value: 'telnet' },
]

const filteredAdapterOptions = computed(() => {
  if (!protocolForm.protocol_type) return []
  return allAdapters.value
    .filter(a => a.protocol_type === protocolForm.protocol_type && a.enabled)
    .map(a => ({ label: a.name, value: a.id }))
})

const protocolListColumns = [
  {
    title: '协议',
    key: 'protocol_type',
    width: 100,
    render(row) {
      const colors = { snmp: 'info', ssh: 'success', http: 'warning', mysql: 'error', redis: 'info', postgres: 'success', vmware: 'warning' }
      return h(NTag, { type: colors[row.protocol_type] || 'default', size: 'small' }, () => row.protocol_type.toUpperCase())
    }
  },
  {
    title: '模板',
    key: 'adapter_template_id',
    render(row) {
      const t = allAdapters.value.find(a => a.id === row.adapter_template_id)
      return t ? t.name : '-'
    }
  },
  {
    title: '状态',
    key: 'enabled',
    width: 80,
    render(row) {
      return h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' }, () => row.enabled ? '启用' : '禁用')
    }
  },
]

async function loadAllAdapters() {
  try {
    const token = localStorage.getItem('token')
    const res = await fetch('/api/v1/admin/adapters', { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) return
    const data = await res.json()
    allAdapters.value = data.items || []
  } catch (e) { console.error('load adapters error:', e) }
}

async function loadDeviceProtocols(deviceId) {
  try {
    const token = localStorage.getItem('token')
    const res = await fetch('/api/v1/admin/adapters/device/' + deviceId + '/protocols', { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) return
    const data = await res.json()
    deviceProtocols.value = data.items || []
  } catch (e) { console.error('load device protocols error:', e) }
}

function onProtocolTypeChange(type) {
  protocolForm.adapter_template_id = null
  protocolForm.port = getDefaultPort(type)
  const adapter = allAdapters.value.find(a => a.protocol_type === type && a.enabled)
  if (adapter && adapter.default_config) {
    const cfg = adapter.default_config
    if (cfg.port) protocolForm.port = cfg.port
    if (cfg.username) protocolForm.username = cfg.username || ''
    if (cfg.timeout) protocolForm.timeout = cfg.timeout
  }
}

function getDefaultPort(type) {
  const ports = { snmp: 161, ssh: 22, http: 80, mysql: 3306, postgres: 5432, redis: 6379, rabbitmq: 15672, kafka: 9092, elasticsearch: 9200, vmware: 443, ipmi: 623, winrm: 5985, kubernetes: 6443, docker: 2375, zabbix: 80, prometheus: 9090, browser: 80, redfish: 443, syslog: 514, telnet: 23 }
  return ports[type] || 22
}

async function saveProtocolConfig() {
  if (!selectedDevice.value?.id || !protocolForm.protocol_type) {
    message.warning('请选择协议类型')
    return
  }
  protocolSaving.value = true
  try {
    const token = localStorage.getItem('token')
    let extra = {}
    if (protocolForm.extra_json) {
      try { extra = JSON.parse(protocolForm.extra_json) } catch { message.warning('额外参数格式错误'); return }
    }
    const overrides = { ...extra }
    if (protocolForm.host) overrides.host = protocolForm.host
    if (protocolForm.port) overrides.port = protocolForm.port
    if (protocolForm.username) overrides.username = protocolForm.username
    if (protocolForm.password) overrides.password = protocolForm.password
    if (protocolForm.timeout) overrides.timeout = protocolForm.timeout
    const res = await fetch('/api/v1/admin/adapters/device/' + selectedDevice.value.id + '/protocols', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify([{
        device_id: selectedDevice.value.id,
        protocol_type: protocolForm.protocol_type,
        adapter_template_id: protocolForm.adapter_template_id || null,
        overrides,
        enabled: protocolForm.enabled,
      }])
    })
    if (!res.ok) throw new Error('保存失败')
    message.success('保存成功')
    loadDeviceProtocols(selectedDevice.value.id)
  } catch (e) {
    message.error(e.message)
  } finally {
    protocolSaving.value = false
  }
}

async function testProtocolConfig() {
  if (!selectedDevice.value?.id || !protocolForm.protocol_type) {
    message.warning('请选择协议类型')
    return
  }
  protocolTesting.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch('/api/v1/admin/adapters/device/' + selectedDevice.value.id + '/protocols/' + protocolForm.protocol_type + '/test', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    const data = await res.json()
    if (data.success) {
      message.success('连接成功: ' + (data.message || ''))
    } else {
      message.warning('连接失败: ' + (data.message || data.error || ''))
    }
  } catch (e) {
    message.error('测试失败: ' + e.message)
  } finally {
    protocolTesting.value = false
  }
}

const stats = reactive([
  { key: 'total', label: '设备总数', value: 0, color: '#18a058' },
  { key: 'online', label: '在线', value: 0, color: '#00b42a' },
  { key: 'offline', label: '离线', value: 0, color: '#86909c' },
  { key: 'unknown', label: '未知', value: 0, color: '#ff7d00' }
])

// 轮询定时器
let pollTimer = null

const statusType = (s) => ({ online: 'success', offline: 'warning', unknown: 'default' })[s] || 'default'
const statusText = (s) => ({ online: '在线', offline: '离线', unknown: '未知' })[s] || s

const columns = [
  { title: '名称', key: 'name', ellipsis: { tooltip: true }, render(row) { return h('a', { style: 'color: #18a058; cursor: pointer', onClick: (e) => { e.preventDefault(); e.stopPropagation(); handleRowClick(row) } }, row.name) } },
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
    
    // 尝试从 /api/v1/devices/stats 获取真实统计，失败时从列表计算
    try {
      const statsRes = await fetch('/api/v1/devices/stats', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (statsRes.ok) {
        const statsData = await statsRes.json()
        stats[0].value = statsData.total || 0
        stats[1].value = statsData.online || 0
        stats[2].value = statsData.offline || 0
        stats[3].value = statsData.unknown || 0
      } else {
        // 备用：从列表计算
        const listRes = await fetch('/api/v1/assets/device?page=1&page_size=1000', {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (listRes.ok) {
          const listData = await listRes.json()
          const devices = listData.items || listData.data?.items || []
          stats[0].value = devices.length
          stats[1].value = devices.filter(d => d.status === 'online').length
          stats[2].value = devices.filter(d => d.status === 'offline').length
          stats[3].value = devices.filter(d => d.status !== 'online' && d.status !== 'offline').length
        }
      }
    } catch {
      // 忽略统计错误，继续加载列表
    }

    // 设备列表从分页接口获取
    const res = await fetch(`/api/v1/assets/device?page=${pagination.page}&page_size=${pagination.pageSize}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')

    deviceList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
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
  activeProtocolTab.value = 'config'
  // Reset form
  protocolForm.protocol_type = ''
  protocolForm.adapter_template_id = null
  protocolForm.host = ''
  protocolForm.port = 22
  protocolForm.username = ''
  protocolForm.password = ''
  protocolForm.timeout = 30
  protocolForm.extra_json = ''
  protocolForm.enabled = true
  loadMetrics(row)
  loadDeviceProtocols(row.id)
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

// 开始轮询
function startPoll() {
  stopPoll()
  pollTimer = setInterval(() => {
    loadDevices()
  }, 30000) // 每30秒刷新一次
}

// 停止轮询
function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  loadAllAdapters()
  loadDevices()
  startPoll()
})

onUnmounted(() => {
  stopPoll()
})
</script>

<style scoped>
.devices-container { padding: 16px; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #1d2129; }
.stat-label { font-size: 13px; color: #86909c; margin-top: 4px; }

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

/* 协议配置 */
.protocol-config-form {
  padding: 8px 0;
}
.protocol-config-form h4 {
  margin: 16px 0 12px 0;
  font-size: 14px;
  color: #1d2129;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 8px;
}
.protocol-list {
  margin-top: 20px;
}
</style>
