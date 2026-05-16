<template>
  <div>
    <div class="page-header">
      <h2>设备管理</h2>
      <n-button type="primary" @click="openCreateModal">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        新增设备
      </n-button>
    </div>

    <!-- 工具栏 -->
    <n-card :bordered="false" style="margin-bottom:16px">
      <n-space :wrap="true" :size="12">
        <n-input
          v-model:value="search.keyword"
          placeholder="搜索主机名/IP/名称"
          clearable
          style="width:220px"
          @keyup.enter="loadData"
        />
        <n-select
          v-model:value="search.device_type"
          placeholder="设备类型"
          clearable
          style="width:160px"
          :options="deviceTypeOptions"
        />
        <n-select
          v-model:value="search.status"
          placeholder="状态"
          clearable
          style="width:140px"
          :options="statusOptions"
        />
        <n-button type="primary" @click="loadData">
          <template #icon><n-icon><SearchOutline /></n-icon></template>
          搜索
        </n-button>
        <n-button @click="resetSearch">重置</n-button>
      </n-space>
    </n-card>

    <!-- 数据表格 -->
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
    <n-modal v-model:show="modalVisible" preset="card" :title="isEdit ? '编辑设备' : '新增设备'" style="width:640px">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <n-grid cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="主机名" path="hostname">
              <n-input v-model:value="formData.hostname" placeholder="请输入主机名" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="设备名称" path="name">
              <n-input v-model:value="formData.name" placeholder="请输入设备名称" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="IP地址" path="ip_address">
              <n-input v-model:value="formData.ip_address" placeholder="请输入IP地址" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="设备类型" path="device_type">
              <n-select v-model:value="formData.device_type" :options="deviceTypeOptions" placeholder="选择设备类型" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="厂商" path="vendor">
              <n-input v-model:value="formData.vendor" placeholder="请输入厂商" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="型号" path="model">
              <n-input v-model:value="formData.model" placeholder="请输入型号" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="操作系统" path="os_type">
              <n-select v-model:value="formData.os_type" :options="osTypeOptions" placeholder="选择操作系统" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="位置" path="location">
              <n-input v-model:value="formData.location" placeholder="请输入位置" />
            </n-form-item>
          </n-gi>
          <n-gi :span="2">
            <n-form-item label="标签" path="tags">
              <n-dynamic-tags v-model:value="formData.tags" />
            </n-form-item>
          </n-gi>
          <n-gi :span="2">
            <n-form-item label="备注" path="remark">
              <n-input v-model:value="formData.remark" type="textarea" placeholder="请输入备注" />
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import {
  AddOutline, SearchOutline, CreateOutline, TrashOutline, HammerOutline,
  ArrowBackOutline, EyeOutline
} from '@vicons/ionicons5'
import {
  getDevices, createDevice, updateDevice, deleteDevice,
  setDeviceMaintain, decommissionDevice
} from '@/api/asset'
import dayjs from 'dayjs'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const submitLoading = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const deviceTypeOptions = [
  { label: '服务器', value: 'server' },
  { label: '交换机', value: 'switch' },
  { label: '路由器', value: 'router' },
  { label: '防火墙', value: 'firewall' },
  { label: '存储设备', value: 'storage' },
  { label: '虚拟机', value: 'vm' }
]

const osTypeOptions = [
  { label: 'Linux', value: 'linux' },
  { label: 'Windows', value: 'windows' },
  { label: 'macOS', value: 'macos' },
  { label: '其他', value: 'other' }
]

const statusOptions = [
  { label: '在线', value: 'online' },
  { label: '离线', value: 'offline' },
  { label: '维护中', value: 'maintenance' }
]

const statusTypeMap = { online: 'success', offline: 'error', maintenance: 'warning' }
const statusLabelMap = { online: '在线', offline: '离线', maintenance: '维护中' }

const search = reactive({ keyword: '', device_type: null, status: null })

const tableData = ref([])
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const formData = reactive({
  id: null, hostname: '', name: '', ip_address: '', device_type: '',
  vendor: '', model: '', os_type: '', tags: [], location: '', remark: ''
})

const formRules = {
  hostname: { required: true, message: '请输入主机名', trigger: 'blur' },
  name: { required: true, message: '请输入设备名称', trigger: 'blur' },
  ip_address: { required: true, message: '请输入IP地址', trigger: 'blur' }
}

const columns = [
  { title: '主机名', key: 'hostname', ellipsis: { tooltip: true } },
  { title: '名称', key: 'name', ellipsis: { tooltip: true } },
  { title: 'IP', key: 'ip', width: 140 },
  { title: '类型', key: 'device_type', width: 100 },
  {
    title: '状态', key: 'status', width: 100,
    render: row => h('span', null, [
      h('n-tag', { type: statusTypeMap[row.status] || 'default', size: 'small' }, { default: () => statusLabelMap[row.status] || row.status })
    ])
  },
  { title: '厂商', key: 'vendor', width: 120 },
  {
    title: '标签', key: 'tags', width: 200,
    render: row => {
      const tags = Array.isArray(row.tags) ? row.tags : (row.tags ? row.tags.split(',') : [])
      return tags.length ? tags.map(t => h('n-tag', { key: t, size: 'small', style: 'margin-right:4px' }, { default: () => t })) : '-'
    }
  },
  { title: '位置', key: 'location', width: 140 },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: row => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 260, fixed: 'right',
    render: row => h('n-space', null, { default: () => [
      h('n-button', { size: 'small', quaternary: true, type: 'info', onClick: () => openEditModal(row) }, { icon: () => h('n-icon', null, { default: () => h(CreateOutline) }), default: () => '编辑' }),
      h('n-button', { size: 'small', quaternary: true, onClick: () => handleMaintain(row) }, { icon: () => h('n-icon', null, { default: () => h(HammerOutline) }), default: () => '维护' }),
      h('n-button', { size: 'small', quaternary: true, type: 'warning', onClick: () => handleDecommission(row) }, { icon: () => h('n-icon', null, { default: () => h(ArrowBackOutline) }), default: () => '退役' }),
      h('n-button', { size: 'small', quaternary: true, type: 'info', onClick: () => router.push(`/devices/${row.hostname || row.name}`) }, { icon: () => h('n-icon', null, { default: () => h(EyeOutline) }), default: () => '详情' }),
      h('n-button', { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, { icon: () => h('n-icon', null, { default: () => h(TrashOutline) }), default: () => '删除' })
    ]})
  }
]

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: search.keyword || undefined,
      device_type: search.device_type || undefined,
      status: search.status || undefined
    }
    const res = await getDevices(params)
    tableData.value = res.items || res.data?.items || []
    pagination.itemCount = res.total || res.data?.total || 0
  } catch (e) {
    message.error('加载设备列表失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handlePageChange(p) { pagination.page = p; loadData() }
function handlePageSizeChange(ps) { pagination.pageSize = ps; pagination.page = 1; loadData() }

function resetSearch() {
  search.keyword = ''
  search.device_type = null
  search.status = null
  pagination.page = 1
  loadData()
}

function openCreateModal() {
  isEdit.value = false
  Object.assign(formData, { id: null, hostname: '', name: '', ip_address: '', device_type: '', vendor: '', model: '', os_type: '', tags: [], location: '', remark: '' })
  modalVisible.value = true
}

function openEditModal(row) {
  isEdit.value = true
  Object.assign(formData, {
    id: row.id,
    hostname: row.hostname || '',
    name: row.name || '',
    ip_address: row.ip || row.ip_address || '',
    device_type: row.device_type || '',
    vendor: row.vendor || '',
    model: row.model || '',
    os_type: row.os_type || '',
    tags: Array.isArray(row.tags) ? row.tags : (row.tags ? row.tags.split(',') : []),
    location: row.location || '',
    remark: row.remark || ''
  })
  modalVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
    submitLoading.value = true
    if (isEdit.value) {
      await updateDevice(formData.id, { ...formData, tags: formData.tags.join(',') })
      message.success('更新成功')
    } else {
      await createDevice({ ...formData, tags: formData.tags.join(',') })
      message.success('创建成功')
    }
    modalVisible.value = false
    loadData()
  } catch (e) {
    if (e.errors) return
    message.error(isEdit.value ? '更新失败' : '创建失败')
    console.error(e)
  } finally {
    submitLoading.value = false
  }
}

function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除设备「${row.name || row.hostname}」吗？此操作不可恢复。`,
    positiveText: '确定删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteDevice(row.id)
        message.success('删除成功')
        loadData()
      } catch (e) {
        message.error('删除失败')
        console.error(e)
      }
    }
  })
}

async function handleMaintain(row) {
  try {
    await setDeviceMaintain(row.id)
    message.success('已设置维护状态')
    loadData()
  } catch (e) {
    message.error('操作失败')
    console.error(e)
  }
}

async function handleDecommission(row) {
  dialog.warning({
    title: '确认退役',
    content: `确定要退役设备「${row.name || row.hostname}」吗？`,
    positiveText: '确定退役',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await decommissionDevice(row.id)
        message.success('设备已退役')
        loadData()
      } catch (e) {
        message.error('操作失败')
        console.error(e)
      }
    }
  })
}

onMounted(() => { loadData() })
</script>
