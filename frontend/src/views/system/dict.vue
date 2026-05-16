<template>
  <div class="page-container">
    <n-card title="字典管理" class="page-card">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon>
            <n-icon><AddOutline /></n-icon>
          </template>
          添加字典
        </n-button>
      </template>

      <div class="filter-bar">
        <n-input
          v-model:value="searchKeyword"
          placeholder="搜索字典名称/编码"
          style="width: 200px"
          clearable
          @keyup.enter="handleSearch"
        />
        <n-button type="primary" @click="handleSearch">搜索</n-button>
      </div>

      <n-data-table
        :columns="columns"
        :data="dictList"
        :loading="loading"
        :pagination="pagination"
        :row-key="(row) => row.id"
      />

      <n-modal
        v-model:show="dialogVisible"
        preset="card"
        :title="dialogTitle"
        style="width: 500px"
      >
        <n-form
          :model="form"
          :rules="rules"
          ref="formRef"
          label-placement="left"
          label-width="100px"
        >
          <n-form-item label="字典名称" path="name">
            <n-input v-model:value="form.name" placeholder="请输入字典名称" />
          </n-form-item>
          <n-form-item label="字典编码" path="code">
            <n-input v-model:value="form.code" placeholder="请输入字典编码" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input
              v-model:value="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入描述"
            />
          </n-form-item>
          <n-form-item label="状态">
            <n-select
              v-model:value="form.status"
              :options="statusOptions"
              placeholder="请选择状态"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="dialogVisible = false">取消</n-button>
            <n-button type="primary" @click="submitForm">确定</n-button>
          </n-space>
        </template>
      </n-modal>

      <n-modal
        v-model:show="itemsDialogVisible"
        preset="card"
        title="字典项管理"
        style="width: 700px"
      >
        <n-data-table
          :columns="itemColumns"
          :data="dictItems"
          :row-key="(row) => row.id"
        />
        <template #footer>
          <n-button type="primary" size="small" @click="handleAddItem">添加字典项</n-button>
        </template>
      </n-modal>
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5'
import { NTag, NButton } from 'naive-ui'

const message = useMessage()
const loading = ref(false)
const searchKeyword = ref('')
const dictList = ref([])
const dialogVisible = ref(false)
const itemsDialogVisible = ref(false)
const dialogTitle = ref('添加字典')
const formRef = ref(null)
const dictItems = ref([])
const currentDictId = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', code: '', description: '', status: '1' })

const statusOptions = [
  { label: '启用', value: '1' },
  { label: '禁用', value: '0' }
]

const rules = {
  name: [{ required: true, message: '请输入字典名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入字典编码', trigger: 'blur' }]
}

const columns = [
  { title: '字典名称', key: 'name', width: 180 },
  { title: '字典编码', key: 'code', width: 150 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(
        NTag,
        { type: row.status === '1' ? 'success' : 'error', size: 'small' },
        { default: () => row.status === '1' ? '启用' : '禁用' }
      )
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render(row) {
      return h('div', { style: { display: 'flex', gap: '8px' } }, [
        h(
          NButton,
          { size: 'small', type: 'primary', quaternary: true, onClick: () => handleItems(row) },
          { default: () => '字典项' }
        ),
        h(
          NButton,
          { size: 'small', type: 'primary', quaternary: true, onClick: () => handleEdit(row) },
          { default: () => '编辑' }
        ),
        h(
          NButton,
          { size: 'small', type: 'error', quaternary: true, onClick: () => handleDelete(row) },
          { default: () => '删除' }
        )
      ])
    }
  }
]

const itemColumns = [
  { title: '标签', key: 'label', width: 120 },
  { title: '值', key: 'value', width: 120 },
  { title: '排序', key: 'sort', width: 80 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(
        NTag,
        { type: row.status === '1' ? 'success' : 'error', size: 'small' },
        { default: () => row.status === '1' ? '启用' : '禁用' }
      )
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render(row) {
      return h('div', { style: { display: 'flex', gap: '8px' } }, [
        h(
          NButton,
          { size: 'small', type: 'primary', quaternary: true, onClick: () => handleEditItem(row) },
          { default: () => '编辑' }
        ),
        h(
          NButton,
          { size: 'small', type: 'error', quaternary: true, onClick: () => handleDeleteItem(row) },
          { default: () => '删除' }
        )
      ])
    }
  }
]

const fetchData = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/v1/admin/dicts?page=${pagination.page}&page_size=${pagination.pageSize}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    if (!res.ok) throw new Error('请求失败')
    const data = await res.json()
    dictList.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('Load dicts error:', error)
    message.error('加载字典列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => { fetchData() })

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleAdd = () => {
  dialogTitle.value = '添加字典'
  Object.assign(form, { id: null, name: '', code: '', description: '', status: '1' })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑字典'
  Object.assign(form, { id: row.id, name: row.name, code: row.code, description: row.description, status: row.status })
  dialogVisible.value = true
}

const handleDelete = (row) => {
  window.$dialog.warning({
    title: '提示',
    content: `确定删除字典 "${row.name}" 吗?`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const token = localStorage.getItem('token')
        await fetch(`/api/v1/admin/dicts/${row.id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        message.success('删除成功')
        fetchData()
      } catch (error) {
        console.error('Delete error:', error)
        message.error('删除失败')
      }
    }
  })
}

const handleItems = (row) => {
  currentDictId.value = row.id
  dictItems.value = [
    { id: 1, label: '是', value: '1', sort: 1, status: '1' },
    { id: 2, label: '否', value: '0', sort: 2, status: '1' }
  ]
  itemsDialogVisible.value = true
}

const handleAddItem = () => { message.info('添加字典项') }
const handleEditItem = (row) => { message.info('编辑字典项') }
const handleDeleteItem = (row) => { message.info('删除字典项') }

const submitForm = async () => {
  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    const token = localStorage.getItem('token')
    const url = form.id ? `/api/v1/admin/dicts/${form.id}` : '/api/v1/admin/dicts'
    const method = form.id ? 'PUT' : 'POST'

    const res = await fetch(url, {
      method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(form)
    })

    if (!res.ok) throw new Error('请求失败')

    message.success(form.id ? '更新成功' : '创建成功')
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Submit error:', error)
    message.error('操作失败')
  }
}
</script>

<style lang="scss" scoped>
.page-container {
  padding: 16px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
</style>
