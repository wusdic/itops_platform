<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">工单列表</h1>
        <p class="page-subtitle">查看和管理所有工单</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="$router.push('/workorder/create')">
          <el-icon><Plus /></el-icon> 创建工单
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索工单标题" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterStatus" placeholder="工单状态" style="width: 120px" clearable @change="handleSearch">
        <el-option label="待处理" value="pending" />
        <el-option label="处理中" value="processing" />
        <el-option label="已完成" value="completed" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-select v-model="filterPriority" placeholder="优先级" style="width: 120px" clearable @change="handleSearch">
        <el-option label="P1-紧急" value="P1" />
        <el-option label="P2-高" value="P2" />
        <el-option label="P3-中" value="P3" />
        <el-option label="P4-低" value="P4" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="workorderList" v-loading="loading" style="width: 100%" stripe>
        <el-table-column prop="order_no" label="工单号" width="160" />
        <el-table-column prop="title" label="工单标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="getPriorityTagType(row.priority)" size="small">{{ getPriorityText(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator" label="创建人" width="100" />
        <el-table-column prop="assignee" label="处理人" width="100">
          <template #default="{ row }">{{ row.assignee || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">详情</el-button>
            <el-button type="warning" link size="small" @click="handleAssign(row)" v-if="row.status === 'pending'">分配</el-button>
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

    <!-- 分配工单对话框 -->
    <el-dialog v-model="assignDialogVisible" title="分配工单" width="500px">
      <el-form :model="assignForm" label-width="80px">
        <el-form-item label="处理人">
          <el-select v-model="assignForm.assignee" placeholder="请选择处理人" filterable style="width: 100%">
            <el-option v-for="u in userList" :key="u.username" :label="u.username" :value="u.username" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="assignForm.note" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAssign">确定</el-button>
      </template>
    </el-dialog>

    <!-- 工单详情对话框 -->
    <el-dialog v-model="detailVisible" title="工单详情" width="600px">
      <div v-if="currentOrder" class="order-detail">
        <div class="detail-row"><span class="label">工单号</span><span class="value">{{ currentOrder.order_no }}</span></div>
        <div class="detail-row"><span class="label">标题</span><span class="value">{{ currentOrder.title }}</span></div>
        <div class="detail-row"><span class="label">类型</span><span class="value">{{ currentOrder.order_type }}</span></div>
        <div class="detail-row"><span class="label">优先级</span><span class="value">{{ getPriorityText(currentOrder.priority) }}</span></div>
        <div class="detail-row"><span class="label">状态</span><span class="value">{{ getStatusText(currentOrder.status) }}</span></div>
        <div class="detail-row"><span class="label">创建人</span><span class="value">{{ currentOrder.creator }}</span></div>
        <div class="detail-row"><span class="label">处理人</span><span class="value">{{ currentOrder.assignee || '-' }}</span></div>
        <div class="detail-row"><span class="label">创建时间</span><span class="value">{{ formatTime(currentOrder.created_at) }}</span></div>
        <div class="detail-row" style="flex-direction: column; align-items: flex-start;">
          <span class="label">描述</span>
          <span class="value" style="margin-top: 8px; white-space: pre-wrap;">{{ currentOrder.description }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button v-if="currentOrder && currentOrder.status === 'pending'" type="warning" @click="handleAssign(currentOrder); detailVisible=false">分配处理人</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { workorder } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterPriority = ref('')
const workorderList = ref([])
const userList = ref([])
const assignDialogVisible = ref(false)
const detailVisible = ref(false)
const currentOrder = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const assignForm = reactive({ assignee: '', note: '' })

onMounted(() => {
  loadData()
  loadUsers()
})

const loadUsers = async () => {
  try {
    const res = await fetch('/api/v1/admin/users').then(r => r.json())
    userList.value = res.items || []
  } catch (e) { console.error(e) }
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterPriority.value) params.priority = filterPriority.value

    const res = await workorder.getList(params).catch(() => ({ items: [], total: 0 }))
    workorderList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load workorder error:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => { pagination.page = 1; loadData() }

const handleView = (row) => {
  currentOrder.value = row
  detailVisible.value = true
}

const handleAssign = (row) => {
  currentOrder.value = row
  Object.assign(assignForm, { assignee: row.assignee || '', note: '' })
  assignDialogVisible.value = true
}

const submitAssign = async () => {
  if (!assignForm.assignee) {
    ElMessage.warning('请选择处理人')
    return
  }
  try {
    await workorder.assign(currentOrder.value.id, { assignee: assignForm.assignee, note: assignForm.note })
    ElMessage.success('分配成功')
    assignDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('Assign error:', error)
    ElMessage.error('分配失败')
  }
}

const getPriorityTagType = (p) => ({ P1: 'danger', P2: 'warning', P3: 'info', P4: 'info' })[p] || 'info'
const getPriorityText = (p) => ({ P1: 'P1-紧急', P2: 'P2-高', P3: 'P3-中', P4: 'P4-低' })[p] || p
const getStatusTagType = (s) => ({ pending: 'warning', processing: 'primary', completed: 'success', closed: 'info' })[s] || 'info'
const getStatusText = (s) => ({ pending: '待处理', processing: '处理中', completed: '已完成', closed: '已关闭' })[s] || s
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
.order-detail {
  .detail-row { display: flex; padding: 8px 0; border-bottom: 1px solid #f2f3f5; &:last-child { border-bottom: none; } .label { width: 90px; color: #909399; flex-shrink: 0; } .value { flex: 1; color: #303133; } }
}
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
