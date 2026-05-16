<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的工单</h1>
        <p class="page-subtitle">查看我创建的运维工单</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="$router.push('/workorder/create')">
          <el-icon><Plus /></el-icon> 创建工单
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card" @click="handleStatClick('')">
        <div class="stat-value">{{ stats.total || 0 }}</div>
        <div class="stat-label">全部</div>
      </div>
      <div class="stat-card pending" @click="handleStatClick('pending')">
        <div class="stat-value">{{ stats.pending || 0 }}</div>
        <div class="stat-label">待处理</div>
      </div>
      <div class="stat-card processing" @click="handleStatClick('processing')">
        <div class="stat-value">{{ stats.processing || 0 }}</div>
        <div class="stat-label">处理中</div>
      </div>
      <div class="stat-card success" @click="handleStatClick('closed')">
        <div class="stat-value">{{ stats.closed || 0 }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-card info" @click="handleStatClick('cancelled')">
        <div class="stat-value">{{ stats.cancelled || 0 }}</div>
        <div class="stat-label">已关闭</div>
      </div>
    </div>

    <!-- 状态筛选 tabs -->
    <div class="filter-tabs">
      <el-tabs v-model="filterStatus" @tab-change="handleStatusChange">
        <el-tab-pane label="全部" name="" />
        <el-tab-pane label="待处理" name="pending" />
        <el-tab-pane label="处理中" name="processing" />
        <el-tab-pane label="已完成" name="closed" />
        <el-tab-pane label="已关闭" name="cancelled" />
      </el-tabs>
    </div>

    <!-- 工单表格 -->
    <div class="table-container">
      <el-table :data="workorderList" v-loading="loading" style="width: 100%">
        <el-table-column prop="work_no" label="工单号" width="140" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="getPriorityType(row.priority)">{{ getPriorityText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">查看</el-button>
            <el-button 
              v-if="canCancel(row)" 
              type="danger" 
              link 
              size="small" 
              @click="handleCancel(row)"
            >取消</el-button>
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

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="工单详情" width="700px">
      <div class="detail-info" v-if="currentWorkorder">
        <div class="detail-row">
          <span class="detail-label">工单号：</span>
          <span>{{ currentWorkorder.work_no || currentWorkorder.id }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">标题：</span>
          <span>{{ currentWorkorder.title }}</span>
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

      <!-- 流转记录 -->
      <el-divider v-if="flowList.length > 0">处理流转记录</el-divider>
      <div class="flow-list" v-if="flowList.length > 0">
        <div v-for="flow in flowList" :key="flow.id" class="flow-item">
          <div class="flow-header">
            <span class="flow-action">{{ flow.action || '处理' }}</span>
            <span class="flow-time">{{ formatTime(flow.created_at) }}</span>
          </div>
          <div class="flow-content" v-if="flow.comment">{{ flow.comment }}</div>
          <div class="flow-operator" v-if="flow.operator_name">操作人：{{ flow.operator_name }}</div>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { workorder } from '@/api'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const filterStatus = ref('')
const workorderList = ref([])
const detailVisible = ref(false)
const currentWorkorder = ref(null)
const flowList = ref([])
const currentUser = ref('')

const stats = reactive({
  total: 0,
  pending: 0,
  processing: 0,
  closed: 0,
  cancelled: 0
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const getPriorityType = (p) => {
  const map = { P1: 'danger', P2: 'warning', P3: 'info', P4: 'info' }
  return map[p] || 'info'
}

const getPriorityText = (p) => {
  const map = { P1: 'P1危险', P2: 'P2警告', P3: 'P3信息', P4: 'P4信息' }
  return map[p] || p || '-'
}

const getStatusType = (s) => {
  const map = { pending: 'warning', processing: 'primary', closed: 'success', cancelled: 'info' }
  return map[s] || 'info'
}

const getStatusText = (s) => {
  const map = { pending: '待处理', processing: '处理中', closed: '已完成', cancelled: '已关闭' }
  return map[s] || s || '-'
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

const getCurrentUser = () => {
  try {
    const userInfo = localStorage.getItem('userInfo')
    if (userInfo) {
      const user = JSON.parse(userInfo)
      currentUser.value = user.username || ''
    }
  } catch (e) {
    console.error('Failed to parse userInfo:', e)
  }
}

const loadStatistics = async () => {
  try {
    const res = await workorder.getStatistics()
    stats.total = res.total || 0
    stats.pending = res.pending || 0
    stats.processing = res.processing || 0
    stats.closed = res.closed || 0
    stats.cancelled = res.cancelled || 0
  } catch (error) {
    console.error('Load statistics error:', error)
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      creator: currentUser.value
    }
    if (filterStatus.value) params.status = filterStatus.value

    const res = await workorder.getList(params)
    workorderList.value = res.items || res.list || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load workorders error:', error)
    workorderList.value = []
  } finally {
    loading.value = false
  }
}

const handleStatusChange = () => {
  pagination.page = 1
  loadData()
}

const handleStatClick = (status) => {
  filterStatus.value = status
  handleStatusChange()
}

const canCancel = (row) => {
  return row.status === 'pending' && row.creator === currentUser.value
}

const handleView = async (row) => {
  currentWorkorder.value = row
  detailVisible.value = true
  
  // 加载流转记录
  try {
    const res = await workorder.getFlows(row.id)
    flowList.value = res.items || res.list || []
  } catch (error) {
    console.error('Load flows error:', error)
    flowList.value = []
  }
}

const handleCancel = (row) => {
  ElMessageBox.confirm('确定要取消该工单吗？', '取消工单', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await workorder.update(row.id, { status: 'cancelled' })
      ElMessage.success('工单已取消')
      loadData()
      loadStatistics()
    } catch (error) {
      console.error('Cancel workorder error:', error)
      ElMessage.error('取消失败')
    }
  }).catch(() => {})
}

onMounted(() => {
  getCurrentUser()
  loadStatistics()
  loadData()
})
</script>

<style lang="scss" scoped>
.page-container { padding: 24px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.page-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: #909399;
}

.stats-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;

  &:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }

  .stat-value { font-size: 28px; font-weight: 600; color: #303133; }
  .stat-label { font-size: 14px; color: #909399; margin-top: 4px; }

  &.pending .stat-value { color: #e6a23c; }
  &.processing .stat-value { color: #409eff; }
  &.success .stat-value { color: #67c23a; }
  &.info .stat-value { color: #909399; }
}

.filter-tabs {
  background: #fff;
  border-radius: 8px;
  margin-bottom: 16px;
  padding: 0 16px;
}

.table-container {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.empty-state { padding: 60px 0; text-align: center; }

.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }

.detail-info { display: flex; flex-direction: column; gap: 12px; }

.detail-row {
  display: flex;
  align-items: flex-start;

  .detail-label { width: 80px; color: #909399; flex-shrink: 0; }
}

.flow-list { margin-top: 16px; }

.flow-item {
  padding: 12px;
  background: #f7f8fa;
  border-radius: 4px;
  margin-bottom: 8px;

  .flow-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .flow-action { font-weight: 500; color: #303133; }
  .flow-time { color: #909399; font-size: 12px; }
  .flow-content { color: #606266; margin: 4px 0; }
  .flow-operator { color: #909399; font-size: 12px; }
}

:deep(.el-table .el-table__header th) { background: #f7f8fa; }
:deep(.el-tabs__header) { margin: 0; }
</style>
