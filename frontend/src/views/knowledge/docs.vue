<template>
  <div>
    <div class="page-header">
      <h2>SOP文档</h2>
      <n-button type="primary" @click="openCreate">
        <template #icon><n-icon><AddOutline /></n-icon></template>创建文档
      </n-button>
    </div>

    <!-- Toolbar -->
    <n-card :bordered="false" style="margin-bottom:16px">
      <n-space :wrap="true" :size="12" style="margin-bottom:16px">
        <n-input v-model:value="searchForm.keyword" placeholder="搜索标题/内容" clearable style="width:220px" @keyup.enter="handleSearch">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="searchForm.category" placeholder="分类" clearable :options="categoryOptions" style="width:140px" />
        <n-select v-model:value="searchForm.status" placeholder="状态" clearable :options="statusOptions" style="width:140px" />
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
    <n-modal v-model:show="editModalShow" preset="card" :title="isEdit ? '编辑SOP文档' : '创建SOP文档'" style="max-width:800px">
      <n-form ref="editFormRef" :model="editForm" :rules="editRules" label-placement="left" label-width="80">
        <n-form-item label="标题" path="title">
          <n-input v-model:value="editForm.title" placeholder="请输入标题" />
        </n-form-item>
        <n-form-item label="内容" path="content">
          <n-input v-model:value="editForm.content" type="textarea" placeholder="请输入文档内容" :rows="8" />
        </n-form-item>
        <n-form-item label="分类" path="category_id">
          <n-select v-model:value="editForm.category_id" placeholder="请选择分类" :options="categoryOptions" clearable />
        </n-form-item>
        <n-form-item label="标签">
          <n-select v-model:value="editForm.tags" placeholder="请选择标签" :options="tagOptions" multiple clearable />
        </n-form-item>
        <n-form-item label="版本">
          <n-input v-model:value="editForm.version" placeholder="如 v1.0" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="editModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleSave" :loading="saveLoading">保存</n-button>
      </template>
    </n-modal>

    <!-- Detail Modal -->
    <n-modal v-model:show="detailModalShow" preset="card" title="SOP文档详情" style="max-width:800px">
      <n-descriptions :column="2" bordered v-if="detailData">
        <n-descriptions-item label="标题">{{ detailData.title }}</n-descriptions-item>
        <n-descriptions-item label="版本">{{ detailData.version || '-' }}</n-descriptions-item>
        <n-descriptions-item label="分类">{{ detailData.category_name || '-' }}</n-descriptions-item>
        <n-descriptions-item label="状态">{{ statusLabel(detailData.status) }}</n-descriptions-item>
        <n-descriptions-item label="创建人">{{ detailData.creator || '-' }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ formatDate(detailData.created_at) }}</n-descriptions-item>
        <n-descriptions-item label="标签" :span="2">{{ (detailData.tags || []).join(', ') || '-' }}</n-descriptions-item>
        <n-descriptions-item label="内容" :span="2">
          <pre style="white-space:pre-wrap;max-height:400px;overflow-y:auto">{{ detailData.content || '-' }}</pre>
        </n-descriptions-item>
      </n-descriptions>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, useDialog, NTag, NButton, NSpace, NPopconfirm } from 'naive-ui'
import { SearchOutline, AddOutline, EyeOutline, CreateOutline, TrashOutline, SendOutline, CheckmarkOutline } from '@vicons/ionicons5'
import {
  getSopList, createSop, getSop, updateSop, deleteSop,
  submitSopReview, approveSop, getCategories, getTags
} from '@/api/knowledge'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const searchForm = reactive({ keyword: '', category: null, status: null })
const categoryOptions = ref([])
const tagOptions = ref([])
const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '审核中', value: 'reviewing' },
  { label: '已发布', value: 'published' },
  { label: '已归档', value: 'archived' }
]

const loading = ref(false)
const tableData = ref([])
const pagination = reactive({
  page: 1, pageSize: 10, itemCount: 0,
  showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { pagination.page = p; loadData() },
  onUpdatePageSize: (s) => { pagination.pageSize = s; pagination.page = 1; loadData() }
})

const statusLabel = (s) => ({ draft: '草稿', reviewing: '审核中', published: '已发布', archived: '已归档' }[s] || s)
const statusType = (s) => ({ draft: 'default', reviewing: 'warning', published: 'success', archived: 'info' }[s] || 'default')
const formatDate = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-'

const columns = [
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  { title: '版本', key: 'version', width: 80 },
  {
    title: '分类', key: 'category_name', width: 120,
    render: (row) => row.category_name || '-'
  },
  {
    title: '状态', key: 'status', width: 90,
    render: (row) => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusLabel(row.status) })
  },
  { title: '创建人', key: 'creator', width: 100 },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: (row) => formatDate(row.created_at)
  },
  {
    title: '操作', key: 'actions', width: 240, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => openDetail(row) }, { default: () => '详情' }),
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(row) }, { default: () => '编辑' }),
        row.status === 'draft'
          ? h(NButton, { size: 'small', quaternary: true, type: 'success', onClick: () => handleSubmitReview(row) }, { default: () => '提交审核' })
          : null,
        row.status === 'reviewing'
          ? h(NButton, { size: 'small', quaternary: true, type: 'warning', onClick: () => handleApprove(row) }, { default: () => '批准' })
          : null,
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row) }, {
          trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '删除' }),
          default: () => '确认删除该文档？'
        })
      ].filter(Boolean)
    })
  }
]

// Edit
const editModalShow = ref(false)
const isEdit = ref(false)
const editFormRef = ref(null)
const editForm = reactive({ id: null, title: '', content: '', category_id: null, tags: [], version: '' })
const editRules = {
  title: { required: true, message: '请输入标题', trigger: 'blur' },
  content: { required: true, message: '请输入内容', trigger: 'blur' }
}
const saveLoading = ref(false)

const detailModalShow = ref(false)
const detailData = ref(null)

function openCreate() {
  isEdit.value = false
  Object.assign(editForm, { id: null, title: '', content: '', category_id: null, tags: [], version: 'v1.0' })
  editModalShow.value = true
}

function openEdit(row) {
  isEdit.value = true
  Object.assign(editForm, { id: row.id, title: row.title, content: row.content, category_id: row.category_id, tags: row.tags || [], version: row.version || '' })
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
      await updateSop(editForm.id, editForm)
      message.success('更新成功')
    } else {
      await createSop(editForm)
      message.success('创建成功')
    }
    editModalShow.value = false
    loadData()
  } catch { message.error(isEdit.value ? '更新失败' : '创建失败') } finally { saveLoading.value = false }
}

async function handleDelete(row) {
  try {
    await deleteSop(row.id)
    message.success('已删除')
    loadData()
  } catch { message.error('删除失败') }
}

async function handleSubmitReview(row) {
  try {
    await submitSopReview(row.id, {})
    message.success('已提交审核')
    loadData()
  } catch { message.error('提交审核失败') }
}

async function handleApprove(row) {
  try {
    await approveSop(row.id)
    message.success('已批准')
    loadData()
  } catch { message.error('批准失败') }
}

async function handleSearch() { pagination.page = 1; loadData() }
function handleReset() { searchForm.keyword = ''; searchForm.category = null; searchForm.status = null; loadData() }

async function loadData() {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize, ...searchForm }
    const res = await getSopList(params)
    tableData.value = res.data?.items || res.data || []
    pagination.itemCount = res.data?.total || 0
  } catch { message.error('加载SOP列表失败') } finally { loading.value = false }
}

async function loadOptions() {
  try {
    const [catRes, tagRes] = await Promise.allSettled([getCategories(), getTags()])
    if (catRes.status === 'fulfilled') {
      const items = catRes.value.data?.items || catRes.value.data || []
      categoryOptions.value = Array.isArray(items) ? items.map(i => ({ label: i.name || i, value: i.id || i })) : []
    }
    if (tagRes.status === 'fulfilled') {
      const items = tagRes.value.data?.items || tagRes.value.data || []
      tagOptions.value = Array.isArray(items) ? items.map(i => ({ label: i.name || i, value: i.name || i.id || i })) : []
    }
  } catch {}
}

onMounted(() => { loadData(); loadOptions() })
</script>

<style scoped>
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-header h2 { margin:0; font-size:20px; }
</style>
