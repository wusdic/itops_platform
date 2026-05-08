<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="decoration-circle circle-1" />
      <div class="decoration-circle circle-2" />
      <div class="decoration-circle circle-3" />
    </div>

    <div class="login-container">
      <!-- 左侧品牌区 -->
      <div class="brand-section">
        <div class="brand-content">
          <div class="brand-logo">
            <svg
              width="56"
              height="56"
              viewBox="0 0 56 56"
              fill="none"
            >
              <rect
                width="56"
                height="56"
                rx="14"
                fill="#165dff"
              />
              <path
                d="M14 21L28 14L42 21V35L28 42L14 35V21Z"
                stroke="white"
                stroke-width="2.5"
              />
              <circle
                cx="28"
                cy="28"
                r="5"
                fill="white"
              />
            </svg>
          </div>
          <h1 class="brand-title">
            IT运维平台
          </h1>
          <p class="brand-subtitle">
            智能化 · 自动化 · 本地化
          </p>
          
          <div class="feature-list">
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><Monitor /></el-icon>
              </div>
              <div class="feature-text">
                <span class="feature-title">全方位监控</span>
                <span class="feature-desc">服务器、网络设备、安全设备一网打尽</span>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              <div class="feature-text">
                <span class="feature-title">AI智能助手</span>
                <span class="feature-desc">本地大模型驱动，智能运维辅助</span>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><Bell /></el-icon>
              </div>
              <div class="feature-text">
                <span class="feature-title">告警即时达</span>
                <span class="feature-desc">多渠道通知，确保重要告警不遗漏</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧登录区 -->
      <div class="login-section">
        <div class="login-card">
          <div class="login-header">
            <h2 class="login-title">
              {{ isLogin ? '欢迎回来' : '创建账号' }}
            </h2>
            <p class="login-hint">
              {{ isLogin ? '请登录您的账号继续使用' : '填写以下信息完成注册' }}
            </p>
          </div>

          <!-- 登录/注册表单切换 -->
          <div class="form-tabs">
            <button 
              class="tab-btn" 
              :class="{ active: isLogin }"
              @click="isLogin = true"
            >
              账号登录
            </button>
            <button 
              class="tab-btn" 
              :class="{ active: !isLogin }"
              @click="isLogin = false"
            >
              注册账号
            </button>
          </div>

          <!-- 登录表单 -->
          <transition
            name="slide-fade"
            mode="out-in"
          >
            <el-form 
              v-if="isLogin"
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              class="login-form"
              @submit.prevent="handleLogin"
            >
              <div class="form-item">
                <label class="form-label">用户名 / 手机号</label>
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名或手机号"
                  size="large"
                  :prefix-icon="User"
                  class="form-input"
                />
              </div>

              <div class="form-item">
                <label class="form-label">
                  <span>密码</span>
                  <el-link
                    type="primary"
                    class="forgot-link"
                  >忘记密码？</el-link>
                </label>
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                  class="form-input"
                />
              </div>

              <div class="form-options">
                <el-checkbox v-model="loginForm.remember">
                  记住登录状态
                </el-checkbox>
              </div>

              <el-button 
                type="primary" 
                size="large" 
                :loading="loginLoading"
                class="submit-btn"
                native-type="submit"
              >
                {{ loginLoading ? '登录中...' : '登 录' }}
              </el-button>
            </el-form>

            <!-- 注册表单 -->
            <el-form 
              v-else
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              class="login-form"
              @submit.prevent="handleRegister"
            >
              <div class="form-item">
                <label class="form-label">用户名</label>
                <el-input
                  v-model="registerForm.username"
                  placeholder="3-20位字母、数字或下划线"
                  size="large"
                  :prefix-icon="User"
                  class="form-input"
                />
              </div>

              <div class="form-item">
                <label class="form-label">邮箱</label>
                <el-input
                  v-model="registerForm.email"
                  placeholder="请输入邮箱地址"
                  size="large"
                  :prefix-icon="Message"
                  class="form-input"
                />
              </div>

              <div class="form-item">
                <label class="form-label">密码</label>
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="8位以上，包含字母和数字"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                  class="form-input"
                />
              </div>

              <div class="form-item">
                <label class="form-label">确认密码</label>
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="再次输入密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                  class="form-input"
                />
              </div>

              <div class="form-options">
                <el-checkbox v-model="registerForm.agreeTerms">
                  我已阅读并同意 <el-link type="primary">
                    《服务条款》
                  </el-link> 和 <el-link type="primary">
                    《隐私政策》
                  </el-link>
                </el-checkbox>
              </div>

              <el-button 
                type="primary" 
                size="large" 
                :loading="registerLoading"
                class="submit-btn"
                native-type="submit"
              >
                {{ registerLoading ? '注册中...' : '立即注册' }}
              </el-button>
            </el-form>
          </transition>

          <!-- 其他登录方式 -->
          <div
            v-if="isLogin"
            class="social-login"
          >
            <div class="divider">
              <span>其他登录方式</span>
            </div>
            <div class="social-icons">
              <button
                class="social-btn"
                title="企业微信"
              >
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-6h2v6zm4 0h-2v-6h2v6zm-2-8c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z" />
                </svg>
              </button>
              <button
                class="social-btn"
                title="钉钉"
              >
                <el-icon><Share /></el-icon>
              </button>
              <button
                class="social-btn"
                title="飞书"
              >
                <el-icon><Connection /></el-icon>
              </button>
            </div>
          </div>
        </div>

        <!-- 底部版权 -->
        <div class="login-footer">
          <p>© 2024 IT运维平台 · 完全本地化部署 · 适用于内网环境</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, Monitor, ChatDotRound, Bell, Share, Connection } from '@element-plus/icons-vue'
import { auth } from '@/api'

const router = useRouter()

// 状态
const isLogin = ref(true)
const loginFormRef = ref(null)
const registerFormRef = ref(null)
const loginLoading = ref(false)
const registerLoading = ref(false)

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
  remember: false
})

// 注册表单
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  agreeTerms: false
})

// 登录验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

// 注册验证规则
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3-20个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
    { pattern: /^(?=.*[a-zA-Z])(?=.*\d).+$/, message: '密码需包含字母和数字', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
  agreeTerms: [
    { 
      validator: (rule, value, callback) => {
        value ? callback() : callback(new Error('请勾选同意条款'))
      }, 
      trigger: 'change' 
    }
  ]
}

// 登录
const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  try {
    await loginFormRef.value.validate()
    loginLoading.value = true
    
    // 调用真实登录API
    const response = await auth.login({
      username: loginForm.username,
      password: loginForm.password
    })
    
    // 保存登录状态
    localStorage.setItem('token', response.access_token)
    localStorage.setItem('userInfo', JSON.stringify({
      id: response.user_id,
      username: loginForm.username,
      role: 'admin'
    }))
    
    ElMessage.success({ message: '登录成功，欢迎回来！', duration: 2000 })
    router.push('/dashboard')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.detail || '用户名或密码错误')
    }
  } finally {
    loginLoading.value = false
  }
}

// 注册
const handleRegister = async () => {
  if (!registerFormRef.value) return
 
  try {
    await registerFormRef.value.validate()
    registerLoading.value = true
    
    // 调用真实注册API
    await auth.register({
      username: registerForm.username,
      password: registerForm.password,
      email: registerForm.email
    })
    
    ElMessage.success({ message: '注册成功，请登录！', duration: 2000 })
    
    // 切换到登录表单
    isLogin.value = true
    registerForm.username = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    registerForm.email = ''
    registerForm.agreeTerms = false
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.detail || '注册失败')
    }
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  position: relative;
  overflow: hidden;
}

// ========== 背景装饰 ==========
.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;

  .decoration-circle {
    position: absolute;
    border-radius: 50%;
    opacity: 0.6;
  }

  .circle-1 {
    width: 400px;
    height: 400px;
    background: linear-gradient(135deg, rgba(22, 93, 255, 0.15), rgba(22, 93, 255, 0.05));
    top: -100px;
    right: -100px;
    animation: float 20s ease-in-out infinite;
  }

  .circle-2 {
    width: 300px;
    height: 300px;
    background: linear-gradient(135deg, rgba(0, 180, 42, 0.1), rgba(0, 180, 42, 0.02));
    bottom: -50px;
    left: -50px;
    animation: float 25s ease-in-out infinite reverse;
  }

  .circle-3 {
    width: 200px;
    height: 200px;
    background: linear-gradient(135deg, rgba(245, 63, 63, 0.08), rgba(245, 63, 63, 0.02));
    top: 40%;
    left: 10%;
    animation: float 18s ease-in-out infinite;
  }
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  25% { transform: translate(20px, -20px) rotate(5deg); }
  50% { transform: translate(0, -30px) rotate(0deg); }
  75% { transform: translate(-20px, -10px) rotate(-5deg); }
}

// ========== 容器 ==========
.login-container {
  display: flex;
  width: 1000px;
  min-height: 600px;
  background: $bg-container;
  border-radius: $border-radius-xl;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  animation: fadeInUp 0.6s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// ========== 品牌区 ==========
.brand-section {
  flex: 1;
  background: linear-gradient(135deg, #165dff 0%, #4285f4 100%);
  color: #fff;
  padding: $spacing-xxxl;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-content {
  max-width: 360px;
}

.brand-logo {
  margin-bottom: $spacing-lg;

  svg {
    filter: drop-shadow(0 4px 12px rgba(22, 93, 255, 0.4));
  }
}

.brand-title {
  font-size: $font-size-xxl;
  font-weight: $font-weight-bold;
  margin-bottom: $spacing-sm;
  letter-spacing: 1px;
}

.brand-subtitle {
  font-size: $font-size-base;
  opacity: 0.8;
  margin-bottom: $spacing-xxl;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: $spacing-md;

  .feature-icon {
    width: 40px;
    height: 40px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
  }

  .feature-text {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .feature-title {
      font-size: $font-size-base;
      font-weight: $font-weight-semibold;
    }

    .feature-desc {
      font-size: $font-size-sm;
      opacity: 0.7;
    }
  }
}

// ========== 登录区 ==========
.login-section {
  width: 440px;
  padding: $spacing-xxl $spacing-xxxl;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-card {
  width: 100%;
}

.login-header {
  margin-bottom: $spacing-xl;
  
  .login-title {
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin-bottom: $spacing-xs;
  }
  
  .login-hint {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

// ========== 表单切换 ==========
.form-tabs {
  display: flex;
  background: $bg-page;
  border-radius: $border-radius-md;
  padding: 4px;
  margin-bottom: $spacing-xl;

  .tab-btn {
    flex: 1;
    padding: $spacing-sm $spacing-md;
    border: none;
    background: transparent;
    font-size: $font-size-sm;
    color: $text-secondary;
    cursor: pointer;
    border-radius: $border-radius-sm;
    transition: $transition-fast;

    &.active {
      background: $bg-container;
      color: $primary;
      font-weight: $font-weight-medium;
      box-shadow: $shadow-sm;
    }

    &:hover:not(.active) {
      color: $text-primary;
    }
  }
}

// ========== 表单 ==========
.login-form {
  .form-item {
    margin-bottom: $spacing-lg;
  }

  .form-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $spacing-sm;
    font-size: $font-size-sm;
    color: $text-regular;
    font-weight: $font-weight-medium;

    .forgot-link {
      font-size: $font-size-xs;
    }
  }

  .form-input {
    :deep(.el-input__wrapper) {
      padding: 12px 16px;
      border-radius: $border-radius-md;
    }
  }
}

.form-options {
  margin-bottom: $spacing-xl;
  
  :deep(.el-checkbox__label) {
    font-size: $font-size-sm;
    color: $text-regular;
  }
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: $font-size-md;
  font-weight: $font-weight-semibold;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-lg;
  transition: $transition-base;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(22, 93, 255, 0.3);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }
}

// ========== 社交登录 ==========
.social-login {
  .divider {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    margin-bottom: $spacing-lg;
    color: $text-placeholder;
    font-size: $font-size-xs;

    &::before,
    &::after {
      content: '';
      flex: 1;
      height: 1px;
      background: $border;
    }
  }

  .social-icons {
    display: flex;
    justify-content: center;
    gap: $spacing-lg;
  }

  .social-btn {
    width: 44px;
    height: 44px;
    border: 1px solid $border;
    border-radius: $border-radius-md;
    background: $bg-container;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $text-secondary;
    font-size: 20px;
    transition: $transition-fast;

    &:hover {
      border-color: $primary;
      color: $primary;
      background: rgba($primary, 0.04);
    }
  }
}

// ========== 底部 ==========
.login-footer {
  margin-top: $spacing-xxl;
  text-align: center;

  p {
    font-size: $font-size-xs;
    color: $text-placeholder;
  }
}

// ========== 动画 ==========
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

// ========== 响应式 ==========
@include respond-to('lg') {
  .login-container {
    flex-direction: column;
    width: 100%;
    min-height: auto;
    border-radius: 0;
  }

  .brand-section {
    padding: $spacing-xxl;
  }

  .login-section {
    width: 100%;
    padding: $spacing-xl;
  }
}

@include respond-to('sm') {
  .brand-section {
    display: none;
  }

  .login-section {
    padding: $spacing-lg;
  }
}
</style>