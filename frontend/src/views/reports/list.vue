<template>
  <div>
    <div class="page-header">
      <h2>报表列表</h2>
      <n-button type="primary" @click="openGenerate">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        生成报表
      </n-button>
    </div>

    <!-- 筛选 -->
    <n-card :bordered="false" style="margin-bottom: 16px">
      <n-space :wrap="true">
        <n-input v-model:value="searchText" placeholder="搜索报表..."
          style="width: 200px" clearable @update:value="loadReports" />
        <n-select v-model:value="filterStatus" :options="statusOptions"
          placeholder="状态" style="width: 130px" clearable @update:value="loadReports" />
        <n-select v-model:value="filterTemplate" :options="templateOptions"
          placeholder="模板" style="width: 180px" clearable @update:value="loadReports" />
        <n-date-picker v-model:value="dateRange" type="daterange"
          placeholder="日期范围" clearable style="width: 240px"
          @update:value="loadReports" />
      </n-space>
    </n-card>

    <!-- 统计图表 -->
    <n-grid cols="2 s:1" responsive="screen" :x-gap="16" :y-gap="16" style="margin-bottom: 16px">
      <n-gi>
        <n-card title="状态分布" :bordered="false">
          <div ref="pieChartRef" style="height: 260px"></div>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="生成趋势" :bordered="false">
          <div ref="lineChartRef" style="height: 260px"></div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 报表列表 -->
    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="reports"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 生成报表弹窗 -->
    <n-modal v-model:show="showGenerateModal" preset="card" title="生成报表"
      style="width: 520px" :bordered="false">
      <n-form :model="generateForm" label-placement="left" label-width="90">
        <n-form-item label="模板" required>
          <n-select v-model:value="generateForm.template_id" :options="templateOptions"
            placeholder="选择模板" />
        </n-form-item>
        <n-form-item label="时间范围">
          <n-date-picker v-model:value="generateForm.dateRange" type="daterange"
            style="width: 100%" />
        </n-form-item>
        <n-form-item label="参数">
          <n-input v-model:value="generateForm.params" type="textarea"
            placeholder='JSON格式参数，如 {"region": "beijing"}' :rows="3" />
        </n-form-item>
        <n-form-item label="生成方式">
          <n-radio-group v-model:value="generateForm.async">
            <n-space>
              <n-radio :value="false">同步（等待完成）</n-radio>
              <n-radio :value="true">异步（后台生成）</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showGenerateModal = false">取消</n-button>
          <n-button type="primary" @click="handleGenerate" :loading="generating">
            开始生成
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted, nextTick } from 'vue'
import { useMessage, NButton, NSpace, NIcon, NTag } from 'naive-ui'
import { AddOutline, DownloadOutline, TrashOutline, ReloadOutline } from '@vicons/ionicons5'
import * as echarts from 'echarts'
import {
  getReports, generateReport, generateReportAsync, downloadReport,
  getReportStats, deleteReport, getTemplates
} from '@/api/report'
import dayjs from 'dayjs'

const message = useMessage()
const loading = ref(false)
const generating = ref(false)
const reports = ref([])
const searchText = ref('')
const filterStatus = ref(null)
const filterTemplate = ref(null)
const dateRange = ref(null)

const statusOptions = [
  { label: '待生成', value: 'pending' },
  { label: '生成中', value: 'generating' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' }
]
const templateOptions = ref([])

const pagination = ref({ page: 1, pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] })

// 图表
const pieChartRef = ref(null)
const lineChartRef = ref(null)

// 生成报表
const showGenerateModal = ref(false)
const generateForm = ref({
  template_id: null, dateRange: null, params: '', async: false
})

const columns = ref([
  { title: 'ID', key: 'id', width: 80 },
  { title: '报表名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '模板', key: 'template_name', width: 140, ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'status', width: 100,
    render: row => {
      const typeMap = { pending: 'warning', generating: 'info', completed: 'success', failed: 'error' }
      const labelMap = { pending: '待生成', generating: '生成中', completed: '已完成', failed: '失败' }
      return h(NTag, { type: typeMap[row.status] || 'default', size: 'small' },
        { default: () => labelMap[row.status] || row.status })
    }
  },
  {
    title: '生成时间', key: 'created_at', width: 180,
    render: row => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render: row => h(NSpace, null, {
      default: () => [
        row.status === 'completed' ? h(NButton, {
          size: 'small', type: 'primary',
          onClick: () => handleDownload(row.id)
        }, { default: () => '下载', icon: () => h(NIcon, null, { default: () => h(DownloadOutline) }) }) : null,
        row.status === 'pending' || row.status === 'failed' ? h(NButton, {
          size: 'small',
          onClick: () => handleRegenerate(row)
        }, { default: () => '重试', icon: () => h(NIcon, null, { default: () => h(ReloadOutline) }) }) : null,
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) },
          { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) })
      ].filter(Boolean)
    })
  }
])

async function loadReports() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }
    if (searchText.value) params.search = searchText.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterTemplate.value) params.template_id = filterTemplate.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dayjs(dateRange.value[0]).format('YYYY-MM-DD')
      params.end_date = dayjs(dateRange.value[1]).format('YYYY-MM-DD')
    }
    const res = await getReports(params)
    const data = res.data || {}
    reports.value = data.items || data.reports || data || []
    if (data.total !== undefined) pagination.value.itemCount = data.total
    await loadStats()
  } catch (e) {
    console.error('Load reports error:', e)
    message.error('加载报表失败')
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const res = await getTemplates({ page_size: 100 })
    const items = res.data?.items || res.data || []
    templateOptions.value = items.map(t => ({ label: t.name, value: t.id }))
  } catch (e) {
    console.error('Load templates error:', e)
  }
}

async function loadStats() {
  try {
    const res = await getReportStats()
    const data = res.data || {}
    renderPieChart(data.status_distribution || {})
    renderLineChart(data.trend || [])
  } catch (e) {
    console.error('Load stats error:', e)
    // 使用默认数据
    renderPieChart({ completed: 120, pending: 5, generating: 3, failed: 2 })
    renderLineChart([8, 12, 6, 15, 10, 20, 18])
  }
}

function renderPieChart(dist) {
  if (!pieChartRef.value) return
  const chart = echarts.init(pieChartRef.value)
  const data = Object.entries(dist).map(([name, value]) => ({ name, value }))
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: data.length ? data : [{ name: '暂无数据', value: 1 }]
    }]
  })
}

function renderLineChart(trend) {
  if (!lineChartRef.value) return
  const chart = echarts.init(lineChartRef.value)
  const labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: trend.length ? trend.map((_, i) => labels[i % 7]) : labels },
    yAxis: { type: 'value' },
    series: [{
      name: '报表数', type: 'line', smooth: true,
      data: trend.length ? trend : [5, 8, 12, 6, 15, 10, 7],
      areaStyle: { opacity: 0.15 }, itemStyle: { color: '#2080f0' }
    }]
  })
}

function openGenerate() {
  generateForm.value = { template_id: null, dateRange: null, params: '', async: false }
  showGenerateModal.value = true
}

async function handleGenerate() {
  if (!generateForm.value.template_id) {
    message.warning('请选择模板')
    return
  }
  generating.value = true
  try {
    const data = {
      template_id: generateForm.value.template_id,
      params: generateForm.value.params ? JSON.parse(generateForm.value.params) : {}
    }
    if (generateForm.value.dateRange && generateForm.value.dateRange.length === 2) {
      data.start_date = dayjs(generateForm.value.dateRange[0]).format('YYYY-MM-DD')
      data.end_date = dayjs(generateForm.value.dateRange[1]).format('YYYY-MM-DD')
    }
    if (generateForm.value.async) {
      await generateReportAsync(data)
      message.success('已提交异步生成任务')
    } else {
      await generateReport(data)
      message.success('报表已生成')
    }
    showGenerateModal.value = false
    await loadReports()
  } catch (e) {
    console.error('Generate error:', e)
    message.error(e.response?.data?.message || '生成失败')
  } finally {
    generating.value = false
  }
}

async function handleDownload(id) {
  try {
    const res = await downloadReport(id)
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const disposition = res.headers?.['content-disposition']
    const filename = disposition
      ? decodeURIComponent(disposition.split('filename=')[1]?.replace(/"/g, '') || 'report')
      : `report_${id}.${res.headers?.['content-type']?.includes('pdf') ? 'pdf' : 'xlsx'}`
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    message.success('下载成功')
  } catch (e) {
    message.error('下载失败')
  }
}

function handleRegenerate(row) {
  generating.value = true
  const data = { template_id: row.template_id, params: row.params || {} }
  generateReport(data)
    .then(() => { message.success('重试成功'); loadReports() })
    .catch(() => message.error('重试失败'))
    .finally(() => { generating.value = false })
}

function handleDelete(id) {
  dialog.warning({
    title: '确认删除', content: '确定删除此报表吗？',
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteReport(id)
        message.success('已删除')
        await loadReports()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(() => {
  loadTemplates()
  loadReports()
  nextTick(() => {
    renderPieChart({ completed: 120, pending: 5, generating: 3, failed: 2 })
    renderLineChart([8, 12, 6, 15, 10, 20, 18])
  })
})
</script>
