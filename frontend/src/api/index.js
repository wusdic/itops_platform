import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  async error => {
    const { response } = error
    const status = response?.status
    const message = response?.data?.message || error.message
    
    console.error('API Error:', status, message)
    
    // 处理不同状态码
    switch (status) {
      case 401:
        ElMessageBox.confirm('登录已过期，请重新登录', '提示', {
          confirmButtonText: '重新登录',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          localStorage.removeItem('token')
          localStorage.removeItem('userInfo')
          window.location.href = '/login'
        }).catch(() => {})
        break
      case 403:
        ElMessage.error('没有权限执行此操作')
        break
      case 404:
        ElMessage.error('请求的资源不存在')
        break
      case 422:
        ElMessage.error(response?.data?.detail || '数据验证失败')
        break
      case 500:
        ElMessage.error('服务器内部错误')
        break
      default:
        ElMessage.error(message || '请求失败')
    }
    
    return Promise.reject(error.response?.data || error)
  }
)

// ========== 认证相关 ==========
export const auth = {
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  register: (data) => api.post('/auth/register', data),
  getUserInfo: () => api.get('/auth/userinfo'),
  refreshToken: () => api.post('/auth/refresh')
}

// ========== 监控相关 ==========
export const monitoring = {
  getMetrics: () => api.get('/monitoring/metrics'),
  getServers: () => api.get('/monitoring/servers'),
  getServerDetail: (id) => api.get(`/monitoring/servers/${id}`),
  getMetricsHistory: (params) => api.get('/monitoring/metrics/history', { params })
}

// ========== 告警相关 ==========
export const alerts = {
  getAlerts: (params) => api.get('/monitoring/alerts', { params }),
  getAlertDetail: (id) => api.get(`/monitoring/alerts/${id}`),
  updateAlert: (id, data) => api.put(`/monitoring/alerts/${id}`, data),
  acknowledgeAlert: (id) => api.post(`/monitoring/alerts/${id}/acknowledge`),
  deleteAlert: (id) => api.delete(`/monitoring/alerts/${id}`),
  getAlertStats: () => api.get('/monitoring/alerts/stats')
}

// ========== 工单相关 ==========
export const workorder = {
  getWorkOrders: (params) => api.get('/workorders/', { params }),
  getWorkOrderDetail: (id) => api.get(`/workorders/${id}`),
  createWorkOrder: (data) => api.post('/workorders/', data),
  updateWorkOrder: (id, data) => api.put(`/workorders/${id}`, data),
  deleteWorkOrder: (id) => api.delete(`/workorders/${id}`),
  approveWorkOrder: (id, data) => api.post(`/workorders/${id}/approve`, data),
  rejectWorkOrder: (id, data) => api.post(`/workorders/${id}/reject`, data),
  getWorkOrderStats: () => api.get('/workorders/stats/summary')
}

// ========== 知识库相关 ==========
export const knowledge = {
  getArticles: (params) => api.get('/knowledge', { params }),
  getArticle: (id) => api.get(`/knowledge/${id}`),
  createArticle: (data) => api.post('/knowledge', data),
  updateArticle: (id, data) => api.put(`/knowledge/${id}`, data),
  deleteArticle: (id) => api.delete(`/knowledge/${id}`),
  getCategories: () => api.get('/knowledge/categories'),
  searchArticles: (params) => api.get('/knowledge/search', { params })
}

// ========== 报告相关 ==========
export const reports = {
  getReports: (params) => api.get('/report/', { params }),
  getReportDetail: (id) => api.get(`/report/${id}`),
  generateReport: (data) => api.post('/report/generate/generate', data),
  deleteReport: (id) => api.delete(`/report/${id}`),
  downloadReport: (id, format) => api.get(`/report/${id}/download?format=${format}`, { responseType: 'blob' }),
  getReportTemplates: () => api.get('/report/templates/'),
  createReportTemplate: (data) => api.post('/report/templates/', data),
  updateReportTemplate: (id, data) => api.put(`/report/templates/${id}`, data),
  deleteReportTemplate: (id) => api.delete(`/report/templates/${id}`)
}

// ========== 资产相关 ==========
export const assets = {
  getAssets: (params) => api.get('/assets', { params }),
  getAssetDetail: (id) => api.get(`/assets/${id}`),
  createAsset: (data) => api.post('/assets', data),
  updateAsset: (id, data) => api.put(`/assets/${id}`, data),
  deleteAsset: (id) => api.delete(`/assets/${id}`),
  importAssets: (formData) => api.post('/assets/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  exportAssets: (params) => api.get('/assets/export', { params, responseType: 'blob' }),
  getAssetStats: () => api.get('/assets/stats')
}

// ========== 通知渠道相关 ==========
export const notifications = {
  getChannels: () => api.get('/notifications'),
  getChannelDetail: (id) => api.get(`/notifications/${id}`),
  createChannel: (data) => api.post('/notifications', data),
  updateChannel: (id, data) => api.put(`/notifications/${id}`, data),
  deleteChannel: (id) => api.delete(`/notifications/${id}`),
  testChannel: (id) => api.post(`/notifications/${id}/test`),
  toggleChannel: (id, enabled) => api.patch(`/notifications/${id}`, { enabled })
}

// ========== 任务调度相关 ==========
export const scheduler = {
  getTasks: (params) => api.get('/scheduler/tasks', { params }),
  getTaskDetail: (id) => api.get(`/scheduler/tasks/${id}`),
  createTask: (data) => api.post('/scheduler/tasks', data),
  updateTask: (id, data) => api.put(`/scheduler/tasks/${id}`, data),
  deleteTask: (id) => api.delete(`/scheduler/tasks/${id}`),
  runTask: (id) => api.post(`/scheduler/tasks/${id}/run`),
  pauseTask: (id) => api.post(`/scheduler/tasks/${id}/pause`),
  resumeTask: (id) => api.post(`/scheduler/tasks/${id}/resume`),
  getTaskLogs: (id, params) => api.get(`/scheduler/tasks/${id}/logs`, { params })
}

// ========== RAG知识库相关 ==========
export const rag = {
  getDocuments: (params) => api.get('/rag/documents', { params }),
  getDocumentDetail: (id) => api.get(`/rag/documents/${id}`),
  uploadDocument: (formData) => api.post('/rag/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  deleteDocument: (id) => api.delete(`/rag/documents/${id}`),
  searchKnowledge: (query) => api.post('/rag/search', { query }),
  ragChat: (data) => api.post('/rag/chat', data)
}

// ========== AI助手相关 ==========
export const ai = {
  chat: (data) => api.post('/ai/chat', data),
  getHistory: (params) => api.get('/ai/conversations', { params }),
  clearHistory: () => api.delete('/ai/conversation/{conversation_id}')
}

// ========== 系统设置相关 ==========
export const settings = {
  getSettings: () => api.get('/settings'),
  updateSettings: (data) => api.put('/settings', data),
  getSystemInfo: () => api.get('/settings/system'),
  getLogs: (params) => api.get('/settings/logs', { params })
}

// 默认导出（兼容旧用法）
export default api
