<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">脚本管理</h1>
        <p class="page-subtitle">自动化运维脚本管理</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="handleAdd">
          <n-icon><AddOutline /></n-icon> 新建脚本
        </n-button>
      </div>
    </div>
    <div class="filter-bar">
      <n-input v-model="searchKeyword" placeholder="搜索脚本名称" style="width: 200px" clearable @change="handleSearch" />
      <n-select v-model="filterType" placeholder="脚本类型" style="width: 140px" clearable @change="handleSearch">
        <n-option label="Shell" value="shell" />
        <n-option label="Python" value="python" />
        <n-option label="PowerShell" value="powershell" />
      </n-select>
    </div>
    <div class="table-container">
      <n-data-table :data="scriptList" style="width: 100%">
        <n-data-table-column prop="name" label="脚本名称" min-width="180" />
        <n-data-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <n-tag size="small">{{ getTypeText(row.type) }}</n-tag>
          </template>
        <n-data-table-column prop="description" label="描述" min-width="200" />
        <n-data-table-column prop="creator" label="创建人" width="120" />
        <n-data-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        <n-data-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <n-button type="primary" link size="small" @click="handleExecute(row)">执行</n-button>
            <n-button type="primary" link size="small" @click="handleEdit(row)">编辑</n-button>
            <n-button type="primary" link size="small" @click="handleView(row)">查看</n-button>
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
        <n-form-item label="脚本名称" prop="name">
          <n-input v-model="form.name" placeholder="请输入脚本名称" />
        </n-form-item>
        <n-form-item label="脚本类型" prop="type">
          <n-select v-model="form.type" placeholder="请选择脚本类型" style="width: 100%">
            <n-option label="Shell" value="shell" />
            <n-option label="Python" value="python" />
            <n-option label="PowerShell" value="powershell" />
          </n-select>
        </n-form-item>
        <n-form-item label="描述" prop="description">
          <n-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </n-form-item>
        <n-form-item label="脚本内容" prop="content">
          <n-input v-model="form.content" type="textarea" :rows="10" placeholder="请输入脚本内容" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="dialogVisible = false">取消</n-button>
        <n-button type="primary" @click="submitForm">确定</n-button>
      </template>
    </n-modal>
    <n-modal v-model="executeDialogVisible" title="执行脚本" width="500px">
      <n-form :model="executeForm" label-width="100px">
        <n-form-item label="目标主机">
          <n-select v-model="executeForm.host_ids" multiple placeholder="请选择目标主机" style="width: 100%">
            <n-option label="192.168.1.10" value="1" />
            <n-option label="192.168.1.11" value="2" />
            <n-option label="192.168.1.12" value="3" />
          </n-select>
        </n-form-item>
        <n-form-item label="执行参数">
          <n-input v-model="executeForm.params" placeholder="请输入执行参数(可选)" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="executeDialogVisible = false">取消</n-button>
        <n-button type="primary" @click="submitExecute">执行</n-button>
      </template>
    </n-modal>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { automation } from '@/api'
import { formatTime } from '@/utils/date'
const loading = ref(false)
const searchKeyword = ref('')
const filterType = ref('')
const scriptList = ref([])
const dialogVisible = ref(false)
const executeDialogVisible = ref(false)
const dialogTitle = ref('新建脚本')
const formRef = ref(null)
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', type: '', description: '', content: '' })
const executeForm = reactive({ host_ids: [], params: '' })
const rules = {
  name: [{ required: true, message: '请输入脚本名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择脚本类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入脚本内容', trigger: 'blur' }]
}
onMounted(() => { loadData() })
const loadData = async () => {
  loading.value = true
  try {
    const res = await automation.getScripts({ page: pagination.page, page_size: pagination.pageSize, keyword: searchKeyword.value, type: filterType.value }).catch(() => ({ items: [], total: 0 }))
    scriptList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load scripts error:', error) }
  finally { loading.value = false }
}
const handleSearch = () => { pagination.page = 1; loadData() }
const getTypeText = (t) => ({ shell: 'Shell', python: 'Python', powershell: 'PowerShell' }[t] || t)
const handleAdd = () => { dialogTitle.value = '新建脚本'; Object.assign(form, { id: null, name: '', type: '', description: '', content: '' }); dialogVisible.value = true }
const handleEdit = (row) => { dialogTitle.value = '编辑脚本'; Object.assign(form, { id: row.id, name: row.name, type: row.type, description: row.description, content: row.content }); dialogVisible.value = true }
const handleView = (row) => { message.info(`查看脚本: ${row.name}`) }
const handleExecute = (row) => { Object.assign(executeForm, { host_ids: [], params: '' }); executeDialogVisible.value = true }
dialog.warning({ title: '提示', content: `确定删除脚本 "${row.name}" 吗?`, positiveText: '确定', negativeText: '取消', onPositiveClick: () => { 
  }, onNegativeClick: () => {} }
const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await automation.updateScript(form.id, form); message.success('更新成功') }
    else { await automation.createScript(form); message.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
const submitExecute = async () => {
  try {
    await automation.executeScript(executeForm.host_ids[0], executeForm)
    message.success('脚本执行已提交')
    executeDialogVisible.value = false
  } catch (error) { console.error('Execute error:', error) }
}
</script>
<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
