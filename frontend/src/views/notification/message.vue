<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的消息</h1>
        <p class="page-subtitle">查看系统通知和告警消息</p>
      </div>
      <el-button type="primary" @click="handleMarkAllRead" :loading="markingRead">
        全部标为已读
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-radio-group v-model="filterStatus" @change="handleFilterChange">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="unread">未读</el-radio-button>
        <el-radio-button label="read">已读</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 消息列表 -->
    <div class="message-list" v-loading="loading">
      <el-empty v-if="!loading && messageList.length === 0" description="暂无消息" />

      <div
        v-for="msg in messageList"
        :key="msg.id"
        class="message-item"
        :class="{ unread: !msg.is_read }"
        @click="handleClickMessage(msg)"
      >
        <div class="message-icon">
          <el-badge :is-dot="!msg.is_read">
            <el-icon size="20"><Bell /></el-icon>
          </el-badge>
        </div>
        <div class="message-content">
          <div class="message-header">
            <span class="message-title">{{ msg.title }}</span>
            <el-tag v-if="msg.type" size="small" type="info">{{ getTypeLabel(msg.type) }}</el-tag>
          </div>
          <div class="message-body">{{ msg.content || '暂无内容' }}</div>
          <div class="message-footer">
            <span class="message-time">{{ formatTime(msg.created_at) }}</span>
            <span v-if="msg.sender" class="message-sender">发送者: {{ msg.sender }}</span>
          </div>
        </div>
        <div class="message-actions">
          <el-button
            v-if="!msg.is_read"
            type="primary"
            link
            size="small"
            @click.stop="handleMarkRead(msg)"
          >
            标为已读
          </el-button>
          <el-button
            type="danger"
            link
            size="small"
            @click.stop="handleDelete(msg)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="pagination.total > 0">
      <el-pagination
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell } from '@element-plus/icons-vue'
import { notification } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const markingRead = ref(false)
const messageList = ref([])
const filterStatus = ref('all')
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const typeMap = {
  email: '邮件',
  sms: '短信',
  webhook: 'Webhook',
  dingtalk: '钉钉',
  feishu: '飞书',
  wechat: '企业微信',
  system: '系统通知',
  alert: '告警'
}

const getTypeLabel = (type) => typeMap[type] || type || '通知'

onMounted(() => { loadData() })

const handleFilterChange = () => {
  pagination.page = 1
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterStatus.value === 'unread') {
      params.is_read = false
    } else if (filterStatus.value === 'read') {
      params.is_read = true
    }
    const res = await notification.getHistory(params).catch(() => ({ items: [], total: 0 }))
    messageList.value = res.items || res.list || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load messages error:', error)
  } finally {
    loading.value = false
  }
}

const handleClickMessage = async (msg) => {
  if (!msg.is_read) {
    await handleMarkRead(msg)
  }
}

const handleMarkRead = async (msg) => {
  try {
    // 尝试调用标记已读API，如果后端没有此接口则使用本地更新
    if (notification.markRead) {
      await notification.markRead(msg.id)
    } else {
      // 本地更新状态
      msg.is_read = true
    }
    loadData()
  } catch (error) {
    console.error('Mark read error:', error)
    ElMessage.error('标记已读失败')
  }
}

const handleMarkAllRead = async () => {
  try {
    await ElMessageBox.confirm('确定要将所有消息标为已读吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    markingRead.value = true
    // 尝试调用全部标记已读API
    if (notification.markAllRead) {
      await notification.markAllRead()
    }
    ElMessage.success('操作成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Mark all read error:', error)
      ElMessage.error('操作失败')
    }
  } finally {
    markingRead.value = false
  }
}

const handleDelete = async (msg) => {
  try {
    await ElMessageBox.confirm('确定要删除该消息吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await notification.deleteHistory(msg.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Delete message error:', error)
      ElMessage.error('删除失败')
    }
  }
}
</script>

<style lang="scss" scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  margin: 16px 0;
}

.message-list {
  min-height: 200px;
}

.message-item {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: #f7f8fa;
  }

  &.unread {
    background-color: #f0f7ff;

    &:hover {
      background-color: #e6f0ff;
    }

    .message-title {
      font-weight: 600;
    }
  }
}

.message-icon {
  flex-shrink: 0;
  margin-right: 12px;
  color: #909399;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.message-title {
  font-size: 14px;
  color: #303133;
}

.message-body {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-footer {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #c0c4cc;
}

.message-actions {
  flex-shrink: 0;
  margin-left: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
