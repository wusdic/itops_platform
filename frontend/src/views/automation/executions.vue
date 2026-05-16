<template>
  <div>
    <div class="page-header">
      <h2>执行历史</h2>
    </div>

    <n-tabs v-model:value="activeTab" type="line">
      <n-tab-pane name="executions" tab="执行历史">
        <n-card :bordered="false">
          <n-data-table
            :columns="execColumns"
            :data="executions"
            :loading="execLoading"
            :pagination="execPagination"
            remote
          />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="rollback" tab="回滚历史">
        <n-card :bordered="false">
          <n-data-table
            :columns="rollbackColumns"
            :data="rollbacks"
            :loading="rollbackLoading"
            :pagination="rollbackPagination"
            remote
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- Execution Detail Modal -->
    <n-modal v-model:show="detailModal" preset="card" title="执行详情" style="width:700px">
      <n-descriptions :column="2" bordered v-if="currentExecution">
        <n-descriptions-item label="执行ID">{{ currentExecution.id }}</n-descriptions-item>
        <n-descriptions-item label="触发规则">{{ currentExecution.rule_name || '-' }}</n-descriptions-item>
        <n-descriptions-item label="目标设备">{{ currentExecution.target_device || '-' }}</n-descriptions-item>
        <n-descriptions-item label="执行动作">{{ currentExecution.action || '-' }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="execStatusType(currentExecution.status)">{{ execStatusLabel(currentExecution.status) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="开始时间">{{ formatTime(currentExecution.started_at) }}</n-descriptions-item>
        <n-descriptions-item label="结束时间">{{ formatTime(currentExecution.finished_at) }}</n-descriptions-item>
        <n-descriptions-item label="耗时">{{ currentExecution.duration || '-' }}</n-descriptions-item>
      </n-descriptions>
      <n-divider>检查点时间线</n-divider>
      <n-timeline v-if="currentExecution?.checkpoints?.length">
        <n-timeline-item v-for="cp in currentExecution.checkpoints" :key="cp.id"
          :type="cp.status === 'success' ? 'success' : cp.status === 'failed' ? 'error' : 'info'"
          :title="cp.name || '检查点'"
          :content="cp.message || ''"
          :time="formatTime(cp.created_at)" />
      </n-timeline>
      <n-empty v-else description="暂无检查点记录" />

      <template #footer>
        <n-space justify="end">
          <n-button @click="detailModal = false">关闭</n-button>
          <n-button v-if="currentExecution?.status === 'completed'" type="warning" :loading="rollbackLoading2" @click="handleRollback(currentExecution)">
            回滚
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NTag, NButton, NSpace, useMessage, useDialog } from 'naive-ui'
import { getRollbackHistory, executeRollback, getSnapshot } from '@/api/automation'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const activeTab = ref('executions')

// Execution history
const execLoading = ref(false)
const executions = ref([])
const execPagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { execPagination.value.page = p; loadExecutions() },
  onUpdatePageSize: (s) => { execPagination.value.pageSize = s; execPagination.value.page = 1; loadExecutions() }
})

// Rollback history
const rollbackLoading = ref(false)
const rollbacks = ref([])
const rollbackPagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { rollbackPagination.value.page = p; loadRollbacks() },
  onUpdatePageSize: (s) => { rollbackPagination.value.pageSize = s; rollbackPagination.value.page = 1; loadRollbacks() }
})

// Detail
const detailModal = ref(false)
const currentExecution = ref(null)
const rollbackLoading2 = ref(false)

const execStatusType = (status) => {
  const map = { pending: 'warning', running: 'info', completed: 'success', failed: 'error', rolled_back: 'default' }
  return map[status] || 'default'
}

const execStatusLabel = (status) => {
  const map = { pending: '待执行', running: '执行中', completed: '已完成', failed: '失败', rolled_back: '已回滚' }
  return map[status] || status
}

const rollbackStatusType = (status) => {
  const map = { success: 'success', failed: 'error', pending: 'warning' }
  return map[status] || 'default'
}

const rollbackStatusLabel = (status) => {
  const map = { success: '成功', failed: '失败', pending: '待执行' }
  return map[status] || status
}

const execColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '触发规则', key: 'rule_name', width: 160, ellipsis: { tooltip: true } },
  { title: '目标设备', key: 'target_device', width: 160, ellipsis: { tooltip: true } },
  { title: '执行动作', key: 'action', width: 130 },
  {
    title: '状态', key: 'status', width: 100,
    render: (row) => h(NTag, { type: execStatusType(row.status), size: 'small' }, { default: () => execStatusLabel(row.status) })
  },
  { title: '耗时', key: 'duration', width: 100 },
  { title: '开始时间', key: 'started_at', width: 180, render: (row) => formatTime(row.started_at) },
  {
    title: '操作', key: 'actions', width: 140, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', type: 'info', onClick: () => handleDetail(row) }, { default: () => '详情' }),
        row.status === 'completed' ? h(NButton, { size: 'small', type: 'warning', onClick: () => handleQuickRollback(row) }, { default: () => '回滚' }) : null
      ].filter(Boolean)
    })
  }
]

const rollbackColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '原始执行', key: 'execution_id', width: 100 },
  { title: '目标设备', key: 'target_device', width: 160, ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'status', width: 100,
    render: (row) => h(NTag, { type: rollbackStatusType(row.status), size: 'small' }, { default: () => rollbackStatusLabel(row.status) })
  },
  { title: '操作人', key: 'operator', width: 120 },
  { title: '原因', key: 'reason', ellipsis: { tooltip: true } },
  { title: '执行时间', key: 'created_at', width: 180, render: (row) => formatTime(row.created_at) }
]

const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'

async function loadExecutions() {
  execLoading.value = true
  try {
    // getSnapshot may not be list API, try with getRollbackHistory first
    const res = await getRollbackHistory({ page: execPagination.value.page, page_size: execPagination.value.pageSize })
    const data = res.data || {}
    // If the API returns both, separate them
    executions.value = data.items || data.executions || []
    execPagination.value.itemCount = data.total || 0
  } catch (e) {
    message.error('加载执行历史失败：' + (e.response?.data?.message || e.message))
  } finally {
    execLoading.value = false
  }
}

async function loadRollbacks() {
  rollbackLoading.value = true
  try {
    const res = await getRollbackHistory({ page: rollbackPagination.value.page, page_size: rollbackPagination.value.pageSize })
    const data = res.data || {}
    rollbacks.value = data.rollback_items || data.items || []
    rollbackPagination.value.itemCount = data.total || data.rollback_total || 0
  } catch (e) {
    message.error('加载回滚历史失败：' + (e.response?.data?.message || e.message))
  } finally {
    rollbackLoading.value = false
  }
}

async function handleDetail(row) {
  currentExecution.value = row
  detailModal.value = true
  // Load snapshot if available
  try {
    const res = await getSnapshot(row.id)
    if (res.data) {
      currentExecution.value = { ...row, ...res.data }
    }
  } catch (e) {
    // Snapshot not available, use existing data
  }
}

async function handleRollback(row) {
  dialog.warning({
    title: '确认回滚',
    content: `确定要回滚执行 #${row.id} 吗？`,
    positiveText: '回滚',
    negativeText: '取消',
    onPositiveClick: async () => {
      rollbackLoading2.value = true
      try {
        await executeRollback(row.id)
        message.success('回滚已执行')
        detailModal.value = false
        loadExecutions()
        loadRollbacks()
      } catch (e) {
        message.error('回滚失败：' + (e.response?.data?.message || e.message))
      } finally {
        rollbackLoading2.value = false
      }
    }
  })
}

async function handleQuickRollback(row) {
  dialog.warning({
    title: '确认回滚',
    content: `确定要回滚执行 #${row.id} 吗？`,
    positiveText: '回滚',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await executeRollback(row.id)
        message.success('回滚已执行')
        loadExecutions()
        loadRollbacks()
      } catch (e) {
        message.error('回滚失败：' + (e.response?.data?.message || e.message))
      }
    }
  })
}

onMounted(() => { loadExecutions(); loadRollbacks() })
</script>
