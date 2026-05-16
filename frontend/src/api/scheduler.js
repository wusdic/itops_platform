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
