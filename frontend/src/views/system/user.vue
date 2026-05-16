<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NDataTable, NButton, NInput, NModal, NForm, NFormItem, NSpace, NTag, NSelect, NSpin } from 'naive-ui'

const users = ref([])
const loading = ref(false)
const modalVisible = ref(false)
const editingItem = ref(null)
const formData = ref({ username: '', email: '', role_id: null, enabled: true })
const roles = ref([])
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '用户名', key: 'username' },
  { title: '邮箱', key: 'email' },
  { title: '角色', key: 'role_name' },
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

async function fetchUsers() {
  loading.value = true
  try {
    const res = await fetch('/api/v1/users', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    })
    users.value = await res.json()
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  const res = await fetch('/api/v1/roles', {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  })
  roles.value = await res.json()
}

function handleAdd() {
  editingItem.value = null
  formData.value = { username: '', email: '', role_id: null, enabled: true }
  modalVisible.value = true
}

function handleEdit(row) {
  editingItem.value = row
  formData.value = { ...row }
  modalVisible.value = true
}

async function handleSave() {
  const method = editingItem.value ? 'PUT' : 'POST'
  const url = editingItem.value ? `/api/v1/users/${editingItem.value.id}` : '/api/v1/users'
  await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify(formData.value)
  })
  modalVisible.value = false
  fetchUsers()
}

async function handleDelete(id) {
  await fetch(`/api/v1/users/${id}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${getToken()}` }
  })
  fetchUsers()
}

onMounted(() => { fetchUsers(); fetchRoles() })
</script>

<template>
  <n-spin :show="loading">
    <n-card title="用户管理">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">新增用户</n-button>
      </template>
      <n-data-table :columns="columns" :data="users" :bordered="false" />
    </n-card>
  </n-spin>

  <n-modal v-model:show="modalVisible" preset="card" :title="editingItem ? '编辑用户' : '新增用户'" style="width: 500px;">
    <n-form :model="formData" label-placement="top">
      <n-form-item label="用户名">
        <n-input v-model:value="formData.username" placeholder="请输入用户名" />
      </n-form-item>
      <n-form-item label="邮箱">
        <n-input v-model:value="formData.email" placeholder="请输入邮箱" />
      </n-form-item>
      <n-form-item label="角色">
        <n-select v-model:value="formData.role_id" :options="roles.map(r => ({ label: r.name, value: r.id }))" placeholder="请选择角色" />
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
