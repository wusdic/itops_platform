<template>
  <div class="alerts-container">
    <n-card title="告警管理" :bordered="false">
      <template #header-extra>
        <n-space>
          <n-select v-model:value="filterLevel" :options="levelOptions" placeholder="告警级别" clearable style="width: 120px" />
          <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="处理状态" clearable style="width: 120px" />
          <n-button type="primary" @click="loadAlerts">刷新</n-button>
        </n-space>
      </template>

      <n-data-table
        :columns="columns"
        :data="alerts"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        :row-key="row => row.id"
      />
    </n-card>

    <n-drawer v-model:show="showDrawer" :width="500" placement="right">
      <n-drawer-content title="告警详情">
        <n-descriptions v-if="currentAlert" :column="1" label-placement="left" bordered>
          <n-descriptions-item label="告警ID">{{ currentAlert.id }}</n-descriptions-item>
          <n-descriptions-item label="告警名称">{{ currentAlert.title }}</n-descriptions-item>
          <n-descriptions-item label="告警级别">
            <n-tag :type="getLevelType(currentAlert.level)">{{ getLevelLabel(currentAlert.level) }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="处理状态">
            <n-tag :type="getStatusType(currentAlert.status)">{{ getStatusLabel(currentAlert.status) }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="设备">{{ currentAlert.device_name }} ({{ currentAlert.device_ip }})</n-descriptions-item>
          <n-descriptions-item label="告警信息">{{ currentAlert.message }}</n-descriptions-item>
          <n-descriptions-item label="发生时间">{{ formatTime(currentAlert.created_at) }}</n-descriptions-item>
          <n-descriptions-item v-if="currentAlert.resolved_at" label="解决时间">{{ formatTime(currentAlert.resolved_at) }}</n-descriptions-item>
        </n-descriptions>

        <template #footer>
          <n-space justify="end">
            <n-button @click="showDrawer = false">关闭</n-button>
            <n-button v-if="currentAlert && currentAlert.status === 'active'" type="primary" @click="handleResolve">标记已处理</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import {
  NCard, NDataTable, NButton, NSpace, NSelect, NDrawer, NDrawerContent,
  NDescriptions, NDescriptionsItem, NTag
} from 'naive-ui'

const alerts = ref([])
const loading = ref(false)
const showDrawer = ref(false)
const currentAlert = ref(null)
const filterLevel = ref(null)
const filterStatus = ref(null)

const levelOptions = [
  { label: 'Critical', value: 'critical' },
  { label: 'Warning', value: 'warning' },
  { label: 'Info', value: 'info' }
]

const statusOptions = [
  { label: '活跃', value: 'active' },
  { label: '已确认', value: 'acknowledged' },
  { label: '已解决', value: 'resolved' }
]

const levelMap = { critical: 'Critical', warning: 'Warning', info: 'Info' }
const statusMap = { active: '活跃', acknowledged: '已确认', resolved: '已解决' }

const getLevelType = (level) => ({ critical: 'error', warning: 'warning', info: 'info' }[level] || 'default')
const getStatusType = (status) => ({ pending: 'warning', processing: 'info', resolved: 'success' }[status] || 'default')
const getLevelLabel = (level) => levelMap[level] || level
const getStatusLabel = (status) => statusMap[status] || status
const formatTime = (ts) => ts ? new Date(ts).toLocaleString() : '-'

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '告警名称', key: 'title', ellipsis: true },
  { 
    title: '级别', 
    key: 'level',
    render: (row) => h(NTag, { type: getLevelType(row.level), size: 'small' }, () => getLevelLabel(row.level))
  },
  { 
    title: '状态', 
    key: 'status',
    render: (row) => h(NTag, { type: getStatusType(row.status), size: 'small' }, () => getStatusLabel(row.status))
  },
  { title: '设备', key: 'device_name', ellipsis: true },
  { title: '发生时间', key: 'occurred_at', render: (row) => formatTime(row.occurred_at) },
  {
    title: '操作',
    key: 'actions',
    render: (row) => h(NButton, { size: 'small', type: 'primary', ghost: true, onClick: () => openDetail(row) }, () => '查看')
  }
]

const openDetail = (alert) => {
  currentAlert.value = alert
  showDrawer.value = true
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
  }
}

const handleResolve = async () => {
  if (!currentAlert.value) return
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/monitoring/alerts/${currentAlert.value.id}/resolve`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    })
    if (res.ok) {
      showDrawer.value = false
      loadAlerts()
    }
  } catch (e) {
    console.error('Failed to resolve alert:', e)
  }
}

onMounted(() => {
  loadAlerts()
})
</script>

<style scoped>
.alerts-container {
  padding: 16px;
}
</style>
