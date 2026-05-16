<template>
  <div class="page-container">
    <n-card title="AI助手分类" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          新建分类
        </n-button>
      </template>

      <n-data-table
        :columns="columns"
        :data="categoryList"
        :loading="loading"
        :row-key="row => row.id"
      />
    </n-card>

    <n-modal v-model:show="dialogVisible" preset="card" :title="dialogTitle" style="width: 500px">
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item label="分类名称">
          <n-input v-model:value="form.name" placeholder="请输入分类名称" />
        </n-form-item>
        <n-form-item label="分类编码">
          <n-input v-model:value="form.code" placeholder="请输入分类编码" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitForm" :loading="submitting">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NForm, NFormItem, NInput, NSpace, NTag, NIcon, useMessage, useDialog } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const submitting = ref(false)
const categoryList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新建分类')

const form = reactive({ id: null, name: '', code: '', description: '' })

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '分类名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '分类编码', key: 'code', width: 150 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '操作', key: 'actions', width: 150,
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleEdit(row) }, () => '编辑'),
        h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, () => '删除')
      ])
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/knowledge/category', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    categoryList.value = data.items || data.data?.items || []
  } catch (e) {
    message.error(`加载分类失败: ${e.message}`)
    console.error('[copilot] loadData error:', e)
    categoryList.value = []
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  dialogTitle.value = '新建分类'
  Object.assign(form, { id: null, name: '', code: '', description: '' })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑分类'
  Object.assign(form, { id: row.id, name: row.name, code: row.code, description: row.description || '' })
  dialogVisible.value = true
}

function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除分类"${row.name}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const token = localStorage.getItem('token') || ''
        const res = await fetch(`/api/v1/knowledge/category/${row.id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        message.success('删除成功')
        loadData()
      } catch (e) {
        message.error(`删除失败: ${e.message}`)
        console.error('[copilot] delete error:', e)
      }
    }
  })
}

async function submitForm() {
  if (!form.name || !form.code) {
    message.warning('请填写必填项')
    return
  }
  submitting.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const method = form.id ? 'PUT' : 'POST'
    const url = form.id ? `/api/v1/knowledge/category/${form.id}` : '/api/v1/knowledge/category'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(form)
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const result = await res.json()
    if (result.error) throw new Error(result.error)
    message.success(form.id ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadData()
  } catch (e) {
    message.error(`操作失败: ${e.message}`)
    console.error('[copilot] submit error:', e)
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
