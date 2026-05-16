<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">知识库 / SOP列表</h1>
        <p class="page-subtitle">运维标准操作流程</p>
      </div>
      <div class="page-actions">
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
        <n-descriptions-item label="分类">{{ currentSOP.category }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="getStatusType(currentSOP.status)">{{ currentSOP.status }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="作者">{{ currentSOP.author }}</n-descriptions-item>
        <n-descriptions-item label="标签">
          <n-space>
            <n-tag v-for="tag in currentSOP.tags" :key="tag" size="small">{{ tag }}</n-tag>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { NIcon, useMessage, NTag, NButton } from 'naive-ui'
import { h } from 'vue'
import { Refresh } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const list = ref([])
const searchKeyword = ref('')
const filterStatus = ref(null)
const filterCategory = ref(null)
const detailModalVisible = ref(false)
const currentSOP = ref(null)

const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '待审核', value: 'pending_review' },
  { label: '已通过', value: 'approved' },
  { label: '已发布', value: 'published' }
]

const categoryOptions = [
  { label: '系统运维', value: 'system' },
  { label: '网络运维', value: 'network' },
  { label: '应用运维', value: 'application' },
  { label: '安全运维', value: 'security' }
]

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
  { title: '分类', key: 'category', width: 100 },
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
  { title: '操作', key: 'actions', width: 100,
    render: (row) => h('button', { style: 'color:#18a058;background:none;border:none;cursor:pointer', onClick: () => showDetail(row) }, '查看')
  }
]

onMounted(() => {
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
    if (filterCategory.value) params.append('category', filterCategory.value)
    
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
