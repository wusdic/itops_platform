<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">任务调度</h1>
        <p class="page-subtitle">自动化任务编排与调度管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新建任务
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-item">
          <span class="stat-label">总任务数</span>
          <span class="stat-value">{{ statistics.total || 0 }}</span>
        </div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-item">
          <span class="stat-label">待执行</span>
          <span class="stat-value stat-pending">{{ statistics.pending || 0 }}</span>
        </div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-item">
          <span class="stat-label">执行中</span>
          <span class="stat-value stat-running">{{ statistics.running || 0 }}</span>
        </div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-item">
          <span class="stat-label">已完成</span>
          <span class="stat-value stat-completed">{{ statistics.completed || 0 }}</span>
        </div>
      </el-card>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filterStatus" placeholder="任务状态" style="width: 130px" clearable @change="handleSearch">
        <el-option label="待执行" value="pending" />
        <el-option label="执行中" value="running" />
        <el-option label="已完成" value="completed" />
        <el-option label="已失败" value="failed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-select v-model="filterType" placeholder="巡检类型" style="width: 130px" clearable @change="handleSearch">
        <el-option label="常规巡检" value="routine" />
        <el-option label="维护巡检" value="maintenance" />
        <el-option label="应急巡检" value="emergency" />
      </el-select>
      <el-input v-model="searchKeyword" placeholder="搜索任务名称" style="width: 200px" clearable @change="handleSearch" />
    </div>

    <!-- 任务列表 -->
    <div class="table-container">
      <el-table :data="taskList" v-loading="loading" style="width: 100%" stripe>
        <el-table-column prop="task_no" label="任务编号" width="180" />
        <el-table-column prop="name" label="任务名称" min-width="180">
          <template #default="{ row }">
            <div class="task-name-cell">
              <span class="task-name">{{ row.name }}</span>
              <span class="task-desc">{{ row.description }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="inspection_type" label="巡检类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="getTypeTagType(row.inspection_type)">
              {{ getTypeText(row.inspection_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="schedule_type" label="调度方式" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getScheduleTagType(row.schedule_type)">
              {{ getScheduleText(row.schedule_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusTagType(row.status)" effect="light">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.progress || 0" :stroke-width="8" />
          </template>
        </el-table-column>
        <el-table-column prop="health_score" label="健康度" width="100">
          <template #default="{ row }">
            <span v-if="row.health_score != null" :class="getHealthClass(row.health_score)">
              {{ row.health_score.toFixed(1) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="primary" link size="small" @click="handleView(row)">查看</el-button>
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

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" :close-on-click-modal="false">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入任务名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="任务描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入任务描述" />
        </el-form-item>
        <el-form-item label="巡检类型" prop="inspection_type">
          <el-select v-model="form.inspection_type" placeholder="请选择巡检类型" style="width: 100%">
            <el-option label="常规巡检" value="routine" />
            <el-option label="维护巡检" value="maintenance" />
            <el-option label="应急巡检" value="emergency" />
          </el-select>
        </el-form-item>
        <el-form-item label="巡检对象" prop="target_type">
          <el-select v-model="form.target_type" placeholder="请选择巡检对象类型" style="width: 100%">
            <el-option label="设备" value="device" />
            <el-option label="分组" value="group" />
            <el-option label="全部" value="all" />
          </el-select>
        </el-form-item>
        <el-form-item label="调度方式" prop="schedule_type">
          <el-select v-model="form.schedule_type" placeholder="请选择调度方式" style="width: 100%">
            <el-option label="手动执行" value="manual" />
            <el-option label="定时执行" value="scheduled" />
            <el-option label="自动执行" value="auto" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="viewDialogVisible" title="任务详情" width="650px">
      <div v-if="currentTask" class="task-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务编号">{{ currentTask.task_no }}</el-descriptions-item>
          <el-descriptions-item label="任务名称">{{ currentTask.name }}</el-descriptions-item>
          <el-descriptions-item label="巡检类型">{{ getTypeText(currentTask.inspection_type) }}</el-descriptions-item>
          <el-descriptions-item label="调度方式">{{ getScheduleText(currentTask.schedule_type) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="getStatusTagType(currentTask.status)">{{ getStatusText(currentTask.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="进度">{{ currentTask.progress || 0 }}%</el-descriptions-item>
          <el-descriptions-item label="巡检设备数">{{ currentTask.total_devices || 0 }}</el-descriptions-item>
          <el-descriptions-item label="健康设备">{{ currentTask.healthy_devices || 0 }}</el-descriptions-item>
          <el-descriptions-item label="警告设备">{{ currentTask.warning_devices || 0 }}</el-descriptions-item>
          <el-descriptions-item label="危险设备">{{ currentTask.critical_devices || 0 }}</el-descriptions-item>
          <el-descriptions-item label="离线设备">{{ currentTask.offline_devices || 0 }}</el-descriptions-item>
          <el-descriptions-item label="健康度评分">
            <span v-if="currentTask.health_score != null" :class="getHealthClass(currentTask.health_score)">
              {{ currentTask.health_score.toFixed(1) }}
            </span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(currentTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(currentTask.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatTime(currentTask.completed_at) }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ currentTask.description || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { scheduler } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const submitLoading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterType = ref('')
const taskList = ref([])
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const dialogTitle = ref('新建任务')
const formRef = ref(null)
const currentTask = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const statistics = reactive({ total: 0, pending: 0, running: 0, completed: 0 })
const form = reactive({
  id: null,
  name: '',
  description: '',
  inspection_type: 'routine',
  target_type: 'device',
  schedule_type: 'manual'
})

const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  inspection_type: [{ required: true, message: '请选择巡检类型', trigger: 'change' }],
  target_type: [{ required: true, message: '请选择巡检对象类型', trigger: 'change' }],
  schedule_type: [{ required: true, message: '请选择调度方式', trigger: 'change' }]
}

onMounted(() => { loadData(); loadStatistics() })

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterType.value) params.inspection_type = filterType.value

    const res = await scheduler.getList(params).catch(() => ({ data: [], total: 0 }))
    taskList.value = res.data || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('Load tasks error:', error)
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  try {
    const res = await scheduler.getStatistics().catch(() => ({}))
    if (res.data) {
      statistics.total = res.data.total_tasks || 0
      statistics.pending = (res.data.total_tasks || 0) - (res.data.completed_tasks || 0) - (res.data.running_tasks || 0)
      statistics.running = res.data.running_tasks || 0
      statistics.completed = res.data.completed_tasks || 0
    }
  } catch (error) {
    console.error('Load statistics error:', error)
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

const handleAdd = () => {
  dialogTitle.value = '新建任务'
  Object.assign(form, { id: null, name: '', description: '', inspection_type: 'routine', target_type: 'device', schedule_type: 'manual' })
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  dialogTitle.value = '编辑任务'
  try {
    const res = await scheduler.getById(row.id).catch(() => ({ data: null }))
    if (res.data) {
      const d = res.data
      Object.assign(form, {
        id: d.id,
        name: d.name,
        description: d.description,
        inspection_type: d.inspection_type,
        target_type: d.target_type,
        schedule_type: d.schedule_type
      })
      dialogVisible.value = true
    }
  } catch (error) {
    console.error('Load task detail error:', error)
  }
}

const handleView = async (row) => {
  try {
    const res = await scheduler.getById(row.id).catch(() => ({ data: null }))
    if (res.data) {
      currentTask.value = res.data
      viewDialogVisible.value = true
    }
  } catch (error) {
    console.error('Load task detail error:', error)
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除任务 "${row.name}" 吗？`, '提示', { type: 'warning' })
    .then(async () => {
      try {
        await scheduler.delete(row.id)
        ElMessage.success('删除成功')
        loadData()
        loadStatistics()
      } catch (error) {
        console.error('Delete error:', error)
      }
    })
    .catch(() => {})
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (form.id) {
      await scheduler.update(form.id, form)
      ElMessage.success('更新成功')
    } else {
      await scheduler.create(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
    loadStatistics()
  } catch (error) {
    console.error('Submit error:', error)
  } finally {
    submitLoading.value = false
  }
}

const getTypeText = (t) => ({ routine: '常规巡检', maintenance: '维护巡检', emergency: '应急巡检' }[t] || t)
const getTypeTagType = (t) => ({ routine: '', maintenance: 'warning', emergency: 'danger' }[t] || 'info')
const getScheduleText = (t) => ({ manual: '手动', scheduled: '定时', auto: '自动' }[t] || t)
const getScheduleTagType = (t) => ({ manual: 'info', scheduled: 'success', auto: 'warning' }[t] || 'info')
const getStatusText = (s) => ({ pending: '待执行', running: '执行中', completed: '已完成', failed: '已失败', cancelled: '已取消' }[s] || s)
const getStatusTagType = (s) => ({ pending: 'info', running: 'primary', completed: 'success', failed: 'danger', cancelled: 'warning' }[s] || 'info')
const getHealthClass = (score) => {
  if (score >= 80) return 'health-good'
  if (score >= 60) return 'health-warning'
  return 'health-danger'
}
</script>

<style lang="scss" scoped>
.page-container { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { font-size: 20px; font-weight: 600; margin: 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 4px 0 0; }

.stats-row { display: flex; gap: 16px; margin-bottom: 16px; }
.stat-card { flex: 1; }
.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-label { font-size: 14px; color: #909399; margin-bottom: 8px; }
.stat-value { font-size: 24px; font-weight: 600; }
.stat-pending { color: #909399; }
.stat-running { color: #409EFF; }
.stat-completed { color: #67C23A; }

.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.table-container { background: #fff; border-radius: 8px; padding: 16px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }

.task-name-cell { display: flex; flex-direction: column; }
.task-name { font-weight: 500; }
.task-desc { font-size: 12px; color: #909399; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.text-muted { color: #c0c4cc; }
.health-good { color: #67C23A; font-weight: 600; }
.health-warning { color: #E6A23C; font-weight: 600; }
.health-danger { color: #F56C6C; font-weight: 600; }

.task-detail { padding: 10px 0; }

:deep(.el-table .el-table__header th) { background: #f7f8fa; }
:deep(.el-progress) { width: 90%; }
</style>
