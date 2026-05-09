<template>
  <div class="app-container">
    <!-- 左侧导航 - 简洁风格 -->
    <aside class="sidebar">
      <div class="sidebar-logo" @click="goHome">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <rect width="32" height="32" rx="8" fill="#165dff"/>
          <path d="M8 12L16 8L24 12V20L16 24L8 20V12Z" stroke="white" stroke-width="2"/>
          <circle cx="16" cy="16" r="3" fill="white"/>
        </svg>
        <span class="logo-text">运维平台</span>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item) }"
        >
          <el-icon :size="20">
            <component :is="item.icon" />
          </el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="user-info" @click="handleUserClick">
          <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
          <div class="user-detail">
            <span class="username">{{ username }}</span>
            <span class="role">{{ roleText }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧内容区 -->
    <div class="main-wrapper">
      <!-- 顶部栏 -->
      <header class="topbar">
        <div class="breadcrumb">
          <span class="breadcrumb-item">{{ currentPageName }}</span>
        </div>
        <div class="topbar-actions">
          <el-button text @click="toggleTheme">
            <el-icon><Sunny v-if="isDark" /><Moon v-else /></el-icon>
          </el-button>
          <el-button text @click="showSettings = true">
            <el-icon><Setting /></el-icon>
          </el-button>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="content">
        <router-view />
      </main>
    </div>

    <!-- 设置抽屉 -->
    <el-drawer
      v-model="showSettings"
      title="系统设置"
      size="400px"
    >
      <div class="settings-section">
        <h4>主题设置</h4>
        <div class="theme-options">
          <div
            v-for="theme in themes"
            :key="theme.value"
            class="theme-option"
            :class="{ active: currentTheme === theme.value }"
            @click="setTheme(theme.value)"
          >
            <div class="theme-preview">
              <div class="theme-sidebar" :style="{ background: theme.sidebar }"></div>
              <div class="theme-main" :style="{ background: theme.main }"></div>
            </div>
            <span>{{ theme.label }}</span>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <h4>快捷操作</h4>
        <el-button type="primary" plain @click="handleLogout" style="width: 100%">
          退出登录
        </el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Monitor,
  Document,
  Bell,
  Connection,
  ChatDotRound,
  Tickets,
  DataLine,
  Setting,
  Sunny,
  Moon,
  HomeFilled
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

// 状态
const showSettings = ref(false)
const isDark = ref(false)
const currentTheme = ref('light')

// 用户信息
const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
const username = ref(userInfo.username || '管理员')
const roleText = computed(() => {
  const roles = { admin: '管理员', operator: '运维人员', viewer: '访客' }
  return roles[userInfo.role] || '管理员'
})

// 菜单项
const menuItems = [
  { path: '/dashboard', label: '仪表盘', icon: HomeFilled },
  { path: '/devices', label: '设备管理', icon: Monitor },
  { path: '/alerts', label: '告警管理', icon: Bell },
  { path: '/workorder', label: '工单管理', icon: Tickets },
  { path: '/knowledge', label: '知识库', icon: Document },
  { path: '/reports', label: '报表中心', icon: DataLine },
  { path: '/settings', label: '系统设置', icon: Setting },
]

// 主题选项
const themes = [
  { value: 'light', label: '简约白', sidebar: '#001529', main: '#ffffff' },
  { value: 'blue', label: '科技蓝', sidebar: '#165dff', main: '#ffffff' },
  { value: 'dark', label: '暗夜黑', sidebar: '#141414', main: '#1f1f1f' },
]

// 当前页面名称
const currentPageName = computed(() => {
  const item = menuItems.find(m => route.path.startsWith(m.path))
  return item ? item.label : '仪表盘'
})

// 判断是否激活
const isActive = (item) => {
  if (item.path === '/dashboard') return route.path === '/dashboard'
  return route.path.startsWith(item.path)
}

// 导航
const goHome = () => router.push('/dashboard')

// 主题切换
const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}

const setTheme = (theme) => {
  currentTheme.value = theme
  isDark.value = theme === 'dark'
  document.documentElement.classList.toggle('dark', isDark.value)
}

// 用户操作
const handleUserClick = () => {
  showSettings.value = true
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    router.push('/login')
  }).catch(() => {})
}

// 监听路由变化更新用户名
watch(() => route.path, () => {
  const info = JSON.parse(localStorage.getItem('userInfo') || '{}')
  username.value = info.username || '管理员'
})
</script>

<style lang="scss" scoped>
.app-container {
  display: flex;
  min-height: 100vh;
  background: #f7f8fa;
}

// 侧边栏
.sidebar {
  width: 220px;
  background: #001529;
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 16px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255,255,255,0.1);

  .logo-text {
    font-size: 16px;
    font-weight: 600;
    color: #fff;
  }
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 4px;
  border-radius: 8px;
  color: rgba(255,255,255,0.65);
  text-decoration: none;
  transition: all 0.2s;
  font-size: 14px;

  &:hover {
    background: rgba(255,255,255,0.08);
    color: #fff;
  }

  &.active {
    background: #165dff;
    color: #fff;
  }
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  &:hover {
    background: rgba(255,255,255,0.08);
  }
}

.user-detail {
  display: flex;
  flex-direction: column;

  .username {
    font-size: 14px;
    color: #fff;
  }
  .role {
    font-size: 12px;
    color: rgba(255,255,255,0.45);
  }
}

// 主内容区
.main-wrapper {
  flex: 1;
  margin-left: 220px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e5e6eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 50;
}

.breadcrumb {
  font-size: 16px;
  font-weight: 500;
  color: #1d2129;
}

.topbar-actions {
  display: flex;
  gap: 8px;
}

.content {
  padding: 24px;
  flex: 1;
}

// 设置抽屉
.settings-section {
  margin-bottom: 32px;

  h4 {
    margin: 0 0 16px;
    font-size: 14px;
    font-weight: 500;
    color: #4b4f59;
  }
}

.theme-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.theme-option {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  transition: all 0.2s;

  &.active {
    border-color: #165dff;
  }

  .theme-preview {
    height: 48px;
    display: flex;

    .theme-sidebar {
      width: 40%;
    }
    .theme-main {
      flex: 1;
    }
  }

  span {
    display: block;
    padding: 8px;
    text-align: center;
    font-size: 12px;
    background: #f7f8fa;
  }
}

// 暗色主题
:deep(.dark) {
  .sidebar {
    background: #141414;
  }
  .topbar {
    background: #1f1f1f;
    border-color: #303030;
  }
  .topbar .breadcrumb {
    color: #e8e8e8;
  }
  .content {
    background: #0f0f0f;
  }
}
</style>
