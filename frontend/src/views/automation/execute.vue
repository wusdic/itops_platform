<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">执行历史</h1>
        <p class="page-subtitle">查看自动化脚本执行记录并进行回滚操作</p>
      </div>
      <div class="page-actions">
        <n-button @click="handleRefresh">
          <n-icon><RefreshOutline /></n-icon> 刷新
        </n-button>
      </div>
    </div>
    <div class="filter-bar">
      <n-input v-model="searchKeyword" placeholder="搜索执行ID或脚本名称" style="width: 240px" clearable @change="handleSearch" />
      <n-select v-model="filterStatus" placeholder="执行状态" style="width: 140px" clearable @change="handleSearch">
        <n-option label="成功" value="success" />
        <n-option label="失败" value="failed" />
        <n-option label="进行中" value="running" />
        <n-option label="已回滚" value="rolled_back" />
      </n-select>
    </div>
    <div class="table-container">
      <n-data-table :data="executionList" style="width: 100%" :empty-text="emptyText">
        <n-data-table-column prop="execution_id" label="执行ID" min-width="140" show-overflow-tooltip />
        <n-data-table-column prop="script_name" label="脚本名称" min-width="150" show-overflow-tooltip />
        <n-data-table-column prop="start_time" label="开始时间" width="160">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        <n-data-table-column prop="end_time" label="结束时间" width="160">
          <template #default="{ row }">{{ formatTime(row.end_time) }}</template>
        <n-data-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">{{ row.duration ? row.duration + 's' : '-' }}</template>
        <n-data-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <n-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</n-tag>
          </template>
        <n-data-table-column prop="executor" label="执行人" width="100" show-overflow-tooltip />
        <n-data-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <n-button type="primary" link size="small" @click="handleCheckpoint(row)" :loading="row.checkpointLoading">保存检查点</n-button>
            <n-button type="warning" link size="small" @click="handleRollback(row)" :loading="row.rollbackLoading">回滚</n-button>
          </template>
      <div v-if="!loading && executionList.length === 0" class="empty-state">
        <n-empty description="暂无执行记录">
          <n-button type="primary" @click="handleRefresh">刷新页面</n-button>
        </n-empty>
      </div>
      <div class="pagination" v-if="pagination.total > 0">
        <n-pagination
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
  </div>
</template>
<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { automation } from '@/api'
import { formatTime } from '@/utils/date'
const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const executionList = ref([])
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const emptyText = computed(() => {
  if (loading.value) return '加载中...'
  if (searchKeyword.value || filterStatus.value) return '没有找到匹配的执行记录'
  return '暂无执行记录'
})
onMounted(() => { loadData() })
const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filterStatus.value) params.status = filterStatus.value
    const res = await automation.getExecutions(params).catch(() => ({ items: [], total: 0 }))
    executionList.value = (res.items || res.list || []).map(item => ({
      ...item,
      checkpointLoading: false,
      rollbackLoading: false
    }))
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load executions error:', error)
    executionList.value = []
  } finally {
    loading.value = false
  }
}
const handleSearch = () => {
  pagination.page = 1
  loadData()
}
const handleRefresh = () => {
  loadData()
}
const getStatusType = (status) => {
  const map = {
    success: 'success',
    failed: 'danger',
    running: 'primary',
    rolled_back: 'warning'
  }
  return map[status] || 'info'
}
const getStatusText = (status) => {
  const map = {
    success: '成功',
    failed: '失败',
    running: '进行中',
    rolled_back: '已回滚'
  }
  return map[status] || status
}
const handleCheckpoint = async (row) => {
  row.checkpointLoading = true
  try {
    await automation.checkpoint(row.execution_id, { snapshot_type: 'script_output' })
    message.success('检查点保存成功')
  } catch (error) {
    console.error('Checkpoint error:', error)
    message.error('保存检查点失败')
  } finally {
    row.checkpointLoading = false
  }
}
const handleRollback = async (row) => {
  dialog.warning({
    title: '确认回滚',
    content: `确定要对执行 ${row.execution_id} 进行回滚吗？这将恢复系统到执行前的状态。`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      row.rollbackLoading = true
      try {
        await automation.rollback(row.execution_id, {})
        message.success('回滚操作已提交')
        loadData()
      } catch (error) {
        console.error('Rollback error:', error)
        message.error('回滚操作失败')
      } finally {
        row.rollbackLoading = false
      }
    },
    onNegativeClick: () => {}
  })
}
</script>
<style lang="scss" scoped>
.page-container {
  padding: 24px;
}
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
.empty-state {
  padding: 60px 0;
  text-align: center;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
:deep(.el-table .el-table__header th) {
  background: #f7f8fa;
}
</style>
