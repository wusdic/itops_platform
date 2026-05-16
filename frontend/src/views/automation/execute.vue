<template>
  <div class="page-container">
    <n-card title="执行记录" :bordered="false">
      <template #header-extra>
        <n-button quaternary @click="loadData">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新
        </n-button>
      </template>

      <n-space style="margin-bottom: 12px">
        <n-input v-model:value="searchKeyword" placeholder="搜索执行ID或脚本名称" clearable style="width: 240px" @change="loadData">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="执行状态" clearable style="width: 140px" @change="loadData" />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="executionList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 执行详情抽屉 -->
    <n-drawer v-model:show="detailDrawer" :width="600" placement="right">
      <n-drawer-content title="执行详情">
        <n-descriptions label-placement="top" :column="1">
          <n-descriptions-item label="ID">{{ currentExecution?.id || '-' }}</n-descriptions-item>
          <n-descriptions-item label="规则名称">{{ currentExecution?.name || '-' }}</n-descriptions-item>
          <n-descriptions-item label="触发类型">{{ currentExecution?.trigger_type || '-' }}</n-descriptions-item>
          <n-descriptions-item label="状态">{{ currentExecution?.enabled ? '启用' : '停用' }}</n-descriptions-item>
          <n-descriptions-item label="创建时间">{{ currentExecution?.created_at || '-' }}</n-descriptions-item>
        </n-descriptions>
        <n-divider />
        <n-input type="textarea" :value="currentExecution?.description || '暂无描述'" :rows="10" readonly placeholder="暂无执行结果" />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NSelect, NInput, NSpace, NTag, NIcon, NDrawer, NDrawerContent, NDescriptions, NDescriptionsItem, NDivider, useMessage } from 'naive-ui'
import { RefreshOutline, SearchOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const executionList = ref([])
const searchKeyword = ref('')
const filterStatus = ref(null)
const detailDrawer = ref(false)
const currentExecution = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const statusOptions = [
  { label: '全部', value: null },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '进行中', value: 'running' }
]

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '规则名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '类型', key: 'trigger_type', width: 100 },
  { title: '状态', key: 'enabled', width: 80,
    render: (r) => h('span', { style: r.enabled ? 'color:#18a058' : 'color:#999' }, r.enabled ? '启用' : '停用')
  },
  { title: '创建时间', key: 'created_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 100,
    render(row) {
      return h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => handleDetail(row) }, () => '详情')
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({ page: pagination.page, page_size: pagination.pageSize })
    if (filterStatus.value) params.append('status', filterStatus.value)
    if (searchKeyword.value) params.append('search', searchKeyword.value)
    const res = await fetch(`/api/v1/automation/trigger-rules?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    executionList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载执行记录失败: ${e.message}`)
    console.error('[automation/execute] loadData error:', e)
    executionList.value = []
  } finally {
    loading.value = false
  }
}

function handleDetail(row) {
  currentExecution.value = row
  detailDrawer.value = true
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
