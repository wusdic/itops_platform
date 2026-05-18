<template>
  <div class="page-container">
    <n-card title="我的工单" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="$router.push('/workorder/create')">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          创建工单
        </n-button>
      </template>

      <n-space style="margin-bottom: 12px">
        <n-input v-model:value="searchKeyword" placeholder="搜索工单标题" clearable style="width: 200px" @change="loadData">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="工单状态" clearable style="width: 120px" @change="loadData" />
        <n-select v-model:value="filterPriority" :options="priorityOptions" placeholder="优先级" clearable style="width: 120px" @change="loadData" />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="workorderList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 分配工单 -->
    <n-modal v-model:show="assignDialogVisible" preset="card" title="分配工单" style="width: 500px">
      <n-form :model="assignForm" label-placement="left" label-width="80">
        <n-form-item label="处理人">
          <n-select v-model:value="assignForm.handler_id" :options="handlerOptions" placeholder="请选择处理人" style="width: 100%" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="assignForm.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="assignDialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitAssign">确定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 工单详情 -->
    <n-modal v-model:show="viewModalVisible" preset="card" title="工单详情" style="width:600px">
      <n-descriptions v-if="viewData" :column="2" bordered size="small">
        <n-descriptions-item label="工单ID">{{ viewData.id }}</n-descriptions-item>
        <n-descriptions-item label="工单号">{{ viewData.order_no || '-' }}</n-descriptions-item>
        <n-descriptions-item label="标题">{{ viewData.title }}</n-descriptions-item>
        <n-descriptions-item label="类型">{{ viewData.type || '-' }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag size="small" :type="getStatusType(viewData.status)">{{ getStatusText(viewData.status) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="优先级">
          <n-tag size="small" :type="getPriorityType(viewData.priority)">{{ getPriorityText(viewData.priority) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="创建人">{{ viewData.creator_name || viewData.creator || '-' }}</n-descriptions-item>
        <n-descriptions-item label="处理人">{{ viewData.assignee_name || viewData.assignee || '-' }}</n-descriptions-item>
        <n-descriptions-item label="描述" :span="2">{{ viewData.description || '-' }}</n-descriptions-item>
        <n-descriptions-item label="处理备注" :span="2">{{ viewData.handling_notes || '-' }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ viewData.created_at || '-' }}</n-descriptions-item>
        <n-descriptions-item label="更新时间">{{ viewData.updated_at || '-' }}</n-descriptions-item>
      </n-descriptions>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NButton, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NSpace, NTag, NIcon, NDescriptions, NDescriptionsItem, useMessage } from 'naive-ui'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'
import { workorder as workorderApi } from '@/api'

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const workorderList = ref([])
const searchKeyword = ref('')
const filterStatus = ref(null)
const filterPriority = ref(null)
const assignDialogVisible = ref(false)
const viewModalVisible = ref(false)
const viewData = ref(null)
const currentOrder = ref(null)
const handlerOptions = ref([])

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const assignForm = reactive({ handler_id: null, remark: '' })

const statusOptions = [
  { label: '全部', value: null },
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' }
]

const priorityOptions = [
  { label: '全部', value: null },
  { label: 'P1', value: 'P1' },
  { label: 'P2', value: 'P2' },
  { label: 'P3', value: 'P3' },
  { label: 'P4', value: 'P4' }
]

const getPriorityType = (p) => ({ P1: 'error', P2: 'warning', P3: 'info', P4: 'default' }[p] || 'default')
const getPriorityText = (p) => ({ P1: 'P1', P2: 'P2', P3: 'P3', P4: 'P4' }[p] || p)
const getStatusType = (s) => ({ pending: 'warning', processing: 'info', resolved: 'success', closed: 'default' }[s] || 'default')
const getStatusText = (s) => ({ pending: '待处理', processing: '处理中', resolved: '已解决', closed: '已关闭' }[s] || s)

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '工单标题', key: 'title', ellipsis: { tooltip: true } },
  { title: '优先级', key: 'priority', width: 90,
    render: (r) => h(NTag, { size: 'small', type: getPriorityType(r.priority) }, () => getPriorityText(r.priority))
  },
  { title: '状态', key: 'status', width: 100,
    render: (r) => h(NTag, { size: 'small', type: getStatusType(r.status) }, () => getStatusText(r.status))
  },
  { title: '处理人', key: 'assignee_name', width: 120 },
  { title: '创建时间', key: 'created_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 120, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => handleView(row) }, () => '查看')
      ])
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({ page: pagination.page, page_size: pagination.pageSize })
    if (filterStatus.value) params.append('status', filterStatus.value)
    if (filterPriority.value) params.append('priority', filterPriority.value)
    if (searchKeyword.value) params.append('search', searchKeyword.value)
    const res = await fetch(`/api/v1/workorders/?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    workorderList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载工单失败: ${e.message}`)
    console.error('[workorder/my] loadData error:', e)
    workorderList.value = []
  } finally {
    loading.value = false
  }
}

async function loadHandlers() {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/admin/users?page=1&page_size=50', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error()
    const data = await res.json()
    handlerOptions.value = (data.items || []).map(u => ({ label: u.username, value: u.id }))
  } catch {
    handlerOptions.value = []
  }
}

function handleView(row) {
  viewData.value = row
  viewModalVisible.value = true
}

async function handleViewAsync(row) {
  try {
    const res = await fetch(`/api/v1/workorders/${row.id}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    viewData.value = await res.json()
    viewModalVisible.value = true
  } catch (e) {
    message.error(`获取工单详情失败: ${e.message}`)
  }
}

async function submitAssign() {
  if (!assignForm.handler_id) { message.warning('请选择处理人'); return }
  try {
    // 调用前需将 handler_id 转为 username（这里 handler_id 是用户ID，需查表或传 username）
    // 后端 /assign 接口接收 assignee (username)
    const handler = handlerOptions.value.find(h => h.value === assignForm.handler_id)
    if (!handler) { message.warning('请选择处理人'); return }
    await workorderApi.assign(currentOrder.value.id, {
      assignee: handler.label,
      comment: assignForm.remark
    })
    message.success('分配成功')
    assignDialogVisible.value = false
    loadData()
  } catch (e) {
    message.error(`分配失败: ${e.message}`)
    console.error('[workorder/my] assign error:', e)
  }
}

onMounted(() => { loadData(); loadHandlers() })
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
