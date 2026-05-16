import api from './request'

export const listTriggerRules = params => api.get('/automation/trigger-rules', { params })
export const createTriggerRule = data => api.post('/automation/trigger-rules', data)
export const getTriggerRule = id => api.get(`/automation/trigger-rules/${id}`)
export const updateTriggerRule = (id, data) => api.put(`/automation/trigger-rules/${id}`, data)
export const deleteTriggerRule = id => api.delete(`/automation/trigger-rules/${id}`)
export const testTriggerRule = id => api.post(`/automation/trigger-rules/${id}/test`)
export const evaluateMetric = data => api.post('/automation/evaluate', data)
export const executeRollback = id => api.post(`/automation/executions/${id}/rollback`)
export const saveCheckpoint = (id, data) => api.post(`/automation/executions/${id}/checkpoint`, data)
export const getSnapshot = id => api.get(`/automation/executions/${id}/snapshot`)
export const getRollbackHistory = params => api.get('/automation/rollback-history', { params })
