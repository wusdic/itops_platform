<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">创建工单</h1>
        <p class="page-subtitle">提交新的运维工单</p>
      </div>
      <el-button @click="$router.push('/workorder/list')">
        <el-icon><Back /></el-icon> 返回列表
      </el-button>
    </div>

    <div class="form-container">
      <el-card>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
          <el-form-item label="工单标题" prop="title">
            <el-input v-model="form.title" placeholder="请输入工单标题" maxlength="100" show-word-limit />
          </el-form-item>

          <el-form-item label="工单类型" prop="order_type">
            <el-radio-group v-model="form.order_type">
              <el-radio value="fault">故障报修</el-radio>
              <el-radio value="change">变更申请</el-radio>
              <el-radio value="request">服务请求</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="优先级" prop="priority">
            <el-select v-model="form.priority" placeholder="请选择优先级" style="width: 200px">
              <el-option label="P1 - 紧急" value="P1" />
              <el-option label="P2 - 高" value="P2" />
              <el-option label="P3 - 中" value="P3" />
              <el-option label="P4 - 低" value="P4" />
            </el-select>
          </el-form-item>

          <el-form-item label="关联设备">
            <el-select v-model="form.device_id" placeholder="选择关联设备（可选）" filterable clearable style="width: 100%">
              <el-option v-for="d in deviceList" :key="d.id" :label="`${d.name} (${d.ip_address})`" :value="d.id" />
            </el-select>
          </el-form-item>

          <el-form-item label="处理人" prop="assignee">
            <el-select v-model="form.assignee" placeholder="选择处理人（可选）" filterable clearable style="width: 100%">
              <el-option v-for="u in userList" :key="u.username" :label="u.username" :value="u.username" />
            </el-select>
          </el-form-item>

          <el-form-item label="工单描述" prop="description">
            <el-input v-model="form.description" type="textarea" :rows="6" placeholder="请详细描述工单内容" maxlength="500" show-word-limit />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleSubmit" :loading="submitting">提交工单</el-button>
            <el-button @click="$router.push('/workorder/list')">取消</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back } from '@element-plus/icons-vue'
import { workorder, devices } from '@/api'

const router = useRouter()
const formRef = ref(null)
const submitting = ref(false)
const deviceList = ref([])
const userList = ref([])

const form = reactive({
  title: '',
  order_type: 'fault',
  priority: 'P3',
  device_id: null,
  assignee: '',
  description: ''
})

const rules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  order_type: [{ required: true, message: '请选择工单类型', trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  description: [{ required: true, message: '请输入工单描述', trigger: 'blur' }]
}

onMounted(async () => {
  // 加载设备列表
  try {
    const res = await devices.getList({ page: 1, page_size: 100 })
    deviceList.value = res.items || []
  } catch (e) { console.error(e) }

  // 加载用户列表
  try {
    const res = await fetch('/api/v1/admin/users').then(r => r.json())
    userList.value = res.items || []
  } catch (e) { console.error(e) }
})

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
      title: form.title,
      order_type: form.order_type,
      priority: form.priority,
      description: form.description
    }
    if (form.device_id) payload.device_id = form.device_id
    if (form.assignee) payload.assignee = form.assignee

    await workorder.create(payload)
    ElMessage.success('工单创建成功')
    router.push('/workorder/list')
  } catch (error) {
    console.error('Create workorder error:', error)
    ElMessage.error('创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
.page-container { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-subtitle { margin: 4px 0 0; color: #909399; font-size: 13px; }
.form-container { max-width: 700px; }
</style>
