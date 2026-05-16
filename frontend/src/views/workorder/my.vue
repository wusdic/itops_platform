<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的工单</h1>
        <p class="page-subtitle">查看和处理我负责的运维工单</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索工单标题" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterStatus" placeholder="工单状态" style="width: 140px" clearable @change="handleSearch">
        <el-option label="待处理" value="pending" />
        <el-option label="处理中" value="processing" />
        <el-option label="已完成" value="closed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-select v-model="filterPriority" placeholder="优先级" style="width: 120px" clearable @change="handleSearch">
        <el-option label="紧急" value="urgent" />
        <el-option label="高" value="high" />
        <el-option label="中" value="medium" />
        <el-option label="低" value="low" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="workorderList" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="工单ID" width="80" />
        <el-table-column prop="title" label="工单标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="getPriorityType(row.priority)">{{ getPriorityText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            {{ getTypeText(row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="100" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && workorderList.length === 0" class="empty-state">
        <el-empty description="暂无工单记录" />
      </div>

      <div class="pagination" v-if="pagination.total > 0">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="工单详情" width="600px">
      <div class="detail-info" v-if="currentWorkorder">
        <div class="detail-row">
          <span class="detail-label">工单ID：</span>
          <span>{{ currentWorkorder.id }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">标题：</span>
          <span>{{ currentWorkorder.title }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">类型：</span>
          <span>{{ getTypeText(currentWorkorder.type) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">优先级：</span>
          <el-tag size="small" :type="getPriorityType(currentWorkorder.priority)">
            {{ getPriorityText(currentWorkorder.priority) }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">状态：</span>
          <el-tag size="small" :type="getStatusType(currentWorkorder.status)">
            {{ getStatusText(currentWorkorder.status) }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">描述：</span>
          <span>{{ currentWorkorder.description || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">创建时间：</span>
          <span>{{ formatTime(currentWorkorder.created_at) }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { workorder } from '@/api'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterPriority = ref('')
const workorderList = ref([])
const detailVisible = ref(false)
const currentWorkorder = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const getPriorityType = (p) => ({ urgent: 'danger', high: 'warning', medium: 'primary', low: 'info' }[p] || 'info')
const getPriorityText = (p) => ({ urgent: '紧急', high: '高', medium: '中', low: '低' }[p] || p)
const getStatusType = (s) => ({ pending: 'info', processing: 'primary', closed: 'success', cancelled: 'info' }[s] || 'info')
const getStatusText = (s) => ({ pending: '待处理', processing: '处理中', closed: '已完成', cancelled: '已取消' }[s] || s)
const getTypeText = (t) => ({ fault: '故障报修', requirement: '需求申请', change: '变更申请', inspection: '日常巡检' }[t] || t)

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterPriority.value) params.priority = filterPriority.value

    const res = await workorder.getList(params).catch(() => ({ items: [], total: 0 }))
    workorderList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load workorders error:', error)
    workorderList.value = []
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

const handleView = (row) => {
  currentWorkorder.value = row
  detailVisible.value = true
}
</script>

<style lang="scss" scoped>
.page-container { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { margin: 0; font-size: 24px; font-weight: 600; color: #303133; }
.page-subtitle { margin: 8px 0 0; font-size: 14px; color: #909399; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.table-container { background: #fff; border-radius: 8px; padding: 16px; }
.empty-state { padding: 60px 0; text-align: center; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.detail-info { display: flex; flex-direction: column; gap: 12px; }
.detail-row { display: flex; align-items: flex-start; }
.detail-label { width: 80px; color: #909399; flex-shrink: 0; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
