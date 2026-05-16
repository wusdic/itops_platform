<template>
  <div class="ai-analyze-container">
    <div class="page-header">
      <h1>智能分析</h1>
      <p>AI驱动的运维故障排查与优化建议</p>
    </div>

    <el-tabs v-model="activeTab" class="analyze-tabs">
      <el-tab-pane label="故障排查" name="troubleshoot">
        <el-card>
          <el-form label-width="120px">
            <el-form-item label="问题描述">
              <el-input v-model="troubleshootForm.description" type="textarea" :rows="3" placeholder="请详细描述遇到的问题..." />
            </el-form-item>
            <el-form-item label="监控指标（可选）">
              <el-input v-model="troubleshootForm.metrics" type="textarea" :rows="2" placeholder="如: CPU 95%, 内存 80%, 磁盘 90%..." />
            </el-form-item>
            <el-form-item label="日志片段（可选）">
              <el-input v-model="troubleshootForm.logs" type="textarea" :rows="3" placeholder="粘贴相关日志..." />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doTroubleshoot" :loading="troubleshootLoading">开始排查</el-button>
              <el-button @click="troubleshootForm = {description:'',metrics:'',logs:''}">重置</el-button>
            </el-form-item>
          </el-form>
          <div v-if="troubleshootResult" class="result-box">
            <h4>排查结果</h4>
            <div v-html="renderResult(troubleshootResult)"></div>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="优化建议" name="suggest">
        <el-card>
          <el-form label-width="120px">
            <el-form-item label="系统类型">
              <el-select v-model="suggestForm.systemType" placeholder="选择系统类型" style="width:100%">
                <el-option label="Web应用" value="web" />
                <el-option label="数据库" value="database" />
                <el-option label="缓存系统" value="cache" />
                <el-option label="消息队列" value="mq" />
                <el-option label="容器平台" value="container" />
              </el-select>
            </el-form-item>
            <el-form-item label="当前状态">
              <el-input v-model="suggestForm.status" type="textarea" :rows="3" placeholder="描述当前系统状态和性能指标..." />
            </el-form-item>
            <el-form-item label="关注领域">
              <el-checkbox-group v-model="suggestForm.focusAreas">
                <el-checkbox label="performance">性能</el-checkbox>
                <el-checkbox label="security">安全</el-checkbox>
                <el-checkbox label="cost">成本</el-checkbox>
                <el-checkbox label="stability">稳定性</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doSuggest" :loading="suggestLoading">获取建议</el-button>
            </el-form-item>
          </el-form>
          <div v-if="suggestResult" class="result-box">
            <h4>优化建议</h4>
            <div v-html="renderResult(suggestResult)"></div>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="报告解读" name="report">
        <el-card>
          <el-form label-width="120px">
            <el-form-item label="报告类型">
              <el-select v-model="reportForm.type" placeholder="选择报告类型" style="width:100%">
                <el-option label="性能报告" value="performance" />
                <el-option label="安全报告" value="security" />
                <el-option label="运维报告" value="ops" />
                <el-option label="容量报告" value="capacity" />
              </el-select>
            </el-form-item>
            <el-form-item label="报告内容">
              <el-input v-model="reportForm.content" type="textarea" :rows="6" placeholder="粘贴报告内容或关键指标..." />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doInterpret" :loading="reportLoading">解读报告</el-button>
            </el-form-item>
          </el-form>
          <div v-if="reportResult" class="result-box">
            <h4>解读结果</h4>
            <div v-html="renderResult(reportResult)"></div>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="日志分析" name="logs">
        <el-card>
          <el-form label-width="120px">
            <el-form-item label="日志级别">
              <el-select v-model="logForm.level" placeholder="选择日志级别" style="width:100%">
                <el-option label="全部" value="" />
                <el-option label="ERROR" value="error" />
                <el-option label="WARNING" value="warning" />
                <el-option label="INFO" value="info" />
              </el-select>
            </el-form-item>
            <el-form-item label="时间范围">
              <el-input v-model="logForm.timeRange" placeholder="如: 最近1小时, 2024-05-15 10:00-12:00" style="width:100%" />
            </el-form-item>
            <el-form-item label="日志内容">
              <el-input v-model="logForm.content" type="textarea" :rows="6" placeholder="粘贴日志内容..." />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doAnalyzeLog" :loading="logLoading">分析日志</el-button>
            </el-form-item>
          </el-form>
          <div v-if="logResult" class="result-box">
            <h4>分析结果</h4>
            <div v-html="renderResult(logResult)"></div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { ai } from '@/api'

const activeTab = ref('troubleshoot')

const troubleshootForm = reactive({ description: '', metrics: '', logs: '' })
const troubleshootLoading = ref(false)
const troubleshootResult = ref('')

const suggestForm = reactive({ systemType: '', status: '', focusAreas: [] })
const suggestLoading = ref(false)
const suggestResult = ref('')

const reportForm = reactive({ type: 'performance', content: '' })
const reportLoading = ref(false)
const reportResult = ref('')

const logForm = reactive({ level: '', timeRange: '', content: '' })
const logLoading = ref(false)
const logResult = ref('')

const renderResult = (text) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
}

const doTroubleshoot = async () => {
  if (!troubleshootForm.description) { ElMessage.warning('请输入问题描述'); return }
  troubleshootLoading.value = true
  troubleshootResult.value = ''
  try {
    const res = await ai.troubleshoot({
      description: troubleshootForm.description,
      metrics: troubleshootForm.metrics,
      logs: troubleshootForm.logs
    })
    troubleshootResult.value = typeof res === 'string' ? res : (res.result || res.response || JSON.stringify(res))
  } catch (e) {
    troubleshootResult.value = '排查服务暂不可用，请稍后重试。'
  } finally {
    troubleshootLoading.value = false
  }
}

const doSuggest = async () => {
  if (!suggestForm.systemType || !suggestForm.status) { ElMessage.warning('请填写完整信息'); return }
  suggestLoading.value = true
  suggestResult.value = ''
  try {
    const res = await ai.suggest({
      system_type: suggestForm.systemType,
      status: suggestForm.status,
      focus_areas: suggestForm.focusAreas.join(',')
    })
    suggestResult.value = typeof res === 'string' ? res : (res.result || res.response || JSON.stringify(res))
  } catch (e) {
    suggestResult.value = '建议服务暂不可用，请稍后重试。'
  } finally {
    suggestLoading.value = false
  }
}

const doInterpret = async () => {
  if (!reportForm.content) { ElMessage.warning('请输入报告内容'); return }
  reportLoading.value = true
  reportResult.value = ''
  try {
    const res = await ai.interpretReport({
      report_type: reportForm.type,
      content: reportForm.content
    })
    reportResult.value = typeof res === 'string' ? res : (res.result || res.response || JSON.stringify(res))
  } catch (e) {
    reportResult.value = '解读服务暂不可用，请稍后重试。'
  } finally {
    reportLoading.value = false
  }
}

const doAnalyzeLog = async () => {
  if (!logForm.content) { ElMessage.warning('请输入日志内容'); return }
  logLoading.value = true
  logResult.value = ''
  try {
    const res = await ai.analyzeLogs({
      level: logForm.level,
      time_range: logForm.timeRange,
      content: logForm.content
    })
    logResult.value = typeof res === 'string' ? res : (res.result || res.response || JSON.stringify(res))
  } catch (e) {
    logResult.value = '日志分析服务暂不可用，请稍后重试。'
  } finally {
    logLoading.value = false
  }
}
</script>

<style scoped>
.ai-analyze-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-header h1 { margin: 0 0 8px 0; font-size: 24px; font-weight: 600; }
.page-header p { margin: 0; color: #909399; }
.analyze-tabs { background: #fff; padding: 0; }
.result-box { margin-top: 20px; padding: 16px; background: #f5f7fa; border-radius: 8px; line-height: 1.8; }
.result-box h4 { margin: 0 0 12px 0; color: #409eff; }
</style>
