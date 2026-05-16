<template>
  <div
    class="stat-card"
    :class="{ clickable, 'has-trend': trend !== null }"
  >
    <div class="stat-main">
      <!-- 左侧图标 -->
      <div
        class="stat-icon"
        :style="iconStyle"
      >
        <el-icon :size="iconSize">
          <component
            :is="iconComponent"
            v-if="typeof iconComponent === 'object'"
          />
          <span v-else>{{ iconComponent }}</span>
        </el-icon>
      </div>
      
      <!-- 中间内容 -->
      <div class="stat-content">
        <div
          class="stat-value"
          :style="{ color: valueColor }"
        >
          <slot name="value">
            {{ displayValue }}
          </slot>
        </div>
        <div class="stat-title">
          {{ title }}
        </div>
        <div
          v-if="description"
          class="stat-desc"
        >
          {{ description }}
        </div>
      </div>
    </div>

    <!-- 右侧趋势 -->
    <div
      v-if="trend !== null"
      class="stat-trend"
      :class="trendClass"
    >
      <el-icon v-if="trend > 0">
        <TrendCharts />
      </el-icon>
      <span>{{ Math.abs(trend) }}%</span>
    </div>

    <!-- 点击效果 -->
    <div class="stat-hover-effect" />
  </div>
</template>

<script setup>
import { computed, toRef } from 'vue'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { TrendCharts } from '@element-plus/icons-vue'

const props = defineProps({
  // 数值
  value: { type: [String, Number], default: '0' },
  // 标题
  title: { type: String, default: '' },
  // 描述
  description: { type: String, default: '' },
  // 图标（可以是组件名或HTML）
  icon: { type: [String, Object], default: 'Odometer' },
  // 图标背景色
  iconBg: { type: String, default: '' },
  // 图标大小
  iconSize: { type: Number, default: 24 },
  // 数值颜色
  valueColor: { type: String, default: '#1d2129' },
  // 是否可点击
  clickable: { type: Boolean, default: false },
  // 趋势百分比
  trend: { type: Number, default: null },
  // 预设主题
  theme: { type: String, default: 'default' }
})

const emit = defineEmits(['click'])

// 图标组件
const iconComponent = computed(() => {
  if (typeof props.icon === 'object') return props.icon
  return ElementPlusIconsVue[props.icon] || '📊'
})

// 图标样式
const iconStyle = computed(() => {
  if (props.iconBg) {
    return { background: props.iconBg }
  }
  
  const themeColors = {
    primary: '#165dff',
    success: '#00b42a',
    warning: '#ff7d00',
    danger: '#f53f3f',
    info: '#6370f5'
  }
  
  if (themeColors[props.theme]) {
    return { background: themeColors[props.theme] }
  }
  
  return { background: '#165dff' }
})

// 趋势样式
const trendClass = computed(() => {
  if (props.trend > 0) return 'trend-up'
  if (props.trend < 0) return 'trend-down'
  return 'trend-flat'
})

// 显示值
const displayValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-lg;
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  &.clickable {
    cursor: pointer;

    &:hover {
      transform: translateY(-4px);
      box-shadow: $shadow-base;

      .stat-hover-effect {
        opacity: 1;
      }

      .stat-icon {
        transform: scale(1.05);
      }
    }

    &:active {
      transform: translateY(-2px);
    }
  }

  &.has-trend {
    padding-right: $spacing-xxl;
  }
}

// ========== 主内容区 ==========
.stat-main {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
}

// ========== 图标 ==========
.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: $border-radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  transition: transform 0.25s ease;
  font-size: 24px;
}

// ========== 内容 ==========
.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: $font-size-max;
  font-weight: $font-weight-bold;
  color: $text-primary;
  line-height: 1.2;
  letter-spacing: -1px;
}

.stat-title {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin-top: $spacing-xs;
}

.stat-desc {
  font-size: $font-size-xs;
  color: $text-placeholder;
  margin-top: 2px;
}

// ========== 趋势 ==========
.stat-trend {
  position: absolute;
  right: $spacing-lg;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  padding: 4px 8px;
  border-radius: $border-radius-sm;

  &.trend-up {
    color: $danger;
    background: rgba($danger, 0.08);
  }

  &.trend-down {
    color: $success;
    background: rgba($success, 0.08);
  }

  &.trend-flat {
    color: $text-secondary;
    background: $bg-page;
  }
}

// ========== 悬停效果 ==========
.stat-hover-effect {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, $primary, $primary-light);
  opacity: 0;
  transition: opacity 0.25s ease;
}
</style>