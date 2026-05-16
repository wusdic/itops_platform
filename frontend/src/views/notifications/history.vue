<template>
  <div>
    <div class="page-header">
      <h2>通知历史</h2>
    </div>

    <!-- 筛选 -->
    <n-card :bordered="false" style="margin-bottom: 16px">
      <n-space :wrap="true">
        <n-select v-model:value="filterChannel" :options="channelOptions"
          placeholder="渠道类型" style="width: 140px" clearable @update:value="loadHistory" />
        <n-select v-model:value="filterStatus" :options="statusOptions"
          placeholder="状态" style="width: 130px" clearable @update:value="loadHistory" />
        <n-date-picker v-model:value="dateRange" type="daterange"
          placeholder="日期范围" clearable style="width: 240px"
          @update:value="loadHistory" />
        <n-input v-model:value="searchText" placeholder="搜索..."
          style="width: 200px" clearable @update:value="loadHistory" />
      </n-space>
    </n-card>

    <!-- 历史列表 -->
    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="history"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 详情弹窗 -->
    <n-modal v-model:show="showDetailModal" preset="card" title="通知详情"
      style="width: 600px" :bordered="false">
      <n-descriptions :column="1" bordered v-if="detailData">
        <n-descriptions-item label="ID">{{ detailData.id }}</n-descriptions-item>
        <n-descriptions-item label="渠道类型">
          <n-tag size="small">{{ channelLabel(detailData.channel_type) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="接收人">{{ detailData.recipient || '-' }}</n-descriptions-item>
        <n-descriptions-item label="标题">{{ detailData.title || '-' }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="statusType(detailData.status)" size="small">
            {{ statusLabel(detailData.status) }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="发送时间">
          {{ detailData.sent_at ? formatDate(detailData.sent_at) : '-' }}
        </n-descriptions-item>
        <n-descriptions-item label="内容">
          <pre style="white-space: pre-wrap; margin: 0; font-size: 13px">{{ detailData.content || '-' }}</pre>
        </n-descriptions-item>
        <n-descriptions-item label="错误信息" v-if="detailData.error">
          <n-alert type="error" style="margin-top: 4px">
            <pre style="white-space: pre-wrap; margin: 0; font-size: 13px">{{ detailData.error }}</pre>
          </n-alert>
        </n-descriptions-item>
        <n-descriptions-item label="重试状态" v-if="detailData.retry_count">
          <n-tag :type="detailData.retry_success ? 'success' : 'error'" size="small">
            重试 {{ detailData.retry_count }} 次
            {{ detailData.retry_success ? ' (成功)' : ' (失败)' }}
          </n-tag>
        </n-descriptions-item>
      </n-descriptions>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { useMessage, NButton, NSpace, NIcon, NTag, NDescriptions, NDescriptionsItem, NAlert } from 'naive-ui'
import { EyeOutline } from '@vicons/ionicons5'
import { getNotificationHistory } from '@/api/notification'
import dayjs from 'dayjs'

const message = useMessage()
const loading = ref(false)
const history = ref([])
const filterChannel = ref(null)
const filterStatus = ref(null)
const dateRange = ref(null)
const searchText = ref('')

const pagination = ref({ page: 1, pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] })

const channelOptions = [
  { label: '邮件', value: 'email' },
  { label: '钉钉', value: 'dingtalk' },
  { label: '飞书', value: 'feishu' },
  { label: '企微', value: 'wecom' },
  { label: '站内信', value: 'in_app' }
]

const statusOptions = [
  { label: '待发送', value: 'pending' },
  { label: '发送中', value: 'sending' },
  { label: '已发送', value: 'sent' },
  { label: '发送失败', value: 'failed' },
  { label: '已送达', value: 'delivered' }
]

const showDetailModal = ref(false)
const detailData = ref(null)

function channelLabel(type) {
  const opt = channelOptions.find(o => o.value === type)
  return opt?.label || type || '-'
}

function statusLabel(status) {
  const map = { pending: '待发送', sending: '发送中', sent: '已发送', failed: '发送失败', delivered: '已送达' }
  return map[status] || status || '-'
}

function statusType(status) {
  const map = { pending: 'warning', sending: 'info', sent: 'success', failed: 'error', delivered: 'success' }
  return map[status] || 'default'
}

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const columns = ref([
  { title: 'ID', key: 'id', width: 80 },
  {
    title: '渠道', key: 'channel_type', width: 100,
    render: row => h(NTag, { size: 'small' }, { default: () => channelLabel(row.channel_type) })
  },
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  { title: '接收人', key: 'recipient', width: 160, ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'status', width: 100,
    render: row => h(NTag, { type: statusType(row.status), size: 'small' },
      { default: () => statusLabel(row.status) })
  },
  {
    title: '发送时间', key: 'sent_at', width: 180,
    render: row => formatDate(row.sent_at)
  },
  {
    title: '操作', key: 'actions', width: 80, fixed: 'right',
    render: row => h(NButton, { size: 'small', onClick: () => showDetail(row) },
      { default: () => '详情', icon: () => h(NIcon, null, { default: () => h(EyeOutline) }) })
  }
])

async function loadHistory() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }
    if (filterChannel.value) params.channel_type = filterChannel.value
    if (filterStatus.value) params.status = filterStatus.value
    if (searchText.value) params.search = searchText.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dayjs(dateRange.value[0]).format('YYYY-MM-DD')
      params.end_date = dayjs(dateRange.value[1]).format('YYYY-MM-DD')
    }

    const res = await getNotificationHistory(params)
    const data = res.data || {}
    history.value = data.items || data.notifications || data || []
    if (data.total !== undefined) pagination.value.itemCount = data.total
  } catch (e) {
    console.error('Load history error:', e)
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

function showDetail(row) {
  detailData.value = row
  showDetailModal.value = true
}

onMounted(() => {
  loadHistory()
})
</script>
