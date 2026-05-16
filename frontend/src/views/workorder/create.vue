<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">工单列表</h1>
        <p class="page-subtitle">查看和管理所有工单</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="$router.push('/workorder/create')">
          <n-icon><AddOutline /></n-icon> 创建工单
        </n-button>
      </div>
    </div>
    <div class="filter-bar">
      <n-input v-model="searchKeyword" placeholder="搜索工单标题" style="width: 200px" clearable @change="handleSearch" />
      <n-select v-model="filterStatus" placeholder="工单状态" style="width: 120px" clearable @change="handleSearch">
        <n-option label="待处理" value="pending" />
        <n-option label="处理中" value="processing" />
        <n-option label="已完成" value="completed" />
        <n-option label="已关闭" value="closed" />
      </n-select>
      <n-select v-model="filterPriority" placeholder="优先级" style="width: 120px" clearable @change="handleSearch">
        <n-option label="紧急" value="urgent" />
        <n-option label="高" value="high" />
        <n-option label="中" value="medium" />
        <n-option label="低" value="low" />
      </n-select>
    </div>
    <div class="table-container">
      <n-data-table :data="workorderList" style="width: 100%">
        <n-data-table-column prop="id" label="工单号" width="100" />
        <n-data-table-column prop="title" label="工单标题" min-width="200" />
        <n-data-table-column prop="priority" label="优先级" width="100">
          <template #default="{ row }">
            <n-tag :type="getPriorityType(row.priority)" size="small">{{ getPriorityText(row.priority) }}</n-tag>
          </template>
        <n-data-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <n-tag :type="getWorkOrderStatusType(row.status)" size="small">{{ getWorkOrderStatusText(row.status) }}</n-tag>
          </template>
        <n-data-table-column prop="creator" label="创建人" width="120" />
        <n-data-table-column prop="handler" label="处理人" width="120" />
        <n-data-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        <n-data-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <n-button type="primary" link size="small" @click="handleView(row)">查看</n-button>
            <n-button type="primary" link size="small" @click="handleAssign(row)" v-if="row.status === 'pending'">分配</n-button>
            <n-button type="success" link size="small" @click="handleComplete(row)" v-if="row.status === 'processing'">完成</n-button>
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
    <n-modal v-model="assignDialogVisible" title="分配工单" width="500px">
      <n-form :model="assignForm" label-width="80px">
        <n-form-item label="处理人">
          <n-select v-model="assignForm.handler_id" placeholder="请选择处理人" style="width: 100%">
            <n-option label="张三" value="1" />
            <n-option label="李四" value="2" />
            <n-option label="王五" value="3" />
          </n-select>
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model="assignForm.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="assignDialogVisible = false">取消</n-button>
        <n-button type="primary" @click="submitAssign">确定</n-button>
      </template>
    </n-modal>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { workorder } from '@/api'
import { formatTime } from '@/utils/date'
import { getPriorityType, getPriorityText, getWorkOrderStatusType, getWorkOrderStatusText } from '@/utils/status'
const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterPriority = ref('')
const workorderList = ref([])
const assignDialogVisible = ref(false)
const currentOrder = ref(null)
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const assignForm = reactive({ handler_id: '', remark: '' })
onMounted(() => { loadData() })
const loadData = async () => {
  loading.value = true
  try {
    const res = await workorder.getList({
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchKeyword.value,
      status: filterStatus.value,
      priority: filterPriority.value
    }).catch(() => ({ items: [], total: 0 }))
    workorderList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load workorder error:', error)
  } finally {
    loading.value = false
  }
}
const handleSearch = () => { pagination.page = 1; loadData() }
const handleView = (row) => { message.info(`查看工单: ${row.title}`) }
const handleAssign = (row) => {
  currentOrder.value = row
  Object.assign(assignForm, { handler_id: '', remark: '' })
  assignDialogVisible.value = true
}
const submitAssign = async () => {
  try {
    await workorder.assign(currentOrder.value.id, assignForm)
    message.success('分配成功')
    assignDialogVisible.value = false
    loadData()
  } catch (error) { console.error('Assign error:', error) }
}
const handleComplete = async (row) => {
  try {
    await workorder.complete(row.id, {})
    message.success('工单已完成')
    loadData()
  } catch (error) { console.error('Complete error:', error) }
}
</script>
<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
