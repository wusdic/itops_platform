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
        <n-space :size="12" align="center">
          <n-input v-model:value="searchKeyword" placeholder="搜索名称/IP" clearable style="width: 200px" @update:value="handleSearch">
            <template #prefix>
              <n-icon><Search /></n-icon>
            </template>
          </n-input>
          <n-button type="primary" @click="loadDevices" :loading="loading">
            <template #icon><n-icon><RefreshOutline /></n-icon></template>
            刷新
          </n-button>
        </n-space>
      </template>

      <n-data-table
        :columns="columns"
        :data="filteredDevices"
        :loading="loading"
        :pagination="{ pageSize: 20 }"
        :row-key="row => row.id"
        :row-class-name="getRowClassName"
        @row-click="handleRowClick"
      />
    </n-card>

    <!-- 设备详情弹窗 -->
    <n-modal v-model:show="drawerVisible" preset="card" :title="selectedDevice?.name || '设备详情'" :style="{ width: '880px' }" :mask-closable="true">
      <template #header-extra>
        <n-button size="small" @click="drawerVisible = false">关闭</n-button>
      </template>

      <n-spin :show="metricsLoading">
        <n-tabs type="line" animated v-model:value="activeDeviceTab" size="small">
          <!-- 基本信息Tab -->
          <n-tab-pane name="info" tab="基本信息">
            <div class="device-info">
              <div class="info-grid">
                <div class="info-item"><span class="label">IP地址:</span> {{ selectedDevice?.ip_address || '-' }}</div>
                <div class="info-item"><span class="label">操作系统:</span> {{ selectedDevice?.os_type || '-' }} {{ selectedDevice?.os_version || '' }}</div>
                <div class="info-item"><span class="label">设备类型:</span> {{ selectedDevice?.device_type || '-' }}</div>
                <div class="info-item"><span class="label">位置:</span> {{ selectedDevice?.location || '-' }}</div>
                <div class="info-item">
                  <span class="label">状态:</span>
                  <n-tag :type="statusType(selectedDevice?.status)" size="small">{{ statusText(selectedDevice?.status) }}</n-tag>
                </div>
                <div class="info-item"><span class="label">厂商:</span> {{ selectedDevice?.manufacturer || '-' }}</div>
                <div class="info-item"><span class="label">型号:</span> {{ selectedDevice?.model || '-' }}</div>
                <div class="info-item"><span class="label">序列号:</span> {{ selectedDevice?.serial_number || '-' }}</div>
                <div class="info-item"><span class="label">最近采集:</span> {{ selectedDevice?.last_collect_time ? new Date(selectedDevice.last_collect_time).toLocaleString('zh-CN') : '-' }}</div>
                <div class="info-item"><span class="label">创建时间:</span> {{ selectedDevice?.created_at ? new Date(selectedDevice.created_at).toLocaleString('zh-CN') : '-' }}</div>
              </div>
            </div>
          </n-tab-pane>

          <!-- 协议配置Tab -->
          <n-tab-pane name="config" tab="协议配置">
            <div class="protocol-config-form">
              <n-form label-placement="left" label-width="100" size="small">
                <n-form-item label="选择协议">
                  <n-tree-select
                    v-model:value="protocolForm.protocol_type"
                    :options="protocolTypeGroups"
                    placeholder="选择协议类型"
                    style="width: 100%"
                    clearable
                    filterable
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
                  <n-input v-model:value="protocolForm.password" type="password" placeholder="协议密码" show-password-on="click" />
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

              <!-- 已配置协议 - 折叠 -->
              <n-collapse v-if="deviceProtocols.length > 0" class="protocol-collapse">
                <n-collapse-item title="已配置协议" name="protocols">
                  <n-data-table
                    :columns="protocolListColumns"
                    :data="deviceProtocols"
                    size="small"
                    :row-key="row => row.protocol_type"
                  />
                </n-collapse-item>
              </n-collapse>
            </div>
          </n-tab-pane>

          <!-- 性能Tab -->
          <n-tab-pane name="metrics" tab="性能指标">
            <div v-if="metricsData" class="metrics-charts">
              <div class="metrics-grid">
                <div class="metric-card">
                  <div class="metric-header">
                    <span class="metric-label">CPU 使用率</span>
                    <span class="metric-value">{{ metricsData.cpu?.toFixed(1) || '0' }}%</span>
                  </div>
                  <div ref="cpuChartRef" class="metric-chart"></div>
                </div>
                <div class="metric-card">
                  <div class="metric-header">
                    <span class="metric-label">内存使用率</span>
                    <span class="metric-value">{{ metricsData.memory?.toFixed(1) || '0' }}%</span>
                  </div>
                  <div ref="memoryChartRef" class="metric-chart"></div>
                </div>
                <div class="metric-card">
                  <div class="metric-header">
                    <span class="metric-label">磁盘使用率</span>
                    <span class="metric-value">{{ metricsData.disk?.toFixed(1) || '0' }}%</span>
                  </div>
                  <div ref="diskChartRef" class="metric-chart"></div>
                </div>
              </div>
            </div>
            <div v-else-if="!metricsLoading && metricsError" class="no-data">
              <n-result status="error" title="加载失败" :description="metricsError">
                <template #footer>
                  <n-button size="small" @click="loadMetrics(selectedDevice)">重试</n-button>
                </template>
              </n-result>
            </div>
            <div v-else-if="!metricsLoading" class="no-data">
              <n-empty description="暂无性能数据" />
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, h, nextTick } from 'vue'
import { NGrid, NGi, NCard, NButton, NDataTable, NTag, NIcon, NSpace, NTooltip, useMessage, useDialog, NModal, NSpin, NEmpty, NResult, NTabs, NTabPane, NForm, NFormItem, NInput, NInputNumber, NSwitch, NSelect, NTreeSelect, NCollapse, NCollapseItem } from 'naive-ui'
import * as echarts from 'echarts'
import { devices } from '@/api'
import { RefreshOutline, Search } from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const deviceList = ref([])
const searchKeyword = ref('')
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

// 抽屉相关
const drawerVisible = ref(false)
const selectedDevice = ref(null)
const metricsLoading = ref(false)
const metricsData = ref(null)
const metricsError = ref(null)

// 图表 ref
const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
const diskChartRef = ref(null)
let cpuChart = null
let memoryChart = null
let diskChart = null

// 设备详情标签页
const activeDeviceTab = ref('info')
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

// 协议类型分组（带折叠功能）
const protocolTypeGroups = [
  {
    label: '远程访问',
    key: 'remote',
    children: [
      { label: 'SSH', value: 'ssh' },
      { label: 'Telnet', value: 'telnet' },
      { label: 'WinRM', value: 'winrm' },
    ]
  },
  {
    label: '数据库',
    key: 'database',
    children: [
      { label: 'MySQL', value: 'mysql' },
      { label: 'PostgreSQL', value: 'postgres' },
      { label: 'Redis', value: 'redis' },
    ]
  },
  {
    label: '消息队列',
    key: 'mq',
    children: [
      { label: 'RabbitMQ', value: 'rabbitmq' },
      { label: 'Kafka', value: 'kafka' },
    ]
  },
  {
    label: '监控采集',
    key: 'monitoring',
    children: [
      { label: 'SNMP', value: 'snmp' },
      { label: 'IPMI', value: 'ipmi' },
      { label: 'Zabbix', value: 'zabbix' },
      { label: 'Prometheus', value: 'prometheus' },
    ]
  },
  {
    label: '虚拟化/容器',
    key: 'vm',
    children: [
      { label: 'VMware', value: 'vmware' },
      { label: 'Kubernetes', value: 'kubernetes' },
      { label: 'Docker', value: 'docker' },
    ]
  },
  {
    label: 'Web/应用',
    key: 'web',
    children: [
      { label: 'HTTP', value: 'http' },
      { label: 'Browser', value: 'browser' },
      { label: 'Elasticsearch', value: 'elasticsearch' },
    ]
  },
  {
    label: '其他',
    key: 'other',
    children: [
      { label: 'Redfish', value: 'redfish' },
      { label: 'Syslog', value: 'syslog' },
    ]
  },
]

// 扁平化选项（用于兼容现有逻辑）
const protocolTypeOptions = protocolTypeGroups.flatMap(g => g.children)

const filteredAdapterOptions = computed(() => {
  if (!protocolForm.protocol_type) return []
  return allAdapters.value
    .filter(a => a.protocol_type === protocolForm.protocol_type && a.enabled)
    .map(a => ({ label: a.name, value: a.id }))
})

// 本地搜索过滤
const filteredDevices = computed(() => {
  if (!searchKeyword.value) return deviceList.value
  const kw = searchKeyword.value.toLowerCase()
  return deviceList.value.filter(d =>
    (d.name || '').toLowerCase().includes(kw) ||
    (d.ip_address || '').toLowerCase().includes(kw)
  )
})

const handleSearch = () => {
  // 搜索在 computed 中实时过滤，无需额外操作
}

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
    const res = await fetch('/api/v1/admin/device/' + deviceId + '/protocols', { headers: { Authorization: `Bearer ${token}` } })
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
    const res = await fetch('/api/v1/admin/device/' + selectedDevice.value.id + '/protocols', {
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
    const res = await fetch('/api/v1/admin/device/' + selectedDevice.value.id + '/protocols/' + protocolForm.protocol_type + '/test', {
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

const getRowClassName = ({ row }) => {
  if (row.status === 'offline') return 'row-offline'
  if (row.status === 'online') return 'row-online'
  return ''
}

const columns = [
  { title: '名称', key: 'name', ellipsis: { tooltip: true }, render(row) { return h('a', { style: 'color: #18a058; cursor: pointer', onClick: (e) => { e.preventDefault(); e.stopPropagation(); handleRowClick(row) } }, row.name) } },
  { title: 'IP地址', key: 'ip_address', width: 140 },
  { title: '系统', key: 'os_type', width: 100, render: (r) => r.os_type || '-' },
  { title: '系统版本', key: 'os_version', width: 150, ellipsis: { tooltip: true } },
  { title: '厂商型号', key: 'manufacturer', width: 160, render: (r) => r.manufacturer ? `${r.manufacturer} ${r.model || ''}` : '-' },
  { title: '状态', key: 'status', width: 90, render: (r) => h(NTag, { type: statusType(r.status), size: 'small' }, () => statusText(r.status)) },
  { title: '位置', key: 'location', width: 150, ellipsis: { tooltip: true } },
  { title: '最近采集', key: 'last_collect_time', width: 170, render: (r) => r.last_collect_time ? new Date(r.last_collect_time).toLocaleString('zh-CN') : '-' },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', type: 'primary', ghost: true, onClick: () => handleRowClick(row) }, () => '详情'),
        h(NButton, { size: 'small', type: 'warning', onClick: () => handleCollect(row) }, () => '采集'),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, () => '删除')
      ])
    }
  }
]

async function loadDevices() {
  loading.value = true
  try {
    const token = localStorage.getItem('token')

    // 统计
    try {
      const statsRes = await fetch('/api/v1/devices/stats', { headers: { Authorization: `Bearer ${token}` } })
      if (statsRes.ok) {
        const statsData = await statsRes.json()
        stats[0].value = statsData.total || 0
        stats[1].value = statsData.online || 0
        stats[2].value = statsData.offline || 0
        stats[3].value = statsData.unknown || 0
      } else {
        const listRes = await fetch('/api/v1/assets/device?page=1&page_size=1000', { headers: { Authorization: `Bearer ${token}` } })
        if (listRes.ok) {
          const listData = await listRes.json()
          const devices = listData.items || listData.data?.items || []
          stats[0].value = devices.length
          stats[1].value = devices.filter(d => d.status === 'online').length
          stats[2].value = devices.filter(d => d.status === 'offline').length
          stats[3].value = devices.filter(d => d.status !== 'online' && d.status !== 'offline').length
        }
      }
    } catch { /* ignore */ }

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

function handleRowClick(row) {
  selectedDevice.value = row
  drawerVisible.value = true
  activeDeviceTab.value = 'info'
  resetProtocolForm()
  loadMetrics(row)
  loadDeviceProtocols(row.id)
}

function resetProtocolForm() {
  protocolForm.protocol_type = ''
  protocolForm.adapter_template_id = null
  protocolForm.host = ''
  protocolForm.port = 22
  protocolForm.username = ''
  protocolForm.password = ''
  protocolForm.timeout = 30
  protocolForm.extra_json = ''
  protocolForm.enabled = true
}

function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除设备 "${row.name}" 吗？此操作不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await devices.delete(row.id)
        message.success('删除成功')
        loadDevices()
      } catch (e) {
        message.error('删除失败: ' + (e.message || e))
      }
    }
  })
}

function handleCollect(row) {
  dialog.warning({
    title: '确认采集',
    content: `确定要采集设备 "${row.name}" 的指标数据吗？`,
    positiveText: '确认采集',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await devices.collect({ device_id: row.id })
        message.success('采集任务已触发')
      } catch (e) {
        message.error('采集失败: ' + (e.message || e))
      }
    }
  })
}

async function loadMetrics(device) {
  if (!device?.id) return
  metricsLoading.value = true
  metricsError.value = null
  metricsData.value = null

  // 销毁旧图表
  cpuChart?.dispose()
  memoryChart?.dispose()
  diskChart?.dispose()
  cpuChart = null
  memoryChart = null
  diskChart = null

  try {
    const token = localStorage.getItem('token')
    const now = new Date()
    const startTime = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString()
    const endTime = now.toISOString()

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

    // 等 DOM 更新后初始化图表
    await nextTick()
    initCharts(cpuData, memData, diskData)
  } catch (e) {
    metricsError.value = e.message
    message.error(`加载性能指标失败: ${e.message}`)
    console.error('[devices] loadMetrics error:', e)
  } finally {
    metricsLoading.value = false
  }
}

function initCharts(cpuData, memData, diskData) {
  const chartData = [
    { ref: cpuChartRef, data: cpuData, color: '#18a058', label: 'CPU' },
    { ref: memoryChartRef, data: memData, color: '#2080f0', label: '内存' },
    { ref: diskChartRef, data: diskData, color: '#f0a020', label: '磁盘' },
  ]

  chartData.forEach(({ ref, data, color, label }) => {
    if (!ref.value) return
    const values = data.data?.values || []
    const currentValue = values.length > 0 ? values[values.length - 1].value ?? 0 : 0

    const chart = echarts.init(ref.value)
    const option = {
      series: [
        // 仪表盘
        {
          type: 'gauge',
          startAngle: 200,
          endAngle: -20,
          radius: '90%',
          center: ['50%', '60%'],
          min: 0,
          max: 100,
          splitNumber: 4,
          itemStyle: { color },
          progress: { show: true, width: 8, itemStyle: { color } },
          pointer: { show: false },
          axisLine: { lineStyle: { width: 8, color: [[1, '#e8e8e8']] } },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          anchor: { show: false },
          title: { show: false },
          detail: {
            valueAnimation: true,
            fontSize: 14,
            fontWeight: 'bold',
            offsetCenter: [0, '10%'],
            formatter: '{value}%',
            color: '#303133',
          },
          data: [{ value: currentValue }],
        },
        // 迷你趋势线
        {
          type: 'line',
          smooth: true,
          symbol: 'none',
          areaStyle: { opacity: 0.3, color },
          lineStyle: { color, width: 1.5 },
          data: values.map(v => v.value ?? 0),
          xAxis: { show: false },
          yAxis: { show: false },
          grid: { left: 0, right: 0, top: 0, bottom: 0 },
        },
      ],
    }
    chart.setOption(option)
  })

  // 保存图表实例
  cpuChart = cpuChartRef.value ? echarts.getInstanceByDom(cpuChartRef.value) : null
  memoryChart = memoryChartRef.value ? echarts.getInstanceByDom(memoryChartRef.value) : null
  diskChart = diskChartRef.value ? echarts.getInstanceByDom(diskChartRef.value) : null
}

// 监听 tab 切换，切换到 metrics 时 resize 图表
let resizeObserver = null

function handlePageChange(page) {
  pagination.page = page
  loadDevices()
}
function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadDevices()
}

function startPoll() {
  stopPoll()
  pollTimer = setInterval(() => { loadDevices() }, 30000)
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  resizeObserver?.disconnect()
}

onMounted(() => {
  loadAllAdapters()
  loadDevices()
  startPoll()

  // 监听窗口 resize
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  stopPoll()
  cpuChart?.dispose()
  memoryChart?.dispose()
  diskChart?.dispose()
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  cpuChart?.resize()
  memoryChart?.resize()
  diskChart?.resize()
}
</script>

<style scoped>
.devices-container { padding: 16px; }
.stat-card { text-align: center; cursor: default; transition: transform 0.2s, box-shadow 0.2s; }
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.stat-value { font-size: 28px; font-weight: 700; color: #1d2129; }
.stat-label { font-size: 13px; color: #86909c; margin-top: 4px; }

.device-info { margin-bottom: 24px; }
.device-info h4 { margin: 0 0 12px 0; font-size: 14px; color: #1d2129; }
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.info-item { font-size: 13px; color: #4b4b4b; }
.info-item .label { color: #86909c; }

.protocol-config-form { padding: 8px 0; }
.protocol-collapse { margin-top: 16px; }

.metrics-charts { padding: 8px 0; }
.metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.metric-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
}
.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.metric-label { font-size: 13px; color: #606266; }
.metric-value { font-size: 18px; font-weight: 700; color: #303133; }
.metric-chart { width: 100%; height: 60px; }

.no-data { padding: 24px 0; text-align: center; }

/* Row status */
:deep(.row-offline) { background-color: #fff1f0 !important; }
:deep(.row-online) { background-color: #f0f9eb !important; }
</style>
