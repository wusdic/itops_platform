<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">字典管理</h1>
        <p class="page-subtitle">系统数据字典管理</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="handleAdd">
          <n-icon><AddOutline /></n-icon> 添加字典
        </n-button>
      </div>
    </div>
    <div class="filter-bar">
      <n-input v-model="searchKeyword" placeholder="搜索字典名称/编码" style="width: 200px" clearable @change="handleSearch" />
    </div>
    <div class="table-container">
      <n-data-table :data="dictList" style="width: 100%">
        <n-data-table-column prop="name" label="字典名称" width="180" />
        <n-data-table-column prop="code" label="字典编码" width="150" />
        <n-data-table-column prop="description" label="描述" min-width="200" />
        <n-data-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <n-tag :type="row.status === '1' ? 'success' : 'info'" size="small">{{ row.status === '1' ? '启用' : '禁用' }}</n-tag>
          </template>
        <n-data-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        <n-data-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <n-button type="primary" link size="small" @click="handleItems(row)">字典项</n-button>
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
    <n-modal v-model="dialogVisible" :title="dialogTitle" width="500px">
      <n-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <n-form-item label="字典名称" prop="name">
          <n-input v-model="form.name" placeholder="请输入字典名称" />
        </n-form-item>
        <n-form-item label="字典编码" prop="code">
          <n-input v-model="form.code" placeholder="请输入字典编码" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </n-form-item>
        <n-form-item label="状态">
          <n-radio-group v-model="form.status">
            <n-radio value="1">启用</n-radio>
            <n-radio value="0">禁用</n-radio>
          </n-radio-group>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="dialogVisible = false">取消</n-button>
        <n-button type="primary" @click="submitForm">确定</n-button>
      </template>
    </n-modal>
    <n-modal v-model="itemsDialogVisible" title="字典项管理" width="700px">
      <n-data-table :data="dictItems" style="width: 100%">
        <n-data-table-column prop="label" label="标签" min-width="120" />
        <n-data-table-column prop="value" label="值" min-width="120" />
        <n-data-table-column prop="sort" label="排序" width="80" />
        <n-data-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <n-tag :type="row.status === '1' ? 'success' : 'info'" size="small">{{ row.status === '1' ? '启用' : '禁用' }}</n-tag>
          </template>
        <n-data-table-column label="操作" width="120">
          <template #default="{ row }">
            <n-button type="primary" link size="small" @click="handleEditItem(row)">编辑</n-button>
            <n-button type="danger" link size="small" @click="handleDeleteItem(row)">删除</n-button>
          </template>
      <div style="margin-top: 16px; text-align: right;">
        <n-button type="primary" size="small" @click="handleAddItem">添加字典项</n-button>
      </div>
    </n-modal>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
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
  dialog.warning({ title: '提示', content: `确定删除字典 "${row.name}" 吗?`, positiveText: '确定', negativeText: '取消', onPositiveClick: () => { }, onNegativeClick: () => { } })
    .then(async () => { try { await dictApi.delete(row.id); message.success('删除成功'); loadData() } catch (error) { console.error('Delete error:', error) } }).catch(() => {})
}
const handleItems = (row) => {
  currentDictId.value = row.id
  dictItems.value = [
    { id: 1, label: '是', value: '1', sort: 1, status: '1' },
    { id: 2, label: '否', value: '0', sort: 2, status: '1' }
  ]
  itemsDialogVisible.value = true
}
const handleAddItem = () => { message.info('添加字典项') }
const handleEditItem = (row) => { message.info('编辑字典项') }
const handleDeleteItem = (row) => { message.info('删除字典项') }
const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await dictApi.update(form.id, form); message.success('更新成功') }
    else { await dictApi.create(form); message.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>
<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
