<template>
  <div class="page-container">
    <n-card title="备份管理" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleCreate" :loading="creating">
          <template #icon><n-icon><CloudUploadOutline /></n-icon></template>
          创建备份
        </n-button>
      </template>

      <template #header>
        <n-tabs v-model:value="filterType" type="segment" @update:value="loadData">
          <n-tab name="">全部</n-tab>
          <n-tab name="full">全量备份</n-tab>
          <n-tab name="incremental">增量备份</n-tab>
        </n-tabs>
      </template>

      <n-input v-model:value="searchKeyword" placeholder="搜索备份名称" clearable style="width: 200px; margin-bottom: 12px" @change="loadData">
        <template #prefix><n-icon><SearchOutline /></n-icon></template>
      </n-input>

      <n-data-table
        :columns="columns"
        :data="backupList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 执行结果抽屉 -->
    <n-drawer v-model:show="resultDrawer" :width="600" placement="right">
      <n-drawer-content title="执行结果">
        <n-spin :show="executing">
          <n-input type="textarea" :value="executeResult" :rows="15" readonly placeholder="暂无执行结果" />
        </n-spin>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NTabs, NTab, NInput, NSpace, NTag, NIcon, NDrawer, NDrawerContent, NSpin, NInputGroup, useMessage } from 'naive-ui'
import { CloudUploadOutline, SearchOutline, PlayOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const creating = ref(false)
const executing = ref(false)
const backupList = ref([])
const searchKeyword = ref('')
const filterType = ref('')
const resultDrawer = ref(false)
const executeResult = ref('')

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '备份名称', key: 'name', ellipsis: { tooltip: true } },
  {
    title: '类型', key: 'type', width: 100,
    render: (r) => h(NTag, { size: 'small', type: r.type === 'full' ? 'success' : 'info' },
      () => r.type === 'full' ? '全量' : '增量')
  },
  { title: '大小', key: 'size', width: 100 },
  { title: '创建人', key: 'creator_name', width: 120 },
  { title: '状态', key: 'status', width: 100,
    render: (r) => {
      const map = { completed: 'success', failed: 'error', running: 'warning' }
      const text = { completed: '完成', failed: '失败', running: '进行中' }
      return h(NTag, { size: 'small', type: map[r.status] || 'default' }, () => text[r.status] || r.status)
    }
  },
  { title: '备份时间', key: 'created_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'info', disabled: row.status !== 'completed', onClick: () => handleDownload(row) }, () => '下载'),
        h(NButton, { size: 'small', quaternary: true, type: 'error', disabled: row.status !== 'completed', onClick: () => handleDelete(row) }, () => '删除')
      ])
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({ page: pagination.page, page_size: pagination.pageSize })
    if (filterType.value) params.append('type', filterType.value)
    if (searchKeyword.value) params.append('search', searchKeyword.value)
    const res = await fetch(`/api/v1/admin/backups?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) {
      if (res.status === 500) {
        message.warning('备份功能暂无可用数据')
        backupList.value = []
        return
      }
      throw new Error(`HTTP ${res.status}`)
    }
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    backupList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载备份失败: ${e.message}`)
    console.error('[backup] loadData error:', e)
    backupList.value = []
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/admin/backups', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ type: 'full', name: `backup_${Date.now()}` })
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const result = await res.json()
    message.success('备份创建成功')
    loadData()
  } catch (e) {
    message.error(`创建备份失败: ${e.message}`)
    console.error('[backup] create error:', e)
  } finally {
    creating.value = false
  }
}

function handleDownload(row) {
  message.info(`下载功能开发中: ${row.name}`)
}

async function handleDelete(row) {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/admin/backups/${row.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error(`删除失败: ${e.message}`)
    console.error('[backup] delete error:', e)
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
