<template>
  <div
    class="advanced-table"
    :class="{ 'is-loading': loading }"
  >
    <!-- 工具栏 -->
    <div
      v-if="showToolbar"
      class="table-toolbar"
    >
      <div class="toolbar-left">
        <!-- 批量选择提示 -->
        <transition name="fade">
          <div
            v-if="selectedCount > 0"
            class="batch-info"
          >
            <el-badge
              :value="selectedCount"
              type="primary"
            />
            <span class="batch-text">已选中 {{ selectedCount }} 项</span>
            <slot name="batch-actions">
              <el-button
                size="small"
                text
                @click="clearSelection"
              >
                清空
              </el-button>
            </slot>
          </div>
        </transition>
      </div>
      <div class="toolbar-right">
        <slot name="toolbar-actions" />
      </div>
    </div>

    <!-- 表格主体 -->
    <div
      class="table-wrapper"
      :class="{ 'is-bordered': bordered }"
    >
      <el-table
        ref="tableRef"
        :data="data"
        :columns="columns"
        v-bind="$attrs"
        @selection-change="handleSelectionChange"
        @sort-change="handleSortChange"
        @row-click="handleRowClick"
        v-on="$listeners"
      >
        <!-- 展开行 -->
        <el-table-column
          v-if="showExpand"
          type="expand"
        >
          <template #default="{ row }">
            <slot
              name="expand"
              :row="row"
            />
          </template>
        </el-table-column>

        <!-- 多选列 -->
        <el-table-column
          v-if="showSelection"
          type="selection"
          width="50"
        />

        <!-- 序号列 -->
        <el-table-column
          v-if="showIndex"
          type="index"
          label="序号"
          width="60"
          align="center"
        />

        <!-- 数据列 -->
        <el-table-column
          v-for="col in visibleColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
          :align="col.align || 'left'"
          :fixed="col.fixed"
          :sortable="col.sortable"
          :show-overflow-tooltip="col.showOverflow !== false"
        >
          <template #default="{ row }">
            <slot
              :name="`column-${col.prop}`"
              :row="row"
              :value="row[col.prop]"
            >
              <!-- 格式化器 -->
              <template v-if="col.formatter">
                {{ col.formatter(row, col) }}
              </template>
              <!-- 默认显示 -->
              <template v-else>
                {{ row[col.prop] }}
              </template>
            </slot>
          </template>

          <!-- 表头插槽 -->
          <template #header="{ column }">
            <slot
              :name="`header-${col.prop}`"
              :column="column"
            >
              {{ col.label }}
            </slot>
          </template>
        </el-table-column>

        <!-- 操作列 -->
        <el-table-column
          v-if="showActions"
          :label="actionsLabel || '操作'"
          :width="actionsWidth || 160"
          :fixed="actionsFixed || 'right'"
          align="center"
        >
          <template #default="{ row }">
            <slot
              name="actions"
              :row="row"
            />
          </template>
        </el-table-column>

        <!-- 空状态插槽 -->
        <template #empty>
          <slot name="empty">
            <EmptyState
              type="data"
              :title="emptyText || '暂无数据'"
              :description="emptyDescription"
              size="sm"
            />
          </slot>
        </template>
      </el-table>
    </div>

    <!-- 分页 -->
    <div
      v-if="showPagination"
      class="table-pagination"
    >
      <div class="pagination-info">
        <span>共 {{ total }} 条</span>
        <el-select 
          v-model="pageSize" 
          size="small" 
          style="width: 100px; margin-left: 16px;"
          @change="handlePageSizeChange"
        >
          <el-option
            :value="10"
            label="10 条/页"
          />
          <el-option
            :value="20"
            label="20 条/页"
          />
          <el-option
            :value="50"
            label="50 条/页"
          />
          <el-option
            :value="100"
            label="100 条/页"
          />
        </el-select>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        :background="true"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>

    <!-- Loading遮罩 -->
    <transition name="fade">
      <div
        v-if="loading"
        class="table-loading"
      >
        <div class="loading-content">
          <div class="loading-spinner" />
          <span>加载中...</span>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  // 数据
  data: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  // 加载状态
  loading: { type: Boolean, default: false },
  // 工具栏
  showToolbar: { type: Boolean, default: true },
  // 选择
  showSelection: { type: Boolean, default: false },
  showIndex: { type: Boolean, default: false },
  // 展开行
  showExpand: { type: Boolean, default: false },
  // 操作列
  showActions: { type: Boolean, default: true },
  actionsLabel: { type: String, default: '操作' },
  actionsWidth: { type: [Number, String], default: 160 },
  actionsFixed: { type: String, default: 'right' },
  // 分页
  showPagination: { type: Boolean, default: true },
  total: { type: Number, default: 0 },
  // 空状态
  emptyText: { type: String, default: '暂无数据' },
  emptyDescription: { type: String, default: '' },
  // 边框
  bordered: { type: Boolean, default: false }
})

const emit = defineEmits([
  'selection-change', 
  'sort-change', 
  'page-change', 
  'page-size-change',
  'row-click'
])

const tableRef = ref(null)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedRows = ref([])

const visibleColumns = computed(() => 
  props.columns.filter(col => col.visible !== false)
)

const selectedCount = computed(() => selectedRows.value.length)

// 选择变化
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
  emit('selection-change', selection)
}

// 排序变化
const handleSortChange = ({ prop, order }) => {
  emit('sort-change', { prop, order })
}

// 行点击
const handleRowClick = (row) => {
  emit('row-click', row)
}

// 分页
const handlePageChange = (page) => {
  currentPage.value = page
  emit('page-change', page)
}

const handlePageSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  emit('page-size-change', size)
}

// 清空选择
const clearSelection = () => {
  tableRef.value?.clearSelection()
}

// 选中行
const setCurrentRow = (row) => {
  tableRef.value?.setCurrentRow(row)
}

// 获取选中行
const getSelection = () => selectedRows.value

defineExpose({
  clearSelection,
  setCurrentRow,
  getSelection,
  refresh: () => tableRef.value?.clearSelection()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.advanced-table {
  position: relative;
  background: $bg-container;
  border-radius: $radius-lg;
  overflow: hidden;

  &.is-loading {
    .table-wrapper {
      opacity: 0.5;
      pointer-events: none;
    }
  }
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $border-light;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  .batch-info {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: 4px 12px;
    background: $primary-lighter;
    border-radius: $radius-pill;

    .batch-text {
      font-size: $font-size-sm;
      color: $primary;
      font-weight: $font-weight-medium;
    }
  }
}

.table-wrapper {
  &.is-bordered {
    border: 1px solid $border-light;
    border-radius: $radius-lg;
  }

  :deep(.el-table) {
    --el-table-border-color: #{$border-light};
    --el-table-header-bg-color: #{$bg-page};
    --el-table-row-hover-bg-color: #{rgba($primary, 0.04)};
    --el-table-header-text-color: #{$text-regular};
    --el-table-text-color: #{$text-primary};

    border-radius: 0;

    .el-table__header th {
      font-weight: $font-weight-semibold;
      font-size: $font-size-sm;
      background: $bg-page !important;
    }

    .el-table__cell {
      font-size: $font-size-sm;
      border-bottom: 1px solid $border-lighter;
    }

    .el-table__body tr {
      transition: all 0.15s;

      &:hover > td.el-table__cell {
        background-color: rgba($primary, 0.04) !important;
      }
    }

    // 展开行
    .el-table__expand-icon {
      color: $text-secondary;
      transition: transform 0.2s;

      &.expanded {
        transform: rotate(90deg);
      }
    }
  }
}

.table-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  border-top: 1px solid $border-light;

  .pagination-info {
    display: flex;
    align-items: center;
    font-size: $font-size-sm;
    color: $text-secondary;
  }

  :deep(.el-pagination) {
    .el-pager li {
      border-radius: $radius-md;
      min-width: 32px;
      height: 32px;
      line-height: 32px;

      &.is-active {
        background: $primary;
        color: #fff;
      }
    }
  }
}

// Loading遮罩
.table-loading {
  position: absolute;
  inset: 0;
  background: rgba($bg-container, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;

  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $spacing-md;

    .loading-spinner {
      width: 40px;
      height: 40px;
      border: 3px solid $border-light;
      border-top-color: $primary;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    span {
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

// 过渡动画
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>