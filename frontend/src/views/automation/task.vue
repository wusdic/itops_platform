<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">脚本管理</h1>
        <p class="page-subtitle">自动化运维脚本管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新建脚本
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索脚本名称" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterType" placeholder="脚本类型" style="width: 140px" clearable @change="handleSearch">
        <el-option label="Shell" value="shell" />
        <el-option label="Python" value="python" />
        <el-option label="PowerShell" value="powershell" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="scriptList" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="脚本名称" min-width="180" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="creator" label="创建人" width="120" />
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleExecute(row)">执行</el-button>
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="primary" link size="small" @click="handleView(row)">查看</el-button>
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
        <el-form-item label="脚本名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入脚本名称" />
        </el-form-item>
        <el-form-item label="脚本类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择脚本类型" style="width: 100%">
            <el-option label="Shell" value="shell" />
            <el-option label="Python" value="python" />
            <el-option label="PowerShell" value="powershell" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="脚本内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="10" placeholder="请输入脚本内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="executeDialogVisible" title="执行脚本" width="500px">
      <el-form :model="executeForm" label-width="100px">
        <el-form-item label="目标主机">
          <el-select v-model="executeForm.host_ids" multiple placeholder="请选择目标主机" style="width: 100%">
            <el-option label="192.168.1.10" value="1" />
            <el-option label="192.168.1.11" value="2" />
            <el-option label="192.168.1.12" value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行参数">
          <el-input v-model="executeForm.params" placeholder="请输入执行参数(可选)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="executeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitExecute">执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
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
const handleView = (row) => { ElMessage.info(`查看脚本: ${row.name}`) }
const handleExecute = (row) => { Object.assign(executeForm, { host_ids: [], params: '' }); executeDialogVisible.value = true }
const handleDelete = (row) => { ElMessageBox.confirm(`确定删除脚本 "${row.name}" 吗?`, '提示', { type: 'warning' }).then(async () => { try { await automation.deleteScript(row.id); ElMessage.success('删除成功'); loadData() } catch (error) { console.error('Delete error:', error) } }).catch(() => {}) }

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await automation.updateScript(form.id, form); ElMessage.success('更新成功') }
    else { await automation.createScript(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}

const submitExecute = async () => {
  try {
    await automation.executeScript(executeForm.host_ids[0], executeForm)
    ElMessage.success('脚本执行已提交')
    executeDialogVisible.value = false
  } catch (error) { console.error('Execute error:', error) }
}
</script>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
