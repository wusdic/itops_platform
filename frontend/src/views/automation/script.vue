<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">自动化规则管理</h1>
        <p class="page-subtitle">告警触发规则配置与管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新建规则
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索规则名称" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterLevel" placeholder="告警级别" style="width: 140px" clearable @change="handleSearch">
        <el-option label="紧急" value="critical" />
        <el-option label="重要" value="major" />
        <el-option label="一般" value="minor" />
        <el-option label="提示" value="info" />
      </el-select>
      <el-select v-model="filterEnabled" placeholder="启用状态" style="width: 120px" clearable @change="handleSearch">
        <el-option label="已启用" value="true" />
        <el-option label="已禁用" value="false" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="ruleList" v-loading="loading" style="width: 100%" stripe>
        <el-table-column prop="name" label="规则名称" min-width="180" />
        <el-table-column label="触发条件" min-width="200">
          <template #default="{ row }">
            <span class="condition-text">{{ formatCondition(row.condition_config) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="告警级别" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getLevelTagType(row.alert_level)">
              {{ getLevelText(row.alert_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              @change="handleToggleEnabled(row)"
              :loading="row._loading"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="primary" link size="small" @click="handleTest(row)">测试</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && ruleList.length === 0" class="empty-tip">
        <el-empty description="暂无自动化规则" />
      </div>

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

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px" @close="handleDialogClose">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入规则描述" />
        </el-form-item>
        <el-form-item label="告警级别" prop="alert_level">
          <el-select v-model="form.alert_level" placeholder="请选择告警级别" style="width: 100%">
            <el-option label="紧急 (Critical)" value="critical" />
            <el-option label="重要 (Major)" value="major" />
            <el-option label="一般 (Minor)" value="minor" />
            <el-option label="提示 (Info)" value="info" />
          </el-select>
        </el-form-item>

        <!-- 触发条件配置 -->
        <el-divider>触发条件</el-divider>
        <el-form-item label="条件类型" prop="condition_config.condition_type">
          <el-select v-model="form.condition_config.condition_type" placeholder="请选择条件类型" style="width: 100%">
            <el-option label="阈值 (Threshold)" value="threshold" />
            <el-option label="变化率 (Change)" value="change" />
            <el-option label="速率 (Rate)" value="rate" />
            <el-option label="常量 (Constant)" value="constant" />
            <el-option label="表达式 (Expression)" value="expression" />
          </el-select>
        </el-form-item>
        <el-form-item label="指标名称" prop="condition_config.metric_name">
          <el-input v-model="form.condition_config.metric_name" placeholder="如: cpu_usage, memory_percent" />
        </el-form-item>
        <el-form-item label="运算符" prop="condition_config.operator" v-if="showOperator">
          <el-select v-model="form.condition_config.operator" placeholder="请选择运算符" style="width: 100%">
            <el-option label="大于 (>)" value=">" />
            <el-option label="小于 (<)" value="<" />
            <el-option label="大于等于 (>=)" value=">=" />
            <el-option label="小于等于 (<=)" value="<=" />
            <el-option label="等于 (==)" value="==" />
            <el-option label="不等于 (!=)" value="!=" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值" prop="condition_config.threshold_value" v-if="showThreshold">
          <el-input-number v-model="form.condition_config.threshold_value" :precision="2" style="width: 100%" placeholder="请输入阈值" />
        </el-form-item>
        <el-form-item label="持续时间" prop="condition_config.duration_seconds" v-if="showDuration">
          <el-input-number v-model="form.condition_config.duration_seconds" :min="0" style="width: 100%" placeholder="持续多少秒触发(0表示立即)" />
          <span class="form-tip">单位：秒，0表示立即触发</span>
        </el-form-item>

        <el-divider>执行动作</el-divider>
        <el-form-item label="设备选择">
          <el-select v-model="form.device_ids" multiple placeholder="请选择目标设备(可选)" style="width: 100%" filterable clearable>
            <el-option v-for="device in devices" :key="device.id" :label="`${device.name} (${device.ip})`" :value="device.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行动作">
          <el-input v-model="form.action" type="textarea" :rows="3" placeholder="请输入执行动作，如：发送告警通知、自动修复等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- Test Result Dialog -->
    <el-dialog v-model="testDialogVisible" title="规则测试" width="600px">
      <div v-if="testLoading" class="test-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在测试规则...</span>
      </div>
      <div v-else-if="testResult" class="test-result">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="规则名称">{{ testResult.name }}</el-descriptions-item>
          <el-descriptions-item label="触发状态">
            <el-tag :type="testResult.triggered ? 'danger' : 'success'">
              {{ testResult.triggered ? '已触发' : '未触发' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前指标值">{{ testResult.current_value ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="阈值">{{ testResult.threshold ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="评估结果">{{ testResult.message || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Loading } from '@element-plus/icons-vue'
import { automation } from '@/api/index.js'

const loading = ref(false)
const submitLoading = ref(false)
const testLoading = ref(false)
const searchKeyword = ref('')
const filterLevel = ref('')
const filterEnabled = ref('')
const ruleList = ref([])
const devices = ref([])
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const dialogTitle = ref('新建规则')
const formRef = ref(null)
const testResult = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const defaultConditionConfig = {
  condition_type: 'threshold',
  metric_name: '',
  operator: '>',
  threshold_value: null,
  duration_seconds: 0
}

const form = reactive({
  id: null,
  name: '',
  description: '',
  alert_level: 'major',
  enabled: true,
  condition_config: { ...defaultConditionConfig },
  device_ids: [],
  action: ''
})

const rules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  'condition_config.condition_type': [{ required: true, message: '请选择条件类型', trigger: 'change' }],
  'condition_config.metric_name': [{ required: true, message: '请输入指标名称', trigger: 'blur' }]
}

// Show/hide fields based on condition_type
const showOperator = computed(() => ['threshold', 'change', 'rate'].includes(form.condition_config.condition_type))
const showThreshold = computed(() => ['threshold', 'rate', 'constant'].includes(form.condition_config.condition_type))
const showDuration = computed(() => ['threshold', 'change', 'rate'].includes(form.condition_config.condition_type))

// Format condition for display
const formatCondition = (config) => {
  if (!config) return '-'
  const typeMap = { threshold: '阈值', change: '变化率', rate: '速率', constant: '常量', expression: '表达式' }
  const type = typeMap[config.condition_type] || config.condition_type
  if (config.condition_type === 'constant') {
    return `${config.metric_name} = ${config.threshold_value}`
  }
  if (config.condition_type === 'expression') {
    return `${config.metric_name} (表达式)`
  }
  return `${config.metric_name} ${config.operator} ${config.threshold_value}${config.duration_seconds ? ` (持续${config.duration_seconds}s)` : ''}`
}

// Level tag type
const getLevelTagType = (level) => ({ critical: 'danger', major: 'warning', minor: 'info', info: '' }[level] || 'info')
const getLevelText = (level) => ({ critical: '紧急', major: '重要', minor: '一般', info: '提示' }[level] || level)

// Format time
const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  return d.toLocaleString('zh-CN')
}

// Load rules from API
const loadData = async () => {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filterLevel.value) params.alert_level = filterLevel.value
    if (filterEnabled.value) params.enabled = filterEnabled.value

    const res = await automation.getTriggerRules(params)
    const data = res.data || res
    ruleList.value = data.items || data.list || []
    pagination.total = data.total || ruleList.value.length
  } catch (err) {
    console.error('Failed to load rules:', err)
    ElMessage.error('加载规则列表失败')
    ruleList.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

// Load devices from API
const loadDevices = async () => {
  try {
    const res = await fetch('/api/v1/assets/device?page_size=100')
    if (res.ok) {
      const data = await res.json()
      devices.value = (data.items || data.devices || []).map(d => ({ id: d.id, name: d.hostname || d.name, ip: d.ip_address }))
    } else {
      devices.value = []
    }
  } catch {
    devices.value = []
  }
}

const handleSearch = () => { pagination.page = 1; loadData() }

const handleDialogClose = () => {
  formRef.value?.resetFields()
}

const handleAdd = () => {
  dialogTitle.value = '新建规则'
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    alert_level: 'major',
    enabled: true,
    condition_config: { ...defaultConditionConfig },
    device_ids: [],
    action: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑规则'
  const conditionConfig = row.condition_config || {}
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description || '',
    alert_level: row.alert_level || 'major',
    enabled: row.enabled !== false,
    condition_config: {
      condition_type: conditionConfig.condition_type || 'threshold',
      metric_name: conditionConfig.metric_name || '',
      operator: conditionConfig.operator || '>',
      threshold_value: conditionConfig.threshold_value ?? null,
      duration_seconds: conditionConfig.duration_seconds || 0
    },
    device_ids: row.device_ids || [],
    action: row.action || ''
  })
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除规则 "${row.name}" 吗?`, '提示', { type: 'warning' })
    .then(async () => {
      try {
        await automation.deleteTriggerRule(row.id)
        ElMessage.success('删除成功')
        loadData()
      } catch (err) {
        console.error('Failed to delete rule:', err)
        ElMessage.error('删除失败')
      }
    })
    .catch(() => {})
}

const handleToggleEnabled = async (row) => {
  row._loading = true
  try {
    await automation.updateTriggerRule(row.id, { enabled: row.enabled })
    ElMessage.success(row.enabled ? '规则已启用' : '规则已禁用')
  } catch (err) {
    console.error('Failed to toggle enabled:', err)
    row.enabled = !row.enabled
    ElMessage.error('更新状态失败')
  } finally {
    row._loading = false
  }
}

const handleTest = async (row) => {
  testDialogVisible.value = true
  testResult.value = null
  testLoading.value = true
  try {
    const res = await automation.testTriggerRule(row.id)
    testResult.value = res.data || res
  } catch (err) {
    console.error('Failed to test rule:', err)
    testResult.value = { name: row.name, triggered: false, message: '测试请求失败' }
  } finally {
    testLoading.value = false
  }
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    const payload = {
      name: form.name,
      description: form.description,
      alert_level: form.alert_level,
      enabled: form.enabled,
      condition_config: {
        condition_type: form.condition_config.condition_type,
        metric_name: form.condition_config.metric_name,
        operator: form.condition_config.operator,
        threshold_value: form.condition_config.threshold_value,
        duration_seconds: form.condition_config.duration_seconds
      },
      device_ids: form.device_ids,
      action: form.action
    }

    if (form.id) {
      await automation.updateTriggerRule(form.id, payload)
      ElMessage.success('更新成功')
    } else {
      await automation.createTriggerRule(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (err) {
    console.error('Failed to submit form:', err)
    ElMessage.error(form.id ? '更新失败' : '创建失败')
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  loadData()
  loadDevices()
})
</script>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.empty-tip { padding: 40px 0; }
.condition-text { color: #606266; font-size: 13px; }
.form-tip { color: #909399; font-size: 12px; margin-left: 8px; }
.test-loading { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 40px 0; color: #909399; }
.test-result { padding: 8px 0; }

:deep(.el-table .el-table__header th) { background: #f7f8fa; }
:deep(.el-divider) { margin: 16px 0; }
</style>
