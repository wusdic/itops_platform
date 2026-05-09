<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card" v-for="stat in stats" :key="stat.title">
        <div class="stat-icon" :style="{ background: stat.bg }">
          <el-icon :size="24" :color="stat.color">
            <component :is="stat.icon" />
          </el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stat.value }}</span>
          <span class="stat-title">{{ stat.title }}</span>
        </div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="dashboard-content">
      <!-- 左侧列表 -->
      <div class="dashboard-left">
        <!-- 设备状态 -->
        <div class="card">
          <div class="card-header">
            <span>设备状态</span>
          </div>
          <div class="card-body">
            <div class="device-status">
              <div class="status-item">
                <span class="status-dot online"></span>
                <span class="status-label">在线</span>
                <span class="status-count">{{ deviceStats.online }}</span>
              </div>
              <div class="status-item">
                <span class="status-dot offline"></span>
                <span class="status-label">离线</span>
                <span class="status-count">{{ deviceStats.offline }}</span>
              </div>
              <div class="status-item">
                <span class="status-dot warning"></span>
                <span class="status-label">告警</span>
                <span class="status-count">{{ deviceStats.warning }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 最近告警 -->
        <div class="card">
          <div class="card-header">
            <span>最近告警</span>
            <el-button type="primary" link @click="$router.push('/alerts')">查看更多</el-button>
          </div>
          <div class="card-body">
            <div class="alert-list">
              <div v-if="recentAlerts.length === 0" class="empty-tip">暂无告警</div>
              <div v-for="alert in recentAlerts" :key="alert.id" class="alert-item">
                <span class="alert-severity" :class="alert.severity">{{ alert.severity_text }}</span>
                <span class="alert-message">{{ alert.message || alert.title }}</span>
                <span class="alert-time">{{ formatTime(alert.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧列表 -->
      <div class="dashboard-right">
        <!-- 待处理工单 -->
        <div class="card">
          <div class="card-header">
            <span>待处理工单</span>
            <el-button type="primary" link @click="$router.push('/workorder')">查看更多</el-button>
          </div>
          <div class="card-body">
            <div class="workorder-list">
              <div v-if="pendingOrders.length === 0" class="empty-tip">暂无待处理工单</div>
              <div v-for="order in pendingOrders" :key="order.id" class="workorder-item">
                <span class="order-priority" :class="order.priority">{{ order.priority_text }}</span>
                <span class="order-title">{{ order.title }}</span>
                <span class="order-time">{{ formatTime(order.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 系统状态 -->
        <div class="card">
          <div class="card-header">
            <span>系统状态</span>
          </div>
          <div class="card-body">
            <div class="system-status">
              <div class="status-row">
                <span>CPU使用率</span>
                <el-progress :percentage="systemStatus.cpu" :color="getProgressColor(systemStatus.cpu)" />
              </div>
              <div class="status-row">
                <span>内存使用率</span>
                <el-progress :percentage="systemStatus.memory" :color="getProgressColor(systemStatus.memory)" />
              </div>
              <div class="status-row">
                <span>磁盘使用率</span>
                <el-progress :percentage="systemStatus.disk" :color="getProgressColor(systemStatus.disk)" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Bell, Tickets, Warning } from '@element-plus/icons-vue'
import { devices, alerts, workorder } from '@/api'

const stats = reactive([
  { title: '设备总数', value: 0, icon: Monitor, color: '#165dff', bg: '#e8f0ff' },
  { title: '在线设备', value: 0, icon: Monitor, color: '#00b42a', bg: '#e8ffea' },
  { title: '告警数量', value: 0, icon: Bell, color: '#ff7d00', bg: '#fff7e6' },
  { title: '待办工单', value: 0, icon: Tickets, color: '#f53f3f', bg: '#fff1f0' },
])

const deviceStats = reactive({ online: 0, offline: 0, warning: 0 })
const recentAlerts = ref([])
const pendingOrders = ref([])
const systemStatus = reactive({ cpu: 45, memory: 62, disk: 38 })

onMounted(async () => {
  await Promise.all([loadDashboard()])
})

const loadDashboard = async () => {
  try {
    // 加载设备统计
    const deviceRes = await devices.getDevices({ page: 1, page_size: 100 })
    const deviceList = deviceRes.items || deviceRes.data?.items || []
    stats[0].value = deviceRes.total || deviceRes.data?.total || 0
    deviceStats.online = deviceList.filter(d => d.status === 'online').length
    deviceStats.offline = deviceList.filter(d => d.status === 'offline').length
    stats[1].value = deviceStats.online

    // 加载告警
    const alertRes = await alerts.getAlerts({ page: 1, page_size: 5 })
    recentAlerts.value = (alertRes.items || alertRes.data?.items || []).map(a => ({
      ...a,
      severity_text: { critical: '严重', high: '高', medium: '中', low: '低' }[a.severity] || a.severity
    }))
    stats[2].value = alertRes.total || 0

    // 加载工单
    const orderRes = await workorder.getWorkOrders({ page: 1, page_size: 5, status: 'pending' })
    pendingOrders.value = (orderRes.items || orderRes.data?.items || []).map(o => ({
      ...o,
      priority_text: { high: '高', medium: '中', low: '低' }[o.priority] || o.priority
    }))
    stats[3].value = orderRes.total || 0

  } catch (error) {
    console.error('Dashboard load error:', error)
  }
}

const formatTime = (time) => {
  if (!time) return ''
  const d = new Date(time)
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const getProgressColor = (value) => {
  if (value >= 90) return '#f53f3f'
  if (value >= 70) return '#ff7d00'
  return '#00b42a'
}
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1;
}

.stat-title {
  font-size: 14px;
  color: #86909c;
  margin-top: 4px;
}

.dashboard-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.dashboard-left, .dashboard-right {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f2f3f5;
  font-size: 16px;
  font-weight: 500;
  color: #1d2129;
}

.card-body {
  padding: 16px 20px;
}

.device-status {
  display: flex;
  gap: 24px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  &.online { background: #00b42a; }
  &.offline { background: #86909c; }
  &.warning { background: #ff7d00; }
}

.status-label {
  font-size: 14px;
  color: #4b4f59;
}

.status-count {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}

.alert-list, .workorder-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-item, .workorder-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f7f8fa;
  &:last-child { border-bottom: none; }
}

.alert-severity, .order-priority {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  &.critical, &.high { background: #fff1f0; color: #f53f3f; }
  &.high, &.medium { background: #fff7e6; color: #ff7d00; }
  &.medium, &.low { background: #e8f0ff; color: #165dff; }
  &.low { background: #f7f8fa; color: #86909c; }
}

.alert-message, .order-title {
  flex: 1;
  font-size: 14px;
  color: #4b4f59;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alert-time, .order-time {
  font-size: 12px;
  color: #c9cdd4;
}

.system-status {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 16px;
  span {
    width: 80px;
    font-size: 14px;
    color: #4b4f59;
  }
  :deep(.el-progress) {
    flex: 1;
  }
}

.empty-tip {
  text-align: center;
  color: #c9cdd4;
  padding: 20px 0;
}
</style>
