<template>
  <div v-if="deviceInfo">
    <div class="page-header">
      <h2>设备详情 - {{ deviceInfo.name || name }}</h2>
      <n-button @click="$router.push('/devices')">
        <template #icon><n-icon><ArrowBackOutline /></n-icon></template>
        返回列表
      </n-button>
    </div>

    <n-grid cols="2 s:1" responsive="screen" :x-gap="16" :y-gap="16">
      <!-- 基本信息 -->
      <n-gi>
        <n-card title="基本信息" :bordered="false">
          <n-descriptions :column="2" bordered>
            <n-descriptions-item label="设备名称">{{ deviceInfo.name || '-' }}</n-descriptions-item>
            <n-descriptions-item label="主机名">{{ deviceInfo.hostname || '-' }}</n-descriptions-item>
            <n-descriptions-item label="IP地址">{{ deviceInfo.ip || '-' }}</n-descriptions-item>
            <n-descriptions-item label="设备类型">{{ deviceInfo.device_type || '-' }}</n-descriptions-item>
            <n-descriptions-item label="厂商">{{ deviceInfo.vendor || '-' }}</n-descriptions-item>
            <n-descriptions-item label="型号">{{ deviceInfo.model || '-' }}</n-descriptions-item>
            <n-descriptions-item label="操作系统">{{ deviceInfo.os_type || '-' }}</n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="statusTypeMap[deviceInfo.status] || 'default'" size="small">
                {{ statusLabelMap[deviceInfo.status] || deviceInfo.status }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="位置" :span="2">{{ deviceInfo.location || '-' }}</n-descriptions-item>
            <n-descriptions-item label="备注" :span="2">{{ deviceInfo.remark || '-' }}</n-descriptions-item>
          </n-descriptions>
        </n-card>
      </n-gi>

      <!-- 实时指标 -->
      <n-gi>
        <n-card title="实时指标" :bordered="false">
          <n-space vertical :size="24">
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span>CPU 使用率</span>
                <span style="font-weight:700">{{ metrics.cpu || 0 }}%</span>
              </div>
              <n-progress type="line" :percentage="Math.min(metrics.cpu || 0, 100)"
                :color="metricColor(metrics.cpu)" :height="16" indicator-placement="inside" />
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span>内存使用率</span>
                <span style="font-weight:700">{{ metrics.memory || 0 }}%</span>
              </div>
              <n-progress type="line" :percentage="Math.min(metrics.memory || 0, 100)"
                :color="metricColor(metrics.memory)" :height="16" indicator-placement="inside" />
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span>磁盘使用率</span>
                <span style="font-weight:700">{{ metrics.disk || 0 }}%</span>
              </div>
              <n-progress type="line" :percentage="Math.min(metrics.disk || 0, 100)"
                :color="metricColor(metrics.disk)" :height="16" indicator-placement="inside" />
            </div>
          </n-space>
          <template #header-extra>
            <n-button size="small" @click="loadMetrics" :loading="metricsLoading">
              <template #icon><n-icon><RefreshOutline /></n-icon></template>
              刷新
            </n-button>
          </template>
        </n-card>
      </n-gi>

      <!-- 指标配置 -->
      <n-gi :span="2">
        <n-card title="指标采集配置" :bordered="false">
          <n-data-table
            :columns="metricColumns"
            :data="metricConfigs"
            :loading="metricLoading"
            size="small"
            :pagination="false"
          />
        </n-card>
      </n-gi>
    </n-grid>
  </div>
  <n-spin v-else :show="true" style="min-height:400px" />
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { ArrowBackOutline, RefreshOutline } from '@vicons/ionicons5'
import { getDeviceByName, getDeviceMetrics, listDeviceMetricConfigs } from '@/api/device'

const route = useRoute()
const message = useMessage()
const name = route.params.name

const deviceInfo = ref(null)
const metrics = reactive({ cpu: 0, memory: 0, disk: 0 })
const metricsLoading = ref(false)
const metricLoading = ref(false)
const metricConfigs = ref([])

const statusTypeMap = { online: 'success', offline: 'error', maintenance: 'warning' }
const statusLabelMap = { online: '在线', offline: '离线', maintenance: '维护中' }

function metricColor(val) {
  if (val > 80) return '#d03050'
  if (val > 60) return '#f0a020'
  return '#18a058'
}

const metricColumns = [
  { title: '指标名称', key: 'name' },
  { title: '标识', key: 'metric_key', width: 160 },
  {
    title: '启用', key: 'enabled', width: 100,
    render: row => h('n-switch', {
      value: !!row.enabled,
      onUpdateValue: (v) => handleToggleMetric(row, v)
    })
  },
  { title: '采集间隔', key: 'interval', width: 120, render: row => row.interval ? `${row.interval}s` : '-' },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } }
]

async function loadDevice() {
  try {
    const res = await getDeviceByName(name)
    deviceInfo.value = res.data || res
  } catch (e) {
    message.error('加载设备信息失败')
    console.error(e)
  }
}

async function loadMetrics() {
  metricsLoading.value = true
  try {
    const res = await getDeviceMetrics(name)
    const d = res.data || res || {}
    metrics.cpu = d.cpu_usage ?? d.cpu ?? 0
    metrics.memory = d.memory_usage ?? d.memory ?? 0
    metrics.disk = d.disk_usage ?? d.disk ?? 0
  } catch (e) {
    console.error(e)
  } finally {
    metricsLoading.value = false
  }
}

async function loadMetricConfigs() {
  metricLoading.value = true
  try {
    const res = await listDeviceMetricConfigs(name)
    metricConfigs.value = res.data?.items || res.items || res.data || []
  } catch (e) {
    console.error(e)
  } finally {
    metricLoading.value = false
  }
}

async function handleToggleMetric(row, enabled) {
  try {
    row.enabled = enabled
    message.success(`${row.name} 已${enabled ? '启用' : '禁用'}`)
  } catch (e) {
    message.error('操作失败')
  }
}

onMounted(() => {
  loadDevice()
  loadMetrics()
  loadMetricConfigs()
})
</script>
