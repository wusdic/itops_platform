import api from './request'

// Users
export const getUsers = params => api.get('/admin/users', { params })
export const createUser = data => api.post('/admin/users', data)
export const getUser = id => api.get(`/admin/users/${id}`)
export const updateUser = (id, data) => api.put(`/admin/users/${id}`, data)
export const deleteUser = id => api.delete(`/admin/users/${id}`)
export const resetPassword = (id, data) => api.post(`/admin/users/${id}/reset-password`, data)

// Roles
export const getRoles = params => api.get('/admin/roles', { params })
export const createRole = data => api.post('/admin/roles', data)
export const updateRole = (id, data) => api.put(`/admin/roles/${id}`, data)
export const deleteRole = id => api.delete(`/admin/roles/${id}`)
export const getPermissions = () => api.get('/admin/permissions')

// System config
export const getSystemConfig = () => api.get('/admin/config')
export const updateSystemConfig = (key, data) => api.put(`/admin/config/${key}`, data)
export const getSystemInfo = () => api.get('/admin/info')
export const getSystemMetrics = () => api.get('/admin/metrics')

// Logs
export const getOperationLogs = params => api.get('/admin/logs', { params })

// Backups
export const getBackups = params => api.get('/admin/backups', { params })
export const createBackup = data => api.post('/admin/backups', data)
export const getBackup = id => api.get(`/admin/backups/${id}`)
export const deleteBackup = id => api.delete(`/admin/backups/${id}`)
export const restoreBackup = (id, data) => api.post(`/admin/backups/${id}/restore`, data)
export const getRestores = params => api.get('/admin/restores', { params })
export const getRestore = id => api.get(`/admin/restores/${id}`)
export const cleanupBackups = () => api.post('/admin/backups/cleanup')
export const getBackupConfig = () => api.get('/admin/backup/config')

// Cache & Health
export const clearCache = () => api.post('/admin/cache/clear')
export const systemHealthCheck = () => api.get('/admin/health')

// API Keys
export const getApiKeys = params => api.get('/admin/api-keys', { params })
export const createApiKey = data => api.post('/admin/api-keys', data)
export const getApiKey = id => api.get(`/admin/api-keys/${id}`)
export const updateApiKey = (id, data) => api.put(`/admin/api-keys/${id}`, data)
export const deleteApiKey = id => api.delete(`/admin/api-keys/${id}`)
export const revokeApiKey = id => api.post(`/admin/api-keys/${id}/revoke`)
export const activateApiKey = id => api.post(`/admin/api-keys/${id}/activate`)
export const rotateApiKey = id => api.post(`/admin/api-keys/${id}/rotate`)
