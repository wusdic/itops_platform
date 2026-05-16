import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/login/index.vue'), meta: { title: '登录' } },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/index.vue'), meta: { title: '仪表盘' } },

      // Assets
      { path: 'assets', name: 'Assets', component: () => import('@/views/assets/index.vue'), meta: { title: '设备管理' } },
      { path: 'assets/groups', name: 'AssetGroups', component: () => import('@/views/assets/groups.vue'), meta: { title: '设备分组' } },
      { path: 'assets/configs', name: 'AssetConfigs', component: () => import('@/views/assets/configs.vue'), meta: { title: '配置管理' } },
      { path: 'assets/business', name: 'AssetBusiness', component: () => import('@/views/assets/business.vue'), meta: { title: '业务系统' } },

      // Devices
      { path: 'devices', name: 'Devices', component: () => import('@/views/devices/index.vue'), meta: { title: '设备监控' } },
      { path: 'devices/:name', name: 'DeviceDetail', component: () => import('@/views/devices/detail.vue'), meta: { title: '设备详情' } },
      { path: 'devices/metrics', name: 'DeviceMetrics', component: () => import('@/views/devices/metrics.vue'), meta: { title: '指标配置' } },
      { path: 'devices/import', name: 'DeviceImport', component: () => import('@/views/devices/import.vue'), meta: { title: '批量导入' } },

      // Discovery
      { path: 'discovery/scan', name: 'DiscoveryScan', component: () => import('@/views/discovery/scan.vue'), meta: { title: '设备扫描' } },
      { path: 'discovery/results', name: 'DiscoveryResults', component: () => import('@/views/discovery/results.vue'), meta: { title: '扫描结果' } },
      { path: 'discovery/tasks', name: 'DiscoveryTasks', component: () => import('@/views/discovery/tasks.vue'), meta: { title: '发现任务' } },

      // Monitoring
      { path: 'monitoring/alerts', name: 'MonitoringAlerts', component: () => import('@/views/monitoring/alerts.vue'), meta: { title: '告警管理' } },
      { path: 'monitoring/rules', name: 'MonitoringRules', component: () => import('@/views/monitoring/rules.vue'), meta: { title: '告警规则' } },
      { path: 'monitoring/metrics', name: 'MonitoringMetrics', component: () => import('@/views/monitoring/metrics.vue'), meta: { title: '监控指标' } },
      { path: 'monitoring/dashboards', name: 'MonitoringDashboards', component: () => import('@/views/monitoring/dashboards.vue'), meta: { title: '监控仪表盘' } },

      // Automation
      { path: 'automation/rules', name: 'AutomationRules', component: () => import('@/views/automation/rules.vue'), meta: { title: '触发规则' } },
      { path: 'automation/executions', name: 'AutomationExecutions', component: () => import('@/views/automation/executions.vue'), meta: { title: '执行历史' } },

      // Inspection
      { path: 'inspection/tasks', name: 'InspectionTasks', component: () => import('@/views/inspection/tasks.vue'), meta: { title: '巡检任务' } },
      { path: 'inspection/reports', name: 'InspectionReports', component: () => import('@/views/inspection/reports.vue'), meta: { title: '巡检报告' } },

      // Workorders
      { path: 'workorders', name: 'Workorders', component: () => import('@/views/workorder/index.vue'), meta: { title: '工单列表' } },
      { path: 'workorders/create', name: 'WorkorderCreate', component: () => import('@/views/workorder/create.vue'), meta: { title: '创建工单' } },
      { path: 'workorders/:id', name: 'WorkorderDetail', component: () => import('@/views/workorder/detail.vue'), meta: { title: '工单详情' } },
      { path: 'workorders/my', name: 'WorkorderMy', component: () => import('@/views/workorder/my.vue'), meta: { title: '我的工单' } },

      // Knowledge
      { path: 'knowledge/docs', name: 'KnowledgeDocs', component: () => import('@/views/knowledge/docs.vue'), meta: { title: 'SOP文档' } },
      { path: 'knowledge/cases', name: 'KnowledgeCases', component: () => import('@/views/knowledge/cases.vue'), meta: { title: '故障案例' } },
      { path: 'knowledge/categories', name: 'KnowledgeCategories', component: () => import('@/views/knowledge/categories.vue'), meta: { title: '分类与审核' } },

      // AI
      { path: 'ai/chat', name: 'AiChat', component: () => import('@/views/ai/chat.vue'), meta: { title: '智能问答' } },
      { path: 'ai/analysis', name: 'AiAnalysis', component: () => import('@/views/ai/analysis.vue'), meta: { title: 'AI分析' } },

      // Reports
      { path: 'reports/templates', name: 'ReportTemplates', component: () => import('@/views/reports/templates.vue'), meta: { title: '报表模板' } },
      { path: 'reports/list', name: 'ReportList', component: () => import('@/views/reports/list.vue'), meta: { title: '报表列表' } },
      { path: 'reports/scheduled', name: 'ReportScheduled', component: () => import('@/views/reports/scheduled.vue'), meta: { title: '定时报表' } },

      // Notifications
      { path: 'notifications/channels', name: 'NotifChannels', component: () => import('@/views/notifications/channels.vue'), meta: { title: '通知渠道' } },
      { path: 'notifications/history', name: 'NotifHistory', component: () => import('@/views/notifications/history.vue'), meta: { title: '通知历史' } },
      { path: 'notifications/rules', name: 'NotifRules', component: () => import('@/views/notifications/rules.vue'), meta: { title: '通知规则' } },

      // System
      { path: 'system/users', name: 'SystemUsers', component: () => import('@/views/system/users.vue'), meta: { title: '用户管理' } },
      { path: 'system/roles', name: 'SystemRoles', component: () => import('@/views/system/roles.vue'), meta: { title: '角色管理' } },
      { path: 'system/configs', name: 'SystemConfigs', component: () => import('@/views/system/configs.vue'), meta: { title: '系统配置' } },
      { path: 'system/backups', name: 'SystemBackups', component: () => import('@/views/system/backups.vue'), meta: { title: '备份管理' } },
      { path: 'system/logs', name: 'SystemLogs', component: () => import('@/views/system/logs.vue'), meta: { title: '操作日志' } },
      { path: 'system/api-keys', name: 'SystemApiKeys', component: () => import('@/views/system/api-keys.vue'), meta: { title: 'API密钥' } },

      // Scheduler
      { path: 'scheduler/tasks', name: 'SchedulerTasks', component: () => import('@/views/scheduler/tasks.vue'), meta: { title: '定时任务' } },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? to.meta.title + ' - ITOps' : 'ITOps Platform'
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
