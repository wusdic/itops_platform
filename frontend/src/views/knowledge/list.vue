<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">知识库 / SOP列表</h1>
        <p class="page-subtitle">运维标准操作流程</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="openCreateModal">
          <template #icon>
            <n-icon><Add /></n-icon>
          </template>
          创建文档
        </n-button>
        <n-button type="primary" @click="loadData">
          <template #icon>
            <n-icon><Refresh /></n-icon>
          </template>
          刷新
        </n-button>
      </div>
    </div>

    <!-- 筛选条件 -->
    <n-card class="mb-4">
      <n-space align="center">
        <n-input
          v-model:value="searchKeyword"
          placeholder="搜索标题"
          clearable
          style="width: 200px"
          @keyup.enter="loadData"
        />
        <n-select
          v-model:value="filterStatus"
          :options="statusOptions"
          placeholder="按状态筛选"
          clearable
          style="width: 150px"
          @update:value="loadData"
        />
        <n-select
          v-model:value="filterCategory"
          :options="categoryOptions"
          placeholder="按分类筛选"
          clearable
          style="width: 150px"
          @update:value="loadData"
        />
      </n-space>
    </n-card>

    <!-- SOP列表 -->
    <n-card title="SOP文档列表">
      <n-data-table
        :columns="columns"
        :data="list"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </n-card>

    <!-- 详情弹窗 -->
    <n-modal
      v-model:show="detailModalVisible"
      preset="card"
      title="SOP详情"
      style="width: 600px"
    >
      <n-descriptions v-if="currentSOP" label-placement="top" :column="1">
        <n-descriptions-item label="标题">{{ currentSOP.title }}</n-descriptions-item>
        <n-descriptions-item label="分类">{{ currentSOP.category_name }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="getStatusType(currentSOP.status)">{{ currentSOP.status }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="作者">{{ currentSOP.author }}</n-descriptions-item>
        <n-descriptions-item label="标签">
          <n-space>
            <n-tag v-for="tag in (currentSOP.tags || [])" :key="tag" size="small">{{ tag }}</n-tag>
          </n-space>
        </n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ currentSOP.created_at }}</n-descriptions-item>
        <n-descriptions-item label="更新时间">{{ currentSOP.updated_at }}</n-descriptions-item>
      </n-descriptions>
      <template #footer>
        <n-space justify="end">
          <n-button @click="detailModalVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 创建/编辑弹窗 -->
    <n-modal
      v-model:show="formModalVisible"
      preset="card"
      :title="isEditing ? '编辑文档' : '创建文档'"
      style="width: 600px"
    >
      <n-form :model="formData" label-placement="top">
        <n-form-item label="标题" required>
          <n-input v-model:value="formData.title" placeholder="请输入文档标题" />
        </n-form-item>
        <n-form-item label="分类" required>
          <n-select v-model:value="formData.category_id" :options="categoryOptions" placeholder="请选择分类" />
        </n-form-item>
        <n-form-item label="内容">
          <n-input v-model:value="formData.content" type="textarea" placeholder="请输入文档内容" :rows="6" />
        </n-form-item>
        <n-form-item label="标签（逗号分隔）">
          <n-input v-model:value="formData.tags_input" placeholder="例如: 运维, 系统, 监控" />
        </n-form-item>
        <n-form-item label="状态" required>
          <n-select v-model:value="formData.status" :options="statusOptionsForForm" placeholder="请选择状态" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="formModalVisible = false">取消</n-button>
          <n-button type="primary" @click="submitForm" :loading="formLoading">确认</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { NIcon, useMessage, useDialog, NTag, NButton } from 'naive-ui'
import { h } from 'vue'
import { Refresh, Add } from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const list = ref([])
const searchKeyword = ref('')
const filterStatus = ref(null)
const filterCategory = ref(null)
const detailModalVisible = ref(false)
const currentSOP = ref(null)

// Form modal state
const formModalVisible = ref(false)
const isEditing = ref(false)
const formLoading = ref(false)
const editingId = ref(null)
const formData = reactive({
  title: '',
  category_id: null,
  content: '',
  tags_input: '',
  status: 'draft'
})

const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '待审核', value: 'pending_review' },
  { label: '已通过', value: 'approved' },
  { label: '已发布', value: 'published' }
]

// Simplified status options for form (only draft/published as requested)
const statusOptionsForForm = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' }
]

// Categories loaded from API
const categoryOptions = ref([])

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const columns = [
  { title: '序号', type: 'index', width: 60 },
  { title: '标题', key: 'title', width: 200,
    render: (row) => h('a', { href: 'javascript:void(0)', onClick: () => showDetail(row) }, row.title)
  },
  { title: '分类', key: 'category_name', width: 100 },
  { title: '状态', key: 'status', width: 100,
    render: (row) => {
      const typeMap = { draft: 'default', pending_review: 'warning', approved: 'info', published: 'success' }
      return h(NTag, { type: typeMap[row.status] || 'default', size: 'small' }, () => row.status)
    }
  },
  { title: '作者', key: 'author', width: 100 },
  { title: '标签', key: 'tags', width: 200,
    render: (row) => (row.tags || []).map(tag => h('span', { style: 'margin-right: 4px' }, `#${tag}`))
  },
  { title: '更新时间', key: 'updated_at', width: 180 },
  { title: '操作', key: 'actions', width: 280,
    render: (row) => h('div', { style: 'display:flex;gap:8px' }, [
      h(NButton, { size: 'small', onClick: () => openEditModal(row) }, () => '编辑'),
      row.status === 'draft' && h(NButton, { size: 'small', type: 'warning', onClick: () => submitReview(row) }, () => '提交审核'),
      row.status === 'pending_review' && h(NButton, { size: 'small', type: 'success', onClick: () => approve(row) }, () => '审核通过'),
      h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, () => '删除')
    ])
  }
]

onMounted(() => {
  loadCategories()
  loadData()
})

const loadData = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({
      page: pagination.page,
      page_size: pagination.pageSize
    })
    if (searchKeyword.value) params.append('keyword', searchKeyword.value)
    if (filterStatus.value) params.append('status', filterStatus.value)
    if (filterCategory.value) params.append('category_id', filterCategory.value)
    
    const res = await fetch(`/api/v1/knowledge/sop?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    list.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载失败: ${e.message}`)
    console.error('[knowledge/list] loadData error:', e)
    list.value = []
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/knowledge/category', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    categoryOptions.value = (data.items || []).map(c => ({ label: c.name, value: c.id }))
  } catch (e) {
    console.error('[knowledge/list] loadCategories error:', e)
  }
}

const openCreateModal = () => {
  isEditing.value = false
  editingId.value = null
  formData.title = ''
  formData.category_id = null
  formData.content = ''
  formData.tags_input = ''
  formData.status = 'draft'
  formModalVisible.value = true
}

const openEditModal = async (row) => {
  isEditing.value = true
  editingId.value = row.id
  formModalVisible.value = true
  formLoading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/knowledge/sop/${row.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    formData.title = data.title || ''
    formData.category_id = data.category_id || null
    formData.content = data.content || ''
    formData.tags_input = (data.tags || []).join(', ')
    formData.status = data.status || 'draft'
  } catch (e) {
    message.error(`加载文档详情失败: ${e.message}`)
    console.error('[knowledge/list] openEditModal error:', e)
    formModalVisible.value = false
  } finally {
    formLoading.value = false
  }
}

const submitForm = async () => {
  if (!formData.title) {
    message.warning('请输入文档标题')
    return
  }
  if (!formData.category_id) {
    message.warning('请选择文档分类')
    return
  }
  formLoading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const tags = formData.tags_input ? formData.tags_input.split(',').map(t => t.trim()).filter(t => t) : []
    const payload = {
      title: formData.title,
      category_id: formData.category_id,
      content: formData.content,
      tags: tags,
      status: formData.status
    }
    const url = isEditing.value ? `/api/v1/knowledge/sop/${editingId.value}` : '/api/v1/knowledge/sop'
    const method = 'PUT'
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success(isEditing.value ? '文档更新成功' : '文档创建成功')
    formModalVisible.value = false
    loadData()
  } catch (e) {
    message.error(`${isEditing.value ? '更新' : '创建'}失败: ${e.message}`)
    console.error('[knowledge/list] submitForm error:', e)
  } finally {
    formLoading.value = false
  }
}

const handleDelete = (row) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除文档「${row.title}」吗？此操作不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const token = localStorage.getItem('token') || ''
        const res = await fetch(`/api/v1/knowledge/sop/${row.id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        message.success('删除成功')
        loadData()
      } catch (e) {
        message.error(`删除失败: ${e.message}`)
        console.error('[knowledge/list] handleDelete error:', e)
      }
    }
  })
}

const submitReview = async (row) => {
  dialog.info({
    title: '确认提交审核',
    content: `确定要提交文档「${row.title}」进行审核吗？`,
    positiveText: '确认提交',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const token = localStorage.getItem('token') || ''
        const res = await fetch(`/api/v1/knowledge/sop/${row.id}/review`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        message.success('提交审核成功')
        loadData()
      } catch (e) {
        message.error(`提交审核失败: ${e.message}`)
        console.error('[knowledge/list] submitReview error:', e)
      }
    }
  })
}

const approve = async (row) => {
  dialog.info({
    title: '确认审核通过',
    content: `确定要让文档「${row.title}」审核通过吗？`,
    positiveText: '确认通过',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const token = localStorage.getItem('token') || ''
        const res = await fetch(`/api/v1/knowledge/sop/${row.id}/approve`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        message.success('审核通过')
        loadData()
      } catch (e) {
        message.error(`审核操作失败: ${e.message}`)
        console.error('[knowledge/list] approve error:', e)
      }
    }
  })
}

const handlePageChange = (page) => {
  pagination.page = page
  loadData()
}

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadData()
}

const showDetail = (row) => {
  currentSOP.value = row
  detailModalVisible.value = true
}

const getStatusType = (status) => {
  const typeMap = { draft: 'default', pending_review: 'warning', approved: 'info', published: 'success' }
  return typeMap[status] || 'default'
}
</script>



<style lang="scss" scoped>
.mb-4 { margin-bottom: 16px; }
</style>
