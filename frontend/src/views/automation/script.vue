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

    <!-- Create/Edit Dialog -->
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

    <!-- View Dialog -->
    <el-dialog v-model="viewDialogVisible" title="查看脚本" width="700px">
      <div class="script-view">
        <div class="script-meta">
          <el-tag size="small">{{ getTypeText(viewScript.type) }}</el-tag>
          <span class="script-desc">{{ viewScript.description }}</span>
        </div>
        <el-input v-model="viewScript.content" type="textarea" :rows="15" readonly class="script-content" />
      </div>
      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Execute Dialog -->
    <el-dialog v-model="executeDialogVisible" title="执行脚本" width="500px">
      <el-form :model="executeForm" label-width="100px">
        <el-form-item label="目标主机">
          <el-select v-model="executeForm.host_ids" multiple placeholder="请选择目标主机" style="width: 100%" filterable>
            <el-option v-for="device in devices" :key="device.id" :label="`${device.name} (${device.ip})`" :value="device.id" />
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const LOADING_KEY = 'scripts_loading'
const STORAGE_KEY = 'automation_scripts'

const loading = ref(false)
const searchKeyword = ref('')
const filterType = ref('')
const scriptList = ref([])
const devices = ref([])
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const executeDialogVisible = ref(false)
const dialogTitle = ref('新建脚本')
const formRef = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', type: '', description: '', content: '' })
const viewScript = reactive({ type: '', description: '', content: '' })
const executeForm = reactive({ host_ids: [], params: '' })

const rules = {
  name: [{ required: true, message: '请输入脚本名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择脚本类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入脚本内容', trigger: 'blur' }]
}

// localStorage helpers
const getScriptsFromStorage = () => {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

const saveScriptsToStorage = (scripts) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(scripts))
}

// Filtered scripts based on search and type
const filteredScripts = computed(() => {
  let scripts = getScriptsFromStorage()
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    scripts = scripts.filter(s => s.name.toLowerCase().includes(kw) || s.description?.toLowerCase().includes(kw))
  }
  if (filterType.value) {
    scripts = scripts.filter(s => s.type === filterType.value)
  }
  return scripts
})

// Format time
const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  return d.toLocaleString('zh-CN')
}

// Get type text
const getTypeText = (t) => ({ shell: 'Shell', python: 'Python', powershell: 'PowerShell' }[t] || t)

// Load scripts from localStorage
const loadData = () => {
  loading.value = true
  try {
    const all = filteredScripts.value
    const start = (pagination.page - 1) * pagination.pageSize
    const end = start + pagination.pageSize
    scriptList.value = all.slice(start, end)
    pagination.total = all.length
  } finally {
    loading.value = false
  }
}

// Load devices from API
const loadDevices = async () => {
  try {
    const res = await fetch('/api/v1/assets/device?page_size=100')
    if (res.ok) {
      const data = await res.json()
      devices.value = (data.items || data.devices || []).map(d => ({ id: d.id, name: d.hostname || d.name, ip: d.ip_address }))
    } else {
      devices.value = []
    }
  } catch {
    devices.value = []
  }
}

const handleSearch = () => { pagination.page = 1; loadData() }

const handleAdd = () => {
  dialogTitle.value = '新建脚本'
  Object.assign(form, { id: null, name: '', type: '', description: '', content: '' })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑脚本'
  Object.assign(form, { id: row.id, name: row.name, type: row.type, description: row.description, content: row.content })
  dialogVisible.value = true
}

const handleView = (row) => {
  Object.assign(viewScript, { type: row.type, description: row.description, content: row.content })
  viewDialogVisible.value = true
}

const handleExecute = (row) => {
  Object.assign(executeForm, { host_ids: [], params: '', script_id: row.id, script_name: row.name })
  executeDialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除脚本 "${row.name}" 吗?`, '提示', { type: 'warning' })
    .then(() => {
      const scripts = getScriptsFromStorage()
      const idx = scripts.findIndex(s => s.id === row.id)
      if (idx !== -1) {
        scripts.splice(idx, 1)
        saveScriptsToStorage(scripts)
        ElMessage.success('删除成功')
        loadData()
      }
    })
    .catch(() => {})
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  const scripts = getScriptsFromStorage()
  if (form.id) {
    const idx = scripts.findIndex(s => s.id === form.id)
    if (idx !== -1) {
      scripts[idx] = { ...scripts[idx], ...form, updated_at: new Date().toISOString() }
    }
    ElMessage.success('更新成功')
  } else {
    scripts.push({
      id: Date.now().toString(),
      name: form.name,
      type: form.type,
      description: form.description,
      content: form.content,
      creator: '当前用户',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
    ElMessage.success('创建成功')
  }
  saveScriptsToStorage(scripts)
  dialogVisible.value = false
  loadData()
}

const submitExecute = async () => {
  if (executeForm.host_ids.length === 0) {
    ElMessage.warning('请选择至少一台目标主机')
    return
  }
  try {
    const res = await fetch('/api/automation/script/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        script_id: executeForm.script_id,
        script_name: executeForm.script_name,
        host_ids: executeForm.host_ids,
        params: executeForm.params
      })
    })
    if (res.ok) {
      ElMessage.success('脚本执行已提交')
    } else {
      ElMessage.error('脚本执行失败')
    }
  } catch (e) {
    ElMessage.error('执行请求失败')
  }
  executeDialogVisible.value = false
}

onMounted(() => {
  loadData()
  loadDevices()
})
</script>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
.script-view { display: flex; flex-direction: column; gap: 12px; }
.script-meta { display: flex; align-items: center; gap: 12px; }
.script-desc { color: #86909c; font-size: 14px; }
.script-content :deep(.el-textarea__inner) { font-family: 'Courier New', monospace; font-size: 13px; }
</style>
