<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的消息</h1>
        <p class="page-subtitle">查看系统通知和告警消息</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" link @click="markAllRead">全部标为已读</n-button>
      </div>
    </div>
    <div class="filter-bar">
      <n-select v-model="filterType" placeholder="消息类型" style="width: 140px" clearable @change="handleSearch">
        <n-option label="系统通知" value="system" />
        <n-option label="告警通知" value="alert" />
        <n-option label="工单通知" value="workorder" />
      </n-select>
      <n-select v-model="filterRead" placeholder="阅读状态" style="width: 140px" clearable @change="handleSearch">
        <n-option label="未读" value="unread" />
        <n-option label="已读" value="read" />
      </n-select>
    </div>
    <div class="message-list">
      <div v-for="msg in messageList" :key="msg.id" :class="['message-item', { unread: !msg.read }]" @click="handleRead(msg)">
        <div class="message-icon">
          <n-icon size="24" :color="getTypeColor(msg.type)"><BellOutline v-if="msg.type === 'alert'" /><ChatboxOutline v-else /></n-icon>
        </div>
        <div class="message-content">
          <div class="message-title">{{ msg.title }}</div>
          <div class="message-body">{{ msg.content }}</div>
          <div class="message-time">{{ formatTime(msg.created_at) }}</div>
        </div>
        <div class="message-actions">
          <n-badge is-dot :hidden="msg.read"><n-button type="primary" link size="small">查看</n-button></n-badge>
        </div>
      </div>
      <n-empty v-if="messageList.length === 0" description="暂无消息" />
    </div>
    <div class="pagination">
      <n-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadData"
        @current-change="loadData"
      />
    </div>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { notification } from '@/api'
import { formatTime } from '@/utils/date'
const loading = ref(false)
const filterType = ref('')
const filterRead = ref('')
const messageList = ref([])
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
onMounted(() => { loadData() })
const loadData = async () => {
  loading.value = true
  try {
    const res = await notification.getList({ page: pagination.page, page_size: pagination.pageSize, type: filterType.value, status: filterRead.value }).catch(() => ({ items: [], total: 0 }))
    messageList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load messages error:', error) }
  finally { loading.value = false }
}
const handleSearch = () => { pagination.page = 1; loadData() }
const getTypeColor = (type) => ({ alert: '#f53f3f', system: '#165dff', workorder: '#00b42a' }[type] || '#86909c')
const handleRead = async (msg) => {
  if (!msg.read) {
    try {
      await notification.markAsRead(msg.id)
      msg.read = true
    } catch (error) { console.error('Mark read error:', error) }
  }
  message.info(`查看消息: ${msg.title}`)
}
const markAllRead = async () => {
  try {
    await notification.markAllAsRead()
    message.success('已全部标为已读')
    loadData()
  } catch (error) { console.error('Mark all read error:', error) }
}
</script>
<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.message-list { background: #fff; border-radius: 8px; overflow: hidden; }
.message-item { display: flex; gap: 16px; padding: 16px; border-bottom: 1px solid #f2f3f5; cursor: pointer; transition: background 0.2s; &:hover { background: #f7f8fa; } &.unread { background: #e8f0ff; &:hover { background: #d9e8ff; } } &:last-child { border-bottom: none; } }
.message-icon { flex-shrink: 0; width: 40px; height: 40px; border-radius: 50%; background: #f7f8fa; display: flex; align-items: center; justify-content: center; }
.message-content { flex: 1; .message-title { font-size: 14px; font-weight: 500; color: #1d2129; } .message-body { font-size: 13px; color: #86909c; margin-top: 4px; } .message-time { font-size: 12px; color: #c9cdd4; margin-top: 4px; } }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
