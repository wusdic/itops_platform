<template>
  <div class="devices-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>设备管理</h2>
      <div class="header-actions">
        <el-button @click="handleDownloadTemplate">
          <el-icon><Download /></el-icon> 下载模板
        </el-button>
        <el-button type="success" @click="openImportDialog">
          <el-icon><Upload /></el-icon> 批量导入
        </el-button>
        <el-button type="primary" @click="openAddDialog">
          <el-icon><Plus /></el-icon> 添加设备
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="searchText"
        placeholder="搜索设备名称/IP"
        style="width: 240px"
        clearable
        @clear="loadDevices"
        @keyup.enter="loadDevices"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="typeFilter" placeholder="设备类型" clearable style="width: 140px" @change="loadDevices">
        <el-option label="服务器" value="server" />
        <el-option label="网络设备" value="network" />
        <el-option label="安全设备" value="security" />
        <el-option label="存储设备" value="storage" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="loadDevices">
        <el-option label="在线" value="online" />
        <el-option label="离线" value="offline" />
        <el-option label="维护中" value="maintenance" />
      </el-select>
      <el-button @click="loadDevices"><el-icon><Refresh /></el-icon> 刷新</el-button>
    </div>

    <!-- 设备列表 -->
    <div class="device-table">
      <el-table :data="devicesData" v-loading="loading" stripe @row-click="handleRowClick">
        <el-table-column prop="name" label="设备名称" min-width="150" />
        <el-table-column prop="hostname" label="主机名" min-width="120" />
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <span class="type-tag">{{ typeText(row.type) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <span class="status-tag" :class="row.status">{{ statusText(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="os_type" label="操作系统" width="100" />
        <el-table-column prop="location" label="位置" min-width="120" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="openEditDialog(row)">编辑</el-button>
            <el-button type="primary" link @click.stop="handleSyncConfig(row)">配置</el-button>
            <el-button type="danger" link @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalCount"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑设备' : '添加设备'"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="deviceForm" :rules="rules" label-width="100px">
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="deviceForm.name" placeholder="如：Web服务器-01" />
        </el-form-item>
        <el-form-item label="主机名" prop="hostname">
          <el-input v-model="deviceForm.hostname" placeholder="服务器主机名" />
        </el-form-item>
        <el-form-item label="IP地址" prop="ip_address">
          <el-input v-model="deviceForm.ip_address" placeholder="如：192.168.1.100" />
        </el-form-item>
        <el-form-item label="设备类型" prop="type">
          <el-select v-model="deviceForm.type" style="width: 100%">
            <el-option label="服务器" value="server" />
            <el-option label="网络设备" value="network" />
            <el-option label="安全设备" value="security" />
            <el-option label="存储设备" value="storage" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作系统" prop="os_type">
          <el-select v-model="deviceForm.os_type" style="width: 100%">
            <el-option label="Windows Server" value="windows" />
            <el-option label="CentOS" value="centos" />
            <el-option label="Ubuntu" value="ubuntu" />
            <el-option label="麒麟Linux" value="kylin" />
            <el-option label="华为VRP" value="vrp" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="deviceForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="deviceForm.username" placeholder="SSH用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="deviceForm.password" type="password" show-password placeholder="SSH密码" />
        </el-form-item>
        <el-form-item label="位置" prop="location">
          <el-input v-model="deviceForm.location" placeholder="如：机房A-机柜3" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="deviceForm.description" type="textarea" :rows="2" placeholder="设备描述信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="批量导入设备"
      width="700px"
      :close-on-click-modal="false"
    >
      <div class="import-guide">
        <el-alert type="info" :closable="false" show-icon>
          <template #title>
            <span>导入说明</span>
          </template>
          <template #default>
            <p>1. 请先 <el-button type="primary" link @click="handleDownloadTemplate">下载导入模板</el-button></p>
            <p>2. 按照模板格式填写设备信息（<strong>设备名称</strong>、<strong>IP地址</strong>、<strong>设备类型</strong>为必填项）</p>
            <p>3. 支持的文件格式：Excel (.xlsx) 或 CSV (.csv)</p>
            <p>4. 支持部分成功：有效行会创建设备，无效行会显示错误原因</p>
          </template>
        </el-alert>
        
        <el-form class="import-form" label-width="100px">
          <el-form-item label="选择文件">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              accept=".xlsx,.xls,.csv"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
            >
              <el-button type="primary">选择文件</el-button>
              <template #tip>
                <div class="el-upload__tip">支持 xlsx、xls、csv 格式</div>
              </template>
            </el-upload>
          </el-form-item>
          <el-form-item label="文件格式">
            <el-radio-group v-model="importFormat">
              <el-radio label="xlsx">Excel (.xlsx)</el-radio>
              <el-radio label="csv">CSV (.csv)</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 导入结果 -->
      <div v-if="importResult" class="import-result">
        <el-divider>导入结果</el-divider>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="总行数" :value="importResult.total" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="成功" :value="importResult.success_count" value-style="color: #00b42a" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="失败" :value="importResult.failed_count" value-style="color: #f56c6c" />
          </el-col>
        </el-row>
        
        <el-table 
          v-if="importResult.results && importResult.results.length > 0" 
          :data="importResult.results" 
          max-height="300"
          stripe
          style="margin-top: 16px"
        >
          <el-table-column prop="row" label="行号" width="60" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                {{ row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="设备名称" min-width="120" show-overflow-tooltip />
          <el-table-column prop="device_id" label="设备ID" width="80">
            <template #default="{ row }">
              <span v-if="row.device_id">{{ row.device_id }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="error" label="错误信息" min-width="150" show-overflow-tooltip />
        </el-table>
      </div>
      
      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 设备详情抽屉 -->
    <el-drawer v-model="detailVisible" title="设备详情" size="500px">
      <div v-if="currentDevice" class="device-detail">
        <div class="detail-row"><span class="label">设备名称</span><span class="value">{{ currentDevice.name }}</span></div>
        <div class="detail-row"><span class="label">主机名</span><span class="value">{{ currentDevice.hostname }}</span></div>
        <div class="detail-row"><span class="label">IP地址</span><span class="value">{{ currentDevice.ip_address }}</span></div>
        <div class="detail-row"><span class="label">类型</span><span class="value">{{ typeText(currentDevice.type) }}</span></div>
        <div class="detail-row"><span class="label">状态</span><span class="value status-tag" :class="currentDevice.status">{{ statusText(currentDevice.status) }}</span></div>
        <div class="detail-row"><span class="label">操作系统</span><span class="value">{{ currentDevice.os_type }}</span></div>
        <div class="detail-row"><span class="label">位置</span><span class="value">{{ currentDevice.location }}</span></div>
        <div class="detail-row"><span class="label">描述</span><span class="value">{{ currentDevice.description }}</span></div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Download, Upload } from '@element-plus/icons-vue'
import { devices } from '@/api'

// 状态
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const isEdit = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const searchText = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const formRef = ref(null)
const devicesData = ref([])
const currentDevice = ref(null)

// 批量导入相关
const importDialogVisible = ref(false)
const importFormat = ref('xlsx')
const importFile = ref(null)
const importResult = ref(null)
const importing = ref(false)
const uploadRef = ref(null)

// 表单
const deviceForm = reactive({
  name: '',
  hostname: '',
  ip_address: '',
  type: 'server',
  os_type: 'centos',
  port: 22,
  username: '',
  password: '',
  location: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  ip_address: [{ required: true, message: '请输入IP地址', trigger: 'blur' }],
  type: [{ required: true, message: '请选择设备类型', trigger: 'change' }]
}

onMounted(() => {
  loadDevices()
})

const loadDevices = async () => {
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (searchText.value) params.keyword = searchText.value
    if (typeFilter.value) params.type = typeFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    
    const res = await devices.getDevices(params)
    devicesData.value = res.items || res.data?.items || []
    totalCount.value = res.total || res.data?.total || 0
  } catch (error) {
    ElMessage.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

const openAddDialog = () => {
  isEdit.value = false
  Object.assign(deviceForm, {
    name: '', hostname: '', ip_address: '', type: 'server',
    os_type: 'centos', port: 22, username: '', password: '',
    location: '', description: ''
  })
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  Object.assign(deviceForm, { ...row, password: '' })
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    saving.value = true
    
    if (isEdit.value) {
      await devices.updateDevice(deviceForm.id, deviceForm)
      ElMessage.success('设备已更新')
    } else {
      await devices.createDevice(deviceForm)
      ElMessage.success('设备已添加')
    }
    
    dialogVisible.value = false
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.detail || '保存失败')
    }
  } finally {
    saving.value = false
  }
}

const handleRowClick = (row) => {
  currentDevice.value = row
  detailVisible.value = true
}

const handleSyncConfig = async (row) => {
  try {
    await devices.syncConfig(row.id)
    ElMessage.success('配置同步成功')
  } catch (error) {
    ElMessage.error('配置同步失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除设备 "${row.name}" 吗？`, '删除确认', { type: 'warning' })
    await devices.deleteDevice(row.id)
    ElMessage.success('设备已删除')
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  loadDevices()
}

const handlePageChange = (val) => {
  currentPage.value = val
  loadDevices()
}

const typeText = (type) => {
  const map = { server: '服务器', network: '网络设备', security: '安全设备', storage: '存储设备' }
  return map[type] || type
}

const statusText = (status) => {
  const map = { online: '在线', offline: '离线', maintenance: '维护中' }
  return map[status] || status
}

// 批量导入相关方法
const openImportDialog = () => {
  importDialogVisible.value = true
  importResult.value = null
  importFile.value = null
}

const handleDownloadTemplate = async () => {
  try {
    const format = importFormat.value || 'xlsx'
    const response = await devices.getImportTemplate(format)
    
    // 创建blob下载
    const blob = new Blob([response], { 
      type: format === 'csv' ? 'text/csv;charset=utf-8' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `device_import_template.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('模板下载成功')
  } catch (error) {
    console.error('下载模板失败:', error)
    ElMessage.error('下载模板失败')
  }
}

const handleFileChange = (file) => {
  importFile.value = file.raw
}

const handleFileRemove = () => {
  importFile.value = null
}

const handleImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请先选择要导入的文件')
    return
  }
  
  importing.value = true
  try {
    const response = await devices.importDevices(importFile.value)
    
    if (response.code === 0) {
      importResult.value = response.data
      ElMessage.success(`导入完成: 成功${response.data.success_count}行, 失败${response.data.failed_count}行`)
      // 刷新设备列表
      loadDevices()
    } else {
      ElMessage.error(response.message || '导入失败')
    }
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  } finally {
    importing.value = false
  }
}
</script>

<style lang="scss" scoped>
.devices-page {
  background: #f7f8fa;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #1d2129;
  }
  
  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.filter-bar {
  background: #fff;
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
  align-items: center;
}

.device-table {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}

.type-tag {
  font-size: 12px;
  padding: 2px 8px;
  background: #e8f0ff;
  color: #165dff;
  border-radius: 4px;
}

.status-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  &.online { background: #e8ffea; color: #00b42a; }
  &.offline { background: #f7f8fa; color: #86909c; }
  &.maintenance { background: #fff7e6; color: #ff7d00; }
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.device-detail {
  .detail-row {
    display: flex;
    padding: 12px 0;
    border-bottom: 1px solid #f2f3f5;
    .label {
      width: 100px;
      color: #86909c;
      font-size: 14px;
    }
    .value {
      flex: 1;
      color: #1d2129;
      font-size: 14px;
    }
  }
}
</style>
