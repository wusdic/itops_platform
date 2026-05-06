<template>
  <div
    class="empty-state"
    :class="[`size-${size}`, { 'is-center': center }]"
  >
    <!-- 装饰性背景 -->
    <div class="empty-bg">
      <div class="bg-circle bg-circle-1" />
      <div class="bg-circle bg-circle-2" />
      <div class="bg-circle bg-circle-3" />
    </div>

    <!-- 插画/SVG -->
    <div
      v-if="!hideIcon"
      class="empty-illustration"
    >
      <div
        class="illustration-wrapper"
        :class="{ 'animate-bounce': animate }"
      >
        <component :is="illustrationComponent" />
      </div>
    </div>

    <!-- 文案 -->
    <div class="empty-content">
      <h3 class="empty-title">
        {{ title }}
      </h3>
      <p
        v-if="description"
        class="empty-description"
      >
        {{ description }}
      </p>
      
      <!-- 插槽：额外的描述信息 -->
      <div
        v-if="$slots.extra"
        class="empty-extra"
      >
        <slot name="extra" />
      </div>
    </div>

    <!-- 操作按钮 -->
    <div
      v-if="$slots.actions || actionText"
      class="empty-actions"
    >
      <slot name="actions">
        <el-button 
          v-if="actionText" 
          :type="actionType" 
          :size="buttonSize"
          @click="$emit('action')"
        >
          <el-icon
            v-if="actionIcon"
            :size="14"
            class="mr-1"
          >
            <component :is="actionIcon" />
          </el-icon>
          {{ actionText }}
        </el-button>
      </slot>
    </div>

    <!-- 快捷提示 -->
    <div
      v-if="tips && tips.length"
      class="empty-tips"
    >
      <div
        v-if="tipsLabel"
        class="tips-label"
      >
        {{ tipsLabel }}
      </div>
      <ul class="tips-list">
        <li
          v-for="(tip, i) in tips"
          :key="i"
          class="tips-item"
        >
          <el-icon :size="12">
            <ArrowRight />
          </el-icon>
          {{ tip }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import EmptyServer from './illustrations/EmptyServer.vue'
import EmptyData from './illustrations/EmptyData.vue'
import EmptySearch from './illustrations/EmptySearch.vue'
import EmptyAlert from './illustrations/EmptyAlert.vue'
import EmptyChart from './illustrations/EmptyChart.vue'

const props = defineProps({
  // 类型：server/data/search/alert/chart
  type: { type: String, default: 'data' },
  // 文案
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '' },
  // 是否居中
  center: { type: Boolean, default: true },
  // 尺寸
  size: { 
    type: String, 
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  // 动画
  animate: { type: Boolean, default: true },
  // 隐藏图标
  hideIcon: { type: Boolean, default: false },
  // 操作按钮
  actionText: { type: String, default: '' },
  actionType: { type: String, default: 'primary' },
  actionIcon: { type: String, default: '' },
  buttonSize: { type: String, default: 'default' },
  // 提示语
  tipsLabel: { type: String, default: '你可以尝试' },
  tips: { type: Array, default: () => [] }
})

defineEmits(['action'])

const illustrationMap = {
  server: EmptyServer,
  data: EmptyData,
  search: EmptySearch,
  alert: EmptyAlert,
  chart: EmptyChart
}

const illustrationComponent = computed(() => illustrationMap[props.type] || EmptyData)
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-xl * 2 $spacing-xl;
  position: relative;
  overflow: hidden;

  &.is-center {
    text-align: center;
  }

  // 尺寸
  &.size-sm {
    padding: $spacing-xl;

    .empty-illustration {
      width: 80px;
      height: 80px;
    }

    .empty-title {
      font-size: $font-size-md;
    }
  }

  &.size-lg {
    .empty-illustration {
      width: 160px;
      height: 160px;
    }

    .empty-title {
      font-size: $font-size-xl;
    }
  }
}

// 装饰背景
.empty-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;

  .bg-circle {
    position: absolute;
    border-radius: 50%;
    opacity: 0.06;

    &.bg-circle-1 {
      width: 200px;
      height: 200px;
      background: $primary;
      top: -60px;
      right: -40px;
      animation: float-slow 8s ease-in-out infinite;
    }

    &.bg-circle-2 {
      width: 150px;
      height: 150px;
      background: $success;
      bottom: -30px;
      left: -20px;
      animation: float-slow 6s ease-in-out infinite reverse;
    }

    &.bg-circle-3 {
      width: 80px;
      height: 80px;
      background: $warning;
      top: 40%;
      right: 20%;
      animation: float-slow 5s ease-in-out infinite 1s;
    }
  }
}

@keyframes float-slow {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(5deg); }
}

// 插画容器
.empty-illustration {
  width: 120px;
  height: 120px;
  margin-bottom: $spacing-xl;
  position: relative;
  z-index: 1;

  .illustration-wrapper {
    width: 100%;
    height: 100%;

    &.animate-bounce {
      animation: illustration-bounce 3s ease-in-out infinite;
    }
  }

  :deep(svg) {
    width: 100%;
    height: 100%;
  }
}

@keyframes illustration-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

// 内容区
.empty-content {
  position: relative;
  z-index: 1;
  max-width: 400px;

  .empty-title {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin: 0 0 $space-2 0;
  }

  .empty-description {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin: $space-1 0 0 0;
    line-height: 1.6;
  }

  .empty-extra {
    margin-top: $spacing-md;
  }
}

// 操作按钮
.empty-actions {
  margin-top: $spacing-xl;
  position: relative;
  z-index: 1;
}

// 快捷提示
.empty-tips {
  margin-top: $spacing-xl;
  padding: $spacing-md $spacing-lg;
  background: $bg-page;
  border-radius: $radius-md;
  border: 1px dashed $border;
  position: relative;
  z-index: 1;
  max-width: 360px;

  .tips-label {
    font-size: $font-size-xs;
    color: $text-placeholder;
    margin-bottom: $spacing-sm;
  }

  .tips-list {
    list-style: none;
    margin: 0;
    padding: 0;

    .tips-item {
      display: flex;
      align-items: center;
      gap: $space-1;
      font-size: $font-size-sm;
      color: $text-secondary;
      padding: 4px 0;

      .el-icon {
        color: $text-placeholder;
        flex-shrink: 0;
      }
    }
  }
}

.mr-1 { margin-right: 4px; }
</style>