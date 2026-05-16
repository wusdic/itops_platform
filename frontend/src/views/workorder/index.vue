<template>
  <div>
    <div class="page-header">
      <h2>工单列表</h2>
    </div>

    <!-- Stats Cards -->
    <n-grid cols="4 m:2 s:1" responsive="screen" :x-gap="16" :y-gap="16" style="margin-bottom:16px">
      <n-gi v-for="s in statCards" :key="s.label">
        <div class="stat-card">
          <div class="stat-icon" :style="{ background: s.color }">
            <n-icon size="24" color="#fff"><component :is="s.icon" /></n-icon>
          </div>
          <div>
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </n-gi>
    </n-grid>

    <!-- Toolbar -->
    <n-card :bordered="false" style="margin-bottom:16px">
      <n-space :wrap="true" :size="12" style="margin-bottom:16px">
        <n-input v-model:value="searchForm.keyword" placeholder="搜索工单号/标题" clearable style="width:220px" @keyup.enter="handleSearch">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="searchForm.status" placeholder="状态" clearable :options="statusOptions" style="width:140px" />
        <n-select v-model:value="searchForm.priority" placeholder="优先级" clearable :options="priorityOptions" style="width:140px" />
        <n-select v-model:value="searchForm.order_type" placeholder="类型" clearable :options="typeOptions" style="width:140px" />
        <n-button type="primary" @click="handleSearch">
          <template #icon><n-icon><SearchOutline /></n-icon></template>搜索
        </n-button>
        <n-button @click="handleReset">重置</n-button>
        <n-button type="success" @click="router.push('/workorders/create')">
          <template #icon><n-icon><AddOutline /></n-icon></template>创建工单
        </n-button>
        <n-button @click="handleExport" :loading="exporting">
          <template #icon><n-icon><DownloadOutline /></n-icon></template>导出
        </n-button>
      </n-space>
    </n-card>

    <!-- Table -->
    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
        remote
      />
    </n-card>

    <!-- Assign Modal -->
    <n-modal v-model:show="assignModalShow" preset="dialog" title="分配工单">
      <n-form :model="assignForm" style="margin-top:16px">
        <n-form-item label="处理人">
          <n-input v-model:value="assignForm.assignee" placeholder="请输入处理人" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="assignModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleAssignConfirm" :loading="assignLoading">确认</n-button>
      </template>
    </n-modal>

    <!-- Approve Modal -->
    <n-modal v-model:show="approveModalShow" preset="dialog" title="审批工单">
      <n-form :model="approveForm" style="margin-top:16px">
        <n-form-item label="审批意见">
          <n-input v-model:value="approveForm.comment" type="textarea" placeholder="请输入审批意见" :rows="3" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="approveModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleApproveConfirm" :loading="approveLoading">通过</n-button>
      </template>
    </n-modal>

    <!-- Resolve Modal -->
    <n-modal v-model:show="resolveModalShow" preset="dialog" title="解决工单">
      <n-form :model="resolveForm" style="margin-top:16px">
        <n-form-item label="解决方案">
          <n-input v-model:value="resolveForm.solution" type="textarea" placeholder="请输入解决方案" :rows="3" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="resolveModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleResolveConfirm" :loading="resolveLoading">确认解决</n-button>
      </template>
    </n-modal>

    <!-- Close Modal -->
    <n-modal v-model:show="closeModalShow" preset="dialog" title="关闭工单">
      <n-form :model="closeForm" style="margin-top:16px">
        <n-form-item label="关闭原因">
          <n-input v-model:value="closeForm.reason" type="textarea" placeholder="请输入关闭原因" :rows="3" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="closeModalShow = false">取消</n-button>
        <n-button type="warning" @click="handleCloseConfirm" :loading="closeLoading">确认关闭</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog, NTag, NButton, NSpace, NPopconfirm } from 'naive-ui'
import {
  SearchOutline, AddOutline, DownloadOutline,
  TicketOutline, HourglassOutline, CheckmarkDoneOutline, ListOutline
} from '@vicons/ionicons5'
import {
  getWorkorders, getWoStats, assignWorkorder, approveWorkorder,
  resolveWorkorder, closeWorkorder, cancelWorkorder, exportWorkorders
} from '@/api/workorder'
import dayjs from 'dayjs'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

// Stats
const statCards = ref([
  { label: '待处理', value: 0, icon: HourglassOutline, color: '#f0a020' },
  { label: '处理中', value: 0, icon: TicketOutline, color: '#2080f0' },
  { label: '已完成', value: 0, icon: CheckmarkDoneOutline, color: '#18a058' },
  { label: '总计', value: 0, icon: ListOutline, color: '#646cfe' }
])

// Search
const searchForm = reactive({ keyword: '', status: null, priority: null, order_type: null })

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'in_progress' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' },
  { label: '已取消', value: 'cancelled' }
]
const priorityOptions = [
  { label: 'P1-紧急', value: 'P1' },
  { label: 'P2-高', value: 'P2' },
  { label: 'P3-中', value: 'P3' },
  { label: 'P4-低', value: 'P4' }
]
const typeOptions = [
  { label: '故障', value: 'incident' },
  { label: '服务请求', value: 'service_request' },
  { label: '变更', value: 'change' },
  { label: '问题', value: 'problem' }
]

// Table
const loading = ref(false)
const tableData = ref([])
const pagination = reactive({
  page: 1, pageSize: 10, itemCount: 0,
  showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { pagination.page = p; loadData() },
  onUpdatePageSize: (s) => { pagination.pageSize = s; pagination.page = 1; loadData() }
})

const priorityColor = (p) => ({ P1: '#d03050', P2: '#f0a020', P3: '#2080f0', P4: '#999' }[p] || '#999')
const priorityType = (p) => ({ P1: 'error', P2: 'warning', P3: 'info', P4: 'default' }[p] || 'default')
const statusType = (s) => ({ pending: 'warning', in_progress: 'info', resolved: 'success', closed: 'default', cancelled: 'error' }[s] || 'default')
const statusLabel = (s) => ({ pending: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭', cancelled: '已取消' }[s] || s)
const typeLabel = (t) => ({ incident: '故障', service_request: '服务请求', change: '变更', problem: '问题' }[t] || t)

const columns = [
  { title: '工单号', key: 'order_no', width: 140 },
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '优先级', key: 'priority', width: 90,
    render: (row) => h(NTag, { type: priorityType(row.priority), size: 'small' }, { default: () => row.priority || '-' })
  },
  {
    title: '类型', key: 'order_type', width: 100,
    render: (row) => typeLabel(row.order_type)
  },
  {
    title: '状态', key: 'status', width: 100,
    render: (row) => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusLabel(row.status) })
  },
  { title: '创建人', key: 'creator', width: 100 },
  { title: '处理人', key: 'assignee', width: 100 },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: (row) => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 280, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => router.push(`/workorders/${row.id}`) }, { default: () => '详情' }),
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openAssign(row) }, { default: () => '分配' }),
        h(NButton, { size: 'small', quaternary: true, type: 'success', onClick: () => openApprove(row) }, { default: () => '审批' }),
        h(NButton, { size: 'small', quaternary: true, type: 'warning', onClick: () => openResolve(row) }, { default: () => '解决' }),
        h(NPopconfirm, { onPositiveClick: () => handleAction(closeWorkorder, row.id, { reason: '手动关闭' }, '已关闭') }, {
          trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'default' }, { default: () => '关闭' }),
          default: () => '确认关闭该工单？'
        }),
        h(NPopconfirm, { onPositiveClick: () => handleAction(cancelWorkorder, row.id, { reason: '手动取消' }, '已取消') }, {
          trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '取消' }),
          default: () => '确认取消该工单？'
        })
      ]
    })
  }
]

// Modals
const assignModalShow = ref(false)
const assignForm = reactive({ assignee: '' })
const assignLoading = ref(false)
const currentRow = ref(null)

const approveModalShow = ref(false)
const approveForm = reactive({ comment: '' })
const approveLoading = ref(false)

const resolveModalShow = ref(false)
const resolveForm = reactive({ solution: '' })
const resolveLoading = ref(false)

const closeModalShow = ref(false)
const closeForm = reactive({ reason: '' })
const closeLoading = ref(false)

const exporting = ref(false)

function openAssign(row) {
  currentRow.value = row
  assignForm.assignee = ''
  assignModalShow.value = true
}
function openApprove(row) {
  currentRow.value = row
  approveForm.comment = ''
  approveModalShow.value = true
}
function openResolve(row) {
  currentRow.value = row
  resolveForm.solution = ''
  resolveModalShow.value = true
}

async function handleAction(fn, id, data, successMsg) {
  try {
    await fn(id, data)
    message.success(successMsg)
    loadData()
  } catch (e) {
    message.error('操作失败')
  }
}

async function handleAssignConfirm() {
  if (!currentRow.value || !assignForm.assignee) { message.warning('请输入处理人'); return }
  assignLoading.value = true
  try {
    await assignWorkorder(currentRow.value.id, { assignee: assignForm.assignee })
    message.success('分配成功')
    assignModalShow.value = false
    loadData()
  } catch { message.error('分配失败') } finally { assignLoading.value = false }
}

async function handleApproveConfirm() {
  if (!currentRow.value) return
  approveLoading.value = true
  try {
    await approveWorkorder(currentRow.value.id, { comment: approveForm.comment })
    message.success('审批通过')
    approveModalShow.value = false
    loadData()
  } catch { message.error('审批失败') } finally { approveLoading.value = false }
}

async function handleResolveConfirm() {
  if (!currentRow.value || !resolveForm.solution) { message.warning('请输入解决方案'); return }
  resolveLoading.value = true
  try {
    await resolveWorkorder(currentRow.value.id, { solution: resolveForm.solution })
    message.success('已解决')
    resolveModalShow.value = false
    loadData()
  } catch { message.error('操作失败') } finally { resolveLoading.value = false }
}

async function handleCloseConfirm() {
  if (!currentRow.value || !closeForm.reason) { message.warning('请输入关闭原因'); return }
  closeLoading.value = true
  try {
    await closeWorkorder(currentRow.value.id, { reason: closeForm.reason })
    message.success('已关闭')
    closeModalShow.value = false
    loadData()
  } catch { message.error('操作失败') } finally { closeLoading.value = false }
}

async function handleSearch() { pagination.page = 1; loadData() }
function handleReset() {
  searchForm.keyword = ''
  searchForm.status = null
  searchForm.priority = null
  searchForm.order_type = null
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize, ...searchForm }
    const res = await getWorkorders(params)
    tableData.value = res.data?.items || res.data || []
    pagination.itemCount = res.data?.total || 0
  } catch (e) {
    message.error('加载工单列表失败')
  } finally { loading.value = false }
}

async function loadStats() {
  try {
    const res = await getWoStats()
    const d = res.data || {}
    statCards.value[0].value = d.pending || 0
    statCards.value[1].value = d.in_progress || 0
    statCards.value[2].value = d.resolved || d.completed || 0
    statCards.value[3].value = d.total || 0
  } catch {}
}

async function handleExport() {
  exporting.value = true
  try {
    const res = await exportWorkorders(searchForm)
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `工单列表_${dayjs().format('YYYYMMDDHHmmss')}.xlsx`
    a.click(); URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch { message.error('导出失败') } finally { exporting.value = false }
}

onMounted(() => { loadData(); loadStats() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 20px; }
.stat-card { display:flex; align-items:center; gap:16px; padding:20px; background:#fff; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
.stat-icon { width:48px; height:48px; border-radius:12px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.stat-value { font-size:26px; font-weight:700; color:#1a1a1a; }
.stat-label { font-size:13px; color:#999; margin-top:2px; }
</style>
