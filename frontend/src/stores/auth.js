import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const userInfo = ref(null)
  const permissions = ref([])
  const roles = ref([])

  const isAdmin = computed(() => roles.value.includes('admin'))
  const isOperator = computed(() => roles.value.includes('operator'))

  const hasPermission = (permission) => {
    return permissions.value.includes(permission) || isAdmin.value
  }

  const setUserInfo = (info) => {
    userInfo.value = info
    roles.value = info?.roles || []
    permissions.value = info?.permissions || []
  }

  const token = computed(() => localStorage.getItem('token') || '')

  const clearAuth = () => {
    userInfo.value = null
    roles.value = []
    permissions.value = []
  }

  return {
    userInfo,
    permissions,
    roles,
    isAdmin,
    isOperator,
    hasPermission,
    setUserInfo,
    clearAuth,
    token
  }
})
