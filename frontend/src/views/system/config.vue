<template>
  <n-card title="参数配置" class="page-card">
    <template #header-extra>
      <n-space>
        <n-button type="primary" @click="loadData" :loading="loading">
          <template #icon>
            <n-icon><RefreshOutline /></n-icon>
          </template>
          刷新
        </n-button>
      </n-space>
    </template>

    <n-data-table
      :columns="columns"
      :data="configList"
      :loading="loading"
      :pagination="pagination"
      :row-key="row => row.key"
    />
  </n-card>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { RefreshOutline, CreateOutline, CheckmarkOutline, CloseOutline } from '@vicons/ionicons5'
import { config as configApi } from '@/api'
import { formatTime } from '@/utils/date'

const message = useMessage()
const loading = ref(false)
const configList = ref([])

const pagination = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  onChange: (page) => {
    pagination.page = page
    loadData()
  },
  onUpdatePageSize: (pageSize) => {
    pagination.pageSize = pageSize
    pagination.page = 1
    loadData()
  }
})

const loadData = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/v1/admin/configs?page=${pagination.page}&page_size=${pagination.pageSize}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('请求失败')
    const data = await res.json()
    configList.value = (data.items || []).map(c => ({ ...c, editing: false, editValue: c.value }))
  } catch (error) {
    console.error('Load config error:', error)
    message.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

const handleEdit = (row) => {
  row.editing = true
  row.editValue = row.value
}

const handleCancel = (row) => {
  row.editing = false
  row.editValue = row.value
}

const handleSave = async (row) => {
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/v1/admin/configs/${row.key}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ value: row.editValue })
    })
    if (!res.ok) throw new Error('更新失败')
    row.value = row.editValue
    row.editing = false
    message.success('保存成功')
  } catch (error) {
    console.error('Save error:', error)
    message.error('保存失败')
  }
}

const columns = [
  {
    title: '配置键',
    key: 'key',
    width: 200,
    ellipsis: { tooltip: true }
  },
  {
    title: '配置值',
    key: 'value',
    width: 300,
    ellipsis: { tooltip: true },
    render(row) {
      if (!row.editing) {
        return row.value
      }
      return h('input', {
        value: row.editValue,
        onInput: (e) => { row.editValue = e.target.value },
        style: 'width: 200px; padding: 4px 8px; border: 1px solid #ddd; border-radius: 4px;'
      })
    }
  },
  {
    title: '描述',
    key: 'description',
    width: 200,
    ellipsis: { tooltip: true }
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 180,
    render(row) {
      return formatTime(row.updated_at)
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right',
    render(row) {
      if (!row.editing) {
        return h(
          nButton,
          { type: 'primary', size: 'small', onClick: () => handleEdit(row) },
          { icon: () => h(nIcon, null, { default: () => h(CreateOutline) }), default: () => '编辑' }
        )
      }
      return h('div', { style: 'display: flex; gap: 8px;' }, [
        h(
          nButton,
          { type: 'primary', size: 'small', onClick: () => handleSave(row) },
          { icon: () => h(nIcon, null, { default: () => h(CheckmarkOutline) }), default: () => '保存' }
        ),
        h(
          nButton,
          { type: 'info', size: 'small', onClick: () => handleCancel(row) },
          { icon: () => h(nIcon, null, { default: () => h(CloseOutline) }), default: () => '取消' }
        )
      ])
    }
  }
]

onMounted(() => { loadData() })
</script>

<style lang="scss" scoped>
.page-card {
  margin: 16px;
}
</style>
