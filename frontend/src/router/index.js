import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/layout/index.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘' }
      },
      // 监控中心
      {
        path: 'monitoring/devices',
        name: 'Devices',
        component: () => import('@/views/monitoring/devices.vue'),
        meta: { title: '设备监控', parent: '监控中心' }
      },
      {
        path: 'monitoring/alerts',
        name: 'Alerts',
        component: () => import('@/views/monitoring/alerts.vue'),
        meta: { title: '告警管理', parent: '监控中心' }
      },
      {
        path: 'monitoring/performance',
        name: 'Performance',
        component: () => import('@/views/monitoring/performance.vue'),
        meta: { title: '性能监控', parent: '监控中心' }
      },
      // 工单管理
      {
        path: 'workorder/list',
        name: 'WorkOrderList',
        component: () => import('@/views/workorder/list.vue'),
        meta: { title: '工单列表', parent: '工单管理' }
      },
      {
        path: 'workorder/create',
        name: 'WorkOrderCreate',
        component: () => import('@/views/workorder/create.vue'),
        meta: { title: '创建工单', parent: '工单管理' }
      },
      {
        path: 'workorder/my',
        name: 'WorkOrderMy',
        component: () => import('@/views/workorder/my.vue'),
        meta: { title: '我的工单', parent: '工单管理' }
      },
      // 知识库
      {
        path: 'knowledge/list',
        name: 'KnowledgeList',
        component: () => import('@/views/knowledge/list.vue'),
        meta: { title: '知识文档', parent: '知识库' }
      },
      {
        path: 'knowledge/category',
        name: 'KnowledgeCategory',
        component: () => import('@/views/knowledge/category.vue'),
        meta: { title: '分类管理', parent: '知识库' }
      },
      {
        path: 'knowledge/cases',
        name: 'KnowledgeCases',
        component: () => import('@/views/knowledge/cases.vue'),
        meta: { title: '故障案例', parent: '知识库' }
      },
      // AI助手
      {
        path: 'ai/chat',
        name: 'AIChat',
        component: () => import('@/views/ai/chat.vue'),
        meta: { title: 'AI 聊天', parent: 'AI助手' }
      },
      {
        path: 'ai/copilot',
        name: 'AICopilot',
        component: () => import('@/views/ai/copilot.vue'),
        meta: { title: '智能问答', parent: 'AI助手' }
      },
      {
        path: 'ai/analyze',
        name: 'AIAnalyze',
        component: () => import('@/views/ai/analyze.vue'),
        meta: { title: '智能分析', parent: 'AI助手' }
      },
      // 自动化
      {
        path: 'automation/script',
        name: 'AutomationScript',
        component: () => import('@/views/automation/script.vue'),
        meta: { title: '脚本管理', parent: '自动化' }
      },
      {
        path: 'automation/task',
        name: 'AutomationTask',
        component: () => import('@/views/automation/task.vue'),
        meta: { title: '任务调度', parent: '自动化' }
      },
      {
        path: 'automation/execute',
        name: 'AutomationExecute',
        component: () => import('@/views/automation/execute.vue'),
        meta: { title: '执行记录', parent: '自动化' }
      },
      // 备份管理
      {
        path: 'backup/list',
        name: 'BackupList',
        component: () => import('@/views/backup/list.vue'),
        meta: { title: '备份记录', parent: '备份管理' }
      },
      {
        path: 'backup/restore',
        name: 'BackupRestore',
        component: () => import('@/views/backup/restore.vue'),
        meta: { title: '恢复管理', parent: '备份管理' }
      },
      // 消息中心
      {
        path: 'notification/message',
        name: 'NotificationMessage',
        component: () => import('@/views/notification/message.vue'),
        meta: { title: '我的消息', parent: '消息中心' }
      },
      {
        path: 'notification/history',
        name: 'NotificationHistory',
        component: () => import('@/views/notification/history.vue'),
        meta: { title: '消息历史', parent: '消息中心' }
      },
      {
        path: 'notification/config',
        name: 'NotificationConfig',
        component: () => import('@/views/notification/config.vue'),
        meta: { title: '通知配置', parent: '消息中心' }
      },
      // 系统管理
      {
        path: 'system/user',
        name: 'SystemUser',
        component: () => import('@/views/system/user.vue'),
        meta: { title: '用户管理', parent: '系统管理' }
      },
      {
        path: 'system/role',
        name: 'SystemRole',
        component: () => import('@/views/system/role.vue'),
        meta: { title: '角色管理', parent: '系统管理' }
      },
      {
        path: 'system/menu',
        name: 'SystemMenu',
        component: () => import('@/views/system/menu.vue'),
        meta: { title: '菜单管理', parent: '系统管理' }
      },
      {
        path: 'system/dict',
        name: 'SystemDict',
        component: () => import('@/views/system/dict.vue'),
        meta: { title: '字典管理', parent: '系统管理' }
      },
      {
        path: 'system/config',
        name: 'SystemConfig',
        component: () => import('@/views/system/config.vue'),
        meta: { title: '参数配置', parent: '系统管理' }
      },
      {
        path: 'system/logs',
        name: 'SystemLogs',
        component: () => import('@/views/system/logs.vue'),
        meta: { title: '日志查看', parent: '系统管理' }
      },
      // 报表管理
      {
        path: 'report/list',
        name: 'ReportList',
        component: () => import('@/views/report/list.vue'),
        meta: { title: '报表管理', parent: '报表管理' }
      },
      {
        path: 'report/create',
        name: 'ReportCreate',
        component: () => import('@/views/report/create.vue'),
        meta: { title: '生成报表', parent: '报表管理' }
      },
      {
        path: 'report/template',
        name: 'ReportTemplate',
        component: () => import('@/views/report/template.vue'),
        meta: { title: '模板管理', parent: '报表管理' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  // 设置页面标题
  document.title = to.meta.title
    ? `${to.meta.title} - 智能运维平台`
    : '智能运维平台'

  // 访问登录页：如果已登录，直接跳转后台
  if (to.path === '/login') {
    if (token) {
      next('/dashboard')
    } else {
      next()
    }
    return
  }

  // 其他页面：需要登录
  if (!token) {
    next('/login')
    return
  }

  next()
})

export default router
