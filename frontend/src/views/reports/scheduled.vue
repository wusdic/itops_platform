<template>
  <div>
    <div class="page-header">
      <h2>定时报表</h2>
      <n-button type="primary" @click="openCreate">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        新建定时任务
      </n-button>
    </div>

    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="schedules"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 创建/编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card"
      :title="isEdit ? '编辑定时任务' : '新建定时任务'"
      style="width: 560px" :bordered="false">
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item label="模板" required>
          <n-select v-model:value="form.template_id" :options="templateOptions"
            placeholder="选择报表模板" />
        </n-form-item>
        <n-form-item label="时间表达式" required>
          <n-input v-model:value="form.cron_expression"
            placeholder="Cron表达式，如 0 9 * * 1-5" />
          <n-p style="color: #999; margin-top: 4px; font-size: 12px">
            格式: 分 时 日 月 星期，例：0 9 * * 1-5 表示工作日每天9点
          </n-p>
        </n-form-item>
        <n-form-item label="接收人">
          <n-input v-model:value="form.recipients"
            placeholder="多个邮箱用逗号分隔" />
        </n-form-item>
        <n-form-item label="格式">
          <n-select v-model:value="form.format" :options="formatOptions" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="form.remark" placeholder="任务备注" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="handleSave" :loading="saving">
            {{ isEdit ? '保存' : '创建' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { useMessage, useDialog, NButton, NSpace, NIcon, NSwitch, NTag } from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { getSchedules, createSchedule, updateSchedule, deleteSchedule, toggleSchedule, getTemplates } from '@/api/report'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const saving = ref(false)
const schedules = ref([])
const templateOptions = ref([])
const pagination = ref({ page: 1, pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] })

const formatOptions = [
  { label: 'PDF', value: 'pdf' },
  { label: 'Excel', value: 'excel' },
  { label: 'CSV', value: 'csv' }
]

const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = ref({ template_id: null, cron_expression: '', recipients: '', format: 'pdf', remark: '' })

const columns = ref([
  { title: 'ID', key: 'id', width: 80 },
  { title: '模板', key: 'template_name', width: 140, ellipsis: { tooltip: true } },
  { title: 'Cron表达式', key: 'cron_expression', width: 160 },
  { title: '接收人', key: 'recipients', ellipsis: { tooltip: true } },
  {
    title: '格式', key: 'format', width: 80,
    render: row => {
      const opt = formatOptions.find(o => o.value === row.format)
      return opt ? opt.label : row.format
    }
  },
  {
    title: '状态', key: 'enabled', width: 80,
    render: row => h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' },
      { default: () => row.enabled ? '启用' : '禁用' })
  },
  {
    title: '上次执行', key: 'last_run_at', width: 180,
    render: row => row.last_run_at ? dayjs(row.last_run_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '下次执行', key: 'next_run_at', width: 180,
    render: row => row.next_run_at ? dayjs(row.next_run_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 220, fixed: 'right',
    render: row => h(NSpace, null, {
      default: () => [
        h(NSwitch, {
          value: row.enabled,
          size: 'small',
          onUpdateValue: () => handleToggle(row)
        }),
        h(NButton, { size: 'small', onClick: () => openEdit(row) },
          { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) },
          { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) })
      ]
    })
  }
])

async function loadSchedules() {
  loading.value = true
  try {
    const params = { page: pagination.value.page, page_size: pagination.value.pageSize }
    const res = await getSchedules(params)
    const data = res.data || {}
    schedules.value = data.items || data.schedules || data || []
    if (data.total !== undefined) pagination.value.itemCount = data.total
  } catch (e) {
    console.error('Load schedules error:', e)
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const res = await getTemplates({ page_size: 100 })
    const items = res.data?.items || res.data || []
    templateOptions.value = items.map(t => ({ label: t.name, value: t.id }))
  } catch (e) {
    console.error('Load templates error:', e)
  }
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  form.value = { template_id: null, cron_expression: '', recipients: '', format: 'pdf', remark: '' }
  showModal.value = true
}

function openEdit(row) {
  isEdit.value = true
  editId.value = row.id
  form.value = {
    template_id: row.template_id,
    cron_expression: row.cron_expression,
    recipients: row.recipients || '',
    format: row.format || 'pdf',
    remark: row.remark || ''
  }
  showModal.value = true
}

async function handleSave() {
  if (!form.value.template_id || !form.value.cron_expression) {
    message.warning('请填写必填项')
    return false
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await updateSchedule(editId.value, form.value)
      message.success('已更新')
    } else {
      await createSchedule(form.value)
      message.success('已创建')
    }
    showModal.value = false
    await loadSchedules()
  } catch (e) {
    message.error('操作失败')
    return false
  } finally {
    saving.value = false
  }
}

async function handleToggle(row) {
  try {
    await toggleSchedule(row.id)
    message.success(row.enabled ? '已禁用' : '已启用')
    await loadSchedules()
  } catch (e) {
    message.error('操作失败')
  }
}

function handleDelete(id) {
  dialog.warning({
    title: '确认删除', content: '确定删除此定时任务吗？',
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteSchedule(id)
        message.success('已删除')
        await loadSchedules()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(() => {
  loadTemplates()
  loadSchedules()
})
</script>
