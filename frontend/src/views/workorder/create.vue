<template>
  <div class="page-container">
    <n-card title="创建工单" :bordered="false">
      <n-form :model="form" label-placement="left" label-width="120" style="max-width: 800px">
        <n-form-item label="工单标题" required>
          <n-input v-model:value="form.title" placeholder="请输入工单标题" maxlength="100" show-count />
        </n-form-item>

        <n-form-item label="优先级">
          <n-select v-model:value="form.priority" :options="priorityOptions" placeholder="请选择" style="width: 200px" />
        </n-form-item>

        <n-form-item label="工单类型" required>
          <n-select v-model:value="form.type" :options="typeOptions" placeholder="请选择工单类型" style="width: 100%" />
        </n-form-item>

        <n-form-item label="关联设备">
          <n-select v-model:value="form.device_id" :options="deviceOptions" placeholder="请选择关联设备（可选）" style="width: 100%" clearable />
        </n-form-item>

        <n-form-item label="工单描述" required>
          <n-input v-model:value="form.description" type="textarea" :rows="6" placeholder="请详细描述工单内容" />
        </n-form-item>

        <n-form-item>
          <n-space>
            <n-button type="primary" @click="submitForm" :loading="submitting">提交工单</n-button>
            <n-button @click="$router.push('/workorder/list')">取消</n-button>
          </n-space>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NForm, NFormItem, NInput, NSelect, NButton, NSpace, useMessage } from 'naive-ui'

const router = useRouter()
const message = useMessage()
const submitting = ref(false)

const form = reactive({
  title: '',
  priority: 'medium',
  type: '',
  device_id: null,
  description: ''
})

const priorityOptions = [
  { label: '紧急', value: 'urgent' },
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' }
]

const typeOptions = [
  { label: '故障报修', value: 'fault' },
  { label: '需求申请', value: 'requirement' },
  { label: '变更申请', value: 'change' },
  { label: '日常巡检', value: 'inspection' }
]

const deviceOptions = ref([])

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

async function submitForm() {
  if (!form.title) { message.warning('请输入工单标题'); return }
  if (!form.type) { message.warning('请选择工单类型'); return }
  if (!form.description) { message.warning('请输入工单描述'); return }
  submitting.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/workorders/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(form)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || `HTTP ${res.status}`)
    }
    message.success('工单提交成功')
    router.push('/workorder/list')
  } catch (e) {
    message.error(`提交失败: ${e.message}`)
    console.error('[workorder/create] submit error:', e)
  } finally {
    submitting.value = false
  }
}

onMounted(loadDevices)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
