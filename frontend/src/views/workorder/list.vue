<template>
  <div>
    <div class="page-header">
      <h2>工单列表</h2>
      <n-button type="primary" @click="$router.push('/workorder/create')">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        创建工单
      </n-button>
    </div>

    <!-- 筛选工具栏 -->
    <n-card :bordered="false" style="margin-bottom:16px">
      <n-space :wrap="true" :size="12">
        <n-input v-model:value="searchKeyword" placeholder="搜索工单标题" clearable style="width:200px" @keyup.enter="loadData" />
        <n-select v-model:value="filterStatus" placeholder="工单状态" clearable :options="statusOptions" style="width:140px" @update:value="loadData" />
        <n-select v-model:value="filterPriority" placeholder="优先级" clearable :options="priorityOptions" style="width:140px" @update:value="loadData" />
        <n-button type="primary" @click="loadData">搜索</n-button>
        <n-button @click="resetFilters">重置</n-button>
      </n-space>
    </n-card>

    <!-- 工单列表 -->
    <n-card :bordered="false">
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

    <!-- 分配弹窗 -->
    <n-modal v-model:show="assignDialogVisible" preset="card" title="分配工单" style="width:500px">
      <n-form label-placement="left" label-width="80">
        <n-form-item label="处理人">
          <n-select v-model="assignForm.handler_id" :options="handlerOptions" placeholder="请选择处理人" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model="assignForm.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="assignDialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitAssign">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, NTag, NButton, NSpace } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/auth'

const message = useMessage()
const authStore = useAuthStore()

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref(null)
const filterPriority = ref(null)
const workorderList = ref([])
const assignDialogVisible = ref(false)
const currentOrder = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })
const assignForm = reactive({ handler_id: null, remark: '' })

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '已关闭', value: 'closed' }
]

const priorityOptions = [
  { label: '紧急', value: 'urgent' },
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' }
]

const handlerOptions = ref([])

const priorityType = (p) => ({ urgent: 'error', high: 'warning', medium: 'info', low: 'default' })[p] || 'default'
const priorityText = (p) => ({ urgent: '紧急', high: '高', medium: '中', low: '低' })[p] || p
const statusType = (s) => ({ pending: 'warning', processing: 'info', completed: 'success', closed: 'default' })[s] || 'default'
const statusText = (s) => ({ pending: '待处理', processing: '处理中', completed: '已完成', closed: '已关闭' })[s] || s

const columns = [
  { title: '工单号', key: 'order_no', width: 180 },
  { title: '工单标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '优先级', key: 'priority', width: 90,
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
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', type: 'info', quaternary: true, onClick: () => handleView(row) }, { default: () => '查看' }),
        row.status === 'pending' ? h(NButton, { size: 'small', type: 'primary', quaternary: true, onClick: () => handleAssign(row) }, { default: () => '分配' }) : null,
        row.status === 'processing' ? h(NButton, { size: 'small', type: 'success', quaternary: true, onClick: () => handleComplete(row) }, { default: () => '完成' }) : null
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

    const res = await fetch(`/api/v1/workorders/?${new URLSearchParams(params)}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    const data = await res.json()
    workorderList.value = data.items || data.data?.items || []
    pagination.itemCount = data.total || data.data?.total || 0
  } catch (e) {
    message.error('加载工单列表失败')
  } finally {
    loading.value = false
  }
}

async function loadHandlers() {
  try {
    const res = await fetch('/api/v1/admin/users', { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } })
    const data = await res.json()
    handlerOptions.value = (data.items || data.data?.items || []).map(u => ({ label: u.full_name || u.username, value: u.id }))
  } catch (e) {}
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

function handleView(row) { message.info('查看工单: ' + row.title) }

function handleAssign(row) {
  currentOrder.value = row
  assignForm.handler_id = null
  assignForm.remark = ''
  assignDialogVisible.value = true
}

async function submitAssign() {
  if (!assignForm.handler_id) { message.warning('请选择处理人'); return }
  try {
    await fetch(`/api/v1/workorders//${currentOrder.value.id}/assign?assignee=${assignForm.handler_id}&comment=${encodeURIComponent(assignForm.remark)}`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    message.success('分配成功')
    assignDialogVisible.value = false
    loadData()
  } catch (e) { message.error('分配失败') }
}

async function handleComplete(row) {
  try {
    await fetch(`/api/v1/workorders//${row.id}/complete`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    message.success('工单已完成')
    loadData()
  } catch (e) { message.error('操作失败') }
}

onMounted(() => { loadData(); loadHandlers() })
</script>

<style scoped>
.page-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 600; }
</style>
