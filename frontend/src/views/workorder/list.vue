<template>
  <div>
    <div class="page-header">
      <div>
        <h2>工单列表</h2>
        <p class="page-subtitle">查看和管理所有工单</p>
      </div>
      <n-button type="primary" @click="$router.push('/workorder/create')">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        创建工单
      </n-button>
    </div>

    <!-- Stats Summary -->
    <div v-if="workorderStats" class="stats-row">
      <div class="stat-badge" @click="filterStatus = 'pending'">
        <span class="stat-num">{{ workorderStats.pending || 0 }}</span>
        <span class="stat-label">待处理</span>
      </div>
      <div class="stat-badge" @click="filterStatus = 'processing'">
        <span class="stat-num">{{ workorderStats.processing || 0 }}</span>
        <span class="stat-label">处理中</span>
      </div>
      <div class="stat-badge" @click="filterStatus = 'resolved'">
        <span class="stat-num">{{ workorderStats.resolved || 0 }}</span>
        <span class="stat-label">已解决</span>
      </div>
      <div class="stat-badge" @click="filterStatus = 'closed'">
        <span class="stat-num">{{ workorderStats.closed || 0 }}</span>
        <span class="stat-label">已关闭</span>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <n-card :bordered="false" style="margin-bottom:12px">
      <n-space :wrap="true" :size="12" align="center">
        <n-input v-model:value="searchKeyword" placeholder="搜索工单标题" clearable style="width:200px" @keyup.enter="loadData" />
        <n-select v-model:value="filterStatus" placeholder="工单状态" clearable :options="statusOptions" style="width:140px" @update:value="loadData" />
        <n-select v-model:value="filterPriority" placeholder="优先级" clearable :options="priorityOptions" style="width:140px" @update:value="loadData" />
        <n-button type="primary" @click="loadData">搜索</n-button>
        <n-button @click="resetFilters">重置</n-button>
      </n-space>
    </n-card>

    <!-- 工单列表 -->
    <n-card :bordered="false">
      <template #header>
        <span>工单列表 <span class="table-count">共 {{ pagination.itemCount }} 条</span></span>
      </template>
      <n-data-table
        :columns="columns"
        :data="workorderList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
        remote
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </n-card>

    <!-- 查看工单详情弹窗 -->
    <n-modal v-model:show="viewModalVisible" preset="card" title="工单详情" style="width:600px">
      <n-descriptions label-placement="left" :column="1" bordered size="large">
        <n-descriptions-item label="工单号">{{ viewData.order_no || '-' }}</n-descriptions-item>
        <n-descriptions-item label="工单标题">{{ viewData.title || '-' }}</n-descriptions-item>
        <n-descriptions-item label="类型">{{ viewData.type || '-' }}</n-descriptions-item>
        <n-descriptions-item label="优先级">
          <n-tag :type="priorityType(viewData.priority)" size="small">{{ priorityText(viewData.priority) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="statusType(viewData.status)" size="small">{{ statusText(viewData.status) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="描述">{{ viewData.description || '-' }}</n-descriptions-item>
        <n-descriptions-item label="设备">{{ viewData.device || '-' }}</n-descriptions-item>
        <n-descriptions-item label="创建人">{{ viewData.created_by || '-' }}</n-descriptions-item>
        <n-descriptions-item label="处理人">{{ viewData.assignee || '-' }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ viewData.created_at ? viewData.created_at.slice(0, 16) : '-' }}</n-descriptions-item>
        <n-descriptions-item label="更新时间">{{ viewData.updated_at ? viewData.updated_at.slice(0, 16) : '-' }}</n-descriptions-item>
        <n-descriptions-item label="处理备注">{{ viewData.handling_notes || '-' }}</n-descriptions-item>
      </n-descriptions>
      <template #footer>
        <n-space justify="end">
          <n-button @click="viewModalVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑工单弹窗 -->
    <n-modal v-model:show="editModalVisible" preset="card" title="编辑工单" style="width:520px">
      <n-alert v-if="statusTransitionHint" type="info" :show-icon="false" style="margin-bottom:16px">
        {{ statusTransitionHint }}
      </n-alert>
      <n-form label-placement="left" label-width="80">
        <n-form-item label="工单号">
          <span class="form-value">{{ editForm.order_no }}</span>
        </n-form-item>
        <n-form-item label="当前状态">
          <n-tag :type="statusType(editForm.status)" size="small">{{ statusText(editForm.status) }}</n-tag>
        </n-form-item>
        <n-form-item label="新状态">
          <n-select v-model="editForm.status" :options="statusTransitionOptions" placeholder="请选择新状态" />
        </n-form-item>
        <n-form-item label="处理人">
          <n-input v-model="editForm.assignee" placeholder="请输入处理人" />
        </n-form-item>
        <n-form-item label="处理备注">
          <n-input v-model="editForm.handling_notes" type="textarea" :rows="4" placeholder="请输入处理备注" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="editModalVisible = false">取消</n-button>
          <n-button type="primary" @click="submitEdit" :loading="editSubmitting">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, h, onMounted, onUnmounted } from 'vue'
import { useMessage, NTag, NButton, NSpace, NAlert } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { workorder as workorderApi } from '@/api'

const message = useMessage()

const loading = ref(false)
const editSubmitting = ref(false)
const searchKeyword = ref('')
const filterStatus = ref(null)
const filterPriority = ref(null)
const workorderList = ref([])

const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const viewModalVisible = ref(false)
const viewData = ref({})

const editModalVisible = ref(false)
const editForm = reactive({ id: null, order_no: '', status: '', assignee: '', handling_notes: '' })
const statusTransitionOptions = ref([])

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '待审批', value: 'pending_approval' },
  { label: '已批准', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' },
  { label: '已取消', value: 'cancelled' }
]

const priorityOptions = [
  { label: 'P1 - 紧急', value: 'P1' },
  { label: 'P2 - 高', value: 'P2' },
  { label: 'P3 - 中', value: 'P3' },
  { label: 'P4 - 低', value: 'P4' }
]

const workorderStats = computed(() => {
  const stats = { pending: 0, processing: 0, resolved: 0, closed: 0 }
  workorderList.value.forEach(w => {
    if (w.status === 'pending') stats.pending++
    else if (w.status === 'processing') stats.processing++
    else if (w.status === 'resolved') stats.resolved++
    else if (w.status === 'closed') stats.closed++
  })
  return stats
})

// 状态流转提示
const statusTransitionHint = computed(() => {
  if (!editForm.status) return ''
  const flow = ['pending', 'processing', 'pending_approval', 'approved', 'rejected', 'resolved', 'closed']
  const labels = { pending: '待处理', processing: '处理中', pending_approval: '待审批', approved: '已批准', rejected: '已拒绝', resolved: '已解决', closed: '已关闭' }
  const idx = flow.indexOf(editForm.status)
  if (idx === -1 || idx === flow.length - 1) return '当前状态无法流转'
  const nextSteps = flow.slice(idx + 1).map(s => labels[s]).join(' → ')
  return `可流转至：${nextSteps}`
})

const priorityType = (p) => ({ P1: 'error', P2: 'warning', P3: 'info', P4: 'default' })[p] || 'default'
const priorityText = (p) => ({ P1: 'P1-紧急', P2: 'P2-高', P3: 'P3-中', P4: 'P4-低' })[p] || p
const statusType = (s) => ({ pending: 'warning', processing: 'info', pending_approval: 'warning', approved: 'success', rejected: 'error', resolved: 'success', closed: 'default', cancelled: 'default' })[s] || 'default'
const statusText = (s) => ({ pending: '待处理', processing: '处理中', pending_approval: '待审批', approved: '已批准', rejected: '已拒绝', resolved: '已解决', closed: '已关闭', cancelled: '已取消' })[s] || s

const getStatusTransitionOptions = (currentStatus) => {
  const flow = ['pending', 'processing', 'pending_approval', 'approved', 'rejected', 'resolved', 'closed', 'cancelled']
  const currentIndex = flow.indexOf(currentStatus)
  if (currentIndex === -1 || currentIndex === flow.length - 1) return []
  return flow.slice(currentIndex + 1).map(s => ({ label: statusText(s), value: s }))
}

const columns = [
  { title: '工单号', key: 'order_no', width: 180 },
  { title: '工单标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '优先级',
    key: 'priority', width: 100,
    render: (row) => h(NTag, { type: priorityType(row.priority), size: 'small' }, { default: () => priorityText(row.priority) })
  },
  {
    title: '状态', key: 'status', width: 100,
    render: (row) => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusText(row.status) })
  },
  { title: '创建人', key: 'creator', width: 120 },
  { title: '处理人', key: 'assignee', width: 120, render: (row) => row.assignee || '-' },
  { title: '创建时间', key: 'created_at', width: 170, render: (row) => row.created_at ? row.created_at.slice(0, 16) : '-' },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render: (row) => h(NSpace, { size: 8 }, {
      default: () => [
        h(NButton, { size: 'small', type: 'primary', quaternary: true, onClick: () => handleView(row) }, { default: () => '查看' }),
        h(NButton, { size: 'small', type: 'info', quaternary: true, onClick: () => handleEdit(row) }, { default: () => '编辑' }),
        row.status !== 'closed' ? h(NButton, { size: 'small', type: 'warning', quaternary: true, onClick: () => handleClose(row) }, { default: () => '关闭' }) : null
      ].filter(Boolean)
    })
  }
]

async function loadData() {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterPriority.value) params.priority = filterPriority.value

    const res = await workorderApi.getList(params)
    workorderList.value = res.items || res.data?.items || []
    pagination.itemCount = res.total || res.data?.total || 0
  } catch (e) {
    console.error('加载工单列表失败:', e)
    message.error(`加载工单列表失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

function handlePageChange(p) { pagination.page = p; loadData() }
function handlePageSizeChange(ps) { pagination.pageSize = ps; pagination.page = 1; loadData() }

function resetFilters() {
  searchKeyword.value = ''
  filterStatus.value = null
  filterPriority.value = null
  pagination.page = 1
  loadData()
}

async function handleView(row) {
  try {
    const data = await workorderApi.getById(row.id)
    viewData.value = data
    viewModalVisible.value = true
  } catch (e) {
    console.error('获取工单详情失败:', e)
    message.error(`获取工单详情失败: ${e.message}`)
  }
}

function handleEdit(row) {
  editForm.id = row.id
  editForm.order_no = row.order_no || ''
  editForm.status = row.status
  editForm.assignee = row.assignee || ''
  editForm.handling_notes = row.handling_notes || ''
  statusTransitionOptions.value = getStatusTransitionOptions(row.status)
  editModalVisible.value = true
}

async function submitEdit() {
  if (!editForm.id) return
  if (!editForm.status) { message.warning('请选择新状态'); return }
  editSubmitting.value = true
  try {
    await workorderApi.update(editForm.id, {
      status: editForm.status,
      assignee: editForm.assignee
    })
    message.success('工单更新成功')
    editModalVisible.value = false
    loadData()
  } catch (e) {
    console.error('更新工单失败:', e)
    message.error(`更新工单失败: ${e.message}`)
  } finally {
    editSubmitting.value = false
  }
}

async function handleClose(row) {
  try {
    await workorderApi.update(row.id, { status: 'closed' })
    message.success('工单已关闭')
    loadData()
  } catch (e) {
    console.error('关闭工单失败:', e)
    message.error(`关闭工单失败: ${e.message}`)
  }
}

let pollTimer = null

function startPoll() {
  stopPoll()
  pollTimer = setInterval(() => { loadData() }, 30000)
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(() => { loadData(); startPoll() })
onUnmounted(() => { stopPoll() })
</script>

<style scoped>
.page-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 600; }
.page-subtitle { margin: 4px 0 0 0; font-size: 13px; color: #909399; }

.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.stat-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f8f9fa;
  border: 1px solid #eee;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.stat-badge:hover {
  background: #e8f4ff;
  border-color: #adc6ff;
}
.stat-num {
  font-size: 18px;
  font-weight: 700;
  color: #165dff;
}
.stat-label {
  font-size: 13px;
  color: #606266;
}

.table-count {
  font-size: 13px;
  color: #909399;
  font-weight: normal;
  margin-left: 8px;
}

.form-value {
  color: #606266;
  font-size: 14px;
}
</style>
