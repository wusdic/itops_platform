<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">设备监控</h1>
        <p class="page-subtitle">管理和监控所有设备状态</p>
      </div>
      <div class="page-actions">
        <n-button type="primary" @click="handleAdd">
          <n-icon><AddOutline /></n-icon> 添加设备
        </n-button>
        <n-button @click="loadData">
          <n-icon><RefreshOutline /></n-icon> 刷新
        </n-button>
      </div>
    </div>
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <n-input v-model="searchKeyword" placeholder="搜索设备名称/IP" style="width: 200px" clearable @change="handleSearch" />
      <n-select v-model="filterStatus" placeholder="设备状态" style="width: 120px" clearable @change="handleSearch">
        <n-option label="在线" value="online" />
        <n-option label="离线" value="offline" />
        <n-option label="告警" value="warning" />
      </n-select>
      <n-select v-model="filterType" placeholder="设备类型" style="width: 140px" clearable @change="handleSearch">
        <n-option label="服务器" value="server" />
        <n-option label="网络设备" value="network" />
        <n-option label="存储设备" value="storage" />
        <n-option label="安全设备" value="security" />
      </n-select>
    </div>
    <!-- 设备列表 -->
    <div class="table-container">
      <n-data-table :data="deviceList" style="width: 100%">
        <n-data-table-column prop="name" label="设备名称" min-width="150" />
        <n-data-table-column prop="ip" label="IP地址" width="140" />
        <n-data-table-column prop="type" label="设备类型" width="100">
          <template #default="{ row }">
            <n-tag size="small">{{ getTypeText(row.type) }}</n-tag>
          </template>
        <n-data-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <n-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </n-tag>
          </template>
        <n-data-table-column prop="cpu" label="CPU" width="100">
          <template #default="{ row }">
            <n-progress :percentage="row.cpu || 0" :color="getProgressColor(row.cpu)" :stroke-width="6" />
          </template>
        <n-data-table-column prop="memory" label="内存" width="100">
          <template #default="{ row }">
            <n-progress :percentage="row.memory || 0" :color="getProgressColor(row.memory)" :stroke-width="6" />
          </template>
        <n-data-table-column prop="disk" label="磁盘" width="100">
          <template #default="{ row }">
            <n-progress :percentage="row.disk || 0" :color="getProgressColor(row.disk)" :stroke-width="6" />
          </template>
        <n-data-table-column prop="updated_at" label="最后更新" width="160">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        <n-data-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <n-button type="primary" link size="small" @click="handleView(row)">查看</n-button>
            <n-button type="primary" link size="small" @click="handleEdit(row)">编辑</n-button>
            <n-button type="danger" link size="small" @click="handleDelete(row)">删除</n-button>
          </template>
      <div class="pagination">
        <n-pagination
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
    <n-modal v-model="deviceDialogVisible" :title="dialogTitle" width="700px">
      <n-form :model="deviceForm" label-width="100px" :rules="deviceRules" ref="deviceFormRef">
        <n-form-item label="设备名称" prop="name">
          <n-input v-model="deviceForm.name" placeholder="请输入设备名称" />
        </n-form-item>
        <n-form-item label="IP地址" prop="ip">
          <n-input v-model="deviceForm.ip" placeholder="请输入IP地址" />
        </n-form-item>
        <n-form-item label="设备类型" prop="type">
          <n-select v-model="deviceForm.type" placeholder="请选择设备类型" style="width: 100%">
            <n-option label="服务器" value="server" />
            <n-option label="网络设备" value="network" />
            <n-option label="存储设备" value="storage" />
            <n-option label="安全设备" value="security" />
          </n-select>
        </n-form-item>
        <n-form-item label="设备描述">
          <n-input v-model="deviceForm.description" type="textarea" :rows="3" placeholder="请输入设备描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="deviceDialogVisible = false">取消</n-button>
        <n-button type="primary" @click="submitDevice">确定</n-button>
      </template>
    </n-modal>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
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
  ip: '',
  type: '',
  description: ''
})
const deviceRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  ip: [{ required: true, message: '请输入IP地址', trigger: 'blur' }],
  type: [{ required: true, message: '请选择设备类型', trigger: 'change' }]
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
  Object.assign(deviceForm, { id: null, name: '', ip: '', type: '', description: '' })
  deviceDialogVisible.value = true
}
const handleEdit = (row) => {
  dialogTitle.value = '编辑设备'
  Object.assign(deviceForm, { id: row.id, name: row.name, ip: row.ip, type: row.type, description: row.description || '' })
  deviceDialogVisible.value = true
}
const handleView = (row) => {
  message.info(`查看设备: ${row.name}`)
}
const handleDelete = (row) => {
  dialog.warning({ title: '提示', content: `确定要删除设备 "${row.name}" 吗?`, positiveText: '确定', negativeText: '取消', onPositiveClick: () => { }, onNegativeClick: () => { } })
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await devices.delete(row.id)
      message.success('删除成功')
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
      message.success('更新成功')
    } else {
      await devices.create(deviceForm)
      message.success('添加成功')
    }
    deviceDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('Submit device error:', error)
  }
}
const getTypeText = (type) => {
  const map = { server: '服务器', network: '网络设备', storage: '存储设备', security: '安全设备' }
  return map[type] || type
}
const getProgressColor = (value) => {
  if (value >= 90) return '#f53f3f'
  if (value >= 70) return '#ff7d00'
  return '#00b42a'
}
</script>
<style lang="scss" scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
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
