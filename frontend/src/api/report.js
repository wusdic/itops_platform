import api from './request'

// Templates
export const getTemplates = params => api.get('/report/template', { params })
export const getTemplate = id => api.get(`/report/template/${id}`)
export const createTemplate = data => api.post('/report/template', data)
export const updateTemplate = (id, data) => api.put(`/report/template/${id}`, data)
export const deleteTemplate = id => api.delete(`/report/template/${id}`)

// Reports
export const getReports = params => api.get('/report/', { params })
export const getReportStats = () => api.get('/report/stats')
export const getReport = id => api.get(`/report/${id}`)
export const deleteReport = id => api.delete(`/report/${id}`)
export const downloadReport = id => api.get(`/report/${id}/download`, { responseType: 'blob' })
export const getReportFile = filename => api.get(`/report/files/${filename}`, { responseType: 'blob' })

// Generate
export const generateReport = data => api.post('/report/generate', data)
export const generateReportAsync = data => api.post('/report/generate/async', data)

// Schedules
export const getSchedules = params => api.get('/report/schedule', { params })
export const createSchedule = data => api.post('/report/schedule', data)
export const updateSchedule = (id, data) => api.put(`/report/schedule/${id}`, data)
export const deleteSchedule = id => api.delete(`/report/schedule/${id}`)
export const toggleSchedule = id => api.post(`/report/schedule/${id}/toggle`)
