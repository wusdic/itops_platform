<template>
  <div>
    <div class="page-header"><h2>配置管理</h2></div>

    <n-tabs type="line" v-model:value="activeTab">
      <!-- 配置项列表 -->
      <n-tab-pane name="items" tab="配置项">
        <n-card :bordered="false" style="margin-top:16px">
          <template #header>
            <span>配置项列表</span>
          </template>
          <template #header-extra>
            <n-button type="primary" @click="openItemModal()">
              <template #icon><n-icon><AddOutline /></n-icon></template>
              新增配置项
            </n-button>
          </template>
          <n-data-table
            :columns="itemColumns"
            :data="configItems"
            :loading="itemLoading"
            :pagination="itemPagination"
            :row-key="row => row.id"
            remote
            @update:page="loadConfigItems"
          />
        </n-card>
      </n-tab-pane>

      <!-- 配置快照 -->
      <n-tab-pane name="snapshots" tab="配置快照">
        <n-card :bordered="false" style="margin-top:16px">
          <template #header>
            <span>配置快照</span>
          </template>
          <template #header-extra>
            <n-space>
              <n-button type="primary" @click="handleCreateSnapshot">
                <template #icon><n-icon><CameraOutline /></n-icon></template>
                创建快照
              </n-button>
              <n-button type="info" @click="handleSyncConfig">
                <template #icon><n-icon><SyncOutline /></n-icon></template>
                同步设备配置
              </n-button>
            </n-space>
          </template>
          <n-data-table
            :columns="snapshotColumns"
            :data="snapshots"
            :loading="snapshotLoading"
            :row-key="row => row.id"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- 配置项弹窗 -->
    <n-modal v-model:show="itemModalVisible" preset="card" :title="itemIsEdit ? '编辑配置项' : '新增配置项'" style="width:520px">
      <n-form ref="itemFormRef" :model="itemForm" :rules="itemFormRules" label-placement="left" label-width="100">
        <n-form-item label="配置键" path="key">
          <n-input v-model:value="itemForm.key" placeholder="如: max_connections" />
        </n-form-item>
        <n-form-item label="配置值" path="value">
          <n-input v-model:value="itemForm.value" placeholder="请输入配置值" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="itemForm.description" type="textarea" placeholder="请输入描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="itemModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="itemSubmitLoading" @click="handleItemSubmit">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { AddOutline, CameraOutline, SyncOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { getConfigItems, createConfigSnapshot, updateConfigItem, deleteConfigItem, syncDeviceConfig } from '@/api/asset'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()
const activeTab = ref('items')

// 配置项
const itemLoading = ref(false)
const itemSubmitLoading = ref(false)
const itemModalVisible = ref(false)
const itemIsEdit = ref(false)
const itemFormRef = ref(null)
const configItems = ref([])
const itemForm = reactive({ id: null, key: '', value: '', description: '' })
const itemFormRules = {
  key: { required: true, message: '请输入配置键', trigger: 'blur' },
  value: { required: true, message: '请输入配置值', trigger: 'blur' }
}
const itemPagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const itemColumns = [
  { title: '配置键', key: 'key', width: 200 },
  { title: '配置值', key: 'value', ellipsis: { tooltip: true } },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '更新时间', key: 'updated_at', width: 170,
    render: row => row.updated_at ? dayjs(row.updated_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 140, fixed: 'right',
    render: row => h('n-space', null, { default: () => [
      h('n-button', { size: 'small', quaternary: true, type: 'info', onClick: () => openItemModal(row) }, { icon: () => h('n-icon', null, { default: () => h(CreateOutline) }), default: () => '编辑' }),
      h('n-button', { size: 'small', quaternary: true, type: 'error', onClick: () => handleDeleteItem(row) }, { icon: () => h('n-icon', null, { default: () => h(TrashOutline) }), default: () => '删除' })
    ]})
  }
]

async function loadConfigItems(page) {
  if (page) itemPagination.page = page
  itemLoading.value = true
  try {
    const res = await getConfigItems({ page: itemPagination.page, page_size: itemPagination.pageSize })
    configItems.value = res.items || res.data?.items || []
    itemPagination.itemCount = res.total || res.data?.total || 0
  } catch (e) {
    message.error('加载配置项失败')
    console.error(e)
  } finally {
    itemLoading.value = false
  }
}

function openItemModal(row = null) {
  itemIsEdit.value = !!row
  if (row) {
    Object.assign(itemForm, { id: row.id, key: row.key, value: row.value, description: row.description || '' })
  } else {
    Object.assign(itemForm, { id: null, key: '', value: '', description: '' })
  }
  itemModalVisible.value = true
}

async function handleItemSubmit() {
  try {
    await itemFormRef.value?.validate()
    itemSubmitLoading.value = true
    if (itemIsEdit.value) {
      await updateConfigItem(itemForm.id, itemForm)
      message.success('更新成功')
    } else {
      await updateConfigItem(null, itemForm)
      message.success('创建成功')
    }
    itemModalVisible.value = false
    loadConfigItems()
  } catch (e) {
    if (e.errors) return
    message.error('操作失败')
  } finally {
    itemSubmitLoading.value = false
  }
}

function handleDeleteItem(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除配置项「${row.key}」吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteConfigItem(row.id)
        message.success('删除成功')
        loadConfigItems()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

// 快照
const snapshotLoading = ref(false)
const snapshots = ref([])

const snapshotColumns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '快照名称', key: 'name' },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: row => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  }
]

async function loadSnapshots() {
  snapshotLoading.value = true
  try {
    const res = await getConfigItems({ type: 'snapshot' })
    snapshots.value = res.items || res.data?.items || []
  } catch (e) {
    message.error('加载快照失败')
    console.error(e)
  } finally {
    snapshotLoading.value = false
  }
}

async function handleCreateSnapshot() {
  try {
    await createConfigSnapshot({ name: `快照_${dayjs().format('YYYYMMDD_HHmmss')}` })
    message.success('快照创建成功')
    loadSnapshots()
  } catch (e) {
    message.error('创建快照失败')
    console.error(e)
  }
}

async function handleSyncConfig() {
  try {
    await syncDeviceConfig()
    message.success('同步请求已发送')
  } catch (e) {
    message.error('同步失败')
    console.error(e)
  }
}

onMounted(() => {
  loadConfigItems()
  loadSnapshots()
})
</script>
