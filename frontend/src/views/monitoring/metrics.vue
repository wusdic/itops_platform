<template>
  <div>
    <div class="page-header">
      <h2>监控指标</h2>
    </div>

    <n-tabs v-model:value="activeTab" type="line">
      <n-tab-pane name="query" tab="指标查询">
        <n-card :bordered="false">
          <n-space vertical :size="12">
            <n-space>
              <n-input v-model:value="promql" placeholder="输入 PromQL 查询语句" style="flex:1" @keyup.ctrl.enter="handlePromqlQuery" />
              <n-button type="primary" :loading="queryLoading" @click="handlePromqlQuery">查询</n-button>
            </n-space>
            <n-select v-model:value="selectedMetric" :options="metricOptions" placeholder="或选择预设指标快速查询" clearable style="width:400px" @update:value="handleMetricSelect" />
          </n-space>
          <div ref="metricChartRef" style="height:400px;margin-top:16px"></div>
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="hosts" tab="主机列表">
        <n-card :bordered="false">
          <n-data-table
            :columns="hostColumns"
            :data="hosts"
            :loading="hostsLoading"
            :pagination="hostPagination"
            remote
          />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="configs" tab="采集配置">
        <n-card :bordered="false" style="margin-bottom:16px">
          <n-space>
            <n-button type="primary" :loading="collecting" @click="handleCollect">手动采集</n-button>
          </n-space>
        </n-card>
        <n-card :bordered="false">
          <n-data-table
            :columns="configColumns"
            :data="configs"
            :loading="configsLoading"
            :pagination="configPagination"
            remote
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { ref, h, onMounted, nextTick } from 'vue'
import { NTag, NButton, NSpace, NSwitch, useMessage } from 'naive-ui'
import * as echarts from 'echarts'
import { queryMetrics, getMonitoredHosts, getAvailableMetrics, promqlQuery, collectMetrics, getMetricConfigs, toggleMetricConfig } from '@/api/monitoring'
import dayjs from 'dayjs'

const message = useMessage()

const activeTab = ref('query')

// Metric query
const promql = ref('')
const selectedMetric = ref(null)
const metricOptions = ref([])
const queryLoading = ref(false)
const metricChartRef = ref(null)
let metricChart = null

// Hosts
const hostsLoading = ref(false)
const hosts = ref([])
const hostPagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { hostPagination.value.page = p; loadHosts() },
  onUpdatePageSize: (s) => { hostPagination.value.pageSize = s; hostPagination.value.page = 1; loadHosts() }
})

// Configs
const configsLoading = ref(false)
const configs = ref([])
const collecting = ref(false)
const configPagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { configPagination.value.page = p; loadConfigs() },
  onUpdatePageSize: (s) => { configPagination.value.pageSize = s; configPagination.value.page = 1; loadConfigs() }
})

const statusType = (status) => {
  const map = { online: 'success', offline: 'error', warning: 'warning' }
  return map[status] || 'default'
}

const statusLabel = (status) => {
  const map = { online: '在线', offline: '离线', warning: '告警' }
  return map[status] || status
}

const hostColumns = [
  { title: '主机名', key: 'hostname', width: 200, ellipsis: { tooltip: true } },
  { title: 'IP', key: 'ip', width: 160 },
  {
    title: '状态', key: 'status', width: 100,
    render: (row) => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusLabel(row.status) })
  },
  { title: 'CPU', key: 'cpu_usage', width: 100, render: (row) => row.cpu_usage != null ? `${row.cpu_usage.toFixed(1)}%` : '-' },
  { title: '内存', key: 'memory_usage', width: 100, render: (row) => row.memory_usage != null ? `${row.memory_usage.toFixed(1)}%` : '-' },
  { title: '磁盘', key: 'disk_usage', width: 100, render: (row) => row.disk_usage != null ? `${row.disk_usage.toFixed(1)}%` : '-' },
  { title: '更新时间', key: 'updated_at', width: 180, render: (row) => formatTime(row.updated_at) }
]

const configColumns = [
  { title: '指标名称', key: 'metric_name', width: 200 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '采集间隔', key: 'interval', width: 120, render: (row) => row.interval ? `${row.interval}s` : '-' },
  {
    title: '状态', key: 'enabled', width: 100,
    render: (row) => h(NSwitch, {
      value: row.enabled,
      loading: row._toggling,
      onUpdateValue: () => handleToggleConfig(row)
    })
  },
  { title: '更新时间', key: 'updated_at', width: 180, render: (row) => formatTime(row.updated_at) }
]

const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'

async function handlePromqlQuery() {
  if (!promql.value) { message.warning('请输入 PromQL 查询语句'); return }
  queryLoading.value = true
  try {
    const res = await promqlQuery({ query: promql.value })
    const data = res.data || {}
    renderChart(data.series || [], data.timestamps || [])
    message.success('查询成功')
  } catch (e) {
    message.error('查询失败：' + (e.response?.data?.message || e.message))
  } finally {
    queryLoading.value = false
  }
}

async function handleMetricSelect(metric) {
  if (!metric) return
  promql.value = metric
  await handlePromqlQuery()
}

async function loadAvailableMetrics() {
  try {
    const res = await getAvailableMetrics()
    const data = res.data || []
    metricOptions.value = Array.isArray(data) ? data.map(m => ({ label: m.name || m.metric, value: m.name || m.metric })) : []
  } catch (e) {
    // Non-critical
  }
}

function renderChart(series, timestamps) {
  if (!metricChartRef.value) return
  if (!metricChart) metricChart = echarts.init(metricChartRef.value)
  const colors = ['#2080f0', '#18a058', '#f0a020', '#d03050', '#646cff', '#999']
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { top: 10 },
    grid: { left: 60, right: 20, top: 50, bottom: 40 },
    xAxis: {
      type: 'category',
      data: timestamps.length ? timestamps.map(t => dayjs(t).format('HH:mm')) : []
    },
    yAxis: { type: 'value' },
    series: (series.length ? series : [{ name: 'Value', data: [] }]).map((s, i) => ({
      name: s.name || 'Value',
      type: 'line',
      smooth: true,
      data: s.data || [],
      itemStyle: { color: colors[i % colors.length] }
    }))
  }
  metricChart.setOption(option, true)
}

async function loadHosts() {
  hostsLoading.value = true
  try {
    const res = await getMonitoredHosts({ page: hostPagination.value.page, page_size: hostPagination.value.pageSize })
    const data = res.data || {}
    hosts.value = data.items || []
    hostPagination.value.itemCount = data.total || 0
  } catch (e) {
    message.error('加载主机列表失败：' + (e.response?.data?.message || e.message))
  } finally {
    hostsLoading.value = false
  }
}

async function loadConfigs() {
  configsLoading.value = true
  try {
    const res = await getMetricConfigs({ page: configPagination.value.page, page_size: configPagination.value.pageSize })
    const data = res.data || {}
    configs.value = (data.items || []).map(c => ({ ...c, _toggling: false }))
    configPagination.value.itemCount = data.total || 0
  } catch (e) {
    message.error('加载采集配置失败：' + (e.response?.data?.message || e.message))
  } finally {
    configsLoading.value = false
  }
}

async function handleToggleConfig(row) {
  row._toggling = true
  try {
    await toggleMetricConfig(row.id)
    row.enabled = !row.enabled
    message.success('配置已更新')
  } catch (e) {
    message.error('更新失败：' + (e.response?.data?.message || e.message))
  } finally {
    row._toggling = false
  }
}

async function handleCollect() {
  collecting.value = true
  try {
    await collectMetrics({})
    message.success('采集任务已触发')
    loadHosts()
  } catch (e) {
    message.error('采集失败：' + (e.response?.data?.message || e.message))
  } finally {
    collecting.value = false
  }
}

onMounted(() => {
  loadAvailableMetrics()
  loadHosts()
  loadConfigs()
  nextTick(() => {
    metricChart = echarts.init(metricChartRef.value)
    metricChart.setOption({
      title: { text: '指标趋势图', left: 'center', textStyle: { color: '#999', fontWeight: 'normal' } },
      grid: { left: 60, right: 20, top: 50, bottom: 40 },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: [{ name: '暂无数据', type: 'line', smooth: true, data: [], itemStyle: { color: '#ccc' } }]
    })
  })
})
</script>
