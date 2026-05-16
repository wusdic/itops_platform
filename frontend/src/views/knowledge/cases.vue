<template>
  <div>
    <div class="page-header">
      <h2>故障案例</h2>
      <n-button type="primary" @click="openCreate">
        <template #icon><n-icon><AddOutline /></n-icon></template>创建案例
      </n-button>
    </div>

    <!-- Toolbar -->
    <n-card :bordered="false" style="margin-bottom:16px">
      <n-space :wrap="true" :size="12" style="margin-bottom:16px">
        <n-input v-model:value="searchForm.keyword" placeholder="搜索标题/现象/根因" clearable style="width:220px" @keyup.enter="handleSearch">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="searchForm.level" placeholder="级别" clearable :options="levelOptions" style="width:140px" />
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

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="editModalShow" preset="card" :title="isEdit ? '编辑故障案例' : '创建故障案例'" style="max-width:800px">
      <n-form ref="editFormRef" :model="editForm" :rules="editRules" label-placement="left" label-width="80">
        <n-form-item label="标题" path="title">
          <n-input v-model:value="editForm.title" placeholder="请输入案例标题" />
        </n-form-item>
        <n-form-item label="现象" path="symptom">
          <n-input v-model:value="editForm.symptom" type="textarea" placeholder="请描述故障现象" :rows="4" />
        </n-form-item>
        <n-form-item label="根因" path="root_cause">
          <n-input v-model:value="editForm.root_cause" type="textarea" placeholder="请分析根本原因" :rows="4" />
        </n-form-item>
        <n-form-item label="解决方案" path="solution">
          <n-input v-model:value="editForm.solution" type="textarea" placeholder="请输入解决方案" :rows="4" />
        </n-form-item>
        <n-form-item label="级别" path="level">
          <n-select v-model:value="editForm.level" placeholder="请选择级别" :options="levelOptions" />
        </n-form-item>
        <n-form-item label="标签">
          <n-select v-model:value="editForm.tags" placeholder="请选择标签" :options="tagOptions" multiple clearable />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="editModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleSave" :loading="saveLoading">保存</n-button>
      </template>
    </n-modal>

    <!-- Detail Modal -->
    <n-modal v-model:show="detailModalShow" preset="card" title="案例详情" style="max-width:800px">
      <n-descriptions :column="2" bordered v-if="detailData">
        <n-descriptions-item label="标题" :span="2">{{ detailData.title }}</n-descriptions-item>
        <n-descriptions-item label="级别">
          <n-tag :type="levelType(detailData.level)" size="small">{{ detailData.level || '-' }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="创建人">{{ detailData.creator || '-' }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ formatDate(detailData.created_at) }}</n-descriptions-item>
        <n-descriptions-item label="标签" :span="2">{{ (detailData.tags || []).join(', ') || '-' }}</n-descriptions-item>
        <n-descriptions-item label="现象" :span="2">
          <pre style="white-space:pre-wrap">{{ detailData.symptom || '-' }}</pre>
        </n-descriptions-item>
        <n-descriptions-item label="根因" :span="2">
          <pre style="white-space:pre-wrap">{{ detailData.root_cause || '-' }}</pre>
        </n-descriptions-item>
        <n-descriptions-item label="解决方案" :span="2">
          <pre style="white-space:pre-wrap">{{ detailData.solution || '-' }}</pre>
        </n-descriptions-item>
      </n-descriptions>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, NTag, NButton, NSpace, NPopconfirm } from 'naive-ui'
import { SearchOutline, AddOutline, EyeOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5'
import {
  getFaultCases, createFaultCase, getFaultCase, updateFaultCase, getTags
} from '@/api/knowledge'
import dayjs from 'dayjs'

const message = useMessage()

const searchForm = reactive({ keyword: '', level: null })
const tagOptions = ref([])
const levelOptions = [
  { label: 'P1-严重', value: 'P1' },
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

const levelType = (l) => ({ P1: 'error', P2: 'warning', P3: 'info', P4: 'default' }[l] || 'default')
const formatDate = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-'

const columns = [
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '级别', key: 'level', width: 90,
    render: (row) => h(NTag, { type: levelType(row.level), size: 'small' }, { default: () => row.level || '-' })
  },
  {
    title: '现象', key: 'symptom', ellipsis: { tooltip: true },
    render: (row) => (row.symptom || '').substring(0, 50) + ((row.symptom || '').length > 50 ? '...' : '')
  },
  { title: '创建人', key: 'creator', width: 100 },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: (row) => formatDate(row.created_at)
  },
  {
    title: '操作', key: 'actions', width: 180, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => openDetail(row) }, { default: () => '详情' }),
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(row) }, { default: () => '编辑' }),
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row) }, {
          trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '删除' }),
          default: () => '确认删除该案例？'
        })
      ]
    })
  }
]

// Edit
const editModalShow = ref(false)
const isEdit = ref(false)
const editFormRef = ref(null)
const editForm = reactive({ id: null, title: '', symptom: '', root_cause: '', solution: '', level: null, tags: [] })
const editRules = {
  title: { required: true, message: '请输入标题', trigger: 'blur' },
  symptom: { required: true, message: '请输入故障现象', trigger: 'blur' },
  root_cause: { required: true, message: '请输入根因', trigger: 'blur' },
  solution: { required: true, message: '请输入解决方案', trigger: 'blur' }
}
const saveLoading = ref(false)

const detailModalShow = ref(false)
const detailData = ref(null)

function openCreate() {
  isEdit.value = false
  Object.assign(editForm, { id: null, title: '', symptom: '', root_cause: '', solution: '', level: null, tags: [] })
  editModalShow.value = true
}

function openEdit(row) {
  isEdit.value = true
  Object.assign(editForm, { id: row.id, title: row.title, symptom: row.symptom, root_cause: row.root_cause, solution: row.solution, level: row.level, tags: row.tags || [] })
  editModalShow.value = true
}

function openDetail(row) {
  detailData.value = row
  detailModalShow.value = true
}

async function handleSave() {
  try { await editFormRef.value?.validate() } catch { return }
  saveLoading.value = true
  try {
    if (isEdit.value) {
      await updateFaultCase(editForm.id, editForm)
      message.success('更新成功')
    } else {
      await createFaultCase(editForm)
      message.success('创建成功')
    }
    editModalShow.value = false
    loadData()
  } catch { message.error(isEdit.value ? '更新失败' : '创建失败') } finally { saveLoading.value = false }
}

async function handleDelete(row) {
  try {
    // Use updateFaultCase with a delete flag or direct API
    message.info('删除功能需要后端支持')
  } catch { message.error('删除失败') }
}

async function handleSearch() { pagination.page = 1; loadData() }
function handleReset() { searchForm.keyword = ''; searchForm.level = null; loadData() }

async function loadData() {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize, ...searchForm }
    const res = await getFaultCases(params)
    tableData.value = res.data?.items || res.data || []
    pagination.itemCount = res.data?.total || 0
  } catch { message.error('加载案例列表失败') } finally { loading.value = false }
}

async function loadTags() {
  try {
    const res = await getTags()
    const items = res.data?.items || res.data || []
    tagOptions.value = Array.isArray(items) ? items.map(i => ({ label: i.name || i, value: i.name || i.id || i })) : []
  } catch {}
}

onMounted(() => { loadData(); loadTags() })
</script>

<style scoped>
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-header h2 { margin:0; font-size:20px; }
</style>
