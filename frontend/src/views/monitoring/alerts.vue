<template>
  <div class="alerts-container">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">告警管理</h1>
        <p class="page-subtitle">监控系统告警信息</p>
      </div>
    </div>

    <!-- Stats Summary -->
    <div v-if="alertStats" class="alert-stats">
      <div class="stat-badge critical" @click="filterLevel = 'critical'">
        <span class="stat-count">{{ alertStats.critical || 0 }}</span>
        <span class="stat-label">严重</span>
      </div>
      <div class="stat-badge warning" @click="filterLevel = 'warning'">
        <span class="stat-count">{{ alertStats.warning || 0 }}</span>
        <span class="stat-label">警告</span>
      </div>
      <div class="stat-badge info" @click="filterLevel = 'info'">
        <span class="stat-count">{{ alertStats.info || 0 }}</span>
        <span class="stat-label">提示</span>
      </div>
      <div class="stat-badge active" @click="filterStatus = 'active'">
        <span class="stat-count">{{ alertStats.active || 0 }}</span>
        <span class="stat-label">待处理</span>
      </div>
      <span v-if="lastUpdateTime" class="update-time">最后更新: {{ lastUpdateTime }}</span>
    </div>

    <!-- Filter Bar -->
    <n-card :bordered="false" class="filter-card">
      <template #header-extra>
        <n-space :size="12" align="center">
          <n-select v-model:value="filterLevel" :options="levelOptions" placeholder="告警级别" clearable style="width: 130px" @update:value="loadAlerts" />
          <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="处理状态" clearable style="width: 130px" @update:value="loadAlerts" />
          <n-button type="primary" @click="loadAlerts" :loading="loading">
            <template #icon>
              <n-icon><Refresh /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </template>
    </n-card>

    <!-- Alert Table -->
    <n-card :bordered="false" class="table-card">
      <template #header>
        <span>告警列表 <span class="table-count">共 {{ alerts.length }} 条</span></span>
      </template>
      <n-data-table
        :columns="columns"
        :data="alerts"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        :row-key="row => row.id"
        :row-class-name="getRowClassName"
      />
    </n-card>

    <!-- Detail Drawer -->
    <n-drawer v-model:show="showDrawer" :width="600" placement="right">
      <n-drawer-content title="告警详情">
        <n-descriptions v-if="currentAlert" :column="1" label-placement="left" bordered size="large">
          <n-descriptions-item label="告警ID">{{ currentAlert.id }}</n-descriptions-item>
          <n-descriptions-item label="告警名称">{{ currentAlert.title }}</n-descriptions-item>
          <n-descriptions-item label="告警级别">
            <n-tag :type="getLevelType(currentAlert.level)" size="small">{{ getLevelLabel(currentAlert.level) }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="处理状态">
            <n-tag :type="getStatusType(currentAlert.status)" size="small">{{ getStatusLabel(currentAlert.status) }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="设备">{{ currentAlert.device_name }} ({{ currentAlert.device_ip }})</n-descriptions-item>
          <n-descriptions-item label="告警信息">{{ currentAlert.message }}</n-descriptions-item>
          <n-descriptions-item label="发生时间">{{ formatTime(currentAlert.occurred_at || currentAlert.created_at) }}</n-descriptions-item>
          <n-descriptions-item v-if="currentAlert.acknowledged_at" label="确认时间">{{ formatTime(currentAlert.acknowledged_at) }}</n-descriptions-item>
          <n-descriptions-item v-if="currentAlert.resolved_at" label="解决时间">{{ formatTime(currentAlert.resolved_at) }}</n-descriptions-item>
        </n-descriptions>

        <template #footer>
          <n-space justify="end">
            <n-button @click="showDrawer = false">关闭</n-button>
            <n-button v-if="currentAlert && currentAlert.status === 'active'" type="warning" :loading="actionLoading" @click="handleAcknowledge(currentAlert)">确认</n-button>
            <n-button v-if="currentAlert && currentAlert.status !== 'resolved'" type="primary" :loading="actionLoading" @click="handleResolve(currentAlert)">标记已解决</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, h, computed, onMounted, onUnmounted } from 'vue'
import {
  NCard, NDataTable, NButton, NSpace, NSelect, NDrawer, NDrawerContent,
  NDescriptions, NDescriptionsItem, NTag, NIcon, useMessage, useDialog
} from 'naive-ui'
import { Refresh } from '@vicons/ionicons5'

const alerts = ref([])
const loading = ref(false)
const showDrawer = ref(false)
const currentAlert = ref(null)
const filterLevel = ref(null)
const filterStatus = ref(null)
const actionLoading = ref(false)
const lastUpdateTime = ref('')

const levelOptions = [
  { label: '严重 (Critical)', value: 'critical' },
  { label: '警告 (Warning)', value: 'warning' },
  { label: '提示 (Info)', value: 'info' }
]

const statusOptions = [
  { label: '活跃', value: 'active' },
  { label: '已确认', value: 'acknowledged' },
  { label: '已解决', value: 'resolved' }
]

const alertStats = computed(() => {
  const stats = { critical: 0, warning: 0, info: 0, active: 0 }
  alerts.value.forEach(a => {
    if (a.level === 'critical') stats.critical++
    else if (a.level === 'warning') stats.warning++
    else if (a.level === 'info') stats.info++
    if (a.status === 'active') stats.active++
  })
  return stats
})

const levelMap = { critical: '严重', warning: '警告', info: '提示' }
const statusMap = { active: '活跃', acknowledged: '已确认', resolved: '已解决' }

const getLevelType = (level) => ({ critical: 'error', warning: 'warning', info: 'info' }[level] || 'default')
const getStatusType = (status) => ({ active: 'warning', acknowledged: 'info', resolved: 'success' }[status] || 'default')
const getLevelLabel = (level) => levelMap[level] || level
const getStatusLabel = (status) => statusMap[status] || status
const formatTime = (ts) => ts ? new Date(ts).toLocaleString('zh-CN') : '-'

const getRowClassName = ({ row }) => {
  if (row.status === 'active') return 'row-active'
  if (row.status === 'resolved') return 'row-resolved'
  return ''
}

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '告警名称', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '级别',
    key: 'level',
    width: 90,
    render: (row) => h(NTag, { type: getLevelType(row.level), size: 'small' }, () => getLevelLabel(row.level))
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) => h(NTag, { type: getStatusType(row.status), size: 'small' }, () => getStatusLabel(row.status))
  },
  { title: '设备', key: 'device_name', ellipsis: { tooltip: true }, width: 140 },
  { title: '发生时间', key: 'occurred_at', render: (row) => formatTime(row.occurred_at || row.created_at), width: 170 },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row) => h(NSpace, { size: 'small' }, () => [
      h(NButton, {
        size: 'small', type: 'primary', ghost: true,
        disabled: row.status === 'resolved' || actionLoading.value,
        onClick: () => openDetail(row)
      }, () => '查看'),
      h(NButton, {
        size: 'small', type: 'warning',
        disabled: row.status !== 'active' || actionLoading.value,
        onClick: () => handleAcknowledge(row)
      }, () => '确认'),
      h(NButton, {
        size: 'small', type: 'success',
        disabled: row.status === 'resolved' || actionLoading.value,
        onClick: () => handleResolve(row)
      }, () => '解决')
    ])
  }
]

const openDetail = (alert) => {
  currentAlert.value = alert
  showDrawer.value = true
}

let messageInstance = null
let dialogInstance = null

const getMessage = () => {
  if (!messageInstance) messageInstance = useMessage()
  return messageInstance
}

const getDialog = () => {
  if (!dialogInstance) dialogInstance = useDialog()
  return dialogInstance
}

const handleAcknowledge = async (alert) => {
  const dialog = getDialog()
  dialog.warning({
    title: '确认操作',
    content: `确定要确认告警"${alert.title}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      actionLoading.value = true
      try {
        const token = localStorage.getItem('token') || ''
        const res = await fetch(`/api/v1/monitoring/alerts/${alert.id}/acknowledge`, {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        })
        if (res.ok) {
          getMessage().success('告警已确认')
          showDrawer.value = false
          loadAlerts()
        } else {
          const err = await res.json().catch(() => ({}))
          getMessage().error(err.message || '确认告警失败')
        }
      } catch (e) {
        getMessage().error('确认告警失败')
      } finally {
        actionLoading.value = false
      }
    }
  })
}

const handleResolve = async (alert) => {
  const dialog = getDialog()
  dialog.warning({
    title: '确认操作',
    content: `确定要解决告警"${alert.title}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      actionLoading.value = true
      try {
        const token = localStorage.getItem('token') || ''
        const res = await fetch(`/api/v1/monitoring/alerts/${alert.id}/resolve`, {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        })
        if (res.ok) {
          getMessage().success('告警已解决')
          showDrawer.value = false
          loadAlerts()
        } else {
          const err = await res.json().catch(() => ({}))
          getMessage().error(err.message || '解决告警失败')
        }
      } catch (e) {
        getMessage().error('解决告警失败')
      } finally {
        actionLoading.value = false
      }
    }
  })
}

const loadAlerts = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams()
    if (filterLevel.value) params.append('level', filterLevel.value)
    if (filterStatus.value) params.append('status', filterStatus.value)

    const res = await fetch(`/api/v1/monitoring/alerts?${params}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      alerts.value = data.items || []
    }
  } catch (e) {
    console.error('Failed to load alerts:', e)
  } finally {
    loading.value = false
    lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
}

let pollTimer = null

onMounted(() => { loadAlerts() })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.alerts-container {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #909399;
  margin: 4px 0 0 0;
}

.alert-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stat-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.stat-badge:hover {
  transform: translateY(-1px);
}

.stat-badge.critical {
  background: #fff1f0;
  border: 1px solid #ffccc7;
}

.stat-badge.warning {
  background: #fff7e6;
  border: 1px solid #ffe58f;
}

.stat-badge.info {
  background: #e8f4ff;
  border: 1px solid #adc6ff;
}

.stat-badge.active {
  background: #f0f5ff;
  border: 1px solid #adc6ff;
}

.stat-count {
  font-size: 20px;
  font-weight: 700;
}

.stat-badge.critical .stat-count { color: #f53f3f; }
.stat-badge.warning .stat-count { color: #ff7d00; }
.stat-badge.info .stat-count { color: #165dff; }
.stat-badge.active .stat-count { color: #165dff; }

.stat-label {
  font-size: 13px;
  color: #606266;
}

.update-time {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.filter-card {
  margin-bottom: 12px;
}

.table-card {
  /* */
}

.table-count {
  font-size: 13px;
  color: #909399;
  font-weight: normal;
  margin-left: 8px;
}

/* Row status colors */
:deep(.row-active) {
  background-color: #fff1f0 !important;
}

:deep(.row-resolved) {
  background-color: #f0f9eb !important;
}
</style>
