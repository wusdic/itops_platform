<template>
  <div class="devices-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">
          设备管理
        </h2>
        <p class="page-subtitle">
          统一管理所有设备，支持多种采集方式
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
        <el-button
          type="primary"
          @click="handleCreate"
        >
          <el-icon><Plus /></el-icon>
          添加设备
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
          v-if="stat.key === 'online'"
          class="stat-pulse"
          :class="{ active: stat.alert }"
        />
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-input
          v-model="searchText"
          placeholder="搜索设备名称、IP..."
          style="width: 260px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select
          v-model="typeFilter"
          placeholder="设备类型"
          style="width: 140px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="服务器"
            value="server"
          >
            <div class="level-option">
              <span class="level-dot server" />
              <span>服务器</span>
            </div>
          </el-option>
          <el-option
            label="网络设备"
            value="network"
          >
            <div class="level-option">
              <span class="level-dot network" />
              <span>网络设备</span>
            </div>
          </el-option>
          <el-option
            label="安全设备"
            value="security"
          >
            <div class="level-option">
              <span class="level-dot security" />
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
            <span class="status-dot online" />
            在线
          </el-option>
          <el-option
            label="离线"
            value="offline"
          >
            <span class="status-dot offline" />
            离线
          </el-option>
          <el-option
            label="维护中"
            value="maintenance"
          >
            <span class="status-dot maintenance" />
            维护中
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
            label="麒麟Linux"
            value="kylin"
          />
          <el-option
            label="CentOS"
            value="centos"
          />
          <el-option
            label="Ubuntu"
            value="ubuntu"
          />
          <el-option
            label="Windows"
            value="windows"
          />
          <el-option
            label="华为VRP"
            value="vrp"
          />
        </el-select>
      </div>

      <div class="filter-right">
        <el-button
          text
          :loading="loading"
          @click="handleRefresh"
        >
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button
          text
          @click="handleBatchCollect"
        >
          <el-icon><DataLine /></el-icon>
          批量采集
        </el-button>
      </div>
    </div>

    <!-- 设备列表 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="devicesData"
        stripe
        class="devices-table"
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column
          type="selection"
          width="50"
        />

        <el-table-column
          label="设备信息"
          min-width="220"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <div class="device-info">
              <div
                class="device-icon"
                :class="row.type"
              >
                <el-icon><component :is="getTypeIcon(row.type)" /></el-icon>
              </div>
              <div class="device-details">
                <span class="device-name">{{ row.name }}</span>
                <span class="device-ip">{{ row.ip }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="类型"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getTypeTagType(row.type)"
            >
              {{ getTypeText(row.type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="操作系统"
          width="120"
        >
          <template #default="{ row }">
            <span class="os-text">{{ row.os }}</span>
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
          label="采集方式"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              type="info"
            >
              {{ getCollectMethod(row.method) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="性能指标"
          min-width="200"
        >
          <template #default="{ row }">
            <div class="metrics-cell">
              <div class="metric-item">
                <span class="metric-label">CPU</span>
                <el-progress
                  :percentage="row.cpu"
                  :stroke-width="6"
                  :color="getMetricColor(row.cpu)"
                  :show-text="false"
                  size="small"
                />
                <span class="metric-value">{{ row.cpu }}%</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">内存</span>
                <el-progress
                  :percentage="row.memory"
                  :stroke-width="6"
                  :color="getMetricColor(row.memory)"
                  :show-text="false"
                  size="small"
                />
                <span class="metric-value">{{ row.memory }}%</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">磁盘</span>
                <el-progress
                  :percentage="row.disk"
                  :stroke-width="6"
                  :color="getMetricColor(row.disk)"
                  :show-text="false"
                  size="small"
                />
                <span class="metric-value">{{ row.disk }}%</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="最后采集"
          width="160"
        >
          <template #default="{ row }">
            <span class="last-collect">{{ row.lastCollect }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="180"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              size="small"
              text
              type="primary"
              @click="handleView(row)"
            >
              <el-icon><View /></el-icon>
            </el-button>
            <el-button
              size="small"
              text
              type="primary"
              @click="handleEdit(row)"
            >
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button
              size="small"
              text
              @click="handleCollect(row)"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-dropdown
              trigger="click"
              @command="(cmd) => handleCommand(cmd, row)"
            >
              <el-button
                size="small"
                text
              >
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="alarm">
                    设置告警
                  </el-dropdown-item>
                  <el-dropdown-item command="ssh">
                    远程连接
                  </el-dropdown-item>
                  <el-dropdown-item command="config">
                    配置管理
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="delete"
                    divided
                  >
                    删除设备
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalCount"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 添加/编辑设备对话框 -->
    <el-dialog
      v-model="deviceDialogVisible"
      :title="isEdit ? '编辑设备' : '添加设备'"
      width="600px"
      :append-to-body="true"
    >
      <el-form
        ref="deviceFormRef"
        :model="deviceForm"
        :rules="deviceRules"
        label-width="100px"
      >
        <el-form-item
          label="设备名称"
          prop="name"
        >
          <el-input
            v-model="deviceForm.name"
            placeholder="请输入设备名称"
          />
        </el-form-item>
        <el-form-item
          label="设备IP"
          prop="ip"
        >
          <el-input
            v-model="deviceForm.ip"
            placeholder="如 192.168.1.100"
          />
        </el-form-item>
        <el-form-item
          label="设备类型"
          prop="type"
        >
          <el-select
            v-model="deviceForm.type"
            placeholder="请选择"
            style="width: 100%"
          >
            <el-option
              label="Windows服务器"
              value="windows"
            />
            <el-option
              label="Linux服务器"
              value="linux"
            />
            <el-option
              label="网络设备"
              value="network"
            />
            <el-option
              label="安全设备"
              value="security"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="操作系统"
          prop="os"
        >
          <el-select
            v-model="deviceForm.os"
            placeholder="请选择"
            style="width: 100%"
          >
            <el-option
              label="Windows Server"
              value="Windows"
            />
            <el-option
              label="麒麟Linux"
              value="Kylin"
            />
            <el-option
              label="CentOS"
              value="CentOS"
            />
            <el-option
              label="Ubuntu"
              value="Ubuntu"
            />
            <el-option
              label="华为VRP"
              value="VRP"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="采集方式"
          prop="method"
        >
          <el-select
            v-model="deviceForm.method"
            placeholder="请选择"
            style="width: 100%"
          >
            <el-option
              label="SNMP"
              value="snmp"
            />
            <el-option
              label="SSH"
              value="ssh"
            />
            <el-option
              label="WMI"
              value="wmi"
            />
            <el-option
              label="API"
              value="api"
            />
            <el-option
              label="浏览器"
              value="browser"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="端口"
          prop="port"
        >
          <el-input-number
            v-model="deviceForm.port"
            :min="1"
            :max="65535"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="deviceForm.remark"
            type="textarea"
            :rows="3"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deviceDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSaveDevice"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Plus, Download, Edit, View, MoreFilled, DataLine,
  Server, Monitor, Connection, Bell, Laptop, SetUp
} from '@element-plus/icons-vue'

const loading = ref(false)
const exportLoading = ref(false)
const searchText = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const osFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(50)
const selectedRows = ref([])

// 统计卡片数据
const statsData = reactive([
  { key: 'total', title: '设备总数', value: 50, icon: 'Server' },
  { key: 'online', title: '在线设备', value: 45, icon: 'CircleCheck', alert: false },
  { key: 'offline', title: '离线设备', value: 3, icon: 'CircleClose', alert: true },
  { key: 'maintenance', title: '维护中', value: 2, icon: 'Setting', alert: false }
])

// 设备列表数据
const devicesData = ref([
  { id: 1, name: 'Web服务器-01', ip: '192.168.1.101', type: 'windows', os: 'Windows Server 2019', status: 'online', method: 'wmi', cpu: 45, memory: 68, disk: 52, lastCollect: '3分钟前' },
  { id: 2, name: '数据库服务器', ip: '192.168.1.102', type: 'linux', os: 'Kylin Linux V10', status: 'online', method: 'ssh', cpu: 32, memory: 75, disk: 61, lastCollect: '2分钟前' },
  { id: 3, name: '核心交换机-CORE-01', ip: '192.168.1.1', type: 'network', os: 'VRP 8.180', status: 'online', method: 'snmp', cpu: 15, memory: 40, disk: 0, lastCollect: '1分钟前' },
  { id: 4, name: '防火墙-FW-01', ip: '192.168.1.254', type: 'security', os: 'TopSec OS', status: 'online', method: 'api', cpu: 25, memory: 55, disk: 30, lastCollect: '5分钟前' },
  { id: 5, name: 'App服务器-01', ip: '192.168.1.103', type: 'linux', os: 'CentOS 7.9', status: 'offline', method: 'ssh', cpu: 0, memory: 0, disk: 58, lastCollect: '2小时前' },
  { id: 6, name: '负载均衡器', ip: '192.168.1.10', type: 'network', os: 'VRP 8.180', status: 'online', method: 'snmp', cpu: 20, memory: 45, disk: 0, lastCollect: '1分钟前' },
  { id: 7, name: '日志服务器', ip: '192.168.1.110', type: 'linux', os: 'Ubuntu 22.04', status: 'maintenance', method: 'ssh', cpu: 8, memory: 30, disk: 72, lastCollect: '30分钟前' },
  { id: 8, name: 'IDS入侵检测', ip: '192.168.1.200', type: 'security', os: 'NSFOCUS 5.0', status: 'online', method: 'api', cpu: 35, memory: 62, disk: 45, lastCollect: '4分钟前' }
])

// 对话框
const deviceDialogVisible = ref(false)
const isEdit = ref(false)
const deviceFormRef = ref(null)
const deviceForm = reactive({
  name: '',
  ip: '',
  type: '',
  os: '',
  method: '',
  port: 22,
  remark: ''
})
const deviceRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  ip: [{ required: true, message: '请输入设备IP', trigger: 'blur' }],
  type: [{ required: true, message: '请选择设备类型', trigger: 'change' }],
  method: [{ required: true, message: '请选择采集方式', trigger: 'change' }]
}

const getTypeIcon = (type) => {
  const map = {
    windows: 'Monitor',
    linux: 'Laptop',
    network: 'Connection',
    security: 'Bell'
  }
  return map[type] || 'Server'
}

const getTypeText = (type) => {
  const map = {
    windows: 'Windows',
    linux: 'Linux',
    network: '网络',
    security: '安全'
  }
  return map[type] || type
}

const getTypeTagType = (type) => {
  const map = {
    windows: '',
    linux: 'success',
    network: 'warning',
    security: 'danger'
  }
  return map[type] || 'info'
}

const getStatusText = (status) => {
  const map = {
    online: '在线',
    offline: '离线',
    maintenance: '维护中'
  }
  return map[status] || status
}

const getCollectMethod = (method) => {
  const map = {
    snmp: 'SNMP',
    ssh: 'SSH',
    wmi: 'WMI',
    api: 'API',
    browser: '浏览器'
  }
  return map[method] || method
}

const getMetricColor = (value) => {
  if (value >= 80) return '#f53f3f'
  if (value >= 60) return '#ff7d00'
  return '#00b42a'
}

const handleSearch = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    ElMessage.success('搜索完成')
  }, 500)
}

const handleFilterChange = () => {
  handleSearch()
}

const handleRefresh = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    ElMessage.success('刷新成功')
  }, 800)
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const handleCreate = () => {
  isEdit.value = false
  Object.assign(deviceForm, { name: '', ip: '', type: '', os: '', method: '', port: 22, remark: '' })
  deviceDialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(deviceForm, row)
  deviceDialogVisible.value = true
}

const handleView = (row) => {
  ElMessage.info('查看设备详情: ' + row.name)
}

const handleSaveDevice = async () => {
  if (!deviceFormRef.value) return
  await deviceFormRef.value.validate((valid) => {
    if (valid) {
      deviceDialogVisible.value = false
      ElMessage.success(isEdit.value ? '设备已更新' : '设备已添加')
    }
  })
}

const handleCollect = (row) => {
  ElMessage.info('正在采集: ' + row.name)
}

const handleCommand = (cmd, row) => {
  switch (cmd) {
    case 'delete':
      ElMessageBox.confirm(`确定删除设备 "${row.name}" 吗？`, '删除确认', {
        type: 'warning'
      }).then(() => {
        ElMessage.success('设备已删除')
      }).catch(() => {})
      break
    default:
      ElMessage.info('操作: ' + cmd)
  }
}

const handleExport = () => {
  exportLoading.value = true
  setTimeout(() => {
    exportLoading.value = false
    ElMessage.success('导出成功')
  }, 1000)
}

const handleBatchCollect = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择设备')
    return
  }
  ElMessage.info(`开始批量采集 ${selectedRows.value.length} 台设备`)
}

const handleSizeChange = (val) => {
  pageSize.value = val
}

const handlePageChange = (val) => {
  currentPage.value = val
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.devices-page {
  padding: $spacing-xl;
  min-height: 100%;
  background: $bg-page;
  animation: fadeIn 0.3s ease-out;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-xl;

  .page-header-left {
    .page-title {
      font-size: $font-size-xl;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin: 0 0 $space-2 0;
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

// 统计卡片
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.stat-card {
  background: $bg-container;
  border-radius: $radius-lg;
  padding: $spacing-lg;
  display: flex;
  align-items: center;
  gap: $spacing-md;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
  animation: fadeInUp 0.4s ease-out backwards;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-sm;
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #fff;

    &.total { background: linear-gradient(135deg, #165dff, #4080ff); }
    &.online { background: linear-gradient(135deg, #00b42a, #23c343); }
    &.offline { background: linear-gradient(135deg, #f53f3f, #ff7875); }
    &.maintenance { background: linear-gradient(135deg, #ff7d00, #ff9f40); }
  }

  .stat-content {
    .stat-value {
      font-size: 24px;
      font-weight: $font-weight-bold;
      color: $text-primary;
    }

    .stat-title {
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }

  .stat-pulse {
    position: absolute;
    right: $spacing-lg;
    top: 50%;
    transform: translateY(-50%);
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: $success;

    &.active {
      background: $danger;
      animation: pulse 1.5s infinite;
    }
  }
}

@keyframes pulse {
  0%, 100% { transform: translateY(-50%) scale(1); opacity: 1; }
  50% { transform: translateY(-50%) scale(1.3); opacity: 0.7; }
}

// 筛选栏
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-md $spacing-lg;
  background: $bg-container;
  border-radius: $radius-lg;
  margin-bottom: $spacing-lg;

  .filter-left {
    display: flex;
    gap: $spacing-sm;
    align-items: center;
  }

  .filter-right {
    display: flex;
    gap: $spacing-sm;
    align-items: center;
  }
}

// 表格卡片
.table-card {
  background: $bg-container;
  border-radius: $radius-lg;
  padding: $spacing-lg;
}

.devices-table {
  :deep(.el-table__header th) {
    background: $bg-page;
    font-weight: $font-weight-medium;
  }
}

// 设备信息单元格
.device-info {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  .device-icon {
    width: 40px;
    height: 40px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    color: #fff;

    &.windows { background: linear-gradient(135deg, #165dff, #4080ff); }
    &.linux { background: linear-gradient(135deg, #00b42a, #23c343); }
    &.network { background: linear-gradient(135deg, #722ed1, #9254de); }
    &.security { background: linear-gradient(135deg, #f53f3f, #ff7875); }
  }

  .device-details {
    display: flex;
    flex-direction: column;

    .device-name {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .device-ip {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }
}

// 状态单元格
.status-cell {
  display: flex;
  align-items: center;
  gap: $spacing-xs;

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.online { background: $success; }
    &.offline { background: $danger; }
    &.maintenance { background: $warning; }
  }

  .status-text {
    font-size: $font-size-sm;
  }
}

// 操作系统
.os-text {
  font-size: $font-size-sm;
  color: $text-secondary;
}

// 指标单元格
.metrics-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 180px;

  .metric-item {
    display: flex;
    align-items: center;
    gap: $spacing-xs;

    .metric-label {
      width: 32px;
      font-size: $font-size-xs;
      color: $text-placeholder;
    }

    :deep(.el-progress-bar__outer) {
      border-radius: 3px;
    }

    .metric-value {
      width: 40px;
      font-size: $font-size-xs;
      color: $text-secondary;
      text-align: right;
    }
  }
}

.last-collect {
  font-size: $font-size-xs;
  color: $text-placeholder;
}

// 分页
.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: $spacing-lg;
}

// 选项样式
.level-option,
.option-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.level-dot,
.option-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.server { background: #165dff; }
  &.network { background: #722ed1; }
  &.security { background: #f53f3f; }
  &.storage { background: #00b42a; }
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.online { background: $success; }
  &.offline { background: $danger; }
  &.maintenance { background: $warning; }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>