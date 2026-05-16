<template>
  <div>
    <div class="page-header">
      <h2>创建工单</h2>
      <n-space>
        <n-button @click="handleSaveDraft" :loading="draftLoading">
          <template #icon><n-icon><SaveOutline /></n-icon></template>保存草稿
        </n-button>
        <n-button type="primary" @click="handleSubmit" :loading="submitLoading">
          <template #icon><n-icon><SendOutline /></n-icon></template>提交工单
        </n-button>
      </n-space>
    </div>

    <n-grid cols="2 s:1" responsive="screen" :x-gap="16" :y-gap="16">
      <!-- Left: Form -->
      <n-gi>
        <n-card title="基本信息" :bordered="false">
          <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="100">
            <n-form-item label="工单标题" path="title">
              <n-input v-model:value="form.title" placeholder="请输入工单标题" maxlength="200" show-count />
            </n-form-item>
            <n-form-item label="工单描述" path="description">
              <n-input v-model:value="form.description" type="textarea" placeholder="请详细描述工单内容" :rows="4" />
            </n-form-item>
            <n-form-item label="工单类型" path="order_type">
              <n-select v-model:value="form.order_type" placeholder="请选择类型" :options="typeOptions" />
            </n-form-item>
            <n-form-item label="优先级" path="priority">
              <n-select v-model:value="form.priority" placeholder="请选择优先级" :options="priorityOptions" />
            </n-form-item>
            <n-form-item label="分类" path="category_id">
              <n-select v-model:value="form.category_id" placeholder="请选择分类" :options="categoryOptions" clearable />
            </n-form-item>
            <n-form-item label="处理人" path="assignee">
              <n-input v-model:value="form.assignee" placeholder="请输入处理人" />
            </n-form-item>
            <n-form-item label="关联设备" path="device_id">
              <n-select v-model:value="form.device_id" placeholder="请选择关联设备" :options="deviceOptions" clearable filterable />
            </n-form-item>
            <n-form-item label="SLA时限(小时)" path="sla_hours">
              <n-input-number v-model:value="form.sla_hours" placeholder="请输入SLA时限" :min="1" :max="720" style="width:100%" />
            </n-form-item>
          </n-form>
        </n-card>
      </n-gi>

      <!-- Right: Attachments & Notes -->
      <n-gi>
        <n-card title="附加信息" :bordered="false">
          <n-form label-placement="left" label-width="100">
            <n-form-item label="影响范围">
              <n-select v-model:value="form.impact" placeholder="请选择影响范围" :options="impactOptions" />
            </n-form-item>
            <n-form-item label="紧急程度">
              <n-select v-model:value="form.urgency" placeholder="请选择紧急程度" :options="urgencyOptions" />
            </n-form-item>
            <n-form-item label="备注">
              <n-input v-model:value="form.notes" type="textarea" placeholder="补充说明" :rows="4" />
            </n-form-item>
          </n-form>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- AI Analysis Buttons -->
    <n-card :bordered="false" style="margin-top:16px">
      <n-space>
        <n-button type="info" @click="handleRootCause" :loading="aiLoading.rootCause">
          <template #icon><n-icon><FlaskOutline /></n-icon></template>AI根因分析
        </n-button>
        <n-button type="warning" @click="handleRemediation" :loading="aiLoading.remediation">
          <template #icon><n-icon><BuildOutline /></n-icon></template>AI修复建议
        </n-button>
      </n-space>
    </n-card>

    <!-- Root Cause Modal -->
    <n-modal v-model:show="rootCauseModal" preset="card" title="AI根因分析" style="max-width:700px">
      <n-spin :show="rootCauseLoading">
        <div v-if="rootCauseResult" style="white-space:pre-wrap">{{ rootCauseResult }}</div>
        <n-empty v-else description="请先填写工单信息后点击AI根因分析" />
      </n-spin>
    </n-modal>

    <!-- Remediation Modal -->
    <n-modal v-model:show="remediationModal" preset="card" title="AI修复建议" style="max-width:700px">
      <n-spin :show="remediationLoading">
        <div v-if="remediationResult" style="white-space:pre-wrap">{{ remediationResult }}</div>
        <n-empty v-else description="请先填写工单信息后点击AI修复建议" />
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { SaveOutline, SendOutline, FlaskOutline, BuildOutline } from '@vicons/ionicons5'
import {
  createWorkorder, saveDraft, analyzeRootCause, analyzeRemediation,
  getWoCategories, getWoPriorities
} from '@/api/workorder'

const router = useRouter()
const message = useMessage()
const formRef = ref(null)

const form = reactive({
  title: '', description: '', order_type: null, priority: null,
  category_id: null, assignee: '', device_id: null, sla_hours: 24,
  impact: null, urgency: null, notes: ''
})

const rules = {
  title: { required: true, message: '请输入工单标题', trigger: 'blur' },
  description: { required: true, message: '请输入工单描述', trigger: 'blur' },
  order_type: { required: true, message: '请选择工单类型', trigger: 'change', type: 'string' },
  priority: { required: true, message: '请选择优先级', trigger: 'change', type: 'string' }
}

const typeOptions = [
  { label: '故障', value: 'incident' },
  { label: '服务请求', value: 'service_request' },
  { label: '变更', value: 'change' },
  { label: '问题', value: 'problem' }
]
const priorityOptions = ref([])
const categoryOptions = ref([])
const deviceOptions = ref([])
const impactOptions = [
  { label: '单个用户', value: 'single' },
  { label: '部门', value: 'department' },
  { label: '全公司', value: 'company' },
  { label: '客户', value: 'customer' }
]
const urgencyOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'urgent' }
]

const draftLoading = ref(false)
const submitLoading = ref(false)

// AI
const aiLoading = reactive({ rootCause: false, remediation: false })
const rootCauseModal = ref(false)
const rootCauseResult = ref('')
const rootCauseLoading = ref(false)
const remediationModal = ref(false)
const remediationResult = ref('')
const remediationLoading = ref(false)

async function loadOptions() {
  try {
    const [catRes, prioRes] = await Promise.allSettled([getWoCategories(), getWoPriorities()])
    if (catRes.status === 'fulfilled') {
      const items = catRes.value.data?.items || catRes.value.data || []
      categoryOptions.value = Array.isArray(items) ? items.map(i => ({ label: i.name || i, value: i.id || i })) : []
    }
    if (prioRes.status === 'fulfilled') {
      const items = prioRes.value.data?.items || prioRes.value.data || []
      priorityOptions.value = Array.isArray(items) ? items.map(i => ({ label: i.name || i, value: i.code || i.id || i })) : []
    }
  } catch {}
}

async function handleSaveDraft() {
  draftLoading.value = true
  try {
    await saveDraft(0, form)
    message.success('草稿已保存')
  } catch { message.error('保存草稿失败') } finally { draftLoading.value = false }
}

async function handleSubmit() {
  try { await formRef.value?.validate() } catch { return }
  submitLoading.value = true
  try {
    await createWorkorder(form)
    message.success('工单创建成功')
    router.push('/workorders')
  } catch { message.error('创建工单失败') } finally { submitLoading.value = false }
}

async function handleRootCause() {
  if (!form.title || !form.description) { message.warning('请先填写标题和描述'); return }
  aiLoading.rootCause = true
  rootCauseLoading.value = true
  rootCauseResult.value = ''
  rootCauseModal.value = true
  try {
    const res = await analyzeRootCause({ title: form.title, description: form.description })
    rootCauseResult.value = res.data?.analysis || res.data?.result || JSON.stringify(res.data, null, 2)
  } catch (e) {
    rootCauseResult.value = '分析失败：' + (e.message || '未知错误')
  } finally { aiLoading.rootCause = false; rootCauseLoading.value = false }
}

async function handleRemediation() {
  if (!form.title || !form.description) { message.warning('请先填写标题和描述'); return }
  aiLoading.remediation = true
  remediationLoading.value = true
  remediationResult.value = ''
  remediationModal.value = true
  try {
    const res = await analyzeRemediation({ title: form.title, description: form.description })
    remediationResult.value = res.data?.analysis || res.data?.result || JSON.stringify(res.data, null, 2)
  } catch (e) {
    remediationResult.value = '分析失败：' + (e.message || '未知错误')
  } finally { aiLoading.remediation = false; remediationLoading.value = false }
}

onMounted(loadOptions)
</script>

<style scoped>
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-header h2 { margin:0; font-size:20px; }
</style>
