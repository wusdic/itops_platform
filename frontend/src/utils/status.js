export const getSeverityType = (severity) => {
  const map = {
    critical: 'danger',
    high: 'warning',
    medium: 'warning',
    low: 'info'
  }
  return map[severity] || 'info'
}

export const getSeverityText = (severity) => {
  const map = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[severity] || severity
}

export const getStatusType = (status) => {
  const map = {
    online: 'success',
    offline: 'info',
    warning: 'warning',
    error: 'danger'
  }
  return map[status] || 'info'
}

export const getStatusText = (status) => {
  const map = {
    online: '在线',
    offline: '离线',
    warning: '告警',
    error: '异常'
  }
  return map[status] || status
}

export const getPriorityType = (priority) => {
  const map = {
    urgent: 'danger',
    high: 'warning',
    medium: 'info',
    low: 'info'
  }
  return map[priority] || ''
}

export const getPriorityText = (priority) => {
  const map = {
    urgent: '紧急',
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[priority] || priority
}

export const getWorkOrderStatusType = (status) => {
  const map = {
    pending: 'warning',
    processing: 'primary',
    completed: 'success',
    closed: 'info'
  }
  return map[status] || 'info'
}

export const getWorkOrderStatusText = (status) => {
  const map = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    closed: '已关闭'
  }
  return map[status] || status
}
