<template>
  <div
    class="chart-card"
    :class="{ 'has-header': $slots.header || title }"
  >
    <!-- 卡片头部 -->
    <div
      v-if="$slots.header || title"
      class="chart-header"
    >
      <slot name="header">
        <div class="header-content">
          <h3 class="chart-title">
            {{ title }}
          </h3>
          <p
            v-if="subtitle"
            class="chart-subtitle"
          >
            {{ subtitle }}
          </p>
        </div>
        <div class="header-actions">
          <slot name="actions" />
        </div>
      </slot>
    </div>

    <!-- 图表内容 -->
    <div class="chart-body">
      <div
        ref="chartRef"
        class="chart-container"
        :style="{ height: height }"
      />
      <div
        v-if="loading"
        class="chart-loading"
      >
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
      </div>
    </div>

    <!-- 卡片底部 -->
    <div
      v-if="$slots.footer"
      class="chart-footer"
    >
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  // 标题
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  
  // 图表配置
  option: { type: Object, default: () => ({}) },
  height: { type: String, default: '300px' },
  
  // 加载状态
  loading: { type: Boolean, default: false },
  
  // 主题
  theme: { type: String, default: 'light' },
  
  // 自动适应
  autoresize: { type: Boolean, default: true }
})

const emit = defineEmits(['ready', 'click'])

const chartRef = ref(null)
let chartInstance = null

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value, props.theme)
  
  // 设置默认配置
  const defaultOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e6eb',
      borderWidth: 1,
      textStyle: {
        color: '#4b4f59',
        fontSize: 13
      },
      axisPointer: {
        type: 'cross',
        crossStyle: { color: '#c9cdd4' }
      }
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#86909c', fontSize: 12 }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%',
      top: '10%',
      containLabel: true
    }
  }
  
  chartInstance.setOption({ ...defaultOption, ...props.option }, true)
  
  emit('ready', chartInstance)
  
  // 绑定点击事件
  chartInstance.on('click', (params) => {
    emit('click', params)
  })
}

// 更新图表
const updateChart = (option) => {
  if (!chartInstance) {
    initChart()
  }
  chartInstance?.setOption(option, true)
}

// 设置选项
const setOption = (option, notMerge = false) => {
  chartInstance?.setOption(option, !notMerge)
}

// 调整大小
const resize = () => {
  chartInstance?.resize()
}

// 清空
const clear = () => {
  chartInstance?.clear()
}

// 销毁
const dispose = () => {
  chartInstance?.dispose()
  chartInstance = null
}

// 监听配置变化
watch(() => props.option, (newOption) => {
  if (chartInstance && newOption) {
    setOption(newOption)
  }
}, { deep: true })

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
  })
  
  // 监听窗口大小变化
  if (props.autoresize) {
    window.addEventListener('resize', resize)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resize)
  dispose()
})

// 暴露方法
defineExpose({
  chartInstance,
  updateChart,
  setOption,
  resize,
  clear,
  dispose
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.chart-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  overflow: hidden;
  transition: box-shadow 0.25s ease;

  &:hover {
    box-shadow: $shadow-base;
  }

  &.has-header {
    .chart-body {
      padding-top: 0;
    }
  }
}

// ========== 头部 ==========
.chart-header {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $border-light;

  :deep(.el-select) {
    width: 120px;
  }
}

.header-content {
  .chart-title {
    font-size: $font-size-md;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin: 0;
  }

  .chart-subtitle {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin: 4px 0 0 0;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

// ========== 图表内容 ==========
.chart-body {
  position: relative;
  padding: $spacing-md $spacing-lg;
}

.chart-container {
  width: 100%;
}

.chart-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  @include flex-center;
  background: rgba(255, 255, 255, 0.8);
  z-index: 10;

  .el-icon {
    font-size: 28px;
    color: $primary;
  }
}

// ========== 底部 ==========
.chart-footer {
  padding: $spacing-md $spacing-lg;
  border-top: 1px solid $border-light;
}
</style>