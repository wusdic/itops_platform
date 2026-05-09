<template>
  <div class="workorder-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">
          工单管理
        </h2>
        <p class="page-subtitle">
          IT运维工单全生命周期管理，支持创建、处理、跟踪和统计
        </p>
      </div>
      <div class="page-header-actions">
        <el-button @click="handleExport">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button
          type="primary"
          @click="showCreateDialog = true"
        >
          <el-icon><Plus /></el-icon>
          创建工单
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div 
        v-for="(stat, index) in statsData" 
        :key="stat.key"
        class="stat-card"
        :style="{ animationDelay: `${index * 0.08}s` }"
      >
        <div
          class="stat-icon"
          :class="stat.key"
        >
          <el-icon><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ stat.value }}
          </div>
          <div class="stat-title">
            {{ stat.title }}
          </div>
        </div>
        <div
          v-if="stat.growth"
          class="stat-growth"
          :class="stat.growth > 0 ? 'up' : 'down'"
        >
          <el-icon><ArrowUp /></el-icon>
          {{ Math.abs(stat.growth) }}%
        </div>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-input
          v-model="searchText"
          placeholder="搜索工单标题、描述..."
          style="width: 260px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button @click="handleSearch" />
          </template>
        </el-input>

        <el-select
          v-model="categoryFilter"
          placeholder="工单分类"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="故障报修"
            value="fault"
          />
          <el-option
            label="变更申请"
            value="change"
          />
          <el-option
            label="需求处理"
            value="requirement"
          />
          <el-option
            label="咨询服务"
            value="consult"
          />
        </el-select>

        <el-select
          v-model="priorityFilter"
          placeholder="优先级"
          style="width: 120px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="紧急"
            value="urgent"
          />
          <el-option
            label="高"
            value="high"
          />
          <el-option
            label="中"
            value="medium"
          />
          <el-option
            label="低"
            value="low"
          />
        </el-select>

        <el-select
          v-model="statusFilter"
          placeholder="处理状态"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="待处理"
            value="pending"
          />
          <el-option
            label="处理中"
            value="processing"
          />
          <el-option
            label="待验收"
            value="pending_approval"
          />
          <el-option
            label="已完成"
            value="completed"
          />
          <el-option
            label="已关闭"
            value="closed"
          />
        </el-select>

        <el-select
          v-model="assignFilter"
          placeholder="处理人"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="我"
            value="me"
          />
          <el-option
            label="未分配"
            value="unassigned"
          />
        </el-select>
      </div>

      <div class="filter-right">
        <el-radio-group
          v-model="viewMode"
          size="small"
        >
          <el-radio-button value="list">
            <el-icon><List /></el-icon>
          </el-radio-button>
          <el-radio-button value="card">
            <el-icon><Grid /></el-icon>
          </el-radio-button>
        </el-radio-group>
        <el-divider direction="vertical" />
        <el-button
          text
          :loading="loading"
          @click="handleRefresh"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 看板视图 -->
    <div
      v-if="viewMode === 'card'"
      class="kanban-board"
    >
      <div
        v-for="status in kanbanStatus"
        :key="status.key"
        class="kanban-column"
      >
        <div class="kanban-header">
          <span class="kanban-title">{{ status.title }}</span>
          <el-badge
            :value="getKanbanCount(status.key)"
            type="info"
          />
        </div>
        <div class="kanban-cards">
          <div 
            v-for="order in getKanbanOrders(status.key)" 
            :key="order.id"
            class="kanban-card"
            :class="order.priority"
            @click="handleViewDetail(order)"
          >
            <div class="card-header">
              <el-tag
                size="small"
                :type="getCategoryTagType(order.category)"
                effect="light"
              >
                {{ getCategoryText(order.category) }}
              </el-tag>
              <el-tag
                size="small"
                :type="getPriorityTagType(order.priority)"
                effect="dark"
              >
                {{ getPriorityText(order.priority) }}
              </el-tag>
            </div>
            <div class="card-title">
              {{ order.title }}
            </div>
            <div class="card-sn">
              工单号: {{ order.sn }}
            </div>
            <div class="card-meta">
              <span class="meta-item">
                <el-icon><User /></el-icon>
                {{ order.creator }}
              </span>
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ order.createTime }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 列表视图 -->
    <div
      v-else
      class="table-card"
    >
      <el-table
        v-loading="loading"
        :data="ordersData"
        stripe
        class="orders-table"
        row-key="id"
        @row-click="handleRowClick"
      >
        <el-table-column
          label="工单号"
          width="140"
        >
          <template #default="{ row }">
            <span class="order-sn">{{ row.sn }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="标题"
          min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <div class="title-cell">
              <span class="order-title">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="分类"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getCategoryTagType(row.category)"
              effect="light"
            >
              {{ getCategoryText(row.category) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="优先级"
          width="90"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getPriorityTagType(row.priority)"
              effect="dark"
            >
              {{ getPriorityText(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <div class="status-cell">
              <span
                class="status-dot"
                :class="row.status"
              />
              <el-tag
                size="small"
                :type="getStatusTagType(row.status)"
                effect="light"
              >
                {{ getStatusText(row.status) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="处理人"
          width="110"
        >
          <template #default="{ row }">
            <span class="assignee-text">{{ row.assignee || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="创建人"
          width="110"
        >
          <template #default="{ row }">
            <span class="creator-text">{{ row.creator }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="创建时间"
          width="160"
          sortable
        >
          <template #default="{ row }">
            <span class="time-text">{{ row.createTime }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="SLA"
          width="100"
        >
          <template #default="{ row }">
            <span
              class="sla-text"
              :class="{ 'sla-warning': isSLAWarning(row) }"
            >
              {{ row.slaRemaining }}
            </span>
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="180"
          fixed="right"
        >
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip
                content="查看详情"
                placement="top"
              >
                <el-button
                  text
                  type="primary"
                  size="small"
                  @click.stop="handleViewDetail(row)"
                >
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                v-if="row.status !== 'completed' && row.status !== 'closed'"
                content="处理工单"
                placement="top"
              >
                <el-button
                  text
                  type="primary"
                  size="small"
                  @click.stop="handleProcess(row)"
                >
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                content="添加评论"
                placement="top"
              >
                <el-button
                  text
                  size="small"
                  @click.stop="handleComment(row)"
                >
                  <el-icon><Comment /></el-icon>
                </el-button>
              </el-tooltip>
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleOrderCommand(cmd, row)"
                @click.stop
              >
                <el-button
                  text
                  size="small"
                >
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item command="transfer">
                      转移
                    </el-dropdown-item>
                    <el-dropdown-item command="close">
                      关闭工单
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="delete"
                      divided
                    >
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="table-footer">
        <div class="table-info">
          共 {{ total }} 条记录，待处理 {{ pendingCount }} 条
        </div>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="sizes, prev, pager, next, total"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 创建工单对话框 -->
    <el-dialog 
      v-model="showCreateDialog" 
      title="创建工单" 
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="orderFormRef"
        :model="orderForm"
        label-width="100px"
        :rules="formRules"
      >
        <el-form-item
          label="工单标题"
          prop="title"
        >
          <el-input
            v-model="orderForm.title"
            placeholder="请输入工单标题"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item
          label="工单分类"
          prop="category"
        >
          <el-select
            v-model="orderForm.category"
            placeholder="请选择工单分类"
            style="width: 100%"
          >
            <el-option
              label="故障报修"
              value="fault"
            />
            <el-option
              label="变更申请"
              value="change"
            />
            <el-option
              label="需求处理"
              value="requirement"
            />
            <el-option
              label="咨询服务"
              value="consult"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="优先级"
          prop="priority"
        >
          <el-radio-group v-model="orderForm.priority">
            <el-radio label="urgent">
              紧急
            </el-radio>
            <el-radio label="high">
              高
            </el-radio>
            <el-radio label="medium">
              中
            </el-radio>
            <el-radio label="low">
              低
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          label="关联设备"
          prop="asset"
        >
          <el-select 
            v-model="orderForm.asset" 
            placeholder="选择关联设备（可选）" 
            style="width: 100%"
            filterable
            clearable
          >
            <el-option 
              v-for="asset in assetList" 
              :key="asset.id" 
              :label="`${asset.name} (${asset.ip})`" 
              :value="asset.id" 
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="处理人"
          prop="assignee"
        >
          <el-select
            v-model="orderForm.assignee"
            placeholder="选择处理人"
            style="width: 100%"
          >
            <el-option
              label="张三"
              value="张三"
            />
            <el-option
              label="李四"
              value="李四"
            />
            <el-option
              label="王五"
              value="王五"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="工单描述"
          prop="description"
        >
          <el-input 
            v-model="orderForm.description" 
            type="textarea" 
            :rows="6" 
            placeholder="请详细描述工单内容，包括故障现象、影响范围等"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="附件">
          <el-upload
            drag
            :auto-upload="false"
            :limit="5"
            accept=".jpg,.png,.pdf,.doc,.docx"
          >
            <el-icon><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽文件或点击上传
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 jpg/png/pdf/doc/docx 格式，单个文件不超过10MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSubmitOrder"
        >
          提交工单
        </el-button>
      </template>
    </el-dialog>

    <!-- 工单详情抽屉 -->
    <el-drawer
      v-model="showDetailDrawer"
      :title="`工单详情 - ${currentOrder?.sn}`"
      size="700px"
    >
      <div
        v-if="currentOrder"
        class="order-detail"
      >
        <div class="detail-header">
          <div class="detail-badges">
            <el-tag
              :type="getCategoryTagType(currentOrder.category)"
              size="large"
            >
              {{ getCategoryText(currentOrder.category) }}
            </el-tag>
            <el-tag
              :type="getPriorityTagType(currentOrder.priority)"
              size="large"
              effect="dark"
            >
              {{ getPriorityText(currentOrder.priority) }}
            </el-tag>
            <el-tag
              :type="getStatusTagType(currentOrder.status)"
              size="large"
            >
              {{ getStatusText(currentOrder.status) }}
            </el-tag>
          </div>
          <h3 class="detail-title">
            {{ currentOrder.title }}
          </h3>
        </div>

        <el-descriptions
          :column="2"
          border
          class="detail-descriptions"
        >
          <el-descriptions-item label="工单编号">
            {{ currentOrder.sn }}
          </el-descriptions-item>
          <el-descriptions-item label="SLA剩余时间">
            <span :class="{ 'sla-warning': isSLAWarning(currentOrder) }">
              {{ currentOrder.slaRemaining }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="创建人">
            {{ currentOrder.creator }}
          </el-descriptions-item>
          <el-descriptions-item label="处理人">
            {{ currentOrder.assignee || '未分配' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ currentOrder.createTime }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ currentOrder.updateTime }}
          </el-descriptions-item>
          <el-descriptions-item
            label="关联资产"
            :span="2"
          >
            {{ currentOrder.assetName || '无' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">
          工单描述
        </el-divider>
        <div class="detail-description">
          {{ currentOrder.description }}
        </div>

        <el-divider content-position="left">
          处理记录
        </el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="(item, index) in currentOrder.processes"
            :key="index"
            :timestamp="item.time"
            :type="item.type"
          >
            <div class="process-item">
              <p class="process-action">
                {{ item.action }}
              </p>
              <p class="process-detail">
                {{ item.detail }}
              </p>
              <p class="process-operator">
                {{ item.operator }}
              </p>
            </div>
          </el-timeline-item>
        </el-timeline>

        <el-divider content-position="left">
          评论
        </el-divider>
        <div class="comments-section">
          <div v-if="currentOrder.comments && currentOrder.comments.length > 0">
            <div
              v-for="(comment, index) in currentOrder.comments"
              :key="index"
              class="comment-item"
            >
              <div class="comment-avatar">
                <el-avatar
                  :size="32"
                  :icon="UserFilled"
                />
              </div>
              <div class="comment-content">
                <div class="comment-header">
                  <span class="comment-author">{{ comment.author }}</span>
                  <span class="comment-time">{{ comment.time }}</span>
                </div>
                <div class="comment-text">
                  {{ comment.text }}
                </div>
              </div>
            </div>
          </div>
          <div
            v-else
            class="no-comments"
          >
            暂无评论
          </div>
        </div>

        <div class="comment-input-section">
          <el-input
            v-model="commentText"
            type="textarea"
            :rows="3"
            placeholder="添加评论..."
          />
          <el-button
            type="primary"
            style="margin-top: 10px;"
            @click="handleAddComment"
          >
            发表评论
          </el-button>
        </div>

        <el-divider content-position="left">
          操作
        </el-divider>
        <div class="detail-actions">
          <el-button
            v-if="currentOrder.status !== 'completed' && currentOrder.status !== 'closed'"
            type="primary"
            @click="handleProcess(currentOrder)"
          >
            处理工单
          </el-button>
          <el-button @click="handleTransfer(currentOrder)">
            转移工单
          </el-button>
          <el-button
            v-if="currentOrder.status !== 'completed' && currentOrder.status !== 'closed'"
            type="success"
            @click="handleComplete(currentOrder)"
          >
            完成工单
          </el-button>
          <el-button @click="handleClose(currentOrder)">
            关闭工单
          </el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 处理工单对话框 -->
    <el-dialog
      v-model="showProcessDialog"
      title="处理工单"
      width="600px"
    >
      <el-form
        :model="processForm"
        label-width="100px"
      >
        <el-form-item label="处理结果">
          <el-radio-group v-model="processForm.result">
            <el-radio label="resolved">
              已解决
            </el-radio>
            <el-radio label="in_progress">
              进行中
            </el-radio>
            <el-radio label="need_info">
              需要更多信息
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理说明">
          <el-input 
            v-model="processForm.description" 
            type="textarea" 
            :rows="5" 
            placeholder="请输入处理说明" 
          />
        </el-form-item>
        <el-form-item label="转交处理人">
          <el-select
            v-model="processForm.assignee"
            placeholder="选择处理人"
            style="width: 100%"
            clearable
          >
            <el-option
              label="张三"
              value="张三"
            />
            <el-option
              label="李四"
              value="李四"
            />
            <el-option
              label="王五"
              value="王五"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProcessDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSubmitProcess"
        >
          提交处理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Download, Plus, List, Grid, View, Edit, Comment, MoreFilled,
  UploadFilled, Clock, User, UserFilled, ArrowUp, Ticket, Timer, CircleCheck, Warning
} from '@element-plus/icons-vue'
import { workorder } from '@/api'

// 状态
const loading = ref(false)
const submitLoading = ref(false)
const ordersData = ref([])
const showCreateDialog = ref(false)
const showDetailDrawer = ref(false)
const showProcessDialog = ref(false)
const viewMode = ref('list')
const currentOrder = ref(null)
const orderFormRef = ref(null)
const commentText = ref('')

// 筛选
const searchText = ref('')
const categoryFilter = ref('')
const priorityFilter = ref('')
const statusFilter = ref('')
const assignFilter = ref('')

// 分页
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 工单表单
const orderForm = reactive({
  title: '',
  category: 'fault',
  priority: 'medium',
  asset: '',
  assignee: '',
  description: ''
})

// 处理表单
const processForm = reactive({
  result: 'in_progress',
  description: '',
  assignee: ''
})

// 表单验证
const formRules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择工单分类', trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  description: [{ required: true, message: '请输入工单描述', trigger: 'blur' }]
}

// 设备列表
const assetList = ref([
  { id: 1, name: 'Web服务器01', ip: '192.168.1.101' },
  { id: 2, name: '数据库服务器', ip: '192.168.1.102' },
  { id: 3, name: '存储服务器', ip: '192.168.1.103' }
])

// 看板状态
const kanbanStatus = [
  { key: 'pending', title: '待处理' },
  { key: 'processing', title: '处理中' },
  { key: 'pending_approval', title: '待验收' },
  { key: 'completed', title: '已完成' }
]

// 统计
const statsData = reactive([
  { key: 'pending', title: '待处理', value: 0, icon: 'Ticket', growth: 0 },
  { key: 'processing', title: '处理中', value: 0, icon: 'Clock', growth: 12 },
  { key: 'completed', title: '本月完成', value: 0, icon: 'CircleCheck', growth: 8 },
  { key: 'overdue', title: '逾期工单', value: 0, icon: 'Warning', growth: -5 }
])

const pendingCount = computed(() => {
  return ordersData.value.filter(o => o.status === 'pending').length
})

// 辅助函数
const getCategoryText = (category) => {
  const texts = { fault: '故障报修', change: '变更申请', requirement: '需求处理', consult: '咨询服务' }
  return texts[category] || category
}

const getCategoryTagType = (category) => {
  const types = { fault: 'danger', change: 'warning', requirement: 'primary', consult: 'info' }
  return types[category] || 'info'
}

const getPriorityText = (priority) => {
  const texts = { urgent: '紧急', high: '高', medium: '中', low: '低' }
  return texts[priority] || priority
}

const getPriorityTagType = (priority) => {
  const types = { urgent: 'danger', high: 'warning', medium: 'info', low: '' }
  return types[priority] || 'info'
}

const getStatusText = (status) => {
  const texts = { pending: '待处理', processing: '处理中', pending_approval: '待验收', completed: '已完成', closed: '已关闭' }
  return texts[status] || status
}

const getStatusTagType = (status) => {
  const types = { pending: 'danger', processing: 'warning', pending_approval: 'info', completed: 'success', closed: 'info' }
  return types[status] || 'info'
}

const isSLAWarning = (order) => {
  return order.slaRemaining.includes('超时') || order.slaRemaining.includes('分钟')
}

const getKanbanCount = (status) => {
  return ordersData.value.filter(o => o.status === status).length
}

const getKanbanOrders = (status) => {
  return ordersData.value.filter(o => o.status === status)
}

// 加载工单数据
const loadOrders = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value,
      category: categoryFilter.value,
      priority: priorityFilter.value,
      status: statusFilter.value,
      assignee: assignFilter.value === 'me' ? 'current_user' : (assignFilter.value === 'unassigned' ? null : assignFilter.value),
      search: searchText.value
    }
    const res = await workorder.getWorkOrders(params)
    ordersData.value = res.data?.list || res.data || []
    total.value = res.data?.total || ordersData.value.length
    updateStats()
  } catch (error) {
    console.error('Failed to load orders:', error)
    ElMessage.error('加载工单列表失败')
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  statsData[0].value = ordersData.value.filter(o => o.status === 'pending').length
  statsData[1].value = ordersData.value.filter(o => o.status === 'processing').length
  statsData[2].value = ordersData.value.filter(o => o.status === 'completed').length
  statsData[3].value = ordersData.value.filter(o => o.slaRemaining.includes('超时')).length
}

// 事件处理
const handleFilterChange = () => {
  currentPage.value = 1
  loadOrders()
}

const handleSearch = () => {
  currentPage.value = 1
  loadOrders()
}

const handleRefresh = () => {
  loadOrders()
  ElMessage.success('刷新成功')
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadOrders()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  loadOrders()
}

const handleRowClick = (row) => {
  handleViewDetail(row)
}

const handleViewDetail = (order) => {
  currentOrder.value = order
  commentText.value = ''
  showDetailDrawer.value = true
}

const handleProcess = (order) => {
  currentOrder.value = order
  processForm.result = 'in_progress'
  processForm.description = ''
  processForm.assignee = ''
  showProcessDialog.value = true
}

const handleSubmitProcess = async () => {
  if (!processForm.description) {
    ElMessage.warning('请输入处理说明')
    return
  }
  
  try {
    await workorder.updateWorkOrder(currentOrder.value.id, {
      status: processForm.result === 'resolved' ? 'completed' : 'processing',
      process_result: processForm.result,
      process_description: processForm.description,
      assignee: processForm.assignee || undefined
    })
    
    if (processForm.assignee) {
      currentOrder.value.assignee = processForm.assignee
    }
    
    showProcessDialog.value = false
    ElMessage.success('处理已提交')
    loadOrders()
  } catch (error) {
    ElMessage.error('提交处理失败')
  }
}

const handleComment = (order) => {
  currentOrder.value = order
  showDetailDrawer.value = true
}

const handleAddComment = async () => {
  if (!commentText.value.trim()) {
    ElMessage.warning('请输入评论内容')
    return
  }
  
  try {
    await workorder.addComment(currentOrder.value.id, {
      content: commentText.value
    })
    
    const now = new Date().toLocaleDateString('zh-CN')
    
    if (!currentOrder.value.comments) {
      currentOrder.value.comments = []
    }
    
    currentOrder.value.comments.push({
      author: '当前用户',
      time: now,
      text: commentText.value
    })
    
    commentText.value = ''
    ElMessage.success('评论已添加')
  } catch (error) {
    ElMessage.error('添加评论失败')
  }
}

const handleTransfer = async (order) => {
  try {
    await workorder.updateWorkOrder(order.id, {
      status: 'pending',
      assignee: processForm.assignee
    })
    ElMessage.success('工单已转移')
    loadOrders()
  } catch (error) {
    ElMessage.error('转移工单失败')
  }
}

const handleComplete = async (order) => {
  try {
    await workorder.approveWorkOrder(order.id, { result: 'approved' })
    ElMessage.success('工单已标记为完成')
    loadOrders()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleClose = async (order) => {
  try {
    await workorder.updateWorkOrder(order.id, { status: 'closed' })
    ElMessage.success('工单已关闭')
    loadOrders()
  } catch (error) {
    ElMessage.error('关闭工单失败')
  }
}

const handleExport = async () => {
  try {
    const params = {
      category: categoryFilter.value,
      priority: priorityFilter.value,
      status: statusFilter.value,
      search: searchText.value
    }
    await workorder.exportWorkOrders(params)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const handleOrderCommand = (command, order) => {
  switch (command) {
    case 'edit':
      orderForm.title = order.title
      orderForm.category = order.category
      orderForm.priority = order.priority
      orderForm.asset = order.assetName
      orderForm.assignee = order.assignee
      orderForm.description = order.description
      showCreateDialog.value = true
      break
    case 'transfer': handleTransfer(order); break
    case 'close': handleClose(order); break
    case 'delete':
      ElMessageBox.confirm('确定要删除此工单吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await workorder.deleteWorkOrder(order.id)
          ElMessage.success('工单已删除')
          loadOrders()
        } catch (error) {
          ElMessage.error('删除失败')
        }
      }).catch(() => {})
      break
  }
}

const handleSubmitOrder = async () => {
  if (!orderFormRef.value) return
  
  try {
    await orderFormRef.value.validate()
    
    submitLoading.value = true
    
    const data = {
      order_type: orderForm.category || 'fault',
      title: orderForm.title,
      description: orderForm.description || '',
      priority: orderForm.priority || 'P3',
      device_name: orderForm.asset || undefined,
      assignee: orderForm.assignee || undefined,
    }
    
    const response = await workorder.createWorkOrder(data)
    
    // 将返回的工单添加到列表头部
    ordersData.value.unshift(response)
    total.value++
    updateStats()
    
    showCreateDialog.value = false
    Object.keys(orderForm).forEach(key => orderForm[key] = key === 'category' || key === 'priority' ? orderForm[key] : '')
    orderForm.category = 'fault'
    orderForm.priority = 'medium'
    
    ElMessage.success('工单创建成功')
  } catch (error) {
    console.error('创建工单失败:', error)
  } finally {
    submitLoading.value = false
  }
}

// 初始化
onMounted(() => {
  loadOrders()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.workorder-page {
  animation: fadeIn 0.3s ease;
}

// ========== 页面头部 ==========
.page-header {
  @include flex-between;
  margin-bottom: $spacing-xl;

  .page-header-left {
    .page-title {
      font-size: $font-size-xxl;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin: 0 0 4px 0;
    }

    .page-subtitle {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin: 0;
    }
  }

  .page-header-actions {
    display: flex;
    gap: $spacing-sm;
  }
}

// ========== 统计卡片 ==========
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-lg;
  background: $bg-container;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-sm;
  animation: slideInUp 0.4s ease-out backwards;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-base;
  }
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: $border-radius-md;
  @include flex-center;
  color: #fff;
  font-size: 24px;

  &.pending { background: linear-gradient(135deg, #f53f3f, #ff7875); }
  &.processing { background: linear-gradient(135deg, #ff7d00, #ff9d00); }
  &.completed { background: linear-gradient(135deg, #00b42a, #23c343); }
  &.overdue { background: linear-gradient(135deg, #f53f3f, #ff7875); }
}

.stat-content {
  flex: 1;

  .stat-value {
    font-size: $font-size-xxl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    line-height: 1.2;
  }

  .stat-title {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin-top: 2px;
  }
}

.stat-growth {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: $font-size-xs;
  padding: 2px 8px;
  border-radius: 10px;

  &.up {
    background: rgba($success, 0.1);
    color: $success;
  }

  &.down {
    background: rgba($danger, 0.1);
    color: $danger;
  }
}

// ========== 筛选工具栏 ==========
.filter-bar {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  background: $bg-container;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-lg;
  box-shadow: $shadow-sm;

  .filter-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    flex: 1;
  }

  .filter-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
}

// ========== 看板视图 ==========
.kanban-board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  min-height: 400px;
}

.kanban-column {
  background: $bg-page;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  min-height: 300px;
}

.kanban-header {
  @include flex-between;
  padding-bottom: $spacing-md;
  margin-bottom: $spacing-md;
  border-bottom: 2px solid $border-light;

  .kanban-title {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $text-primary;
  }
}

.kanban-cards {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.kanban-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;

  &:hover {
    box-shadow: $shadow-base;
    transform: translateY(-2px);
  }

  &.urgent { border-left-color: $danger; }
  &.high { border-left-color: $warning; }
  &.medium { border-left-color: $primary; }
  &.low { border-left-color: $text-placeholder; }
}

.card-header {
  display: flex;
  gap: $spacing-sm;
  margin-bottom: $spacing-sm;
}

.card-title {
  font-size: $font-size-sm;
  color: $text-primary;
  margin-bottom: 4px;
  @include multi-ellipsis(2);
}

.card-sn {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-bottom: $spacing-sm;
}

.card-meta {
  display: flex;
  gap: $spacing-md;

  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

// ========== 表格 ==========
.table-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.orders-table {
  :deep(.el-table__header th) {
    background: $bg-page !important;
    color: $text-secondary;
    font-weight: $font-weight-semibold;
  }
}

.order-sn {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: $font-size-sm;
  color: $primary;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
}

.title-cell {
  .order-title {
    font-size: $font-size-sm;
    color: $text-primary;
  }
}

.status-cell {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.pending { background: $danger; box-shadow: 0 0 6px $danger; }
    &.processing { background: $warning; }
    &.pending_approval { background: $primary; }
    &.completed { background: $success; }
    &.closed { background: $text-placeholder; }
  }
}

.assignee-text, .creator-text {
  font-size: $font-size-sm;
  color: $text-regular;
}

.time-text {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.sla-text {
  font-size: $font-size-sm;
  color: $text-secondary;

  &.sla-warning {
    color: $danger;
    font-weight: $font-weight-medium;
  }
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
}

// ========== 表格底部 ==========
.table-footer {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  border-top: 1px solid $border-light;

  .table-info {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

// ========== 工单详情 ==========
.order-detail {
  .detail-header {
    margin-bottom: $spacing-xl;

    .detail-badges {
      display: flex;
      gap: $spacing-sm;
      margin-bottom: $spacing-md;
    }

    .detail-title {
      font-size: $font-size-lg;
      color: $text-primary;
      margin: 0;
    }
  }

  .detail-description {
    font-size: $font-size-sm;
    color: $text-regular;
    line-height: 1.8;
    padding: $spacing-md;
    background: $bg-page;
    border-radius: $border-radius-md;
  }

  .detail-actions {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-sm;
  }
}

.process-item {
  p {
    margin: 0;
    line-height: 1.6;

    &.process-action {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    &.process-detail {
      font-size: $font-size-sm;
      color: $text-regular;
      margin-top: 4px;
    }

    &.process-operator {
      font-size: $font-size-xs;
      color: $text-secondary;
      margin-top: 4px;
    }
  }
}

// ========== 评论 ==========
.comments-section {
  margin-bottom: $spacing-lg;
}

.comment-item {
  display: flex;
  gap: $spacing-md;
  padding: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-sm;

  .comment-avatar {
    flex-shrink: 0;
  }

  .comment-content {
    flex: 1;

    .comment-header {
      display: flex;
      align-items: center;
      gap: $spacing-md;
      margin-bottom: 4px;

      .comment-author {
        font-size: $font-size-sm;
        font-weight: $font-weight-medium;
        color: $text-primary;
      }

      .comment-time {
        font-size: $font-size-xs;
        color: $text-secondary;
      }
    }

    .comment-text {
      font-size: $font-size-sm;
      color: $text-regular;
    }
  }
}

.no-comments {
  text-align: center;
  padding: $spacing-lg;
  color: $text-placeholder;
  font-size: $font-size-sm;
}

.comment-input-section {
  margin-top: $spacing-md;
}

// ========== 动画 ==========
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// ========== 响应式 ==========
@include respond-to('xl') {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .kanban-board {
    grid-template-columns: repeat(2, 1fr);
  }
}

@include respond-to('lg') {
  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-md;

    .filter-left {
      flex-wrap: wrap;
    }
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .kanban-board {
    grid-template-columns: 1fr;
  }
}
</style>