<template>
  <div>
    <div class="page-header">
      <h2>巡检报告</h2>
    </div>

    <!-- Summary Stats -->
    <n-grid cols="4 m:2 s:1" responsive="screen" :x-gap="16" :y-gap="16" style="margin-bottom:16px">
      <n-gi v-for="item in summaryItems" :key="item.label">
        <n-card :bordered="false">
          <div class="summary-card">
            <div class="summary-value" :style="{ color: item.color }">{{ item.value }}</div>
            <div class="summary-label">{{ item.label }}</div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-tabs v-model:value="activeTab" type="line">
      <n-tab-pane name="reports" tab="报告列表">
        <n-card :bordered="false">
          <n-data-table
            :columns="reportColumns"
            :data="reports"
            :loading="reportLoading"
            :pagination="reportPagination"
            remote
          />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="template" tab="报告模板">
        <n-card :bordered="false">
          <template v-if="template">
            <n-descriptions :column="1" bordered>
              <n-descriptions-item label="模板名称">{{ template.name || '默认巡检报告模板' }}</n-descriptions-item>
              <n-descriptions-item label="包含章节">
                <n-space :wrap="true">
                  <n-tag v-for="section in (template.sections || [])" :key="section" size="small">{{ section }}</n-tag>
                </n-space>
              </n-descriptions-item>
              <n-descriptions-item label="模板内容">
                <pre style="white-space:pre-wrap;font-size:13px;background:#f6f6f6;padding:12px;border-radius:4px">{{ template.content || JSON.stringify(template, null, 2) }}</pre>
              </n-descriptions-item>
            </n-descriptions>
          </template>
          <n-empty v-else description="暂无模板" />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- Report Detail Modal -->
    <n-modal v-model:show="detailModal" preset="card" :title="currentReport?.task_name || '报告详情'" style="width:800px">
      <n-descriptions :column="2" bordered v-if="currentReport">
        <n-descriptions-item label="任务名称">{{ currentReport.task_name }}</n-descriptions-item>
        <n-descriptions-item label="目标设备">{{ (currentReport.targets || []).join(', ') || '-' }}</n-descriptions-item>
        <n-descriptions-item label="执行时间">{{ formatTime(currentReport.executed_at) }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="reportStatusType(currentReport.status)">{{ reportStatusLabel(currentReport.status) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="总检查项">{{ currentReport.total_checks || 0 }}</n-descriptions-item>
        <n-descriptions-item label="通过项">{{ currentReport.passed_checks || 0 }}</n-descriptions-item>
        <n-descriptions-item label="失败项">{{ currentReport.failed_checks || 0 }}</n-descriptions-item>
        <n-descriptions-item label="告警项">{{ currentReport.warning_checks || 0 }}</n-descriptions-item>
      </n-descriptions>

      <n-divider>检查详情</n-divider>
      <n-data-table
        v-if="currentReport?.results?.length"
        :columns="resultColumns"
        :data="currentReport.results"
        :pagination="{ pageSize: 10 }"
        size="small"
      />
      <n-empty v-else description="暂无检查结果" />

      <template #footer>
        <n-space justify="end">
          <n-button @click="detailModal = false">关闭</n-button>
          <n-button type="primary" @click="handleExport(currentReport)">导出报告</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NTag, NButton, NSpace, useMessage } from 'naive-ui'
import { getInspectionReport, exportInspectionReport, getReportTemplate, getInspectionSummary } from '@/api/inspection'
import dayjs from 'dayjs'

const message = useMessage()

const activeTab = ref('reports')

// Summary
const summaryItems = ref([
  { label: '总巡检次数', value: 0, color: '#2080f0' },
  { label: '通过率', value: '0%', color: '#18a058' },
  { label: '失败项', value: 0, color: '#d03050' },
  { label: '告警项', value: 0, color: '#f0a020' }
])

// Reports
const reportLoading = ref(false)
const reports = ref([])
const reportPagination = ref({
  page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50],
  onUpdatePage: (p) => { reportPagination.value.page = p; loadReports() },
  onUpdatePageSize: (s) => { reportPagination.value.pageSize = s; reportPagination.value.page = 1; loadReports() }
})

// Template
const template = ref(null)

// Detail
const detailModal = ref(false)
const currentReport = ref(null)

const reportStatusType = (status) => {
  const map = { passed: 'success', failed: 'error', warning: 'warning', partial: 'info' }
  return map[status] || 'default'
}

const reportStatusLabel = (status) => {
  const map = { passed: '通过', failed: '失败', warning: '告警', partial: '部分通过' }
  return map[status] || status
}

const checkStatusType = (status) => {
  const map = { pass: 'success', fail: 'error', warning: 'warning' }
  return map[status] || 'default'
}

const checkStatusLabel = (status) => {
  const map = { pass: '通过', fail: '失败', warning: '告警' }
  return map[status] || status
}

const reportColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '任务名称', key: 'task_name', width: 180, ellipsis: { tooltip: true } },
  { title: '目标', key: 'targets', width: 200, render: (row) => (row.targets || []).join(', ') || '-' },
  {
    title: '状态', key: 'status', width: 90,
    render: (row) => h(NTag, { type: reportStatusType(row.status), size: 'small' }, { default: () => reportStatusLabel(row.status) })
  },
  { title: '检查项', key: 'total_checks', width: 80 },
  { title: '通过', key: 'passed_checks', width: 70 },
  { title: '失败', key: 'failed_checks', width: 70 },
  { title: '执行时间', key: 'executed_at', width: 180, render: (row) => formatTime(row.executed_at) },
  {
    title: '操作', key: 'actions', width: 160, fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', type: 'info', onClick: () => handleDetail(row) }, { default: () => '查看' }),
        h(NButton, { size: 'small', type: 'primary', onClick: () => handleExport(row) }, { default: () => '导出' })
      ]
    })
  }
]

const resultColumns = [
  { title: '检查项', key: 'name', width: 160 },
  { title: '目标', key: 'target', width: 140 },
  {
    title: '结果', key: 'status', width: 80,
    render: (row) => h(NTag, { type: checkStatusType(row.status), size: 'small' }, { default: () => checkStatusLabel(row.status) })
  },
  { title: '详情', key: 'detail', ellipsis: { tooltip: true } },
  { title: '检查时间', key: 'checked_at', width: 180, render: (row) => formatTime(row.checked_at) }
]

const formatTime = (t) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'

async function loadReports() {
  reportLoading.value = true
  try {
    // Use getInspectionReport - it might be per-task, so we might need to adapt
    const res = await getInspectionReport('all')
    const data = res.data || {}
    if (Array.isArray(data)) {
      reports.value = data
      reportPagination.value.itemCount = data.length
    } else if (data.items) {
      reports.value = data.items
      reportPagination.value.itemCount = data.total || 0
    } else {
      reports.value = [data].filter(Boolean)
      reportPagination.value.itemCount = reports.value.length
    }
  } catch (e) {
    // Non-critical error
    reports.value = []
  } finally {
    reportLoading.value = false
  }
}

async function loadSummary() {
  try {
    const res = await getInspectionSummary()
    const data = res.data || {}
    summaryItems.value[0].value = data.total_runs || 0
    summaryItems.value[1].value = data.pass_rate ? `${data.pass_rate}%` : '0%'
    summaryItems.value[2].value = data.failed_checks || 0
    summaryItems.value[3].value = data.warning_checks || 0
  } catch (e) {
    // Non-critical
  }
}

async function loadTemplate() {
  try {
    const res = await getReportTemplate()
    template.value = res.data || {}
  } catch (e) {
    template.value = null
  }
}

async function handleDetail(row) {
  try {
    const res = await getInspectionReport(row.id || row.task_id)
    currentReport.value = res.data || row
    detailModal.value = true
  } catch (e) {
    currentReport.value = row
    detailModal.value = true
  }
}

async function handleExport(row) {
  try {
    const res = await exportInspectionReport(row.id || row.task_id)
    // Create download link for blob
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `巡检报告_${row.task_name || 'report'}_${dayjs().format('YYYYMMDD')}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
    message.success('报告导出成功')
  } catch (e) {
    message.error('导出失败：' + (e.response?.data?.message || e.message))
  }
}

onMounted(() => {
  loadReports()
  loadSummary()
  loadTemplate()
})
</script>

<style scoped>
.summary-card { text-align: center; padding: 8px 0; }
.summary-value { font-size: 28px; font-weight: 700; }
.summary-label { font-size: 13px; color: #999; margin-top: 4px; }
</style>
