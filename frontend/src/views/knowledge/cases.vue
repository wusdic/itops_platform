<template>
  <div class="page-container">
    <n-card title="故障案例库" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加案例
        </n-button>
      </template>

      <!-- 搜索筛选 -->
      <n-space style="margin-bottom: 16px">
        <n-input v-model:value="searchKeyword" placeholder="搜索标题/关键词" clearable style="width: 200px" @keyup.enter="loadData" />
        <n-select v-model:value="filterSeverity" :options="severityOptions" placeholder="严重程度" clearable style="width: 140px" @update:value="loadData" />
        <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="处理状态" clearable style="width: 140px" @update:value="loadData" />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="list"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </n-card>

    <!-- 详情抽屉 -->
    <n-drawer v-model:show="detailDrawer" :width="640" placement="right">
      <n-drawer-content :title="currentCase?.title || '案例详情'">
        <n-descriptions v-if="currentCase" label-placement="top" :column="1">
          <n-descriptions-item label="案例ID">{{ currentCase.id }}</n-descriptions-item>
          <n-descriptions-item label="严重程度">
            <n-tag :type="getSeverityType(currentCase.severity)" size="small">{{ currentCase.severity }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="处理状态">
            <n-tag :type="getStatusType(currentCase.status)" size="small">{{ currentCase.status }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="关键词">{{ currentCase.keywords || '-' }}</n-descriptions-item>
          <n-descriptions-item label="影响范围">{{ currentCase.impact || '-' }}</n-descriptions-item>
          <n-descriptions-item label="发生时间">{{ currentCase.occurred_at || '-' }}</n-descriptions-item>
          <n-descriptions-item label="解决时间">{{ currentCase.resolved_at || '-' }}</n-descriptions-item>
        </n-descriptions>
        <n-divider />
        <n-tabs type="line">
          <n-tab-pane name="desc" tab="问题描述">
            <div style="white-space: pre-wrap; line-height: 1.8">{{ currentCase?.description || '暂无' }}</div>
          </n-tab-pane>
          <n-tab-pane name="root" tab="根因分析">
            <div style="white-space: pre-wrap; line-height: 1.8">{{ currentCase?.root_cause || '暂无' }}</div>
          </n-tab-pane>
          <n-tab-pane name="solution" tab="解决方案">
            <div style="white-space: pre-wrap; line-height: 1.8">{{ currentCase?.solution || '暂无' }}</div>
          </n-tab-pane>
          <n-tab-pane name="lessons" tab="经验教训">
            <div style="white-space: pre-wrap; line-height: 1.8">{{ currentCase?.lessons_learned || '暂无' }}</div>
          </n-tab-pane>
        </n-tabs>
        <template #footer>
          <n-space justify="end">
            <n-button @click="detailDrawer = false">关闭</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const list = ref([])
const searchKeyword = ref('')
const filterSeverity = ref(null)
const filterStatus = ref(null)
const detailDrawer = ref(false)
const currentCase = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const severityOptions = [
  { label: '严重', value: 'critical' },
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' },
]

const statusOptions = [
  { label: '未解决', value: 'open' },
  { label: '处理中', value: 'in_progress' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' },
]

const columns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '标题', key: 'title', ellipsis: { tooltip: true }, render: (row) => h('a', { href: 'javascript:void(0)', style: 'color:#18a058', onClick: () => showDetail(row) }, row.title) },
  { title: '严重程度', key: 'severity', width: 90,
    render: (row) => h('n-tag', { type: getSeverityType(row.severity), size: 'small' }, () => row.severity || '-') },
  { title: '状态', key: 'status', width: 90,
    render: (row) => h('n-tag', { type: getStatusType(row.status), size: 'small' }, () => row.status || '-') },
  { title: '关键词', key: 'keywords', width: 160, ellipsis: { tooltip: true } },
  { title: '发生时间', key: 'occurred_at', width: 170 },
  { title: '操作', key: 'actions', width: 80,
    render: (row) => h('button', { style: 'color:#18a058;background:none;border:none;cursor:pointer', onClick: () => showDetail(row) }, '查看') },
]

function getSeverityType(s) {
  return { critical: 'error', high: 'warning', medium: 'info', low: 'default' }[s] || 'default'
}

function getStatusType(s) {
  return { open: 'error', in_progress: 'warning', resolved: 'success', closed: 'default' }[s] || 'default'
}

function showDetail(row) {
  currentCase.value = row
  detailDrawer.value = true
}

onMounted(() => { loadData() })

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({ page: pagination.page, page_size: pagination.pageSize })
    if (searchKeyword.value) params.append('keyword', searchKeyword.value)
    if (filterSeverity.value) params.append('severity', filterSeverity.value)
    if (filterStatus.value) params.append('status', filterStatus.value)
    const res = await fetch(`/api/v1/knowledge/fault-case?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    list.value = data.items || []
    pagination.total = data.total || 0
  } catch (e) {
    message.error(`加载失败: ${e.message}`)
    console.error('[knowledge/cases] loadData error:', e)
    list.value = []
  } finally {
    loading.value = false
  }
}

function handlePageChange(page) {
  pagination.page = page
  loadData()
}

function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadData()
}

function handleAdd() {
  message.warning('故障案例创建功能需后端支持故障案例数据模型和 API')
}
</script>
