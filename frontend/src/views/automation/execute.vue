<template>
  <div class="page-container">
    <n-card title="回滚历史" :bordered="false">
      <template #header-extra>
        <n-button quaternary @click="loadData">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新
        </n-button>
      </template>

      <n-space style="margin-bottom: 12px">
        <n-input v-model:value="searchKeyword" placeholder="搜索执行ID或规则名称" clearable style="width: 240px" @change="loadData">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="回滚状态" clearable style="width: 140px" @change="loadData" />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="rollbackList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.execution_id"
      />
    </n-card>

    <!-- 快照详情 -->
    <n-modal v-model:show="snapshotDialogVisible" preset="card" title="执行快照" style="width: 800px">
      <n-spin :show="snapshotLoading">
        <n-input type="textarea" :value="snapshotDetail" :rows="25" readonly placeholder="暂无快照数据" />
      </n-spin>
      <template #footer>
        <n-space justify="end">
          <n-button @click="snapshotDialogVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 回滚详情抽屉 -->
    <n-drawer v-model:show="detailDrawer" :width="600" placement="right">
      <n-drawer-content title="回滚详情">
        <n-spin :show="detailLoading">
          <n-descriptions label-placement="top" :column="1" v-if="currentRollback">
            <n-descriptions-item label="执行ID">{{ currentRollback.execution_id || '-' }}</n-descriptions-item>
            <n-descriptions-item label="规则名称">{{ currentRollback.rule_name || '-' }}</n-descriptions-item>
            <n-descriptions-item label="触发时间">{{ currentRollback.triggered_at || '-' }}</n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="getStatusType(currentRollback.status)">{{ getStatusText(currentRollback.status) }}</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="设备ID">{{ currentRollback.device_id || '-' }}</n-descriptions-item>
            <n-descriptions-item label="指标名称">{{ currentRollback.metric_name || '-' }}</n-descriptions-item>
            <n-descriptions-item label="触发值">{{ currentRollback.trigger_value ?? '-' }}</n-descriptions-item>
          </n-descriptions>
          <n-divider />
          <div v-if="currentRollback && currentRollback.actions_taken">
            <div style="font-weight: 500; margin-bottom: 8px;">执行的操作:</div>
            <n-input type="textarea" :value="formatActions(currentRollback.actions_taken)" :rows="8" readonly />
          </div>
          <n-empty v-else description="暂无操作详情" />
        </n-spin>
        <template #footer>
          <n-space justify="end">
            <n-button @click="handleViewSnapshot">查看快照</n-button>
            <n-button @click="detailDrawer = false">关闭</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NSelect, NInput, NSpace, NTag, NIcon, NDrawer, NDrawerContent, NDescriptions, NDescriptionsItem, NDivider, NEmpty, NSpin, useMessage } from 'naive-ui'
import { RefreshOutline, SearchOutline, EyeOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const snapshotLoading = ref(false)
const detailLoading = ref(false)
const rollbackList = ref([])
const searchKeyword = ref('')
const filterStatus = ref(null)
const detailDrawer = ref(false)
const snapshotDialogVisible = ref(false)
const currentRollback = ref(null)
const snapshotDetail = ref('')

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const statusOptions = [
  { label: '全部', value: null },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '进行中', value: 'running' },
  { label: '回滚中', value: 'rolling_back' }
]

const columns = [
  { title: '执行ID', key: 'execution_id', width: 120 },
  { title: '规则名称', key: 'rule_name', ellipsis: { tooltip: true } },
  { title: '设备ID', key: 'device_id', width: 100 },
  { title: '指标', key: 'metric_name', ellipsis: { tooltip: true } },
  { title: '触发值', key: 'trigger_value', width: 100 },
  { title: '状态', key: 'status', width: 100,
    render: (r) => {
      return h(NTag, { size: 'small', type: getStatusType(r.status) }, () => getStatusText(r.status))
    }
  },
  { title: '触发时间', key: 'triggered_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 160, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => handleDetail(row) }, () => '详情'),
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleViewSnapshot(row) }, () => '快照')
      ])
    }
  }
]

function getStatusType(status) {
  const map = { success: 'success', failed: 'error', running: 'warning', rolling_back: 'info', pending: 'default' }
  return map[status] || 'default'
}

function getStatusText(status) {
  const map = { success: '成功', failed: '失败', running: '进行中', rolling_back: '回滚中', pending: '待处理' }
  return map[status] || status || '-'
}

function formatActions(actions) {
  if (typeof actions === 'string') {
    try {
      return JSON.stringify(JSON.parse(actions), null, 2)
    } catch {
      return actions
    }
  }
  return JSON.stringify(actions, null, 2)
}

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({ page: pagination.page, page_size: pagination.pageSize })
    if (filterStatus.value) params.append('status', filterStatus.value)
    if (searchKeyword.value) params.append('search', searchKeyword.value)
    const res = await fetch(`/api/v1/automation/rollback-history?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    rollbackList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载回滚历史失败: ${e.message}`)
    console.error('[automation/execute] loadData error:', e)
    rollbackList.value = []
  } finally {
    loading.value = false
  }
}

async function handleDetail(row) {
  currentRollback.value = row
  detailDrawer.value = true
}

async function handleViewSnapshot(row) {
  const executionId = row?.execution_id || currentRollback.value?.execution_id
  if (!executionId) {
    message.warning('无法获取执行ID')
    return
  }
  currentRollback.value = row || currentRollback.value
  snapshotDialogVisible.value = true
  snapshotDetail.value = ''
  snapshotLoading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/automation/executions/${executionId}/snapshot`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    snapshotDetail.value = JSON.stringify(data, null, 2)
  } catch (e) {
    snapshotDetail.value = `加载快照失败: ${e.message}`
    message.error(`加载快照失败: ${e.message}`)
    console.error('[automation/execute] snapshot error:', e)
  } finally {
    snapshotLoading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
