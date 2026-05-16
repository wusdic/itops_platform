<template>
  <div>
    <div class="page-header"><h2>批量导入</h2></div>

    <n-grid cols="1" :x-gap="16" :y-gap="16">
      <!-- 步骤1: 下载模板 -->
      <n-gi>
        <n-card title="步骤 1：下载导入模板" :bordered="false">
          <n-space>
            <span>请先下载Excel模板，按模板格式填写设备信息</span>
            <n-button type="primary" @click="handleDownloadTemplate">
              <template #icon><n-icon><DownloadOutline /></n-icon></template>
              下载模板
            </n-button>
          </n-space>
        </n-card>
      </n-gi>

      <!-- 步骤2: 上传文件 -->
      <n-gi>
        <n-card title="步骤 2：上传文件" :bordered="false">
          <n-upload
            :file-list="fileList"
            :custom-request="handleUpload"
            :show-file-list="false"
            accept=".xlsx,.xls,.csv"
          >
            <n-upload-dragger>
              <div style="text-align:center">
                <n-icon size="48" color="#ccc"><CloudUploadOutline /></n-icon>
                <p style="margin:12px 0 4px">点击或拖拽文件到此区域上传</p>
                <p style="color:#999;font-size:12px">支持 .xlsx, .xls, .csv 格式</p>
              </div>
            </n-upload-dragger>
          </n-upload>
        </n-card>
      </n-gi>

      <!-- 步骤3: 验证预览 -->
      <n-gi v-if="validateResult">
        <n-card title="步骤 3：数据验证预览" :bordered="false">
          <n-space style="margin-bottom:12px">
            <n-tag type="success">有效: {{ validateResult.valid_count || 0 }}</n-tag>
            <n-tag type="error">无效: {{ validateResult.invalid_count || 0 }}</n-tag>
            <n-tag type="warning">重复: {{ validateResult.duplicate_count || 0 }}</n-tag>
          </n-space>
          <n-data-table
            :columns="previewColumns"
            :data="validateResult.items || []"
            size="small"
            :pagination="{ pageSize: 10 }"
            :max-height="400"
          />
          <template #header-extra>
            <n-button type="success" :loading="importLoading" @click="handleImport">
              <template #icon><n-icon><DownloadOutline /></n-icon></template>
              确认导入
            </n-button>
          </template>
        </n-card>
      </n-gi>

      <!-- 步骤4: 导入结果 -->
      <n-gi v-if="importResult">
        <n-card title="步骤 4：导入结果" :bordered="false">
          <n-result v-if="importResult.success" status="success" title="导入成功" :description="importResult.message" />
          <n-result v-else status="error" title="导入失败" :description="importResult.message" />
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup>
import { ref, reactive, h } from 'vue'
import { useMessage } from 'naive-ui'
import { DownloadOutline, CloudUploadOutline, CheckmarkCircleOutline, CloseCircleOutline } from '@vicons/ionicons5'
import { downloadTemplate, validateImport, importDevices } from '@/api/import'

const message = useMessage()

const fileList = ref([])
const validateResult = ref(null)
const importLoading = ref(false)
const importResult = ref(null)
const validateFile = ref(null)

const previewColumns = [
  { title: '行号', key: 'row', width: 80 },
  { title: '主机名', key: 'hostname' },
  { title: '名称', key: 'name' },
  { title: 'IP', key: 'ip', width: 140 },
  { title: '类型', key: 'device_type', width: 100 },
  {
    title: '状态', key: 'status', width: 100,
    render: row => row.valid
      ? h('n-tag', { type: 'success', size: 'small' }, { default: () => '有效' })
      : h('n-tag', { type: 'error', size: 'small' }, { default: () => row.error || '无效' })
  }
]

async function handleDownloadTemplate() {
  try {
    const res = await downloadTemplate()
    const blob = new Blob([res.data])
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '设备导入模板.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
    message.success('模板下载成功')
  } catch (e) {
    message.error('下载模板失败')
    console.error(e)
  }
}

async function handleUpload({ file, onFinish, onError }) {
  try {
    const formData = new FormData()
    formData.append('file', file.file)
    const res = await validateImport(formData)
    validateResult.value = res.data || res
    validateFile.value = file.file
    message.success('验证完成')
    onFinish()
  } catch (e) {
    message.error('验证失败')
    console.error(e)
    onError()
  }
}

async function handleImport() {
  if (!validateFile.value) {
    message.error('请先上传文件')
    return
  }
  importLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', validateFile.value)
    const res = await importDevices(formData)
    importResult.value = { success: true, message: res.data?.message || res.message || '导入成功' }
    message.success('导入成功')
  } catch (e) {
    importResult.value = { success: false, message: e.response?.data?.message || e.message || '导入失败' }
    message.error('导入失败')
  } finally {
    importLoading.value = false
  }
}
</script>
