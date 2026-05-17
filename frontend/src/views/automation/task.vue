<template>
  <div class="page-container">
    <n-card title="指标评估" :bordered="false">
      <n-tabs type="line" animated>
        <n-tab-pane name="evaluate" tab="指标评估">
          <n-form :model="form" label-placement="left" label-width="100" style="max-width: 600px; margin-top: 16px;">
            <n-form-item label="设备" required>
              <n-select v-model:value="form.device_id" :options="deviceOptions" placeholder="请选择设备" style="width: 100%" @update:value="loadMetrics" />
            </n-form-item>
            <n-form-item label="指标" required>
              <n-select v-model:value="form.metric_name" :options="metricOptions" placeholder="请先选择设备" style="width: 100%" :disabled="!form.device_id" />
            </n-form-item>
            <n-form-item label="阈值(可选)">
              <n-input v-model:value="form.threshold" placeholder="请输入阈值(可选)" />
            </n-form-item>
            <n-form-item>
              <n-space>
                <n-button type="primary" @click="handleEvaluate" :loading="evaluating">评估</n-button>
                <n-button @click="resetForm">重置</n-button>
              </n-space>
            </n-form-item>
          </n-form>

          <!-- 评估结果 -->
          <n-card v-if="evalResult" title="评估结果" style="margin-top: 16px;" :bordered="true">
            <n-descriptions label-placement="top" :column="2" v-if="evalResult">
              <n-descriptions-item label="设备ID">{{ evalResult.device_id || '-' }}</n-descriptions-item>
              <n-descriptions-item label="指标名称">{{ evalResult.metric_name || '-' }}</n-descriptions-item>
              <n-descriptions-item label="当前值">{{ evalResult.current_value ?? '-' }}</n-descriptions-item>
              <n-descriptions-item label="阈值">{{ evalResult.threshold ?? '-' }}</n-descriptions-item>
              <n-descriptions-item label="状态">
                <n-tag :type="getStatusType(evalResult.status)">{{ getStatusText(evalResult.status) }}</n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="执行ID">{{ evalResult.execution_id || '-' }}</n-descriptions-item>
            </n-descriptions>
            <n-divider />
            <n-input type="textarea" :value="evalResultDetail" :rows="8" readonly placeholder="暂无详细结果" />
          </n-card>
        </n-tab-pane>

        <n-tab-pane name="history" tab="评估历史">
          <n-space style="margin-bottom: 12px">
            <n-button quaternary @click="loadHistory" :loading="historyLoading">
              <template #icon><n-icon><RefreshOutline /></n-icon></template>
              刷新
            </n-button>
          </n-space>
          <n-data-table
            :columns="historyColumns"
            :data="historyList"
            :loading="historyLoading"
            :pagination="historyPagination"
            :row-key="row => row.execution_id"
          />
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 快照详情 -->
    <n-modal v-model:show="snapshotDialogVisible" preset="card" title="执行快照" style="width: 700px">
      <n-spin :show="snapshotLoading">
        <n-input type="textarea" :value="snapshotDetail" :rows="20" readonly placeholder="暂无快照数据" />
      </n-spin>
      <template #footer>
        <n-space justify="end">
          <n-button @click="snapshotDialogVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NSpace, NTag, NIcon, NSpin, NTabs, NTabPane, NDescriptions, NDescriptionsItem, NDivider, useMessage } from 'naive-ui'
import { RefreshOutline, SearchOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const evaluating = ref(false)
const historyLoading = ref(false)
const snapshotLoading = ref(false)
const deviceOptions = ref([])
const metricOptions = ref([])
const evalResult = ref(null)
const evalResultDetail = ref('')
const historyList = ref([])
const snapshotDialogVisible = ref(false)
const snapshotDetail = ref('')
const currentExecutionId = ref(null)

const form = reactive({ device_id: null, metric_name: null, threshold: '' })
const historyPagination = reactive({ page: 1, pageSize: 10, total: 0 })

const historyColumns = [
  { title: '执行ID', key: 'execution_id', width: 120 },
  { title: '设备ID', key: 'device_id', width: 100 },
  { title: '指标名称', key: 'metric_name', ellipsis: { tooltip: true } },
  { title: '当前值', key: 'current_value', width: 100 },
  { title: '状态', key: 'status', width: 100,
    render: (r) => {
      const typeMap = { normal: 'success', warning: 'warning', critical: 'error', triggered: 'error' }
      const textMap = { normal: '正常', warning: '警告', critical: '严重', triggered: '触发' }
      return h(NTag, { size: 'small', type: typeMap[r.status] || 'default' }, () => textMap[r.status] || r.status || '-')
    }
  },
  { title: '触发时间', key: 'triggered_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 100,
    render(row) {
      return h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => handleViewSnapshot(row) }, () => '快照')
    }
  }
]

function getStatusType(status) {
  const map = { normal: 'success', warning: 'warning', critical: 'error', triggered: 'error' }
  return map[status] || 'default'
}

function getStatusText(status) {
  const map = { normal: '正常', warning: '警告', critical: '严重', triggered: '触发' }
  return map[status] || status || '-'
}

async function loadDevices() {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/assets/device?page=1&page_size=100', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    deviceOptions.value = (data.items || data.data?.items || []).map(d => ({ label: `${d.name} (${d.ip_address})`, value: d.id }))
  } catch (e) {
    message.error(`加载设备失败: ${e.message}`)
    console.error('[automation/task] loadDevices error:', e)
    deviceOptions.value = []
  }
}

async function loadMetrics(deviceId) {
  if (!deviceId) {
    metricOptions.value = []
    return
  }
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/assets/device/${deviceId}/metrics`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const metrics = data.metrics || data.items || data.data?.items || []
    metricOptions.value = metrics.map(m => ({ label: m.name || m.metric_name, value: m.name || m.metric_name }))
  } catch (e) {
    console.error('[automation/task] loadMetrics error:', e)
    // Fallback: use common metric names
    metricOptions.value = [
      { label: 'CPU使用率', value: 'cpu_usage' },
      { label: '内存使用率', value: 'memory_usage' },
      { label: '磁盘使用率', value: 'disk_usage' },
      { label: '网络流量', value: 'network_traffic' }
    ]
  }
}

async function handleEvaluate() {
  if (!form.device_id) { message.warning('请选择设备'); return }
  if (!form.metric_name) { message.warning('请选择指标'); return }
  evaluating.value = true
  evalResult.value = null
  evalResultDetail.value = ''
  try {
    const token = localStorage.getItem('token') || ''
    const payload = {
      device_id: form.device_id,
      metric_name: form.metric_name
    }
    if (form.threshold) {
      payload.threshold = parseFloat(form.threshold)
    }
    const res = await fetch('/api/v1/automation/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    evalResult.value = data
    evalResultDetail.value = JSON.stringify(data, null, 2)
    message.success('评估完成')
  } catch (e) {
    evalResultDetail.value = `评估失败: ${e.message}`
    message.error(`评估失败: ${e.message}`)
    console.error('[automation/task] evaluate error:', e)
  } finally {
    evaluating.value = false
  }
}

async function handleViewSnapshot(row) {
  currentExecutionId.value = row.execution_id
  snapshotDialogVisible.value = true
  snapshotDetail.value = ''
  snapshotLoading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/automation/executions/${row.execution_id}/snapshot`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    snapshotDetail.value = JSON.stringify(data, null, 2)
  } catch (e) {
    snapshotDetail.value = `加载快照失败: ${e.message}`
    message.error(`加载快照失败: ${e.message}`)
    console.error('[automation/task] snapshot error:', e)
  } finally {
    snapshotLoading.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({ page: historyPagination.page, page_size: historyPagination.pageSize })
    const res = await fetch(`/api/v1/automation/rollback-history?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    // 评估历史使用 rollback-history 接口数据
    historyList.value = data.items || data.data?.items || []
    historyPagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载历史记录失败: ${e.message}`)
    console.error('[automation/task] loadHistory error:', e)
    historyList.value = []
  } finally {
    historyLoading.value = false
  }
}

function resetForm() {
  form.device_id = null
  form.metric_name = null
  form.threshold = ''
  evalResult.value = null
  evalResultDetail.value = ''
  metricOptions.value = []
}

onMounted(() => {
  loadDevices()
  loadHistory()
})
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
