<template>
  <div>
    <div class="page-header">
      <h2>发现任务</h2>
      <n-button type="primary" @click="openTaskModal()">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        创建任务
      </n-button>
    </div>

    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
        remote
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </n-card>

    <!-- 创建任务弹窗 -->
    <n-modal v-model:show="taskModalVisible" preset="card" title="创建发现任务" style="width:560px">
      <n-form ref="taskFormRef" :model="taskForm" :rules="taskFormRules" label-placement="left" label-width="100">
        <n-form-item label="任务名称" path="name">
          <n-input v-model:value="taskForm.name" placeholder="请输入任务名称" />
        </n-form-item>
        <n-form-item label="扫描类型" path="scan_type">
          <n-select v-model:value="taskForm.scan_type" :options="scanTypeOptions" />
        </n-form-item>
        <n-form-item label="IP范围" path="ip_range">
          <n-input v-model:value="taskForm.ip_range" placeholder="如: 192.168.1.1-254" />
        </n-form-item>
        <n-form-item label="端口">
          <n-input v-model:value="taskForm.ports" placeholder="如: 22,80,443" />
        </n-form-item>
        <n-form-item label="Community" v-if="taskForm.scan_type === 'snmp'">
          <n-input v-model:value="taskForm.community" placeholder="如: public" />
        </n-form-item>
        <n-form-item label="周期">
          <n-select v-model:value="taskForm.schedule" :options="scheduleOptions" clearable placeholder="可选" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="taskForm.description" type="textarea" placeholder="请输入描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="taskModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="taskSubmitLoading" @click="handleTaskSubmit">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 任务详情弹窗 -->
    <n-modal v-model:show="detailVisible" preset="card" title="任务详情" style="width:640px">
      <n-descriptions :column="2" bordered v-if="detailTask">
        <n-descriptions-item label="任务名称">{{ detailTask.name }}</n-descriptions-item>
        <n-descriptions-item label="扫描类型">{{ detailTask.scan_type }}</n-descriptions-item>
        <n-descriptions-item label="IP范围">{{ detailTask.ip_range }}</n-descriptions-item>
        <n-descriptions-item label="端口">{{ detailTask.ports || '-' }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="taskStatusType(detailTask.status)" size="small">{{ taskStatusLabel(detailTask.status) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="已发现">{{ detailTask.found_count || 0 }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ detailTask.created_at ? dayjs(detailTask.created_at).format('YYYY-MM-DD HH:mm') : '-' }}</n-descriptions-item>
        <n-descriptions-item label="周期">{{ detailTask.schedule || '不重复' }}</n-descriptions-item>
        <n-descriptions-item label="描述" :span="2">{{ detailTask.description || '-' }}</n-descriptions-item>
      </n-descriptions>
      <template #footer>
        <n-space justify="end">
          <n-button @click="detailVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { AddOutline, PlayOutline, EyeOutline, TrashOutline } from '@vicons/ionicons5'
import { createDiscoveryTask, listDiscoveryTasks, getScanStatus } from '@/api/discovery'
import dayjs from 'dayjs'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const taskModalVisible = ref(false)
const taskSubmitLoading = ref(false)
const taskFormRef = ref(null)

const tableData = ref([])
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const taskForm = reactive({
  name: '', scan_type: 'ip', ip_range: '', ports: '',
  community: '', schedule: null, description: ''
})
const taskFormRules = {
  name: { required: true, message: '请输入任务名称', trigger: 'blur' },
  ip_range: { required: true, message: '请输入IP范围', trigger: 'blur' }
}

const scanTypeOptions = [
  { label: 'IP扫描', value: 'ip' },
  { label: 'SNMP扫描', value: 'snmp' }
]

const scheduleOptions = [
  { label: '每小时', value: 'hourly' },
  { label: '每天', value: 'daily' },
  { label: '每周', value: 'weekly' },
  { label: '每月', value: 'monthly' }
]

const taskStatusType = (s) => {
  const map = { running: 'info', completed: 'success', failed: 'error', pending: 'warning', stopped: 'default' }
  return map[s] || 'default'
}
const taskStatusLabel = (s) => {
  const map = { running: '运行中', completed: '已完成', failed: '失败', pending: '等待中', stopped: '已停止' }
  return map[s] || s
}

const columns = [
  { title: '任务名称', key: 'name' },
  { title: '类型', key: 'scan_type', width: 100, render: row => row.scan_type === 'snmp' ? 'SNMP' : 'IP' },
  { title: 'IP范围', key: 'ip_range', width: 200 },
  {
    title: '状态', key: 'status', width: 100,
    render: row => h('n-tag', { type: taskStatusType(row.status), size: 'small' }, { default: () => taskStatusLabel(row.status) })
  },
  { title: '已发现', key: 'found_count', width: 100 },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: row => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render: row => h('n-space', null, { default: () => [
      h('n-button', { size: 'small', quaternary: true, type: 'success', onClick: () => handleExecute(row) }, { icon: () => h('n-icon', null, { default: () => h(PlayOutline) }), default: () => '执行' }),
      h('n-button', { size: 'small', quaternary: true, type: 'info', onClick: () => handleDetail(row) }, { icon: () => h('n-icon', null, { default: () => h(EyeOutline) }), default: () => '详情' }),
      h('n-button', { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, { icon: () => h('n-icon', null, { default: () => h(TrashOutline) }), default: () => '删除' })
    ]})
  }
]

const detailVisible = ref(false)
const detailTask = ref(null)

async function loadData(page) {
  if (page) pagination.page = page
  loading.value = true
  try {
    const res = await listDiscoveryTasks({ page: pagination.page, page_size: pagination.pageSize })
    tableData.value = res.items || res.data?.items || []
    pagination.itemCount = res.total || res.data?.total || 0
  } catch (e) {
    message.error('加载任务列表失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handlePageChange(p) { loadData(p) }
function handlePageSizeChange(ps) { pagination.pageSize = ps; pagination.page = 1; loadData() }

function openTaskModal() {
  Object.assign(taskForm, { name: '', scan_type: 'ip', ip_range: '', ports: '', community: '', schedule: null, description: '' })
  taskModalVisible.value = true
}

async function handleTaskSubmit() {
  try {
    await taskFormRef.value?.validate()
    taskSubmitLoading.value = true
    await createDiscoveryTask({ ...taskForm })
    message.success('任务创建成功')
    taskModalVisible.value = false
    loadData()
  } catch (e) {
    if (e.errors) return
    message.error('创建失败')
    console.error(e)
  } finally {
    taskSubmitLoading.value = false
  }
}

async function handleExecute(row) {
  try {
    message.success('任务已开始执行')
    loadData()
  } catch (e) {
    message.error('执行失败')
    console.error(e)
  }
}

async function handleDetail(row) {
  detailTask.value = row
  detailVisible.value = true
  try {
    const res = await getScanStatus(row.id)
    Object.assign(detailTask.value, res.data || res)
  } catch (e) {
    console.error(e)
  }
}

function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除任务「${row.name}」吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      message.success('删除成功')
      loadData()
    }
  })
}

onMounted(() => { loadData() })
</script>
