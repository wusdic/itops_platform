import api from './request'

// Work orders
export const getWorkorders = params => api.get('/workorder/', { params })
export const createWorkorder = data => api.post('/workorder/', data)
export const getWorkorder = id => api.get(`/workorder/${id}`)
export const updateWorkorder = (id, data) => api.put(`/workorder/${id}`, data)
export const deleteWorkorder = id => api.delete(`/workorder/${id}`)
export const saveDraft = (id, data) => api.put(`/workorder/${id}/draft`, data)
export const listDrafts = params => api.get('/workorder/draft/list', { params })
export const getDraft = id => api.get(`/workorder/draft/${id}`)
export const deleteDraft = id => api.delete(`/workorder/draft/${id}`)
export const getWorkorderFlows = id => api.get(`/workorder/${id}/flows`)
export const createWorkorderFlow = (id, data) => api.post(`/workorder/${id}/flows`, data)
export const assignWorkorder = (id, data) => api.post(`/workorder/${id}/assign`, data)
export const approveWorkorder = (id, data) => api.post(`/workorder/${id}/approve`, data)
export const resolveWorkorder = (id, data) => api.post(`/workorder/${id}/resolve`, data)
export const closeWorkorder = (id, data) => api.post(`/workorder/${id}/close`, data)
export const cancelWorkorder = (id, data) => api.post(`/workorder/${id}/cancel`, data)
export const exportWorkorders = params => api.get('/workorder/export', { params, responseType: 'blob' })
export const exportSingleWorkorder = id => api.get(`/workorder/export/${id}`, { responseType: 'blob' })

// Categories & priorities
export const getWoCategories = () => api.get('/workorder/categories')
export const getWoPriorities = () => api.get('/workorder/priorities')

// Stats
export const getWoStats = () => api.get('/workorder/stats/summary')
export const getWoTrend = params => api.get('/workorder/stats/trend', { params })

// SLA
export const getWoSla = id => api.get(`/workorder/${id}/sla`)
export const refreshSla = id => api.post(`/workorder/${id}/sla/refresh`)
export const getSlaHistory = id => api.get(`/workorder/${id}/sla/history`)
export const startSlaTimer = id => api.post(`/workorder/${id}/sla/timer/start`)

// AI analysis
export const analyzeRootCause = data => api.post('/workorder/analyze/root-cause', data)
export const analyzeRemediation = data => api.post('/workorder/analyze/remediation', data)
