<template>
  <n-layout has-sider class="layout" :native-scrollbar="false">
    <!-- Mobile Header -->
    <n-layout-header class="mobile-header">
      <n-space align="center">
        <n-button quaternary circle size="small" @click="toggleSidebar">
          <template #icon>
            <n-icon><MenuOutline /></n-icon>
          </template>
        </n-button>
        <span class="mobile-title">ITOps</span>
      </n-space>
      <n-space align="center">
        <n-badge :value="notificationCount" :max="99" :show="notificationCount > 0">
          <n-button quaternary circle size="small" @click="$router.push('/notification/message')">
            <template #icon><n-icon><NotificationsOutline /></n-icon></template>
          </n-button>
        </n-badge>
        <n-dropdown :options="userDropdown" @select="onUserAction">
          <n-space align="center" style="cursor:pointer;padding:0 8px">
            <n-avatar round size="small" style="background:#18a058">
              {{ username.charAt(0).toUpperCase() }}
            </n-avatar>
            <span style="font-size:13px" class="mobile-username">{{ username }}</span>
          </n-space>
        </n-dropdown>
      </n-space>
    </n-layout-header>

    <!-- Sidebar -->
    <n-layout-sider
      bordered
      :collapsed="collapsed"
      :collapsed-width="64"
      :width="220"
      show-trigger="bar"
      collapse-mode="width"
      :native-scrollbar="false"
      class="sider"
      :class="{ 'mobile-sider': isMobile }"
      :style="isMobile && !collapsed ? { position: 'fixed', left: 0, top: 0, bottom: 0, zIndex: 1000, transform: 'translateX(-100%)', transition: 'transform 0.3s' } : {}"
    >
      <!-- Overlay for mobile -->
      <div v-if="isMobile && !collapsed" class="sidebar-overlay" @click="collapsed = true"></div>

      <div class="logo" @click="goHome">
        <n-icon size="26" color="#18a058"><ServerOutline /></n-icon>
        <span v-show="!collapsed" class="logo-text">ITOps</span>
      </div>

      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        :indent="16"
        @update:value="onMenuSelect"
      />
    </n-layout-sider>

    <!-- Main Content Area -->
    <n-layout class="main">
      <n-layout-header class="header">
        <n-breadcrumb>
          <n-breadcrumb-item v-for="b in breadcrumbs" :key="b">{{ b }}</n-breadcrumb-item>
        </n-breadcrumb>
        <n-space align="center" class="desktop-only">
          <n-badge :value="notificationCount" :max="99" :show="notificationCount > 0">
            <n-button quaternary circle size="small" @click="$router.push('/notification/message')">
              <template #icon><n-icon><NotificationsOutline /></n-icon></template>
            </n-button>
          </n-badge>
          <n-dropdown :options="userDropdown" @select="onUserAction">
            <n-space align="center" style="cursor:pointer;padding:0 8px">
              <n-avatar round size="small" style="background:#18a058">
                {{ username.charAt(0).toUpperCase() }}
              </n-avatar>
              <span style="font-size:13px">{{ username }}</span>
            </n-space>
          </n-dropdown>
        </n-space>
      </n-layout-header>

      <n-layout-content class="content" :native-scrollbar="false">
        <div class="page">
          <router-view />
        </div>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import {
  ServerOutline, GridOutline, DesktopOutline,
  AlertOutline, FlashOutline, TicketOutline,
  BookOutline, SparklesOutline, DocumentText,
  NotificationsOutline, SettingsOutline, MenuOutline,
  Ticket, TimeOutline
} from '@vicons/ionicons5'
import { notification } from '@/api'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const dialog = useDialog()

const collapsed = ref(false)
const isMobile = ref(false)
const notificationCount = ref(0)
const activeKey = computed(() => route.path)

const username = computed(() => {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) return JSON.parse(userStr).username || 'admin'
  } catch {}
  return 'admin'
})

function icon(comp) {
  return () => h(comp)
}

// Helper to create parent menu items (non-clickable headers)
function parentItem(label, iconComp) {
  return {
    key: label,
    label,
    icon: icon(iconComp),
    disabled: true,
    show: true
  }
}

// Helper to create child menu items
function childItem(path, label) {
  return {
    key: path,
    label,
    path
  }
}

const menuOptions = [
  { key: '/dashboard', label: '仪表盘', icon: icon(GridOutline) },
  parentItem('监控中心', ServerOutline),
  childItem('/monitoring/devices', '设备监控'),
  childItem('/monitoring/alerts', '告警管理'),
  childItem('/monitoring/performance', '性能监控'),
  parentItem('工单管理', TicketOutline),
  childItem('/workorder/list', '工单列表'),
  childItem('/workorder/create', '创建工单'),
  childItem('/workorder/my', '我的工单'),
  parentItem('知识库', BookOutline),
  childItem('/knowledge/list', '知识文档'),
  childItem('/knowledge/category', '分类管理'),
  parentItem('AI助手', SparklesOutline),
  childItem('/ai/copilot', '智能问答'),
  childItem('/ai/analyze', '智能分析'),
  parentItem('自动化', FlashOutline),
  childItem('/automation/script', '脚本管理'),
  childItem('/automation/task', '任务调度'),
  childItem('/automation/execute', '执行记录'),
  parentItem('备份管理', DocumentText),
  childItem('/backup/list', '备份记录'),
  childItem('/backup/restore', '恢复管理'),
  parentItem('消息中心', NotificationsOutline),
  childItem('/notification/message', '我的消息'),
  childItem('/notification/config', '通知配置'),
  parentItem('系统管理', SettingsOutline),
  childItem('/system/user', '用户管理'),
  childItem('/system/role', '角色管理'),
  childItem('/system/menu', '菜单管理'),
  childItem('/system/dict', '字典管理'),
  childItem('/system/config', '参数配置'),
  childItem('/system/logs', '日志查看'),
  childItem('/system/adapters', '适配器管理'),
]

const breadcrumbs = computed(() => {
  const result = []
  route.matched.forEach(r => { if (r.meta.title) result.push(r.meta.title) })
  return result.length ? result : ['仪表盘']
})

function goHome() {
  router.push('/dashboard')
}

function toggleSidebar() {
  collapsed.value = !collapsed.value
}

function onMenuSelect(key) {
  // Ignore clicks on parent menu items (they have spaces in key or are disabled)
  if (!key || key.includes(' ') || key === key.toUpperCase().slice(0, -1)) {
    return
  }
  router.push(key)
}

const userDropdown = [
  { label: '个人中心', key: 'profile' },
  { label: '修改密码', key: 'password' },
  { type: 'divider', key: 'd1' },
  { label: '退出登录', key: 'logout' },
]

function onUserAction(key) {
  if (key === 'logout') {
    dialog.warning({
      title: '退出确认',
      content: '确定要退出登录吗？',
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: () => {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        message.success('已退出登录')
        router.push('/login')
      }
    })
  } else if (key === 'password') {
    message.info('修改密码功能开发中')
  } else if (key === 'profile') {
    message.info('个人中心功能开发中')
  }
}

const fetchNotificationCount = async () => {
  try {
    const res = await notification.getHistory({ page: 1, page_size: 1 })
    // Assuming API returns { items: [...], total: number } or direct total
    notificationCount.value = res?.total || (Array.isArray(res) ? res.length : 0)
  } catch (err) {
    console.warn('Failed to fetch notification count:', err)
    // Silently fail, notification badge will show 0
  }
}

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    collapsed.value = true
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  fetchNotificationCount()
  // Poll for new notifications every 60 seconds
  const interval = setInterval(fetchNotificationCount, 60000)
  onUnmounted(() => clearInterval(interval))
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.layout {
  height: 100vh;
}

.sider {
  background: #f8f9fa;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 52px;
  gap: 8px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
}

.logo-text {
  font-size: 17px;
  font-weight: 700;
  color: #18a058;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 48px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  z-index: 1;
}

.content {
  background: #f0f2f5;
}

.page {
  padding: 20px;
}

/* Mobile styles */
.mobile-header {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 48px;
  padding: 0 12px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  z-index: 999;
}

.mobile-title {
  font-size: 16px;
  font-weight: 700;
  color: #18a058;
}

.mobile-sider {
  position: fixed !important;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 1000;
}

.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: -1;
}

.desktop-only {
  display: flex;
}

.mobile-username {
  display: none;
}

@media (max-width: 768px) {
  .mobile-header {
    display: flex;
    justify-content: space-between;
  }

  .header {
    display: none;
  }

  .sider:not(.mobile-sider) {
    display: none;
  }

  .main {
    margin-top: 48px;
  }

  .page {
    padding: 12px;
  }

  .desktop-only {
    display: none;
  }

  .mobile-username {
    display: inline;
  }
}
</style>
