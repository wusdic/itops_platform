<template>
  <div>
    <div class="page-header">
      <h2>指标配置</h2>
      <n-button type="primary" @click="handleBatchUpdate">
        <template #icon><n-icon><SaveOutline /></n-icon></template>
        批量更新
      </n-button>
    </div>

    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
        remote
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </n-card>

    <!-- 指标配置弹窗 -->
    <n-modal v-model:show="configModalVisible" preset="card" :title="`指标配置 - ${currentDevice?.name || ''}`" style="width:600px">
      <n-form label-placement="left" label-width="100">
        <n-form-item v-for="cat in categories" :key="cat.key" :label="cat.label">
          <n-switch v-model:value="configForm[cat.key]" />
          <span style="margin-left:12px;color:#999;font-size:12px">{{ cat.desc }}</span>
        </n-form-item>
        <n-form-item label="采集间隔">
          <n-input-number v-model:value="configForm.interval" :min="5" :max="3600" style="width:140px" />
          <span style="margin-left:8px;color:#999">秒</span>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="configModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="configSubmitLoading" @click="handleConfigSubmit">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { SaveOutline, SettingsOutline } from '@vicons/ionicons5'
import { getDeviceList, listDeviceMetricConfigs, updateDeviceMetric } from '@/api/device'

const message = useMessage()

const loading = ref(false)
const configModalVisible = ref(false)
const configSubmitLoading = ref(false)
const currentDevice = ref(null)

const tableData = ref([])
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const categories = [
  { key: 'cpu', label: 'CPU', desc: '采集CPU使用率、负载等指标' },
  { key: 'memory', label: '内存', desc: '采集内存使用率、可用内存等指标' },
  { key: 'disk', label: '磁盘', desc: '采集磁盘使用率、IO等指标' },
  { key: 'network', label: '网络', desc: '采集网络流量、带宽等指标' }
]

const configForm = reactive({ cpu: true, memory: true, disk: true, network: true, interval: 30 })

const columns = [
  { title: '设备名称', key: 'name' },
  { title: '主机名', key: 'hostname', ellipsis: { tooltip: true } },
  { title: 'IP', key: 'ip', width: 140 },
  {
    title: '指标状态', key: 'metrics',
    render: row => h('n-space', { size: 4, wrap: true }, { default: () => {
      const metrics = row.metric_status || { cpu: false, memory: false, disk: false, network: false }
      return categories.map(cat => h('n-tag', {
        key: cat.key,
        type: metrics[cat.key] ? 'success' : 'default',
        size: 'small'
      }, { default: () => `${cat.label}${metrics[cat.key] ? ' ✓' : ''}` }))
    }})
  },
  { title: '采集间隔', key: 'collect_interval', width: 120, render: row => row.collect_interval ? `${row.collect_interval}s` : '-' },
  {
    title: '操作', key: 'actions', width: 120, fixed: 'right',
    render: row => h('n-button', { size: 'small', type: 'primary', quaternary: true, onClick: () => openConfigModal(row) }, {
      icon: () => h('n-icon', null, { default: () => h(SettingsOutline) }),
      default: () => '配置'
    })
  }
]

async function loadData(page) {
  if (page) pagination.page = page
  loading.value = true
  try {
    const res = await getDeviceList({ page: pagination.page, page_size: pagination.pageSize })
    const items = res.items || res.data?.items || []
    // 为每个设备加载指标配置
    tableData.value = items
    pagination.itemCount = res.total || res.data?.total || 0
  } catch (e) {
    message.error('加载设备列表失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handlePageChange(p) { loadData(p) }
function handlePageSizeChange(ps) { pagination.pageSize = ps; pagination.page = 1; loadData() }

async function openConfigModal(row) {
  currentDevice.value = row
  try {
    const res = await listDeviceMetricConfigs(row.id)
    const configs = res.data || res || {}
    configForm.cpu = configs.cpu?.enabled ?? true
    configForm.memory = configs.memory?.enabled ?? true
    configForm.disk = configs.disk?.enabled ?? true
    configForm.network = configs.network?.enabled ?? true
    configForm.interval = configs.interval || 30
  } catch (e) {
    console.error(e)
  }
  configModalVisible.value = true
}

async function handleConfigSubmit() {
  configSubmitLoading.value = true
  try {
    const device = currentDevice.value
    await updateDeviceMetric(device.id, 'all', {
      cpu: configForm.cpu,
      memory: configForm.memory,
      disk: configForm.disk,
      network: configForm.network,
      interval: configForm.interval
    })
    message.success('配置已更新')
    configModalVisible.value = false
    loadData()
  } catch (e) {
    message.error('更新失败')
    console.error(e)
  } finally {
    configSubmitLoading.value = false
  }
}

async function handleBatchUpdate() {
  message.info('请逐个设备配置指标采集')
}

onMounted(() => { loadData() })
</script>
