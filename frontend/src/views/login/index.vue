<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <div class="logo">
          <svg width="48" height="48" viewBox="0 0 32 32" fill="none">
            <rect width="32" height="32" rx="8" fill="#165dff"/>
            <path d="M8 12L16 8L24 12V20L16 24L8 20V12Z" stroke="white" stroke-width="2"/>
            <circle cx="16" cy="16" r="3" fill="white"/>
          </svg>
        </div>
        <h1 class="title">智能运维平台</h1>
        <p class="subtitle">IT Operations Platform</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" class="login-form" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item prop="captcha">
          <div class="captcha-row">
            <el-input v-model="form.captcha" placeholder="请输入验证码" size="large" prefix-icon="CircleCheck" style="flex: 1" @keyup.enter="handleLogin" />
            <div class="captcha-img" @click="refreshCaptcha">
              <img v-if="captchaUrl" :src="captchaUrl" alt="验证码" />
            </div>
          </div>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.remember">记住密码</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" style="width: 100%" @click="handleLogin">
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span class="copyright">© 2024 智能运维平台 v3.0</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { auth } from '@/api'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const appStore = useAppStore()
const formRef = ref(null)
const loading = ref(false)
const captchaUrl = ref('')

const form = reactive({
  username: '',
  password: '',
  captcha: '',
  remember: false
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
}

onMounted(() => {
  // 填充记住的用户名
  const savedUsername = localStorage.getItem('savedUsername')
  if (savedUsername) {
    form.username = savedUsername
    form.remember = true
  }
  refreshCaptcha()
})

const refreshCaptcha = () => {
  captchaUrl.value = `/api/auth/captcha?t=${Date.now()}`
}

const handleLogin = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await auth.login({
      username: form.username,
      password: form.password,
      captcha: form.captcha
    })

    // 保存token和用户信息
    appStore.setToken(res.token)
    appStore.setUserInfo(res.userInfo)

    // 记住用户名
    if (form.remember) {
      localStorage.setItem('savedUsername', form.username)
    } else {
      localStorage.removeItem('savedUsername')
    }

    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    console.error('Login error:', error)
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-box {
  width: 420px;
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;

  .logo {
    margin-bottom: 16px;
  }

  .title {
    font-size: 24px;
    font-weight: 600;
    color: #1d2129;
    margin: 0 0 8px;
  }

  .subtitle {
    font-size: 14px;
    color: #86909c;
    margin: 0;
  }
}

.login-form {
  .captcha-row {
    display: flex;
    gap: 12px;
    width: 100%;
  }

  .captcha-img {
    width: 120px;
    height: 40px;
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    background: #f7f8fa;
    display: flex;
    align-items: center;
    justify-content: center;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }
}

.login-footer {
  text-align: center;
  margin-top: 24px;

  .copyright {
    font-size: 12px;
    color: #86909c;
  }
}

:deep(.el-input__wrapper) {
  padding: 12px 16px;
}

:deep(.el-button--large) {
  height: 44px;
  font-size: 16px;
}
</style>
