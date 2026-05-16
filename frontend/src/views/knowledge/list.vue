<template>
  <div class="knowledge-list-container">
    <n-card>
      <template #header>
        <div class="card-header">
          <span>知识文档</span>
          <n-button type="primary" @click="loadDocs">刷新</n-button>
        </div>
      </template>
      <n-data-table
        :columns="columns"
        :data="documents"
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
          @update:page="loadDocs"
          @update:page-size="loadDocs"
        />
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, h } from 'vue'
import { useAppStore } from '@/stores/app'
import { NCard, NButton, NDataTable, NPagination, NTag } from 'naive-ui'

const appStore = useAppStore()
const documents = ref([])
const loading = ref(false)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const totalPages = computed(() => Math.ceil(pagination.total / pagination.pageSize) || 1)

const columns = [
  { title: '标题', key: 'title', minWidth: 200 },
  { title: '分类', key: 'category', width: 150 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      const typeMap = { active: 'success', draft: 'default', archived: 'warning' }
      const textMap = { active: '启用', draft: '草稿', archived: '归档' }
      return h(NTag, { type: typeMap[row.status] || 'default', size: 'small' }, () => textMap[row.status] || row.status)
    }
  },
  { title: '更新时间', key: 'updated_at', width: 180, render: (row) => formatTime(row.updated_at) }
]

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

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

const loadDocs = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: pagination.page,
      page_size: pagination.pageSize
    })
    const res = await fetchApi(`/api/v1/knowledge/docs?${params}`)
    // Support both {items, total} and {data, total} formats
    if (res.items) {
      documents.value = res.items
      pagination.total = res.total || 0
    } else if (res.data && Array.isArray(res.data)) {
      documents.value = res.data
      pagination.total = res.total || 0
    } else if (Array.isArray(res)) {
      documents.value = res
      pagination.total = res.length
    } else {
      documents.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('Load knowledge docs error:', error)
    documents.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadDocs)
</script>

<style scoped>
.knowledge-list-container {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
