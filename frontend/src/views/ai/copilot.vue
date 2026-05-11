<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">分类管理</h1>
        <p class="page-subtitle">知识库分类管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新建分类
        </el-button>
      </div>
    </div>

    <div class="table-container">
      <el-table :data="categoryList" v-loading="loading" style="width: 100%" row-key="id" :tree-props="{ children: 'children' }">
        <el-table-column prop="name" label="分类名称" min-width="200" />
        <el-table-column prop="code" label="分类编码" width="150" />
        <el-table-column prop="sort" label="排序" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '1' ? 'success' : 'info'" size="small">{{ row.status === '1' ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="上级分类" prop="parent_id">
          <el-tree-select v-model="form.parent_id" :data="treeData" placeholder="请选择上级分类" clearable check-strictly style="width: 100%" />
        </el-form-item>
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="分类编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入分类编码" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="1">启用</el-radio>
            <el-radio value="0">禁用</el-radio>
          </el-radio-group>
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
const categoryList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新建分类')
const formRef = ref(null)

const form = reactive({ id: null, parent_id: null, name: '', code: '', sort: 0, status: '1' })
const rules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入分类编码', trigger: 'blur' }]
}

const treeData = computed(() => [{ id: 0, label: '顶级分类', children: categoryList.value.map(c => ({ id: c.id, label: c.name })) }])

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await knowledge.getCategory().catch(() => [])
    categoryList.value = res || []
  } catch (error) { console.error('Load category error:', error) }
  finally { loading.value = false }
}

const handleAdd = () => {
  dialogTitle.value = '新建分类'
  Object.assign(form, { id: null, parent_id: null, name: '', code: '', sort: 0, status: '1' })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑分类'
  Object.assign(form, { id: row.id, parent_id: row.parent_id, name: row.name, code: row.code, sort: row.sort, status: row.status })
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除分类 "${row.name}" 吗?`, '提示', { type: 'warning' })
    .then(async () => {
      try { await knowledge.deleteCategory(row.id); ElMessage.success('删除成功'); loadData() }
      catch (error) { console.error('Delete error:', error) }
    }).catch(() => {})
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await knowledge.updateCategory(form.id, form); ElMessage.success('更新成功') }
    else { await knowledge.createCategory(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>

<script>
import { computed } from 'vue'
export default { name: 'KnowledgeCategory' }
</script>

<style lang="scss" scoped>
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
