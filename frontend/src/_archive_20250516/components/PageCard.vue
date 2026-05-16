<template>
  <div
    class="page-card"
    :class="[
      `page-card--${variant}`,
      { 'is-clickable': clickable, 'is-bordered': bordered }
    ]"
    :style="customStyle"
    @click="handleClick"
  >
    <!-- 顶部装饰条 -->
    <div
      v-if="accent"
      class="card-accent"
      :style="{ background: accentColor }"
    />

    <!-- 头部 -->
    <div
      v-if="$slots.header || title"
      class="card-header"
    >
      <div class="card-header-left">
        <div
          v-if="icon"
          class="card-icon"
          :style="{ background: iconBg }"
        >
          <el-icon :size="iconSize">
            <component :is="icon" />
          </el-icon>
        </div>
        <div class="card-titles">
          <h3
            v-if="title"
            class="card-title"
          >
            {{ title }}
          </h3>
          <p
            v-if="subtitle"
            class="card-subtitle"
          >
            {{ subtitle }}
          </p>
        </div>
      </div>
      <div
        v-if="$slots.header"
        class="card-header-right"
      >
        <slot name="header" />
      </div>
    </div>

    <!-- 内容 -->
    <div
      class="card-body"
      :class="{ 'no-padding': noPadding }"
    >
      <slot />
    </div>

    <!-- 底部 -->
    <div
      v-if="$slots.footer"
      class="card-footer"
    >
      <slot name="footer" />
    </div>

    <!-- 悬浮角标 -->
    <div
      v-if="badge"
      class="card-badge"
    >
      <el-badge
        :value="badge"
        :type="badgeType"
        :max="99"
      />
    </div>

    <!-- 选中态 -->
    <div
      v-if="selected"
      class="card-checked"
    >
      <el-icon :size="20">
        <Check />
      </el-icon>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Check } from '@element-plus/icons-vue'

const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  icon: { type: String, default: '' },
  iconSize: { type: Number, default: 20 },
  iconBg: { type: String, default: '' },
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'bordered', 'shadow', 'gradient', 'glow'].includes(v)
  },
  accent: { type: Boolean, default: false },
  accentColor: { type: String, default: '#165dff' },
  clickable: { type: Boolean, default: false },
  bordered: { type: Boolean, default: false },
  noPadding: { type: Boolean, default: false },
  badge: { type: [String, Number], default: null },
  badgeType: { type: String, default: 'primary' },
  selected: { type: Boolean, default: false },
  background: { type: String, default: '' }
})

const emit = defineEmits(['click'])

const customStyle = computed(() => ({
  ...(props.background ? { background: props.background } : {})
}))

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.page-card {
  position: relative;
  background: $bg-container;
  border-radius: $radius-lg;
  overflow: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

  // 变体
  &--default {
    box-shadow: $shadow-sm;
  }

  &--bordered {
    border: 1px solid $border-light;
  }

  &--shadow {
    box-shadow: $shadow-md;

    &:hover {
      box-shadow: $shadow-lg;
    }
  }

  &--gradient {
    background: linear-gradient(135deg, $bg-container 0%, $bg-page 100%);
  }

  &--glow {
    &::before {
      content: '';
      position: absolute;
      inset: -1px;
      border-radius: $radius-lg;
      padding: 1px;
      background: linear-gradient(135deg, var(--accent, $primary), transparent, var(--accent, $primary));
      -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      opacity: 0;
      transition: opacity 0.3s;
      pointer-events: none;
    }

    &:hover::before {
      opacity: 1;
    }
  }

  // 可点击
  &.is-clickable {
    cursor: pointer;

    &:hover {
      transform: translateY(-2px);
      box-shadow: $shadow-base;
    }

    &:active {
      transform: translateY(0);
    }
  }

  // 带边框
  &.is-bordered {
    border: 1px solid $border;
  }
}

// 顶部装饰条
.card-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  opacity: 0;
  transition: opacity 0.3s;
}

.page-card:hover .card-accent {
  opacity: 1;
}

// 头部
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-lg;
  border-bottom: 1px solid $border-light;

  .card-header-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }

  .card-icon {
    width: 40px;
    height: 40px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    background: $primary-lighter;
    color: $primary;
    flex-shrink: 0;
  }

  .card-titles {
    .card-title {
      font-size: $font-size-md;
      font-weight: $font-weight-semibold;
      color: $text-primary;
      margin: 0;
      line-height: 1.4;
    }

    .card-subtitle {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin: 2px 0 0 0;
    }
  }

  .card-header-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
}

// 内容区
.card-body {
  padding: $spacing-lg;

  &.no-padding {
    padding: 0;
  }
}

// 底部
.card-footer {
  padding: $spacing-md $spacing-lg;
  border-top: 1px solid $border-light;
  background: $bg-page;
}

// 角标
.card-badge {
  position: absolute;
  top: $spacing-md;
  right: $spacing-md;
}

// 选中态
.card-checked {
  position: absolute;
  top: 0;
  right: 0;
  width: 32px;
  height: 32px;
  background: var(--accent, $primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-radius: 0 $radius-lg 0 $radius-md;
}
</style>