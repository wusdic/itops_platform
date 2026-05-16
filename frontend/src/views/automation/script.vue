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
    <!-- Create/Edit Dialog -->
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
    <!-- View Dialog -->
    <n-modal v-model="viewDialogVisible" title="查看脚本" width="700px">
      <div class="script-view">
        <div class="script-meta">
          <n-tag size="small">{{ getTypeText(viewScript.type) }}</n-tag>
          <span class="script-desc">{{ viewScript.description }}</span>
        </div>
        <n-input v-model="viewScript.content" type="textarea" :rows="15" readonly class="script-content" />
      </div>
      <template #footer>
        <n-button @click="viewDialogVisible = false">关闭</n-button>
      </template>
    </n-modal>
    <!-- Execute Dialog -->
    <n-modal v-model="executeDialogVisible" title="执行脚本" width="500px">
      <n-form :model="executeForm" label-width="100px">
        <n-form-item label="目标主机">
          <n-select v-model="executeForm.host_ids" multiple placeholder="请选择目标主机" style="width: 100%" filterable>
            <n-option v-for="device in devices" :key="device.id" :label="`${device.name} (${device.ip})`" :value="device.id" />
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
import { ref, reactive, onMounted, computed } from 'vue'
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
    const res = await fetch('/api/devices')
    if (res.ok) {
      devices.value = await res.json()
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
  dialog.warning({ title: '提示', content: `确定删除脚本 "${row.name}" 吗?`, positiveText: '确定', negativeText: '取消', onPositiveClick: () => { }, onNegativeClick: () => { } })
    .then(() => {
      const scripts = getScriptsFromStorage()
      const idx = scripts.findIndex(s => s.id === row.id)
      if (idx !== -1) {
        scripts.splice(idx, 1)
        saveScriptsToStorage(scripts)
        message.success('删除成功')
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
    message.success('更新成功')
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
    message.success('创建成功')
  }
  saveScriptsToStorage(scripts)
  dialogVisible.value = false
  loadData()
}
const submitExecute = async () => {
  if (executeForm.host_ids.length === 0) {
    message.warning('请选择至少一台目标主机')
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
      message.success('脚本执行已提交')
    } else {
      message.error('脚本执行失败')
    }
  } catch (e) {
    message.error('执行请求失败')
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
