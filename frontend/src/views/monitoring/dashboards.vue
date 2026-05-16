<template>
  <div>
    <div class="page-header">
      <h2>监控仪表盘</h2>
      <n-button type="primary" @click="openCreateDashboard">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        创建仪表盘
      </n-button>
    </div>

    <!-- Dashboard cards -->
    <n-grid cols="1 m:2 l:3" responsive="screen" :x-gap="16" :y-gap="16" v-if="dashboards.length">
      <n-gi v-for="dash in dashboards" :key="dash.id">
        <n-card :title="dash.name" :bordered="false" hoverable>
          <template #header-extra>
            <n-space>
              <n-button size="small" @click="openEditDashboard(dash)">编辑</n-button>
              <n-button size="small" type="info" @click="handleSnapshot(dash)">快照</n-button>
              <n-popconfirm @positive-click="() => handleDelete(dash)">
                <template #trigger><n-button size="small" type="error" ghost>删除</n-button></template>
                确认删除此仪表盘？
              </n-popconfirm>
            </n-space>
          </template>
          <p style="color:#999;font-size:13px;margin-bottom:12px">{{ dash.description || '暂无描述' }}</p>
          <div :ref="el => setChartRef(dash.id, el)" style="height:220px"></div>
        </n-card>
      </n-gi>
    </n-grid>
    <n-empty v-else description="暂无仪表盘，点击右上角创建" style="margin-top:40px" />

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showModal" preset="card" :title="isEdit ? '编辑仪表盘' : '创建仪表盘'" style="width:500px">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="80">
        <n-form-item label="名称" path="name">
          <n-input v-model:value="formData.name" placeholder="仪表盘名称" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="formData.description" type="textarea" placeholder="仪表盘描述" :rows="3" />
        </n-form-item>
        <n-form-item label="图表类型" path="chart_type">
          <n-select v-model:value="formData.chart_type" :options="chartTypeOptions" />
        </n-form-item>
        <n-form-item label="指标查询" path="promql">
          <n-input v-model:value="formData.promql" type="textarea" placeholder="PromQL 查询语句" :rows="2" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">提交</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted, nextTick } from 'vue'
import { NButton, NSpace, useMessage, useDialog } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import * as echarts from 'echarts'
import { getDashboards, getDashboardLayout, saveDashboardLayout, createLayoutSnapshot } from '@/api/monitoring'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const dashboards = ref([])
const chartRefs = ref({})
const chartInstances = ref({})

const showModal = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const formData = ref({ name: '', description: '', chart_type: 'line', promql: '' })

const formRules = {
  name: { required: true, message: '请输入仪表盘名称', trigger: 'blur' }
}

const chartTypeOptions = [
  { label: '折线图', value: 'line' },
  { label: '柱状图', value: 'bar' },
  { label: '面积图', value: 'area' },
  { label: '饼图', value: 'pie' }
]

function setChartRef(id, el) {
  if (el) chartRefs.value[id] = el
}

function renderChart(dash) {
  const el = chartRefs.value[dash.id]
  if (!el) return
  if (!chartInstances.value[dash.id]) {
    chartInstances.value[dash.id] = echarts.init(el)
  }
  const chart = chartInstances.value[dash.id]
  const type = dash.chart_type || 'line'
  const colors = ['#2080f0', '#18a058', '#f0a020', '#d03050', '#646cff', '#999']

  const seriesData = dash.series || []
  const timestamps = dash.timestamps || []

  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 16, top: 16, bottom: 30 },
    xAxis: { type: 'category', data: timestamps.map(t => dayjs(t).format('HH:mm')) },
    yAxis: { type: 'value' },
    series: seriesData.map((s, i) => ({
      name: s.name || 'Value',
      type: type === 'area' ? 'line' : type,
      smooth: true,
      data: s.data || [],
      areaStyle: type === 'area' ? { opacity: 0.15 } : undefined,
      itemStyle: { color: colors[i % colors.length] }
    }))
  }
  chart.setOption(option, true)
}

async function loadDashboards() {
  loading.value = true
  try {
    const [dashRes, layoutRes] = await Promise.allSettled([
      getDashboards({}),
      getDashboardLayout()
    ])
    const dashData = dashRes.status === 'fulfilled' ? (dashRes.value.data || {}) : {}
    dashboards.value = dashData.items || []
    const layoutData = layoutRes.status === 'fulfilled' ? (layoutRes.value.data || {}) : {}

    // Merge layout data into dashboards
    if (layoutData.widgets) {
      layoutData.widgets.forEach(w => {
        const dash = dashboards.value.find(d => d.id === w.dashboard_id || d.id === w.id)
        if (dash) {
          Object.assign(dash, w)
        }
      })
    }

    nextTick(() => {
      dashboards.value.forEach(d => renderChart(d))
    })
  } catch (e) {
    message.error('加载仪表盘失败：' + (e.response?.data?.message || e.message))
  } finally {
    loading.value = false
  }
}

function openCreateDashboard() {
  isEdit.value = false
  editingId.value = null
  formData.value = { name: '', description: '', chart_type: 'line', promql: '' }
  showModal.value = true
}

function openEditDashboard(dash) {
  isEdit.value = true
  editingId.value = dash.id
  formData.value = {
    name: dash.name, description: dash.description || '',
    chart_type: dash.chart_type || 'line', promql: dash.promql || ''
  }
  showModal.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch { return }
  submitting.value = true
  try {
    const layouts = dashboards.value.map(d => ({
      id: d.id, name: d.name, chart_type: d.chart_type, promql: d.promql, description: d.description
    }))
    if (isEdit.value) {
      const idx = layouts.findIndex(l => l.id === editingId.value)
      if (idx >= 0) {
        layouts[idx] = { ...layouts[idx], ...formData.value }
      }
    } else {
      layouts.push({ id: Date.now(), ...formData.value })
    }
    await saveDashboardLayout({ widgets: layouts })
    message.success(isEdit.value ? '仪表盘已更新' : '仪表盘已创建')
    showModal.value = false
    loadDashboards()
  } catch (e) {
    message.error('操作失败：' + (e.response?.data?.message || e.message))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(dash) {
  try {
    const layouts = dashboards.value.filter(d => d.id !== dash.id).map(d => ({
      id: d.id, name: d.name, chart_type: d.chart_type, promql: d.promql, description: d.description
    }))
    await saveDashboardLayout({ widgets: layouts })
    if (chartInstances.value[dash.id]) {
      chartInstances.value[dash.id].dispose()
      delete chartInstances.value[dash.id]
    }
    message.success('仪表盘已删除')
    loadDashboards()
  } catch (e) {
    message.error('删除失败：' + (e.response?.data?.message || e.message))
  }
}

async function handleSnapshot(dash) {
  try {
    await createLayoutSnapshot({ layout_id: dash.id, label: `快照 ${dayjs().format('YYYY-MM-DD HH:mm')}` })
    message.success('快照已创建')
  } catch (e) {
    message.error('创建快照失败：' + (e.response?.data?.message || e.message))
  }
}

onMounted(() => loadDashboards())
</script>
