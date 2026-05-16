<template>
  <div>
    <div class="page-header">
      <h2>自动化触发规则</h2>
    </div>

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

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showModal" preset="card" :title="isEdit ? '编辑规则' : '创建触发规则'" style="width:600px">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <n-form-item label="规则名称" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入规则名称" />
        </n-form-item>
        <n-form-item label="触发条件" path="condition">
          <n-input v-model:value="formData.condition" type="textarea" placeholder="如: cpu_usage > 90" :rows="3" />
        </n-form-item>
        <n-form-item label="执行动作" path="action">
          <n-select v-model:value="formData.action" :options="actionOptions" placeholder="选择动作类型" />
        </n-form-item>
        <n-form-item label="动作参数" path="action_params">
          <n-input v-model:value="formData.action_params" type="textarea" placeholder="JSON 格式的动作参数" :rows="3" />
        </n-form-item>
        <n-form-item label="目标设备" path="target_devices">
          <n-select v-model:value="formData.target_devices" :options="deviceOptions" placeholder="选择目标设备" multiple filterable />
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
import { listTriggerRules, createTriggerRule, updateTriggerRule, deleteTriggerRule, testTriggerRule } from '@/api/automation'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const rules = ref([])
const showModal = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const formData = ref({
  name: '', condition: '', action: 'restart_service', action_params: '',
  target_devices: [], enabled: true
})

const formRules = {
  name: { required: true, message: '请输入规则名称', trigger: 'blur' },
  condition: { required: true, message: '请输入触发条件', trigger: 'blur' },
  action: { required: true, message: '请选择执行动作', trigger: 'change' }
}

const actionOptions = [
  { label: '重启服务', value: 'restart_service' },
  { label: '清理磁盘', value: 'clean_disk' },
  { label: '发送告警', value: 'send_alert' },
  { label: '执行脚本', value: 'run_script' },
  { label: '扩容', value: 'scale_up' },
  { label: '切换主备', value: 'failover' }
]

const deviceOptions = ref([
  { label: '所有设备', value: '*' },
  { label: 'web-server-01', value: 'web-server-01' },
  { label: 'db-server-01', value: 'db-server-01' },
  { label: 'cache-server-01', value: 'cache-server-01' }
])

const pagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { pagination.value.page = p; loadRules() },
  onUpdatePageSize: (s) => { pagination.value.pageSize = s; pagination.value.page = 1; loadRules() }
})

const actionLabel = (action) => {
  const opt = actionOptions.find(o => o.value === action)
  return opt ? opt.label : action
}

const columns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '规则名称', key: 'name', width: 180, ellipsis: { tooltip: true } },
  { title: '触发条件', key: 'condition', ellipsis: { tooltip: true } },
  {
    title: '执行动作', key: 'action', width: 120,
    render: (row) => h(NTag, { type: 'info', size: 'small' }, { default: () => actionLabel(row.action) })
  },
  { title: '目标设备', key: 'target_devices', width: 160, render: (row) => (row.target_devices || []).join(', ') || '全部' },
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

const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'

async function loadRules() {
  loading.value = true
  try {
    const res = await listTriggerRules({ page: pagination.value.page, page_size: pagination.value.pageSize })
    const data = res.data || {}
    rules.value = data.items || []
    pagination.value.itemCount = data.total || 0
  } catch (e) {
    message.error('加载规则失败：' + (e.response?.data?.message || e.message))
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  isEdit.value = false
  editingId.value = null
  formData.value = { name: '', condition: '', action: 'restart_service', action_params: '', target_devices: [], enabled: true }
  showModal.value = true
}

function openEditModal(row) {
  isEdit.value = true
  editingId.value = row.id
  formData.value = {
    name: row.name, condition: row.condition, action: row.action,
    action_params: row.action_params || '', target_devices: row.target_devices || [], enabled: row.enabled
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
    await testTriggerRule(row.id)
    message.success('规则测试完成')
  } catch (e) {
    message.error('测试失败：' + (e.response?.data?.message || e.message))
  }
}

onMounted(() => loadRules())
</script>
