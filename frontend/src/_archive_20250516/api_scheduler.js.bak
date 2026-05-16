import request from './request'

// 巡检任务 - 使用 inspection 路由
export const scheduler = {
  getList: (params) => request.get('/inspection/tasks', { params }),
  getById: (id) => request.get(`/inspection/tasks/${id}`),
  create: (data) => request.post('/inspection/tasks', data),
  update: (id, data) => request.put(`/inspection/tasks/${id}`, data),
  delete: (id) => request.delete(`/inspection/tasks/${id}`),
  getReports: (taskId) => request.get(`/inspection/reports/${taskId}`),
  exportReport: (taskId) => request.get(`/inspection/reports/${taskId}/export`),
  getReportTemplate: () => request.get('/inspection/reports/template'),
  getResults: (taskId) => request.get(`/inspection/results/${taskId}`),
  getStatistics: () => request.get('/inspection/statistics/summary')
}

// 报表管理 - 使用 report 路由
export const reports = {
  getList: (params) => request.get('/report/', { params }),
  getById: (id) => request.get(`/report/${id}`),
  create: (data) => request.post('/report/generate', data),
  update: (id, data) => request.put(`/report/template/${id}`, data),
  delete: (id) => request.delete(`/report/${id}`),
  download: (id) => request.get(`/report/${id}/download`),
  // 报表模板
  getTemplates: () => request.get('/report/template'),
  getTemplate: (id) => request.get(`/report/template/${id}`),
  createTemplate: (data) => request.post('/report/template', data),
  updateTemplate: (id, data) => request.put(`/report/template/${id}`, data),
  deleteTemplate: (id) => request.delete(`/report/template/${id}`),
  // 定时报表
  getSchedules: () => request.get('/report/schedule'),
  createSchedule: (data) => request.post('/report/schedule', data),
  updateSchedule: (id, data) => request.put(`/report/schedule/${id}`, data),
  deleteSchedule: (id) => request.delete(`/report/schedule/${id}`),
  toggleSchedule: (id) => request.post(`/report/schedule/${id}/toggle`),
  // 统计
  getStats: () => request.get('/report/stats'),
  // 报表文件
  getFile: (filename) => request.get(`/report/files/${filename}`)
}
