<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">设备监控</h1>
        <p class="page-subtitle">管理和监控所有设备状态</p>
      </div>
      <div class="page-actions">
        <el-button type="success" @click="scanDialogVisible = true">
          <el-icon><Connection /></el-icon> 网络扫描
        </el-button>
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加设备
        </el-button>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button type="info" @click="startAutoRefresh" v-if="!autoRefreshTimer">
          <el-icon><Timer /></el-icon> 自动刷新
        </el-button>
        <el-button type="warning" @click="stopAutoRefresh" v-else>
          <el-icon><Timer /></el-icon> 停止刷新
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索设备名称/IP/厂商" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterStatus" placeholder="设备状态" style="width: 120px" clearable @change="handleSearch">
        <el-option label="在线" value="online" />
        <el-option label="离线" value="offline" />
        <el-option label="告警" value="warning" />
      </el-select>
      <el-select v-model="filterType" placeholder="设备类型" style="width: 140px" clearable @change="handleSearch">
        <el-option label="服务器" value="server" />
        <el-option label="网络设备" value="network" />
        <el-option label="存储设备" value="storage" />
        <el-option label="安全设备" value="security" />
      </el-select>
      <el-select v-model="filterVendor" placeholder="设备厂商" style="width: 150px" clearable @change="handleSearch">
        <el-option v-for="v in vendorList" :key="v" :label="v" :value="v" />
      </el-select>
    </div>

    <!-- 设备列表 -->
    <div class="table-container">
      <el-table :data="deviceList" v-loading="loading" style="width: 100%" stripe>
        <el-table-column prop="name" label="设备名称" min-width="150" />
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column label="厂商/型号" width="180">
          <template #default="{ row }">
            <span v-if="row.manufacturer">{{ row.manufacturer }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="device_type" label="设备类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getTypeText(row.device_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="os_type" label="操作系统" width="120">
          <template #default="{ row }">
            <span v-if="row.os_type">{{ row.os_type }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="采集协议" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.protocols && row.protocols.ssh" type="success" size="small">SSH</el-tag>
            <el-tag v-if="row.protocols && row.protocols.snmp" type="warning" size="small">SNMP</el-tag>
            <el-tag v-if="row.protocols && row.protocols.http" type="info" size="small">HTTP</el-tag>
            <span v-if="!row.protocols || (!row.protocols.ssh && !row.protocols.snmp && !row.protocols.http)" class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_collect_time" label="最后采集" width="160">
          <template #default="{ row }">
            {{ formatTime(row.last_collect_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">查看</el-button>
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="primary" link size="small" @click="handleCollect(row)">采集</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- 设备详情弹窗 -->
    <el-dialog v-model="deviceDialogVisible" :title="dialogTitle" width="700px">
      <el-form :model="deviceForm" label-width="100px" :rules="deviceRules" ref="deviceFormRef">
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="deviceForm.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="IP地址" prop="ip">
          <el-input v-model="deviceForm.ip" placeholder="请输入IP地址" />
        </el-form-item>
        <el-form-item label="设备类型" prop="type">
          <el-select v-model="deviceForm.type" placeholder="请选择设备类型" style="width: 100%">
            <el-option label="服务器" value="server" />
            <el-option label="网络设备" value="network" />
            <el-option label="存储设备" value="storage" />
            <el-option label="安全设备" value="security" />
          </el-select>
        </el-form-item>
        <el-form-item label="厂商">
          <el-input v-model="deviceForm.vendor" placeholder="如: Cisco, Huawei, Dell" />
        </el-form-item>
        <el-form-item label="操作系统">
          <el-input v-model="deviceForm.os" placeholder="如: Linux, Windows, vSphere" />
        </el-form-item>
        <el-form-item label="协议配置">
          <el-checkbox v-model="deviceForm.protocols.ssh.enabled">SSH</el-checkbox>
          <el-checkbox v-model="deviceForm.protocols.snmp.enabled">SNMP</el-checkbox>
          <el-checkbox v-model="deviceForm.protocols.http.enabled">HTTP</el-checkbox>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="deviceForm.description" type="textarea" :rows="3" placeholder="请输入设备描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deviceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitDevice">确定</el-button>
      </template>
    </el-dialog>

    <!-- 设备详情查看 -->
    <el-dialog v-model="viewDialogVisible" title="设备详情" width="700px">
      <el-descriptions :column="2" border v-if="currentDevice">
        <el-descriptions-item label="设备名称">{{ currentDevice.name }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentDevice.ip_address }}</el-descriptions-item>
        <el-descriptions-item label="设备类型">{{ getTypeText(currentDevice.device_type) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentDevice.status)" size="small">{{ getStatusText(currentDevice.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="厂商">{{ currentDevice.manufacturer || '-' }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ currentDevice.model || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作系统">{{ currentDevice.os_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最后采集">{{ formatTime(currentDevice.last_collect_time) }}</el-descriptions-item>
        <el-descriptions-item label="采集协议" :span="2">
          <template v-if="currentDevice.protocols">
            <el-tag v-if="currentDevice.protocols.ssh" type="success" size="small" style="margin-right:4px">SSH</el-tag>
            <el-tag v-if="currentDevice.protocols.snmp" type="warning" size="small" style="margin-right:4px">SNMP</el-tag>
            <el-tag v-if="currentDevice.protocols.http" type="info" size="small">HTTP</el-tag>
          </template>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 网络扫描弹窗 -->
    <el-dialog v-model="scanDialogVisible" title="网络扫描" width="900px" :close-on-click-modal="false">
      <div v-if="!scanStarted">
        <el-form label-width="120px">
          <el-form-item label="扫描范围">
            <el-input v-model="scanForm.cidr" placeholder="例如：192.168.1.0/24 或 192.168.1.1" style="width: 280px" />
            <span style="margin-left: 12px; color: #909399; font-size: 13px;">支持 CIDR 格式或单个 IP</span>
          </el-form-item>
          <el-form-item label="扫描选项">
            <el-checkbox v-model="scanForm.scan_ports">扫描端口</el-checkbox>
            <el-checkbox v-model="scanForm.grab_banners">获取 banner</el-checkbox>
          </el-form-item>
          <el-form-item label="设备类型">
            <el-select v-model="scanForm.device_type" style="width: 200px">
              <el-option label="服务器" value="server" />
              <el-option label="网络设备" value="network" />
              <el-option label="存储设备" value="storage" />
              <el-option label="安全设备" value="security" />
            </el-select>
          </el-form-item>
          <el-form-item label="增强扫描">
            <el-switch v-model="scanForm.enhanced" active-text="开启" inactive-text="关闭" />
            <span style="margin-left: 12px; color: #909399; font-size: 13px;">
              开启后自动识别设备厂商/型号，并尝试默认凭据认证
            </span>
          </el-form-item>
        </el-form>
      </div>

      <!-- 扫描中状态 -->
      <div v-else-if="scanning" style="text-align: center; padding: 40px 0;">
        <el-icon class="is-loading" :size="40" color="#409eff"><Loading /></el-icon>
        <p style="margin-top: 16px; color: #606266;">正在扫描 {{ scanForm.cidr }}，请稍候...</p>
        <p v-if="scanForm.enhanced" style="margin-top: 8px; color: #67C23A; font-size: 13px;">
          增强模式：正在识别设备指纹和探测认证...
        </p>
        <p style="margin-top: 8px; color: #909399; font-size: 13px;">扫描完成前请勿关闭对话框</p>
      </div>

      <!-- 扫描结果 -->
      <div v-else>
        <el-alert v-if="scanError" type="error" :closable="false" style="margin-bottom: 16px">
          {{ scanError }}
        </el-alert>
        <div v-if="scanResults.length > 0" style="margin-bottom: 16px">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
            <span style="color: #606266;">发现 <strong style="color: #409eff">{{ scanResults.length }}</strong> 台主机</span>
            <div>
              <el-button type="primary" size="small" @click="handleImportSelected" :loading="importing" style="margin-right: 8px">
                导入选中 ({{ selectedHosts.length }})
              </el-button>
            </div>
          </div>
          <el-table :data="scanResults" @selection-change="handleSelectionChange" max-height="400" stripe>
            <el-table-column type="selection" width="50" />
            <el-table-column prop="ip" label="IP地址" width="130" />
            <el-table-column prop="hostname" label="主机名" min-width="130">
              <template #default="{ row }">{{ row.hostname || '-' }}</template>
            </el-table-column>
            <el-table-column label="厂商/型号" width="160">
              <template #default="{ row }">
                <span v-if="row.fingerprint && row.fingerprint.vendor">
                  <strong>{{ row.fingerprint.vendor }}</strong>
                  <span v-if="row.fingerprint.model" style="color: #909399"> / {{ row.fingerprint.model }}</span>
                </span>
                <span v-else-if="row.vendor">{{ row.vendor }}</span>
                <span v-else style="color: #c0c4cc">-</span>
              </template>
            </el-table-column>
            <el-table-column label="设备类型" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.fingerprint && row.fingerprint.category" size="small" type="info">
                  {{ getCategoryText(row.fingerprint.category) }}
                </el-tag>
                <el-tag v-else-if="row.os_type" size="small">{{ getTypeText(row.os_type) }}</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="开放端口" min-width="180">
              <template #default="{ row }">
                <span v-if="row.ports && row.ports.length">
                  {{ row.ports.slice(0, 6).join(', ') }}{{ row.ports.length > 6 ? '...' : '' }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="认证状态" width="100">
              <template #default="{ row }">
                <template v-if="row.auth_result && row.auth_result.accessible">
                  <el-tag type="success" size="small">已认证</el-tag>
                </template>
                <template v-else-if="row.fingerprint && row.fingerprint.possible_creds && row.fingerprint.possible_creds.length">
                  <el-tag type="warning" size="small">待验证</el-tag>
                </template>
                <el-tag v-else type="info" size="small">-</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'up' ? 'success' : 'info'" size="small">
                  {{ row.status === 'up' ? '在线' : '离线' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div v-else style="text-align: center; padding: 40px 0; color: #909399;">
          <p>未发现主机，请确认扫描范围是否正确</p>
        </div>
      </div>

      <template #footer>
        <el-button @click="closeScanDialog">关闭</el-button>
        <el-button v-if="!scanStarted" type="primary" @click="startScan" :loading="scanning">
          开始扫描
        </el-button>
        <el-button v-else-if="scanResults.length > 0" type="success" @click="handleImportAll">
          导入全部 ({{ scanResults.length }})
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Connection, Loading, Timer } from '@element-plus/icons-vue'
import request from '@/api/request'
import { devices } from '@/api'
import { formatTime } from '@/utils/date'
import { getStatusType, getStatusText } from '@/utils/status'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterType = ref('')
const filterVendor = ref('')
const deviceList = ref([])
const deviceDialogVisible = ref(false)
const viewDialogVisible = ref(false)
const dialogTitle = ref('添加设备')
const deviceFormRef = ref(null)
const currentDevice = ref(null)
const autoRefreshTimer = ref(null)

// 厂商列表（从扫描结果中发现）
const vendorList = ref([])

// 网络扫描相关
const scanDialogVisible = ref(false)
const scanStarted = ref(false)
const scanning = ref(false)
const scanForm = reactive({
  cidr: '',
  scan_ports: true,
  grab_banners: true,
  device_type: 'server',
  enhanced: true  // 默认开启增强扫描
})
const scanResults = ref([])
const selectedHosts = ref([])
const scanError = ref('')
const importing = ref(false)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const deviceForm = reactive({
  id: null,
  name: '',
  ip: '',
  type: 'server',
  vendor: '',
  os: '',
  description: '',
  protocols: {
    ssh: { enabled: false },
    snmp: { enabled: false },
    http: { enabled: false }
  }
})

const deviceRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  ip: [{ required: true, message: '请输入IP地址', trigger: 'blur' }],
  type: [{ required: true, message: '请选择设备类型', trigger: 'change' }]
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  stopAutoRefresh()
})

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterType.value) params.type = filterType.value
    if (filterVendor.value) params.vendor = filterVendor.value

    const res = await devices.getList(params).catch(() => ({ items: [], total: 0 }))
    deviceList.value = res.items || []
    pagination.total = res.total || 0

    // 提取厂商列表
    const vendors = [...new Set(deviceList.value.filter(d => d.vendor).map(d => d.vendor))]
    vendorList.value = vendors
  } catch (error) {
    console.error('Load devices error:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

// 自动刷新
const startAutoRefresh = () => {
  autoRefreshTimer.value = setInterval(() => {
    loadData()
    ElMessage({ message: '设备列表已刷新', type: 'info', duration: 1000 })
  }, 30000) // 30秒刷新一次
  ElMessage.success('已开启自动刷新（每30秒）')
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value)
    autoRefreshTimer.value = null
    ElMessage.warning('已停止自动刷新')
  }
}

const handleAdd = () => {
  dialogTitle.value = '添加设备'
  Object.assign(deviceForm, {
    id: null, name: '', ip: '', type: 'server', vendor: '', os: '',
    description: '', protocols: { ssh: { enabled: false }, snmp: { enabled: false }, http: { enabled: false } }
  })
  deviceDialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑设备'
  Object.assign(deviceForm, {
    id: row.name,  // device identity
    name: row.name,
    ip: row.ip,
    type: row.type || 'server',
    vendor: row.vendor || '',
    os: row.os || '',
    description: row.description || '',
    protocols: row.protocols || { ssh: { enabled: false }, snmp: { enabled: false }, http: { enabled: false } }
  })
  deviceDialogVisible.value = true
}

const handleView = (row) => {
  currentDevice.value = row
  viewDialogVisible.value = true
}

const handleCollect = async (row) => {
  try {
    ElMessage.info(`正在采集 ${row.name} 的指标...`)
    const res = await request.post('/devices/collect', {
      device_name: row.name
    })
    if (res.error) {
      ElMessage.warning(`${row.name} 采集失败: ${res.error}`)
    } else {
      ElMessage.success(`${row.name} 采集成功`)
      loadData()
    }
  } catch (error) {
    console.error('Collect error:', error)
    ElMessage.error('采集失败')
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除设备 "${row.name}" 吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await devices.delete(row.name)
      ElMessage.success('删除成功')
      loadData()
    } catch (error) {
      console.error('Delete device error:', error)
    }
  }).catch(() => {})
}

const submitDevice = async () => {
  const valid = await deviceFormRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    if (deviceForm.id) {
      await devices.update(deviceForm.id, deviceForm)
      ElMessage.success('更新成功')
    } else {
      await devices.create(deviceForm)
      ElMessage.success('添加成功')
    }
    deviceDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('Submit device error:', error)
  }
}

const getTypeText = (type) => {
  const map = { server: '服务器', network: '网络设备', storage: '存储设备', security: '安全设备' }
  return map[type] || type || '未知'
}

const getCategoryText = (category) => {
  const map = {
    server: '服务器', switch: '交换机', router: '路由器',
    firewall: '防火墙', wireless: '无线AP', storage: '存储',
    camera: '摄像头', loadbalancer: '负载均衡', ids_ips: '入侵检测',
    ups: 'UPS电源', other: '其他'
  }
  return map[category] || category || '其他'
}

// ===== 网络扫描 =====
const startScan = async () => {
  if (!scanForm.cidr.trim()) {
    ElMessage.warning('请输入扫描范围')
    return
  }
  scanning.value = true
  scanStarted.value = true
  scanResults.value = []
  scanError.value = ''
  selectedHosts.value = []

  try {
    const res = await request.post('/discovery/ip/scan/sync', {
      cidr: scanForm.cidr.trim(),
      scan_ports: scanForm.scan_ports,
      grab_banners: scanForm.grab_banners
    }, { params: { enhanced: scanForm.enhanced } })

    scanResults.value = (res.hosts || []).filter(h => h.status === 'up')
    if (scanResults.value.length === 0) {
      ElMessage.warning('未发现在线主机')
    } else {
      const mode = res.scan_mode === 'enhanced' ? '（增强模式）' : ''
      ElMessage.success(`发现 ${scanResults.value.length} 台在线主机${mode}`)
    }
  } catch (error) {
    console.error('Scan error:', error)
    scanError.value = '扫描失败：' + (error.message || '网络错误')
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedHosts.value = selection
}

const handleImportSelected = async () => {
  if (selectedHosts.value.length === 0) {
    ElMessage.warning('请先选择要导入的主机')
    return
  }
  await doImport(selectedHosts.value)
}

const handleImportAll = async () => {
  if (scanResults.value.length === 0) return
  await doImport(scanResults.value)
}

const doImport = async (hosts) => {
  importing.value = true
  try {
    const ips = hosts.map(h => h.ip)
    const res = await request.post('/discovery/devices/import', {
      ips: JSON.stringify(ips),
      device_type: scanForm.device_type
    })
    const imported = res.imported || []
    const failed = res.failed || []
    if (imported.length > 0) {
      ElMessage.success(`成功导入 ${imported.length} 台设备`)
    }
    if (failed.length > 0) {
      ElMessage.warning(`${failed.length} 台设备导入失败`)
    }
    if (imported.length > 0) {
      loadData()
      scanDialogVisible.value = false
      scanStarted.value = false
      scanForm.cidr = ''
    }
  } catch (error) {
    console.error('Import error:', error)
    ElMessage.error('导入失败：' + (error.message || '网络错误'))
  } finally {
    importing.value = false
  }
}

const closeScanDialog = () => {
  scanDialogVisible.value = false
  scanStarted.value = false
  scanResults.value = []
  scanError.value = ''
}
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.page-subtitle {
  margin: 4px 0 0;
  color: #909399;
  font-size: 13px;
}

.page-actions {
  display: flex;
  gap: 8px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
}

.table-container {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.text-muted {
  color: #c0c4cc;
}

:deep(.el-table) {
  .el-table__header th {
    background: #f7f8fa;
  }
}
</style>
