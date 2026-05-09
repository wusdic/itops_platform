<template>
  <div class="reports-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">
          报告中心
        </h2>
        <p class="page-subtitle">
          运维报告生成与管理，支持定期报告和自定义报告模板
        </p>
      </div>
      <div class="page-header-actions">
        <el-button @click="showTemplateDialog = true">
          <el-icon><Setting /></el-icon>
          模板设置
        </el-button>
        <el-button
          type="primary"
          @click="showCreateDialog = true"
        >
          <el-icon><Plus /></el-icon>
          生成报告
        </el-button>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <div 
        v-for="action in quickActions" 
        :key="action.key"
        class="quick-action-card"
        @click="handleQuickAction(action)"
      >
        <div
          class="action-icon"
          :class="action.key"
        >
          <el-icon><component :is="action.icon" /></el-icon>
        </div>
        <div class="action-text">
          <div class="action-title">
            {{ action.title }}
          </div>
          <div class="action-desc">
            {{ action.desc }}
          </div>
        </div>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-select
          v-model="reportType"
          placeholder="报告类型"
          style="width: 130px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="运维日报"
            value="daily"
          />
          <el-option
            label="运维周报"
            value="weekly"
          />
          <el-option
            label="运维月报"
            value="monthly"
          />
          <el-option
            label="资产报告"
            value="asset"
          />
          <el-option
            label="告警报告"
            value="alert"
          />
          <el-option
            label="工单报告"
            value="workorder"
          />
        </el-select>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
          @change="handleFilterChange"
        />

        <el-select
          v-model="statusFilter"
          placeholder="状态"
          style="width: 120px"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="已完成"
            value="completed"
          />
          <el-option
            label="生成中"
            value="generating"
          />
          <el-option
            label="已过期"
            value="expired"
          />
        </el-select>
      </div>

      <div class="filter-right">
        <el-input
          v-model="searchText"
          placeholder="搜索报告..."
          style="width: 200px"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button
          text
          @click="handleRefresh"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 报告列表 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="reportsData"
        stripe
      >
        <el-table-column
          label="报告信息"
          min-width="280"
        >
          <template #default="{ row }">
            <div class="report-info">
              <div
                class="report-icon"
                :class="row.type"
              >
                <el-icon><component :is="getTypeIcon(row.type)" /></el-icon>
              </div>
              <div class="report-text">
                <div class="report-name">
                  {{ row.name }}
                </div>
                <div class="report-meta">
                  <span class="type-badge">{{ getTypeText(row.type) }}</span>
                  <span>{{ row.period }}</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="生成时间"
          width="170"
        >
          <template #default="{ row }">
            <span>{{ row.createdAt }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="数据范围"
          width="180"
        >
          <template #default="{ row }">
            <span>{{ row.dataRange }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getStatusTagType(row.status)"
              effect="light"
            >
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="大小"
          width="80"
        >
          <template #default="{ row }">
            <span>{{ row.size }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="200"
          fixed="right"
        >
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip
                content="预览"
                placement="top"
              >
                <el-button
                  text
                  type="primary"
                  size="small"
                  @click="handlePreview(row)"
                >
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                content="下载"
                placement="top"
              >
                <el-button
                  text
                  size="small"
                  @click="handleDownload(row)"
                >
                  <el-icon><Download /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                content="分享"
                placement="top"
              >
                <el-button
                  text
                  size="small"
                  @click="handleShare(row)"
                >
                  <el-icon><Share /></el-icon>
                </el-button>
              </el-tooltip>
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleReportCommand(cmd, row)"
              >
                <el-button
                  text
                  size="small"
                >
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="regenerate">
                      重新生成
                    </el-dropdown-item>
                    <el-dropdown-item command="edit">
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item command="schedule">
                      加入计划
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="delete"
                      divided
                    >
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="table-footer">
        <div class="table-info">
          共 {{ total }} 条记录
        </div>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 创建报告对话框 -->
    <el-dialog 
      v-model="showCreateDialog" 
      title="生成报告" 
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="reportFormRef"
        :model="reportForm"
        label-width="110px"
        :rules="formRules"
      >
        <el-form-item
          label="报告类型"
          prop="type"
        >
          <el-select
            v-model="reportForm.type"
            placeholder="选择报告类型"
            style="width: 100%"
            @change="handleTypeChange"
          >
            <el-option
              label="运维日报"
              value="daily"
            />
            <el-option
              label="运维周报"
              value="weekly"
            />
            <el-option
              label="运维月报"
              value="monthly"
            />
            <el-option
              label="资产报告"
              value="asset"
            />
            <el-option
              label="告警报告"
              value="alert"
            />
            <el-option
              label="工单报告"
              value="workorder"
            />
            <el-option
              label="自定义报告"
              value="custom"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="报告名称"
          prop="name"
        >
          <el-input
            v-model="reportForm.name"
            placeholder="请输入报告名称"
          />
        </el-form-item>

        <el-form-item label="数据范围">
          <el-row :gutter="10">
            <el-col :span="12">
              <el-date-picker
                v-model="reportForm.startDate"
                type="date"
                placeholder="开始日期"
                style="width: 100%"
              />
            </el-col>
            <el-col :span="12">
              <el-date-picker
                v-model="reportForm.endDate"
                type="date"
                placeholder="结束日期"
                style="width: 100%"
              />
            </el-col>
          </el-row>
        </el-form-item>

        <el-form-item label="选择设备">
          <el-select 
            v-model="reportForm.devices" 
            multiple 
            filterable 
            placeholder="选择设备（不选则全部）"
            style="width: 100%"
            clearable
          >
            <el-option 
              v-for="device in deviceList" 
              :key="device.id" 
              :label="`${device.name} (${device.ip})`" 
              :value="device.id" 
            />
          </el-select>
        </el-form-item>

        <el-form-item label="报告模板">
          <el-select
            v-model="reportForm.template"
            placeholder="选择模板"
            style="width: 100%"
          >
            <el-option
              label="默认模板"
              value="default"
            />
            <el-option
              label="简洁模板"
              value="simple"
            />
            <el-option
              label="详细模板"
              value="detailed"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="输出格式">
          <el-checkbox-group v-model="reportForm.formats">
            <el-checkbox label="pdf">
              PDF
            </el-checkbox>
            <el-checkbox label="excel">
              Excel
            </el-checkbox>
            <el-checkbox label="html">
              HTML
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="报告描述">
          <el-input 
            v-model="reportForm.description" 
            type="textarea" 
            :rows="3" 
            placeholder="请输入报告描述" 
          />
        </el-form-item>

        <el-form-item label="自动发送">
          <el-switch v-model="reportForm.autoSend" />
          <span class="form-hint">生成后自动发送到指定邮箱</span>
        </el-form-item>

        <el-form-item
          v-if="reportForm.autoSend"
          label="收件人"
        >
          <el-input
            v-model="reportForm.recipients"
            placeholder="多个邮箱用逗号分隔"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button @click="handleSaveAsTemplate">
          另存为模板
        </el-button>
        <el-button
          type="primary"
          @click="handleGenerateReport"
        >
          生成报告
        </el-button>
      </template>
    </el-dialog>

    <!-- 模板设置对话框 -->
    <el-dialog
      v-model="showTemplateDialog"
      title="报告模板设置"
      width="900px"
    >
      <el-tabs v-model="templateTab">
        <el-tab-pane
          label="模板列表"
          name="list"
        >
          <el-table
            :data="templates"
            stripe
          >
            <el-table-column
              prop="name"
              label="模板名称"
            />
            <el-table-column
              prop="type"
              label="报告类型"
            />
            <el-table-column
              prop="format"
              label="格式"
              width="100"
            />
            <el-table-column
              prop="items"
              label="包含项"
              width="200"
            >
              <template #default="{ row }">
                <el-tag
                  v-for="item in row.items"
                  :key="item"
                  size="small"
                  style="margin-right: 4px;"
                >
                  {{ item }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="150"
            >
              <template #default="{ row }">
                <el-button
                  text
                  size="small"
                  type="primary"
                  @click="handleEditTemplate(row)"
                >
                  编辑
                </el-button>
                <el-button
                  text
                  size="small"
                  type="danger"
                  @click="handleDeleteTemplate(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane
          label="添加模板"
          name="add"
        >
          <el-form
            :model="templateForm"
            label-width="100px"
          >
            <el-form-item label="模板名称">
              <el-input
                v-model="templateForm.name"
                placeholder="请输入模板名称"
              />
            </el-form-item>
            <el-form-item label="报告类型">
              <el-select
                v-model="templateForm.type"
                style="width: 100%"
              >
                <el-option
                  label="运维日报"
                  value="daily"
                />
                <el-option
                  label="运维周报"
                  value="weekly"
                />
                <el-option
                  label="运维月报"
                  value="monthly"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="包含内容">
              <el-checkbox-group v-model="templateForm.items">
                <el-checkbox label="设备概览">
                  设备概览
                </el-checkbox>
                <el-checkbox label="告警统计">
                  告警统计
                </el-checkbox>
                <el-checkbox label="工单统计">
                  工单统计
                </el-checkbox>
                <el-checkbox label="性能趋势">
                  性能趋势
                </el-checkbox>
                <el-checkbox label="容量分析">
                  容量分析
                </el-checkbox>
                <el-checkbox label="可用性">
                  可用性
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </el-form>
          <div style="text-align: right; margin-top: 20px;">
            <el-button
              type="primary"
              @click="handleSaveTemplate"
            >
              保存模板
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- 报告预览抽屉 -->
    <el-drawer
      v-model="showPreviewDrawer"
      title="报告预览"
      size="900px"
    >
      <div
        v-if="currentReport"
        class="report-preview"
      >
        <div class="preview-header">
          <h3>{{ currentReport.name }}</h3>
          <div class="preview-meta">
            <span>类型: {{ getTypeText(currentReport.type) }}</span>
            <span>期间: {{ currentReport.period }}</span>
            <span>生成时间: {{ currentReport.createdAt }}</span>
          </div>
        </div>

        <div class="preview-content">
          <!-- 概览统计 -->
          <div class="preview-section">
            <h4>概览统计</h4>
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-value">156</span>
                <span class="stat-label">监控设备</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">23</span>
                <span class="stat-label">告警数</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">45</span>
                <span class="stat-label">工单数</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">99.8%</span>
                <span class="stat-label">可用率</span>
              </div>
            </div>
          </div>

          <!-- 图表区域 -->
          <div class="preview-section">
            <h4>趋势图表</h4>
            <div class="chart-placeholder">
              <div class="placeholder-icon">
                <el-icon><DataLine /></el-icon>
              </div>
              <span>图表数据预览区</span>
            </div>
          </div>

          <!-- 详细数据 -->
          <div class="preview-section">
            <h4>详细数据</h4>
            <el-table
              :data="previewTableData"
              stripe
              size="small"
            >
              <el-table-column
                prop="device"
                label="设备"
              />
              <el-table-column
                prop="cpu"
                label="CPU平均"
              />
              <el-table-column
                prop="memory"
                label="内存平均"
              />
              <el-table-column
                prop="disk"
                label="磁盘平均"
              />
              <el-table-column
                prop="alerts"
                label="告警数"
              />
            </el-table>
          </div>
        </div>

        <div class="preview-footer">
          <el-button
            type="primary"
            @click="handleDownload(currentReport)"
          >
            <el-icon><Download /></el-icon>
            下载报告
          </el-button>
          <el-button @click="handleShare(currentReport)">
            <el-icon><Share /></el-icon>
            分享报告
          </el-button>
          <el-button @click="handlePrint">
            <el-icon><Printer /></el-icon>
            打印
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Download, Plus, Setting, View, Share, MoreFilled,
  Document, DataLine, Printer, Ticket, Warning, TrendCharts
} from '@element-plus/icons-vue'
import { reports } from '@/api'

// 状态
const loading = ref(false)
const reportsData = ref([])
const showCreateDialog = ref(false)
const showTemplateDialog = ref(false)
const showPreviewDrawer = ref(false)
const currentReport = ref(null)
const reportFormRef = ref(null)

// 筛选
const searchText = ref('')
const reportType = ref('')
const dateRange = ref(null)
const statusFilter = ref('')

// 分页
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 模板
const templateTab = ref('list')
const templates = ref([
  { name: '日报模板', type: 'daily', format: 'PDF', items: ['设备概览', '告警统计', '工单统计'] },
  { name: '周报模板', type: 'weekly', format: 'PDF+Excel', items: ['性能趋势', '容量分析', '可用性'] },
  { name: '月报模板', type: 'monthly', format: 'PDF', items: ['设备概览', '告警统计', '工单统计', '性能趋势'] }
])

const templateForm = reactive({
  name: '',
  type: 'daily',
  items: []
})

// 设备列表
const deviceList = ref([
  { id: 1, name: 'Web服务器01', ip: '192.168.1.101' },
  { id: 2, name: '数据库服务器', ip: '192.168.1.102' },
  { id: 3, name: '存储服务器', ip: '192.168.1.103' }
])

// 报告表单
const reportForm = reactive({
  type: 'daily',
  name: '',
  startDate: '',
  endDate: '',
  devices: [],
  template: 'default',
  formats: ['pdf'],
  description: '',
  autoSend: false,
  recipients: ''
})

// 表单验证
const formRules = {
  type: [{ required: true, message: '请选择报告类型', trigger: 'change' }],
  name: [{ required: true, message: '请输入报告名称', trigger: 'blur' }]
}

// 快捷操作
const quickActions = [
  { key: 'daily', title: '生成日报', desc: '今日运维数据汇总', icon: 'Document' },
  { key: 'weekly', title: '生成周报', desc: '本周运维数据汇总', icon: 'TrendCharts' },
  { key: 'alert', title: '告警报告', desc: '告警统计分析报告', icon: 'Warning' },
  { key: 'workorder', title: '工单报告', desc: '工单处理统计报告', icon: 'Ticket' }
]

// 预览数据
const previewTableData = ref([
  { device: 'Web服务器01', cpu: '45%', memory: '62%', disk: '55%', alerts: 3 },
  { device: '数据库服务器', cpu: '38%', memory: '71%', disk: '68%', alerts: 1 },
  { device: '存储服务器', cpu: '22%', memory: '45%', disk: '72%', alerts: 0 }
])

// 辅助函数
const getTypeText = (type) => {
  const texts = {
    daily: '运维日报', weekly: '运维周报', monthly: '运维月报',
    asset: '资产报告', alert: '告警报告', workorder: '工单报告', custom: '自定义'
  }
  return texts[type] || type
}

const getTypeIcon = (type) => {
  const icons = {
    daily: 'Document', weekly: 'TrendCharts', monthly: 'Document',
    asset: 'TrendCharts', alert: 'Warning', workorder: 'Ticket'
  }
  return icons[type] || 'Document'
}

const getStatusText = (status) => {
  const texts = { completed: '已完成', generating: '生成中', expired: '已过期' }
  return texts[status] || status
}

const getStatusTagType = (status) => {
  const types = { completed: 'success', generating: 'warning', expired: 'info' }
  return types[status] || 'info'
}

// 加载报告数据
const loadReports = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value,
      type: reportType.value,
      status: statusFilter.value,
      search: searchText.value
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.startDate = dateRange.value[0]
      params.endDate = dateRange.value[1]
    }
    const res = await reports.getReports(params)
    reportsData.value = res.data?.list || res.data || []
    total.value = res.data?.total || res.total || 0
  } catch (error) {
    console.error('Failed to load reports:', error)
    ElMessage.error('加载报告列表失败')
  } finally {
    loading.value = false
  }
}

// 事件处理
const handleFilterChange = () => {
  currentPage.value = 1
  loadReports()
}

const handleSearch = () => {
  currentPage.value = 1
  loadReports()
}

const handleRefresh = () => {
  loadReports()
  ElMessage.success('刷新成功')
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadReports()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  loadReports()
}

const handleQuickAction = (action) => {
  reportForm.type = action.key
  reportForm.name = `${new Date().toLocaleDateString('zh-CN')} ${getTypeText(action.key)}`
  showCreateDialog.value = true
}

const handleTypeChange = () => {
  if (!reportForm.name) {
    reportForm.name = `${new Date().toLocaleDateString('zh-CN')} ${getTypeText(reportForm.type)}`
  }
}

const handleGenerateReport = async () => {
  if (!reportFormRef.value) return
  
  try {
    await reportFormRef.value.validate()
    await reports.generateReport(reportForm)
    ElMessage.success('报告正在生成中...')
    showCreateDialog.value = false
    setTimeout(() => {
      loadReports()
    }, 1500)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('生成报告失败')
    }
  }
}

const handleSaveAsTemplate = async () => {
  try {
    await reports.saveTemplate(reportForm)
    ElMessage.success('模板保存成功')
    showCreateDialog.value = false
    loadReports()
  } catch (error) {
    ElMessage.error('保存模板失败')
  }
}

const handlePreview = (report) => {
  currentReport.value = report
  showPreviewDrawer.value = true
}

const handleDownload = async (report) => {
  try {
    await reports.downloadReport(report.id, 'pdf')
    ElMessage.success(`正在下载: ${report.name}`)
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const handleShare = async (report) => {
  try {
    await reports.shareReport(report.id)
    ElMessage.success('分享链接已复制到剪贴板')
  } catch (error) {
    ElMessage.error('分享失败')
  }
}

const handleReportCommand = (command, report) => {
  switch (command) {
    case 'regenerate': ElMessage.success('报告重新生成中...'); break
    case 'edit': ElMessage.info('编辑报告'); break
    case 'schedule': ElMessage.info('添加到定时计划'); break
    case 'delete': 
      ElMessageBox.confirm('确定要删除此报告吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        reportsData.value = reportsData.value.filter(r => r.id !== report.id)
        ElMessage.success('报告已删除')
      }).catch(() => {})
      break
  }
}

const handleEditTemplate = (template) => {
  templateForm.name = template.name
  templateForm.type = template.type
  templateForm.items = [...template.items]
  templateTab.value = 'edit'
}

const handleDeleteTemplate = async (template) => {
  try {
    await reports.deleteReportTemplate(template.id)
    templates.value = templates.value.filter(t => t.id !== template.id)
    ElMessage.success('模板已删除')
  } catch (error) {
    ElMessage.error('删除模板失败')
  }
}

const handleSaveTemplate = async () => {
  try {
    await reports.createReportTemplate(templateForm)
    ElMessage.success('模板保存成功')
    templateTab.value = 'list'
    loadReports()
  } catch (error) {
    ElMessage.error('保存模板失败')
  }
}

const handlePrint = () => {
  ElMessage.success('正在调用打印...')
}

// 初始化
onMounted(() => {
  loadReports()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.reports-page {
  animation: fadeIn 0.3s ease;
}

// ========== 页面头部 ==========
.page-header {
  @include flex-between;
  margin-bottom: $spacing-xl;

  .page-header-left {
    .page-title {
      font-size: $font-size-xxl;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin: 0 0 4px 0;
    }

    .page-subtitle {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin: 0;
    }
  }

  .page-header-actions {
    display: flex;
    gap: $spacing-sm;
  }
}

// ========== 快捷操作 ==========
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.quick-action-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-lg;
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  cursor: pointer;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-base;
  }

  .action-icon {
    width: 48px;
    height: 48px;
    border-radius: $border-radius-md;
    @include flex-center;
    font-size: 22px;
    color: #fff;

    &.daily { background: linear-gradient(135deg, #165dff, #4080ff); }
    &.weekly { background: linear-gradient(135deg, #00b42a, #23c343); }
    &.alert { background: linear-gradient(135deg, #f53f3f, #ff7875); }
    &.workorder { background: linear-gradient(135deg, #ff7d00, #ff9d00); }
  }

  .action-text {
    .action-title {
      font-size: $font-size-base;
      font-weight: $font-weight-semibold;
      color: $text-primary;
    }

    .action-desc {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-top: 2px;
    }
  }
}

// ========== 筛选工具栏 ==========
.filter-bar {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  background: $bg-container;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-lg;
  box-shadow: $shadow-sm;

  .filter-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }

  .filter-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
}

// ========== 表格 ==========
.table-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.report-info {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.report-icon {
  width: 40px;
  height: 40px;
  border-radius: $border-radius-md;
  @include flex-center;
  font-size: 18px;
  color: #fff;

  &.daily { background: linear-gradient(135deg, #165dff, #4080ff); }
  &.weekly { background: linear-gradient(135deg, #00b42a, #23c343); }
  &.monthly { background: linear-gradient(135deg, #722ed1, #b37feb); }
  &.asset { background: linear-gradient(135deg, #ff7d00, #ff9d00); }
  &.alert { background: linear-gradient(135deg, #f53f3f, #ff7875); }
  &.workorder { background: linear-gradient(135deg, #00c7bd, #2daa9c); }
}

.report-text {
  .report-name {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-primary;
  }

  .report-meta {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-xs;
    color: $text-secondary;
    margin-top: 2px;

    .type-badge {
      background: $bg-page;
      padding: 2px 6px;
      border-radius: 4px;
    }
  }
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
}

// ========== 表格底部 ==========
.table-footer {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  border-top: 1px solid $border-light;

  .table-info {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

// ========== 表单 ==========
.form-hint {
  margin-left: $spacing-sm;
  font-size: $font-size-xs;
  color: $text-secondary;
}

// ========== 报告预览 ==========
.report-preview {
  .preview-header {
    margin-bottom: $spacing-xl;

    h3 {
      font-size: $font-size-lg;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin: 0 0 $spacing-md 0;
    }

    .preview-meta {
      display: flex;
      gap: $spacing-lg;
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }

  .preview-content {
    .preview-section {
      margin-bottom: $spacing-xl;

      h4 {
        font-size: $font-size-base;
        font-weight: $font-weight-semibold;
        color: $text-primary;
        margin-bottom: $spacing-md;
      }
    }
  }

  .preview-footer {
    display: flex;
    gap: $spacing-md;
    padding-top: $spacing-lg;
    border-top: 1px solid $border-light;
  }
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
}

.stat-item {
  padding: $spacing-lg;
  background: $bg-page;
  border-radius: $border-radius-md;
  text-align: center;

  .stat-value {
    display: block;
    font-size: $font-size-xxl;
    font-weight: $font-weight-bold;
    color: $primary;
  }

  .stat-label {
    display: block;
    font-size: $font-size-sm;
    color: $text-secondary;
    margin-top: 4px;
  }
}

.chart-placeholder {
  height: 200px;
  background: $bg-page;
  border-radius: $border-radius-md;
  @include flex-center;
  flex-direction: column;
  gap: $spacing-sm;

  .placeholder-icon {
    font-size: 48px;
    color: $text-placeholder;
  }

  span {
    font-size: $font-size-sm;
    color: $text-placeholder;
  }
}

// ========== 动画 ==========
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

// ========== 响应式 ==========
@include respond-to('xl') {
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }

  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@include respond-to('lg') {
  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-md;
  }

  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>