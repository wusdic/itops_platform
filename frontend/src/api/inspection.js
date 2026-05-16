import api from './request'

export const getInspectionTasks = params => api.get('/inspection/tasks', { params })
export const getInspectionTask = id => api.get(`/inspection/tasks/${id}`)
export const createInspectionTask = data => api.post('/inspection/tasks', data)
export const getInspectionReport = taskId => api.get(`/inspection/reports/${taskId}`)
export const exportInspectionReport = taskId => api.get(`/inspection/reports/${taskId}/export`, { responseType: 'blob' })
export const getReportTemplate = () => api.get('/inspection/reports/template')
export const getInspectionResults = taskId => api.get(`/inspection/results/${taskId}`)
export const getInspectionSummary = () => api.get('/inspection/statistics/summary')
