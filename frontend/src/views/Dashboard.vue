<template>
  <div class="dashboard">
    <!-- 欢迎栏 -->
    <div class="welcome-bar">
      <div class="welcome-content">
        <h2 class="welcome-title">
          <span class="greeting-icon">👋</span>
          {{ greeting }}，管理员
        </h2>
        <p class="welcome-desc">
          今天是 {{ currentDate }}，您有 
          <span class="alert-count" v-if="alertStats.pending > 0">{{ alertStats.pending }} 条</span>
          <span class="alert-count safe" v-else>0 条</span>
          待处理告警
        </p>
      </div>
      <div class="welcome-actions">
        <el-button type="primary" @click="handleQuickAction">
          <el-icon><Plus /></el-icon>
          快捷操作
        </el-button>
      </div>
    </div>

    <!-- 统计卡片区 -->
    <div class="stats-grid">
      <div
        v-for="(stat, index) in stats"
        :key="stat.title"
        class="stat-card"
        :style="{ animationDelay: `${index * 0.1}s` }"
        @click="handleStatClick(stat)"
      >
        <div class="stat-icon" :style="{ background: stat.color }">
          <el-icon><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-title">{{ stat.title }}</div>
          <div class="stat-desc">{{ stat.description }}</div>
        </div>
        <div class="stat-trend" :class="stat.trend > 0 ? 'up' : 'down'" v-if="stat.trend !== undefined">
          <el-icon><component :is="stat.trend > 0 ? 'Top' : 'Bottom'" /></el-icon>
          {{ Math.abs(stat.trend) }}%
        </div>
        <div class="stat-accent" :style="{ background: stat.color }"></div>
      </div>
    </div>

    <!-- 主要内容区 -->
    <el-row :gutter="20" class="main-content">
      <!-- 左侧图表区 -->
      <el-col :span="16">
        <!-- 服务器状态 -->
        <PageCard title="设备状态分布" subtitle="实时监控设备运行状态" :icon="'Odometer'" icon-bg="rgba(22, 93, 255, 0.1)">
          <template #header>
            <el-select v-model="serverTimeRange" size="small" @change="loadServerData">
              <el-option label="实时" value="realtime" />
              <el-option label="24小时" value="24h" />
              <el-option label="7天" value="7d" />
            </el-select>
          </template>
          <div class="chart-wrapper">
            <div ref="serverChartRef" class="chart-container"></div>
            <div class="chart-legend">
              <div class="legend-item" v-for="item in serverLegend" :key="item.name">
                <span class="legend-dot" :style="{ background: item.color }"></span>
                <span class="legend-label">{{ item.name }}</span>
                <span class="legend-value">{{ item.value }}</span>
              </div>
            </div>
          </div>
        </PageCard>

        <!-- 告警趋势 -->
        <PageCard title="告警趋势" subtitle="近7天告警统计" :icon="'DataLine'" icon-bg="rgba(255, 125, 0, 0.1)">
          <template #header>
            <el-radio-group v-model="alertTimeRange" size="small" @change="loadAlertTrend">
              <el-radio-button label="7d">近7天</el-radio-button>
              <el-radio-button label="30d">近30天</el-radio-button>
            </el-radio-group>
          </template>
          <div ref="alertChartRef" class="chart-container" style="height: 280px"></div>
        </PageCard>

        <!-- 资源使用率 -->
        <PageCard title="资源使用率" subtitle="CPU/内存/磁盘实时状态" :icon="'Monitor'" icon-bg="rgba(0, 180, 42, 0.1)">
          <div class="resource-list">
            <div class="resource-item" v-for="item in resourceItems" :key="item.name">
              <div class="resource-header">
                <span class="resource-name">{{ item.name }}</span>
                <span class="resource-value" :style="{ color: getResourceColor(item.value) }">
                  {{ item.value }}%
                </span>
              </div>
              <el-progress
                :percentage="item.value"
                :stroke-width="10"
                :color="getResourceColor(item.value)"
                :show-text="false"
              />
              <div class="resource-detail">
                <span>已用: {{ item.used }}{{ item.unit }}</span>
                <span>总计: {{ item.total }}{{ item.unit }}</span>
              </div>
            </div>
          </div>
        </PageCard>
      </el-col>

      <!-- 右侧列表区 -->
      <el-col :span="8">
        <!-- 待办事项 -->
        <PageCard :icon="'Bell'" icon-bg="rgba(245, 63, 63, 0.1)" badge-type="danger">
          <template #header>
            <el-badge :value="todoItems.length" type="danger" />
          </template>
          <template #default>
            <div class="todo-list">
              <div 
                class="todo-item" 
                v-for="todo in todoItems" 
                :key="todo.id"
                @click="handleTodoClick(todo)"
              >
                <div class="todo-priority" :class="todo.priority"></div>
                <div class="todo-content">
                  <p class="todo-title">{{ todo.title }}</p>
                  <p class="todo-time">{{ todo.time }}</p>
                </div>
                <el-tag size="small" :type="todo.tagType">{{ todo.tag }}</el-tag>
              </div>
            </div>
          </template>
        </PageCard>

        <!-- 最近告警 -->
        <PageCard :icon="'Warning'" icon-bg="rgba(255, 125, 0, 0.1)">
          <template #header>
            <el-link type="primary" @click="$router.push('/alerts')">查看全部</el-link>
          </template>
          <template #default>
            <div class="alert-list">
              <div 
                class="alert-item" 
                v-for="alert in recentAlerts" 
                :key="alert.id"
                :class="alert.level"
              >
                <div class="alert-level">
                  <el-icon v-if="alert.level === 'critical'" color="#f53f3f"><CircleCheckFilled /></el-icon>
                  <el-icon v-else color="#ff7d00"><WarningFilled /></el-icon>
                </div>
                <div class="alert-content">
                  <p class="alert-message">{{ alert.message }}</p>
                  <p class="alert-host">{{ alert.host }} · {{ alert.time }}</p>
                </div>
                <el-button size="small" text @click.stop="handleAlertAck(alert)">处理</el-button>
              </div>
            </div>
          </template>
        </PageCard>

        <!-- 快捷操作 -->
        <PageCard :icon="'Operation'" icon-bg="rgba(22, 93, 255, 0.1)">
          <template #default>
            <div class="quick-actions">
              <div 
                class="quick-action" 
                v-for="action in quickActions" 
                :key="action.title"
                @click="handleQuickActionClick(action)"
              >
                <div class="action-icon" :style="{ background: action.bg }">
                  <el-icon><component :is="action.icon" /></el-icon>
                </div>
                <span class="action-title">{{ action.title }}</span>
              </div>
            </div>
          </template>
        </PageCard>
      </el-col>
    </el-row>

    <!-- Loading状态 -->
    <div class="loading-overlay" v-if="loading">
      <div class="loading-spinner"></div>
      <span>加载数据中...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Bell, Warning, Operation, CircleCheckFilled, WarningFilled, Top, Bottom, Odometer, DataLine, Monitor } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import PageCard from '@/components/PageCard.vue'

const router = useRouter()

const loading = ref(false)
const serverTimeRange = ref('realtime')
const alertTimeRange = ref('7d')

// 统计数据
const serverStats = reactive({
  total: 50,
  online: 45,
  offline: 3,
  maintenance: 2
})

const alertStats = reactive({
  critical: 2,
  warning: 5,
  pending: 7,
  total: 12
})

const workOrderStats = reactive({
  pending: 3,
  total: 15
})

// 服务器图例
const serverLegend = computed(() => [
  { name: '在线', value: serverStats.online, color: '#00b42a' },
  { name: '离线', value: serverStats.offline, color: '#f53f3f' },
  { name: '维护中', value: serverStats.maintenance, color: '#ff7d00' }
])

// 统计卡片配置
const stats = computed(() => [
  { 
    title: '设备总数', 
    value: serverStats.total, 
    description: '在线 ' + serverStats.online + ' 台',
    icon: 'Odometer', 
    color: 'linear-gradient(135deg, #165dff, #4080ff)',
    trend: 5,
    route: '/devices'
  },
  { 
    title: '在线设备', 
    value: serverStats.online, 
    description: '占比 ' + Math.round(serverStats.online / serverStats.total * 100) + '%',
    icon: 'CircleCheck', 
    color: 'linear-gradient(135deg, #00b42a, #23c343)',
    trend: 2,
    route: '/devices'
  },
  { 
    title: '告警数量', 
    value: alertStats.pending, 
    description: '严重 ' + alertStats.critical + ' 条',
    icon: 'Warning', 
    color: 'linear-gradient(135deg, #ff7d00, #ff9f40)',
    trend: -10,
    route: '/alerts'
  },
  { 
    title: '待处理工单', 
    value: workOrderStats.pending, 
    description: '共 ' + workOrderStats.total + ' 条',
    icon: 'Document', 
    color: 'linear-gradient(135deg, #f53f3f, #ff7875)',
    trend: 15,
    route: '/workorder'
  }
])

// 资源使用率
const resourceItems = reactive([
  { name: 'CPU 使用率', value: 45, used: '45', total: '100', unit: '核' },
  { name: '内存使用率', value: 68, used: '55', total: '80', unit: 'GB' },
  { name: '磁盘使用率', value: 52, used: '520', total: '1000', unit: 'GB' }
])

// 待办事项
const todoItems = reactive([
  { id: 1, title: '服务器 web-01 内存使用率超阈值', time: '10分钟前', priority: 'high', tag: '紧急', tagType: 'danger' },
  { id: 2, title: '完成防火墙规则变更审批', time: '30分钟前', priority: 'medium', tag: '待审批', tagType: 'warning' },
  { id: 3, title: '备份任务执行失败需检查', time: '1小时前', priority: 'medium', tag: '待处理', tagType: 'info' },
  { id: 4, title: '系统巡检报告待生成', time: '2小时前', priority: 'low', tag: '计划中', tagType: 'success' }
])

// 最近告警
const recentAlerts = ref([
  { id: 1, level: 'critical', message: 'CPU使用率 > 90%', host: 'web-01', time: '10:30' },
  { id: 2, level: 'warning', message: '磁盘空间不足', host: 'db-02', time: '10:15' },
  { id: 3, level: 'warning', message: '内存使用率 > 80%', host: 'app-03', time: '09:45' },
  { id: 4, level: 'warning', message: '网络延迟异常', host: 'net-01', time: '09:20' },
  { id: 5, level: 'critical', message: '服务响应超时', host: 'web-02', time: '08:55' }
])

// 快捷操作
const quickActions = [
  { title: '新建工单', icon: 'EditPen', bg: 'rgba(22, 93, 255, 0.1)', color: '#165dff' },
  { title: '设备采集', icon: 'Refresh', bg: 'rgba(0, 180, 42, 0.1)', color: '#00b42a' },
  { title: '查看报告', icon: 'Document', bg: 'rgba(255, 125, 0, 0.1)', color: '#ff7d00' },
  { title: '知识搜索', icon: 'Search', bg: 'rgba(245, 63, 63, 0.1)', color: '#f53f3f' }
]

// 获取问候语
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

// 当前日期
const currentDate = computed(() => {
  const now = new Date()
  return `${now.getMonth() + 1}月${now.getDate()}日 ${['周日', '周一', '周二', '周三', '周四', '周五', '周六'][now.getDay()]}`
})

// 获取资源颜色
const getResourceColor = (value) => {
  if (value >= 80) return '#f53f3f'
  if (value >= 60) return '#ff7d00'
  return '#00b42a'
}

// 图表 Ref
const serverChartRef = ref(null)
const alertChartRef = ref(null)
let serverChart = null
let alertChart = null

// 初始化图表
const initCharts = () => {
  initServerChart()
  initAlertChart()
}

// 服务器状态饼图
const initServerChart = () => {
  if (!serverChartRef.value) return
  
  serverChart = echarts.init(serverChartRef.value)
  serverChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    color: ['#00b42a', '#f53f3f', '#ff7d00'],
    series: [{
      type: 'pie',
      radius: ['50%', '75%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#fff',
        borderWidth: 3
      },
      label: { show: false },
      emphasis: {
        scale: true,
        scaleSize: 8
      },
      data: [
        { value: serverStats.online, name: '在线' },
        { value: serverStats.offline, name: '离线' },
        { value: serverStats.maintenance, name: '维护中' }
      ]
    }]
  })
}

// 告警趋势图
const initAlertChart = () => {
  if (!alertChartRef.value) return
  
  alertChart = echarts.init(alertChartRef.value)
  alertChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['严重', '警告'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#86909c' }
    },
    series: [
      {
        name: '严重',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: [2, 1, 3, 5, 4, 3, 2],
        lineStyle: { color: '#f53f3f', width: 2 },
        itemStyle: { color: '#f53f3f' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245, 63, 63, 0.3)' },
            { offset: 1, color: 'rgba(245, 63, 63, 0)' }
          ])
        }
      },
      {
        name: '警告',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: [5, 4, 8, 12, 10, 7, 5],
        lineStyle: { color: '#ff7d00', width: 2 },
        itemStyle: { color: '#ff7d00' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255, 125, 0, 0.3)' },
            { offset: 1, color: 'rgba(255, 125, 0, 0)' }
          ])
        }
      }
    ]
  })
}

// 加载服务器数据
const loadServerData = () => {
  console.log('Loading server data, range:', serverTimeRange.value)
}

// 加载告警趋势
const loadAlertTrend = () => {
  console.log('Loading alert trend, range:', alertTimeRange.value)
}

// 窗口大小变化
const handleResize = () => {
  serverChart?.resize()
  alertChart?.resize()
}

// 事件处理
const handleStatClick = (stat) => {
  if (stat.route) {
    router.push(stat.route)
  }
}

const handleQuickAction = () => {
  ElMessage.info('快捷操作面板')
}

const handleTodoClick = (todo) => {
  ElMessage.info('待办详情: ' + todo.title)
}

const handleAlertAck = (alert) => {
  ElMessage.success('已确认告警: ' + alert.message)
}

const handleQuickActionClick = (action) => {
  const routes = {
    '新建工单': '/workorder?action=create',
    '设备采集': '/devices?action=collect',
    '查看报告': '/reports',
    '知识搜索': '/knowledge'
  }
  router.push(routes[action.title] || '/')
}

// 生命周期
onMounted(() => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    initCharts()
  }, 500)
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  serverChart?.dispose()
  alertChart?.dispose()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.dashboard {
  padding: $spacing-xl;
  min-height: 100%;
  background: $bg-page;
  animation: fadeIn 0.3s ease-out;
}

// 欢迎栏
.welcome-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-xl $spacing-xxl;
  background: linear-gradient(135deg, $primary 0%, #4080ff 100%);
  border-radius: $radius-xl;
  margin-bottom: $spacing-xl;
  color: #fff;

  .welcome-content {
    .welcome-title {
      font-size: $font-size-xl;
      font-weight: $font-weight-bold;
      margin: 0 0 $space-2 0;
      display: flex;
      align-items: center;
      gap: $spacing-sm;

      .greeting-icon {
        font-size: 24px;
      }
    }

    .welcome-desc {
      font-size: $font-size-sm;
      opacity: 0.9;
      margin: 0;

      .alert-count {
        background: rgba(255,255,255,0.2);
        padding: 2px 8px;
        border-radius: $radius-pill;
        font-weight: $font-weight-medium;

        &.safe {
          background: rgba(0,180,42,0.3);
        }
      }
    }
  }

  .welcome-actions {
    :deep(.el-button) {
      background: rgba(255,255,255,0.2);
      border: 1px solid rgba(255,255,255,0.3);
      color: #fff;

      &:hover {
        background: rgba(255,255,255,0.3);
      }
    }
  }
}

// 统计卡片网格
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.stat-card {
  background: $bg-container;
  border-radius: $radius-lg;
  padding: $spacing-xl;
  display: flex;
  align-items: flex-start;
  gap: $spacing-md;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: fadeInUp 0.4s ease-out backwards;

  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-lg;
    border-color: $primary-lighter;

    .stat-accent {
      opacity: 1;
    }

    .stat-icon {
      transform: scale(1.05);
    }
  }

  .stat-icon {
    width: 52px;
    height: 52px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 22px;
    flex-shrink: 0;
    transition: transform 0.3s;
  }

  .stat-content {
    flex: 1;
    min-width: 0;

    .stat-value {
      font-size: 28px;
      font-weight: $font-weight-bold;
      color: $text-primary;
      line-height: 1.2;
    }

    .stat-title {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-top: $space-1;
    }

    .stat-desc {
      font-size: $font-size-xs;
      color: $text-placeholder;
      margin-top: 2px;
    }
  }

  .stat-trend {
    position: absolute;
    right: $spacing-md;
    top: $spacing-md;
    display: flex;
    align-items: center;
    gap: 2px;
    font-size: $font-size-xs;
    font-weight: $font-weight-medium;
    padding: 3px 8px;
    border-radius: $radius-pill;

    &.up {
      color: $danger;
      background: $danger-lighter;
    }

    &.down {
      color: $success;
      background: $success-lighter;
    }
  }

  .stat-accent {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    opacity: 0;
    transition: opacity 0.3s;
  }
}

// 主要内容区
.main-content {
  .el-col {
    &:first-child {
      .page-card {
        margin-bottom: $spacing-lg;
      }
    }

    &:last-child {
      .page-card {
        margin-bottom: $spacing-lg;
      }
    }
  }
}

// 图表包装器
.chart-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-xl;

  .chart-container {
    flex: 1;
    height: 200px;
  }

  .chart-legend {
    display: flex;
    flex-direction: column;
    gap: $spacing-md;
    padding: $spacing-md;

    .legend-item {
      display: flex;
      align-items: center;
      gap: $spacing-sm;

      .legend-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }

      .legend-label {
        font-size: $font-size-sm;
        color: $text-secondary;
        width: 50px;
      }

      .legend-value {
        font-size: $font-size-sm;
        font-weight: $font-weight-medium;
        color: $text-primary;
      }
    }
  }
}

// 资源列表
.resource-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;

  .resource-item {
    .resource-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: $spacing-sm;

      .resource-name {
        font-size: $font-size-sm;
        color: $text-regular;
      }

      .resource-value {
        font-size: $font-size-sm;
        font-weight: $font-weight-medium;
      }
    }

    :deep(.el-progress-bar__outer) {
      background: $bg-page;
    }

    .resource-detail {
      display: flex;
      justify-content: space-between;
      margin-top: $space-1;
      font-size: $font-size-xs;
      color: $text-placeholder;
    }
  }
}

// 待办列表
.todo-list {
  .todo-item {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-md 0;
    border-bottom: 1px solid $border-light;
    cursor: pointer;
    transition: all 0.15s;

    &:last-child {
      border-bottom: none;
    }

    &:hover {
      transform: translateX(2px);
    }

    .todo-priority {
      width: 4px;
      height: 32px;
      border-radius: 2px;
      flex-shrink: 0;

      &.high { background: $danger; }
      &.medium { background: $warning; }
      &.low { background: $success; }
    }

    .todo-content {
      flex: 1;
      min-width: 0;

      .todo-title {
        font-size: $font-size-sm;
        color: $text-primary;
        margin: 0 0 2px 0;
        @include text-ellipsis;
      }

      .todo-time {
        font-size: $font-size-xs;
        color: $text-placeholder;
        margin: 0;
      }
    }
  }
}

// 告警列表
.alert-list {
  .alert-item {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-md 0;
    border-bottom: 1px solid $border-light;

    &:last-child {
      border-bottom: none;
    }

    .alert-level {
      width: 28px;
      height: 28px;
      border-radius: $radius-round;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;

      &.critical {
        background: $danger-lighter;
      }

      &.warning {
        background: $warning-lighter;
      }
    }

    .alert-content {
      flex: 1;
      min-width: 0;

      .alert-message {
        font-size: $font-size-sm;
        color: $text-primary;
        margin: 0 0 2px 0;
        @include text-ellipsis;
      }

      .alert-host {
        font-size: $font-size-xs;
        color: $text-placeholder;
        margin: 0;
      }
    }
  }
}

// 快捷操作
.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;

  .quick-action {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-lg;
    background: $bg-page;
    border-radius: $radius-md;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: $shadow-sm;

      .action-icon {
        transform: scale(1.1);
      }
    }

    .action-icon {
      width: 44px;
      height: 44px;
      border-radius: $radius-md;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s;

      .el-icon {
        font-size: 20px;
      }
    }

    .action-title {
      font-size: $font-size-sm;
      color: $text-regular;
      font-weight: $font-weight-medium;
    }
  }
}

// Loading状态
.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba($bg-page, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-lg;
  z-index: 100;

  .loading-spinner {
    width: 48px;
    height: 48px;
    border: 3px solid $border-light;
    border-top-color: $primary;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  span {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>