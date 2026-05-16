<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">备份记录</h1>
        <p class="page-subtitle">管理和恢复系统备份</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon> 创建备份
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索备份名称" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterType" placeholder="备份类型" style="width: 140px" clearable @change="handleSearch">
        <el-option label="全量备份" value="full" />
        <el-option label="增量备份" value="incremental" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="backupList" v-loading="loading" style="width: 100%" stripe>
        <el-table-column prop="name" label="备份名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type === 'full' ? '全量' : '增量' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="120">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="creator" label="创建人" width="120" />
        <el-table-column prop="created_at" label="备份时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleRestore(row)">恢复</el-button>
            <el-button type="success" link size="small" @click="handleDownload(row)">下载</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
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

    <!-- 创建备份对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建备份" width="500px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="备份名称">
          <el-input v-model="createForm.name" placeholder="请输入备份名称" />
        </el-form-item>
        <el-form-item label="备份类型">
          <el-select v-model="createForm.type" placeholder="请选择备份类型" style="width: 100%">
            <el-option label="全量备份" value="full" />
            <el-option label="增量备份" value="incremental" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate" :loading="creating">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { backup } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const creating = ref(false)
const searchKeyword = ref('')
const filterType = ref('')
const backupList = ref([])
const createDialogVisible = ref(false)

const createForm = reactive({ name: '', type: 'full' })

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
    if (filterType.value) params.type = filterType.value

    const res = await backup.getList(params).catch(() => ({ items: [], total: 0 }))
    backupList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load backup error:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => { pagination.page = 1; loadData() }

const handleCreate = () => {
  createForm.name = ''
  createForm.type = 'full'
  createDialogVisible.value = true
}

const submitCreate = async () => {
  if (!createForm.name.trim()) {
    ElMessage.warning('请输入备份名称')
    return
  }
  creating.value = true
  try {
    // Sanitize name: replace : and space with _
    const sanitizedName = createForm.name.trim().replace(/[:\s]+/g, '_')
    await backup.create({ type: createForm.type, name: sanitizedName })
    ElMessage.success('创建备份成功')
    createDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('Create backup error:', error)
    ElMessage.error('创建备份失败')
  } finally {
    creating.value = false
  }
}

const handleRestore = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要恢复备份「${row.name}」吗？`, '确认恢复', {
      type: 'warning'
    })
    await backup.restore(row.id)
    ElMessage.success('恢复备份成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Restore backup error:', error)
      ElMessage.error('恢复备份失败')
    }
  }
}

const handleDownload = (row) => {
  const filePath = row.file_path
  if (filePath) {
    window.open(filePath, '_blank')
  } else {
    // Try download URL
    const downloadUrl = `/api/v1/admin/backup/download/${row.id}`
    window.open(downloadUrl, '_blank')
    // If download URL doesn't exist, show tip after a short delay
    setTimeout(() => {
      if (!row.file_path) {
        ElMessage.info('下载功能暂不可用，请联系管理员')
      }
    }, 1000)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除备份「${row.name}」吗？此操作不可恢复。`, '确认删除', {
      type: 'warning'
    })
    await backup.delete(row.id)
    ElMessage.success('删除备份成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Delete backup error:', error)
      ElMessage.error('删除备份失败')
    }
  }
}

const getStatusType = (s) => ({ completed: 'success', failed: 'danger', running: 'warning' }[s] || 'info')
const getStatusText = (s) => ({ completed: '已完成', failed: '失败', running: '进行中' }[s] || s)

const formatSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}
</script>

<style lang="scss" scoped>
.page-container { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-subtitle { margin: 4px 0 0; color: #909399; font-size: 13px; }
.page-actions { display: flex; gap: 8px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.table-container { background: #fff; border-radius: 8px; padding: 16px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
