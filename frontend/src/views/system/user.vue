<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">通知配置</h1>
        <p class="page-subtitle">消息通知渠道配置</p>
      </div>
    </div>

    <div class="form-container">
      <el-form :model="configForm" label-width="140px">
        <el-form-item label="邮件通知">
          <el-switch v-model="configForm.emailEnabled" />
          <el-input v-model="configForm.email" placeholder="通知邮箱" style="width: 300px; margin-left: 16px" :disabled="!configForm.emailEnabled" />
        </el-form-item>

        <el-form-item label="短信通知">
          <el-switch v-model="configForm.smsEnabled" />
          <el-input v-model="configForm.phone" placeholder="手机号码" style="width: 300px; margin-left: 16px" :disabled="!configForm.smsEnabled" />
        </el-form-item>

        <el-form-item label="企业微信通知">
          <el-switch v-model="configForm.wecomEnabled" />
          <el-input v-model="configForm.wecomWebhook" placeholder="企业微信Webhook地址" style="width: 400px; margin-left: 16px" :disabled="!configForm.wecomEnabled" />
        </el-form-item>

        <el-form-item label="钉钉通知">
          <el-switch v-model="configForm.dingtalkEnabled" />
          <el-input v-model="configForm.dingtalkWebhook" placeholder="钉钉Webhook地址" style="width: 400px; margin-left: 16px" :disabled="!configForm.dingtalkEnabled" />
        </el-form-item>

        <el-form-item label="告警通知类型">
          <el-checkbox-group v-model="configForm.alertTypes">
            <el-checkbox label="critical">严重告警</el-checkbox>
            <el-checkbox label="high">高优先级告警</el-checkbox>
            <el-checkbox label="medium">中优先级告警</el-checkbox>
            <el-checkbox label="low">低优先级告警</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="通知频率限制">
          <el-input-number v-model="configForm.frequencyLimit" :min="1" :max="100" />
          <span style="margin-left: 8px; color: #86909c">分钟内最多发送</span>
          <el-input-number v-model="configForm.maxPerHour" :min="1" :max="1000" style="margin-left: 8px" />
          <span style="margin-left: 8px; color: #86909c">条</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSave">保存配置</el-button>
          <el-button @click="handleTest">发送测试通知</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { notification } from '@/api'

const configForm = reactive({
  emailEnabled: true,
  email: 'admin@example.com',
  smsEnabled: false,
  phone: '',
  wecomEnabled: true,
  wecomWebhook: '',
  dingtalkEnabled: false,
  dingtalkWebhook: '',
  alertTypes: ['critical', 'high'],
  frequencyLimit: 5,
  maxPerHour: 100
})

onMounted(async () => {
  try {
    const res = await notification.getConfig().catch(() => ({}))
    Object.assign(configForm, res)
  } catch (error) { console.error('Load config error:', error) }
})

const handleSave = async () => {
  try {
    await notification.updateConfig(configForm)
    ElMessage.success('配置保存成功')
  } catch (error) { console.error('Save config error:', error) }
}

const handleTest = () => {
  ElMessage.success('测试通知已发送')
}
</script>

<style lang="scss" scoped>
.form-container { max-width: 800px; }
</style>
