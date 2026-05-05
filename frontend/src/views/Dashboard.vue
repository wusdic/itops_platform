<template>
  <div class="dashboard">
    <!-- 欢迎栏 -->
    <div class="welcome-bar">
      <div class="welcome-content">
        <h2 class="welcome-title">早上好，管理员</h2>
        <p class="welcome-desc">今天是 {{ currentDate }}，您有 {{ alertStats.pending }} 条待处理告警</p>
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
      <StatCard
        v-for="(stat, index) in stats"
        :key="stat.title"
        :value="stat.value"
        :title="stat.title"
        :description="stat.description"
        :icon="stat.icon"
        :icon-bg="stat.color"
        :trend="stat.trend"
        :clickable="true"
        :style="{ animationDelay: `${index * 0.1}s` }"
        class="stat-animate"
        @click="handleStatClick(stat)"
      />
    </div>

    <!-- 主要内容区 -->
    <el-row :gutter="20" class="main-content">
      <!-- 左侧图表区 -->
      <el-col :span="16">
        <!-- 服务器状态 -->
        <ChartCard title="设备状态分布" subtitle="实时监控设备运行状态">
          <template #actions>
            <el-select v-model="serverTimeRange" size="small" @change="loadServerData">
              <el-option label="实时" value="realtime" />
              <el-option label="24小时" value="24h" />
              <el-option label="7天" value="7d" />
            </el-select>
          </template>
          <template #default>
            <div class="chart-wrapper">
              <div ref="serverChartRef" class="chart-container"></div>
              <div class="chart-legend">
                <div class="legend-item">
                  <span class="legend-dot online"></span>
                  <span class="legend-label">在线</span>
                  <span class="legend-value">{{ serverStats.online }}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot offline"></span>
                  <span class="legend-label">离线</span>
                  <span class="legend-value">{{ serverStats.offline }}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot maintenance"></span>
                  <span class="legend-label">维护中</span>
                  <span class="legend-value">{{ serverStats.maintenance }}</span>
                </div>
              </div>
            </div>
          </template>
        </ChartCard>

        <!-- 告警趋势 -->
        <ChartCard title="告警趋势" subtitle="近7天告警统计">
          <template #actions>
            <el-radio-group v-model="alertTimeRange" size="small" @change="loadAlertTrend">
              <el-radio-button label="7d">近7天</el-radio-button>
              <el-radio-button label="30d">近30天</el-radio-button>
            </el-radio-group>
          </template>
          <div ref="alertChartRef" class="chart-container" style="height: 280px"></div>
        </ChartCard>

        <!-- 资源使用率 -->
        <ChartCard title="资源使用率" subtitle="CPU/内存/磁盘实时状态">
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
                :stroke-width="8"
                :color="getResourceColor(item.value)"
                :show-text="false"
              />
              <div class="resource-detail">
                <span>已用: {{ item.used }}{{ item.unit }}</span>
                <span>总计: {{ item.total }}{{ item.unit }}</span>
              </div>
            </div>
          </div>
        </ChartCard>
      </el-col>

      <!-- 右侧列表区 -->
      <el-col :span="8">
        <!-- 待办事项 -->
        <div class="side-card todo-card">
          <div class="side-card-header">
            <h3 class="side-card-title">
              <el-icon><Bell /></el-icon>
              待处理事项
            </h3>
            <el-badge :value="todoItems.length" type="danger" />
          </div>
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
        </div>

        <!-- 最近告警 -->
        <div class="side-card alert-card">
          <div class="side-card-header">
            <h3 class="side-card-title">
              <el-icon><Warning /></el-icon>
              最近告警
            </h3>
            <el-link type="primary" @click="$router.push('/alerts')">查看全部</el-link>
          </div>
          <div class="alert-list">
            <div 
              class="alert-item" 
              v-for="alert in recentAlerts" 
              :key="alert.id"
              :class="alert.level"
            >
              <div class="alert-level">
                <el-icon v-if="alert.level === 'critical'" color="#f53f3f"><-circle-check-filled /></el-icon>
                <el-icon v-else color="#ff7d00"><warning-filled /></el-icon>
              </div>
              <div class="alert-content">
                <p class="alert-message">{{ alert.message }}</p>
                <p class="alert-host">{{ alert.host }} · {{ alert.time }}</p>
              </div>
              <el-button size="small" text @click.stop="handleAlertAck(alert)">处理</el-button>
            </div>
          </div>
        </div>

        <!-- 快捷操作 -->
        <div class="side-card action-card">
          <div class="side-card-header">
            <h3 class="side-card-title">
              <el-icon><Operation /></el-icon>
              快捷操作
            </h3>
          </div>
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
        </div>
      </el-col>
    </el-row>

    <!-- 加载状态 -->
    <LoadingSpinner v-if="loading" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Bell, Warning, Operation, CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import StatCard from '@/components/StatCard.vue'
import ChartCard from '@/components/ChartCard.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const router = useRouter()

// 加载状态
const loading = ref(false)

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

// 统计卡片配置
const stats = computed(() => [
  { 
    title: '设备总数', 
    value: serverStats.total, 
    description: '在线 ' + serverStats.online + ' 台',
    icon: 'Odometer', 
    color: '#165dff',
    trend: 5,
    route: '/devices'
  },
  { 
    title: '在线设备', 
    value: serverStats.online, 
    description: '占比 ' + Math.round(serverStats.online / serverStats.total * 100) + '%',
    icon: 'CircleCheck', 
    color: '#00b42a',
    trend: 2,
    route: '/devices'
  },
  { 
    title: '告警数量', 
    value: alertStats.pending, 
    description: '严重 ' + alertStats.critical + ' 条',
    icon: 'Warning', 
    color: '#ff7d00',
    trend: -10,
    route: '/alerts'
  },
  { 
    title: '待处理工单', 
    value: workOrderStats.pending, 
    description: '共 ' + workOrderStats.total + ' 条',
    icon: 'Document', 
    color: '#f53f3f',
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

// 时间范围
const serverTimeRange = ref('realtime')
const alertTimeRange = ref('7d')

// 图表 Ref
const serverChartRef = ref(null)
const alertChartRef = ref(null)
let serverChart = null
let alertChart = null

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
      label: {
        show: false
      },
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
  // 模拟加载
  console.log('Loading server data, range:', serverTimeRange.value)
}

// 加载告警趋势
const loadAlertTrend = () => {
  // 模拟加载
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
  
  // 模拟数据加载
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
  animation: fadeIn 0.3s ease;
}

// ========== 欢迎栏 ==========
.welcome-bar {
  @include flex-between;
  margin-bottom: $spacing-xl;

  .welcome-title {
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin-bottom: $spacing-xs;
  }

  .welcome-desc {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

// ========== 统计卡片区 ==========
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.stat-animate {
  animation: slideInUp 0.4s ease-out backwards;
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// ========== 主要内容区 ==========
.main-content {
  .el-col {
    &:first-child {
      display: flex;
      flex-direction: column;
      gap: $spacing-lg;
    }

    &:last-child {
      display: flex;
      flex-direction: column;
      gap: $spacing-lg;
    }
  }
}

// ========== 图表 ==========
.chart-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-xl;
}

.chart-container {
  flex: 1;
  height: 260px;
}

.chart-legend {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;

  .legend-item {
    display: flex;
    align-items: center;
    gap: $spacing-sm;

    .legend-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;

      &.online { background: #00b42a; }
      &.offline { background: #f53f3f; }
      &.maintenance { background: #ff7d00; }
    }

    .legend-label {
      font-size: $font-size-sm;
      color: $text-secondary;
      width: 50px;
    }

    .legend-value {
      font-size: $font-size-md;
      font-weight: $font-weight-semibold;
      color: $text-primary;
    }
  }
}

// ========== 资源列表 ==========
.resource-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-lg;

  .resource-item {
    padding: $spacing-md;
    background: $bg-page;
    border-radius: $border-radius-md;

    .resource-header {
      @include flex-between;
      margin-bottom: $spacing-sm;

      .resource-name {
        font-size: $font-size-sm;
        color: $text-regular;
      }

      .resource-value {
        font-size: $font-size-md;
        font-weight: $font-weight-bold;
      }
    }

    .resource-detail {
      @include flex-between;
      margin-top: $spacing-sm;
      font-size: $font-size-xs;
      color: $text-placeholder;
    }
  }
}

// ========== 侧边卡片 ==========
.side-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  padding: $spacing-lg;
  box-shadow: $shadow-sm;
}

.side-card-header {
  @include flex-between;
  margin-bottom: $spacing-md;

  .side-card-title {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin: 0;

    .el-icon {
      color: $primary;
    }
  }
}

// ========== 待办列表 ==========
.todo-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: $transition-fast;

  &:hover {
    background: rgba($primary, 0.04);
  }

  .todo-priority {
    width: 4px;
    height: 36px;
    border-radius: 2px;

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
      margin: 0;
      @include multi-ellipsis(1);
    }

    .todo-time {
      font-size: $font-size-xs;
      color: $text-placeholder;
      margin: 4px 0 0 0;
    }
  }
}

// ========== 告警列表 ==========
.alert-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;
  transition: $transition-fast;

  &:hover {
    background: rgba($primary, 0.04);
  }

  &.critical {
    border-left: 3px solid $danger;
  }

  &.warning {
    border-left: 3px solid $warning;
  }

  .alert-content {
    flex: 1;
    min-width: 0;

    .alert-message {
      font-size: $font-size-sm;
      color: $text-primary;
      margin: 0;
    }

    .alert-host {
      font-size: $font-size-xs;
      color: $text-placeholder;
      margin: 2px 0 0 0;
    }
  }
}

// ========== 快捷操作 ==========
.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;

  .quick-action {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-md;
    background: $bg-page;
    border-radius: $border-radius-md;
    cursor: pointer;
    transition: $transition-fast;

    &:hover {
      background: rgba($primary, 0.04);
      transform: translateY(-2px);
    }

    .action-icon {
      width: 40px;
      height: 40px;
      border-radius: $border-radius-md;
      @include flex-center;
      font-size: 18px;
    }

    .action-title {
      font-size: $font-size-sm;
      color: $text-regular;
    }
  }
}

// ========== 响应式 ==========
@include respond-to('xl') {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@include respond-to('lg') {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .main-content {
    .el-col:first-child,
    .el-col:last-child {
      width: 100%;
    }
  }

  .resource-list {
    grid-template-columns: 1fr;
  }
}
</style>