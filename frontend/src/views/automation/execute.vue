<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">任务调度</h1>
        <p class="page-subtitle">定时任务配置与管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新建任务
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索任务名称" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterStatus" placeholder="任务状态" style="width: 140px" clearable @change="handleSearch">
        <el-option label="运行中" value="running" />
        <el-option label="已停止" value="stopped" />
        <el-option label="已禁用" value="disabled" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="taskList" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="任务名称" min-width="180" />
        <el-table-column prop="type" label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cron" label="执行周期" width="150" />
        <el-table-column prop="last_run" label="上次执行" width="160">
          <template #default="{ row }">{{ formatTime(row.last_run) }}</template>
        </el-table-column>
        <el-table-column prop="next_run" label="下次执行" width="160">
          <template #default="{ row }">{{ formatTime(row.next_run) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : row.status === 'stopped' ? 'warning' : 'info'" size="small">
              {{ row.status === 'running' ? '运行中' : row.status === 'stopped' ? '已停止' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggle(row)" :loading="row.loading" />
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="任务类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择任务类型" style="width: 100%">
            <el-option label="脚本执行" value="script" />
            <el-option label="API调用" value="api" />
            <el-option label="数据备份" value="backup" />
          </el-select>
        </el-form-item>
        <el-form-item label="CRON表达式" prop="cron">
          <el-input v-model="form.cron" placeholder="如: 0 0 * * *" />
        </el-form-item>
        <el-form-item label="关联脚本" v-if="form.type === 'script'">
          <el-select v-model="form.script_id" placeholder="请选择脚本" style="width: 100%">
            <el-option label="系统备份脚本" value="1" />
            <el-option label="日志清理脚本" value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { automation } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const taskList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新建任务')
const formRef = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', type: '', cron: '', script_id: '', description: '' })
const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  cron: [{ required: true, message: '请输入CRON表达式', trigger: 'blur' }]
}

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await automation.getTasks({ page: pagination.page, page_size: pagination.pageSize, keyword: searchKeyword.value }).catch(() => ({ items: [], total: 0 }))
    taskList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load tasks error:', error) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; loadData() }
const getTypeText = (t) => ({ script: '脚本执行', api: 'API调用', backup: '数据备份' }[t] || t)

const handleAdd = () => { dialogTitle.value = '新建任务'; Object.assign(form, { id: null, name: '', type: '', cron: '', script_id: '', description: '' }); dialogVisible.value = true }
const handleEdit = (row) => { dialogTitle.value = '编辑任务'; Object.assign(form, { id: row.id, name: row.name, type: row.type, cron: row.cron, script_id: row.script_id, description: row.description }); dialogVisible.value = true }
const handleDelete = (row) => { ElMessageBox.confirm(`确定删除任务 "${row.name}" 吗?`, '提示', { type: 'warning' }).then(async () => { try { await automation.deleteTask(row.id); ElMessage.success('删除成功'); loadData() } catch (error) { console.error('Delete error:', error) } }).catch(() => {}) }

const handleToggle = async (row) => {
  row.loading = true
  try {
    await automation.toggleTask(row.id, row.enabled)
    ElMessage.success(row.enabled ? '任务已启用' : '任务已禁用')
  } catch (error) {
    row.enabled = !row.enabled
    console.error('Toggle error:', error)
  }
  row.loading = false
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await automation.updateTask(form.id, form); ElMessage.success('更新成功') }
    else { await automation.createTask(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
:deep(.el-switch) { margin-right: 12px; }
</style>
