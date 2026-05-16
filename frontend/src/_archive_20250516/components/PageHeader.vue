<template>
  <div
    class="page-header"
    :class="[`size-${size}`, { 'no-border': noBorder }]"
  >
    <!-- 左侧 -->
    <div class="header-left">
      <!-- 返回按钮 -->
      <el-button 
        v-if="showBack" 
        text 
        class="back-btn"
        @click="handleBack"
      >
        <el-icon :size="18">
          <ArrowLeft />
        </el-icon>
      </el-button>

      <!-- 标题区 -->
      <div class="header-title-area">
        <div class="title-row">
          <!-- 图标 -->
          <div
            v-if="icon"
            class="title-icon"
            :style="{ background: iconBg }"
          >
            <el-icon
              :size="iconSize"
              :color="iconColor"
            >
              <component :is="icon" />
            </el-icon>
          </div>
          
          <!-- 标题 -->
          <h1 class="page-title">
            {{ title }}
          </h1>
          
          <!-- 状态标签 -->
          <el-tag
            v-if="status"
            :type="statusType"
            size="small"
            effect="light"
          >
            {{ status }}
          </el-tag>

          <!-- 徽章 -->
          <el-badge 
            v-if="badge" 
            :value="badge" 
            :max="99"
            :type="badgeType"
          />
        </div>

        <!-- 副标题 -->
        <p
          v-if="subtitle"
          class="page-subtitle"
        >
          {{ subtitle }}
        </p>
      </div>
    </div>

    <!-- 右侧操作区 -->
    <div
      v-if="$slots.actions || actions.length"
      class="header-right"
    >
      <slot name="actions">
        <template
          v-for="(action, i) in actions"
          :key="i"
        >
          <el-button 
            v-if="!action.hidden"
            :type="action.type || 'default'"
            :size="action.size || 'default'"
            :icon="action.icon"
            :loading="action.loading"
            :disabled="action.disabled"
            @click="action.handler?.()"
          >
            {{ action.text }}
          </el-button>
        </template>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps({
  // 标题
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  // 图标
  icon: { type: String, default: '' },
  iconSize: { type: Number, default: 20 },
  iconBg: { type: String, default: '' },
  iconColor: { type: String, default: '' },
  // 状态
  status: { type: String, default: '' },
  statusType: { type: String, default: 'primary' },
  // 徽章
  badge: { type: [String, Number], default: null },
  badgeType: { type: String, default: 'primary' },
  // 返回按钮
  showBack: { type: Boolean, default: false },
  backPath: { type: String, default: '' },
  // 尺寸
  size: { 
    type: String, 
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  // 操作按钮
  actions: {
    type: Array,
    default: () => []
  },
  // 无边框
  noBorder: { type: Boolean, default: false }
})

const emit = defineEmits(['back'])

// 默认图标背景色
const defaultIconBg = computed(() => {
  const colorMap = {
    primary: 'var(--el-color-primary-light-8)',
    success: 'var(--el-color-success-light-8)',
    warning: 'var(--el-color-warning-light-8)',
    danger: 'var(--el-color-danger-light-8)',
    info: 'var(--el-color-info-light-8)'
  }
  return props.iconBg || colorMap.primary
})

const handleBack = () => {
  if (props.backPath) {
    router.push(props.backPath)
  } else {
    router.back()
  }
  emit('back')
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: $spacing-xl 0;
  margin-bottom: $spacing-lg;
  border-bottom: 1px solid $border-light;
  transition: all 0.2s;

  &.no-border {
    border-bottom: none;
    margin-bottom: 0;
  }

  // 尺寸
  &.size-sm {
    padding: $spacing-md 0;

    .page-title {
      font-size: $font-size-lg;
    }
  }

  &.size-lg {
    padding: $spacing-xl * 1.5 0;

    .page-title {
      font-size: $font-size-xxl;
    }
  }
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.back-btn {
  padding: $space-2;
  border-radius: $radius-md;
  transition: all 0.15s;

  &:hover {
    background: $bg-page;
  }

  .el-icon {
    color: $text-secondary;
    transition: transform 0.2s;
  }

  &:hover .el-icon {
    transform: translateX(-2px);
    color: $text-primary;
  }
}

.header-title-area {
  .title-row {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  .title-icon {
    width: 36px;
    height: 36px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .page-title {
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0;
    line-height: 1.4;
  }

  .page-subtitle {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin: $space-2 0 0 0;
    line-height: 1.5;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-shrink: 0;
}
</style>