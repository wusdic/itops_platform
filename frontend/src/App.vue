<template>
  <div class="app-layout" :class="{ 'is-collapse': isCollapse }">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="8" fill="#165dff"/>
              <path d="M8 12L16 8L24 12V20L16 24L8 20V12Z" stroke="white" stroke-width="2"/>
              <circle cx="16" cy="16" r="3" fill="white"/>
            </svg>
          </div>
          <span class="logo-text" v-show="!isCollapse">IT运维平台</span>
        </div>
        <button class="collapse-btn" @click="toggleCollapse">
          <el-icon :size="18">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
        </button>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        class="sidebar-menu"
        background-color="#1f1f1f"
        text-color="#a6a8ab"
        active-text-color="#ffffff"
        :router="true"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>监控仪表盘</template>
        </el-menu-item>

        <el-sub-menu index="monitor">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>监控管理</span>
          </template>
          <el-menu-item index="/devices">设备列表</el-menu-item>
          <el-menu-item index="/alerts">告警中心</el-menu-item>
          <el-menu-item index="/assets">资产管理</el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/workorder">
          <el-icon><Document /></el-icon>
          <template #title>工单管理</template>
        </el-menu-item>

        <el-sub-menu index="knowledge">
          <template #title>
            <el-icon><Reading /></el-icon>
            <span>知识中心</span>
          </template>
          <el-menu-item index="/knowledge">知识库</el-menu-item>
          <el-menu-item index="/knowledge-base">RAG知识库</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="operation">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>运维工具</span>
          </template>
          <el-menu-item index="/scheduler">任务调度</el-menu-item>
          <el-menu-item index="/reports">报告中心</el-menu-item>
          <el-menu-item index="/notifications">通知渠道</el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/ai-copilot">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>AI助手</template>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-icon><Tools /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>

      <!-- 底部用户信息 -->
      <div class="sidebar-footer">
        <div class="user-info" @click="handleUserMenu">
          <el-avatar :size="32" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c059fc9f4c5da60f png?s=1645185542760" />
          <div class="user-detail" v-show="!isCollapse">
            <span class="username">{{ username }}</span>
            <span class="role">{{ userRole }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-container">
      <!-- 顶部导航 -->
      <header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="parentTitle">{{ parentTitle }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 快捷搜索 -->
          <el-button class="search-btn" @click="showSearch = true">
            <el-icon><Search /></el-icon>
            <span>搜索...</span>
            <kbd>⌘K</kbd>
          </el-button>

          <!-- 通知 -->
          <el-badge :value="alertCount" :hidden="alertCount === 0" :max="99" type="danger">
            <el-button circle class="header-btn" @click="$router.push('/alerts')">
              <el-icon><Bell /></el-icon>
            </el-button>
          </el-badge>

          <!-- 全屏 -->
          <el-button circle class="header-btn" @click="toggleFullscreen">
            <el-icon><FullScreen /></el-icon>
          </el-button>

          <!-- 主题切换 -->
          <el-button circle class="header-btn" @click="toggleTheme">
            <el-icon><Sunny v-if="theme === 'dark'" /><Moon v-else /></el-icon>
          </el-button>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- 搜索面板 -->
    <transition name="fade">
      <div class="search-overlay" v-if="showSearch" @click.self="showSearch = false">
        <div class="search-panel">
          <div class="search-input-wrapper">
            <el-icon><Search /></el-icon>
            <input 
              v-model="searchKeyword" 
              placeholder="搜索功能、文档、工单..." 
              @keyup.escape="showSearch = false"
              ref="searchInput"
            />
            <kbd>ESC</kbd>
          </div>
          <div class="search-results" v-if="searchResults.length > 0">
            <div 
              v-for="(result, index) in searchResults" 
              :key="index"
              class="search-item"
              @click="handleSearchClick(result)"
            >
              <el-icon><component :is="result.icon" /></el-icon>
              <span>{{ result.title }}</span>
              <span class="search-tag">{{ result.path }}</span>
            </div>
          </div>
          <div class="search-tips" v-else>
            <p>输入关键词搜索...</p>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  Odometer, Monitor, Document, Reading, Setting, ChatDotRound, 
  Bell, FullScreen, Sunny, Moon, Search, Tools, Fold, Expand
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 状态
const isCollapse = ref(false)
const showSearch = ref(false)
const searchKeyword = ref('')
const searchInput = ref(null)
const theme = ref('light')

// 用户信息
const username = ref('管理员')
const userRole = ref('系统管理员')
const alertCount = ref(3)

// 计算属性
const activeMenu = computed(() => route.path)
const pageTitle = computed(() => route.meta.title || '仪表盘')
const parentTitle = computed(() => route.meta.parentTitle || '')

// 搜索菜单配置
const menuItems = [
  { title: '监控仪表盘', path: '/dashboard', icon: 'Odometer' },
  { title: '设备列表', path: '/devices', icon: 'Monitor' },
  { title: '告警中心', path: '/alerts', icon: 'Bell' },
  { title: '资产管理', path: '/assets', icon: 'Server' },
  { title: '工单管理', path: '/workorder', icon: 'Document' },
  { title: '知识库', path: '/knowledge', icon: 'Reading' },
  { title: 'RAG知识库', path: '/knowledge-base', icon: 'Folder' },
  { title: '任务调度', path: '/scheduler', icon: 'Timer' },
  { title: '报告中心', path: '/reports', icon: 'DataLine' },
  { title: '通知渠道', path: '/notifications', icon: 'Message' },
  { title: 'AI助手', path: '/ai-copilot', icon: 'ChatDotRound' },
  { title: '系统设置', path: '/settings', icon: 'Tools' }
]

// 搜索结果
const searchResults = computed(() => {
  if (!searchKeyword.value) return []
  const keyword = searchKeyword.value.toLowerCase()
  return menuItems.filter(item => 
    item.title.toLowerCase().includes(keyword)
  ).slice(0, 8)
})

// 监听搜索显示
watch(showSearch, (val) => {
  if (val) {
    setTimeout(() => searchInput.value?.focus(), 100)
  } else {
    searchKeyword.value = ''
  }
})

// 方法
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

const toggleTheme = () => {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme.value)
}

const handleUserMenu = () => {
  router.push('/settings')
}

const handleSearchClick = (result) => {
  showSearch.value = false
  router.push(result.path)
}

// 键盘快捷键
const handleKeydown = (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    showSearch.value = true
  }
}

// 初始化
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  
  // 恢复折叠状态
  const savedCollapse = localStorage.getItem('sidebar-collapse')
  if (savedCollapse) {
    isCollapse.value = savedCollapse === 'true'
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// 监听折叠状态变化
watch(isCollapse, (val) => {
  localStorage.setItem('sidebar-collapse', val.toString())
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.app-layout {
  display: flex;
  height: 100vh;
  background: $bg-page;
}

// ========== 侧边栏 ==========
.sidebar {
  width: $sidebar-width;
  height: 100vh;
  background: #1f1f1f;
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 100;

  .is-collapse & {
    width: $sidebar-collapsed-width;
  }
}

.sidebar-header {
  height: $header-height;
  @include flex-between;
  padding: 0 $spacing-md;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  .logo {
    @include flex-center;
    gap: $spacing-sm;

    .logo-icon {
      width: 32px;
      height: 32px;
      flex-shrink: 0;
    }

    .logo-text {
      font-size: $font-size-md;
      font-weight: $font-weight-semibold;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
    }
  }

  .collapse-btn {
    width: 28px;
    height: 28px;
    border: none;
    background: rgba(255, 255, 255, 0.06);
    border-radius: $border-radius-sm;
    color: #a6a8ab;
    cursor: pointer;
    @include flex-center;
    transition: $transition-fast;

    &:hover {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }
  }
}

.sidebar-menu {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  border-right: none;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
  }

  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 48px;
    line-height: 48px;
    margin: 4px 8px;
    padding: 0 12px !important;
    border-radius: $border-radius-md;
    transition: $transition-fast;

    &:hover {
      background: rgba(255, 255, 255, 0.06) !important;
    }

    .el-icon {
      font-size: 18px;
      margin-right: 12px;
    }
  }

  :deep(.el-menu-item.is-active) {
    background: $primary !important;
    color: #fff !important;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      background: #fff;
      border-radius: 0 2px 2px 0;
    }
  }

  :deep(.el-sub-menu .el-menu-item) {
    height: 42px;
    line-height: 42px;
    margin: 2px 8px;
    padding-left: 44px !important;
  }
}

.sidebar-footer {
  padding: $spacing-md;
  border-top: 1px solid rgba(255, 255, 255, 0.06);

  .user-info {
    @include flex-center;
    gap: $spacing-sm;
    padding: $spacing-sm;
    border-radius: $border-radius-md;
    cursor: pointer;
    transition: $transition-fast;

    &:hover {
      background: rgba(255, 255, 255, 0.06);
    }

    .user-detail {
      display: flex;
      flex-direction: column;

      .username {
        color: #fff;
        font-size: $font-size-sm;
        font-weight: $font-weight-medium;
      }

      .role {
        color: #8a8a8a;
        font-size: $font-size-xs;
      }
    }
  }
}

// ========== 主容器 ==========
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// ========== 顶部导航 ==========
.header {
  height: $header-height;
  @include flex-between;
  padding: 0 $spacing-xl;
  background: $bg-container;
  border-bottom: 1px solid $border-light;
  box-shadow: $shadow-xs;

  .header-left {
    .el-breadcrumb {
      font-size: $font-size-sm;
    }
  }

  .header-right {
    @include flex-center;
    gap: $spacing-sm;

    .search-btn {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      padding: 8px 16px;
      border: 1px solid $border;
      border-radius: $border-radius-md;
      background: $bg-page;
      color: $text-secondary;
      cursor: pointer;
      transition: $transition-fast;
      font-size: $font-size-sm;

      &:hover {
        border-color: $primary;
        color: $primary;
      }

      kbd {
        padding: 2px 6px;
        background: $bg-container;
        border: 1px solid $border;
        border-radius: $border-radius-xs;
        font-size: 11px;
        font-family: inherit;
      }
    }

    .header-btn {
      width: 36px;
      height: 36px;
      @include flex-center;
      border: none;
      background: transparent;
      color: $text-secondary;
      transition: $transition-fast;

      &:hover {
        background: $bg-page;
        color: $primary;
      }
    }
  }
}

// ========== 内容区 ==========
.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: $spacing-lg;
  @include custom-scrollbar;
}

// ========== 搜索面板 ==========
.search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 2000;
  @include flex-center;
}

.search-panel {
  width: 560px;
  max-height: 70vh;
  background: $bg-container;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-lg;
  overflow: hidden;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-md $spacing-xl;
  border-bottom: 1px solid $border-light;

  .el-icon {
    color: $text-secondary;
    font-size: 20px;
  }

  input {
    flex: 1;
    border: none;
    outline: none;
    font-size: $font-size-md;
    background: transparent;

    &::placeholder {
      color: $text-placeholder;
    }
  }

  kbd {
    padding: 4px 8px;
    background: $bg-page;
    border: 1px solid $border;
    border-radius: $border-radius-sm;
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

.search-results {
  padding: $spacing-sm;

  .search-item {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-md $spacing-lg;
    border-radius: $border-radius-md;
    cursor: pointer;
    transition: $transition-fast;

    &:hover {
      background: $bg-page;
    }

    .el-icon {
      color: $text-secondary;
    }

    .search-tag {
      margin-left: auto;
      font-size: $font-size-xs;
      color: $text-placeholder;
    }
  }
}

.search-tips {
  padding: $spacing-xl;
  text-align: center;
  color: $text-secondary;
}

// ========== 过渡动画 ==========
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.2s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// ========== 响应式 ==========
@include respond-to('lg') {
  .sidebar {
    position: fixed;
    left: -$sidebar-width;
    
    &.is-show {
      left: 0;
    }
  }

  .main-container {
    width: 100%;
  }
}
</style>