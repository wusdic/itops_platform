<template>
  <div>
    <div class="page-header">
      <h2>工单详情</h2>
      <n-space>
        <n-button @click="handleExportSingle" :loading="exportLoading">
          <template #icon><n-icon><DownloadOutline /></n-icon></template>导出
        </n-button>
        <n-button type="primary" @click="router.push('/workorders')">返回</n-button>
      </n-space>
    </div>

    <n-grid cols="2 s:1" responsive="screen" :x-gap="16" :y-gap="16">
      <!-- Basic Info -->
      <n-gi>
        <n-card title="基本信息" :bordered="false">
          <n-descriptions :column="2" bordered>
            <n-descriptions-item label="工单号">{{ detail.order_no || '-' }}</n-descriptions-item>
            <n-descriptions-item label="标题">{{ detail.title || '-' }}</n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="statusType(detail.status)" size="small">{{ statusLabel(detail.status) }}</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="优先级">
              <n-tag :type="priorityType(detail.priority)" size="small">{{ detail.priority || '-' }}</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="类型">{{ typeLabel(detail.order_type) }}</n-descriptions-item>
            <n-descriptions-item label="分类">{{ detail.category_name || '-' }}</n-descriptions-item>
            <n-descriptions-item label="创建人">{{ detail.creator || '-' }}</n-descriptions-item>
            <n-descriptions-item label="处理人">{{ detail.assignee || '-' }}</n-descriptions-item>
            <n-descriptions-item label="关联设备">{{ detail.device_name || '-' }}</n-descriptions-item>
            <n-descriptions-item label="创建时间">{{ formatDate(detail.created_at) }}</n-descriptions-item>
            <n-descriptions-item label="更新时间">{{ formatDate(detail.updated_at) }}</n-descriptions-item>
            <n-descriptions-item label="解决时间">{{ formatDate(detail.resolved_at) }}</n-descriptions-item>
            <n-descriptions-item label="描述" :span="2">{{ detail.description || '-' }}</n-descriptions-item>
            <n-descriptions-item label="备注" :span="2">{{ detail.notes || '-' }}</n-descriptions-item>
          </n-descriptions>
        </n-card>
      </n-gi>

      <!-- SLA Status -->
      <n-gi>
        <n-card title="SLA状态" :bordered="false">
          <n-descriptions :column="2" bordered>
            <n-descriptions-item label="SLA时限">{{ slaData.sla_hours || '-' }}小时</n-descriptions-item>
            <n-descriptions-item label="剩余时间">
              <n-tag :type="slaStatusType">{{ slaRemaining }}</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag :type="slaStatusType">{{ slaData.status || '-' }}</n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="升级次数">{{ slaData.escalation_count || 0 }}</n-descriptions-item>
          </n-descriptions>
        </n-card>

        <!-- Actions -->
        <n-card title="操作" :bordered="false" style="margin-top:16px">
          <n-space :wrap="true">
            <n-button @click="openAssign">分配</n-button>
            <n-button @click="openApprove">审批</n-button>
            <n-button @click="openResolve">解决</n-button>
            <n-button @click="openClose" type="warning">关闭</n-button>
            <n-button @click="handleCancel" type="error">取消</n-button>
          </n-space>
          <n-space style="margin-top:12px">
            <n-button type="info" @click="handleRootCause" :loading="aiLoading.rootCause">AI根因分析</n-button>
            <n-button type="warning" @click="handleRemediation" :loading="aiLoading.remediation">AI修复建议</n-button>
            <n-button @click="openFlowModal">添加流程记录</n-button>
          </n-space>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Flow History -->
    <n-card title="流程历史" :bordered="false" style="margin-top:16px">
      <n-timeline v-if="flows.length">
        <n-timeline-item v-for="f in flows" :key="f.id"
          :type="flowType(f.action)" :title="flowLabel(f.action)"
          :content="f.comment || f.description || ''"
          :time="formatDate(f.created_at)"
          :line-type="f.is_latest ? 'default' : 'default'" />
      </n-timeline>
      <n-empty v-else description="暂无流程记录" />
    </n-card>

    <!-- SLA History -->
    <n-card title="升级历史" :bordered="false" style="margin-top:16px">
      <n-timeline v-if="slaHistory.length">
        <n-timeline-item v-for="s in slaHistory" :key="s.id"
          type="warning" :title="s.action || 'SLA升级'"
          :content="s.description || ''"
          :time="formatDate(s.created_at)" />
      </n-timeline>
      <n-empty v-else description="暂无升级记录" />
    </n-card>

    <!-- Assign Modal -->
    <n-modal v-model:show="assignModalShow" preset="dialog" title="分配工单">
      <n-form style="margin-top:16px">
        <n-form-item label="处理人">
          <n-input v-model:value="assignForm.assignee" placeholder="请输入处理人" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="assignModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleAssign" :loading="assignLoading">确认</n-button>
      </template>
    </n-modal>

    <!-- Approve Modal -->
    <n-modal v-model:show="approveModalShow" preset="dialog" title="审批工单">
      <n-form style="margin-top:16px">
        <n-form-item label="审批意见">
          <n-input v-model:value="approveForm.comment" type="textarea" :rows="3" placeholder="请输入审批意见" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="approveModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleApprove" :loading="approveLoading">通过</n-button>
      </template>
    </n-modal>

    <!-- Resolve Modal -->
    <n-modal v-model:show="resolveModalShow" preset="dialog" title="解决工单">
      <n-form style="margin-top:16px">
        <n-form-item label="解决方案">
          <n-input v-model:value="resolveForm.solution" type="textarea" :rows="3" placeholder="请输入解决方案" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="resolveModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleResolve" :loading="resolveLoading">确认解决</n-button>
      </template>
    </n-modal>

    <!-- Close Modal -->
    <n-modal v-model:show="closeModalShow" preset="dialog" title="关闭工单">
      <n-form style="margin-top:16px">
        <n-form-item label="关闭原因">
          <n-input v-model:value="closeForm.reason" type="textarea" :rows="3" placeholder="请输入关闭原因" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button @click="closeModalShow = false">取消</n-button>
        <n-button type="warning" @click="handleClose" :loading="closeLoading">确认关闭</n-button>
      </template>
    </n-modal>

    <!-- Add Flow Modal -->
    <n-modal v-model:show="flowModalShow" preset="card" title="添加流程记录" style="max-width:600px">
      <n-form :model="flowForm">
        <n-form-item label="操作类型">
          <n-select v-model:value="flowForm.action" :options="actionOptions" />
        </n-form-item>
        <n-form-item label="说明">
          <n-input v-model:value="flowForm.comment" type="textarea" :rows="3" placeholder="请输入说明" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="flowModalShow = false">取消</n-button>
        <n-button type="primary" @click="handleAddFlow" :loading="flowLoading">确认</n-button>
      </template>
    </n-modal>

    <!-- Root Cause Modal -->
    <n-modal v-model:show="rootCauseModal" preset="card" title="AI根因分析" style="max-width:700px">
      <n-spin :show="rootCauseLoading">
        <div v-if="rootCauseResult" style="white-space:pre-wrap">{{ rootCauseResult }}</div>
        <n-empty v-else description="暂无分析结果" />
      </n-spin>
    </n-modal>

    <!-- Remediation Modal -->
    <n-modal v-model:show="remediationModal" preset="card" title="AI修复建议" style="max-width:700px">
      <n-spin :show="remediationLoading">
        <div v-if="remediationResult" style="white-space:pre-wrap">{{ remediationResult }}</div>
        <n-empty v-else description="暂无建议结果" />
      </n-spin>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { DownloadOutline } from '@vicons/ionicons5'
import {
  getWorkorder, getWorkorderFlows, createWorkorderFlow,
  getWoSla, getSlaHistory, startSlaTimer,
  assignWorkorder, approveWorkorder, resolveWorkorder,
  closeWorkorder, cancelWorkorder, exportSingleWorkorder,
  analyzeRootCause, analyzeRemediation
} from '@/api/workorder'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const woId = computed(() => route.params.id)

// Detail
const detail = ref({})
const flows = ref([])

// SLA
const slaData = ref({})
const slaHistory = ref([])
const slaRemaining = computed(() => {
  if (!slaData.value.remaining_seconds && slaData.value.remaining_seconds !== 0) return '-'
  const s = slaData.value.remaining_seconds
  if (s < 0) return '已超时'
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}小时${m}分钟`
})
const slaStatusType = computed(() => {
  if (slaData.value.remaining_seconds < 0) return 'error'
  if (slaData.value.remaining_seconds < 3600) return 'warning'
  return 'success'
})

// Helper
const formatDate = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'
const statusType = (s) => ({ pending: 'warning', in_progress: 'info', resolved: 'success', closed: 'default', cancelled: 'error' }[s] || 'default')
const statusLabel = (s) => ({ pending: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭', cancelled: '已取消' }[s] || s)
const priorityType = (p) => ({ P1: 'error', P2: 'warning', P3: 'info', P4: 'default' }[p] || 'default')
const typeLabel = (t) => ({ incident: '故障', service_request: '服务请求', change: '变更', problem: '问题' }[t] || t)
const flowType = (a) => ({ assign: 'info', approve: 'success', resolve: 'success', close: 'default', cancel: 'error', comment: 'info' }[a] || 'default')
const flowLabel = (a) => ({ assign: '分配', approve: '审批', resolve: '解决', close: '关闭', cancel: '取消', comment: '备注' }[a] || a)

const actionOptions = [
  { label: '备注', value: 'comment' },
  { label: '分配', value: 'assign' },
  { label: '升级', value: 'escalate' }
]

// Modals
const assignModalShow = ref(false)
const assignForm = reactive({ assignee: '' })
const assignLoading = ref(false)

const approveModalShow = ref(false)
const approveForm = reactive({ comment: '' })
const approveLoading = ref(false)

const resolveModalShow = ref(false)
const resolveForm = reactive({ solution: '' })
const resolveLoading = ref(false)

const closeModalShow = ref(false)
const closeForm = reactive({ reason: '' })
const closeLoading = ref(false)

const flowModalShow = ref(false)
const flowForm = reactive({ action: 'comment', comment: '' })
const flowLoading = ref(false)

const exportLoading = ref(false)

// AI
const aiLoading = reactive({ rootCause: false, remediation: false })
const rootCauseModal = ref(false)
const rootCauseResult = ref('')
const rootCauseLoading = ref(false)
const remediationModal = ref(false)
const remediationResult = ref('')
const remediationLoading = ref(false)

function openAssign() { assignForm.assignee = ''; assignModalShow.value = true }
function openApprove() { approveForm.comment = ''; approveModalShow.value = true }
function openResolve() { resolveForm.solution = ''; resolveModalShow.value = true }
function openClose() { closeForm.reason = ''; closeModalShow.value = true }
function openFlowModal() { flowForm.action = 'comment'; flowForm.comment = ''; flowModalShow.value = true }

async function loadData() {
  try {
    const [woRes, flowRes, slaRes, slaHistRes] = await Promise.allSettled([
      getWorkorder(woId.value),
      getWorkorderFlows(woId.value),
      getWoSla(woId.value),
      getSlaHistory(woId.value)
    ])
    if (woRes.status === 'fulfilled') detail.value = woRes.value.data || {}
    if (flowRes.status === 'fulfilled') flows.value = flowRes.value.data?.items || flowRes.value.data || []
    if (slaRes.status === 'fulfilled') slaData.value = slaRes.value.data || {}
    if (slaHistRes.status === 'fulfilled') slaHistory.value = slaHistRes.value.data?.items || slaHistRes.value.data || []
  } catch (e) {
    message.error('加载工单详情失败')
  }
}

async function handleAssign() {
  if (!assignForm.assignee) { message.warning('请输入处理人'); return }
  assignLoading.value = true
  try {
    await assignWorkorder(woId.value, assignForm)
    message.success('分配成功'); assignModalShow.value = false; loadData()
  } catch { message.error('分配失败') } finally { assignLoading.value = false }
}

async function handleApprove() {
  approveLoading.value = true
  try {
    await approveWorkorder(woId.value, approveForm)
    message.success('审批通过'); approveModalShow.value = false; loadData()
  } catch { message.error('审批失败') } finally { approveLoading.value = false }
}

async function handleResolve() {
  if (!resolveForm.solution) { message.warning('请输入解决方案'); return }
  resolveLoading.value = true
  try {
    await resolveWorkorder(woId.value, resolveForm)
    message.success('已解决'); resolveModalShow.value = false; loadData()
  } catch { message.error('操作失败') } finally { resolveLoading.value = false }
}

async function handleClose() {
  if (!closeForm.reason) { message.warning('请输入关闭原因'); return }
  closeLoading.value = true
  try {
    await closeWorkorder(woId.value, closeForm)
    message.success('已关闭'); closeModalShow.value = false; loadData()
  } catch { message.error('操作失败') } finally { closeLoading.value = false }
}

async function handleCancel() {
  try {
    await cancelWorkorder(woId.value, { reason: '手动取消' })
    message.success('已取消'); loadData()
  } catch { message.error('操作失败') }
}

async function handleAddFlow() {
  if (!flowForm.comment) { message.warning('请输入说明'); return }
  flowLoading.value = true
  try {
    await createWorkorderFlow(woId.value, flowForm)
    message.success('添加成功'); flowModalShow.value = false; loadData()
  } catch { message.error('添加失败') } finally { flowLoading.value = false }
}

async function handleExportSingle() {
  exportLoading.value = true
  try {
    const res = await exportSingleWorkorder(woId.value)
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `工单_${woId.value}.pdf`; a.click()
    URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch { message.error('导出失败') } finally { exportLoading.value = false }
}

async function handleRootCause() {
  aiLoading.rootCause = true; rootCauseLoading.value = true; rootCauseResult.value = ''
  rootCauseModal.value = true
  try {
    const res = await analyzeRootCause({ id: woId.value, title: detail.value.title, description: detail.value.description })
    rootCauseResult.value = res.data?.analysis || res.data?.result || JSON.stringify(res.data, null, 2)
  } catch (e) { rootCauseResult.value = '分析失败：' + (e.message || '未知错误') }
  finally { aiLoading.rootCause = false; rootCauseLoading.value = false }
}

async function handleRemediation() {
  aiLoading.remediation = true; remediationLoading.value = true; remediationResult.value = ''
  remediationModal.value = true
  try {
    const res = await analyzeRemediation({ id: woId.value, title: detail.value.title, description: detail.value.description })
    remediationResult.value = res.data?.analysis || res.data?.result || JSON.stringify(res.data, null, 2)
  } catch (e) { remediationResult.value = '分析失败：' + (e.message || '未知错误') }
  finally { aiLoading.remediation = false; remediationLoading.value = false }
}

onMounted(() => { loadData(); startSlaTimer(woId.value).catch(() => {}) })
</script>

<style scoped>
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-header h2 { margin:0; font-size:20px; }
</style>
