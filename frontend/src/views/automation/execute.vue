<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">回滚历史</h1>
        <p class="page-subtitle">查看历史回滚记录</p>
      </div>
      <div class="page-actions">
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索执行ID或脚本名称" style="width: 240px" clearable @change="handleSearch" />
    </div>

    <div class="table-container">
      <el-table :data="executionList" v-loading="loading" style="width: 100%" :empty-text="emptyText">
        <el-table-column prop="id" label="执行ID" min-width="120" show-overflow-tooltip />
        <el-table-column prop="script_name" label="脚本名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="executed_at" label="执行时间" width="160">
          <template #default="{ row }">{{ formatTime(row.executed_at) }}</template>
        </el-table-column>
        <el-table-column prop="rollback_at" label="回滚时间" width="160">
          <template #default="{ row }">{{ formatTime(row.rollback_at) }}</template>
        </el-table-column>
        <el-table-column prop="rollback_by" label="回滚人" width="100" show-overflow-tooltip />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleViewDetail(row)" :loading="row.detailLoading">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && executionList.length === 0" class="empty-state">
        <el-empty description="暂无回滚历史">
          <el-button type="primary" @click="handleRefresh">刷新页面</el-button>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { automation } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const searchKeyword = ref('')
const executionList = ref([])

const emptyText = computed(() => {
  if (loading.value) return '加载中...'
  if (searchKeyword.value) return '没有找到匹配的回滚记录'
  return '暂无回滚历史'
})

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (searchKeyword.value) params.keyword = searchKeyword.value

    const res = await automation.getRollbackHistory().catch(() => [])
    let data = Array.isArray(res) ? res : []
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase()
      data = data.filter(item =>
        (item.id && item.id.toString().toLowerCase().includes(kw)) ||
        (item.script_name && item.script_name.toLowerCase().includes(kw))
      )
    }
    executionList.value = data.map(item => ({
      ...item,
      detailLoading: false
    }))
  } catch (error) {
    console.error('Load rollback history error:', error)
    executionList.value = []
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
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

const handleViewDetail = async (row) => {
  ElMessage.info(`查看回滚记录 ${row.id} 详情`)
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

:deep(.el-table .el-table__header th) {
  background: #f7f8fa;
}
</style>
