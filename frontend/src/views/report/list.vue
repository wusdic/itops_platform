<template>
  <div class="report-list-container">
    <!-- Statistics Summary Cards -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" class="stats-grid">
      <n-gi>
        <n-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon total">
              <n-icon :size="32"><DocumentTextOutline /></n-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total || 0 }}</div>
              <div class="stat-label">Total Reports</div>
            </div>
          </div>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon completed">
              <n-icon :size="32"><PlayOutline /></n-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.completed || 0 }}</div>
              <div class="stat-label">Completed</div>
            </div>
          </div>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon failed">
              <n-icon :size="32"><TrashOutline /></n-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.failed || 0 }}</div>
              <div class="stat-label">Failed</div>
            </div>
          </div>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon generating">
              <n-icon :size="32"><RefreshOutline /></n-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.generating || 0 }}</div>
              <div class="stat-label">Generating</div>
            </div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Filter Bar -->
    <n-card class="filter-card" :content-style="{ padding: '16px' }">
      <n-space :size="16" align="center" justify="space-between">
        <n-space :size="12" align="center">
          <n-select
            v-model:value="filters.type"
            :options="typeOptions"
            placeholder="Report Type"
            clearable
            style="width: 150px"
          />
          <n-select
            v-model:value="filters.status"
            :options="statusOptions"
            placeholder="Status"
            clearable
            style="width: 140px"
          />
          <n-date-picker
            v-model:value="filters.dateRange"
            type="daterange"
            range
            clearable
            placeholder="Date Range"
            style="width: 280px"
          />
        </n-space>
        <n-space :size="12" align="center">
          <n-button type="primary" @click="handleSearch">
            <template #icon>
              <n-icon><DocumentTextOutline /></n-icon>
            </template>
            Search
          </n-button>
          <n-button @click="handleReset">Reset</n-button>
          <n-button type="primary" @click="handleRefresh">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
          </n-button>
        </n-space>
      </n-space>
    </n-card>

    <!-- Reports Data Table -->
    <n-card class="table-card">
      <n-data-table
        :columns="columns"
        :data="reportList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- Preview Modal -->
    <n-modal
      v-model:show="previewModal.show"
      preset="card"
      title="Report Preview"
      :style="{ width: '80%', maxWidth: '1000px' }"
      :segmented="{ content: true, footer: true }"
    >
      <div class="preview-content">
        <n-spin :show="previewModal.loading">
          <div v-html="previewModal.content" class="preview-html"></div>
        </n-spin>
      </div>
      <template #footer>
        <n-space justify="end">
          <n-button @click="previewModal.show = false">Close</n-button>
          <n-button type="primary" @click="handleDownload(previewModal.reportId)">
            <template #icon>
              <n-icon><DownloadOutline /></n-icon>
            </template>
            Download
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- Delete Confirmation Modal -->
    <n-modal
      v-model:show="deleteModal.show"
      preset="dialog"
      title="Confirm Delete"
      :content="deleteModal.message"
      positive-text="Delete"
      negative-text="Cancel"
      @positive-click="handleConfirmDelete"
      @negative-click="deleteModal.show = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import {
  DocumentTextOutline,
  DownloadOutline,
  TrashOutline,
  PlayOutline,
  EyeOutline,
  RefreshOutline
} from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const reportList = ref([])
const stats = ref({})

// Filters
const filters = reactive({
  type: null,
  status: null,
  dateRange: null
})

// Pagination
const pagination = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page) => {
    pagination.page = page
    fetchReportList()
  },
  onUpdatePageSize: (pageSize) => {
    pagination.pageSize = pageSize
    pagination.page = 1
    fetchReportList()
  }
})

// Options
const typeOptions = [
  { label: 'Daily Report', value: 'daily' },
  { label: 'Weekly Report', value: 'weekly' },
  { label: 'Monthly Report', value: 'monthly' },
  { label: 'Quarterly Report', value: 'quarterly' },
  { label: 'Annual Report', value: 'annual' },
  { label: 'Custom Report', value: 'custom' }
]

const statusOptions = [
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
  { label: 'Generating', value: 'generating' },
  { label: 'Pending', value: 'pending' }
]

// Preview Modal
const previewModal = reactive({
  show: false,
  loading: false,
  content: '',
  reportId: null
})

// Delete Modal
const deleteModal = reactive({
  show: false,
  message: '',
  reportId: null
})

// Table Columns
const columns = [
  {
    title: 'Report Name',
    key: 'name',
    width: 200,
    ellipsis: { tooltip: true }
  },
  {
    title: 'Type',
    key: 'type',
    width: 120,
    render(row) {
      const typeLabels = {
        daily: 'Daily',
        weekly: 'Weekly',
        monthly: 'Monthly',
        quarterly: 'Quarterly',
        annual: 'Annual',
        custom: 'Custom'
      }
      return typeLabels[row.type] || row.type
    }
  },
  {
    title: 'Template',
    key: 'template_name',
    width: 150,
    ellipsis: { tooltip: true }
  },
  {
    title: 'Status',
    key: 'status',
    width: 110,
    render(row) {
      const statusConfig = {
        completed: { type: 'success', label: 'Completed' },
        failed: { type: 'error', label: 'Failed' },
        generating: { type: 'info', label: 'Generating' },
        pending: { type: 'warning', label: 'Pending' }
      }
      const config = statusConfig[row.status] || { type: 'default', label: row.status }
      return h(
        NTag,
        { type: config.type, bordered: false },
        { default: () => config.label }
      )
    }
  },
  {
    title: 'Format',
    key: 'format',
    width: 90,
    render(row) {
      return row.format?.toUpperCase() || 'PDF'
    }
  },
  {
    title: 'Created At',
    key: 'created_at',
    width: 180,
    render(row) {
      return formatDate(row.created_at)
    }
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 180,
    fixed: 'right',
    render(row) {
      return h('div', { class: 'action-buttons' }, [
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            onClick: () => handlePreview(row)
          },
          {
            icon: () => h(NIcon, null, { default: () => h(EyeOutline) })
          }
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            disabled: row.status !== 'completed',
            onClick: () => handleDownload(row.id)
          },
          {
            icon: () => h(NIcon, null, { default: () => h(DownloadOutline) })
          }
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            type: 'error',
            onClick: () => handleDelete(row)
          },
          {
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) })
          }
        )
      ])
    }
  }
]

// Helper Functions
function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
}

// API Functions
async function fetchStats() {
  try {
    const response = await fetch('http://localhost:8000/api/v1/reports/stats', {
      method: 'GET',
      headers: getHeaders()
    })
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    const data = await response.json()
    stats.value = data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
    message.error('Failed to load statistics')
    stats.value = { total: 0, completed: 0, failed: 0, generating: 0 }
  }
}

async function fetchReportList() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: pagination.page,
      page_size: pagination.pageSize
    })
    
    if (filters.type) params.append('type', filters.type)
    if (filters.status) params.append('status', filters.status)
    if (filters.dateRange && filters.dateRange[0]) {
      params.append('start_date', new Date(filters.dateRange[0]).toISOString())
      params.append('end_date', new Date(filters.dateRange[1]).toISOString())
    }

    const response = await fetch(`http://localhost:8000/api/v1/reports/?${params}`, {
      method: 'GET',
      headers: getHeaders()
    })
    
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    const data = await response.json()
    reportList.value = data.items || data
    pagination.itemCount = data.total || reportList.value.length
  } catch (error) {
    console.error('Failed to fetch report list:', error)
    message.error('Failed to load report list')
    reportList.value = []
  } finally {
    loading.value = false
  }
}

async function fetchReportPreview(id) {
  previewModal.loading = true
  try {
    const response = await fetch(`http://localhost:8000/api/v1/reports/${id}/preview`, {
      method: 'GET',
      headers: getHeaders()
    })
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    const data = await response.json()
    previewModal.content = data.content || data.html || '<p>No preview available</p>'
  } catch (error) {
    console.error('Failed to fetch preview:', error)
    message.error('Failed to load report preview')
    previewModal.content = '<n-empty description="Preview not available" />'
  } finally {
    previewModal.loading = false
  }
}

async function downloadReport(id) {
  try {
    const response = await fetch(`http://localhost:8000/api/v1/reports/${id}/download`, {
      method: 'GET',
      headers: getHeaders()
    })
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${id}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    message.success('Report downloaded successfully')
  } catch (error) {
    console.error('Failed to download report:', error)
    message.error('Failed to download report')
  }
}

async function deleteReport(id) {
  try {
    const response = await fetch(`http://localhost:8000/api/v1/reports/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    })
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    message.success('Report deleted successfully')
    fetchReportList()
    fetchStats()
  } catch (error) {
    console.error('Failed to delete report:', error)
    message.error('Failed to delete report')
  }
}

// Action Handlers
function handleSearch() {
  pagination.page = 1
  fetchReportList()
}

function handleReset() {
  filters.type = null
  filters.status = null
  filters.dateRange = null
  pagination.page = 1
  fetchReportList()
}

function handleRefresh() {
  fetchReportList()
  fetchStats()
}

function handlePreview(row) {
  previewModal.reportId = row.id
  previewModal.show = true
  previewModal.content = ''
  fetchReportPreview(row.id)
}

function handleDownload(id) {
  downloadReport(id)
}

function handleDelete(row) {
  deleteModal.reportId = row.id
  deleteModal.message = `Are you sure you want to delete report "${row.name}"? This action cannot be undone.`
  deleteModal.show = true
}

function handleConfirmDelete() {
  if (deleteModal.reportId) {
    deleteReport(deleteModal.reportId)
  }
  deleteModal.show = false
}

// Lifecycle
onMounted(() => {
  fetchReportList()
  fetchStats()
})
</script>

<style scoped>
.report-list-container {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-grid {
  margin-bottom: 8px;
}

.stat-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.total {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.completed {
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
}

.stat-icon.failed {
  background: linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%);
}

.stat-icon.generating {
  background: linear-gradient(135deg, #1890ff 0%, #69c0ff 100%);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #8c8c8c;
  margin-top: 4px;
}

.filter-card {
  margin-bottom: 8px;
}

.table-card {
  flex: 1;
}

.action-buttons {
  display: flex;
  gap: 4px;
}

.preview-content {
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.preview-html {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
