<template>
  <div class="template-container">
    <!-- Header -->
    <div class="header-section">
      <div class="header-title">
        <h2>Report Templates</h2>
        <p class="header-desc">Manage and configure report templates for automated generation</p>
      </div>
      <n-button type="primary" @click="handleCreate">
        <template #icon>
          <n-icon><AddOutline /></n-icon>
        </template>
        Create Template
      </n-button>
    </div>

    <!-- Templates Grid -->
    <n-grid :cols="3" :x-gap="20" :y-gap="20" v-if="templateList.length > 0">
      <n-gi v-for="template in templateList" :key="template.id">
        <n-card class="template-card" hoverable>
          <div class="template-header">
            <div class="template-icon">
              <n-icon :size="28"><DocumentTextOutline /></n-icon>
            </div>
            <div class="template-info">
              <h3 class="template-name">{{ template.name }}</h3>
              <n-tag :type="getTypeColor(template.type)" size="small">
                {{ formatType(template.type) }}
              </n-tag>
            </div>
          </div>
          
          <div class="template-description">
            {{ template.description || 'No description provided' }}
          </div>
          
          <div class="template-meta">
            <div class="meta-item">
              <span class="meta-label">Fields:</span>
              <span class="meta-value">{{ template.fields?.length || 0 }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Status:</span>
              <n-tag :type="template.active ? 'success' : 'default'" size="small">
                {{ template.active ? 'Active' : 'Inactive' }}
              </n-tag>
            </div>
          </div>

          <div class="template-actions">
            <n-button size="small" @click="handleEdit(template)">
              <template #icon>
                <n-icon><CreateOutline /></n-icon>
              </template>
              Edit
            </n-button>
            <n-button size="small" type="error" @click="handleDelete(template)">
              <template #icon>
                <n-icon><TrashOutline /></n-icon>
              </template>
              Delete
            </n-button>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Empty State -->
    <n-empty v-else description="No templates found" class="empty-state">
      <template #extra>
        <n-button size="small" @click="handleCreate">Create your first template</n-button>
      </template>
    </n-empty>

    <!-- Create/Edit Modal -->
    <n-modal
      v-model:show="modal.show"
      preset="card"
      :title="modal.isEdit ? 'Edit Template' : 'Create Template'"
      :style="{ width: '600px' }"
      :segmented="{ content: true, footer: true }"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-placement="top"
      >
        <n-form-item label="Template Name" path="name">
          <n-input
            v-model:value="formData.name"
            placeholder="Enter template name"
          />
        </n-form-item>

        <n-form-item label="Report Type" path="type">
          <n-select
            v-model:value="formData.type"
            :options="typeOptions"
            placeholder="Select report type"
          />
        </n-form-item>

        <n-form-item label="Description" path="description">
          <n-input
            v-model:value="formData.description"
            type="textarea"
            placeholder="Enter template description"
            :rows="3"
          />
        </n-form-item>

        <n-form-item label="Template Content" path="content">
          <n-input
            v-model:value="formData.content"
            type="textarea"
            placeholder="Enter HTML template content with placeholders like {{device_name}}, {{metric_value}}"
            :rows="8"
            monospaced
          />
        </n-form-item>

        <n-form-item label="Active Status">
          <n-switch v-model:value="formData.active" />
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="modal.show = false">Cancel</n-button>
          <n-button type="primary" @click="handleSubmit" :loading="modal.loading">
            {{ modal.isEdit ? 'Update' : 'Create' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- Delete Confirmation Modal -->
    <n-modal
      v-model:show="deleteModal.show"
      preset="dialog"
      title="Confirm Delete"
      :content="deleteModal.message"
      positive-text="Delete"
      negative-text="Cancel"
      type="error"
      @positive-click="handleConfirmDelete"
      @negative-click="deleteModal.show = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import {
  AddOutline,
  DocumentTextOutline,
  CreateOutline,
  TrashOutline
} from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const templateList = ref([])
const formRef = ref(null)

// Modal state
const modal = reactive({
  show: false,
  isEdit: false,
  loading: false,
  currentId: null
})

// Delete modal state
const deleteModal = reactive({
  show: false,
  message: '',
  templateId: null
})

// Form data
const formData = reactive({
  name: '',
  type: null,
  description: '',
  content: '',
  active: true
})

// Form rules
const formRules = {
  name: { required: true, message: 'Please enter template name', trigger: 'blur' },
  type: { required: true, type: 'string', message: 'Please select report type', trigger: 'change' },
  content: { required: true, message: 'Please enter template content', trigger: 'blur' }
}

// Type options
const typeOptions = [
  { label: 'Daily Report', value: 'daily' },
  { label: 'Weekly Report', value: 'weekly' },
  { label: 'Monthly Report', value: 'monthly' },
  { label: 'Quarterly Report', value: 'quarterly' },
  { label: 'Annual Report', value: 'annual' },
  { label: 'Custom Report', value: 'custom' }
]

// Helper functions
function getTypeColor(type) {
  const colors = {
    daily: 'info',
    weekly: 'success',
    monthly: 'warning',
    quarterly: 'error',
    annual: 'info',
    custom: 'default'
  }
  return colors[type] || 'default'
}

function formatType(type) {
  const labels = {
    daily: 'Daily',
    weekly: 'Weekly',
    monthly: 'Monthly',
    quarterly: 'Quarterly',
    annual: 'Annual',
    custom: 'Custom'
  }
  return labels[type] || type
}

function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
}

function resetForm() {
  formData.name = ''
  formData.type = null
  formData.description = ''
  formData.content = ''
  formData.active = true
}

// API Functions
async function fetchTemplates() {
  loading.value = true
  try {
    const response = await fetch('http://localhost:8000/api/v1/reports/template', {
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
    loading.value = false
  }
}

async function createTemplate() {
  try {
    const response = await fetch('http://localhost:8000/api/v1/reports/template', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(formData)
    })
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    const data = await response.json()
    message.success('Template created successfully')
    modal.show = false
    resetForm()
    fetchTemplates()
    return data
  } catch (error) {
    console.error('Failed to create template:', error)
    message.error('Failed to create template')
    throw error
  }
}

async function updateTemplate() {
  try {
    const response = await fetch(`http://localhost:8000/api/v1/reports/template/${modal.currentId}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(formData)
    })
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    const data = await response.json()
    message.success('Template updated successfully')
    modal.show = false
    resetForm()
    fetchTemplates()
    return data
  } catch (error) {
    console.error('Failed to update template:', error)
    message.error('Failed to update template')
    throw error
  }
}

async function deleteTemplate(id) {
  try {
    const response = await fetch(`http://localhost:8000/api/v1/reports/template/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    })
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    message.success('Template deleted successfully')
    fetchTemplates()
  } catch (error) {
    console.error('Failed to delete template:', error)
    message.error('Failed to delete template')
  }
}

// Action Handlers
function handleCreate() {
  resetForm()
  modal.isEdit = false
  modal.currentId = null
  modal.show = true
}

function handleEdit(template) {
  modal.isEdit = true
  modal.currentId = template.id
  formData.name = template.name
  formData.type = template.type
  formData.description = template.description || ''
  formData.content = template.content || ''
  formData.active = template.active ?? true
  modal.show = true
}

function handleDelete(template) {
  deleteModal.templateId = template.id
  deleteModal.message = `Are you sure you want to delete template "${template.name}"? This action cannot be undone.`
  deleteModal.show = true
}

function handleConfirmDelete() {
  if (deleteModal.templateId) {
    deleteTemplate(deleteModal.templateId)
  }
  deleteModal.show = false
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
    modal.loading = true
    if (modal.isEdit) {
      await updateTemplate()
    } else {
      await createTemplate()
    }
  } catch (error) {
    // Validation error - handled by form
  } finally {
    modal.loading = false
  }
}

// Lifecycle
onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped>
.template-container {
  padding: 16px;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-title h2 {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.header-desc {
  margin: 0;
  font-size: 14px;
  color: #8c8c8c;
}

.template-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.template-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.template-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.template-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.template-info {
  flex: 1;
  min-width: 0;
}

.template-name {
  margin: 0 0 6px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-description {
  flex: 1;
  font-size: 14px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.template-meta {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid #f0f0f0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-label {
  font-size: 13px;
  color: #8c8c8c;
}

.meta-value {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
}

.template-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  margin-top: 80px;
}
</style>
