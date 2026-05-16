import request from './request'

export const assets = {
  // 设备管理 - 使用 /assets/device 路由
  getList: (params) => request.get('/assets/device', { params }),
  getById: (id) => request.get(`/assets/device/${id}`),
  create: (data) => request.post('/assets/device', data),
  update: (id, data) => request.put(`/assets/device/${id}`, data),
  delete: (id) => request.delete(`/assets/device/${id}`),
  setMaintain: (id) => request.post(`/assets/device/${id}/maintain`),
  decommission: (id) => request.post(`/assets/device/${id}/decommission`),
  getStats: () => request.get('/assets/stats'),

  // 设备分组
  getGroups: () => request.get('/assets/group'),
  getGroupDevices: (id) => request.get(`/assets/group/${id}/devices`),

  // 业务系统
  getBusiness: () => request.get('/assets/business'),
  getBusinessDevices: (id) => request.get(`/assets/business/${id}/devices`),

  // 配置管理
  getConfigs: () => request.get('/assets/config'),
  createConfigSnapshot: (data) => request.post('/assets/config/snapshot', data),
  updateConfig: (id, data) => request.put(`/assets/config/${id}`, data),
  deleteConfig: (id) => request.delete(`/assets/config/${id}`),
  syncConfig: (deviceId) => request.post(`/assets/config/sync/${deviceId}`),

  // 设备导入导出 - 使用 /devices/import 路由
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
