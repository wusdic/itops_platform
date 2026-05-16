<template>
  <div>
    <div class="page-header">
      <h2>业务系统</h2>
      <n-button type="primary" @click="openModal()">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        新增业务系统
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

    <!-- 新增/编辑弹窗 -->
    <n-modal v-model:show="modalVisible" preset="card" :title="isEdit ? '编辑业务系统' : '新增业务系统'" style="width:560px">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <n-form-item label="系统名称" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入系统名称" />
        </n-form-item>
        <n-form-item label="系统编码" path="code">
          <n-input v-model:value="formData.code" placeholder="请输入系统编码" />
        </n-form-item>
        <n-form-item label="负责人">
          <n-input v-model:value="formData.owner" placeholder="请输入负责人" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="formData.description" type="textarea" placeholder="请输入描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 详情弹窗 - 关联设备 -->
    <n-modal v-model:show="detailVisible" preset="card" title="业务系统详情" style="width:800px">
      <n-descriptions :column="2" bordered>
        <n-descriptions-item label="系统名称">{{ detailData.name }}</n-descriptions-item>
        <n-descriptions-item label="系统编码">{{ detailData.code }}</n-descriptions-item>
        <n-descriptions-item label="负责人">{{ detailData.owner || '-' }}</n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ detailData.created_at ? dayjs(detailData.created_at).format('YYYY-MM-DD HH:mm') : '-' }}</n-descriptions-item>
        <n-descriptions-item label="描述" :span="2">{{ detailData.description || '-' }}</n-descriptions-item>
      </n-descriptions>
      <n-divider>关联设备</n-divider>
      <n-data-table
        :columns="deviceColumns"
        :data="relatedDevices"
        :loading="deviceLoading"
        size="small"
        :pagination="{ pageSize: 10 }"
      />
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline, EyeOutline } from '@vicons/ionicons5'
import { getBusinessSystems, getBusinessSystem, getBusinessDevices } from '@/api/asset'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const submitLoading = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const tableData = ref([])
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const formData = reactive({ id: null, name: '', code: '', owner: '', description: '' })
const formRules = {
  name: { required: true, message: '请输入系统名称', trigger: 'blur' },
  code: { required: true, message: '请输入系统编码', trigger: 'blur' }
}

const columns = [
  { title: '系统名称', key: 'name' },
  { title: '系统编码', key: 'code', width: 140 },
  { title: '负责人', key: 'owner', width: 120 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: row => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render: row => h('n-space', null, { default: () => [
      h('n-button', { size: 'small', quaternary: true, type: 'info', onClick: () => openModal(row) }, { icon: () => h('n-icon', null, { default: () => h(CreateOutline) }), default: () => '编辑' }),
      h('n-button', { size: 'small', quaternary: true, onClick: () => handleDetail(row) }, { icon: () => h('n-icon', null, { default: () => h(EyeOutline) }), default: () => '详情' }),
      h('n-button', { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, { icon: () => h('n-icon', null, { default: () => h(TrashOutline) }), default: () => '删除' })
    ]})
  }
]

const deviceColumns = [
  { title: '主机名', key: 'hostname' },
  { title: '名称', key: 'name' },
  { title: 'IP', key: 'ip', width: 140 },
  { title: '类型', key: 'device_type', width: 100 },
  {
    title: '状态', key: 'status', width: 90,
    render: row => {
      const map = { online: 'success', offline: 'error', maintenance: 'warning' }
      const labels = { online: '在线', offline: '离线', maintenance: '维护中' }
      return h('n-tag', { type: map[row.status] || 'default', size: 'small' }, { default: () => labels[row.status] || row.status })
    }
  }
]

const detailVisible = ref(false)
const detailData = reactive({})
const relatedDevices = ref([])
const deviceLoading = ref(false)

async function loadData(page) {
  if (page) pagination.page = page
  loading.value = true
  try {
    const res = await getBusinessSystems({ page: pagination.page, page_size: pagination.pageSize })
    tableData.value = res.items || res.data?.items || []
    pagination.itemCount = res.total || res.data?.total || 0
  } catch (e) {
    message.error('加载业务系统失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handlePageChange(p) { loadData(p) }
function handlePageSizeChange(ps) { pagination.pageSize = ps; pagination.page = 1; loadData() }

function openModal(row = null) {
  isEdit.value = !!row
  if (row) {
    Object.assign(formData, { id: row.id, name: row.name, code: row.code, owner: row.owner || '', description: row.description || '' })
  } else {
    Object.assign(formData, { id: null, name: '', code: '', owner: '', description: '' })
  }
  modalVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
    submitLoading.value = true
    message.success(isEdit.value ? '更新成功' : '创建成功')
    modalVisible.value = false
    loadData()
  } catch (e) {
    if (e.errors) return
    message.error('操作失败')
  } finally {
    submitLoading.value = false
  }
}

function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除业务系统「${row.name}」吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      message.success('删除成功')
      loadData()
    }
  })
}

async function handleDetail(row) {
  Object.assign(detailData, row)
  detailVisible.value = true
  deviceLoading.value = true
  try {
    const res = await getBusinessDevices(row.id)
    relatedDevices.value = res.data?.items || res.items || res.data || []
  } catch (e) {
    message.error('加载关联设备失败')
  } finally {
    deviceLoading.value = false
  }
}

onMounted(() => { loadData() })
</script>
