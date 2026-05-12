<template>
  <div class="devices-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>设备列表</span>
          <el-button type="primary" @click="refreshDevices">刷新</el-button>
        </div>
      </template>
      <el-table :data="devices" stripe>
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="ip" label="IP地址" />
        <el-table-column prop="type" label="设备类型" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'danger'">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const devices = ref([])

const refreshDevices = async () => {
  try {
    const res = await fetch('/api/devices')
    if (res.ok) {
      devices.value = await res.json()
    }
  } catch (e) {
    ElMessage.error('获取设备列表失败')
  }
}

onMounted(() => {
  refreshDevices()
})
</script>

<style scoped>
.devices-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
