<template>
  <div class="ai-analyze-container">
    <n-card>
      <template #header>
        <span>智能分析</span>
      </template>
      <n-alert type="info" :show-icon="true">
        AI 智能分析功能 - 输入日志或错误信息，AI 将自动分析问题原因并提供解决方案
      </n-alert>

      <n-space vertical size="large" class="analyze-form">
        <n-form-item label="分析类型">
          <n-select
            v-model:value="analyzeType"
            :options="typeOptions"
            placeholder="选择分析类型"
            style="width: 200px"
          />
        </n-form-item>

        <n-form-item label="分析内容">
          <n-input
            v-model:value="content"
            type="textarea"
            placeholder="输入日志、错误信息或系统状态描述..."
            :rows="6"
            :maxlength="2000"
            show-count
          />
        </n-form-item>

        <n-space>
          <n-button type="primary" :loading="analyzing" @click="handleAnalyze">开始分析</n-button>
          <n-button @click="handleReset">重置</n-button>
        </n-space>
      </n-space>

      <div v-if="result" class="result-container">
        <n-divider>分析结果</n-divider>
        <n-spin :show="analyzing">
          <n-card class="result-card" title="AI 分析报告">
            <n-input
              v-model:value="result"
              type="textarea"
              :rows="12"
              readonly
              placeholder="分析结果将显示在这里..."
            />
            <template #footer>
              <n-space>
                <n-button size="small" @click="handleCopy">复制结果</n-button>
                <n-button size="small" type="primary" @click="handleSave">保存记录</n-button>
              </n-space>
            </template>
          </n-card>
        </n-spin>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  NCard, NAlert, NInput, NSelect, NButton, NSpace,
  NFormItem, NDivider, NSpin, NForm
} from 'naive-ui'
import { useMessage } from 'naive-ui'

const message = useMessage()

const analyzeType = ref('log')
const content = ref('')
const result = ref('')
const analyzing = ref(false)

const typeOptions = [
  { label: '日志分析', value: 'log' },
  { label: '错误分析', value: 'error' },
  { label: '性能分析', value: 'performance' },
  { label: '安全分析', value: 'security' }
]

const fetchApi = async (url, options = {}) => {
  const token = localStorage.getItem('token') || ''
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {})
    }
  })
  if (!res.ok) throw new Error(`HTTP error ${res.status}`)
  return res.json()
}

const handleAnalyze = async () => {
  if (!content.value.trim()) {
    message.warning('请输入分析内容')
    return
  }

  analyzing.value = true
  try {
    const res = await fetchApi('/api/v1/ai/troubleshoot', {
      method: 'POST',
      body: JSON.stringify({ query: content.value })
    })
    // Support both {data: {...}} and direct result formats
    if (res.data) {
      result.value = typeof res.data === 'string' ? res.data : JSON.stringify(res.data, null, 2)
    } else if (typeof res === 'string') {
      result.value = res
    } else {
      result.value = JSON.stringify(res, null, 2)
    }
    message.success('分析完成')
  } catch (error) {
    console.error('Analyze error:', error)
    message.error('分析失败，请重试')
    result.value = '分析失败: ' + error.message
  } finally {
    analyzing.value = false
  }
}

const handleReset = () => {
  content.value = ''
  result.value = ''
  analyzeType.value = 'log'
}

const handleCopy = () => {
  navigator.clipboard.writeText(result.value).then(() => {
    message.success('已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}

const handleSave = () => {
  message.info('保存功能开发中')
}
</script>

<style scoped>
.ai-analyze-container {
  padding: 20px;
}
.analyze-form {
  margin-top: 20px;
}
.result-container {
  margin-top: 20px;
}
.result-card {
  margin-top: 12px;
}
</style>
