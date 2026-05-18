<template>
  <div class="page-container">
    <n-card title="创建工单" :bordered="false">
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="120" style="max-width: 800px">
        <n-form-item label="工单标题" path="title">
          <n-input v-model:value="form.title" placeholder="请输入工单标题" maxlength="100" show-count />
        </n-form-item>

        <n-form-item label="优先级" path="priority">
          <n-select v-model:value="form.priority" :options="priorityOptions" placeholder="请选择" style="width: 200px" />
        </n-form-item>

        <n-form-item label="工单类型" path="type">
          <n-select v-model:value="form.type" :options="typeOptions" placeholder="请选择工单类型" style="width: 100%" />
        </n-form-item>

        <n-form-item label="关联设备">
          <n-select v-model:value="form.device_id" :options="deviceOptions" placeholder="请选择关联设备（可选）" style="width: 100%" clearable />
        </n-form-item>

        <n-form-item label="工单描述" path="description">
          <n-input v-model:value="form.description" type="textarea" :rows="6" placeholder="请详细描述工单内容" />
        </n-form-item>

        <n-form-item>
          <n-space>
            <n-button type="primary" @click="submitForm" :loading="submitting">提交工单</n-button>
            <n-button @click="$router.push('/workorder/my')">取消</n-button>
          </n-space>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NForm, NFormItem, NInput, NSelect, NButton, NSpace, useMessage, useDialog } from 'naive-ui'

const router = useRouter()
const message = useMessage()
const submitting = ref(false)
const formRef = ref(null)

const form = reactive({
  title: '',
  priority: 'P3',
  type: '',
  device_id: null,
  description: ''
})

const rules = {
  title: { required: true, message: '请输入工单标题', trigger: 'blur' },
  type: { required: true, message: '请选择工单类型', trigger: 'change' },
  description: { required: true, message: '请输入工单描述', trigger: 'blur' }
}

const priorityOptions = [
  { label: 'P1 - 紧急', value: 'P1' },
  { label: 'P2 - 高', value: 'P2' },
  { label: 'P3 - 中', value: 'P3' },
  { label: 'P4 - 低', value: 'P4' }
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
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    deviceOptions.value = (data.items || []).map(d => ({
      label: `${d.name} (${d.ip_address || d.ip})`,
      value: d.id
    }))
  } catch (e) {
    deviceOptions.value = []
    message.error(`加载设备列表失败: ${e.message}`)
    console.error('[workorder/create] loadDevices error:', e)
  }
}

async function submitForm() {
  submitting.value = true
  try {
    await formRef.value?.validate()
  } catch {
    submitting.value = false
    return
  }

  try {
    const token = localStorage.getItem('token') || ''
    const payload = {
      title: form.title,
      description: form.description,
      priority: form.priority,
      order_type: form.type,
      device_id: form.device_id
    }
    const res = await fetch('/api/v1/workorders/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || `HTTP ${res.status}`)
    }
    message.success('工单提交成功')
    router.push('/workorder/my')
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
