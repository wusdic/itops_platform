import { defineStore } from 'pinia'
import { ref } from 'vue'
import { monitoring as monitoringApi, alerts as alertsApi } from '@/api'

export const useMonitoringStore = defineStore('monitoring', () => {
  const servers = ref([])
  const metrics = ref({})
  const loading = ref(false)
  const serverStats = ref({
    total: 0,
    online: 0,
    offline: 0,
    maintenance: 0
  })

  // 获取服务器列表
  const fetchServers = async (params = {}) => {
    loading.value = true
    try {
      const res = await monitoringApi.getServers(params)
      servers.value = res.items || res
      return servers.value
    } finally {
      loading.value = false
    }
  }

  // 获取监控指标
  const fetchMetrics = async (params = {}) => {
    loading.value = true
    try {
      const res = await monitoringApi.getMetrics(params)
      metrics.value = res
      return metrics.value
    } finally {
      loading.value = false
    }
  }

  // 获取服务器详情
  const fetchServerDetail = async (id) => {
    try {
      return await monitoringApi.getServerDetail(id)
    } catch (e) {
      console.error('Failed to fetch server detail:', e)
      return null
    }
  }

  // 获取历史指标
  const fetchMetricsHistory = async (params = {}) => {
    try {
      return await monitoringApi.getMetricsHistory(params)
    } catch (e) {
      console.error('Failed to fetch metrics history:', e)
      return []
    }
  }

  // 计算服务器统计数据
  const calculateServerStats = () => {
    const stats = {
      total: servers.value.length,
      online: 0,
      offline: 0,
      maintenance: 0
    }
    servers.value.forEach(server => {
      switch (server.status) {
        case 'online':
        case 'running':
          stats.online++
          break
        case 'offline':
        case 'down':
          stats.offline++
          break
        case 'maintenance':
          stats.maintenance++
          break
      }
    })
    serverStats.value = stats
    return stats
  }

  return {
    servers,
    metrics,
    loading,
    serverStats,
    fetchServers,
    fetchMetrics,
    fetchServerDetail,
    fetchMetricsHistory,
    calculateServerStats
  }
})

// 告警Store
export const useAlertsStore = defineStore('alerts', () => {
  const alerts = ref([])
  const loading = ref(false)
  const alertStats = ref({
    critical: 0,
    warning: 0,
    info: 0,
    total: 0
  })

  // 获取告警列表
  const fetchAlerts = async (params = {}) => {
    loading.value = true
    try {
      const res = await alertsApi.getAlerts(params)
      alerts.value = res.items || res
      return alerts.value
    } finally {
      loading.value = false
    }
  }

  // 获取告警统计
  const fetchAlertStats = async () => {
    try {
      const res = await alertsApi.getAlertStats()
      alertStats.value = res
      return res
    } catch (e) {
      console.error('Failed to fetch alert stats:', e)
      return null
    }
  }

  // 确认告警
  const acknowledgeAlert = async (id) => {
    try {
      await alertsApi.acknowledgeAlert(id)
      const alert = alerts.value.find(a => a.id === id)
      if (alert) {
        alert.status = 'acknowledged'
      }
      return true
    } catch (e) {
      console.error('Failed to acknowledge alert:', e)
      return false
    }
  }

  // 删除告警
  const deleteAlert = async (id) => {
    try {
      await alertsApi.deleteAlert(id)
      alerts.value = alerts.value.filter(a => a.id !== id)
      return true
    } catch (e) {
      console.error('Failed to delete alert:', e)
      return false
    }
  }

  return {
    alerts,
    loading,
    alertStats,
    fetchAlerts,
    fetchAlertStats,
    acknowledgeAlert,
    deleteAlert
  }
})
