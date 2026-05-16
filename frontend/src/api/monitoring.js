import request from './request'

export const devices = {
  getList: (params) => request.get('/assets/device', { params }),
  getById: (id) => request.get(`/assets/device/${id}`),
  create: (data) => request.post('/assets/device', data),
  update: (id, data) => request.put(`/assets/device/${id}`, data),
  delete: (id) => request.delete(`/assets/device/${id}`),
  getMetrics: (name) => request.get(`/devices/${name}/metrics`),
  getStatus: (name) => request.get(`/devices/${name}/status`),
  collect: (data) => request.post('/devices/collect', data),
  collectAll: () => request.post('/devices/collect/all'),
  getStats: () => request.get('/devices/stats'),
  getStatus: () => request.get('/assets/stats'),
  batchOperate: (ids, action) => request.post('/assets/device/batch', { ids, action }),
  // 批量导入相关 - 使用 /devices/import 路由
  getImportTemplate: (format = 'xlsx') => request.get('/devices/import/template', { params: { format }, responseType: 'blob' }),
  validateImport: (rows) => request.post('/devices/import/validate', rows),
  importDevices: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/devices/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  importDevicesSimple: (rows) => request.post('/devices/import/simple', rows)
}

export const alerts = {
  getList: (params) => request.get('/monitoring/alerts', { params }),
  getById: (id) => request.get(`/monitoring/alerts/${id}`),
  create: (data) => request.post('/monitoring/alerts', data),
  update: (id, data) => request.put(`/monitoring/alerts/${id}`, data),
  delete: (id) => request.delete(`/monitoring/alerts/${id}`),
  acknowledge: (id, data) => request.put(`/monitoring/alerts/${id}/acknowledge`, data),
  resolve: (id, data) => request.put(`/monitoring/alerts/${id}/resolve`, data),
  getAuditLogs: (id) => request.get(`/monitoring/alerts/${id}/audit-logs`),
  createAuditLog: (id, data) => request.post(`/monitoring/alerts/${id}/audit-logs`, data),
  getRules: () => request.get('/monitoring/rules'),
  getRule: (id) => request.get(`/monitoring/rules/${id}`)
}

export const performance = {
  getMetrics: (params) => request.get('/monitoring/metrics', { params }),
  collect: (data) => request.post('/monitoring/metrics/collect', data),
  getHosts: () => request.get('/monitoring/metrics/hosts'),
  getAvailable: () => request.get('/monitoring/metrics/available'),
  query: (data) => request.post('/monitoring/metrics/query', data),
  // 触发规则
  getTriggerRules: (params) => request.get('/monitoring/trigger-rules', { params }),
  createTriggerRule: (data) => request.post('/monitoring/trigger-rules', data),
  getTriggerRule: (id) => request.get(`/monitoring/trigger-rules/${id}`),
  updateTriggerRule: (id, data) => request.put(`/monitoring/trigger-rules/${id}`, data),
  deleteTriggerRule: (id) => request.delete(`/monitoring/trigger-rules/${id}`),
  testTriggerRule: (id) => request.post(`/monitoring/trigger-rules/${id}/test`),
  getTriggerEvents: () => request.get('/monitoring/trigger-events'),
  evaluateTrigger: (data) => request.post('/monitoring/trigger/evaluate', data),
  // 仪表盘
  getDashboards: () => request.get('/monitoring/dashboards'),
  getDashboard: (id) => request.get(`/monitoring/dashboards/${id}`),
  // 采集项配置
  getMetricConfigs: (params) => request.get('/monitoring/metric-configs', { params }),
  getMetricConfig: (id) => request.get(`/monitoring/metric-configs/${id}`),
  createMetricConfig: (data) => request.post('/monitoring/metric-configs', data),
  updateMetricConfig: (id, data) => request.patch(`/monitoring/metric-configs/${id}`, data)
}
