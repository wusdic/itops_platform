<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">执行记录</h1>
        <p class="page-subtitle">自动化任务执行历史</p>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索任务名称" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterStatus" placeholder="执行状态" style="width: 140px" clearable @change="handleSearch">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
        <el-option label="运行中" value="running" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="executionList" v-loading="loading" style="width: 100%">
        <el-table-column prop="task_name" label="任务名称" min-width="180" />
        <el-table-column prop="type" label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="executor" label="执行人" width="120" />
        <el-table-column prop="started_at" label="开始时间" width="160">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">{{ row.duration }}s</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleViewLog(row)">查看日志</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
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

    <el-dialog v-model="logDialogVisible" title="执行日志" width="800px">
      <el-input v-model="logContent" type="textarea" :rows="20" readonly placeholder="暂无日志" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { automation } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const executionList = ref([])
const logDialogVisible = ref(false)
const logContent = ref('')

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await automation.getExecutions({ page: pagination.page, page_size: pagination.pageSize, keyword: searchKeyword.value, status: filterStatus.value }).catch(() => ({ items: [], total: 0 }))
    executionList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load executions error:', error) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; loadData() }
const getTypeText = (t) => ({ script: '脚本执行', api: 'API调用', backup: '数据备份' }[t] || t)
const getStatusType = (s) => ({ success: 'success', failed: 'danger', running: 'warning' }[s] || 'info')
const getStatusText = (s) => ({ success: '成功', failed: '失败', running: '运行中' }[s] || s)

const handleViewLog = async (row) => {
  try {
    const res = await automation.getExecutionLog(row.id).catch(() => '')
    logContent.value = res || '暂无日志'
  } catch (error) {
    logContent.value = '获取日志失败'
  }
  logDialogVisible.value = true
}
</script>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
