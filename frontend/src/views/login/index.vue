<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="login-card">
        <div class="login-header">
          <n-icon size="40" color="#18a058"><ServerOutline /></n-icon>
          <h1>ITOps Platform</h1>
          <p>智能运维管理平台</p>
        </div>
        <n-form ref="formRef" :model="formData" :rules="rules" size="large">
          <n-form-item path="username">
            <n-input v-model:value="formData.username" placeholder="用户名" :input-props="{ autocomplete: 'username' }">
              <template #prefix>
                <n-icon><PersonOutline /></n-icon>
              </template>
            </n-input>
          </n-form-item>
          <n-form-item path="password">
            <n-input v-model:value="formData.password" type="password" placeholder="密码" show-password-on="click" :input-props="{ autocomplete: 'current-password' }" @keydown.enter="handleLogin">
              <template #prefix>
                <n-icon><LockClosedOutline /></n-icon>
              </template>
            </n-input>
          </n-form-item>
          <n-form-item path="captcha">
            <n-space style="width:100%">
              <n-input v-model:value="formData.captcha" placeholder="验证码" style="flex:1" @keydown.enter="handleLogin" />
              <div class="captcha-box" @click="refreshCaptcha">
                <img v-if="captchaImg" :src="captchaImg" alt="验证码" />
                <span v-else>点击获取</span>
              </div>
            </n-space>
          </n-form-item>
          <n-form-item>
            <n-checkbox v-model:checked="rememberMe">记住登录</n-checkbox>
          </n-form-item>
          <n-button type="primary" size="large" block :loading="loading" @click="handleLogin" style="height:44px;font-size:15px">
            {{ loading ? '登录中...' : '登 录' }}
          </n-button>
        </n-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { getCaptcha } from '@/api/auth'
import { ServerOutline, PersonOutline, LockClosedOutline } from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const authStore = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const captchaImg = ref('')
const rememberMe = ref(false)

const formData = ref({
  username: '',
  password: '',
  captcha: ''
})

const rules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
  captcha: { required: true, message: '请输入验证码', trigger: 'blur' }
}

async function refreshCaptcha() {
  try {
    const res = await getCaptcha()
    if (res.data && res.data.image) {
      captchaImg.value = res.data.image
    }
  } catch {
    message.error('验证码获取失败')
  }
}

async function handleLogin() {
  try {
    await formRef.value?.validate()
    loading.value = true
    await authStore.login(formData.value.username, formData.value.password, formData.value.captcha)
    message.success('登录成功')
    const redirect = route.query.redirect || '/dashboard'
    router.push(redirect)
  } catch (err) {
    if (err.response?.status === 401) {
      message.error('用户名或密码错误')
      refreshCaptcha()
    } else if (err.message) {
      // validation error
    } else {
      message.error('登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refreshCaptcha()
})
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.login-card { width: 420px; padding: 40px; background: #fff; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.login-header { text-align: center; margin-bottom: 32px; }
.login-header h1 { margin: 12px 0 4px; font-size: 24px; color: #1a1a1a; }
.login-header p { margin: 0; font-size: 14px; color: #999; }
.captcha-box { width: 120px; height: 40px; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; cursor: pointer; display: flex; align-items: center; justify-content: center; background: #f5f5f5; }
.captcha-box img { width: 100%; height: 100%; object-fit: cover; }
.captcha-box span { font-size: 12px; color: #999; }
</style>
