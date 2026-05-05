<template>
  <div class="empty-state" :class="[size]">
    <!-- SVG插画 -->
    <div class="empty-illustration">
      <svg v-if="type === 'data'" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="30" y="80" width="140" height="60" rx="8" fill="#f0f2f5"/>
        <rect x="30" y="60" width="140" height="20" rx="4" fill="#e5e7eb"/>
        <circle cx="100" cy="100" r="20" fill="#d1d5db"/>
        <path d="M90 100L100 90L110 100L100 110L90 100Z" fill="white"/>
        <rect x="50" y="40" width="20" height="30" rx="2" fill="#e5e7eb"/>
        <rect x="80" y="30" width="20" height="40" rx="2" fill="#d1d5db"/>
        <rect x="110" y="35" width="20" height="35" rx="2" fill="#e5e7eb"/>
        <rect x="140" y="45" width="20" height="25" rx="2" fill="#d1d5db"/>
      </svg>
      
      <svg v-else-if="type === 'search'" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="80" cy="70" r="40" fill="#f0f2f5"/>
        <circle cx="80" cy="70" r="30" stroke="#d1d5db" stroke-width="4" fill="none"/>
        <line x1="105" y1="95" x2="130" y2="120" stroke="#d1d5db" stroke-width="6" stroke-linecap="round"/>
        <circle cx="80" cy="70" r="10" fill="#165dff" opacity="0.3"/>
        <rect x="40" y="130" width="80" height="8" rx="4" fill="#e5e7eb"/>
        <rect x="50" y="145" width="60" height="6" rx="3" fill="#f0f2f5"/>
      </svg>
      
      <svg v-else-if="type === 'chat'" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="40" y="30" width="120" height="80" rx="12" fill="#f0f2f5"/>
        <path d="M60 50H140" stroke="#e5e7eb" stroke-width="6" stroke-linecap="round"/>
        <path d="M60 70H120" stroke="#d1d5db" stroke-width="6" stroke-linecap="round"/>
        <path d="M60 90H100" stroke="#e5e7eb" stroke-width="6" stroke-linecap="round"/>
        <circle cx="145" cy="125" r="25" fill="#165dff" opacity="0.1"/>
        <circle cx="145" cy="125" r="15" fill="#165dff" opacity="0.2"/>
        <path d="M140 120L145 125L150 120" stroke="#165dff" stroke-width="2" stroke-linecap="round"/>
        <path d="M145 125V130" stroke="#165dff" stroke-width="2" stroke-linecap="round"/>
      </svg>
      
      <svg v-else-if="type === 'file'" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="60" y="20" width="80" height="100" rx="8" fill="#f0f2f5"/>
        <rect x="70" y="30" width="60" height="80" rx="4" fill="white" stroke="#e5e7eb" stroke-width="2"/>
        <path d="M100 20V40H130" fill="#e5e7eb"/>
        <path d="M100 20L130 40H100V20Z" fill="#d1d5db"/>
        <rect x="80" y="50" width="40" height="4" rx="2" fill="#e5e7eb"/>
        <rect x="80" y="60" width="35" height="4" rx="2" fill="#f0f2f5"/>
        <rect x="80" y="70" width="40" height="4" rx="2" fill="#e5e7eb"/>
        <rect x="80" y="80" width="30" height="4" rx="2" fill="#f0f2f5"/>
      </svg>
      
      <svg v-else-if="type === 'alert'" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="100" cy="80" r="50" fill="#fff7e6"/>
        <path d="M100 45L130 110H70L100 45Z" fill="#ff9d00" opacity="0.3"/>
        <path d="M100 45L130 110H70L100 45Z" stroke="#ff7d00" stroke-width="4" fill="none"/>
        <circle cx="100" cy="90" r="8" fill="#ff7d00"/>
        <line x1="100" y1="98" x2="100" y2="105" stroke="#ff7d00" stroke-width="4" stroke-linecap="round"/>
        <rect x="60" y="140" width="80" height="8" rx="4" fill="#f0f2f5"/>
      </svg>
      
      <svg v-else-if="type === 'success'" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="100" cy="80" r="50" fill="#e8ffea"/>
        <circle cx="100" cy="80" r="40" stroke="#00b42a" stroke-width="4" fill="none"/>
        <path d="M80 80L95 95L120 65" stroke="#00b42a" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
        <rect x="50" y="140" width="100" height="8" rx="4" fill="#f0f2f5"/>
      </svg>
      
      <svg v-else viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="40" y="30" width="120" height="100" rx="12" fill="#f0f2f5"/>
        <circle cx="100" cy="70" r="25" fill="#e5e7eb"/>
        <rect x="70" y="100" width="60" height="8" rx="4" fill="#d1d5db"/>
        <rect x="80" y="115" width="40" height="6" rx="3" fill="#e5e7eb"/>
      </svg>
    </div>

    <!-- 文字内容 -->
    <div class="empty-content">
      <h3 class="empty-title">{{ title || '暂无数据' }}</h3>
      <p class="empty-desc">{{ description || '当前没有内容，请稍后再试' }}</p>
      
      <div class="empty-actions" v-if="$slots.actions || actionText">
        <slot name="actions">
          <el-button
            v-if="actionText"
            :type="actionType"
            @click="$emit('action')"
          >
            {{ actionText }}
          </el-button>
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  actionText: { type: String, default: '' },
  actionType: { type: String, default: 'primary' },
  type: { 
    type: String, 
    default: 'default',
    validator: (v) => ['default', 'data', 'search', 'chat', 'file', 'alert', 'success'].includes(v)
  },
  size: {
    type: String,
    default: 'medium',
    validator: (v) => ['small', 'medium', 'large'].includes(v)
  }
})

defineEmits(['action'])
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.empty-state {
  @include flex-center;
  flex-direction: column;
  padding: $space-10 0;
  text-align: center;

  &.small {
    .empty-illustration svg {
      width: 120px;
      height: 96px;
    }
    
    .empty-title {
      font-size: $font-size-base;
    }
  }

  &.large {
    .empty-illustration svg {
      width: 200px;
      height: 160px;
    }
    
    .empty-title {
      font-size: $font-size-xl;
    }
  }
}

.empty-illustration {
  margin-bottom: $space-6;
  
  svg {
    width: 160px;
    height: 128px;
    animation: fadeInUp 0.6s ease-out;
    
    path, rect, circle, line {
      animation: float 3s ease-in-out infinite;
    }
  }
}

.empty-content {
  max-width: 400px;
}

.empty-title {
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: $text-primary;
  margin: 0 0 $space-2 0;
}

.empty-desc {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin: 0 0 $space-6 0;
  line-height: 1.6;
}

.empty-actions {
  margin-top: $space-4;
}
</style>