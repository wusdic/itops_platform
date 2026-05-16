<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NDataTable, NButton, NInput, NModal, NForm, NFormItem, NSpace, NTag, NSwitch, NSpin } from 'naive-ui'

const categories = ref([])
const loading = ref(false)
const modalVisible = ref(false)
const editingItem = ref(null)
const formData = ref({ name: '', description: '', enabled: true })
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name' },
  { title: '描述', key: 'description' },
  { title: '状态', key: 'enabled', render(row) { return h(NSwitch, { value: row.enabled, disabled: true }) } },
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

async function fetchCategories() {
  loading.value = true
  try {
    const res = await fetch('/api/v1/ai/categories', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    })
    categories.value = await res.json()
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  editingItem.value = null
  formData.value = { name: '', description: '', enabled: true }
  modalVisible.value = true
}

function handleEdit(row) {
  editingItem.value = row
  formData.value = { ...row }
  modalVisible.value = true
}

async function handleSave() {
  const method = editingItem.value ? 'PUT' : 'POST'
  const url = editingItem.value ? `/api/v1/ai/categories/${editingItem.value.id}` : '/api/v1/ai/categories'
  await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify(formData.value)
  })
  modalVisible.value = false
  fetchCategories()
}

async function handleDelete(id) {
  await fetch(`/api/v1/ai/categories/${id}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${getToken()}` }
  })
  fetchCategories()
}

onMounted(fetchCategories)
</script>

<template>
  <n-spin :show="loading">
    <n-card title="AI 分类管理">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">新增分类</n-button>
      </template>
      <n-data-table :columns="columns" :data="categories" :bordered="false" />
    </n-card>
  </n-spin>

  <n-modal v-model:show="modalVisible" preset="card" :title="editingItem ? '编辑分类' : '新增分类'" style="width: 500px;">
    <n-form :model="formData" label-placement="top">
      <n-form-item label="名称">
        <n-input v-model:value="formData.name" placeholder="请输入分类名称" />
      </n-form-item>
      <n-form-item label="描述">
        <n-input v-model:value="formData.description" placeholder="请输入分类描述" />
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
