<template>
  <div class="page-container">
    <n-card title="触发规则管理" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          新建规则
        </n-button>
      </template>

      <n-space style="margin-bottom: 12px">
        <n-input v-model:value="searchKeyword" placeholder="搜索规则名称" clearable style="width: 200px" @change="loadData">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="filterType" :options="typeOptions" placeholder="规则类型" clearable style="width: 140px" @change="loadData" />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="ruleList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 新建/编辑规则 -->
    <n-modal v-model:show="dialogVisible" preset="card" :title="dialogTitle" style="width: 700px">
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item label="规则名称" required>
          <n-input v-model:value="form.name" placeholder="请输入规则名称" />
        </n-form-item>
        <n-form-item label="规则类型">
          <n-select v-model:value="form.type" :options="typeOptions" placeholder="请选择" style="width: 100%" />
        </n-form-item>
        <n-form-item label="启用状态">
          <n-switch v-model:value="form.enabled" />
        </n-form-item>
        <n-form-item label="条件配置">
          <n-input v-model:value="form.conditions" type="textarea" :rows="4" placeholder="请输入触发条件 (JSON格式)" />
        </n-form-item>
        <n-form-item label="动作配置">
          <n-input v-model:value="form.actions" type="textarea" :rows="4" placeholder="请输入执行动作 (JSON格式)" />
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

    <!-- 测试结果 -->
    <n-modal v-model:show="testDialogVisible" preset="card" title="测试规则" style="width: 600px">
      <n-spin :show="testing">
        <n-input type="textarea" :value="testResult" :rows="15" readonly placeholder="暂无测试结果" />
      </n-spin>
      <template #footer>
        <n-space justify="end">
          <n-button @click="testDialogVisible = false">关闭</n-button>
          <n-button type="primary" @click="handleTest" :loading="testing">重新测试</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NSpace, NTag, NIcon, NSwitch, NSpin, useMessage } from 'naive-ui'
import { AddOutline, SearchOutline, PlayOutline, RefreshOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const testing = ref(false)
const ruleList = ref([])
const searchKeyword = ref('')
const filterType = ref(null)
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const dialogTitle = ref('新建规则')
const testResult = ref('')
const currentTestRule = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', type: 'threshold', enabled: true, conditions: '', actions: '', description: '' })

const typeOptions = [
  { label: '阈值触发', value: 'threshold' },
  { label: '趋势触发', value: 'trend' },
  { label: '异常触发', value: 'anomaly' },
  { label: '周期触发', value: 'periodic' }
]

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '规则名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '类型', key: 'type', width: 120,
    render: (r) => {
      const typeMap = { threshold: '阈值触发', trend: '趋势触发', anomaly: '异常触发', periodic: '周期触发' }
      return h(NTag, { size: 'small', type: 'info' }, () => typeMap[r.type] || r.type || '-')
    }
  },
  { title: '启用状态', key: 'enabled', width: 100,
    render: (r) => h(NTag, { size: 'small', type: r.enabled ? 'success' : 'default' }, () => r.enabled ? '启用' : '停用')
  },
  { title: '条件数', key: 'conditions_count', width: 90,
    render: (r) => h('span', {}, Array.isArray(r.conditions) ? r.conditions.length : (r.conditions ? '1' : '0'))
  },
  { title: '动作数', key: 'actions_count', width: 90,
    render: (r) => h('span', {}, Array.isArray(r.actions) ? r.actions.length : (r.actions ? '1' : '0'))
  },
  { title: '创建时间', key: 'created_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 220, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', onClick: () => handleTestRule(row) }, () => '测试'),
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
    ruleList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载规则失败: ${e.message}`)
    console.error('[automation/script] loadData error:', e)
    ruleList.value = []
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  dialogTitle.value = '新建规则'
  Object.assign(form, { id: null, name: '', type: 'threshold', enabled: true, conditions: '', actions: '', description: '' })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑规则'
  Object.assign(form, {
    id: row.id,
    name: row.name,
    type: row.type || 'threshold',
    enabled: row.enabled ?? true,
    conditions: typeof row.conditions === 'string' ? row.conditions : JSON.stringify(row.conditions, null, 2),
    actions: typeof row.actions === 'string' ? row.actions : JSON.stringify(row.actions, null, 2),
    description: row.description || ''
  })
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
    console.error('[automation/script] delete error:', e)
  }
}

async function handleTestRule(row) {
  currentTestRule.value = row
  testDialogVisible.value = true
  testResult.value = ''
  await handleTest()
}

async function handleTest() {
  if (!currentTestRule.value) return
  testing.value = true
  testResult.value = ''
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/automation/trigger-rules/${currentTestRule.value.id}/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    testResult.value = JSON.stringify(data, null, 2)
  } catch (e) {
    testResult.value = `测试失败: ${e.message}`
    message.error(`测试失败: ${e.message}`)
    console.error('[automation/script] test error:', e)
  } finally {
    testing.value = false
  }
}

async function submitForm() {
  if (!form.name) { message.warning('请填写规则名称'); return }
  submitting.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const method = form.id ? 'PUT' : 'POST'
    const url = form.id ? `/api/v1/automation/trigger-rules/${form.id}` : '/api/v1/automation/trigger-rules'
    
    // Parse conditions and actions if they're JSON strings
    let payload = { ...form }
    try {
      if (payload.conditions) {
        const parsed = JSON.parse(payload.conditions)
        payload.conditions = parsed
      }
    } catch { /* keep as string if not valid JSON */ }
    try {
      if (payload.actions) {
        const parsed = JSON.parse(payload.actions)
        payload.actions = parsed
      }
    } catch { /* keep as string if not valid JSON */ }
    
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
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

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
