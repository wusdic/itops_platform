<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">设备监控</h1>
        <p class="page-subtitle">管理和监控所有设备状态</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加设备
        </el-button>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索设备名称/IP" style="width: 200px" clearable @change="handleSearch" />
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
    </div>

    <!-- 设备列表 -->
    <div class="table-container">
      <el-table :data="deviceList" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="设备名称" min-width="150" />
        <el-table-column prop="ip_address" label="IP地址" width="140" />
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
        <el-table-column prop="os_type" label="操作系统" width="100" />
        <el-table-column prop="network_interfaces" label="开放端口" width="200">
          <template #default="{ row }">
            {{ row.network_interfaces || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最后更新" width="160">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">查看</el-button>
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
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
        <el-form-item label="IP地址" prop="ip_address">
          <el-input v-model="deviceForm.ip_address" placeholder="请输入IP地址" />
        </el-form-item>
        <el-form-item label="设备类型" prop="device_type">
          <el-select v-model="deviceForm.device_type" placeholder="请选择设备类型" style="width: 100%">
            <el-option label="服务器" value="SERVER_LINUX" />
            <el-option label="Windows服务器" value="SERVER_WINDOWS" />
            <el-option label="网络设备" value="NETWORK_SWITCH" />
            <el-option label="存储设备" value="STORAGE_NAS" />
            <el-option label="安全设备" value="SECURITY_IPS" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作系统" prop="os_type">
          <el-input v-model="deviceForm.os_type" placeholder="如: Linux, Windows" />
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { devices } from '@/api'
import { formatTime } from '@/utils/date'
import { getStatusType, getStatusText } from '@/utils/status'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterType = ref('')
const deviceList = ref([])
const deviceDialogVisible = ref(false)
const dialogTitle = ref('添加设备')
const deviceFormRef = ref(null)

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const deviceForm = reactive({
  id: null,
  name: '',
  ip_address: '',
  device_type: 'SERVER_LINUX',
  os_type: '',
  description: ''
})

const deviceRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  ip_address: [{ required: true, message: '请输入IP地址', trigger: 'blur' }],
  device_type: [{ required: true, message: '请选择设备类型', trigger: 'change' }]
}

onMounted(() => {
  loadData()
})

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchKeyword.value,
      status: filterStatus.value,
      type: filterType.value
    }
    const res = await devices.getList(params).catch(() => ({ items: [], total: 0 }))
    deviceList.value = res.items || res.data?.items || []
    pagination.total = res.total || res.data?.total || 0
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

const handleAdd = () => {
  dialogTitle.value = '添加设备'
  Object.assign(deviceForm, { id: null, name: '', ip_address: '', device_type: 'SERVER_LINUX', os_type: '', description: '' })
  deviceDialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑设备'
  Object.assign(deviceForm, {
    id: row.id,
    name: row.name,
    ip_address: row.ip_address,
    device_type: row.device_type,
    os_type: row.os_type || '',
    description: row.description || ''
  })
  deviceDialogVisible.value = true
}

const handleView = (row) => {
  ElMessage.info(`查看设备: ${row.name} (${row.ip_address})`)
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除设备 "${row.name}" 吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await devices.delete(row.id)
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
  const map = {
    SERVER_LINUX: 'Linux服务器',
    SERVER_WINDOWS: 'Windows服务器',
    SERVER_VMWARE: 'VMware虚拟机',
    SERVER_KVM: 'KVM虚拟机',
    NETWORK_SWITCH: '交换机',
    NETWORK_ROUTER: '路由器',
    NETWORK_FIREWALL: '防火墙',
    NETWORK_WAF: 'WAF',
    NETWORK_LB: '负载均衡',
    STORAGE_NAS: 'NAS存储',
    STORAGE_ARRAY: '存储阵列',
    SECURITY_IPS: 'IPS',
    SECURITY_AMS: 'AMS',
    OTHER: '其他'
  }
  return map[type] || type || '未知'
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

:deep(.el-table) {
  .el-table__header th {
    background: #f7f8fa;
  }
}
</style>
