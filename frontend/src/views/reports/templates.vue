<template>
  <div>
    <div class="page-header">
      <h2>报表模板</h2>
      <n-button type="primary" @click="openCreate">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        新建模板
      </n-button>
    </div>

    <!-- 筛选 -->
    <n-card :bordered="false" style="margin-bottom: 16px">
      <n-space>
        <n-input v-model:value="searchText" placeholder="搜索模板名称..."
          style="width: 240px" clearable @update:value="loadTemplates" />
        <n-select v-model:value="filterType" :options="typeOptions"
          placeholder="类型筛选" style="width: 160px" clearable @update:value="loadTemplates" />
      </n-space>
    </n-card>

    <!-- 模板列表 -->
    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="templates"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 创建/编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="dialog"
      :title="isEdit ? '编辑模板' : '新建模板'"
      :positive-text="isEdit ? '保存' : '创建'"
      :negative-text="'取消'"
      @positive-click="handleSave"
      @negative-click="showModal = false"
      style="width: 560px"
    >
      <n-form ref="formRef" :model="form" label-placement="left" label-width="80" style="margin-top: 16px">
        <n-form-item label="名称" required>
          <n-input v-model:value="form.name" placeholder="模板名称" />
        </n-form-item>
        <n-form-item label="类型">
          <n-select v-model:value="form.type" :options="typeOptions" />
        </n-form-item>
        <n-form-item label="格式">
          <n-select v-model:value="form.format" :options="formatOptions" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" type="textarea"
            placeholder="模板描述..." :rows="3" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { useMessage, useDialog, NButton, NSpace, NIcon } from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '@/api/report'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const templates = ref([])
const searchText = ref('')
const filterType = ref(null)

const typeOptions = [
  { label: '设备报表', value: 'device' },
  { label: '告警报表', value: 'alert' },
  { label: '工单报表', value: 'workorder' },
  { label: '巡检报表', value: 'inspection' },
  { label: '综合报表', value: 'general' }
]

const formatOptions = [
  { label: 'PDF', value: 'pdf' },
  { label: 'Excel', value: 'excel' },
  { label: 'CSV', value: 'csv' },
  { label: 'HTML', value: 'html' }
]

const pagination = ref({ page: 1, pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] })

// 弹窗
const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = ref({ name: '', type: 'general', format: 'pdf', description: '' })
const formRef = ref(null)

const columns = ref([
  { title: 'ID', key: 'id', width: 80 },
  { title: '模板名称', key: 'name', ellipsis: { tooltip: true } },
  {
    title: '类型', key: 'type', width: 120,
    render: row => {
      const opt = typeOptions.find(o => o.value === row.type)
      return opt ? opt.label : row.type
    }
  },
  {
    title: '格式', key: 'format', width: 100,
    render: row => {
      const opt = formatOptions.find(o => o.value === row.format)
      return opt ? opt.label : row.format
    }
  },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '更新时间', key: 'updated_at', width: 180,
    render: row => row.updated_at ? dayjs(row.updated_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 160, fixed: 'right',
    render: row => h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openEdit(row) },
          { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) },
          { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) })
      ]
    })
  }
])

async function loadTemplates() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }
    if (searchText.value) params.search = searchText.value
    if (filterType.value) params.type = filterType.value

    const res = await getTemplates(params)
    const data = res.data || {}
    templates.value = data.items || data.templates || data || []
    if (data.total !== undefined) {
      pagination.value.itemCount = data.total
    }
  } catch (e) {
    console.error('Load templates error:', e)
    message.error('加载模板失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', type: 'general', format: 'pdf', description: '' }
  showModal.value = true
}

function openEdit(row) {
  isEdit.value = true
  editId.value = row.id
  form.value = {
    name: row.name,
    type: row.type || 'general',
    format: row.format || 'pdf',
    description: row.description || ''
  }
  showModal.value = true
}

async function handleSave() {
  if (!form.value.name) {
    message.warning('请输入模板名称')
    return false
  }
  try {
    if (isEdit.value) {
      await updateTemplate(editId.value, form.value)
      message.success('模板已更新')
    } else {
      await createTemplate(form.value)
      message.success('模板已创建')
    }
    showModal.value = false
    await loadTemplates()
  } catch (e) {
    message.error(isEdit.value ? '更新失败' : '创建失败')
    return false
  }
}

function handleDelete(id) {
  dialog.warning({
    title: '确认删除',
    content: '确定删除此模板吗？此操作不可恢复。',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteTemplate(id)
        message.success('模板已删除')
        await loadTemplates()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(() => {
  loadTemplates()
})
</script>
