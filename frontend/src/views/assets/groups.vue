<template>
  <div>
    <div class="page-header">
      <h2>设备分组</h2>
      <n-button type="primary" @click="openGroupModal()">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        新增分组
      </n-button>
    </div>

    <n-grid cols="12" :x-gap="16" responsive="screen">
      <!-- 左侧分组树 -->
      <n-gi :span="3">
        <n-card title="分组列表" :bordered="false" size="small">
          <n-tree
            :data="treeData"
            :selected-keys="selectedGroupKeys"
            block-line
            selectable
            @update:selected-keys="handleSelectGroup"
          />
          <template #header-extra>
            <n-space>
              <n-button size="tiny" quaternary @click="openGroupModal()">
                <template #icon><n-icon><AddOutline /></n-icon></template>
              </n-button>
              <n-button v-if="selectedGroupId" size="tiny" quaternary type="info" @click="openGroupModal(currentGroup)">
                <template #icon><n-icon><CreateOutline /></n-icon></template>
              </n-button>
              <n-button v-if="selectedGroupId" size="tiny" quaternary type="error" @click="handleDeleteGroup">
                <template #icon><n-icon><TrashOutline /></n-icon></template>
              </n-button>
            </n-space>
          </template>
        </n-card>
      </n-gi>

      <!-- 右侧设备列表 -->
      <n-gi :span="9">
        <n-card :bordered="false">
          <template #header>
            <span>{{ currentGroupName }} 设备列表</span>
          </template>
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
      </n-gi>
    </n-grid>

    <!-- 分组弹窗 -->
    <n-modal v-model:show="groupModalVisible" preset="card" :title="groupIsEdit ? '编辑分组' : '新增分组'" style="width:480px">
      <n-form ref="groupFormRef" :model="groupForm" :rules="groupFormRules" label-placement="left" label-width="80">
        <n-form-item label="分组名称" path="name">
          <n-input v-model:value="groupForm.name" placeholder="请输入分组名称" />
        </n-form-item>
        <n-form-item label="父分组">
          <n-select v-model:value="groupForm.parent_id" :options="parentOptions" placeholder="选择父分组（可选）" clearable />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="groupForm.description" type="textarea" placeholder="请输入描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="groupModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="groupSubmitLoading" @click="handleGroupSubmit">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, computed, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { getDeviceGroups, getGroupDevices } from '@/api/asset'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const groupSubmitLoading = ref(false)
const groupModalVisible = ref(false)
const groupIsEdit = ref(false)
const groupFormRef = ref(null)

const selectedGroupId = ref(null)
const selectedGroupKeys = ref([])
const groups = ref([])

const groupForm = reactive({ id: null, name: '', parent_id: null, description: '' })
const groupFormRules = { name: { required: true, message: '请输入分组名称', trigger: 'blur' } }

const parentOptions = computed(() => {
  return groups.value.filter(g => g.id !== groupForm.id).map(g => ({ label: g.name, value: g.id }))
})

const currentGroup = computed(() => groups.value.find(g => g.id === selectedGroupId.value) || null)
const currentGroupName = computed(() => currentGroup.value?.name || '请选择分组')

const treeData = computed(() => buildTree(groups.value))

function buildTree(items) {
  const map = {}
  const roots = []
  items.forEach(g => { map[g.id] = { ...g, key: String(g.id), label: g.name, children: [] } })
  items.forEach(g => {
    const node = map[g.id]
    if (g.parent_id && map[g.parent_id]) {
      map[g.parent_id].children.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
}

const tableData = ref([])
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const columns = [
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
  },
  { title: '厂商', key: 'vendor', width: 100 },
  {
    title: '创建时间', key: 'created_at', width: 170,
    render: row => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  }
]

async function loadGroups() {
  try {
    const res = await getDeviceGroups()
    groups.value = res.data?.items || res.data || res.items || []
  } catch (e) {
    message.error('加载分组失败')
    console.error(e)
  }
}

async function loadGroupDevices() {
  if (!selectedGroupId.value) return
  loading.value = true
  try {
    const res = await getGroupDevices(selectedGroupId.value)
    const items = res.data?.items || res.items || res.data || []
    tableData.value = Array.isArray(items) ? items : []
    pagination.itemCount = res.data?.total || res.total || items.length || 0
  } catch (e) {
    message.error('加载设备失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleSelectGroup(keys) {
  if (keys.length) {
    selectedGroupId.value = Number(keys[0])
    selectedGroupKeys.value = keys
    pagination.page = 1
    loadGroupDevices()
  }
}

function handlePageChange(p) { pagination.page = p; loadGroupDevices() }
function handlePageSizeChange(ps) { pagination.pageSize = ps; pagination.page = 1; loadGroupDevices() }

function openGroupModal(group = null) {
  groupIsEdit.value = !!group
  if (group) {
    Object.assign(groupForm, { id: group.id, name: group.name, parent_id: group.parent_id || null, description: group.description || '' })
  } else {
    Object.assign(groupForm, { id: null, name: '', parent_id: null, description: '' })
  }
  groupModalVisible.value = true
}

async function handleGroupSubmit() {
  try {
    await groupFormRef.value?.validate()
    groupSubmitLoading.value = true
    message.success(groupIsEdit.value ? '更新成功' : '创建成功')
    groupModalVisible.value = false
    await loadGroups()
  } catch (e) {
    if (e.errors) return
    message.error('操作失败')
    console.error(e)
  } finally {
    groupSubmitLoading.value = false
  }
}

function handleDeleteGroup() {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除分组「${currentGroup.value?.name}」吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      message.success('删除成功')
      selectedGroupId.value = null
      selectedGroupKeys.value = []
      tableData.value = []
      await loadGroups()
    }
  })
}

onMounted(() => { loadGroups() })
</script>
