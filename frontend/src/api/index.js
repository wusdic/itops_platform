import request from './request'
import { devices, alerts, performance } from './monitoring'
import { auth, user, role, menu, dict, config, system } from './system'
import { assets } from './assets'
import { scheduler, reports } from './scheduler'
import { notification } from './notification'

export const workorder = {
  getList: (params) => request.get('/workorders/', { params }),
  getById: (id) => request.get(`/workorders/${id}`),
  create: (data) => request.post('/workorders/', data),
  update: (id, data) => request.put(`/workorders/${id}`, data),
  delete: (id) => request.delete(`/workorders/${id}`),
  assign: (id, data) => request.post(`/workorders/${id}/assign`, data),
  approve: (id, data) => request.post(`/workorders/${id}/approve`, data),
  getCategories: () => request.get('/workorders/categories'),
  getPriorities: () => request.get('/workorders/priorities'),
  getStatistics: () => request.get('/workorders/stats/summary'),
  getTrend: () => request.get('/workorders/stats/trend'),
  getFlows: (id) => request.get(`/workorders/${id}/flows`),
  addFlow: (id, data) => request.post(`/workorders/${id}/flows`, data),
  getDraftList: () => request.get('/workorders/draft/list'),
  getDraft: (id) => request.get(`/workorders/draft/${id}`),
  saveDraft: (data) => request.post('/workorders/draft/save', data),
  deleteDraft: (id) => request.delete(`/workorders/draft/${id}`),
  getSla: (id) => request.get(`/workorders/${id}/sla`),
  refreshSla: (id) => request.post(`/workorders/${id}/sla/refresh`),
  startSlaTimer: (id) => request.post(`/workorders/${id}/sla/timer/start`),
  analyzeRootCause: (id, data) => request.post(`/workorders/${id}/analyze/root-cause`, data),
  analyzeRemediation: (id, data) => request.post(`/workorders/${id}/analyze/remediation`, data)
}

export const knowledge = {
  search: (params) => request.get('/knowledge/search', { params }),
  // SOP文档
  getSopList: (params) => request.get('/knowledge/sop', { params }),
  getSop: (id) => request.get(`/knowledge/sop/${id}`),
  createSop: (data) => request.post('/knowledge/sop', data),
  updateSop: (id, data) => request.put(`/knowledge/sop/${id}`, data),
  deleteSop: (id) => request.delete(`/knowledge/sop/${id}`),
  submitSopReview: (id) => request.post(`/knowledge/sop/${id}/review`),
  approveSop: (id) => request.post(`/knowledge/sop/${id}/approve`),
  // 故障案例
  getFaultCaseList: (params) => request.get('/knowledge/fault-case', { params }),
  getFaultCase: (id) => request.get(`/knowledge/fault-case/${id}`),
  createFaultCase: (data) => request.post('/knowledge/fault-case', data),
  updateFaultCase: (id, data) => request.put(`/knowledge/fault-case/${id}`, data),
  deleteFaultCase: (id) => request.delete(`/knowledge/fault-case/${id}`),
  // 分类与标签
  getCategory: () => request.get('/knowledge/category'),
  createCategory: (data) => request.post('/knowledge/category', data),
  getTag: () => request.get('/knowledge/tag'),
  getStats: () => request.get('/knowledge/stats'),
  // 审核流程
  getReviewFlows: (params) => request.get('/knowledge/review-flows', { params }),
  createReviewFlow: (data) => request.post('/knowledge/review-flows', data),
  getReviewFlow: (id) => request.get(`/knowledge/review-flows/${id}`),
  updateReviewFlow: (id, data) => request.put(`/knowledge/review-flows/${id}`, data),
  deleteReviewFlow: (id) => request.delete(`/knowledge/review-flows/${id}`),
  // 审核记录
  submitReview: (data) => request.post('/knowledge/reviews/submit', data),
  getReviews: (params) => request.get('/knowledge/reviews', { params }),
  getReview: (id) => request.get(`/knowledge/reviews/${id}`),
  approveReview: (id) => request.post(`/knowledge/reviews/${id}/approve`),
  rejectReview: (id) => request.post(`/knowledge/reviews/${id}/reject`),
  requestRevision: (id, data) => request.post(`/knowledge/reviews/${id}/request-revision`, data),
  withdrawReview: (id) => request.post(`/knowledge/reviews/${id}/withdraw`),
  resubmitReview: (id) => request.post(`/knowledge/reviews/${id}/resubmit`),
  getPendingReviews: () => request.get('/knowledge/reviews/pending')
}

export const ai = {
  chat: (data) => request.post('/ai/chat', data),
  getConversations: (params) => request.get('/ai/conversations', { params }),
  getConversation: (id) => request.get(`/ai/conversation/${id}`),
  deleteConversation: (id) => request.delete(`/ai/conversation/${id}`),
  pinConversation: (id) => request.put(`/ai/conversation/${id}/pin`),
  saveMessage: (id, data) => request.post(`/ai/conversation/${id}/messages`, data),
  troubleshoot: (data) => request.post('/ai/troubleshoot', data),
  troubleshootAuto: (data) => request.post('/ai/troubleshoot/auto', data),
  suggest: (data) => request.post('/ai/suggest', data),
  interpretReport: (data) => request.post('/ai/interpret/report', data),
  analyzeLogs: (data) => request.post('/ai/analyze/logs', data),
  qa: (data) => request.post('/ai/qa', data),
  getStats: () => request.get('/ai/stats')
}

export const automation = {
  // 触发规则
  getTriggerRules: (params) => request.get('/automation/trigger-rules', { params }),
  createTriggerRule: (data) => request.post('/automation/trigger-rules', data),
  getTriggerRule: (id) => request.get(`/automation/trigger-rules/${id}`),
  updateTriggerRule: (id, data) => request.put(`/automation/trigger-rules/${id}`, data),
  deleteTriggerRule: (id) => request.delete(`/automation/trigger-rules/${id}`),
  testTriggerRule: (id) => request.post(`/automation/trigger-rules/${id}/test`),
  evaluateMetric: (data) => request.post('/automation/evaluate', data),
  // 执行相关
  rollbackExecution: (id) => request.post(`/automation/executions/${id}/rollback`),
  checkpointExecution: (id) => request.post(`/automation/executions/${id}/checkpoint`),
  getSnapshot: (id) => request.get(`/automation/executions/${id}/snapshot`),
  getRollbackHistory: () => request.get('/automation/rollback-history')
}

export const backup = {
  getList: (params) => request.get('/admin/backup', { params }),
  create: (data) => request.post('/admin/backup', data),
  restore: (id, data) => request.post(`/admin/backup/${id}/restore`, data)
}

export { devices, alerts, performance, auth, user, role, menu, dict, config, system, assets, scheduler, reports, notification }
