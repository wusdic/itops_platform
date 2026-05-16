import api from './request'

export const downloadTemplate = () => api.get('/devices/import/template', { responseType: 'blob' })
export const validateImport = data => api.post('/devices/import/validate', data)
export const importDevices = data => api.post('/devices/import', data, { headers: { 'Content-Type': 'multipart/form-data' } })
export const importDevicesSimple = data => api.post('/devices/import/simple', data)
