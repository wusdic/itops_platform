<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的工单</h1>
        <p class="page-subtitle">查看和处理您负责的工单</p>
      </div>
    </div>

    <n-card class="filter-bar">
      <n-space>
        <n-input
          v-model:value="searchKeyword"
          placeholder="搜索工单标题"
          clearable
          style="width: 200px"
          @change="handleSearch"
        />
        <n-select
          v-model:value="filterStatus"
          placeholder="工单状态"
          :options="statusOptions"
          clearable
          style="width: 140px"
          @change="handleSearch"
        />
        <n-select
          v-model:value="filterPriority"
          placeholder="优先级"
          :options="priorityOptions"
          clearable
          style="width: 120px"
          @change="handleSearch"
        />
        <n-button type="primary" @click="loadData">刷新</n-button>
      </n-space>
    </n-card>

    <n-card class="table-container">
      <n-data-table
        :columns="columns"
        :data="workorderList"
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, h } from 'vue'
import { useAppStore } from '@/stores/app'
import {
  NCard, NInput, NSelect, NButton, NSpace,
  NDataTable, NPagination, NTag, NModal, NForm, NFormItem
} from 'naive-ui'

const appStore = useAppStore()
const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref(null)
const filterPriority = ref(null)
const workorderList = ref([])

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const totalPages = computed(() => Math.ceil(pagination.total / pagination.pageSize) || 1)

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '已关闭', value: 'closed' }
]

const priorityOptions = [
  { label: '紧急', value: 'urgent' },
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' }
]

const getPriorityTagType = (priority) => {
  const map = { urgent: 'error', high: 'warning', medium: 'info', low: 'default' }
  return map[priority] || 'default'
}

const getPriorityText = (priority) => {
  const map = { urgent: '紧急', high: '高', medium: '中', low: '低' }
  return map[priority] || priority
}

const getStatusTagType = (status) => {
  const map = { pending: 'default', processing: 'info', completed: 'success', closed: 'default' }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = { pending: '待处理', processing: '处理中', completed: '已完成', closed: '已关闭' }
  return map[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const columns = [
  { title: '工单号', key: 'id', width: 100 },
  { title: '工单标题', key: 'title', minWidth: 200 },
  {
    title: '优先级',
    key: 'priority',
    width: 100,
    render: (row) => h(NTag, { type: getPriorityTagType(row.priority), size: 'small' }, () => getPriorityText(row.priority))
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { type: getStatusTagType(row.status), size: 'small' }, () => getStatusText(row.status))
  },
  { title: '创建人', key: 'creator', width: 120 },
  { title: '处理人', key: 'handler', width: 120 },
  { title: '创建时间', key: 'created_at', width: 180, render: (row) => formatTime(row.created_at) }
]

const fetchApi = async (url, options = {}) => {
  const token = appStore.token
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
    if (filterStatus.value) params.append('status', filterStatus.value)
    if (filterPriority.value) params.append('priority', filterPriority.value)

    const res = await fetchApi(`/api/v1/workorders?${params}`)
    // Support both {items, total} and {data, total} formats
    if (res.items) {
      workorderList.value = res.items
      pagination.total = res.total || 0
    } else if (res.data && Array.isArray(res.data)) {
      workorderList.value = res.data
      pagination.total = res.total || 0
    } else if (Array.isArray(res)) {
      workorderList.value = res
      pagination.total = res.length
    } else {
      workorderList.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('Load workorders error:', error)
    workorderList.value = []
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
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
