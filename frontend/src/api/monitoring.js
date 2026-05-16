import api from './request'

// Metrics
export const queryMetrics = params => api.get('/monitoring/metrics', { params })
export const collectMetrics = data => api.post('/monitoring/metrics/collect', data)
export const getMonitoredHosts = params => api.get('/monitoring/metrics/hosts', { params })
export const getAvailableMetrics = () => api.get('/monitoring/metrics/available')
export const promqlQuery = data => api.post('/monitoring/metrics/query', data)

// Alerts
export const getAlerts = params => api.get('/monitoring/alerts', { params })
export const createAlert = data => api.post('/monitoring/alerts', data)
export const getAlert = id => api.get(`/monitoring/alerts/${id}`)
export const acknowledgeAlert = id => api.put(`/monitoring/alerts/${id}/acknowledge`)
export const resolveAlert = id => api.put(`/monitoring/alerts/${id}/resolve`)
export const deleteAlert = id => api.delete(`/monitoring/alerts/${id}`)
export const getAlertAuditLogs = id => api.get(`/monitoring/alerts/${id}/audit-logs`)
export const createAlertAuditLog = (id, data) => api.post(`/monitoring/alerts/${id}/audit-logs`, data)
export const getAuditLogs = params => api.get('/monitoring/audit-logs', { params })

// Rules
export const getAlertRules = params => api.get('/monitoring/rules', { params })
export const getAlertRule = id => api.get(`/monitoring/rules/${id}`)

// Dashboards
export const getDashboards = params => api.get('/monitoring/dashboards', { params })
export const getDashboard = id => api.get(`/monitoring/dashboards/${id}`)
export const getDashboardLayout = () => api.get('/monitoring/dashboard/layout')
export const saveDashboardLayout = data => api.put('/monitoring/dashboard/layout', data)
export const listDashboardLayouts = () => api.get('/monitoring/dashboard/layouts')
export const deleteDashboardLayout = id => api.delete(`/monitoring/dashboard/layout/${id}`)
export const createLayoutSnapshot = data => api.post('/monitoring/dashboard/layout/snapshot', data)
export const getLayoutSnapshot = (layoutId, version) => api.get(`/monitoring/dashboard/layout/snapshot/${layoutId}/${version}`)
export const getDashboardColumns = () => api.get('/monitoring/dashboard/columns')

// Trigger rules
export const getTriggerRules = params => api.get('/monitoring/trigger-rules', { params })
export const createTriggerRule = data => api.post('/monitoring/trigger-rules', data)
export const getTriggerRule = id => api.get(`/monitoring/trigger-rules/${id}`)
export const updateTriggerRule = (id, data) => api.put(`/monitoring/trigger-rules/${id}`, data)
export const deleteTriggerRule = id => api.delete(`/monitoring/trigger-rules/${id}`)
export const testTriggerRule = (id, data) => api.post(`/monitoring/trigger-rules/${id}/test`, data)
export const getTriggerEvents = params => api.get('/monitoring/trigger-events', { params })
export const evaluateTrigger = data => api.post('/monitoring/trigger/evaluate', data)

// Metric configs
export const getMetricConfigs = params => api.get('/monitoring/metric-configs', { params })
export const getMetricConfig = id => api.get(`/monitoring/metric-configs/${id}`)
export const createMetricConfig = data => api.post('/monitoring/metric-configs', data)
export const updateMetricConfig = (id, data) => api.patch(`/monitoring/metric-configs/${id}`, data)
export const toggleMetricConfig = id => api.patch(`/monitoring/metric-configs/${id}/toggle`)
export const deleteMetricConfig = id => api.delete(`/monitoring/metric-configs/${id}`)
export const getDeviceMetricConfigs = id => api.get(`/monitoring/metric-configs/device/${id}`)
