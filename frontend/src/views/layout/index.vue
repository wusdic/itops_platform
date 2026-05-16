<template>
  <n-layout has-sider class="layout">
    <!-- 侧边栏 -->
    <n-layout-sider
      bordered
      :collapsed="collapsed"
      :collapsed-width="64"
      :width="220"
      show-trigger
      collapse-mode="width"
      @collapse="collapsed = !collapsed"
      :native-scrollbar="false"
      class="sider"
    >
      <div class="logo" @click="$router.push('/dashboard')">
        <n-icon size="26" color="#18a058"><ServerOutline /></n-icon>
        <span v-show="!collapsed" class="logo-text">ITOps</span>
      </div>
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        @update:value="onMenuSelect"
        :indent="16"
      />
    </n-layout-sider>

    <!-- 主内容区 -->
    <n-layout class="main">
      <n-layout-header class="header">
        <n-breadcrumb>
          <n-breadcrumb-item v-for="b in breadcrumbs" :key="b">{{ b }}</n-breadcrumb-item>
        </n-breadcrumb>
        <n-space align="center">
          <n-badge :value="3" :max="99">
            <n-button quaternary circle size="small">
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
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  ServerOutline, GridOutline, DesktopOutline, SearchOutline,
  AlertOutline, FlashOutline, ClipboardOutline, TicketOutline,
  BookOutline, SparklesOutline, BarChartOutline,
  NotificationsOutline, SettingsOutline, TimeOutline,
  Ticket, DocumentText, CreateOutline
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const collapsed = ref(false)
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

const menuOptions = [
  { key: '/dashboard', label: '仪表盘', icon: icon(GridOutline) },
  { key: 'monitoring', label: '监控中心', icon: icon(ServerOutline), children: [
    { key: '/monitoring/devices', label: '设备监控' },
    { key: '/monitoring/alerts', label: '告警管理' },
    { key: '/monitoring/performance', label: '性能监控' },
  ]},
  { key: 'workorder', label: '工单管理', icon: icon(TicketOutline), children: [
    { key: '/workorder/list', label: '工单列表' },
    { key: '/workorder/create', label: '创建工单' },
    { key: '/workorder/my', label: '我的工单' },
  ]},
  { key: 'knowledge', label: '知识库', icon: icon(BookOutline), children: [
    { key: '/knowledge/list', label: '知识文档' },
    { key: '/knowledge/category', label: '分类管理' },
  ]},
  { key: 'ai', label: 'AI助手', icon: icon(SparklesOutline), children: [
    { key: '/ai/copilot', label: '智能问答' },
    { key: '/ai/analyze', label: '智能分析' },
  ]},
  { key: 'automation', label: '自动化', icon: icon(FlashOutline), children: [
    { key: '/automation/script', label: '脚本管理' },
    { key: '/automation/task', label: '任务调度' },
    { key: '/automation/execute', label: '执行记录' },
  ]},
  { key: 'backup', label: '备份管理', icon: icon(DocumentText), children: [
    { key: '/backup/list', label: '备份记录' },
    { key: '/backup/restore', label: '恢复管理' },
  ]},
  { key: 'notification', label: '消息中心', icon: icon(NotificationsOutline), children: [
    { key: '/notification/message', label: '我的消息' },
    { key: '/notification/config', label: '通知配置' },
  ]},
  { key: 'system', label: '系统管理', icon: icon(SettingsOutline), children: [
    { key: '/system/user', label: '用户管理' },
    { key: '/system/role', label: '角色管理' },
    { key: '/system/menu', label: '菜单管理' },
    { key: '/system/dict', label: '字典管理' },
    { key: '/system/config', label: '参数配置' },
  ]},
]

const breadcrumbs = computed(() => {
  const result = []
  route.matched.forEach(r => { if (r.meta.title) result.push(r.meta.title) })
  return result.length ? result : ['仪表盘']
})

function onMenuSelect(key) {
  if (key) router.push(key)
}

const userDropdown = [
  { label: '个人中心', key: 'profile' },
  { label: '修改密码', key: 'password' },
  { type: 'divider', key: 'd1' },
  { label: '退出登录', key: 'logout' },
]

function onUserAction(key) {
  if (key === 'logout') {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
    message.success('已退出')
  } else if (key === 'password') {
    message.info('修改密码功能开发中')
  } else if (key === 'profile') {
    message.info('个人中心功能开发中')
  }
}
</script>

<style scoped>
.layout { height: 100vh; }
.sider { background: #f8f9fa; }
.logo {
  display: flex; align-items: center; justify-content: center;
  height: 52px; gap: 8px; border-bottom: 1px solid #eee; cursor: pointer;
}
.logo-text { font-size: 17px; font-weight: 700; color: #18a058; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; height: 48px; background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04); z-index: 1;
}
.content { background: #f0f2f5; }
.page { padding: 20px; }
</style>
