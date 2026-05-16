<template>
  <div class="page-container">
    <n-card title="脚本管理" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          新建脚本
        </n-button>
      </template>

      <n-space style="margin-bottom: 12px">
        <n-input v-model:value="searchKeyword" placeholder="搜索脚本名称" clearable style="width: 200px" @change="loadData">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="filterType" :options="typeOptions" placeholder="脚本类型" clearable style="width: 140px" @change="loadData" />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="scriptList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 新建/编辑 -->
    <n-modal v-model:show="dialogVisible" preset="card" :title="dialogTitle" style="width: 700px">
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item label="脚本名称" required>
          <n-input v-model:value="form.name" placeholder="请输入脚本名称" />
        </n-form-item>
        <n-form-item label="脚本类型">
          <n-select v-model:value="form.type" :options="typeOptions" placeholder="请选择" style="width: 100%" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </n-form-item>
        <n-form-item label="脚本内容">
          <n-input v-model:value="form.content" type="textarea" :rows="10" placeholder="请输入脚本内容" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitForm" :loading="submitting">确定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 查看脚本 -->
    <n-modal v-model:show="viewDialogVisible" preset="card" title="查看脚本" style="width: 700px">
      <n-space vertical>
        <n-space>
          <n-tag>{{ viewScript.type || '-' }}</n-tag>
          <span style="color: #86909c">{{ viewScript.description || '' }}</span>
        </n-space>
        <n-input type="textarea" :value="viewScript.content || ''" :rows="15" readonly />
      </n-space>
    </n-modal>

    <!-- 执行 -->
    <n-modal v-model:show="executeDialogVisible" preset="card" title="执行脚本" style="width: 500px">
      <n-form :model="executeForm" label-placement="left" label-width="100">
        <n-form-item label="目标主机">
          <n-select v-model:value="executeForm.host_ids" :options="deviceOptions" multiple placeholder="请选择目标主机" style="width: 100%" />
        </n-form-item>
        <n-form-item label="执行参数">
          <n-input v-model:value="executeForm.params" placeholder="请输入执行参数(可选)" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="executeDialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitExecute" :loading="executing">执行</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NSpace, NTag, NIcon, useMessage } from 'naive-ui'
import { AddOutline, SearchOutline, PlayOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const executing = ref(false)
const scriptList = ref([])
const searchKeyword = ref('')
const filterType = ref(null)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const executeDialogVisible = ref(false)
const dialogTitle = ref('新建脚本')
const deviceOptions = ref([])

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', type: 'shell', description: '', content: '' })
const viewScript = reactive({ type: '', description: '', content: '' })
const executeForm = reactive({ host_ids: [], params: '', script_id: null, script_name: '' })

const typeOptions = [
  { label: 'Shell', value: 'shell' },
  { label: 'Python', value: 'python' },
  { label: 'PowerShell', value: 'powershell' }
]

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '脚本名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '类型', key: 'type', width: 120,
    render: (r) => h(NTag, { size: 'small', type: 'info' }, () => r.type?.toUpperCase() || '-')
  },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '创建人', key: 'creator_name', width: 120 },
  { title: '更新时间', key: 'updated_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => handleExecute(row) }, () => '执行'),
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleView(row) }, () => '查看'),
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleEdit(row) }, () => '编辑'),
        h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, () => '删除')
      ])
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({ page: pagination.page, page_size: pagination.pageSize })
    if (filterType.value) params.append('type', filterType.value)
    if (searchKeyword.value) params.append('search', searchKeyword.value)
    const res = await fetch(`/api/v1/automation/trigger-rules?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    scriptList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载脚本失败: ${e.message}`)
    console.error('[automation/script] loadData error:', e)
    scriptList.value = []
  } finally {
    loading.value = false
  }
}

async function loadDevices() {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/assets/device?page=1&page_size=100', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error()
    const data = await res.json()
    deviceOptions.value = (data.items || []).map(d => ({ label: `${d.name} (${d.ip_address})`, value: d.id }))
  } catch {
    deviceOptions.value = []
  }
}

function handleAdd() {
  dialogTitle.value = '新建脚本'
  Object.assign(form, { id: null, name: '', type: 'shell', description: '', content: '' })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑脚本'
  Object.assign(form, { id: row.id, name: row.name, type: row.type || 'shell', description: row.description || '', content: row.content || '' })
  dialogVisible.value = true
}

function handleView(row) {
  Object.assign(viewScript, { type: row.type || '', description: row.description || '', content: row.content || '' })
  viewDialogVisible.value = true
}

function handleExecute(row) {
  Object.assign(executeForm, { host_ids: [], params: '', script_id: row.id, script_name: row.name })
  executeDialogVisible.value = true
}

async function handleDelete(row) {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/automation/trigger-rules/${row.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error(`删除失败: ${e.message}`)
    console.error('[automation/script] delete error:', e)
  }
}

async function submitForm() {
  if (!form.name) { message.warning('请填写脚本名称'); return }
  submitting.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const method = form.id ? 'PUT' : 'POST'
    const url = form.id ? `/api/v1/automation/trigger-rules/${form.id}` : '/api/v1/automation/trigger-rules'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(form)
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success(form.id ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadData()
  } catch (e) {
    message.error(`操作失败: ${e.message}`)
    console.error('[automation/script] submit error:', e)
  } finally {
    submitting.value = false
  }
}

async function submitExecute() {
  if (executeForm.host_ids.length === 0) { message.warning('请选择至少一台目标主机'); return }
  executing.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/automation/trigger-rules/${executeForm.script_id}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ host_ids: executeForm.host_ids, params: executeForm.params })
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success('脚本执行已提交')
    executeDialogVisible.value = false
  } catch (e) {
    message.error(`执行失败: ${e.message}`)
    console.error('[automation/script] execute error:', e)
  } finally {
    executing.value = false
  }
}

onMounted(() => { loadData(); loadDevices() })
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
