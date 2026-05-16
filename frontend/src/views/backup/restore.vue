<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">恢复历史</h1>
        <p class="page-subtitle">数据恢复操作记录</p>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索备份名称" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterStatus" placeholder="恢复状态" style="width: 140px" clearable @change="handleSearch">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
        <el-option label="进行中" value="running" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="restoreList" v-loading="loading" style="width: 100%">
        <el-table-column prop="backup_name" label="备份名称" min-width="180" />
        <el-table-column prop="type" label="备份类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.backup_type === 'full' ? '全量备份' : '增量备份' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="恢复状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="120" />
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">{{ formatTime(row.completed_at) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleViewDetail(row)">详情</el-button>
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

    <el-dialog v-model="detailDialogVisible" title="恢复详情" width="600px">
      <el-descriptions v-if="currentRestore" :column="2" border>
        <el-descriptions-item label="备份名称">{{ currentRestore.backup_name }}</el-descriptions-item>
        <el-descriptions-item label="备份类型">{{ currentRestore.backup_type === 'full' ? '全量备份' : '增量备份' }}</el-descriptions-item>
        <el-descriptions-item label="恢复状态">
          <el-tag :type="getStatusType(currentRestore.status)" size="small">{{ getStatusText(currentRestore.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="操作人">{{ currentRestore.operator }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatTime(currentRestore.started_at) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatTime(currentRestore.completed_at) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="恢复说明" :span="2">{{ currentRestore.description || '-' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer><el-button @click="detailDialogVisible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { request } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const restoreList = ref([])
const detailDialogVisible = ref(false)
const currentRestore = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

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
    const res = await request.get('/admin/restores', { params }).catch(() => ({ items: [], total: 0 }))
    restoreList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load restore history error:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => { pagination.page = 1; loadData() }

const handleViewDetail = (row) => {
  currentRestore.value = row
  detailDialogVisible.value = true
}

const getStatusType = (s) => ({ success: 'success', failed: 'danger', running: 'warning' }[s] || 'info')
const getStatusText = (s) => ({ success: '成功', failed: '失败', running: '进行中' }[s] || s)
</script>

<style lang="scss" scoped>
.page-container { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { font-size: 20px; font-weight: 600; margin: 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 4px 0 0; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.table-container { background: #fff; border-radius: 8px; padding: 16px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
