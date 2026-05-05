<template>
  <div class="page-header" :class="{ 'has-tabs': tabs.length > 0 }">
    <!-- 标题区 -->
    <div class="header-left">
      <div class="header-title">
        <h1 class="title">{{ title }}</h1>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
      </div>
      <div class="header-tags" v-if="$slots.tags">
        <slot name="tags"></slot>
      </div>
    </div>

    <!-- 操作区 -->
    <div class="header-right" v-if="$slots.actions || actions.length > 0">
      <slot name="actions">
        <el-button
          v-for="action in actions"
          :key="action.label"
          :type="action.type || 'default'"
          :icon="action.icon"
          :loading="action.loading"
          @click="action.handler"
        >
          {{ action.label }}
        </el-button>
      </slot>
    </div>

    <!-- 标签页 -->
    <div class="header-tabs" v-if="tabs.length > 0">
      <div class="tabs-nav">
        <div
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-item"
          :class="{ active: activeTab === tab.key }"
          @click="handleTabClick(tab)"
        >
          <el-icon v-if="tab.icon" :size="16"><component :is="tab.icon" /></el-icon>
          <span>{{ tab.label }}</span>
          <el-badge
            v-if="tab.badge"
            :value="tab.badge"
            :type="tab.badgeType || 'primary'"
            :hidden="tab.badge === 0"
          />
        </div>
      </div>
    </div>

    <!-- 快捷搜索 -->
    <div class="header-quick-search" v-if="showSearch">
      <el-input
        v-model="quickSearch"
        placeholder="快捷搜索... (⌘K)"
        size="small"
        clearable
        @keyup="handleQuickSearch"
        @focus="showSearchPanel = true"
        @blur="handleSearchBlur"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  tabs: { type: Array, default: () => [] },
  activeTab: { type: String, default: '' },
  actions: { type: Array, default: () => [] },
  showSearch: { type: Boolean, default: true }
})

const emit = defineEmits(['tab-change', 'search', 'action'])

const quickSearch = ref('')
const showSearchPanel = ref(false)

const handleTabClick = (tab) => {
  emit('tab-change', tab.key)
}

const handleQuickSearch = () => {
  if (quickSearch.value.length > 0) {
    emit('search', quickSearch.value)
  }
}

const handleSearchBlur = () => {
  setTimeout(() => {
    showSearchPanel.value = false
  }, 200)
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.page-header {
  @include flex-between;
  padding: $space-6 $space-8;
  background: $bg-container;
  border-bottom: 1px solid $border-light;
  position: relative;

  &.has-tabs {
    flex-direction: column;
    align-items: flex-start;
    gap: $space-4;
  }
}

.header-left {
  @include flex-start;
  gap: $space-4;
  flex: 1;
}

.header-title {
  .title {
    font-size: $font-size-xxl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0;
    line-height: 1.3;
  }

  .subtitle {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin: $space-1 0 0 0;
  }
}

.header-tags {
  @include flex-start;
  gap: $space-2;
}

.header-right {
  @include flex-start;
  gap: $space-3;

  .el-button {
    font-weight: $font-weight-medium;
  }
}

.header-tabs {
  width: 100%;
  margin-top: $space-4;
  border-top: 1px solid $border-lighter;
  padding-top: $space-4;
}

.tabs-nav {
  display: flex;
  gap: $space-2;
  flex-wrap: wrap;
}

.tab-item {
  @include flex-center;
  gap: $space-2;
  padding: $space-2 $space-4;
  border-radius: $radius-md;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: $text-secondary;
  cursor: pointer;
  transition: $transition-fast;
  background: $bg-page;
  border: 1px solid transparent;

  &:hover {
    color: $primary;
    background: $primary-lighter;
  }

  &.active {
    color: $primary;
    background: $primary-lighter;
    border-color: rgba($primary, 0.2);
  }
}

.header-quick-search {
  position: absolute;
  right: $space-8;
  top: 50%;
  transform: translateY(-50%);

  .el-input {
    width: 240px;
  }
}
</style>