<template>
  <div>
    <div class="page-header">
      <h2>AI分析</h2>
      <n-button @click="loadStats" :loading="statsLoading">
        <template #icon><n-icon><RefreshOutline /></n-icon></template>
        刷新统计
      </n-button>
    </div>

    <!-- 统计卡片 -->
    <n-grid cols="4 m:2 s:1" responsive="screen" :x-gap="16" :y-gap="16" style="margin-bottom:16px">
      <n-gi v-for="item in statsCards" :key="item.label">
        <n-card :bordered="false" class="stat-card">
          <div class="stat-icon" :style="{ background: item.color }">
            <n-icon size="22" color="#fff"><component :is="item.icon" /></n-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ item.value }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- 故障排查 -->
      <n-tab-pane name="troubleshoot" tab="故障排查">
        <n-card :bordered="false">
          <n-form :model="troubleshootForm" label-placement="left" label-width="100">
            <n-form-item label="故障现象">
              <n-input v-model:value="troubleshootForm.symptom" type="textarea"
                placeholder="请描述您遇到的问题..." :rows="3" />
            </n-form-item>
            <n-form-item label="设备信息">
              <n-input v-model:value="troubleshootForm.deviceInfo"
                placeholder="设备名称、IP、型号等" />
            </n-form-item>
            <n-form-item label="错误日志">
              <n-input v-model:value="troubleshootForm.errorLog" type="textarea"
                placeholder="粘贴相关错误日志..." :rows="5" />
            </n-form-item>
          </n-form>
          <n-space style="margin-top: 16px">
            <n-button type="primary" @click="handleTroubleshoot" :loading="loading">
              提交诊断
            </n-button>
            <n-button type="info" @click="handleAutoDiagnose" :loading="loading">
              <template #icon><n-icon><FlashOutline /></n-icon></template>
              自动诊断
            </n-button>
          </n-space>
          <n-divider />
          <div v-if="troubleshootResult" class="result-area">
            <n-alert type="info" :title="'诊断结果'">
              <pre class="result-text">{{ troubleshootResult }}</pre>
            </n-alert>
          </div>
        </n-card>
      </n-tab-pane>

      <!-- 日志分析 -->
      <n-tab-pane name="logs" tab="日志分析">
        <n-card :bordered="false">
          <n-input v-model:value="logText" type="textarea"
            placeholder="粘贴日志内容..." :rows="10" class="log-textarea" />
          <n-space style="margin-top: 12px">
            <n-button type="primary" @click="handleAnalyzeLogs" :loading="loading">
              <template #icon><n-icon><SearchOutline /></n-icon></template>
              分析日志
            </n-button>
          </n-space>
          <div v-if="logResult" class="result-area">
            <n-alert type="success" :title="'分析结果'">
              <pre class="result-text">{{ logResult }}</pre>
            </n-alert>
          </div>
        </n-card>
      </n-tab-pane>

      <!-- 优化建议 -->
      <n-tab-pane name="suggest" tab="优化建议">
        <n-card :bordered="false">
          <n-form :model="suggestForm">
            <n-form-item label="优化类型">
              <n-select v-model:value="suggestForm.type" :options="suggestTypeOptions" />
            </n-form-item>
            <n-form-item label="补充说明">
              <n-input v-model:value="suggestForm.description" type="textarea"
                placeholder="描述您的系统环境、需求等..." :rows="5" />
            </n-form-item>
          </n-form>
          <n-space style="margin-top: 12px">
            <n-button type="primary" @click="handleSuggest" :loading="loading">
              生成建议
            </n-button>
          </n-space>
          <div v-if="suggestResult" class="result-area">
            <n-alert type="warning" :title="'优化建议'">
              <pre class="result-text">{{ suggestResult }}</pre>
            </n-alert>
          </div>
        </n-card>
      </n-tab-pane>

      <!-- 报表解读 -->
      <n-tab-pane name="interpret" tab="报表解读">
        <n-card :bordered="false">
          <n-form :model="interpretForm">
            <n-form-item label="报表内容">
              <n-input v-model:value="interpretForm.content" type="textarea"
                placeholder="粘贴报表内容或描述..." :rows="8" />
            </n-form-item>
            <n-form-item label="关注点">
              <n-input v-model:value="interpretForm.focus"
                placeholder="您希望重点分析哪些方面..." />
            </n-form-item>
          </n-form>
          <n-space style="margin-top: 12px">
            <n-button type="primary" @click="handleInterpret" :loading="loading">
              解读报表
            </n-button>
          </n-space>
          <div v-if="interpretResult" class="result-area">
            <n-alert type="info" :title="'报表解读'">
              <pre class="result-text">{{ interpretResult }}</pre>
            </n-alert>
          </div>
        </n-card>
      </n-tab-pane>

      <!-- 知识问答 -->
      <n-tab-pane name="qa" tab="知识问答">
        <n-card :bordered="false">
          <n-form :model="qaForm">
            <n-form-item label="问题">
              <n-input v-model:value="qaForm.question" type="textarea"
                placeholder="输入您的技术问题..." :rows="4" />
            </n-form-item>
          </n-form>
          <n-space style="margin-top: 12px">
            <n-button type="primary" @click="handleQA" :loading="loading">
              提问
            </n-button>
          </n-space>
          <div v-if="qaResult" class="result-area">
            <n-alert type="success" :title="'回答'">
              <pre class="result-text">{{ qaResult }}</pre>
            </n-alert>
          </div>
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import {
  RefreshOutline, FlashOutline, SearchOutline, ChatbubbleOutline,
  TrendingUpOutline, AlertOutline, BookOutline
} from '@vicons/ionicons5'
import {
  troubleshoot, troubleshootAuto, analyzeLogs, suggest,
  interpretReport, questionAnswer, getAiStats
} from '@/api/ai'

const message = useMessage()
const loading = ref(false)
const statsLoading = ref(false)
const activeTab = ref('troubleshoot')

// 统计
const statsData = ref({})
const statsCards = ref([
  { label: '总提问次数', value: 0, icon: ChatbubbleOutline, color: '#2080f0' },
  { label: '故障排查', value: 0, icon: AlertOutline, color: '#d03050' },
  { label: '日志分析', value: 0, icon: SearchOutline, color: '#f0a020' },
  { label: '优化建议', value: 0, icon: TrendingUpOutline, color: '#18a058' }
])

// 故障排查
const troubleshootForm = ref({ symptom: '', deviceInfo: '', errorLog: '' })
const troubleshootResult = ref('')

// 日志分析
const logText = ref('')
const logResult = ref('')

// 优化建议
const suggestTypeOptions = [
  { label: '性能优化', value: 'performance' },
  { label: '安全加固', value: 'security' },
  { label: '容量规划', value: 'capacity' },
  { label: '综合优化', value: 'general' }
]
const suggestForm = ref({ type: 'performance', description: '' })
const suggestResult = ref('')

// 报表解读
const interpretForm = ref({ content: '', focus: '' })
const interpretResult = ref('')

// 知识问答
const qaForm = ref({ question: '' })
const qaResult = ref('')

async function loadStats() {
  statsLoading.value = true
  try {
    const res = await getAiStats()
    statsData.value = res.data || {}
    const d = res.data || {}
    statsCards.value[0].value = d.total_questions || 0
    statsCards.value[1].value = d.troubleshoot_count || 0
    statsCards.value[2].value = d.log_analysis_count || 0
    statsCards.value[3].value = d.suggestion_count || 0
  } catch (e) {
    console.error('Load stats error:', e)
  } finally {
    statsLoading.value = false
  }
}

async function handleTroubleshoot() {
  if (!troubleshootForm.value.symptom) {
    message.warning('请填写故障现象')
    return
  }
  loading.value = true
  try {
    const res = await troubleshoot(troubleshootForm.value)
    troubleshootResult.value = res.data?.result || res.data?.reply || '诊断完成'
    message.success('诊断完成')
  } catch (e) {
    message.error('诊断失败')
  } finally {
    loading.value = false
  }
}

async function handleAutoDiagnose() {
  loading.value = true
  try {
    const res = await troubleshootAuto(troubleshootForm.value)
    troubleshootResult.value = res.data?.result || res.data?.reply || '自动诊断完成'
    message.success('自动诊断完成')
  } catch (e) {
    message.error('自动诊断失败')
  } finally {
    loading.value = false
  }
}

async function handleAnalyzeLogs() {
  if (!logText.value.trim()) {
    message.warning('请粘贴日志内容')
    return
  }
  loading.value = true
  try {
    const res = await analyzeLogs({ logs: logText.value })
    logResult.value = res.data?.result || res.data?.reply || '日志分析完成'
    message.success('日志分析完成')
  } catch (e) {
    message.error('日志分析失败')
  } finally {
    loading.value = false
  }
}

async function handleSuggest() {
  if (!suggestForm.value.description) {
    message.warning('请补充说明')
    return
  }
  loading.value = true
  try {
    const res = await suggest(suggestForm.value)
    suggestResult.value = res.data?.result || res.data?.reply || '建议已生成'
    message.success('建议已生成')
  } catch (e) {
    message.error('生成建议失败')
  } finally {
    loading.value = false
  }
}

async function handleInterpret() {
  if (!interpretForm.value.content) {
    message.warning('请填写报表内容')
    return
  }
  loading.value = true
  try {
    const res = await interpretReport(interpretForm.value)
    interpretResult.value = res.data?.result || res.data?.reply || '报表解读完成'
    message.success('报表解读完成')
  } catch (e) {
    message.error('报表解读失败')
  } finally {
    loading.value = false
  }
}

async function handleQA() {
  if (!qaForm.value.question.trim()) {
    message.warning('请输入问题')
    return
  }
  loading.value = true
  try {
    const res = await questionAnswer({ question: qaForm.value.question })
    qaResult.value = res.data?.answer || res.data?.reply || '回答完毕'
    message.success('回答完毕')
  } catch (e) {
    message.error('提问失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px;
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
}
.stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.result-area {
  margin-top: 16px;
}
.result-text {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}
.log-textarea {
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
}
</style>
