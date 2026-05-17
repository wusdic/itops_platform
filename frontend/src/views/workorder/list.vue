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
    <n-modal v-model:show="editModalVisible" preset="card" title="编辑工单" style="width:500px">
      <n-form label-placement="left" label-width="80">
        <n-form-item label="工单号">
          <span>{{ editForm.order_no }}</span>
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
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, NTag, NButton, NSpace } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'

const message = useMessage()

const loading = ref(false)
const editSubmitting = ref(false)
const searchKeyword = ref('')
const filterStatus = ref(null)
const filterPriority = ref(null)
const workorderList = ref([])

const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

// 查看弹窗
const viewModalVisible = ref(false)
const viewData = ref({})

// 编辑弹窗
const editModalVisible = ref(false)
const editForm = reactive({ id: null, order_no: '', status: '', assignee: '', handling_notes: '' })
const statusTransitionOptions = ref([])

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'open' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' }
]

const priorityOptions = [
  { label: 'P1', value: 'P1' },
  { label: 'P2', value: 'P2' },
  { label: 'P3', value: 'P3' },
  { label: 'P4', value: 'P4' }
]

const priorityType = (p) => ({ P1: 'error', P2: 'warning', P3: 'info', P4: 'default' })[p] || 'default'
const priorityText = (p) => ({ P1: 'P1', P2: 'P2', P3: 'P3', P4: 'P4' })[p] || p
const statusType = (s) => ({ pending: 'warning', open: 'info', resolved: 'success', closed: 'default' })[s] || 'default'
const statusText = (s) => ({ pending: '待处理', open: '处理中', resolved: '已解决', closed: '已关闭' })[s] || s

// 状态流转选项：pending→open→resolved→closed
const getStatusTransitionOptions = (currentStatus) => {
  const flow = ['pending', 'open', 'resolved', 'closed']
  const currentIndex = flow.indexOf(currentStatus)
  if (currentIndex === -1 || currentIndex === flow.length - 1) return []
  return flow.slice(currentIndex + 1).map(s => ({ label: statusText(s), value: s }))
}

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
    title: '操作', key: 'actions', width: 220, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', type: 'info', quaternary: true, onClick: () => handleView(row) }, { default: () => '查看' }),
        h(NButton, { size: 'small', type: 'primary', quaternary: true, onClick: () => handleEdit(row) }, { default: () => '编辑' }),
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

    const res = await fetch(`/api/v1/workorders/?${new URLSearchParams(params)}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    workorderList.value = data.items || data.data?.items || []
    pagination.itemCount = data.total || data.data?.total || 0
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

// 查看工单
async function handleView(row) {
  try {
    const res = await fetch(`/api/v1/workorders/${row.id}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    viewData.value = data
    viewModalVisible.value = true
  } catch (e) {
    console.error('获取工单详情失败:', e)
    message.error(`获取工单详情失败: ${e.message}`)
  }
}

// 编辑工单
function handleEdit(row) {
  editForm.id = row.id
  editForm.order_no = row.order_no || ''
  editForm.status = row.status
  editForm.assignee = row.assignee || ''
  editForm.handling_notes = row.handling_notes || ''
  statusTransitionOptions.value = getStatusTransitionOptions(row.status)
  editModalVisible.value = true
}

// 提交编辑
async function submitEdit() {
  if (!editForm.id) return
  if (!editForm.status) {
    message.warning('请选择新状态')
    return
  }
  editSubmitting.value = true
  try {
    const token = localStorage.getItem('token') || ''
    // 先尝试 PUT /api/v1/workorders/{id}/status
    let res = await fetch(`/api/v1/workorders/${editForm.id}/status`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        status: editForm.status,
        handling_notes: editForm.handling_notes,
        assignee: editForm.assignee
      })
    })
    
    // 如果 status 端点不存在（404），则使用 PATCH /api/v1/workorders/{id}
    if (res.status === 404) {
      res = await fetch(`/api/v1/workorders/${editForm.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          status: editForm.status,
          handling_notes: editForm.handling_notes,
          assignee: editForm.assignee
        })
      })
    }
    
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
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

// 关闭工单
async function handleClose(row) {
  try {
    const token = localStorage.getItem('token') || ''
    // 先尝试 PUT /api/v1/workorders/{id}/status 关闭
    let res = await fetch(`/api/v1/workorders/${row.id}/status`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ status: 'closed', handling_notes: '关闭工单' })
    })
    
    // 如果 404，尝试 PATCH /api/v1/workorders/{id}/close
    if (res.status === 404) {
      res = await fetch(`/api/v1/workorders/${row.id}/close`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` }
      })
    }
    
    // 如果还是 404，尝试 PATCH 主资源
    if (res.status === 404) {
      res = await fetch(`/api/v1/workorders/${row.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ status: 'closed' })
      })
    }
    
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success('工单已关闭')
    loadData()
  } catch (e) {
    console.error('关闭工单失败:', e)
    message.error(`关闭工单失败: ${e.message}`)
  }
}

onMounted(() => { loadData() })
</script>

<style scoped>
.page-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 600; }
</style>
