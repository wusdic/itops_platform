import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/index.vue'),
    meta: { title: '仪表盘' }
  },
  // 监控中心
  {
    path: '/monitoring/devices',
    name: 'Devices',
    component: () => import('@/views/monitoring/devices.vue'),
    meta: { title: '设备监控', parent: '监控中心' }
  },
  {
    path: '/monitoring/alerts',
    name: 'Alerts',
    component: () => import('@/views/monitoring/alerts.vue'),
    meta: { title: '告警管理', parent: '监控中心' }
  },
  {
    path: '/monitoring/performance',
    name: 'Performance',
    component: () => import('@/views/monitoring/performance.vue'),
    meta: { title: '性能监控', parent: '监控中心' }
  },
  // 工单管理
  {
    path: '/workorder/list',
    name: 'WorkOrderList',
    component: () => import('@/views/workorder/list.vue'),
    meta: { title: '工单列表', parent: '工单管理' }
  },
  {
    path: '/workorder/create',
    name: 'WorkOrderCreate',
    component: () => import('@/views/workorder/create.vue'),
    meta: { title: '创建工单', parent: '工单管理' }
  },
  {
    path: '/workorder/my',
    name: 'WorkOrderMy',
    component: () => import('@/views/workorder/my.vue'),
    meta: { title: '我的工单', parent: '工单管理' }
  },
  // 知识库
  {
    path: '/knowledge/list',
    name: 'KnowledgeList',
    component: () => import('@/views/knowledge/list.vue'),
    meta: { title: '知识文档', parent: '知识库' }
  },
  {
    path: '/knowledge/category',
    name: 'KnowledgeCategory',
    component: () => import('@/views/knowledge/category.vue'),
    meta: { title: '分类管理', parent: '知识库' }
  },
  // AI助手
  {
    path: '/ai/copilot',
    name: 'AICopilot',
    component: () => import('@/views/ai/copilot.vue'),
    meta: { title: '智能问答', parent: 'AI助手' }
  },
  {
    path: '/ai/analyze',
    name: 'AIAnalyze',
    component: () => import('@/views/ai/analyze.vue'),
    meta: { title: '智能分析', parent: 'AI助手' }
  },
  // 自动化
  {
    path: '/automation/script',
    name: 'AutomationScript',
    component: () => import('@/views/automation/script.vue'),
    meta: { title: '脚本管理', parent: '自动化' }
  },
  {
    path: '/automation/task',
    name: 'AutomationTask',
    component: () => import('@/views/automation/task.vue'),
    meta: { title: '任务调度', parent: '自动化' }
  },
  {
    path: '/automation/execute',
    name: 'AutomationExecute',
    component: () => import('@/views/automation/execute.vue'),
    meta: { title: '执行记录', parent: '自动化' }
  },
  // 备份管理
  {
    path: '/backup/list',
    name: 'BackupList',
    component: () => import('@/views/backup/list.vue'),
    meta: { title: '备份记录', parent: '备份管理' }
  },
  {
    path: '/backup/restore',
    name: 'BackupRestore',
    component: () => import('@/views/backup/restore.vue'),
    meta: { title: '恢复管理', parent: '备份管理' }
  },
  // 消息中心
  {
    path: '/notification/message',
    name: 'NotificationMessage',
    component: () => import('@/views/notification/message.vue'),
    meta: { title: '我的消息', parent: '消息中心' }
  },
  {
    path: '/notification/config',
    name: 'NotificationConfig',
    component: () => import('@/views/notification/config.vue'),
    meta: { title: '通知配置', parent: '消息中心' }
  },
  // 系统管理
  {
    path: '/system/user',
    name: 'SystemUser',
    component: () => import('@/views/system/user.vue'),
    meta: { title: '用户管理', parent: '系统管理' }
  },
  {
    path: '/system/role',
    name: 'SystemRole',
    component: () => import('@/views/system/role.vue'),
    meta: { title: '角色管理', parent: '系统管理' }
  },
  {
    path: '/system/menu',
    name: 'SystemMenu',
    component: () => import('@/views/system/menu.vue'),
    meta: { title: '菜单管理', parent: '系统管理' }
  },
  {
    path: '/system/dict',
    name: 'SystemDict',
    component: () => import('@/views/system/dict.vue'),
    meta: { title: '字典管理', parent: '系统管理' }
  },
  {
    path: '/system/config',
    name: 'SystemConfig',
    component: () => import('@/views/system/config.vue'),
    meta: { title: '参数配置', parent: '系统管理' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 智能运维平台` : '智能运维平台'
  const token = localStorage.getItem('token')

  if (to.path !== '/login' && !token) {
    next('/login')
    return
  }

  if (to.path === '/login' && token) {
    next('/dashboard')
    return
  }

  next()
})

export default router
