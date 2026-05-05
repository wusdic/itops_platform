<template>
  <div class="data-table">
    <!-- 工具栏 -->
    <div class="table-toolbar" v-if="$slots.toolbar || showSearch || showRefresh">
      <div class="toolbar-left">
        <slot name="toolbar"></slot>
      </div>
      <div class="toolbar-right">
        <el-input
          v-if="showSearch"
          v-model="searchKeyword"
          :placeholder="searchPlaceholder"
          class="search-input"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
          @input="handleSearchInput"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button
          v-if="showRefresh"
          :icon="Refresh"
          @click="handleRefresh"
          :loading="loading"
        />
      </div>
    </div>

    <!-- 表格主体 -->
    <el-table
      ref="tableRef"
      :data="tableData"
      :loading="loading"
      :stripe="stripe"
      :border="border"
      :size="size"
      :row-key="rowKey"
      :height="height"
      :max-height="maxHeight"
      :selection="selection"
      @selection-change="handleSelectionChange"
      @sort-change="handleSortChange"
      @row-click="handleRowClick"
      class="main-table"
      v-bind="$attrs"
    >
      <!-- 选择列 -->
      <el-table-column
        v-if="selection"
        type="selection"
        width="55"
        :selectable="selectable"
      />

      <!-- 序号列 -->
      <el-table-column
        v-if="showIndex"
        type="index"
        label="序号"
        width="60"
        :index="indexMethod"
        align="center"
      />

      <!-- 表格列 -->
      <slot></slot>

      <!-- 默认插槽（用于传入 el-table-column） -->
    </el-table>

    <!-- 空状态 -->
    <div class="empty-state" v-if="!loading && tableData.length === 0">
      <el-empty :description="emptyText" :image-size="120">
        <template #image>
          <div class="empty-icon">
            <el-icon><Document /></el-icon>
          </div>
        </template>
        <slot name="empty"></slot>
      </el-empty>
    </div>

    <!-- 分页 -->
    <div class="table-pagination" v-if="showPagination && total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="pageSizes"
        :total="total"
        :layout="paginationLayout"
        :background="true"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, toRef } from 'vue'
import { Search, Refresh, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  // 数据
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  
  // 分页
  showPagination: { type: Boolean, default: true },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 10 },
  pageSizes: { type: Array, default: () => [10, 20, 50, 100] },
  total: { type: Number, default: 0 },
  paginationLayout: { type: String, default: 'total, sizes, prev, pager, next, jumper' },
  
  // 搜索
  showSearch: { type: Boolean, default: false },
  searchPlaceholder: { type: String, default: '搜索...' },
  searchDelay: { type: Number, default: 300 },
  
  // 功能
  showRefresh: { type: Boolean, default: true },
  showIndex: { type: Boolean, default: false },
  stripe: { type: Boolean, default: true },
  border: { type: Boolean, default: false },
  selection: { type: Boolean, default: false },
  selectable: { type: Function, default: () => true },
  rowKey: { type: String, default: 'id' },
  height: { type: [String, Number], default: null },
  maxHeight: { type: [String, Number], default: null },
  size: { type: String, default: 'default' },
  emptyText: { type: String, default: '暂无数据' },
  
  // 搜索字段配置
  searchFields: { type: Array, default: () => [] }
})

const emit = defineEmits([
  'update:page',
  'update:pageSize',
  'search',
  'refresh',
  'selection-change',
  'sort-change',
  'row-click',
  'page-change',
  'size-change'
])

// Refs
const tableRef = ref(null)
const tableData = ref([])
const searchKeyword = ref('')
const currentPage = ref(props.page)
const pageSize = ref(props.pageSize)

// Watch 数据
watch(() => props.data, (val) => {
  tableData.value = val || []
}, { immediate: true })

// 搜索防抖
let searchTimer = null
const handleSearchInput = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    handleSearch()
  }, props.searchDelay)
}

// 搜索
const handleSearch = () => {
  emit('search', searchKeyword.value)
}

// 刷新
const handleRefresh = () => {
  emit('refresh')
}

// 分页
const handlePageChange = (page) => {
  currentPage.value = page
  emit('update:page', page)
  emit('page-change', page)
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  emit('update:pageSize', size)
  emit('size-change', size)
}

// 选择
const handleSelectionChange = (selection) => {
  emit('selection-change', selection)
}

// 排序
const handleSortChange = ({ prop, order }) => {
  emit('sort-change', { prop, order })
}

// 行点击
const handleRowClick = (row) => {
  emit('row-click', row)
}

// 序号
const indexMethod = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 暴露方法
defineExpose({
  tableRef,
  refresh: () => emit('refresh'),
  clearSelection: () => tableRef.value?.clearSelection(),
  toggleRowSelection: (row, selected) => tableRef.value?.toggleRowSelection(row, selected)
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.data-table {
  display: flex;
  flex-direction: column;
  height: 100%;
}

// ========== 工具栏 ==========
.table-toolbar {
  @include flex-between;
  margin-bottom: $spacing-md;
  gap: $spacing-md;

  .toolbar-left {
    display: flex;
    gap: $spacing-sm;
    flex-wrap: wrap;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  .search-input {
    width: 260px;
  }
}

// ========== 表格 ==========
.main-table {
  flex: 1;
  border-radius: $border-radius-md;
  overflow: hidden;

  :deep(.el-table__header th) {
    background: $bg-page !important;
    font-weight: $font-weight-medium;
    color: $text-regular;
  }

  :deep(.el-table__row) {
    transition: background 0.15s ease;
    
    &:hover > td {
      background: rgba($primary, 0.04) !important;
    }
  }

  :deep(.el-table__cell) {
    padding: 12px 0;
  }

  :deep(.el-table__empty-text) {
    padding: $spacing-xxl 0;
  }
}

// ========== 空状态 ==========
.empty-state {
  padding: $spacing-xxxl 0;

  .empty-icon {
    width: 80px;
    height: 80px;
    background: $bg-page;
    border-radius: 50%;
    @include flex-center;
    font-size: 36px;
    color: $text-placeholder;
    margin: 0 auto;
  }
}

// ========== 分页 ==========
.table-pagination {
  margin-top: $spacing-lg;
  @include flex-center;
  justify-content: flex-end;
}
</style>