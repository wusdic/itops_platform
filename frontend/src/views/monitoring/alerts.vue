<template>
  <div>
    <div class="page-header">
      <h2>告警管理</h2>
    </div>

    <!-- Toolbar -->
    <n-card :bordered="false" style="margin-bottom:16px">
      <n-space vertical :size="12">
        <n-space :wrap="true">
          <n-input v-model:value="searchKeyword" placeholder="搜索告警标题/设备..." clearable style="width:240px" @keyup.enter="loadAlerts" />
          <n-select v-model:value="levelFilter" placeholder="级别筛选" clearable :options="levelOptions" style="width:160px" />
          <n-select v-model:value="statusFilter" placeholder="状态筛选" clearable :options="statusOptions" style="width:180px" />
          <n-date-picker v-model:value="dateRange" type="daterange" placeholder="日期范围" clearable style="width:260px" />
          <n-button type="primary" @click="loadAlerts">查询</n-button>
          <n-button @click="resetFilters">重置</n-button>
          <n-button type="success" :disabled="!checkedRowKeys.length" @click="batchAcknowledge">批量确认</n-button>
          <n-button type="warning" :disabled="!checkedRowKeys.length" @click="batchResolve">批量解决</n-button>
        </n-space>
      </n-space>
    </n-card>

    <!-- Table -->
    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="alerts"
        :loading="loading"
        :row-key="row => row.id"
        v-model:checked-row-keys="checkedRowKeys"
        :pagination="pagination"
        remote
      />
    </n-card>

    <!-- Detail Drawer -->
    <n-drawer v-model:show="detailDrawer" :width="600" placement="right">
      <n-drawer-content :title="currentAlert?.title || '告警详情'">
        <n-descriptions :column="1" bordered v-if="currentAlert">
          <n-descriptions-item label="告警键">{{ currentAlert.alert_key }}</n-descriptions-item>
          <n-descriptions-item label="设备名称">{{ currentAlert.device_name }}</n-descriptions-item>
          <n-descriptions-item label="级别">
            <n-tag :type="levelType(currentAlert.level)">{{ levelLabel(currentAlert.level) }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="状态">
            <n-tag :type="statusType(currentAlert.status)">{{ statusLabel(currentAlert.status) }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="告警内容">{{ currentAlert.message }}</n-descriptions-item>
          <n-descriptions-item label="发生时间">{{ formatTime(currentAlert.occurred_at) }}</n-descriptions-item>
          <n-descriptions-item label="更新时间">{{ formatTime(currentAlert.updated_at) }}</n-descriptions-item>
        </n-descriptions>

        <n-divider>审计时间线</n-divider>
        <n-timeline v-if="auditLogs.length">
          <n-timeline-item v-for="log in auditLogs" :key="log.id"
            :type="log.action_type === 'acknowledge' ? 'success' : log.action_type === 'resolve' ? 'info' : 'default'"
            :title="log.action_label"
            :content="log.operator || '系统'"
            :time="formatTime(log.created_at)" />
        </n-timeline>
        <n-empty v-else description="暂无审计记录" />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NTag, NButton, NSpace, useMessage, useDialog } from 'naive-ui'
import { getAlerts, acknowledgeAlert, resolveAlert, deleteAlert, getAlertAuditLogs } from '@/api/monitoring'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const searchKeyword = ref('')
const levelFilter = ref(null)
const statusFilter = ref(null)
const dateRange = ref(null)
const alerts = ref([])
const checkedRowKeys = ref([])
const detailDrawer = ref(false)
const currentAlert = ref(null)
const auditLogs = ref([])

const levelOptions = [
  { label: 'Critical', value: 'critical' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
  { label: 'Info', value: 'info' }
]

const statusOptions = [
  { label: 'Active', value: 'active' },
  { label: 'Acknowledged', value: 'acknowledged' },
  { label: 'Resolved', value: 'resolved' }
]

const pagination = ref({
  page: 1,
  pageSize: 10,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onUpdatePage: (page) => { pagination.value.page = page; loadAlerts() },
  onUpdatePageSize: (pageSize) => { pagination.value.pageSize = pageSize; pagination.value.page = 1; loadAlerts() }
})

const levelType = (level) => {
  const map = { critical: 'error', high: 'error', medium: 'warning', low: 'info', info: 'info' }
  return map[level] || 'default'
}

const levelLabel = (level) => {
  const map = { critical: '严重', high: '高', medium: '中', low: '低', info: '信息' }
  return map[level] || level
}

const statusType = (status) => {
  const map = { active: 'error', acknowledged: 'warning', resolved: 'success' }
  return map[status] || 'default'
}

const statusLabel = (status) => {
  const map = { active: '活跃', acknowledged: '已确认', resolved: '已解决' }
  return map[status] || status
}

const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'

const columns = [
  { type: 'selection' },
  { title: '告警键', key: 'alert_key', width: 180, ellipsis: { tooltip: true } },
  { title: '设备名称', key: 'device_name', width: 150, ellipsis: { tooltip: true } },
  {
    title: '级别', key: 'level', width: 90,
    render: (row) => h(NTag, { type: levelType(row.level), size: 'small' }, { default: () => levelLabel(row.level) })
  },
  { title: '标题', key: 'title', width: 200, ellipsis: { tooltip: true } },
  { title: '消息', key: 'message', ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'status', width: 120,
    render: (row) => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusLabel(row.status) })
  },
  { title: '发生时间', key: 'occurred_at', width: 180, render: (row) => formatTime(row.occurred_at) },
  {
    title: '操作', key: 'actions', width: 240, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        row.status === 'active' ? h(NButton, { size: 'small', type: 'success', onClick: () => handleAcknowledge(row) }, { default: () => '确认' }) : null,
        row.status !== 'resolved' ? h(NButton, { size: 'small', type: 'warning', onClick: () => handleResolve(row) }, { default: () => '解决' }) : null,
        h(NButton, { size: 'small', type: 'info', onClick: () => handleDetail(row) }, { default: () => '详情' }),
        h(NButton, { size: 'small', type: 'error', ghost: true, onClick: () => handleDelete(row) }, { default: () => '删除' })
      ].filter(Boolean)
    })
  }
]

async function loadAlerts() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
      keyword: searchKeyword.value || undefined,
      level: levelFilter.value || undefined,
      status: statusFilter.value || undefined
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dayjs(dateRange.value[0]).format('YYYY-MM-DD')
      params.end_date = dayjs(dateRange.value[1]).format('YYYY-MM-DD')
    }
    const res = await getAlerts(params)
    const data = res.data || {}
    alerts.value = data.items || []
    pagination.value.itemCount = data.total || 0
  } catch (e) {
    message.error('加载告警失败：' + (e.response?.data?.message || e.message))
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  searchKeyword.value = ''
  levelFilter.value = null
  statusFilter.value = null
  dateRange.value = null
  pagination.value.page = 1
  loadAlerts()
}

async function handleAcknowledge(row) {
  try {
    await acknowledgeAlert(row.id)
    message.success('告警已确认')
    loadAlerts()
  } catch (e) {
    message.error('确认失败：' + (e.response?.data?.message || e.message))
  }
}

async function handleResolve(row) {
  try {
    await resolveAlert(row.id)
    message.success('告警已解决')
    loadAlerts()
  } catch (e) {
    message.error('解决失败：' + (e.response?.data?.message || e.message))
  }
}

async function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除告警 "${row.title}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteAlert(row.id)
        message.success('删除成功')
        loadAlerts()
      } catch (e) {
        message.error('删除失败：' + (e.response?.data?.message || e.message))
      }
    }
  })
}

async function handleDetail(row) {
  currentAlert.value = row
  detailDrawer.value = true
  try {
    const res = await getAlertAuditLogs(row.id)
    auditLogs.value = (res.data || []).reverse()
  } catch (e) {
    auditLogs.value = []
  }
}

async function batchAcknowledge() {
  dialog.warning({
    title: '批量确认',
    content: `确认选中的 ${checkedRowKeys.value.length} 条告警？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      let success = 0
      for (const id of checkedRowKeys.value) {
        try {
          await acknowledgeAlert(id)
          success++
        } catch (e) { /* skip */ }
      }
      message.success(`成功确认 ${success}/${checkedRowKeys.value.length} 条告警`)
      checkedRowKeys.value = []
      loadAlerts()
    }
  })
}

async function batchResolve() {
  dialog.warning({
    title: '批量解决',
    content: `解决选中的 ${checkedRowKeys.value.length} 条告警？`,
    positiveText: '解决',
    negativeText: '取消',
    onPositiveClick: async () => {
      let success = 0
      for (const id of checkedRowKeys.value) {
        try {
          await resolveAlert(id)
          success++
        } catch (e) { /* skip */ }
      }
      message.success(`成功解决 ${success}/${checkedRowKeys.value.length} 条告警`)
      checkedRowKeys.value = []
      loadAlerts()
    }
  })
}

onMounted(() => loadAlerts())
</script>
