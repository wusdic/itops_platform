<template>
  <div class="ai-analyze-container">
    <div class="page-header">
      <h1>智能分析</h1>
      <p>AI驱动的运维故障排查与优化建议</p>
    </div>

    <div class="analyze-toolbar">
      <div class="tab-switcher">
        <el-radio-group v-model="activeTab" @change="handleTabChange">
          <el-radio-button value="logs">
            <span class="tab-icon">📋</span> 日志分析
          </el-radio-button>
          <el-radio-button value="troubleshoot">
            <span class="tab-icon">🔧</span> 故障诊断
          </el-radio-button>
          <el-radio-button value="report">
            <span class="tab-icon">📊</span> 报告解读
          </el-radio-button>
        </el-radio-group>
      </div>
      <el-button type="primary" plain @click="handleNewAnalysis">
        <el-icon><Plus /></el-icon> 新建分析
      </el-button>
    </div>

    <div class="analyze-content">
      <el-card class="input-card">
        <template #header>
          <div class="card-header">
            <span>{{ tabConfig[activeTab].title }}</span>
          </div>
        </template>
        <el-form :model="formData" label-position="top">
          <el-form-item :label="tabConfig[activeTab].inputLabel">
            <el-input
              v-model="formData.content"
              type="textarea"
              :rows="8"
              :placeholder="tabConfig[activeTab].placeholder"
              resize="vertical"
            />
          </el-form-item>
          <el-form-item v-if="activeTab === 'report'">
            <el-select v-model="formData.reportType" placeholder="选择报告类型" style="width: 200px">
              <el-option label="性能报告" value="performance" />
              <el-option label="安全报告" value="security" />
              <el-option label="运维报告" value="ops" />
              <el-option label="容量报告" value="capacity" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleAnalyze" :disabled="!formData.content.trim()">
              {{ loading ? '分析中...' : '开始分析' }}
            </el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <div v-if="loading" class="loading-state">
        <el-icon class="loading-spinner"><Loading /></el-icon>
        <p>AI 正在分析，请稍候...</p>
      </div>

      <el-card v-if="result && !loading" class="result-card">
        <template #header>
          <div class="card-header">
            <span>分析结果</span>
            <el-button size="small" text @click="handleCopy">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
        </template>
        <div class="result-content" v-html="renderedResult"></div>
      </el-card>

      <el-card v-if="error && !loading" class="error-card">
        <el-alert type="error" :closable="false">
          <template #title>
            <span>{{ error }}</span>
          </template>
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Loading, CopyDocument } from '@element-plus/icons-vue'
import { ai } from '@/api'

const activeTab = ref('logs')
const loading = ref(false)
const result = ref('')
const error = ref('')

const formData = reactive({
  content: '',
  reportType: 'performance'
})

const tabConfig = {
  logs: {
    title: '日志分析',
    inputLabel: '日志内容',
    placeholder: '请粘贴日志内容，AI将分析可能的问题和异常...',
    promptTemplate: (content) => `请分析以下日志，识别潜在问题、错误和异常模式，并提供解决方案建议。\n\n日志内容：\n${content}`
  },
  troubleshoot: {
    title: '故障诊断',
    inputLabel: '故障描述',
    placeholder: '请描述设备故障或告警信息，AI将诊断可能的原因并给出解决方案...',
    promptTemplate: (content) => `请诊断以下故障，分析可能的原因并提供详细的解决步骤。\n\n故障/告警信息：\n${content}`
  },
  report: {
    title: '报告解读',
    inputLabel: '报告内容',
    placeholder: '请粘贴报告内容或关键指标，AI将解读关键指标和发现...',
    promptTemplate: (content, reportType) => `请解读以下${reportType}报告，提取关键指标、分析发现并给出建议。\n\n报告内容：\n${content}`
  }
}

const renderedResult = computed(() => {
  if (!result.value) return ''
  return renderMarkdown(result.value)
})

const renderMarkdown = (text) => {
  if (!text) return ''
  
  let html = text
    // 转义 HTML 特殊字符
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 代码块
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    // 行内代码
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 加粗
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // 标题
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    // 列表
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
    // 换行
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
  
  // 包装列表
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
  // 清理连续列表
  html = html.replace(/<\/ul><ul>/g, '')
  
  return `<p>${html}</p>`
}

const handleTabChange = () => {
  result.value = ''
  error.value = ''
  formData.content = ''
}

const handleNewAnalysis = () => {
  handleTabChange()
}

const handleReset = () => {
  formData.content = ''
  result.value = ''
  error.value = ''
}

const handleAnalyze = async () => {
  if (!formData.content.trim()) {
    ElMessage.warning('请输入分析内容')
    return
  }

  loading.value = true
  error.value = ''
  result.value = ''

  try {
    const config = tabConfig[activeTab.value]
    const prompt = activeTab.value === 'report' 
      ? config.promptTemplate(formData.content, formData.reportType)
      : config.promptTemplate(formData.content)

    const res = await ai.chat({
      message: prompt,
      stream: false
    })

    // 提取响应内容
    result.value = typeof res === 'string' 
      ? res 
      : (res.result || res.response || res.data?.response || JSON.stringify(res))
      
  } catch (e) {
    console.error('AI analysis error:', e)
    error.value = '分析服务暂不可用，请稍后重试。错误信息：' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

const handleCopy = async () => {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(result.value)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.ai-analyze-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.page-header p {
  margin: 0;
  color: #909399;
}

.analyze-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: #fff;
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.tab-switcher :deep(.el-radio-button__inner) {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
}

.tab-icon {
  font-size: 16px;
}

.analyze-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: #fff;
  border-radius: 8px;
}

.loading-spinner {
  font-size: 32px;
  color: #409eff;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-state p {
  margin-top: 16px;
  color: #606266;
}

.result-card {
  border-radius: 8px;
}

.result-content {
  line-height: 1.8;
  color: #303133;
}

.result-content :deep(p) {
  margin: 0 0 12px 0;
}

.result-content :deep(h2) {
  font-size: 18px;
  margin: 20px 0 12px 0;
  color: #409eff;
}

.result-content :deep(h3) {
  font-size: 16px;
  margin: 16px 0 10px 0;
  color: #409eff;
}

.result-content :deep(h4) {
  font-size: 15px;
  margin: 14px 0 8px 0;
  color: #303133;
}

.result-content :deep(ul) {
  margin: 8px 0;
  padding-left: 24px;
}

.result-content :deep(li) {
  margin: 4px 0;
}

.result-content :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 12px 0;
}

.result-content :deep(code) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
}

.result-content :deep(strong) {
  color: #409eff;
  font-weight: 600;
}

.result-content :deep(em) {
  color: #67c23a;
}

.error-card {
  border-radius: 8px;
}

@media (max-width: 768px) {
  .analyze-toolbar {
    flex-direction: column;
    gap: 16px;
  }
  
  .tab-switcher :deep(.el-radio-group) {
    display: flex;
    flex-direction: column;
  }
}
</style>
