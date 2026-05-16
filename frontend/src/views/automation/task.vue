<template>
  <div class="page-container">
    <n-card title="自动化任务" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          新建任务
        </n-button>
      </template>

      <n-space style="margin-bottom: 12px">
        <n-input v-model:value="searchKeyword" placeholder="搜索任务名称" clearable style="width: 200px" @change="loadData">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="任务状态" clearable style="width: 140px" @change="loadData" />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="taskList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 新建/编辑任务 -->
    <n-modal v-model:show="dialogVisible" preset="card" :title="dialogTitle" style="width: 700px">
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item label="任务名称" required>
          <n-input v-model:value="form.name" placeholder="请输入任务名称" />
        </n-form-item>
        <n-form-item label="触发类型">
          <n-select v-model:value="form.trigger_type" :options="triggerOptions" placeholder="请选择" style="width: 100%" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitForm" :loading="submitting">确定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 执行结果抽屉 -->
    <n-drawer v-model:show="resultDrawer" :width="600" placement="right">
      <n-drawer-content title="执行结果">
        <n-spin :show="executing">
          <n-input type="textarea" :value="executeResult" :rows="15" readonly placeholder="暂无执行结果" />
        </n-spin>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NSpace, NTag, NIcon, NDrawer, NDrawerContent, NSpin, useMessage } from 'naive-ui'
import { AddOutline, SearchOutline, PlayOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const executing = ref(false)
const taskList = ref([])
const searchKeyword = ref('')
const filterStatus = ref(null)
const dialogVisible = ref(false)
const resultDrawer = ref(false)
const executeResult = ref('')
const dialogTitle = ref('新建任务')

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', trigger_type: 'manual', description: '' })

const statusOptions = [
  { label: '全部', value: null },
  { label: '就绪', value: 'ready' },
  { label: '进行中', value: 'running' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' }
]

const triggerOptions = [
  { label: '手动执行', value: 'manual' },
  { label: '定时触发', value: 'schedule' },
  { label: '事件触发', value: 'event' }
]

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '任务名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '触发类型', key: 'trigger_type', width: 120,
    render: (r) => {
      const map = { manual: '手动', schedule: '定时', event: '事件' }
      return h(NTag, { size: 'small', type: 'info' }, () => map[r.trigger_type] || r.trigger_type)
    }
  },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '状态', key: 'status', width: 100,
    render: (r) => {
      const map = { ready: 'info', running: 'warning', success: 'success', failed: 'error' }
      const text = { ready: '就绪', running: '进行中', success: '成功', failed: '失败' }
      return h(NTag, { size: 'small', type: map[r.status] || 'default' }, () => text[r.status] || r.status)
    }
  },
  { title: '最后执行', key: 'last_run_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 150, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => handleExecute(row) }, () => '执行'),
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
    if (filterStatus.value) params.append('status', filterStatus.value)
    if (searchKeyword.value) params.append('search', searchKeyword.value)
    const res = await fetch(`/api/v1/automation/trigger-rules?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    taskList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载任务失败: ${e.message}`)
    console.error('[automation/task] loadData error:', e)
    taskList.value = []
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  dialogTitle.value = '新建任务'
  Object.assign(form, { id: null, name: '', trigger_type: 'manual', description: '' })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑任务'
  Object.assign(form, { id: row.id, name: row.name, trigger_type: row.trigger_type || 'manual', description: row.description || '' })
  dialogVisible.value = true
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
    console.error('[automation/task] delete error:', e)
  }
}

async function handleExecute(row) {
  executing.value = true
  resultDrawer.value = true
  executeResult.value = ''
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/automation/trigger-rules/${row.id}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    executeResult.value = JSON.stringify(data, null, 2)
    message.success('执行成功')
  } catch (e) {
    executeResult.value = `执行失败: ${e.message}`
    message.error(`执行失败: ${e.message}`)
    console.error('[automation/task] execute error:', e)
  } finally {
    executing.value = false
  }
}

async function submitForm() {
  if (!form.name) {
    message.warning('请填写任务名称')
    return
  }
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
    console.error('[automation/task] submit error:', e)
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
