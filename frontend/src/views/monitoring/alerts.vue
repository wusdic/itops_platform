<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">告警管理</h1>
        <p class="page-subtitle">查看和处理所有告警事件</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索告警标题/设备" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterStatus" placeholder="告警状态" style="width: 130px" clearable @change="handleSearch">
        <el-option label="激活" value="active" />
        <el-option label="已确认" value="acknowledged" />
        <el-option label="已解决" value="resolved" />
      </el-select>
      <el-select v-model="filterSeverity" placeholder="严重程度" style="width: 130px" clearable @change="handleSearch">
        <el-option label="严重" value="critical" />
        <el-option label="高" value="high" />
        <el-option label="中" value="medium" />
        <el-option label="低" value="low" />
        <el-option label="提示" value="info" />
      </el-select>
    </div>

    <!-- 告警列表 -->
    <div class="table-container">
      <el-table :data="alertList" v-loading="loading" style="width: 100%" stripe>
        <el-table-column prop="level" label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.level)" size="small">
              {{ getSeverityText(row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="告警标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="device_name" label="设备名称" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.device_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="device_ip" label="IP地址" width="130">
          <template #default="{ row }">{{ row.device_ip || '-' }}</template>
        </el-table-column>
        <el-table-column prop="metric_name" label="指标" width="120">
          <template #default="{ row }">{{ row.metric_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="occurred_at" label="发生时间" width="160">
          <template #default="{ row }">{{ formatTime(row.occurred_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">详情</el-button>
            <el-button v-if="row.status === 'active'" type="warning" link size="small" @click="handleAck(row)">确认</el-button>
            <el-button v-if="row.status !== 'resolved'" type="success" link size="small" @click="handleResolve(row)">解决</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- 告警详情弹窗 -->
    <el-dialog v-model="detailVisible" title="告警详情" width="600px">
      <div v-if="currentAlert" class="alert-detail">
        <div class="detail-row"><span class="label">告警标题</span><span class="value">{{ currentAlert.title }}</span></div>
        <div class="detail-row"><span class="label">严重程度</span><span class="value">
          <el-tag :type="getSeverityType(currentAlert.level)" size="small">{{ getSeverityText(currentAlert.level) }}</el-tag>
        </span></div>
        <div class="detail-row"><span class="label">状态</span><span class="value">
          <el-tag :type="getStatusTagType(currentAlert.status)" size="small">{{ getStatusText(currentAlert.status) }}</el-tag>
        </span></div>
        <div class="detail-row"><span class="label">设备名称</span><span class="value">{{ currentAlert.device_name || '-' }}</span></div>
        <div class="detail-row"><span class="label">设备IP</span><span class="value">{{ currentAlert.device_ip || '-' }}</span></div>
        <div class="detail-row"><span class="label">指标名称</span><span class="value">{{ currentAlert.metric_name || '-' }}</span></div>
        <div class="detail-row"><span class="label">当前值</span><span class="value">{{ currentAlert.metric_value || '-' }} {{ currentAlert.unit || '' }}</span></div>
        <div class="detail-row"><span class="label">阈值</span><span class="value">{{ currentAlert.threshold || '-' }}</span></div>
        <div class="detail-row"><span class="label">发生时间</span><span class="value">{{ formatTime(currentAlert.occurred_at) }}</span></div>
        <div class="detail-row"><span class="label">告警描述</span><span class="value">{{ currentAlert.message || '-' }}</span></div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button v-if="currentAlert && currentAlert.status === 'active'" type="warning" @click="handleAck(currentAlert)">确认告警</el-button>
        <el-button v-if="currentAlert && currentAlert.status !== 'resolved'" type="success" @click="handleResolve(currentAlert)">解决告警</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { alerts } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterSeverity = ref('')
const alertList = ref([])
const detailVisible = ref(false)
const currentAlert = ref(null)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

onMounted(() => {
  loadData()
})

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (searchKeyword.value) params.host = searchKeyword.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterSeverity.value) params.severity = filterSeverity.value

    const res = await alerts.getList(params).catch(() => ({ items: [], total: 0 }))
    alertList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load alerts error:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

const handleView = (row) => {
  currentAlert.value = row
  detailVisible.value = true
}

const handleAck = async (row) => {
  try {
    await alerts.handle(row.id, {})
    ElMessage.success('告警已确认')
    detailVisible.value = false
    loadData()
  } catch (error) {
    console.error('Ack alert error:', error)
    ElMessage.error('操作失败')
  }
}

const handleResolve = async (row) => {
  try {
    await alerts.handle(row.id, { action: 'resolve' })
    ElMessage.success('告警已解决')
    detailVisible.value = false
    loadData()
  } catch (error) {
    console.error('Resolve alert error:', error)
    ElMessage.error('操作失败')
  }
}

const getSeverityType = (level) => {
  const map = { critical: 'danger', high: 'danger', medium: 'warning', low: 'info', info: 'info' }
  return map[level] || 'info'
}

const getSeverityText = (level) => {
  const map = { critical: '严重', high: '高', medium: '中', low: '低', info: '提示' }
  return map[level] || level
}

const getStatusTagType = (status) => {
  const map = { active: 'danger', acknowledged: 'warning', resolved: 'success' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { active: '激活', acknowledged: '已确认', resolved: '已解决' }
  return map[status] || status
}
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.page-subtitle {
  margin: 4px 0 0;
  color: #909399;
  font-size: 13px;
}

.page-actions {
  display: flex;
  gap: 8px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
}

.table-container {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.alert-detail {
  .detail-row {
    display: flex;
    padding: 8px 0;
    border-bottom: 1px solid #f2f3f5;
    &:last-child { border-bottom: none; }
    .label {
      width: 100px;
      color: #909399;
      flex-shrink: 0;
    }
    .value {
      flex: 1;
      color: #303133;
    }
  }
}

:deep(.el-table) {
  .el-table__header th {
    background: #f7f8fa;
  }
}
</style>
