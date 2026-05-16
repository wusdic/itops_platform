<template>
  <div>
    <div class="page-header">
      <h2>我的工单</h2>
    </div>

    <!-- Toolbar -->
    <n-card :bordered="false" style="margin-bottom:16px">
      <n-space :wrap="true" :size="12" style="margin-bottom:16px">
        <n-input v-model:value="searchForm.keyword" placeholder="搜索工单号/标题" clearable style="width:220px" @keyup.enter="handleSearch">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="searchForm.status" placeholder="状态" clearable :options="statusOptions" style="width:140px" />
        <n-select v-model:value="searchForm.priority" placeholder="优先级" clearable :options="priorityOptions" style="width:140px" />
        <n-button type="primary" @click="handleSearch">
          <template #icon><n-icon><SearchOutline /></n-icon></template>搜索
        </n-button>
        <n-button @click="handleReset">重置</n-button>
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

    <!-- Resolve Modal -->
    <n-modal v-model:show="resolveModalShow" preset="dialog" title="解决工单">
      <n-form style="margin-top:16px">
        <n-form-item label="解决方案">
          <n-input v-model:value="resolveForm.solution" type="textarea" :rows="3" placeholder="请输入解决方案" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="resolveModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleResolveConfirm" :loading="resolveLoading">确认解决</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NTag, NButton, NSpace, NPopconfirm } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import { getWorkorders, resolveWorkorder } from '@/api/workorder'
import dayjs from 'dayjs'

const router = useRouter()
const message = useMessage()

const searchForm = reactive({ keyword: '', status: null, priority: null })

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'in_progress' },
  { label: '已解决', value: 'resolved' },
  { label: '已关闭', value: 'closed' }
]
const priorityOptions = [
  { label: 'P1-紧急', value: 'P1' },
  { label: 'P2-高', value: 'P2' },
  { label: 'P3-中', value: 'P3' },
  { label: 'P4-低', value: 'P4' }
]

const loading = ref(false)
const tableData = ref([])
const pagination = reactive({
  page: 1, pageSize: 10, itemCount: 0,
  showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { pagination.page = p; loadData() },
  onUpdatePageSize: (s) => { pagination.pageSize = s; pagination.page = 1; loadData() }
})

const priorityType = (p) => ({ P1: 'error', P2: 'warning', P3: 'info', P4: 'default' }[p] || 'default')
const statusType = (s) => ({ pending: 'warning', in_progress: 'info', resolved: 'success', closed: 'default', cancelled: 'error' }[s] || 'default')
const statusLabel = (s) => ({ pending: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭', cancelled: '已取消' }[s] || s)

const columns = [
  { title: '工单号', key: 'order_no', width: 140 },
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '优先级', key: 'priority', width: 90,
    render: (row) => h(NTag, { type: priorityType(row.priority), size: 'small' }, { default: () => row.priority || '-' })
  },
  {
    title: '状态', key: 'status', width: 100,
    render: (row) => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusLabel(row.status) })
  },
  { title: '创建人', key: 'creator', width: 100 },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: (row) => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => router.push(`/workorders/${row.id}`) }, { default: () => '详情' }),
        row.status === 'pending'
          ? h(NPopconfirm, { onPositiveClick: () => handleAccept(row) }, {
              trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'success' }, { default: () => '接受' }),
              default: () => '确认接受该工单？'
            })
          : null,
        row.status !== 'resolved' && row.status !== 'closed'
          ? h(NButton, { size: 'small', quaternary: true, type: 'warning', onClick: () => openResolve(row) }, { default: () => '解决' })
          : null
      ].filter(Boolean)
    })
  }
]

const resolveModalShow = ref(false)
const resolveForm = reactive({ solution: '' })
const resolveLoading = ref(false)
const currentRow = ref(null)

function openResolve(row) {
  currentRow.value = row
  resolveForm.solution = ''
  resolveModalShow.value = true
}

async function handleAccept(row) {
  try {
    await resolveWorkorder(row.id, { action: 'accept' })
    message.success('已接受')
    loadData()
  } catch { message.error('操作失败') }
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

async function handleSearch() { pagination.page = 1; loadData() }
function handleReset() { searchForm.keyword = ''; searchForm.status = null; searchForm.priority = null; loadData() }

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

onMounted(loadData)
</script>

<style scoped>
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-header h2 { margin:0; font-size:20px; }
</style>
