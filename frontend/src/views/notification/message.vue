<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">恢复管理</h1>
        <p class="page-subtitle">数据恢复历史记录</p>
      </div>
    </div>

    <div class="table-container">
      <el-table :data="restoreList" v-loading="loading" style="width: 100%">
        <el-table-column prop="backup_name" label="备份名称" min-width="180" />
        <el-table-column prop="type" label="备份类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type === 'full' ? '全量' : '增量' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="restored_at" label="恢复时间" width="180">
          <template #default="{ row }">{{ formatTime(row.restored_at) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="120" />
        <el-table-column prop="remark" label="备注" min-width="200" />
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { backup } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const restoreList = ref([])
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await backup.getList({ page: pagination.page, page_size: pagination.pageSize }).catch(() => ({ items: [], total: 0 }))
    restoreList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load restore history error:', error) }
  finally { loading.value = false }
}
</script>

<style lang="scss" scoped>
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
