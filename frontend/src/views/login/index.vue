<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-shape shape1"></div>
      <div class="bg-shape shape2"></div>
      <div class="bg-shape shape3"></div>
    </div>
    <div class="login-card">
      <div class="login-header">
        <n-icon size="48" color="#18a058"><ServerOutline /></n-icon>
        <h1>ITOps 智能运维平台</h1>
        <p>IT Operations Platform</p>
      </div>

      <n-form ref="formRef" :model="form" :rules="rules" size="large">
        <n-form-item path="username" label="用户名">
          <n-input v-model:value="form.username" placeholder="请输入用户名" @keydown.enter="handleLogin">
            <template #prefix><n-icon><PersonOutline /></n-icon></template>
          </n-input>
        </n-form-item>
        <n-form-item path="password" label="密码">
          <n-input v-model:value="form.password" type="password" placeholder="请输入密码" show-password-on="mousedown" @keydown.enter="handleLogin">
            <template #prefix><n-icon><LockClosedOutline /></n-icon></template>
          </n-input>
        </n-form-item>
        <n-form-item>
          <n-checkbox v-model:checked="form.remember">记住密码</n-checkbox>
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="loading" block size="large" @click="handleLogin">
            {{ loading ? '登录中...' : '登 录' }}
          </n-button>
        </n-form-item>
      </n-form>

      <div class="login-footer">
        <span>© 2024 ITOps Platform v3.0</span>
        <span>默认账号: admin / Admin@123456</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { ServerOutline, PersonOutline, LockClosedOutline } from '@vicons/ionicons5'
import { auth } from '@/api'

const router = useRouter()
const message = useMessage()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: 'Admin@123456',
  remember: false
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

onMounted(() => {
  const savedUsername = localStorage.getItem('savedUsername')
  if (savedUsername) {
    form.username = savedUsername
    form.remember = true
  }
})

const handleLogin = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    const res = await auth.login({
      username: form.username,
      password: form.password
    })

    const token = res.access_token
    localStorage.setItem('token', token)

    const userInfo = res.user || {}
    localStorage.setItem('user', JSON.stringify(userInfo))

    if (form.remember) {
      localStorage.setItem('savedUsername', form.username)
    } else {
      localStorage.removeItem('savedUsername')
    }

    message.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    message.error(error.response?.data?.message || error.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0c7a43 0%, #18a058 40%, #36ad6a 100%);
  position: relative;
  overflow: hidden;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.1;
}
.shape1 { width: 600px; height: 600px; background: #fff; top: -200px; right: -100px; }
.shape2 { width: 400px; height: 400px; background: #fff; bottom: -150px; left: -100px; }
.shape3 { width: 300px; height: 300px; background: #fff; top: 50%; left: 10%; }

.login-card {
  position: relative;
  z-index: 1;
  width: 420px;
  background: rgba(255,255,255,0.97);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 48px 40px 32px;
  box-shadow: 0 25px 60px rgba(0,0,0,0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.login-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
}

.login-header p {
  margin: 0;
  font-size: 13px;
  color: #8c8c8c;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.login-footer span {
  font-size: 12px;
  color: #8c8c8c;
}
</style>
