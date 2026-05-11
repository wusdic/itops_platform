<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">知识文档</h1>
        <p class="page-subtitle">运维知识库管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新建文档
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索文档标题/内容" style="width: 240px" clearable @change="handleSearch" />
      <el-select v-model="filterCategory" placeholder="文档分类" style="width: 160px" clearable @change="handleSearch">
        <el-option label="系统运维" value="ops" />
        <el-option label="故障处理" value="fault" />
        <el-option label="安全规范" value="security" />
        <el-option label="操作手册" value="manual" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="knowledgeList" v-loading="loading" style="width: 100%">
        <el-table-column prop="title" label="文档标题" min-width="200" />
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getCategoryText(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="author" label="作者" width="120" />
        <el-table-column prop="views" label="浏览" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
              {{ row.status === 'published' ? '已发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">查看</el-button>
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入文档标题" />
        </el-form-item>
        <el-form-item label="文档分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
            <el-option label="系统运维" value="ops" />
            <el-option label="故障处理" value="fault" />
            <el-option label="安全规范" value="security" />
            <el-option label="操作手册" value="manual" />
          </el-select>
        </el-form-item>
        <el-form-item label="文档内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="请输入文档内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
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

const handleView = (row) => { ElMessage.info(`查看文档: ${row.title}`) }

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除文档 "${row.title}" 吗?`, '提示', { type: 'warning' })
    .then(async () => {
      try { await knowledge.delete(row.id); ElMessage.success('删除成功'); loadData() }
      catch (error) { console.error('Delete error:', error) }
    }).catch(() => {})
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await knowledge.update(form.id, form); ElMessage.success('更新成功') }
    else { await knowledge.create(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
