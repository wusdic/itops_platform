<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">字典管理</h1>
        <p class="page-subtitle">系统数据字典管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加字典
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索字典名称/编码" style="width: 200px" clearable @change="handleSearch" />
    </div>

    <div class="table-container">
      <el-table :data="dictList" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="字典名称" width="180" />
        <el-table-column prop="code" label="字典编码" width="150" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '1' ? 'success' : 'info'" size="small">{{ row.status === '1' ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleItems(row)">字典项</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="字典名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入字典名称" />
        </el-form-item>
        <el-form-item label="字典编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入字典编码" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入描述" />
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

    <el-dialog v-model="itemsDialogVisible" title="字典项管理" width="700px">
      <el-table :data="dictItems" style="width: 100%">
        <el-table-column prop="label" label="标签" min-width="120" />
        <el-table-column prop="value" label="值" min-width="120" />
        <el-table-column prop="sort" label="排序" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '1' ? 'success' : 'info'" size="small">{{ row.status === '1' ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEditItem(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDeleteItem(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 16px; text-align: right;">
        <el-button type="primary" size="small" @click="handleAddItem">添加字典项</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { dict as dictApi } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const searchKeyword = ref('')
const dictList = ref([])
const dialogVisible = ref(false)
const itemsDialogVisible = ref(false)
const dialogTitle = ref('添加字典')
const formRef = ref(null)
const dictItems = ref([])
const currentDictId = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', code: '', description: '', status: '1' })
const rules = {
  name: [{ required: true, message: '请输入字典名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入字典编码', trigger: 'blur' }]
}

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await dictApi.getList({ page: pagination.page, page_size: pagination.pageSize, keyword: searchKeyword.value }).catch(() => ({ items: [], total: 0 }))
    dictList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load dicts error:', error) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; loadData() }

const handleAdd = () => { dialogTitle.value = '添加字典'; Object.assign(form, { id: null, name: '', code: '', description: '', status: '1' }); dialogVisible.value = true }
const handleEdit = (row) => { dialogTitle.value = '编辑字典'; Object.assign(form, { id: row.id, name: row.name, code: row.code, description: row.description, status: row.status }); dialogVisible.value = true }

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除字典 "${row.name}" 吗?`, '提示', { type: 'warning' })
    .then(async () => { try { await dictApi.delete(row.id); ElMessage.success('删除成功'); loadData() } catch (error) { console.error('Delete error:', error) } }).catch(() => {})
}

const handleItems = (row) => {
  currentDictId.value = row.id
  dictItems.value = [
    { id: 1, label: '是', value: '1', sort: 1, status: '1' },
    { id: 2, label: '否', value: '0', sort: 2, status: '1' }
  ]
  itemsDialogVisible.value = true
}

const handleAddItem = () => { ElMessage.info('添加字典项') }
const handleEditItem = (row) => { ElMessage.info('编辑字典项') }
const handleDeleteItem = (row) => { ElMessage.info('删除字典项') }

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await dictApi.update(form.id, form); ElMessage.success('更新成功') }
    else { await dictApi.create(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
