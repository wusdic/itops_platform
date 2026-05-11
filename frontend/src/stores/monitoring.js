import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMonitoringStore = defineStore('monitoring', () => {
  const devices = ref([])
  const alerts = ref([])
  const metrics = ref({
    cpu: 0,
    memory: 0,
    disk: 0,
    network: 0
  })

  const setDevices = (list) => {
    devices.value = list
  }

  const setAlerts = (list) => {
    alerts.value = list
  }

  const setMetrics = (data) => {
    metrics.value = data
  }

  const addAlert = (alert) => {
    alerts.value.unshift(alert)
  }

  const removeAlert = (id) => {
    const index = alerts.value.findIndex(a => a.id === id)
    if (index > -1) {
      alerts.value.splice(index, 1)
    }
  }

  const updateDeviceStatus = (deviceId, status) => {
    const device = devices.value.find(d => d.id === deviceId)
    if (device) {
      device.status = status
    }
  }

  return {
    devices,
    alerts,
    metrics,
    setDevices,
    setAlerts,
    setMetrics,
    addAlert,
    removeAlert,
    updateDeviceStatus
  }
})
