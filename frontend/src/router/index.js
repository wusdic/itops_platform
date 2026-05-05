import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import Dashboard from '../views/Dashboard.vue'
import Devices from '../views/Devices.vue'
import Alerts from '../views/Alerts.vue'
import WorkOrder from '../views/WorkOrder.vue'
import Knowledge from '../views/Knowledge.vue'
import KnowledgeBase from '../views/KnowledgeBase.vue'
import Notifications from '../views/Notifications.vue'
import Scheduler from '../views/Scheduler.vue'
import Reports from '../views/Reports.vue'
import Assets from '../views/Assets.vue'
import AICopilot from '../views/AICopilot.vue'
import Settings from '../views/Settings.vue'
import Login from '../views/Login.vue'

// 路由白名单（不需要登录）
const whiteList = ['/login', '/register']

// 路由配置
const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'Login', component: Login, meta: { requiresAuth: false } },
  { path: '/dashboard', name: 'Dashboard', component: Dashboard, meta: { requiresAuth: true, title: '监控仪表盘' } },
  { path: '/devices', name: 'Devices', component: Devices, meta: { requiresAuth: true, title: '设备管理' } },
  { path: '/alerts', name: 'Alerts', component: Alerts, meta: { requiresAuth: true, title: '告警中心' } },
  { path: '/workorder', name: 'WorkOrder', component: WorkOrder, meta: { requiresAuth: true, title: '工单管理' } },
  { path: '/knowledge', name: 'Knowledge', component: Knowledge, meta: { requiresAuth: true, title: '知识库' } },
  { path: '/knowledge-base', name: 'KnowledgeBase', component: KnowledgeBase, meta: { requiresAuth: true, title: 'RAG知识库' } },
  { path: '/notifications', name: 'Notifications', component: Notifications, meta: { requiresAuth: true, title: '通知渠道' } },
  { path: '/scheduler', name: 'Scheduler', component: Scheduler, meta: { requiresAuth: true, title: '任务调度' } },
  { path: '/reports', name: 'Reports', component: Reports, meta: { requiresAuth: true, title: '报告中心' } },
  { path: '/assets', name: 'Assets', component: Assets, meta: { requiresAuth: true, title: '资产管理' } },
  { path: '/ai-copilot', name: 'AICopilot', component: AICopilot, meta: { requiresAuth: true, title: 'AI助手' } },
  { path: '/settings', name: 'Settings', component: Settings, meta: { requiresAuth: true, title: '系统设置' } }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const requiresAuth = to.meta.requiresAuth !== false
  
  if (requiresAuth && !token) {
    // 需要登录但没有token
    ElMessage.warning('请先登录')
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && token) {
    // 已登录访问登录页，重定向到首页
    next('/dashboard')
  } else {
    next()
  }
})

// 路由错误处理
router.onError((error) => {
  console.error('Router error:', error)
  ElMessage.error('页面加载失败，请刷新重试')
})

export default router

// 导出路由配置供其他地方使用
export { routes }
