<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">备份记录</h1>
        <p class="page-subtitle">系统数据备份管理</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="handleCreate">
          <n-icon><AddOutline /></n-icon> 创建备份
        </n-button>
      </div>
    </div>
    <div class="filter-bar">
      <n-input v-model="searchKeyword" placeholder="搜索备份名称" style="width: 200px" clearable @change="handleSearch" />
      <n-select v-model="filterType" placeholder="备份类型" style="width: 140px" clearable @change="handleSearch">
        <n-option label="全量备份" value="full" />
        <n-option label="增量备份" value="incremental" />
      </n-select>
    </div>
    <div class="table-container">
      <n-data-table :data="backupList" style="width: 100%">
        <n-data-table-column prop="name" label="备份名称" min-width="180" />
        <n-data-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <n-tag size="small">{{ row.type === 'full' ? '全量备份' : '增量备份' }}</n-tag>
          </template>
        <n-data-table-column prop="size" label="大小" width="120" />
        <n-data-table-column prop="creator" label="创建人" width="120" />
        <n-data-table-column prop="created_at" label="备份时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        <n-data-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <n-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">
              {{ row.status === 'completed' ? '已完成' : row.status === 'failed' ? '失败' : '进行中' }}
            </n-tag>
          </template>
        <n-data-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <n-button type="primary" link size="small" @click="handleRestore(row)" :disabled="row.status !== 'completed'">恢复</n-button>
            <n-button type="primary" link size="small" @click="handleDownload(row)">下载</n-button>
            <n-button type="danger" link size="small" @click="handleDelete(row)">删除</n-button>
          </template>
      <div class="pagination">
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
import { ref, reactive, onMounted } from 'vue'
import { backup } from '@/api'
import { formatTime } from '@/utils/date'
const loading = ref(false)
const searchKeyword = ref('')
const filterType = ref('')
const backupList = ref([])
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
onMounted(() => { loadData() })
const loadData = async () => {
  loading.value = true
  try {
    const res = await backup.getList({ page: pagination.page, page_size: pagination.pageSize, keyword: searchKeyword.value, type: filterType.value }).catch(() => ({ items: [], total: 0 }))
    backupList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load backup error:', error) }
  finally { loading.value = false }
}
const handleSearch = () => { pagination.page = 1; loadData() }
const handleCreate = async () => {
  try {
    await backup.create({ type: 'full', name: `备份_${new Date().toLocaleString()}` })
    message.success('备份任务已创建')
    loadData()
  } catch (error) { console.error('Create backup error:', error) }
}
const handleRestore = async (row) => {
  dialog.warning({ title: '警告', content: `确定要恢复备份 "${row.name}" 吗? 这将覆盖当前数据。`, positiveText: '确定', negativeText: '取消', onPositiveClick: () => { }, onNegativeClick: () => { } })
    .then(async () => {
      try {
        await backup.restore(row.id)
        message.success('恢复任务已启动')
      } catch (error) { console.error('Restore error:', error) }
    }).catch(() => {})
}
const handleDownload = (row) => { message.info(`下载备份: ${row.name}`) }
const handleDelete = (row) => {
  dialog.warning({ title: '提示', content: `确定删除备份 "${row.name}" 吗?`, positiveText: '确定', negativeText: '取消', onPositiveClick: () => { }, onNegativeClick: () => { } })
    .then(async () => {
      try { await backup.delete(row.id); message.success('删除成功'); loadData() }
      catch (error) { console.error('Delete error:', error) }
    }).catch(() => {})
}
</script>
<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
