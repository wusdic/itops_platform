<template>
  <div
    class="filter-bar"
    :class="{ 'is-compact': compact }"
  >
    <!-- 左侧：筛选条件 -->
    <div class="filter-left">
      <!-- 搜索框 -->
      <div
        v-if="showSearch"
        class="filter-search"
      >
        <el-input
          v-model="searchKeyword"
          :placeholder="searchPlaceholder"
          clearable
          @clear="handleSearchClear"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 快速筛选标签 -->
      <div
        v-if="quickFilters.length"
        class="filter-tags"
      >
        <el-radio-group 
          v-model="activeQuickFilter" 
          size="small"
          @change="handleQuickFilterChange"
        >
          <el-radio-button 
            v-for="filter in quickFilters" 
            :key="filter.value"
            :value="filter.value"
          >
            {{ filter.label }}
            <span
              v-if="filter.count !== undefined"
              class="filter-count"
            >({{ filter.count }})</span>
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 筛选下拉 -->
      <slot name="filters" />
    </div>

    <!-- 右侧：操作按钮 -->
    <div class="filter-right">
      <!-- 视图切换 -->
      <div
        v-if="showViewSwitch"
        class="view-switch"
      >
        <el-radio-group
          v-model="viewMode"
          size="small"
        >
          <el-radio-button value="table">
            <el-icon><Grid /></el-icon>
          </el-radio-button>
          <el-radio-button value="card">
            <el-icon><Menu /></el-icon>
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 刷新按钮 -->
      <el-tooltip
        v-if="showRefresh"
        content="刷新数据"
        placement="bottom"
      >
        <el-button 
          :icon="Refresh" 
          circle 
          size="small"
          :loading="refreshing"
          @click="handleRefresh"
        />
      </el-tooltip>

      <!-- 批量操作 -->
      <slot name="actions" />

      <!-- 新增按钮 -->
      <slot name="append" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Search, Refresh, Grid, Menu } from '@element-plus/icons-vue'

const props = defineProps({
  // 搜索
  showSearch: { type: Boolean, default: true },
  searchPlaceholder: { type: String, default: '搜索...' },
  // 快速筛选
  quickFilters: { type: Array, default: () => [] },
  // 视图切换
  showViewSwitch: { type: Boolean, default: false },
  // 刷新
  showRefresh: { type: Boolean, default: true },
  // 紧凑模式
  compact: { type: Boolean, default: false }
})

const emit = defineEmits(['search', 'refresh', 'filter-change', 'view-change'])

const searchKeyword = ref('')
const activeQuickFilter = ref('')
const viewMode = ref('table')
const refreshing = ref(false)

// 搜索
const handleSearch = () => {
  emit('search', searchKeyword.value)
}

const handleSearchClear = () => {
  emit('search', '')
}

// 快速筛选
const handleQuickFilterChange = (value) => {
  emit('filter-change', { quickFilter: value })
}

// 刷新
const handleRefresh = async () => {
  refreshing.value = true
  emit('refresh')
  setTimeout(() => {
    refreshing.value = false
  }, 1000)
}

// 视图切换
watch(viewMode, (val) => {
  emit('view-change', val)
})

// 暴露方法
defineExpose({
  setLoading: (val) => { refreshing.value = val },
  clearSearch: () => { 
    searchKeyword.value = ''
    activeQuickFilter.value = ''
  }
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-xl;
  background: $bg-container;
  border-radius: $radius-lg;
  margin-bottom: $spacing-lg;
  border: 1px solid $border-light;
  gap: $spacing-md;
  transition: all 0.2s;

  &.is-compact {
    padding: $spacing-sm $spacing-md;

    .filter-left {
      gap: $spacing-sm;
    }

    .filter-right {
      gap: $spacing-xs;
    }
  }

  &:hover {
    border-color: $primary-lighter;
    box-shadow: 0 2px 8px rgba($primary, 0.08);
  }
}

.filter-left {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  flex-wrap: wrap;
  flex: 1;
}

.filter-search {
  width: 280px;

  :deep(.el-input__wrapper) {
    border-radius: $radius-md;
    transition: all 0.2s;

    &:hover, &.is-focus {
      box-shadow: 0 0 0 2px rgba($primary, 0.1);
    }
  }
}

.filter-tags {
  :deep(.el-radio-group) {
    display: flex;
    flex-wrap: nowrap;
  }

  :deep(.el-radio-button) {
    .el-radio-button__inner {
      border-radius: $radius-md;
      border-left: 1px solid $border;
      font-weight: $font-weight-medium;
      transition: all 0.15s;

      &:hover {
        color: $primary;
      }
    }

    &.is-active .el-radio-button__inner {
      background: $primary;
      border-color: $primary;
      color: #fff;
    }
  }

  .filter-count {
    opacity: 0.7;
    font-size: 0.9em;
    margin-left: 2px;
  }
}

.filter-right {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-shrink: 0;
}

.view-switch {
  :deep(.el-radio-group) {
    :deep(.el-radio-button__inner) {
      padding: 6px 10px;

      .el-icon {
        font-size: 14px;
      }
    }
  }
}

.divider {
  width: 1px;
  height: 24px;
  background: $border-light;
  margin: 0 $spacing-xs;
}
</style>