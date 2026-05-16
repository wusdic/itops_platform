<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NDataTable, NButton, NInput, NModal, NForm, NFormItem, NSpace, NTag, NSwitch, NSpin } from 'naive-ui'

const roles = ref([])
const loading = ref(false)
const modalVisible = ref(false)
const editingItem = ref(null)
const formData = ref({ name: '', code: '', description: '', enabled: true })
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '角色名称', key: 'name' },
  { title: '角色代码', key: 'code' },
  { title: '描述', key: 'description' },
  { title: '状态', key: 'enabled', render(row) { return h(NTag, { type: row.enabled ? 'success' : 'error' }, { default: () => row.enabled ? '启用' : '禁用' }) } },
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

async function fetchRoles() {
  loading.value = true
  try {
    const res = await fetch('/api/v1/roles', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    })
    roles.value = await res.json()
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  editingItem.value = null
  formData.value = { name: '', code: '', description: '', enabled: true }
  modalVisible.value = true
}

function handleEdit(row) {
  editingItem.value = row
  formData.value = { ...row }
  modalVisible.value = true
}

async function handleSave() {
  const method = editingItem.value ? 'PUT' : 'POST'
  const url = editingItem.value ? `/api/v1/roles/${editingItem.value.id}` : '/api/v1/roles'
  await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify(formData.value)
  })
  modalVisible.value = false
  fetchRoles()
}

async function handleDelete(id) {
  await fetch(`/api/v1/roles/${id}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${getToken()}` }
  })
  fetchRoles()
}

onMounted(fetchRoles)
</script>

<template>
  <n-spin :show="loading">
    <n-card title="角色管理">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">新增角色</n-button>
      </template>
      <n-data-table :columns="columns" :data="roles" :bordered="false" />
    </n-card>
  </n-spin>

  <n-modal v-model:show="modalVisible" preset="card" :title="editingItem ? '编辑角色' : '新增角色'" style="width: 500px;">
    <n-form :model="formData" label-placement="top">
      <n-form-item label="角色名称">
        <n-input v-model:value="formData.name" placeholder="请输入角色名称" />
      </n-form-item>
      <n-form-item label="角色代码">
        <n-input v-model:value="formData.code" placeholder="请输入角色代码" />
      </n-form-item>
      <n-form-item label="描述">
        <n-input v-model:value="formData.description" placeholder="请输入描述" />
      </n-form-item>
      <n-form-item label="启用">
        <n-switch v-model:value="formData.enabled" />
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
