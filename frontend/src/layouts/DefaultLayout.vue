<template>
  <n-layout has-sider class="layout">
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
      <div class="logo">
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
import { useAuthStore } from '@/stores/auth'
import { useMessage } from 'naive-ui'
import {
  ServerOutline, GridOutline, DesktopOutline, SearchOutline,
  AlertOutline, FlashOutline, ClipboardOutline, TicketOutline,
  BookOutline, SparklesOutline, BarChartOutline,
  NotificationsOutline, SettingsOutline, TimeOutline
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const authStore = useAuthStore()
const collapsed = ref(false)
const activeKey = computed(() => route.path)

const username = computed(() => authStore.user?.username || 'admin')

function icon(comp) {
  return () => h(comp)
}

const menuOptions = [
  { key: '/dashboard', label: '仪表盘', icon: icon(GridOutline) },
  { key: 'assets', label: '资产管理', icon: icon(DesktopOutline), children: [
    { key: '/assets', label: '设备列表' },
    { key: '/assets/groups', label: '设备分组' },
    { key: '/assets/configs', label: '配置管理' },
    { key: '/assets/business', label: '业务系统' },
  ]},
  { key: 'devices', label: '设备监控', icon: icon(ServerOutline), children: [
    { key: '/devices', label: '设备列表' },
    { key: '/devices/metrics', label: '指标配置' },
    { key: '/devices/import', label: '批量导入' },
  ]},
  { key: 'discovery', label: '设备发现', icon: icon(SearchOutline), children: [
    { key: '/discovery/scan', label: '设备扫描' },
    { key: '/discovery/results', label: '扫描结果' },
    { key: '/discovery/tasks', label: '发现任务' },
  ]},
  { key: 'monitoring', label: '监控告警', icon: icon(AlertOutline), children: [
    { key: '/monitoring/alerts', label: '告警管理' },
    { key: '/monitoring/rules', label: '告警规则' },
    { key: '/monitoring/metrics', label: '监控指标' },
    { key: '/monitoring/dashboards', label: '监控仪表盘' },
  ]},
  { key: 'automation', label: '自动化', icon: icon(FlashOutline), children: [
    { key: '/automation/rules', label: '触发规则' },
    { key: '/automation/executions', label: '执行历史' },
  ]},
  { key: 'inspection', label: '巡检管理', icon: icon(ClipboardOutline), children: [
    { key: '/inspection/tasks', label: '巡检任务' },
    { key: '/inspection/reports', label: '巡检报告' },
  ]},
  { key: 'workorders', label: '工单管理', icon: icon(TicketOutline), children: [
    { key: '/workorders', label: '工单列表' },
    { key: '/workorders/create', label: '创建工单' },
    { key: '/workorders/my', label: '我的工单' },
  ]},
  { key: 'knowledge', label: '知识库', icon: icon(BookOutline), children: [
    { key: '/knowledge/docs', label: 'SOP文档' },
    { key: '/knowledge/cases', label: '故障案例' },
    { key: '/knowledge/categories', label: '分类与审核' },
  ]},
  { key: 'ai', label: 'AI助手', icon: icon(SparklesOutline), children: [
    { key: '/ai/chat', label: '智能问答' },
    { key: '/ai/analysis', label: 'AI分析' },
  ]},
  { key: 'reports', label: '报表中心', icon: icon(BarChartOutline), children: [
    { key: '/reports/templates', label: '报表模板' },
    { key: '/reports/list', label: '报表列表' },
    { key: '/reports/scheduled', label: '定时报表' },
  ]},
  { key: 'notifications', label: '通知管理', icon: icon(NotificationsOutline), children: [
    { key: '/notifications/channels', label: '通知渠道' },
    { key: '/notifications/history', label: '通知历史' },
    { key: '/notifications/rules', label: '通知规则' },
  ]},
  { key: 'system', label: '系统管理', icon: icon(SettingsOutline), children: [
    { key: '/system/users', label: '用户管理' },
    { key: '/system/roles', label: '角色管理' },
    { key: '/system/configs', label: '系统配置' },
    { key: '/system/backups', label: '备份管理' },
    { key: '/system/logs', label: '操作日志' },
    { key: '/system/api-keys', label: 'API密钥' },
  ]},
  { key: '/scheduler/tasks', label: '定时任务', icon: icon(TimeOutline) },
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
    authStore.logout().then(() => { router.push('/login'); message.success('已退出') })
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
  height: 52px; gap: 8px; border-bottom: 1px solid #eee;
}
.logo-text { font-size: 17px; font-weight: 700; color: #18a058; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; height: 48px; background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  z-index: 1;
}
.content { background: #f0f2f5; }
.page { padding: 20px; }
</style>
