<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">备份列表</h1>
        <p class="page-subtitle">查看和管理数据备份记录</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="loadData">刷新</n-button>
      </div>
    </div>

    <n-card class="filter-bar">
      <n-space>
        <n-input
          v-model:value="searchKeyword"
          placeholder="搜索备份名称"
          clearable
          style="width: 200px"
          @change="handleSearch"
        />
        <n-select
          v-model:value="filterType"
          placeholder="备份类型"
          :options="typeOptions"
          clearable
          style="width: 120px"
          @change="handleSearch"
        />
        <n-select
          v-model:value="filterStatus"
          placeholder="备份状态"
          :options="statusOptions"
          clearable
          style="width: 120px"
          @change="handleSearch"
        />
      </n-space>
    </n-card>

    <n-card class="table-container">
      <n-data-table
        :columns="columns"
        :data="backupList"
        :loading="loading"
        :pagination="false"
        :row-key="(row) => row.id"
      />
      <div class="pagination">
        <n-pagination
          v-model:page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-count="totalPages"
          show-quick-jumper
          @update:page="loadData"
          @update:page-size="loadData"
        />
      </div>
    </n-card>

    <n-modal v-model:show="detailModalVisible" preset="card" title="备份详情" style="max-width: 600px;">
      <n-descriptions label-placement="top" :column="1" v-if="currentBackup">
        <n-descriptions-item label="备份名称">{{ currentBackup.name || currentBackup.backup_name }}</n-descriptions-item>
        <n-descriptions-item label="备份类型">{{ currentBackup.type === 'full' ? '全量' : '增量' }}</n-descriptions-item>
        <n-descriptions-item label="备份时间">{{ formatTime(currentBackup.backup_at || currentBackup.created_at) }}</n-descriptions-item>
        <n-descriptions-item label="备份大小">{{ currentBackup.size || '-' }}</n-descriptions-item>
        <n-descriptions-item label="状态">{{ currentBackup.status === 'success' ? '成功' : '失败' }}</n-descriptions-item>
        <n-descriptions-item label="操作人">{{ currentBackup.operator || '-' }}</n-descriptions-item>
        <n-descriptions-item label="备注">{{ currentBackup.remark || '-' }}</n-descriptions-item>
      </n-descriptions>
      <template #footer>
        <n-space justify="end">
          <n-button @click="detailModalVisible = false">关闭</n-button>
          <n-button type="primary" @click="handleRestore">恢复此备份</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, h } from 'vue'

import {
  NCard, NInput, NSelect, NButton, NSpace,
  NDataTable, NPagination, NTag, NModal,
  NDescriptions, NDescriptionsItem, NDivider
} from 'naive-ui'
import { useMessage } from 'naive-ui'

const message = useMessage()

const loading = ref(false)
const searchKeyword = ref('')
const filterType = ref(null)
const filterStatus = ref(null)
const backupList = ref([])
const detailModalVisible = ref(false)
const currentBackup = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const totalPages = computed(() => Math.ceil(pagination.total / pagination.pageSize) || 1)

const typeOptions = [
  { label: '全量', value: 'full' },
  { label: '增量', value: 'incremental' }
]

const statusOptions = [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '进行中', value: 'running' }
]

const getTypeText = (type) => {
  return type === 'full' ? '全量' : '增量'
}

const getStatusTagType = (status) => {
  const map = { success: 'success', failed: 'error', running: 'warning' }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = { success: '成功', failed: '失败', running: '进行中' }
  return map[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const columns = [
  { title: '备份名称', key: 'name', minWidth: 180 },
  {
    title: '备份类型',
    key: 'type',
    width: 100,
    render: (row) => h(NTag, { type: 'info', size: 'small' }, () => getTypeText(row.type))
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { type: getStatusTagType(row.status), size: 'small' }, () => getStatusText(row.status))
  },
  { title: '备份时间', key: 'backup_at', width: 180, render: (row) => formatTime(row.backup_at || row.created_at) },
  { title: '备份大小', key: 'size', width: 120 },
  { title: '操作人', key: 'operator', width: 120 },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'small', onClick: () => handleView(row) }, () => '详情'),
      h(NButton, { size: 'small', type: 'primary', onClick: () => handleRestore(row) }, () => '恢复')
    ])
  }
]

const fetchApi = async (url, options = {}) => {
  const token = localStorage.getItem('token') || ''
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
      ...options.headers
    }
  })
  if (!res.ok) throw new Error(`HTTP error ${res.status}`)
  return res.json()
}

const loadData = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: pagination.page,
      page_size: pagination.pageSize
    })
    if (searchKeyword.value) params.append('keyword', searchKeyword.value)
    if (filterType.value) params.append('type', filterType.value)
    if (filterStatus.value) params.append('status', filterStatus.value)

    const res = await fetchApi(`/api/v1/backup/list?${params}`)
    // Support both {items, total} and {data, total} formats
    if (res.items) {
      backupList.value = res.items
      pagination.total = res.total || 0
    } else if (res.data && Array.isArray(res.data)) {
      backupList.value = res.data
      pagination.total = res.total || 0
    } else if (Array.isArray(res)) {
      backupList.value = res
      pagination.total = res.length
    } else {
      backupList.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('Load backup list error:', error)
    backupList.value = []
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

const handleView = (row) => {
  currentBackup.value = row
  detailModalVisible.value = true
}

const handleRestore = async (row) => {
  if (row) {
    currentBackup.value = row
  }
  if (!currentBackup.value) return
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/admin/backup/${currentBackup.value.id}/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({})
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
      message.error(`恢复失败: ${err.message || res.status}`)
      return
    }
    message.success('备份恢复成功')
    detailModalVisible.value = false
  } catch (e) {
    message.error(`恢复失败: ${e.message}`)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}
.page-subtitle {
  font-size: 14px;
  color: #666;
  margin: 4px 0 0 0;
}
.filter-bar {
  margin-bottom: 16px;
}
.table-container {
  margin-bottom: 16px;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
