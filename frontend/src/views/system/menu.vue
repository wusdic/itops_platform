<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NDataTable, NButton, NInput, NModal, NForm, NFormItem, NSpace, NTree, NSpin } from 'naive-ui'

const menus = ref([])
const loading = ref(false)
const modalVisible = ref(false)
const editingItem = ref(null)
const formData = ref({ name: '', path: '', parent_id: null, icon: '', order_num: 0 })
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '菜单名称', key: 'name' },
  { title: '路径', key: 'path' },
  { title: '图标', key: 'icon' },
  { title: '排序', key: 'order_num', width: 80 },
  { title: '操作', key: 'actions', render(row) { return h(NSpace, null, { default: () => [h(NButton, { size: 'small', onClick: () => handleEdit(row) }, { default: () => '编辑' }), h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) }, { default: () => '删除' })] }) } }
]

import { h } from 'vue'
const { useAuthStore } = require('@/stores/auth')

function getToken() {
  try {
    const store = useAuthStore()
    return store.token || ''
  } catch {
    return ''
  }
}

async function fetchMenus() {
  loading.value = true
  try {
    const res = await fetch('/api/v1/menus', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    })
    menus.value = await res.json()
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  editingItem.value = null
  formData.value = { name: '', path: '', parent_id: null, icon: '', order_num: 0 }
  modalVisible.value = true
}

function handleEdit(row) {
  editingItem.value = row
  formData.value = { ...row }
  modalVisible.value = true
}

async function handleSave() {
  const method = editingItem.value ? 'PUT' : 'POST'
  const url = editingItem.value ? `/api/v1/menus/${editingItem.value.id}` : '/api/v1/menus'
  await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify(formData.value)
  })
  modalVisible.value = false
  fetchMenus()
}

async function handleDelete(id) {
  await fetch(`/api/v1/menus/${id}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${getToken()}` }
  })
  fetchMenus()
}

onMounted(fetchMenus)
</script>

<template>
  <n-spin :show="loading">
    <n-card title="菜单管理">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">新增菜单</n-button>
      </template>
      <n-data-table :columns="columns" :data="menus" :bordered="false" />
    </n-card>
  </n-spin>

  <n-modal v-model:show="modalVisible" preset="card" :title="editingItem ? '编辑菜单' : '新增菜单'" style="width: 500px;">
    <n-form :model="formData" label-placement="top">
      <n-form-item label="菜单名称">
        <n-input v-model:value="formData.name" placeholder="请输入菜单名称" />
      </n-form-item>
      <n-form-item label="路径">
        <n-input v-model:value="formData.path" placeholder="请输入菜单路径" />
      </n-form-item>
      <n-form-item label="图标">
        <n-input v-model:value="formData.icon" placeholder="请输入图标" />
      </n-form-item>
      <n-form-item label="排序">
        <n-input-number v-model:value="formData.order_num" :min="0" />
      </n-form-item>
    </n-form>
    <template #footer>
      <n-space justify="end">
        <n-button @click="modalVisible = false">取消</n-button>
        <n-button type="primary" @click="handleSave">保存</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<style scoped>
</style>
