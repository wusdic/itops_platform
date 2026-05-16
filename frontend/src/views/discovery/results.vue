<template>
  <div>
    <div class="page-header">
      <h2>扫描结果</h2>
      <n-button type="primary" :disabled="!selectedRowKeys.length" @click="handleBatchImport">
        <template #icon><n-icon><DownloadOutline /></n-icon></template>
        批量导入 ({{ selectedRowKeys.length }})
      </n-button>
    </div>

    <n-card :bordered="false" style="margin-bottom:16px">
      <n-space :wrap="true" :size="12">
        <n-input v-model:value="search.keyword" placeholder="搜索IP/主机名" clearable style="width:220px" @keyup.enter="loadData" />
        <n-select v-model:value="search.group_id" placeholder="导入分组" clearable style="width:180px" :options="groupOptions" />
        <n-button type="primary" @click="loadData">
          <template #icon><n-icon><SearchOutline /></n-icon></template>
          搜索
        </n-button>
      </n-space>
    </n-card>

    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
        :remote="true"
        v-model:checked-row-keys="selectedRowKeys"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { SearchOutline, DownloadOutline, CheckmarkCircleOutline } from '@vicons/ionicons5'
import { listDiscoveredHosts, importDiscoveredHosts } from '@/api/discovery'
import { getDeviceGroups } from '@/api/asset'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const selectedRowKeys = ref([])
const search = reactive({ keyword: '', group_id: null })

const tableData = ref([])
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const groupOptions = ref([])

const columns = [
  { type: 'selection' },
  { title: 'IP', key: 'ip', width: 160 },
  { title: '主机名', key: 'hostname', ellipsis: { tooltip: true } },
  { title: 'MAC', key: 'mac', width: 180 },
  { title: '厂商', key: 'vendor', width: 140 },
  {
    title: '开放端口', key: 'open_ports', width: 200,
    render: row => {
      const ports = Array.isArray(row.open_ports) ? row.open_ports : (row.open_ports ? row.open_ports.split(',') : [])
      return ports.slice(0, 5).map(p => h('n-tag', { key: p, size: 'small', style: 'margin-right:4px' }, { default: () => String(p) })).concat(
        ports.length > 5 ? [h('n-tag', { size: 'small' }, { default: () => `+${ports.length - 5}` })] : []
      )
    }
  },
  {
    title: '操作系统', key: 'os', width: 140,
    render: row => row.os || row.os_type || '-'
  },
  {
    title: '发现时间', key: 'discovered_at', width: 170,
    render: row => row.discovered_at ? dayjs(row.discovered_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '状态', key: 'imported', width: 100,
    render: row => row.imported
      ? h('n-tag', { type: 'success', size: 'small' }, { default: () => '已导入' })
      : h('n-tag', { type: 'warning', size: 'small' }, { default: () => '未导入' })
  }
]

async function loadGroups() {
  try {
    const res = await getDeviceGroups()
    const items = res.data?.items || res.data || res.items || []
    groupOptions.value = items.map(g => ({ label: g.name, value: g.id }))
  } catch (e) {
    console.error(e)
  }
}

async function loadData(page) {
  if (page) pagination.page = page
  loading.value = true
  try {
    const res = await listDiscoveredHosts({
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: search.keyword || undefined
    })
    tableData.value = res.items || res.data?.items || []
    pagination.itemCount = res.total || res.data?.total || 0
  } catch (e) {
    message.error('加载扫描结果失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handlePageChange(p) { loadData(p) }
function handlePageSizeChange(ps) { pagination.pageSize = ps; pagination.page = 1; loadData() }

function handleBatchImport() {
  dialog.info({
    title: '确认导入',
    content: `确定要将选中的 ${selectedRowKeys.value.length} 台设备导入到资产库吗？`,
    positiveText: '确定导入',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const group_id = search.group_id || null
        await importDiscoveredHosts({
          host_ids: selectedRowKeys.value,
          group_id
        })
        message.success('导入成功')
        selectedRowKeys.value = []
        loadData()
      } catch (e) {
        message.error('导入失败')
        console.error(e)
      }
    }
  })
}

onMounted(() => {
  loadData()
  loadGroups()
})
</script>
