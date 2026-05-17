<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">知识文档</h1>
        <p class="page-subtitle">运维知识库管理</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="handleAdd">
          <n-icon><AddOutline /></n-icon> 新建文档
        </n-button>
      </div>
    </div>
    <div class="filter-bar">
      <n-input v-model="searchKeyword" placeholder="搜索文档标题/内容" style="width: 240px" clearable @change="handleSearch" />
      <n-select
        v-model="filterCategory"
        placeholder="文档分类"
        style="width: 160px"
        clearable
        :options="categoryOptions"
        @update:value="handleSearch"
      />
    </div>
    <div class="table-container">
      <n-data-table
        :loading="loading"
        :data="knowledgeList"
        :columns="columns"
        :pagination="pagination"
        :row-key="row => row.id"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
      <div class="pagination">
        <n-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>
    <n-modal v-model="dialogVisible" :title="dialogTitle" width="700px">
      <n-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <n-form-item label="文档标题" prop="title">
          <n-input v-model="form.title" placeholder="请输入文档标题" />
        </n-form-item>
        <n-form-item label="文档分类" prop="category">
          <n-select v-model="form.category" placeholder="请选择分类" style="width: 100%" :options="categoryOptions" />
        </n-form-item>
        <n-form-item label="文档内容" prop="content">
          <n-input v-model="form.content" type="textarea" :rows="8" placeholder="请输入文档内容" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitForm">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { knowledge } from '@/api'
import { formatTime } from '@/utils/date'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const searchKeyword = ref('')
const filterCategory = ref(null)
const knowledgeList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新建文档')
const formRef = ref(null)

const categoryOptions = [
  { label: '系统运维', value: 'ops' },
  { label: '故障处理', value: 'fault' },
  { label: '安全规范', value: 'security' },
  { label: '操作手册', value: 'manual' }
]

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const form = reactive({ id: null, title: '', category: '', content: '' })

const rules = {
  title: [{ required: true, message: '请输入文档标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入文档内容', trigger: 'blur' }]
}

const columns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '文档标题', key: 'title', minWidth: 200, ellipsis: { tooltip: true } },
  {
    title: '分类', key: 'category', width: 120,
    render: (row) => h('span', null, getCategoryText(row.category))
  },
  { title: '作者', key: 'author', width: 120 },
  { title: '浏览', key: 'views', width: 80 },
  {
    title: '状态', key: 'status', width: 100,
    render: (row) => h('n-tag', { type: row.status === 'published' ? 'success' : 'info', size: 'small' }, () => row.status === 'published' ? '已发布' : '草稿')
  },
  {
    title: '更新时间', key: 'updated_at', width: 160,
    render: (row) => h('span', null, formatTime(row.updated_at))
  },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render: (row) => h('n-space', null, [
      h('n-button', { type: 'primary', link: true, size: 'small', onClick: () => handleView(row) }, () => '查看'),
      h('n-button', { type: 'primary', link: true, size: 'small', onClick: () => handleEdit(row) }, () => '编辑'),
      h('n-button', { type: 'error', link: true, size: 'small', onClick: () => handleDelete(row) }, () => '删除')
    ])
  }
]

onMounted(() => { loadData() })

async function loadData() {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filterCategory.value) params.category = filterCategory.value
    const res = await knowledge.getSopList(params).catch(() => ({ items: [], total: 0 }))
    knowledgeList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    message.error('加载数据失败')
    console.error('Load knowledge error:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() { pagination.page = 1; loadData() }

function handlePageChange(page) { pagination.page = page; loadData() }
function handlePageSizeChange(pageSize) { pagination.pageSize = pageSize; pagination.page = 1; loadData() }

function getCategoryText(c) {
  return categoryOptions.find(o => o.value === c)?.label || c || '-'
}

function handleAdd() {
  dialogTitle.value = '新建文档'
  Object.assign(form, { id: null, title: '', category: '', content: '' })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑文档'
  Object.assign(form, { id: row.id, title: row.title, category: row.category, content: row.content || '' })
  dialogVisible.value = true
}

function handleView(row) { message.info(`查看文档: ${row.title}`) }

function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除文档 "${row.title}" 吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await knowledge.deleteSop(row.id)
        message.success('删除成功')
        loadData()
      } catch (error) {
        message.error('删除失败')
        console.error('Delete error:', error)
      }
    }
  })
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) {
      await knowledge.updateSop(form.id, form)
      message.success('更新成功')
    } else {
      await knowledge.createSop(form)
      message.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (error) {
    message.error('保存失败')
    console.error('Submit error:', error)
  }
}
</script>

<style lang="scss" scoped>
.page-container { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
.page-subtitle { color: #999; margin: 4px 0 0; font-size: 14px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.table-container { background: #fff; padding: 16px; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
