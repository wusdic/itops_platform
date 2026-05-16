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
      <n-select v-model="filterCategory" placeholder="文档分类" style="width: 160px" clearable @change="handleSearch">
        <n-option label="系统运维" value="ops" />
        <n-option label="故障处理" value="fault" />
        <n-option label="安全规范" value="security" />
        <n-option label="操作手册" value="manual" />
      </n-select>
    </div>
    <div class="table-container">
      <n-data-table :data="knowledgeList" style="width: 100%">
        <n-data-table-column prop="title" label="文档标题" min-width="200" />
        <n-data-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <n-tag size="small">{{ getCategoryText(row.category) }}</n-tag>
          </template>
        <n-data-table-column prop="author" label="作者" width="120" />
        <n-data-table-column prop="views" label="浏览" width="80" />
        <n-data-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <n-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
              {{ row.status === 'published' ? '已发布' : '草稿' }}
            </n-tag>
          </template>
        <n-data-table-column prop="updated_at" label="更新时间" width="160">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        <n-data-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <n-button type="primary" link size="small" @click="handleView(row)">查看</n-button>
            <n-button type="primary" link size="small" @click="handleEdit(row)">编辑</n-button>
            <n-button type="danger" link size="small" @click="handleDelete(row)">删除</n-button>
          </template>
      <div class="pagination">
        <n-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
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
          <n-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
            <n-option label="系统运维" value="ops" />
            <n-option label="故障处理" value="fault" />
            <n-option label="安全规范" value="security" />
            <n-option label="操作手册" value="manual" />
          </n-select>
        </n-form-item>
        <n-form-item label="文档内容" prop="content">
          <n-input v-model="form.content" type="textarea" :rows="8" placeholder="请输入文档内容" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="dialogVisible = false">取消</n-button>
        <n-button type="primary" @click="submitForm">确定</n-button>
      </template>
    </n-modal>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { knowledge } from '@/api'
import { formatTime } from '@/utils/date'
const loading = ref(false)
const searchKeyword = ref('')
const filterCategory = ref('')
const knowledgeList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新建文档')
const formRef = ref(null)
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, title: '', category: '', content: '' })
const rules = {
  title: [{ required: true, message: '请输入文档标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入文档内容', trigger: 'blur' }]
}
onMounted(() => { loadData() })
const loadData = async () => {
  loading.value = true
  try {
    const res = await knowledge.getList({ page: pagination.page, page_size: pagination.pageSize, keyword: searchKeyword.value, category: filterCategory.value }).catch(() => ({ items: [], total: 0 }))
    knowledgeList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load knowledge error:', error) }
  finally { loading.value = false }
}
const handleSearch = () => { pagination.page = 1; loadData() }
const getCategoryText = (c) => ({ ops: '系统运维', fault: '故障处理', security: '安全规范', manual: '操作手册' }[c] || c)
const handleAdd = () => {
  dialogTitle.value = '新建文档'
  Object.assign(form, { id: null, title: '', category: '', content: '' })
  dialogVisible.value = true
}
const handleEdit = (row) => {
  dialogTitle.value = '编辑文档'
  Object.assign(form, { id: row.id, title: row.title, category: row.category, content: row.content || '' })
  dialogVisible.value = true
}
const handleView = (row) => { message.info(`查看文档: ${row.title}`) }
const handleDelete = (row) => {
  dialog.warning({ title: '提示', content: `确定删除文档 "${row.title}" 吗?`, positiveText: '确定', negativeText: '取消', onPositiveClick: () => { }, onNegativeClick: () => { } })
    .then(async () => {
      try { await knowledge.delete(row.id); message.success('删除成功'); loadData() }
      catch (error) { console.error('Delete error:', error) }
    }).catch(() => {})
}
const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await knowledge.update(form.id, form); message.success('更新成功') }
    else { await knowledge.create(form); message.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>
<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
