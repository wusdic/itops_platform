<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">创建工单</h1>
        <p class="page-subtitle">提交新的运维工单</p>
      </div>
    </div>

    <div class="form-container">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="工单标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入工单标题" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="优先级" prop="priority">
          <el-radio-group v-model="form.priority">
            <el-radio value="urgent">紧急</el-radio>
            <el-radio value="high">高</el-radio>
            <el-radio value="medium">中</el-radio>
            <el-radio value="low">低</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="工单类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择工单类型" style="width: 100%">
            <el-option label="故障报修" value="fault" />
            <el-option label="需求申请" value="requirement" />
            <el-option label="变更申请" value="change" />
            <el-option label="日常巡检" value="inspection" />
          </el-select>
        </el-form-item>

        <el-form-item label="关联设备" prop="device_id">
          <el-select v-model="form.device_id" placeholder="请选择关联设备" style="width: 100%" clearable>
            <el-option label="Web Server 01" value="1" />
            <el-option label="DB Server 01" value="2" />
            <el-option label="App Server 01" value="3" />
          </el-select>
        </el-form-item>

        <el-form-item label="工单描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="6" placeholder="请详细描述工单内容" />
        </el-form-item>

        <el-form-item label="附件">
          <el-upload action="#" :auto-upload="false" :limit="5">
            <el-button>上传附件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 jpg、png、pdf、zip 格式，单个文件不超过10MB</div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="submitting">提交工单</el-button>
          <el-button @click="$router.push('/workorder/list')">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { workorder } from '@/api'

const router = useRouter()
const formRef = ref(null)
const submitting = ref(false)

const form = reactive({
  title: '',
  priority: 'medium',
  type: '',
  device_id: '',
  description: ''
})

const rules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  type: [{ required: true, message: '请选择工单类型', trigger: 'change' }],
  description: [{ required: true, message: '请输入工单描述', trigger: 'blur' }]
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await workorder.create(form)
    ElMessage.success('工单提交成功')
    router.push('/workorder/list')
  } catch (error) {
    console.error('Create workorder error:', error)
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
.form-container { max-width: 800px; }
</style>
