<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">参数配置</h1>
        <p class="page-subtitle">系统参数配置管理</p>
      </div>
    </div>
    <div class="table-container">
      <n-data-table :data="configList" style="width: 100%">
        <n-data-table-column prop="key" label="配置键" min-width="200" />
        <n-data-table-column prop="value" label="配置值" min-width="300">
          <template #default="{ row }">
            <span v-if="!row.editing">{{ row.value }}</span>
            <n-input v-else v-model="row.editValue" size="small" style="width: 200px" />
          </template>
        <n-data-table-column prop="description" label="描述" min-width="200" />
        <n-data-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        <n-data-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <template v-if="!row.editing">
              <n-button type="primary" link size="small" @click="handleEdit(row)">编辑</n-button>
            </template>
            <template v-else>
              <n-button type="primary" link size="small" @click="handleSave(row)">保存</n-button>
              <n-button type="info" link size="small" @click="row.editing = false">取消</n-button>
            </template>
          </template>
    </div>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { config as configApi } from '@/api'
import { formatTime } from '@/utils/date'
const loading = ref(false)
const configList = ref([])
onMounted(() => { loadData() })
const loadData = async () => {
  loading.value = true
  try {
    const res = await configApi.getList().catch(() => [])
    configList.value = (res || []).map(c => ({ ...c, editing: false, editValue: c.value }))
  } catch (error) { console.error('Load config error:', error) }
  finally { loading.value = false }
}
const handleEdit = (row) => { row.editing = true; row.editValue = row.value }
const handleSave = async (row) => {
  try {
    await configApi.update(row.key, { value: row.editValue })
    row.value = row.editValue
    row.editing = false
    message.success('保存成功')
  } catch (error) { console.error('Save error:', error) }
}
</script>
<style lang="scss" scoped>
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
