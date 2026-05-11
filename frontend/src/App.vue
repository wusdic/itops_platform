<template>
  <div class="app-wrapper" :class="{ 'sidebar-collapsed': isCollapsed }">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo" @click="$router.push('/dashboard')">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <rect width="32" height="32" rx="8" fill="#165dff"/>
            <path d="M8 12L16 8L24 12V20L16 24L8 20V12Z" stroke="white" stroke-width="2"/>
            <circle cx="16" cy="16" r="3" fill="white"/>
          </svg>
          <span v-show="!isCollapsed" class="logo-text">智能运维平台</span>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        class="sidebar-menu"
        background-color="#001529"
        text-color="rgba(255,255,255,0.65)"
        active-text-color="#fff"
      >
        <el-menu-item index="/dashboard" @click="$router.push('/dashboard')">
          <el-icon><HomeFilled /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>

        <el-sub-menu index="monitoring">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>监控中心</span>
          </template>
          <el-menu-item index="/monitoring/devices" @click="$router.push('/monitoring/devices')">设备监控</el-menu-item>
          <el-menu-item index="/monitoring/alerts" @click="$router.push('/monitoring/alerts')">告警管理</el-menu-item>
          <el-menu-item index="/monitoring/performance" @click="$router.push('/monitoring/performance')">性能监控</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="workorder">
          <template #title>
            <el-icon><Tickets /></el-icon>
            <span>工单管理</span>
          </template>
          <el-menu-item index="/workorder/list" @click="$router.push('/workorder/list')">工单列表</el-menu-item>
          <el-menu-item index="/workorder/create" @click="$router.push('/workorder/create')">创建工单</el-menu-item>
          <el-menu-item index="/workorder/my" @click="$router.push('/workorder/my')">我的工单</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="knowledge">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>知识库</span>
          </template>
          <el-menu-item index="/knowledge/list" @click="$router.push('/knowledge/list')">知识文档</el-menu-item>
          <el-menu-item index="/knowledge/category" @click="$router.push('/knowledge/category')">分类管理</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="ai">
          <template #title>
            <el-icon><ChatDotRound /></el-icon>
            <span>AI助手</span>
          </template>
          <el-menu-item index="/ai/copilot" @click="$router.push('/ai/copilot')">智能问答</el-menu-item>
          <el-menu-item index="/ai/analyze" @click="$router.push('/ai/analyze')">智能分析</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="automation">
          <template #title>
            <el-icon><Connection /></el-icon>
            <span>自动化</span>
          </template>
          <el-menu-item index="/automation/script" @click="$router.push('/automation/script')">脚本管理</el-menu-item>
          <el-menu-item index="/automation/task" @click="$router.push('/automation/task')">任务调度</el-menu-item>
          <el-menu-item index="/automation/execute" @click="$router.push('/automation/execute')">执行记录</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="backup">
          <template #title>
            <el-icon><FolderOpened /></el-icon>
            <span>备份管理</span>
          </template>
          <el-menu-item index="/backup/list" @click="$router.push('/backup/list')">备份记录</el-menu-item>
          <el-menu-item index="/backup/restore" @click="$router.push('/backup/restore')">恢复管理</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="notification">
          <template #title>
            <el-icon><Bell /></el-icon>
            <span>消息中心</span>
          </template>
          <el-menu-item index="/notification/message" @click="$router.push('/notification/message')">我的消息</el-menu-item>
          <el-menu-item index="/notification/config" @click="$router.push('/notification/config')">通知配置</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/system/user" @click="$router.push('/system/user')">用户管理</el-menu-item>
          <el-menu-item index="/system/role" @click="$router.push('/system/role')">角色管理</el-menu-item>
          <el-menu-item index="/system/menu" @click="$router.push('/system/menu')">菜单管理</el-menu-item>
          <el-menu-item index="/system/dict" @click="$router.push('/system/dict')">字典管理</el-menu-item>
          <el-menu-item index="/system/config" @click="$router.push('/system/config')">参数配置</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </aside>

    <!-- 右侧主内容 -->
    <div class="main-wrapper">
      <!-- 顶部导航 -->
      <header class="navbar">
        <div class="navbar-left">
          <el-icon class="collapse-btn" @click="toggleSidebar">
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentParent">{{ currentParent }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="navbar-right">
          <el-badge :value="3" :max="99" class="navbar-item">
            <el-icon size="20"><Bell /></el-icon>
          </el-badge>
          <el-icon size="20" class="navbar-item" @click="toggleFullscreen">
            <FullScreen />
          </el-icon>
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
              <span class="username">{{ username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="settings">系统设置</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const isCollapsed = ref(false)
const username = computed(() => appStore.username || '管理员')

// 菜单映射
const menuMap = {
  '/monitoring': '监控中心',
  '/workorder': '工单管理',
  '/knowledge': '知识库',
  '/ai': 'AI助手',
  '/automation': '自动化',
  '/backup': '备份管理',
  '/notification': '消息中心',
  '/system': '系统管理'
}

const activeMenu = computed(() => route.path)

const currentParent = computed(() => {
  const path = route.path
  for (const [key, value] of Object.entries(menuMap)) {
    if (path.startsWith(key)) return value
  }
  return ''
})

const currentTitle = computed(() => {
  const titles = {
    '/dashboard': '仪表盘',
    '/monitoring/devices': '设备监控',
    '/monitoring/alerts': '告警管理',
    '/monitoring/performance': '性能监控',
    '/workorder/list': '工单列表',
    '/workorder/create': '创建工单',
    '/workorder/my': '我的工单',
    '/knowledge/list': '知识文档',
    '/knowledge/category': '分类管理',
    '/ai/copilot': '智能问答',
    '/ai/analyze': '智能分析',
    '/automation/script': '脚本管理',
    '/automation/task': '任务调度',
    '/automation/execute': '执行记录',
    '/backup/list': '备份记录',
    '/backup/restore': '恢复管理',
    '/notification/message': '我的消息',
    '/notification/config': '通知配置',
    '/system/user': '用户管理',
    '/system/role': '角色管理',
    '/system/menu': '菜单管理',
    '/system/dict': '字典管理',
    '/system/config': '参数配置'
  }
  return titles[route.path] || ''
})

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

const handleCommand = (command) => {
  switch (command) {
    case 'profile':
      router.push('/system/profile')
      break
    case 'settings':
      router.push('/system/config')
      break
    case 'logout':
      ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        appStore.logout()
        router.push('/login')
        ElMessage.success('已退出登录')
      }).catch(() => {})
      break
  }
}

// 监听路由变化
watch(() => route.path, () => {
  document.title = currentTitle.value ? `${currentTitle.value} - 智能运维平台` : '智能运维平台'
}, { immediate: true })
</script>

<style lang="scss">
@import '@/assets/styles/variables.scss';

.app-wrapper {
  display: flex;
  min-height: 100vh;
  background: $bg-page;
}

.sidebar {
  width: $sidebar-width;
  background: $sidebar-bg;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 1001;
  transition: width 0.3s;
  overflow: hidden;

  .sidebar-header {
    height: 60px;
    display: flex;
    align-items: center;
    padding: 0 16px;
    border-bottom: 1px solid rgba(255,255,255,0.1);

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;

      .logo-text {
        font-size: 16px;
        font-weight: 600;
        color: #fff;
        white-space: nowrap;
      }
    }
  }

  .sidebar-menu {
    border-right: none;
    height: calc(100vh - 60px);
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(255,255,255,0.2);
      border-radius: 2px;
    }
  }
}

.main-wrapper {
  flex: 1;
  margin-left: $sidebar-width;
  min-height: 100vh;
  transition: margin-left 0.3s;
}

.sidebar-collapsed {
  .sidebar {
    width: $sidebar-collapsed-width;
  }

  .main-wrapper {
    margin-left: $sidebar-collapsed-width;
  }
}

.navbar {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid $border-light;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: sticky;
  top: 0;
  z-index: 100;

  .navbar-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .collapse-btn {
      font-size: 20px;
      cursor: pointer;
      color: $text-secondary;
      transition: color 0.2s;

      &:hover {
        color: $primary;
      }
    }
  }

  .navbar-right {
    display: flex;
    align-items: center;
    gap: 20px;

    .navbar-item {
      cursor: pointer;
      color: $text-secondary;
      transition: color 0.2s;

      &:hover {
        color: $primary;
      }
    }

    .user-dropdown {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      transition: background 0.2s;

      &:hover {
        background: $bg-page;
      }

      .username {
        font-size: 14px;
        color: $text-primary;
      }
    }
  }
}

.main-content {
  padding: 20px;
  min-height: calc(100vh - 60px);
}

// 路由过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
