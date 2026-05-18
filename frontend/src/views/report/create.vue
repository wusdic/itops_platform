<template>
  <div class="create-report-container">
    <n-card class="main-card">
      <div class="card-header">
        <div class="header-info">
          <h2>Generate New Report</h2>
          <p>Create customized reports with your preferred settings and filters</p>
        </div>
      </div>

      <n-tabs type="line" animated>
        <!-- Basic Settings Tab -->
        <n-tab-pane name="basic" tab="Basic Settings">
          <div class="tab-content">
            <n-grid :cols="2" :x-gap="24">
              <!-- Left Column - Report Configuration -->
              <n-gi>
                <n-card title="Report Configuration" class="config-card">
                  <!-- Report Type Selector -->
                  <n-form-item label="Report Type" required>
                    <n-grid :cols="3" :x-gap="12" :y-gap="12">
                      <n-gi v-for="type in reportTypes" :key="type.value">
                        <div
                          class="type-option"
                          :class="{ active: formData.type === type.value }"
                          @click="formData.type = type.value"
                        >
                          <n-icon :size="24" class="type-icon">
                            <component :is="type.icon" />
                          </n-icon>
                          <span class="type-label">{{ type.label }}</span>
                          <span class="type-desc">{{ type.description }}</span>
                        </div>
                      </n-gi>
                    </n-grid>
                  </n-form-item>

                  <!-- Template Selector -->
                  <n-form-item label="Report Template" required>
                    <n-select
                      v-model:value="formData.template_id"
                      :options="templateOptions"
                      placeholder="Select a template"
                      filterable
                      :loading="templatesLoading"
                    />
                  </n-form-item>

                  <!-- Output Format Selector -->
                  <n-form-item label="Output Format" required>
                    <n-space vertical :size="12">
                      <n-grid :cols="3" :x-gap="12">
                        <n-gi v-for="format in outputFormats" :key="format.value">
                          <div
                            class="format-option"
                            :class="{ active: formData.format === format.value }"
                            @click="formData.format = format.value"
                          >
                            <n-icon :size="32" class="format-icon">
                              <component :is="format.icon" />
                            </n-icon>
                            <span class="format-label">{{ format.label }}</span>
                          </div>
                        </n-gi>
                      </n-grid>
                    </n-space>
                  </n-form-item>
                </n-card>
              </n-gi>

              <!-- Right Column - Date & Filters -->
              <n-gi>
                <n-card title="Date Range & Filters" class="config-card">
                  <!-- Date Range Picker -->
                  <n-form-item label="Date Range" required>
                    <n-date-picker
                      v-model:value="formData.date_range"
                      type="daterange"
                      range
                      clearable
                      style="width: 100%"
                    />
                  </n-form-item>

                  <!-- Quick Date Presets -->
                  <n-form-item label="Quick Select">
                    <n-space :size="8">
                      <n-button
                        v-for="preset in datePresets"
                        :key="preset.label"
                        size="small"
                        @click="applyDatePreset(preset)"
                      >
                        {{ preset.label }}
                      </n-button>
                    </n-space>
                  </n-form-item>

                  <!-- Device Group Filter -->
                  <n-form-item label="Device Group">
                    <n-select
                      v-model:value="formData.device_group"
                      :options="deviceGroupOptions"
                      placeholder="All device groups"
                      clearable
                      multiple
                    />
                  </n-form-item>

                  <!-- Alert Level Filter -->
                  <n-form-item label="Alert Level">
                    <n-select
                      v-model:value="formData.alert_level"
                      :options="alertLevelOptions"
                      placeholder="All alert levels"
                      clearable
                      multiple
                    />
                  </n-form-item>
                </n-card>
              </n-gi>
            </n-grid>

            <!-- Report Name -->
            <n-card title="Report Details" class="details-card">
              <n-form-item label="Report Name" required>
                <n-input
                  v-model:value="formData.name"
                  placeholder="Enter a name for this report"
                />
              </n-form-item>
              <n-form-item label="Description">
                <n-input
                  v-model:value="formData.description"
                  type="textarea"
                  placeholder="Optional description for this report"
                  :rows="2"
                />
              </n-form-item>
            </n-card>
          </div>
        </n-tab-pane>

        <!-- Preview Tab -->
        <n-tab-pane name="preview" tab="Preview">
          <div class="tab-content">
            <n-card title="Report Preview" class="preview-card">
              <template #header-extra>
                <n-space>
                  <n-button @click="refreshPreview" :loading="previewLoading">
                    <template #icon>
                      <n-icon><RefreshOutline /></n-icon>
                    </template>
                    Refresh
                  </n-button>
                </n-space>
              </template>
              
              <n-spin :show="previewLoading">
                <div class="preview-container">
                  <div v-if="previewContent" class="preview-content" v-html="previewContent"></div>
                  <n-empty v-else description="Configure settings and click Generate Preview to see a preview" />
                </div>
              </n-spin>
            </n-card>
          </div>
        </n-tab-pane>
      </n-tabs>

      <!-- Action Buttons -->
      <div class="action-bar">
        <n-space justify="space-between" align="center">
          <n-button @click="handleReset">Reset Form</n-button>
          <n-space>
            <n-button @click="handleSaveTemplate" :loading="saving">
              <template #icon>
                <n-icon><DocumentTextOutline /></n-icon>
              </template>
              Save as Template
            </n-button>
            <n-button @click="handleGenerate" type="primary" :loading="generating">
              <template #icon>
                <n-icon><PlayOutline /></n-icon>
              </template>
              Generate Report
            </n-button>
          </n-space>
        </n-space>
      </div>
    </n-card>

    <!-- Save Template Modal -->
    <n-modal
      v-model:show="saveTemplateModal.show"
      preset="card"
      title="Save as Template"
      :style="{ width: '450px' }"
    >
      <n-form :model="saveTemplateForm" label-placement="top">
        <n-form-item label="Template Name" required>
          <n-input v-model:value="saveTemplateForm.name" placeholder="Enter template name" />
        </n-form-item>
        <n-form-item label="Description">
          <n-input
            v-model:value="saveTemplateForm.description"
            type="textarea"
            placeholder="Optional description"
            :rows="2"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="saveTemplateModal.show = false">Cancel</n-button>
          <n-button type="primary" @click="confirmSaveTemplate" :loading="savingTemplate">
            Save
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- Generation Progress Modal -->
    <n-modal
      v-model:show="progressModal.show"
      preset="card"
      title="Generating Report"
      :closable="false"
      :mask-closable="false"
    >
      <div class="progress-content">
        <n-progress
          type="line"
          :percentage="progressModal.percentage"
          :status="progressModal.status"
          :processing="progressModal.processing"
        />
        <p class="progress-text">{{ progressModal.message }}</p>
      </div>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, h } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import {
  AddOutline,
  DocumentTextOutline,
  DownloadOutline,
  TrashOutline,
  PlayOutline,
  EyeOutline,
  CreateOutline,
  RefreshOutline,
  ChevronForwardOutline
} from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()

// Loading states
const templatesLoading = ref(false)
const previewLoading = ref(false)
const generating = ref(false)
const saving = ref(false)
const savingTemplate = ref(false)

// Form data
const formData = reactive({
  name: '',
  description: '',
  type: 'daily',
  template_id: null,
  format: 'pdf',
  date_range: null,
  device_group: null,
  alert_level: null
})

// Save template modal
const saveTemplateModal = reactive({
  show: false
})

const saveTemplateForm = reactive({
  name: '',
  description: ''
})

// Progress modal
const progressModal = reactive({
  show: false,
  percentage: 0,
  status: 'success',
  processing: true,
  message: 'Preparing report generation...'
})

// Preview content
const previewContent = ref('')

// Template list
const templateList = ref([])

// Template options for select
const templateOptions = computed(() => {
  return templateList.value.map(t => ({
    label: t.name,
    value: t.id
  }))
})

// Device group options
const deviceGroupOptions = [
  { label: 'Production Servers', value: 'prod_servers' },
  { label: 'Development Servers', value: 'dev_servers' },
  { label: 'Database Servers', value: 'db_servers' },
  { label: 'Network Devices', value: 'network' },
  { label: 'Storage Systems', value: 'storage' }
]

// Alert level options
const alertLevelOptions = [
  { label: 'Critical', value: 'critical' },
  { label: 'Warning', value: 'warning' },
  { label: 'Info', value: 'info' }
]

// Report types configuration
const reportTypes = [
  {
    value: 'daily',
    label: 'Daily',
    description: '24-hour summary',
    icon: 'DailyOutline'
  },
  {
    value: 'weekly',
    label: 'Weekly',
    description: '7-day summary',
    icon: 'WeeklyOutline'
  },
  {
    value: 'monthly',
    label: 'Monthly',
    description: '30-day summary',
    icon: 'MonthlyOutline'
  },
  {
    value: 'quarterly',
    label: 'Quarterly',
    description: '90-day summary',
    icon: 'QuarterlyOutline'
  },
  {
    value: 'annual',
    label: 'Annual',
    description: 'Yearly summary',
    icon: 'AnnualOutline'
  },
  {
    value: 'custom',
    label: 'Custom',
    description: 'Custom date range',
    icon: 'CustomOutline'
  }
]

// Output formats configuration
const outputFormats = [
  { value: 'pdf', label: 'PDF', icon: 'PdfOutline' },
  { value: 'html', label: 'HTML', icon: 'HtmlOutline' },
  { value: 'excel', label: 'Excel', icon: 'ExcelOutline' }
]

// Date presets
const datePresets = [
  { label: 'Today', getValue: () => { const now = new Date(); return [now, now] } },
  { label: 'Yesterday', getValue: () => { const y = new Date(); y.setDate(y.getDate() - 1); return [y, y] } },
  { label: 'Last 7 Days', getValue: () => { const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 6); return [s, e] } },
  { label: 'Last 30 Days', getValue: () => { const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 29); return [s, e] } },
  { label: 'This Month', getValue: () => { const now = new Date(); return [new Date(now.getFullYear(), now.getMonth(), 1), now] } },
  { label: 'Last Month', getValue: () => { const now = new Date(); const s = new Date(now.getFullYear(), now.getMonth() - 1, 1); const e = new Date(now.getFullYear(), now.getMonth(), 0); return [s, e] } }
]

// Helper functions
function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
}

function applyDatePreset(preset) {
  const range = preset.getValue()
  if (range) {
    formData.date_range = range
  }
}

function validateForm() {
  if (!formData.name?.trim()) {
    message.error('Please enter a report name')
    return false
  }
  if (!formData.type) {
    message.error('Please select a report type')
    return false
  }
  if (!formData.template_id) {
    message.error('Please select a template')
    return false
  }
  if (!formData.format) {
    message.error('Please select an output format')
    return false
  }
  if (!formData.date_range || !formData.date_range[0] || !formData.date_range[1]) {
    message.error('Please select a date range')
    return false
  }
  return true
}

// API Functions
async function fetchTemplates() {
  templatesLoading.value = true
  try {
    const response = await fetch('/api/v1/reports/template', {
      method: 'GET',
      headers: getHeaders()
    })
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    const data = await response.json()
    templateList.value = data.items || data || []
  } catch (error) {
    console.error('Failed to fetch templates:', error)
    message.error('Failed to load templates')
    templateList.value = []
  } finally {
    templatesLoading.value = false
  }
}

async function fetchPreview() {
  if (!formData.template_id) {
    message.warning('Please select a template first')
    return
  }
  
  previewLoading.value = true
  try {
    const payload = {
      template_id: formData.template_id,
      type: formData.type,
      start_date: formData.date_range?.[0] ? new Date(formData.date_range[0]).toISOString() : null,
      end_date: formData.date_range?.[1] ? new Date(formData.date_range[1]).toISOString() : null,
      device_group: formData.device_group,
      alert_level: formData.alert_level
    }
    
    const response = await fetch('/api/v1/reports/preview', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    })
    
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    const data = await response.json()
    previewContent.value = data.content || data.html || '<p>Preview not available</p>'
  } catch (error) {
    console.error('Failed to fetch preview:', error)
    message.error('Failed to load preview')
    previewContent.value = ''
  } finally {
    previewLoading.value = false
  }
}

async function generateReport() {
  generating.value = true
  progressModal.show = true
  progressModal.percentage = 0
  progressModal.status = 'success'
  progressModal.processing = true
  progressModal.message = 'Starting report generation...'
  
  try {
    // Simulate progress updates
    const progressInterval = setInterval(() => {
      if (progressModal.percentage < 90) {
        progressModal.percentage += Math.random() * 15
      }
    }, 500)
    
    const payload = {
      name: formData.name,
      description: formData.description,
      template_id: formData.template_id,
      type: formData.type,
      format: formData.format,
      start_date: formData.date_range?.[0] ? new Date(formData.date_range[0]).toISOString() : null,
      end_date: formData.date_range?.[1] ? new Date(formData.date_range[1]).toISOString() : null,
      filters: {
        device_group: formData.device_group,
        alert_level: formData.alert_level
      }
    }
    
    const response = await fetch('/api/v1/reports/generate', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    })
    
    clearInterval(progressInterval)
    
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    
    const data = await response.json()
    progressModal.percentage = 100
    progressModal.message = 'Report generated successfully!'
    progressModal.processing = false
    progressModal.status = 'success'
    
    message.success('Report generated successfully')
    
    setTimeout(() => {
      progressModal.show = false
    }, 1500)
    
    return data
  } catch (error) {
    console.error('Failed to generate report:', error)
    progressModal.percentage = 100
    progressModal.status = 'error'
    progressModal.processing = false
    progressModal.message = 'Failed to generate report'
    message.error('Failed to generate report')
    throw error
  } finally {
    generating.value = false
  }
}

async function saveAsTemplate() {
  savingTemplate.value = true
  try {
    const payload = {
      name: saveTemplateForm.name,
      description: saveTemplateForm.description,
      type: formData.type,
      content: `<!-- Template for ${formData.type} report -->\n<!-- Settings: ${JSON.stringify({ format: formData.format, filters: { device_group: formData.device_group, alert_level: formData.alert_level } })} -->`,
      active: true
    }
    
    const response = await fetch('/api/v1/reports/template', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    })
    
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    
    message.success('Template saved successfully')
    saveTemplateModal.show = false
    saveTemplateForm.name = ''
    saveTemplateForm.description = ''
    fetchTemplates()
  } catch (error) {
    console.error('Failed to save template:', error)
    message.error('Failed to save template')
  } finally {
    savingTemplate.value = false
  }
}

// Action Handlers
function handleReset() {
  dialog.warning({
    title: 'Confirm Reset',
    content: 'Are you sure you want to reset all form data?',
    positiveText: 'Reset',
    negativeText: 'Cancel',
    onPositiveClick: () => {
      formData.name = ''
      formData.description = ''
      formData.type = 'daily'
      formData.template_id = null
      formData.format = 'pdf'
      formData.date_range = null
      formData.device_group = null
      formData.alert_level = null
      previewContent.value = ''
      message.success('Form reset successfully')
    }
  })
}

function handleSaveTemplate() {
  if (!formData.type || !formData.format) {
    message.warning('Please select report type and format first')
    return
  }
  saveTemplateModal.show = true
}

function confirmSaveTemplate() {
  if (!saveTemplateForm.name?.trim()) {
    message.error('Please enter a template name')
    return
  }
  saveAsTemplate()
}

async function handleGenerate() {
  if (!validateForm()) return
  try {
    await generateReport()
  } catch (error) {
    // Error already handled in generateReport
  }
}

function refreshPreview() {
  fetchPreview()
}

// Lifecycle
onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped>
.create-report-container {
  padding: 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 100px);
}

.main-card {
  border-radius: 12px;
}

.card-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.header-info h2 {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.header-info p {
  margin: 0;
  font-size: 14px;
  color: #8c8c8c;
}

.tab-content {
  padding: 20px 0;
}

.config-card {
  margin-bottom: 16px;
  border-radius: 8px;
}

.details-card {
  margin-top: 16px;
  border-radius: 8px;
}

.preview-card {
  border-radius: 8px;
}

.preview-container {
  min-height: 400px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.preview-content {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  max-width: 100%;
  overflow-x: auto;
}

/* Report Type Selector */
.type-option {
  padding: 12px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  transition: all 0.2s ease;
  background: white;
}

.type-option:hover {
  border-color: #667eea;
  background: #f8f8ff;
}

.type-option.active {
  border-color: #667eea;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.type-option.active .type-label,
.type-option.active .type-desc {
  color: white;
}

.type-icon {
  margin-bottom: 6px;
  color: #667eea;
}

.type-option.active .type-icon {
  color: white;
}

.type-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 2px;
}

.type-desc {
  display: block;
  font-size: 11px;
  color: #8c8c8c;
}

/* Output Format Selector */
.format-option {
  padding: 16px 12px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  transition: all 0.2s ease;
  background: white;
}

.format-option:hover {
  border-color: #52c41a;
  background: #f8fff8;
}

.format-option.active {
  border-color: #52c41a;
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
  color: white;
}

.format-option.active .format-label {
  color: white;
}

.format-icon {
  margin-bottom: 8px;
  color: #52c41a;
}

.format-option.active .format-icon {
  color: white;
}

.format-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

/* Action Bar */
.action-bar {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

/* Progress Content */
.progress-content {
  padding: 20px 0;
}

.progress-text {
  text-align: center;
  margin-top: 12px;
  color: #666;
}
</style>
