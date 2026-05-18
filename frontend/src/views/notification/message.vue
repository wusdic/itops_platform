<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">消息中心</h1>
        <p class="page-subtitle">查看系统通知和告警消息</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="loadData">刷新</n-button>
      </div>
    </div>

    <n-card class="filter-bar">
      <n-space>
        <n-select
          v-model:value="filterRead"
          placeholder="消息状态"
          :options="readOptions"
          clearable
          style="width: 140px"
          @change="handleSearch"
        />
        <n-button @click="handleMarkAllRead">全部标为已读</n-button>
      </n-space>
    </n-card>

    <n-card class="message-list-container">
      <n-list v-if="messages.length > 0">
        <n-list-item
          v-for="msg in messages"
          :key="msg.id"
          @click="handleViewMessage(msg)"
        >
          <n-thing>
            <template #header>
              <n-space justify="space-between" align="center">
                <n-badge :dot="!msg.is_read">
                  <span :class="{ 'unread-title': !msg.is_read }">{{ msg.title }}</span>
                </n-badge>
                <n-tag :type="getTypeTag(msg.type)" size="small">{{ getTypeText(msg.type) }}</n-tag>
              </n-space>
            </template>
            <template #description>
              <p class="message-content">{{ msg.content }}</p>
            </template>
            <template #header-extra>
              <span class="message-time">{{ formatTime(msg.created_at) }}</span>
            </template>
          </n-thing>
        </n-list-item>
      </n-list>
      <n-empty v-else description="暂无消息" />
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

    <n-modal v-model:show="detailModalVisible" preset="card" title="消息详情" style="max-width: 500px;">
      <n-descriptions label-placement="top" :column="1" v-if="currentMessage">
        <n-descriptions-item label="标题">{{ currentMessage.title }}</n-descriptions-item>
        <n-descriptions-item label="类型">{{ getTypeText(currentMessage.type) }}</n-descriptions-item>
        <n-descriptions-item label="时间">{{ formatTime(currentMessage.created_at) }}</n-descriptions-item>
        <n-descriptions-item label="内容">{{ currentMessage.content }}</n-descriptions-item>
      </n-descriptions>
      <template #footer>
        <n-space justify="end">
          <n-button @click="detailModalVisible = false">关闭</n-button>
          <n-button
            v-if="currentMessage && !currentMessage.is_read"
            type="primary"
            @click="handleMarkRead(currentMessage)"
          >
            标为已读
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, h } from 'vue'

import {
  NCard, NSelect, NButton, NSpace, NList, NListItem,
  NThing, NBadge, NTag, NPagination, NEmpty, NModal,
  NDescriptions, NDescriptionsItem
} from 'naive-ui'
import { useMessage } from 'naive-ui'

const message = useMessage()

const loading = ref(false)
const filterRead = ref(null)
const messages = ref([])
const detailModalVisible = ref(false)
const currentMessage = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const totalPages = computed(() => Math.ceil(pagination.total / pagination.pageSize) || 1)

const readOptions = [
  { label: '未读', value: 0 },
  { label: '已读', value: 1 }
]

const getTypeTag = (type) => {
  const map = { info: 'info', warning: 'warning', error: 'error', success: 'success' }
  return map[type] || 'default'
}

const getTypeText = (type) => {
  const map = { info: '通知', warning: '警告', error: '错误', success: '成功' }
  return map[type] || '通知'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

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
    if (filterRead.value !== null && filterRead.value !== '') {
      params.append('is_read', filterRead.value)
    }

    const res = await fetchApi(`/api/v1/notifications/history?${params}`)
    // Support both {items, total} and {data, total} formats
    if (res.items) {
      messages.value = res.items
      pagination.total = res.total || 0
    } else if (res.data && Array.isArray(res.data)) {
      messages.value = res.data
      pagination.total = res.total || 0
    } else if (Array.isArray(res)) {
      messages.value = res
      pagination.total = res.length
    } else {
      messages.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('Load messages error:', error)
    messages.value = []
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

const handleViewMessage = (msg) => {
  currentMessage.value = msg
  detailModalVisible.value = true
  // Auto mark as read when viewed
  if (!msg.is_read) {
    handleMarkRead(msg)
  }
}

const handleMarkRead = async (msg) => {
  try {
    await fetchApi(`/api/v1/notifications/history/${msg.id}/read`, {
      method: 'PUT'
    })
    msg.is_read = true
    message.success('已标为已读')
  } catch (error) {
    console.error('Mark read error:', error)
  }
}

const handleMarkAllRead = async () => {
  try {
    await fetchApi('/api/v1/notifications/history/read-all', {
      method: 'PUT'
    })
    message.success('全部已标为已读')
    loadData()
  } catch (error) {
    console.error('Mark all read error:', error)
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
.message-list-container {
  margin-bottom: 16px;
}
.unread-title {
  font-weight: 600;
}
.message-content {
  margin: 8px 0 0 0;
  color: #666;
  font-size: 14px;
}
.message-time {
  font-size: 12px;
  color: #999;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
