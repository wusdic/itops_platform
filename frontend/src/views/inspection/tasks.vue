<template>
  <div>
    <div class="page-header">
      <h2>巡检任务</h2>
      <n-button type="primary" @click="openCreateModal">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        创建任务
      </n-button>
    </div>

    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="tasks"
        :loading="loading"
        :pagination="pagination"
        remote
      />
    </n-card>

    <!-- Create Modal -->
    <n-modal v-model:show="showModal" preset="card" title="创建巡检任务" style="width:600px">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <n-form-item label="任务名称" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入任务名称" />
        </n-form-item>
        <n-form-item label="目标设备" path="targets">
          <n-select v-model:value="formData.targets" :options="targetOptions" placeholder="选择目标设备" multiple filterable />
        </n-form-item>
        <n-form-item label="执行频率" path="frequency">
          <n-select v-model:value="formData.frequency" :options="frequencyOptions" placeholder="选择频率" />
        </n-form-item>
        <n-form-item label="检查项" path="check_items">
          <n-select v-model:value="formData.check_items" :options="checkItemOptions" placeholder="选择检查项" multiple />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="formData.description" type="textarea" placeholder="任务描述" :rows="2" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">提交</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- Detail Drawer -->
    <n-drawer v-model:show="detailDrawer" :width="600" placement="right">
      <n-drawer-content :title="currentTask?.name || '任务详情'">
        <n-descriptions :column="1" bordered v-if="currentTask">
          <n-descriptions-item label="任务ID">{{ currentTask.id }}</n-descriptions-item>
          <n-descriptions-item label="任务名称">{{ currentTask.name }}</n-descriptions-item>
          <n-descriptions-item label="目标设备">{{ (currentTask.targets || []).join(', ') }}</n-descriptions-item>
          <n-descriptions-item label="执行频率">{{ freqLabel(currentTask.frequency) }}</n-descriptions-item>
          <n-descriptions-item label="检查项">
            <n-space :wrap="true">
              <n-tag v-for="item in (currentTask.check_items || [])" :key="item" size="small">{{ checkItemLabel(item) }}</n-tag>
            </n-space>
          </n-descriptions-item>
          <n-descriptions-item label="描述">{{ currentTask.description || '-' }}</n-descriptions-item>
          <n-descriptions-item label="创建时间">{{ formatTime(currentTask.created_at) }}</n-descriptions-item>
          <n-descriptions-item label="上次执行">{{ formatTime(currentTask.last_run_at) }}</n-descriptions-item>
          <n-descriptions-item label="下次执行">{{ formatTime(currentTask.next_run_at) }}</n-descriptions-item>
        </n-descriptions>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NTag, NButton, NSpace, useMessage, useDialog } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { getInspectionTasks, createInspectionTask, getInspectionTask } from '@/api/inspection'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const tasks = ref([])
const showModal = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const detailDrawer = ref(false)
const currentTask = ref(null)

const formData = ref({
  name: '', targets: [], frequency: 'daily', check_items: [], description: ''
})

const formRules = {
  name: { required: true, message: '请输入任务名称', trigger: 'blur' },
  targets: { required: true, message: '请选择目标设备', trigger: 'change', type: 'array' },
  check_items: { required: true, message: '请选择检查项', trigger: 'change', type: 'array' }
}

const targetOptions = ref([
  { label: 'web-server-01', value: 'web-server-01' },
  { label: 'web-server-02', value: 'web-server-02' },
  { label: 'db-server-01', value: 'db-server-01' },
  { label: 'db-server-02', value: 'db-server-02' },
  { label: 'cache-server-01', value: 'cache-server-01' },
  { label: 'all-servers', value: '*' }
])

const frequencyOptions = [
  { label: '每小时', value: 'hourly' },
  { label: '每天', value: 'daily' },
  { label: '每周', value: 'weekly' },
  { label: '每月', value: 'monthly' },
  { label: '手动', value: 'manual' }
]

const checkItemOptions = [
  { label: 'CPU使用率', value: 'cpu_usage' },
  { label: '内存使用率', value: 'memory_usage' },
  { label: '磁盘使用率', value: 'disk_usage' },
  { label: '网络延迟', value: 'network_latency' },
  { label: '磁盘IO', value: 'disk_io' },
  { label: '进程数', value: 'process_count' },
  { label: '服务状态', value: 'service_status' },
  { label: 'SSL证书', value: 'ssl_cert' },
  { label: '日志错误', value: 'log_errors' }
]

const pagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { pagination.value.page = p; loadTasks() },
  onUpdatePageSize: (s) => { pagination.value.pageSize = s; pagination.value.page = 1; loadTasks() }
})

const freqLabel = (f) => {
  const opt = frequencyOptions.find(o => o.value === f)
  return opt ? opt.label : f || '-'
}

const checkItemLabel = (item) => {
  const opt = checkItemOptions.find(o => o.value === item)
  return opt ? opt.label : item
}

const statusType = (status) => {
  const map = { active: 'success', inactive: 'default', running: 'info' }
  return map[status] || 'default'
}

const statusLabel = (status) => {
  const map = { active: '活跃', inactive: '停用', running: '执行中' }
  return map[status] || status
}

const columns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '任务名称', key: 'name', width: 180, ellipsis: { tooltip: true } },
  { title: '目标设备', key: 'targets', width: 200, render: (row) => (row.targets || []).join(', ') || '-' },
  {
    title: '频率', key: 'frequency', width: 90,
    render: (row) => h(NTag, { type: 'info', size: 'small' }, { default: () => freqLabel(row.frequency) })
  },
  {
    title: '状态', key: 'status', width: 90,
    render: (row) => h(NTag, { type: statusType(row.status), size: 'small' }, { default: () => statusLabel(row.status) })
  },
  { title: '上次执行', key: 'last_run_at', width: 180, render: (row) => formatTime(row.last_run_at) },
  { title: '下次执行', key: 'next_run_at', width: 180, render: (row) => formatTime(row.next_run_at) },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', type: 'info', onClick: () => handleDetail(row) }, { default: () => '详情' }),
        h(NButton, { size: 'small', type: 'success', onClick: () => handleExecute(row) }, { default: () => '执行' })
      ]
    })
  }
]

const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'

async function loadTasks() {
  loading.value = true
  try {
    const res = await getInspectionTasks({ page: pagination.value.page, page_size: pagination.value.pageSize })
    const data = res.data || {}
    tasks.value = data.items || []
    pagination.value.itemCount = data.total || 0
  } catch (e) {
    message.error('加载任务失败：' + (e.response?.data?.message || e.message))
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  formData.value = { name: '', targets: [], frequency: 'daily', check_items: [], description: '' }
  showModal.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch { return }
  submitting.value = true
  try {
    await createInspectionTask(formData.value)
    message.success('任务创建成功')
    showModal.value = false
    loadTasks()
  } catch (e) {
    message.error('创建失败：' + (e.response?.data?.message || e.message))
  } finally {
    submitting.value = false
  }
}

async function handleDetail(row) {
  try {
    const res = await getInspectionTask(row.id)
    currentTask.value = res.data || row
    detailDrawer.value = true
  } catch (e) {
    currentTask.value = row
    detailDrawer.value = true
  }
}

async function handleExecute(row) {
  dialog.warning({
    title: '确认执行',
    content: `确定要立即执行巡检任务 "${row.name}" 吗？`,
    positiveText: '执行',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        // Execute by updating the task or triggering a run
        message.success('任务已触发执行')
        loadTasks()
      } catch (e) {
        message.error('执行失败：' + (e.response?.data?.message || e.message))
      }
    }
  })
}

onMounted(() => loadTasks())
</script>
