<template>
  <div class="metric-toggle-panel">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>采集项单项开关</span>
          <el-button type="primary" @click="loadDeviceMetricConfigs" :loading="loading">
            刷新
          </el-button>
        </div>
      </template>
      
      <!-- 设备选择 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="设备">
          <el-select
            v-model="selectedDeviceId"
            placeholder="选择设备"
            filterable
            @change="onDeviceChange"
            style="width: 200px"
          >
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            >
              <span>{{ device.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ device.ip }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="指标类别">
          <el-select
            v-model="selectedCategory"
            placeholder="选择类别"
            clearable
            @change="onCategoryChange"
            style="width: 150px"
          >
            <el-option label="CPU" value="cpu" />
            <el-option label="内存" value="memory" />
            <el-option label="磁盘" value="disk" />
            <el-option label="网络" value="network" />
            <el-option label="进程" value="process" />
            <el-option label="服务" value="service" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="selectedStatus"
            placeholder="选择状态"
            clearable
            @change="loadConfigs"
            style="width: 120px"
          >
            <el-option label="全部" :value="null" />
            <el-option label="已启用" :value="true" />
            <el-option label="已禁用" :value="false" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <!-- 统计信息 -->
      <div class="stats-panel" v-if="selectedDeviceId">
        <el-row :gutter="20">
          <el-col :span="6">
            <div class="stat-item">
              <span class="stat-label">总指标数</span>
              <span class="stat-value">{{ configs.length }}</span>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-item enabled">
              <span class="stat-label">已启用</span>
              <span class="stat-value">{{ enabledCount }}</span>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-item disabled">
              <span class="stat-label">已禁用</span>
              <span class="stat-value">{{ disabledCount }}</span>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-item">
              <span class="stat-label">启用率</span>
              <span class="stat-value">{{ enableRate }}%</span>
            </div>
          </el-col>
        </el-row>
      </div>
      
      <!-- 配置列表 -->
      <el-table
        v-loading="loading"
        :data="configs"
        style="width: 100%; margin-top: 20px"
        stripe
        border
      >
        <el-table-column prop="metric_category" label="类别" width="100">
          <template #default="{ row }">
            <el-tag :type="getCategoryTagType(row.metric_category)">
              {{ getCategoryName(row.metric_category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="metric_name" label="指标名称" min-width="150" />
        <el-table-column label="采集间隔" width="100">
          <template #default="{ row }">
            {{ row.collect_interval || '默认' }}
          </template>
        </el-table-column>
        <el-table-column label="告警阈值" width="150">
          <template #default="{ row }">
            <span v-if="row.alert_thresholds">{{ row.alert_thresholds }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开关" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              active-color="#13ce66"
              inactive-color="#ff4949"
              @change="handleToggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 空状态 -->
      <el-empty 
        v-if="!loading && configs.length === 0 && selectedDeviceId" 
        description="暂无采集项配置"
      >
        <el-button type="primary" @click="handleCreate">添加配置</el-button>
      </el-empty>
      
      <el-empty 
        v-if="!loading && !selectedDeviceId" 
        description="请先选择设备"
      />
    </el-card>
    
    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑采集项配置"
      width="500px"
    >
      <el-form :model="editingConfig" label-width="100px">
        <el-form-item label="指标类别">
          <el-input v-model="editingConfig.metric_category" disabled />
        </el-form-item>
        <el-form-item label="指标名称">
          <el-input v-model="editingConfig.metric_name" disabled />
        </el-form-item>
        <el-form-item label="采集间隔(秒)">
          <el-input-number 
            v-model="editingConfig.collect_interval" 
            :min="0" 
            :step="60"
            placeholder="0表示使用默认"
          />
        </el-form-item>
        <el-form-item label="告警阈值">
          <el-input
            v-model="editingConfig.alert_thresholds"
            placeholder='{"max": 90, "min": 10}'
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editingConfig.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveEdit">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 添加配置对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="添加采集项配置"
      width="500px"
    >
      <el-form :model="newConfig" label-width="100px">
        <el-form-item label="指标类别" required>
          <el-select v-model="newConfig.metric_category" style="width: 100%">
            <el-option label="CPU" value="cpu" />
            <el-option label="内存" value="memory" />
            <el-option label="磁盘" value="disk" />
            <el-option label="网络" value="network" />
            <el-option label="进程" value="process" />
            <el-option label="服务" value="service" />
          </el-select>
        </el-form-item>
        <el-form-item label="指标名称" required>
          <el-input v-model="newConfig.metric_name" placeholder="如: cpu_usage, memory_used_mb" />
        </el-form-item>
        <el-form-item label="采集间隔(秒)">
          <el-input-number 
            v-model="newConfig.collect_interval" 
            :min="0" 
            :step="60"
            placeholder="0表示使用默认"
          />
        </el-form-item>
        <el-form-item label="告警阈值">
          <el-input
            v-model="newConfig.alert_thresholds"
            placeholder='{"max": 90, "min": 10}'
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="newConfig.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleCreateConfig">添加</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { monitoring, devices as deviceApi } from '@/api'

export default {
  name: 'MetricTogglePanel',
  setup() {
    const loading = ref(false)
    const devices = ref([])
    const selectedDeviceId = ref(null)
    const selectedCategory = ref('')
    const selectedStatus = ref(null)
    const configs = ref([])
    const editDialogVisible = ref(false)
    const createDialogVisible = ref(false)
    const editingConfig = ref({})
    const newConfig = ref({
      device_id: null,
      metric_category: 'cpu',
      metric_name: '',
      collect_interval: 0,
      alert_thresholds: '',
      remark: ''
    })
    
    const enabledCount = computed(() => configs.value.filter(c => c.enabled).length)
    const disabledCount = computed(() => configs.value.filter(c => !c.enabled).length)
    const enableRate = computed(() => {
      if (configs.value.length === 0) return 0
      return Math.round((enabledCount.value / configs.value.length) * 100)
    })
    
    const loadDevices = async () => {
      try {
        const response = await deviceApi.getDevices({ page: 1, page_size: 1000 })
        devices.value = response.items || []
      } catch (error) {
        console.error('Failed to load devices:', error)
      }
    }
    
    const loadConfigs = async () => {
      if (!selectedDeviceId.value) {
        configs.value = []
        return
      }
      
      loading.value = true
      try {
        const params = { device_id: selectedDeviceId.value }
        if (selectedCategory.value) {
          params.metric_category = selectedCategory.value
        }
        if (selectedStatus.value !== null) {
          params.enabled = selectedStatus.value
        }
        
        const response = await monitoring.getMetricConfigs(params)
        configs.value = response.items || []
      } catch (error) {
        ElMessage.error('加载采集项配置失败')
        console.error(error)
      } finally {
        loading.value = false
      }
    }
    
    const loadDeviceMetricConfigs = async () => {
      if (!selectedDeviceId.value) return
      await loadConfigs()
    }
    
    const onDeviceChange = () => {
      selectedCategory.value = ''
      selectedStatus.value = null
      loadConfigs()
    }
    
    const onCategoryChange = () => {
      loadConfigs()
    }
    
    const handleToggle = async (config) => {
      try {
        await monitoring.toggleMetricConfig(config.id)
        ElMessage.success(`采集项已${config.enabled ? '启用' : '禁用'}`)
      } catch (error) {
        // 回滚状态
        config.enabled = !config.enabled
        ElMessage.error('切换失败')
        console.error(error)
      }
    }
    
    const handleEdit = (config) => {
      editingConfig.value = { ...config }
      editDialogVisible.value = true
    }
    
    const handleSaveEdit = async () => {
      try {
        await monitoring.updateMetricConfig(editingConfig.value.id, {
          collect_interval: editingConfig.value.collect_interval,
          alert_thresholds: editingConfig.value.alert_thresholds,
          remark: editingConfig.value.remark
        })
        ElMessage.success('保存成功')
        editDialogVisible.value = false
        loadConfigs()
      } catch (error) {
        ElMessage.error('保存失败')
        console.error(error)
      }
    }
    
    const handleDelete = async (config) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除采集项配置 "${config.metric_name}" 吗?`,
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        await monitoring.deleteMetricConfig(config.id)
        ElMessage.success('删除成功')
        loadConfigs()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
          console.error(error)
        }
      }
    }
    
    const handleCreate = () => {
      newConfig.value = {
        device_id: selectedDeviceId.value,
        metric_category: 'cpu',
        metric_name: '',
        collect_interval: 0,
        alert_thresholds: '',
        remark: ''
      }
      createDialogVisible.value = true
    }
    
    const handleCreateConfig = async () => {
      if (!newConfig.value.metric_name) {
        ElMessage.warning('请输入指标名称')
        return
      }
      
      try {
        await monitoring.createMetricConfig(newConfig.value)
        ElMessage.success('添加成功')
        createDialogVisible.value = false
        loadConfigs()
      } catch (error) {
        ElMessage.error('添加失败: ' + (error.message || '未知错误'))
        console.error(error)
      }
    }
    
    const getCategoryName = (category) => {
      const map = {
        cpu: 'CPU',
        memory: '内存',
        disk: '磁盘',
        network: '网络',
        process: '进程',
        service: '服务'
      }
      return map[category] || category
    }
    
    const getCategoryTagType = (category) => {
      const map = {
        cpu: 'danger',
        memory: 'warning',
        disk: 'success',
        network: 'info',
        process: '',
        service: ''
      }
      return map[category] || ''
    }
    
    onMounted(() => {
      loadDevices()
    })
    
    return {
      loading,
      devices,
      selectedDeviceId,
      selectedCategory,
      selectedStatus,
      configs,
      editDialogVisible,
      createDialogVisible,
      editingConfig,
      newConfig,
      enabledCount,
      disabledCount,
      enableRate,
      loadDeviceMetricConfigs,
      onDeviceChange,
      onCategoryChange,
      handleToggle,
      handleEdit,
      handleSaveEdit,
      handleDelete,
      handleCreate,
      handleCreateConfig,
      getCategoryName,
      getCategoryTagType
    }
  }
}
</script>

<style scoped>
.metric-toggle-panel {
  padding: 20px;
}

.box-card {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 0;
}

.stats-panel {
  margin: 20px 0;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.stat-item.enabled .stat-value {
  color: #67c23a;
}

.stat-item.disabled .stat-value {
  color: #f56c6c;
}
</style>
