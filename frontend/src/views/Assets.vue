<template>
  <div class="assets-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">
          资产管理
        </h2>
        <p class="page-subtitle">
          统一管理所有IT资产，支持多类型设备监控
        </p>
      </div>
      <div class="page-header-actions">
        <el-button
          :loading="exportLoading"
          @click="handleExport"
        >
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button @click="handleImport">
          <el-icon><Upload /></el-icon>
          导入
        </el-button>
        <el-button
          type="primary"
          @click="handleCreate"
        >
          <el-icon><Plus /></el-icon>
          添加资产
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div 
        v-for="(stat, index) in statsData" 
        :key="stat.title"
        class="stat-card"
        :style="{ animationDelay: `${index * 0.08}s` }"
      >
        <div
          class="stat-icon"
          :style="{ background: stat.color }"
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
          v-if="stat.trend !== undefined"
          class="stat-trend"
          :class="stat.trend > 0 ? 'up' : 'down'"
        >
          <el-icon><TrendCharts /></el-icon>
          {{ Math.abs(stat.trend) }}%
        </div>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-input
          v-model="searchText"
          placeholder="搜索资产名称、IP、主机名..."
          style="width: 280px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button
              :icon="Search"
              @click="handleSearch"
            />
          </template>
        </el-input>

        <el-select
          v-model="typeFilter"
          placeholder="资产类型"
          style="width: 140px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="服务器"
            value="server"
          >
            <div class="option-item">
              <span class="option-dot server" />
              <span>服务器</span>
            </div>
          </el-option>
          <el-option
            label="网络设备"
            value="network"
          >
            <div class="option-item">
              <span class="option-dot network" />
              <span>网络设备</span>
            </div>
          </el-option>
          <el-option
            label="存储设备"
            value="storage"
          >
            <div class="option-item">
              <span class="option-dot storage" />
              <span>存储设备</span>
            </div>
          </el-option>
          <el-option
            label="安全设备"
            value="security"
          >
            <div class="option-item">
              <span class="option-dot security" />
              <span>安全设备</span>
            </div>
          </el-option>
        </el-select>

        <el-select
          v-model="statusFilter"
          placeholder="运行状态"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="在线"
            value="online"
          >
            <template #default>
              <span class="status-dot online" />
              在线
            </template>
          </el-option>
          <el-option
            label="离线"
            value="offline"
          >
            <template #default>
              <span class="status-dot offline" />
              离线
            </template>
          </el-option>
          <el-option
            label="维护中"
            value="maintenance"
          >
            <template #default>
              <span class="status-dot maintenance" />
              维护中
            </template>
          </el-option>
        </el-select>

        <el-select
          v-model="osFilter"
          placeholder="操作系统"
          style="width: 140px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="CentOS"
            value="centos"
          />
          <el-option
            label="Ubuntu"
            value="ubuntu"
          />
          <el-option
            label="麒麟Linux"
            value="kylin"
          />
          <el-option
            label="Windows Server"
            value="windows"
          />
          <el-option
            label="其他"
            value="other"
          />
        </el-select>
      </div>

      <div class="filter-right">
        <el-checkbox
          v-model="showOnlineOnly"
          @change="handleFilterChange"
        >
          仅显示在线
        </el-checkbox>
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

    <!-- 资产表格 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="assetsData"
        stripe
        class="assets-table"
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column
          type="selection"
          width="50"
        />

        <el-table-column
          label="资产信息"
          min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <div class="asset-info">
              <div
                class="asset-icon"
                :class="row.type"
              >
                <el-icon><component :is="getTypeIcon(row.type)" /></el-icon>
              </div>
              <div class="asset-details">
                <span class="asset-name">{{ row.name }}</span>
                <span class="asset-hostname">{{ row.hostname || '-' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="类型"
          width="110"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getTypeTagType(row.type)"
              effect="light"
            >
              {{ getTypeText(row.type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="IP地址"
          width="140"
        >
          <template #default="{ row }">
            <span class="ip-address">{{ row.ip || '-' }}</span>
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
              <span class="status-text">{{ getStatusText(row.status) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="操作系统"
          width="120"
        >
          <template #default="{ row }">
            <span class="os-text">{{ row.os_type || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="位置"
          width="130"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span class="location-text">{{ row.location || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="最后更新"
          width="160"
        >
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.updated_at) }}</span>
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
                  @click="handleView(row)"
                >
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                content="编辑"
                placement="top"
              >
                <el-button
                  text
                  type="primary"
                  @click="handleEdit(row)"
                >
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                content="监控数据"
                placement="top"
              >
                <el-button
                  text
                  @click="handleMonitor(row)"
                >
                  <el-icon><DataLine /></el-icon>
                </el-button>
              </el-tooltip>
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleCommand(cmd, row)"
              >
                <el-button text>
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="collect">
                      <el-icon><Refresh /></el-icon>
                      立即采集
                    </el-dropdown-item>
                    <el-dropdown-item command="maintenance">
                      <el-icon><Tools /></el-icon>
                      进入维护
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="delete"
                      divided
                    >
                      <el-icon><Delete /></el-icon>
                      删除资产
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
          共 {{ total }} 条记录，已选择 {{ selectedRows.length }} 项
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

    <!-- 资产详情抽屉 -->
    <el-drawer
      v-model="showDetailDrawer"
      :title="currentAsset?.name"
      size="600px"
    >
      <div
        v-if="currentAsset"
        class="asset-detail"
      >
        <div class="detail-header">
          <div
            class="detail-icon"
            :class="currentAsset.type"
          >
            <el-icon><component :is="getTypeIcon(currentAsset.type)" /></el-icon>
          </div>
          <div class="detail-status">
            <span
              class="status-dot large"
              :class="currentAsset.status"
            />
            {{ getStatusText(currentAsset.status) }}
          </div>
        </div>

        <el-descriptions
          :column="2"
          border
          class="detail-descriptions"
        >
          <el-descriptions-item label="资产名称">
            {{ currentAsset.name }}
          </el-descriptions-item>
          <el-descriptions-item label="主机名">
            {{ currentAsset.hostname || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="资产类型">
            {{ getTypeText(currentAsset.type) }}
          </el-descriptions-item>
          <el-descriptions-item label="IP地址">
            {{ currentAsset.ip || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="操作系统">
            {{ currentAsset.os_type || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="端口">
            {{ currentAsset.port || '-' }}
          </el-descriptions-item>
          <el-descriptions-item
            label="位置"
            :span="2"
          >
            {{ currentAsset.location || '-' }}
          </el-descriptions-item>
          <el-descriptions-item
            label="描述"
            :span="2"
          >
            {{ currentAsset.description || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ currentAsset.created_at || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ currentAsset.updated_at || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">
          监控指标
        </el-divider>
        <div class="monitor-metrics">
          <div class="metric-item">
            <span class="metric-label">CPU使用率</span>
            <el-progress
              :percentage="72"
              :color="getProgressColor(72)"
            />
          </div>
          <div class="metric-item">
            <span class="metric-label">内存使用率</span>
            <el-progress
              :percentage="58"
              :color="getProgressColor(58)"
            />
          </div>
          <div class="metric-item">
            <span class="metric-label">磁盘使用率</span>
            <el-progress
              :percentage="45"
              :color="getProgressColor(45)"
            />
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showFormDialog"
      :title="editingAsset ? '编辑资产' : '添加资产'"
      width="650px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        class="asset-form"
      >
        <div class="form-section">
          <h4 class="form-section-title">
            基本信息
          </h4>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item
                label="资产名称"
                prop="name"
              >
                <el-input
                  v-model="form.name"
                  placeholder="请输入资产名称"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item
                label="主机名"
                prop="hostname"
              >
                <el-input
                  v-model="form.hostname"
                  placeholder="请输入主机名"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item
                label="资产类型"
                prop="type"
              >
                <el-select
                  v-model="form.type"
                  style="width: 100%"
                >
                  <el-option
                    label="服务器"
                    value="server"
                  />
                  <el-option
                    label="网络设备"
                    value="network"
                  />
                  <el-option
                    label="存储设备"
                    value="storage"
                  />
                  <el-option
                    label="安全设备"
                    value="security"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item
                label="操作系统"
                prop="os_type"
              >
                <el-select
                  v-model="form.os_type"
                  style="width: 100%"
                >
                  <el-option
                    label="CentOS"
                    value="centos"
                  />
                  <el-option
                    label="Ubuntu"
                    value="ubuntu"
                  />
                  <el-option
                    label="麒麟Linux"
                    value="kylin"
                  />
                  <el-option
                    label="Windows Server"
                    value="windows"
                  />
                  <el-option
                    label="其他"
                    value="other"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div class="form-section">
          <h4 class="form-section-title">
            网络配置
          </h4>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item
                label="IP地址"
                prop="ip"
              >
                <el-input
                  v-model="form.ip"
                  placeholder="如: 192.168.1.100"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item
                label="端口"
                prop="port"
              >
                <el-input-number
                  v-model="form.port"
                  :min="1"
                  :max="65535"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div class="form-section">
          <h4 class="form-section-title">
            位置信息
          </h4>
          <el-form-item
            label="位置"
            prop="location"
          >
            <el-input
              v-model="form.location"
              placeholder="如: 机房A-机柜3"
            />
          </el-form-item>
        </div>

        <div class="form-section">
          <h4 class="form-section-title">
            备注信息
          </h4>
          <el-form-item label="备注">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入备注信息"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showFormDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitLoading"
          @click="handleSubmit"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入资产"
      width="500px"
    >
      <div class="import-tip">
        <el-icon color="#909399">
          <InfoFilled />
        </el-icon>
        <span>支持 Excel (.xlsx, .xls) 和 CSV 格式，请下载模板后上传</span>
      </div>
      <el-button
        type="text"
        class="download-template"
        @click="handleDownloadTemplate"
      >
        <el-icon><Download /></el-icon>
        下载导入模板
      </el-button>
      <el-upload
        ref="uploadRef"
        drag
        action="#"
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".xlsx,.xls,.csv"
        class="import-upload"
      >
        <el-icon class="upload-icon">
          <UploadFilled />
        </el-icon>
        <div class="upload-text">
          拖拽文件到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="upload-tip">
            支持 Excel (.xlsx, .xls) 和 CSV 格式
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showImportDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="importLoading"
          @click="handleImportSubmit"
        >
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, Refresh, Download, Upload, View, Edit, Delete, MoreFilled,
  TrendCharts, DataLine, Tools, UploadFilled, InfoFilled, Server, Connection,
  Box, Lock, Cpu
} from '@element-plus/icons-vue'
import { assets } from '@/api'

// 状态
const loading = ref(false)
const submitLoading = ref(false)
const importLoading = ref(false)
const exportLoading = ref(false)
const assetsData = ref([])
const showFormDialog = ref(false)
const showImportDialog = ref(false)
const showDetailDrawer = ref(false)
const editingAsset = ref(null)
const currentAsset = ref(null)
const formRef = ref(null)
const uploadRef = ref(null)
const importFile = ref(null)
const selectedRows = ref([])

// 筛选
const typeFilter = ref('')
const statusFilter = ref('')
const osFilter = ref('')
const searchText = ref('')
const showOnlineOnly = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 统计
const statsData = reactive([
  { title: '资产总数', value: 0, icon: 'Odometer', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', trend: 12 },
  { title: '在线设备', value: 0, icon: 'CircleCheck', color: 'linear-gradient(135deg, #00b42a 0%, #00d680 100%)', trend: 5 },
  { title: '服务器', value: 0, icon: 'Cpu', color: 'linear-gradient(135deg, #165dff 0%, #4080ff 100%)' },
  { title: '安全设备', value: 0, icon: 'Lock', color: 'linear-gradient(135deg, #f53f3f 0%, #ff7875 100%)' }
])

// 表单
const form = reactive({
  name: '',
  type: 'server',
  ip: '',
  hostname: '',
  os_type: 'centos',
  port: 22,
  location: '',
  description: ''
})

// 表单验证
const rules = {
  name: [{ required: true, message: '请输入资产名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择资产类型', trigger: 'change' }],
  ip: [
    { required: true, message: '请输入IP地址', trigger: 'blur' },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: 'IP地址格式不正确', trigger: 'blur' }
  ]
}

// 辅助函数
const getTypeText = (type) => {
  const texts = { server: '服务器', network: '网络设备', storage: '存储设备', security: '安全设备' }
  return texts[type] || type
}

const getTypeIcon = (type) => {
  const icons = { server: 'Cpu', network: 'Connection', storage: 'Box', security: 'Lock' }
  return icons[type] || 'Server'
}

const getTypeTagType = (type) => {
  const types = { server: '', network: 'success', storage: 'warning', security: 'danger' }
  return types[type] || 'info'
}

const getStatusText = (status) => {
  const texts = { online: '在线', offline: '离线', maintenance: '维护中' }
  return texts[status] || status
}

const getProgressColor = (value) => {
  if (value >= 80) return '#f53f3f'
  if (value >= 60) return '#ff7d00'
  return '#00b42a'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// 加载资产列表
const loadAssets = async () => {
  loading.value = true
  try {
    // 模拟数据
    assetsData.value = [
      { id: 1, name: 'Web服务器-01', hostname: 'web-01', type: 'server', ip: '192.168.1.101', status: 'online', os_type: 'CentOS 7.9', location: '机房A-机柜1', created_at: '2024-01-15 10:30:00', updated_at: '2024-05-04 14:25:00' },
      { id: 2, name: '数据库服务器', hostname: 'db-01', type: 'server', ip: '192.168.1.102', status: 'online', os_type: 'Ubuntu 22.04', location: '机房A-机柜2', created_at: '2024-01-15 10:30:00', updated_at: '2024-05-04 14:20:00' },
      { id: 3, name: '华为核心交换机', hostname: 'sw-core-01', type: 'network', ip: '192.168.1.1', status: 'online', os_type: 'VRP', location: '机房A-机柜0', created_at: '2024-01-10 09:00:00', updated_at: '2024-05-04 14:00:00' },
      { id: 4, name: '天融信防火墙', hostname: 'fw-01', type: 'security', ip: '192.168.1.254', status: 'online', os_type: 'TOS', location: '机房A-机柜0', created_at: '2024-01-10 09:00:00', updated_at: '2024-05-04 13:55:00' },
      { id: 5, name: '应用服务器-01', hostname: 'app-01', type: 'server', ip: '192.168.1.103', status: 'maintenance', os_type: '麒麟Linux V10', location: '机房A-机柜3', created_at: '2024-02-01 11:00:00', updated_at: '2024-05-04 12:00:00' },
      { id: 6, name: '绿盟IDS', hostname: 'ids-01', type: 'security', ip: '192.168.1.200', status: 'online', os_type: 'NF', location: '机房A-机柜0', created_at: '2024-01-20 14:00:00', updated_at: '2024-05-04 13:50:00' },
      { id: 7, name: '存储阵列', hostname: 'storage-01', type: 'storage', ip: '192.168.1.50', status: 'online', os_type: '-', location: '机房B-机柜1', created_at: '2024-03-01 10:00:00', updated_at: '2024-05-04 13:45:00' },
      { id: 8, name: '启明星辰WAF', hostname: 'waf-01', type: 'security', ip: '192.168.1.253', status: 'offline', os_type: '-', location: '机房A-机柜0', created_at: '2024-01-15 15:00:00', updated_at: '2024-05-03 22:00:00' }
    ]
    total.value = assetsData.value.length
    updateStats()
  } catch (error) {
    console.error('Failed to load assets:', error)
    ElMessage.error('加载资产列表失败')
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  statsData[0].value = total.value
  statsData[1].value = assetsData.value.filter(a => a.status === 'online').length
  statsData[2].value = assetsData.value.filter(a => a.type === 'server').length
  statsData[3].value = assetsData.value.filter(a => a.type === 'security').length
}

// 事件处理
const handleFilterChange = () => {
  currentPage.value = 1
  loadAssets()
}

const handleSearch = () => {
  currentPage.value = 1
  loadAssets()
}

const handleRefresh = () => {
  loadAssets()
  ElMessage.success('刷新成功')
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadAssets()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  loadAssets()
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const handleCreate = () => {
  editingAsset.value = null
  Object.assign(form, {
    name: '',
    type: 'server',
    ip: '',
    hostname: '',
    os_type: 'centos',
    port: 22,
    location: '',
    description: ''
  })
  showFormDialog.value = true
}

const handleEdit = (asset) => {
  editingAsset.value = asset
  Object.assign(form, { ...asset })
  showFormDialog.value = true
}

const handleView = (asset) => {
  currentAsset.value = asset
  showDetailDrawer.value = true
}

const handleMonitor = (asset) => {
  ElMessage.info('跳转到监控页面: ' + asset.name)
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    submitLoading.value = true
    // 模拟保存
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success(editingAsset.value ? '更新成功' : '添加成功')
    showFormDialog.value = false
    loadAssets()
  } catch (error) {
    // 验证失败
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (asset) => {
  try {
    await ElMessageBox.confirm(`确定要删除资产「${asset.name}」吗？此操作不可撤销。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger'
    })
    ElMessage.success('删除成功')
    loadAssets()
  } catch {
    // 取消
  }
}

const handleCommand = (command, asset) => {
  switch (command) {
    case 'collect':
      ElMessage.success(`开始采集 ${asset.name} 的数据...`)
      break
    case 'maintenance':
      ElMessage.info(`${asset.name} 已进入维护模式`)
      break
    case 'delete':
      handleDelete(asset)
      break
  }
}

const handleImport = () => {
  importFile.value = null
  showImportDialog.value = true
}

const handleFileChange = (file) => {
  importFile.value = file
}

const handleImportSubmit = async () => {
  if (!importFile.value) {
    ElMessage.warning('请选择要导入的文件')
    return
  }
  importLoading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1500))
    ElMessage.success('导入成功：8条记录')
    showImportDialog.value = false
    loadAssets()
  } catch {
    ElMessage.error('导入失败')
  } finally {
    importLoading.value = false
  }
}

const handleExport = async () => {
  exportLoading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
}

const handleDownloadTemplate = () => {
  ElMessage.success('开始下载导入模板')
}

// 初始化
onMounted(() => {
  loadAssets()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.assets-page {
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

.stat-trend {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;

  &.up { color: $success; }
  &.down { color: $danger; }
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

.option-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .option-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.server { background: #165dff; }
    &.network { background: #00b42a; }
    &.storage { background: #ff7d00; }
    &.security { background: #f53f3f; }
  }
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;

  &.online { background: $success; box-shadow: 0 0 6px $success; }
  &.offline { background: $danger; }
  &.maintenance { background: $warning; }
  &.large { width: 12px; height: 12px; }
}

// ========== 表格 ==========
.table-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.assets-table {
  :deep(.el-table__header th) {
    background: $bg-page !important;
    color: $text-secondary;
    font-weight: $font-weight-semibold;
  }
}

.asset-info {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  .asset-icon {
    width: 36px;
    height: 36px;
    border-radius: $border-radius-md;
    @include flex-center;
    font-size: 18px;

    &.server { background: rgba($primary, 0.1); color: $primary; }
    &.network { background: rgba($success, 0.1); color: $success; }
    &.storage { background: rgba($warning, 0.1); color: $warning; }
    &.security { background: rgba($danger, 0.1); color: $danger; }
  }

  .asset-details {
    display: flex;
    flex-direction: column;

    .asset-name {
      font-size: $font-size-base;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .asset-hostname {
      font-size: $font-size-xs;
      color: $text-placeholder;
    }
  }
}

.ip-address {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: $font-size-sm;
  color: $text-regular;
}

.status-cell {
  display: flex;
  align-items: center;

  .status-text {
    font-size: $font-size-sm;
  }
}

.os-text, .location-text, .time-text {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 4px;
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

// ========== 资产详情 ==========
.asset-detail {
  .detail-header {
    display: flex;
    align-items: center;
    gap: $spacing-lg;
    margin-bottom: $spacing-xl;

    .detail-icon {
      width: 64px;
      height: 64px;
      border-radius: $border-radius-lg;
      @include flex-center;
      font-size: 32px;
      color: #fff;

      &.server { background: linear-gradient(135deg, #165dff, #4080ff); }
      &.network { background: linear-gradient(135deg, #00b42a, #26d959); }
      &.security { background: linear-gradient(135deg, #f53f3f, #ff7875); }
      &.storage { background: linear-gradient(135deg, #ff7d00, #ff9d00); }
    }

    .detail-status {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      font-size: $font-size-md;
      color: $text-regular;
    }
  }
}

.monitor-metrics {
  .metric-item {
    margin-bottom: $spacing-md;

    .metric-label {
      display: block;
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-bottom: $spacing-xs;
    }
  }
}

// ========== 表单 ==========
.asset-form {
  .form-section {
    margin-bottom: $spacing-lg;

    &:last-child {
      margin-bottom: 0;
    }

    .form-section-title {
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $text-primary;
      margin: 0 0 $spacing-md 0;
      padding-left: $spacing-sm;
      border-left: 3px solid $primary;
    }
  }
}

// ========== 导入 ==========
.import-tip {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-md;
  font-size: $font-size-sm;
  color: $text-secondary;
}

.download-template {
  margin-bottom: $spacing-lg;
}

.import-upload {
  :deep(.el-upload-dragger) {
    padding: $spacing-xl;
  }

  .upload-icon {
    font-size: 48px;
    color: $text-placeholder;
    margin-bottom: $spacing-md;
  }

  .upload-text {
    font-size: $font-size-sm;
    color: $text-secondary;

    em {
      color: $primary;
      font-style: normal;
    }
  }
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
}
</style>