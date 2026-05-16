<template>
  <div>
    <div class="page-header">
      <h2>告警规则</h2>
    </div>

    <n-tabs v-model:value="activeTab" type="line">
      <n-tab-pane name="rules" tab="规则列表">
        <n-card :bordered="false" style="margin-bottom:16px">
          <n-space>
            <n-button type="primary" @click="openCreateModal">
              <template #icon><n-icon><AddOutline /></n-icon></template>
              创建规则
            </n-button>
          </n-space>
        </n-card>

        <n-card :bordered="false">
          <n-data-table
            :columns="columns"
            :data="rules"
            :loading="loading"
            :pagination="pagination"
            remote
          />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="events" tab="触发事件">
        <n-card :bordered="false">
          <n-data-table
            :columns="eventColumns"
            :data="events"
            :loading="eventsLoading"
            :pagination="eventPagination"
            remote
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showModal" preset="card" :title="isEdit ? '编辑规则' : '创建告警规则'" style="width:600px">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <n-form-item label="规则名称" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入规则名称" />
        </n-form-item>
        <n-form-item label="监控指标" path="metric">
          <n-input v-model:value="formData.metric" placeholder="如: cpu_usage" />
        </n-form-item>
        <n-form-item label="条件" path="condition">
          <n-select v-model:value="formData.condition" :options="conditionOptions" placeholder="选择条件" />
        </n-form-item>
        <n-form-item label="阈值" path="threshold">
          <n-input-number v-model:value="formData.threshold" :min="0" style="width:100%" />
        </n-form-item>
        <n-form-item label="告警级别" path="level">
          <n-select v-model:value="formData.level" :options="levelOptions" placeholder="选择级别" />
        </n-form-item>
        <n-form-item label="通知方式" path="notify_method">
          <n-select v-model:value="formData.notify_method" :options="notifyOptions" placeholder="选择通知方式" multiple />
        </n-form-item>
        <n-form-item label="是否启用" path="enabled">
          <n-switch v-model:value="formData.enabled" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">提交</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NTag, NButton, NSpace, NSwitch, useMessage, useDialog } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { getAlertRules, createTriggerRule, updateTriggerRule, deleteTriggerRule, testTriggerRule, getTriggerEvents } from '@/api/monitoring'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const rules = ref([])
const activeTab = ref('rules')

const eventsLoading = ref(false)
const events = ref([])

const showModal = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const formData = ref({
  name: '', metric: '', condition: '>', threshold: 80, level: 'medium',
  notify_method: [], enabled: true
})

const formRules = {
  name: { required: true, message: '请输入规则名称', trigger: 'blur' },
  metric: { required: true, message: '请输入监控指标', trigger: 'blur' },
  condition: { required: true, message: '请选择条件', trigger: 'change' },
  threshold: { required: true, type: 'number', message: '请输入阈值', trigger: 'blur' },
  level: { required: true, message: '请选择级别', trigger: 'change' }
}

const conditionOptions = [
  { label: '大于 (>)', value: '>' },
  { label: '小于 (<)', value: '<' },
  { label: '等于 (=)', value: '=' },
  { label: '大于等于 (>=)', value: '>=' },
  { label: '小于等于 (<=)', value: '<=' }
]

const levelOptions = [
  { label: 'Critical', value: 'critical' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
  { label: 'Info', value: 'info' }
]

const notifyOptions = [
  { label: '邮件', value: 'email' },
  { label: '短信', value: 'sms' },
  { label: 'Webhook', value: 'webhook' },
  { label: '企业微信', value: 'wecom' },
  { label: '钉钉', value: 'dingtalk' }
]

const pagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { pagination.value.page = p; loadRules() },
  onUpdatePageSize: (s) => { pagination.value.pageSize = s; pagination.value.page = 1; loadRules() }
})

const eventPagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { eventPagination.value.page = p; loadEvents() },
  onUpdatePageSize: (s) => { eventPagination.value.pageSize = s; eventPagination.value.page = 1; loadEvents() }
})

const levelTagType = (level) => {
  const map = { critical: 'error', high: 'error', medium: 'warning', low: 'info', info: 'info' }
  return map[level] || 'default'
}

const levelLabel = (level) => {
  const map = { critical: '严重', high: '高', medium: '中', low: '低', info: '信息' }
  return map[level] || level
}

const columns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '规则名称', key: 'name', width: 180, ellipsis: { tooltip: true } },
  { title: '指标', key: 'metric', width: 140 },
  {
    title: '条件', key: 'condition', width: 100,
    render: (row) => `${row.condition} ${row.threshold}`
  },
  {
    title: '级别', key: 'level', width: 90,
    render: (row) => h(NTag, { type: levelTagType(row.level), size: 'small' }, { default: () => levelLabel(row.level) })
  },
  {
    title: '通知方式', key: 'notify_method', width: 160,
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => (row.notify_method || []).map(m => h(NTag, { size: 'small', type: 'info' }, { default: () => m }))
    })
  },
  {
    title: '状态', key: 'enabled', width: 80,
    render: (row) => h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' }, { default: () => row.enabled ? '启用' : '禁用' })
  },
  { title: '创建时间', key: 'created_at', width: 180, render: (row) => formatTime(row.created_at) },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', type: 'primary', onClick: () => openEditModal(row) }, { default: () => '编辑' }),
        h(NButton, { size: 'small', type: 'info', onClick: () => handleTest(row) }, { default: () => '测试' }),
        h(NButton, { size: 'small', type: 'error', ghost: true, onClick: () => handleDelete(row) }, { default: () => '删除' })
      ]
    })
  }
]

const eventColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '规则名称', key: 'rule_name', width: 180, ellipsis: { tooltip: true } },
  { title: '触发指标', key: 'metric', width: 140 },
  { title: '触发值', key: 'triggered_value', width: 100 },
  {
    title: '级别', key: 'level', width: 90,
    render: (row) => h(NTag, { type: levelTagType(row.level), size: 'small' }, { default: () => levelLabel(row.level) })
  },
  { title: '消息', key: 'message', ellipsis: { tooltip: true } },
  { title: '触发时间', key: 'triggered_at', width: 180, render: (row) => formatTime(row.triggered_at) }
]

const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'

async function loadRules() {
  loading.value = true
  try {
    const res = await getAlertRules({ page: pagination.value.page, page_size: pagination.value.pageSize })
    const data = res.data || {}
    rules.value = data.items || []
    pagination.value.itemCount = data.total || 0
  } catch (e) {
    message.error('加载规则失败：' + (e.response?.data?.message || e.message))
  } finally {
    loading.value = false
  }
}

async function loadEvents() {
  eventsLoading.value = true
  try {
    const res = await getTriggerEvents({ page: eventPagination.value.page, page_size: eventPagination.value.pageSize })
    const data = res.data || {}
    events.value = data.items || []
    eventPagination.value.itemCount = data.total || 0
  } catch (e) {
    message.error('加载触发事件失败：' + (e.response?.data?.message || e.message))
  } finally {
    eventsLoading.value = false
  }
}

function openCreateModal() {
  isEdit.value = false
  editingId.value = null
  formData.value = { name: '', metric: '', condition: '>', threshold: 80, level: 'medium', notify_method: [], enabled: true }
  showModal.value = true
}

function openEditModal(row) {
  isEdit.value = true
  editingId.value = row.id
  formData.value = {
    name: row.name, metric: row.metric, condition: row.condition,
    threshold: row.threshold, level: row.level,
    notify_method: row.notify_method || [], enabled: row.enabled
  }
  showModal.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch { return }
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateTriggerRule(editingId.value, formData.value)
      message.success('规则更新成功')
    } else {
      await createTriggerRule(formData.value)
      message.success('规则创建成功')
    }
    showModal.value = false
    loadRules()
  } catch (e) {
    message.error('提交失败：' + (e.response?.data?.message || e.message))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除规则 "${row.name}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteTriggerRule(row.id)
        message.success('删除成功')
        loadRules()
      } catch (e) {
        message.error('删除失败：' + (e.response?.data?.message || e.message))
      }
    }
  })
}

async function handleTest(row) {
  try {
    await testTriggerRule(row.id, { test_value: row.threshold })
    message.success('规则测试完成')
  } catch (e) {
    message.error('测试失败：' + (e.response?.data?.message || e.message))
  }
}

onMounted(() => { loadRules(); loadEvents() })
</script>
