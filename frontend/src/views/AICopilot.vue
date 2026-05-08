<template>
  <div class="ai-copilot-page">
    <div class="copilot-container">
      <!-- 左侧边栏 -->
      <aside
        class="sidebar"
        :class="{ collapsed: sidebarCollapsed }"
      >
        <div class="sidebar-header">
          <div
            v-if="!sidebarCollapsed"
            class="logo"
          >
            <el-icon :size="24">
              <MagicStick />
            </el-icon>
            <span>AI 助手</span>
          </div>
          <el-button
            text
            @click="sidebarCollapsed = !sidebarCollapsed"
          >
            <el-icon><component :is="sidebarCollapsed ? 'Expand' : 'Fold'" /></el-icon>
          </el-button>
        </div>

        <div
          v-if="!sidebarCollapsed"
          class="sidebar-content"
        >
          <el-button
            type="primary"
            class="new-chat-btn"
            @click="startNewChat"
          >
            <el-icon><Plus /></el-icon>
            新建对话
          </el-button>

          <div class="chat-history">
            <div class="history-label">
              历史对话
            </div>
            <div class="history-list">
              <div 
                v-for="chat in chatHistory" 
                :key="chat.id"
                class="history-item"
                :class="{ active: currentChatId === chat.id }"
                @click="loadChat(chat)"
              >
                <el-icon><ChatLineSquare /></el-icon>
                <span class="history-title">{{ chat.title }}</span>
                <el-dropdown
                  trigger="click"
                  @command="(cmd) => handleHistoryCommand(cmd, chat)"
                  @click.stop
                >
                  <el-button
                    text
                    size="small"
                    class="history-menu"
                  >
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="rename">
                        重命名
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
            </div>
          </div>
        </div>

        <div
          v-if="!sidebarCollapsed"
          class="sidebar-footer"
        >
          <div class="model-status">
            <div
              class="model-indicator"
              :class="modelStatus"
            />
            <div class="model-info">
              <div class="model-name">
                {{ currentModel }}
              </div>
              <div class="model-status-text">
                {{ modelStatusText }}
              </div>
            </div>
            <el-button
              text
              size="small"
              @click="showModelSelector = true"
            >
              <el-icon><Setting /></el-icon>
            </el-button>
          </div>
        </div>
      </aside>

      <!-- 主聊天区域 -->
      <main class="chat-main">
        <!-- 聊天头部 -->
        <header class="chat-header">
          <div class="header-info">
            <h2 class="chat-title">
              {{ currentChatTitle }}
            </h2>
            <div class="chat-meta">
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ formatDate(currentChat.createdAt) }}
              </span>
              <span class="meta-item">
                <el-icon><ChatDotRound /></el-icon>
                {{ messages.length }} 条消息
              </span>
            </div>
          </div>
          <div class="header-actions">
            <el-tooltip content="导出对话">
              <el-button
                text
                @click="exportChat"
              >
                <el-icon><Download /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="清空对话">
              <el-button
                text
                @click="clearHistory"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>
            <el-button
              text
              @click="showSettingsDrawer = true"
            >
              <el-icon><Setting /></el-icon>
            </el-button>
          </div>
        </header>

        <!-- 消息区域 -->
        <div
          ref="messagesContainer"
          class="chat-messages"
        >
          <!-- 空状态：使用新的EmptyState组件 -->
          <div
            v-if="messages.length === 0"
            class="empty-state"
          >
            <EmptyState
              type="search"
              :title="welcomeTitle"
              :description="welcomeDesc"
              size="lg"
              :animate="true"
              :action-text="'开始对话'"
              :action-icon="'ChatDotRound'"
              @action="handleStartChat"
            >
              <template #extra>
                <div class="quick-prompts-grid">
                  <div 
                    v-for="prompt in quickPrompts" 
                    :key="prompt.title"
                    class="prompt-card"
                    @click="usePrompt(prompt)"
                  >
                    <div
                      class="prompt-icon"
                      :style="{ background: prompt.bgColor }"
                    >
                      <el-icon><component :is="prompt.icon" /></el-icon>
                    </div>
                    <div class="prompt-text">
                      {{ prompt.title }}
                    </div>
                  </div>
                </div>
              </template>
              <template #actions>
                <div class="empty-actions-row">
                  <el-button 
                    v-for="action in quickActions" 
                    :key="action.title"
                    size="small"
                    @click="usePrompt(action)"
                  >
                    <el-icon><component :is="action.icon" /></el-icon>
                    {{ action.title }}
                  </el-button>
                </div>
              </template>
            </EmptyState>
          </div>

          <!-- 消息列表 -->
          <div
            v-else
            class="messages-list"
          >
            <div 
              v-for="(msg, index) in messages" 
              :key="index"
              class="message-wrapper"
              :class="msg.role"
            >
              <div class="message-avatar">
                <div
                  class="avatar-circle"
                  :class="msg.role"
                >
                  <el-icon
                    v-if="msg.role === 'user'"
                    :size="20"
                  >
                    <User />
                  </el-icon>
                  <el-icon
                    v-else
                    :size="20"
                  >
                    <MagicStick />
                  </el-icon>
                </div>
              </div>

              <div class="message-bubble">
                <div
                  class="message-content"
                  v-html="formatMessage(msg.content)"
                />
                <div class="message-footer">
                  <div class="message-time">
                    {{ msg.time }}
                  </div>
                  <div
                    v-if="msg.role === 'assistant'"
                    class="message-actions"
                  >
                    <el-tooltip content="复制">
                      <el-button
                        text
                        size="small"
                        @click="copyMessage(msg.content)"
                      >
                        <el-icon><CopyDocument /></el-icon>
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="重新生成">
                      <el-button
                        text
                        size="small"
                        @click="regenerateMessage(index)"
                      >
                        <el-icon><RefreshLeft /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </div>
                </div>
              </div>
            </div>

            <!-- 正在输入指示器 -->
            <div
              v-if="isTyping"
              class="message-wrapper assistant"
            >
              <div class="message-avatar">
                <div class="avatar-circle assistant">
                  <el-icon :size="20">
                    <MagicStick />
                  </el-icon>
                </div>
              </div>
              <div class="message-bubble typing">
                <div class="typing-indicator">
                  <span class="dot" />
                  <span class="dot" />
                  <span class="dot" />
                </div>
                <span class="typing-text">AI 正在思考...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 快捷操作栏 -->
        <div
          v-if="messages.length > 0"
          class="quick-actions-bar"
        >
          <div class="quick-actions-scroll">
            <div 
              v-for="action in quickActions" 
              :key="action.title"
              class="quick-action-chip"
              @click="usePrompt(action)"
            >
              <el-icon><component :is="action.icon" /></el-icon>
              {{ action.title }}
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <footer class="chat-footer">
          <div class="input-container">
            <div
              class="input-wrapper"
              :class="{ focused: inputFocused }"
            >
              <el-input
                v-model="inputMessage"
                type="textarea"
                :rows="1"
                :autosize="{ minRows: 1, maxRows: 4 }"
                placeholder="输入您的问题，AI 助手将为您解答..."
                :disabled="isTyping"
                class="message-input"
                @keydown.enter.exact.prevent="sendMessage"
                @focus="inputFocused = true"
                @blur="inputFocused = false"
              />
              <div class="input-actions">
                <div class="attachment-btn">
                  <el-tooltip content="上传附件">
                    <el-button
                      text
                      size="small"
                      :disabled="isTyping"
                    >
                      <el-icon><Paperclip /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
                <div class="send-btn">
                  <el-button 
                    type="primary" 
                    :disabled="!inputMessage.trim() || isTyping"
                    @click="sendMessage"
                  >
                    <el-icon><Promotion /></el-icon>
                    发送
                  </el-button>
                </div>
              </div>
            </div>
            <div class="input-hint">
              按 Enter 发送，Shift + Enter 换行
            </div>
          </div>
        </footer>
      </main>

      <!-- 右侧功能面板 -->
      <aside
        v-if="!featuresCollapsed"
        class="features-panel"
      >
        <div class="panel-header">
          <h3>功能说明</h3>
          <el-button
            text
            @click="featuresCollapsed = true"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>

        <div class="panel-content">
          <div 
            v-for="cap in capabilities" 
            :key="cap.title"
            class="capability-card"
          >
            <div
              class="cap-icon"
              :style="{ background: cap.bgColor }"
            >
              <el-icon><component :is="cap.icon" /></el-icon>
            </div>
            <div class="cap-info">
              <div class="cap-title">
                {{ cap.title }}
              </div>
              <div class="cap-desc">
                {{ cap.description }}
              </div>
            </div>
          </div>
        </div>

        <div class="context-section">
          <div class="section-title">
            <el-icon><Connection /></el-icon>
            当前上下文
          </div>
          <div class="context-tags">
            <el-tag
              v-if="currentContext.server"
              size="small"
              closable
              @close="removeContext('server')"
            >
              服务器: {{ currentContext.server }}
            </el-tag>
            <el-tag
              v-if="currentContext.service"
              size="small"
              closable
              @close="removeContext('service')"
            >
              服务: {{ currentContext.service }}
            </el-tag>
            <el-tag
              v-if="!currentContext.server && !currentContext.service"
              type="info"
              size="small"
            >
              无上下文
            </el-tag>
          </div>
        </div>

        <div class="stats-section">
          <div class="section-title">
            <el-icon><DataAnalysis /></el-icon>
            使用统计
          </div>
          <div class="stats-list">
            <div class="stat-item">
              <span class="stat-label">今日对话</span>
              <span class="stat-value">{{ todayStats.conversations }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">消息总数</span>
              <span class="stat-value">{{ todayStats.messages }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Token 消耗</span>
              <span class="stat-value">{{ todayStats.tokens }}</span>
            </div>
          </div>
        </div>
      </aside>

      <button
        v-if="featuresCollapsed"
        class="features-toggle"
        @click="featuresCollapsed = false"
      >
        <el-icon><ArrowLeft /></el-icon>
      </button>
    </div>

    <!-- 模型选择器对话框 -->
    <el-dialog
      v-model="showModelSelector"
      title="选择 AI 模型"
      width="500px"
    >
      <div class="model-selector">
        <div class="model-list">
          <div 
            v-for="model in availableModels" 
            :key="model.id"
            class="model-item"
            :class="{ active: currentModel === model.id }"
            @click="selectModel(model)"
          >
            <div class="model-icon">
              <el-icon><component :is="model.icon" /></el-icon>
            </div>
            <div class="model-details">
              <div class="model-name">
                {{ model.name }}
              </div>
              <div class="model-desc">
                {{ model.description }}
              </div>
            </div>
            <div
              v-if="model.recommended"
              class="model-badge"
            >
              <el-tag
                size="small"
                type="success"
              >
                推荐
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 设置抽屉 -->
    <el-drawer
      v-model="showSettingsDrawer"
      title="对话设置"
      size="400px"
    >
      <div class="settings-content">
        <el-form label-position="top">
          <el-form-item label="Temperature（创造性）">
            <el-slider
              v-model="settings.temperature"
              :min="0"
              :max="2"
              :step="0.1"
              :marks="tempMarks"
            />
          </el-form-item>
          <el-form-item label="Max Tokens（最大回复长度）">
            <el-input-number
              v-model="settings.maxTokens"
              :min="100"
              :max="4000"
              :step="100"
            />
          </el-form-item>
          <el-form-item label="上下文轮次">
            <el-input-number
              v-model="settings.contextTurns"
              :min="1"
              :max="20"
            />
          </el-form-item>
          <el-form-item label="启用上下文记忆">
            <el-switch v-model="settings.enableMemory" />
          </el-form-item>
        </el-form>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  MagicStick, Plus, ChatLineSquare, MoreFilled, User, Clock, ChatDotRound,
  Download, Delete, Setting, CopyDocument, RefreshLeft, Fold, Expand, Close,
  Promotion, Paperclip, Connection, DataAnalysis, ArrowLeft, VideoPlay, Document,
  DataLine, Warning, Odometer, Search, Operation, Star, Histogram, Bell
} from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()

const sidebarCollapsed = ref(false)
const featuresCollapsed = ref(true)
const showModelSelector = ref(false)
const showSettingsDrawer = ref(false)

const inputMessage = ref('')
const inputFocused = ref(false)
const messages = ref([])
const isTyping = ref(false)
const messagesContainer = ref(null)

const currentChatId = ref(1)
const currentChatTitle = ref('新对话')
const currentChat = reactive({ createdAt: new Date() })

const modelStatus = ref('online')
const modelStatusText = ref('在线')
const currentModel = ref('Qwen3.5-8B')

const settings = reactive({
  temperature: 0.7,
  maxTokens: 2000,
  contextTurns: 10,
  enableMemory: true
})

const tempMarks = {
  0: '精确',
  0.5: '平衡',
  1: '创意',
  1.5: '随机',
  2: '狂野'
}

const chatHistory = ref([
  { id: 1, title: '服务器故障排查', createdAt: '2026-05-04' },
  { id: 2, title: 'Nginx 配置优化', createdAt: '2026-05-03' },
  { id: 3, title: '数据库性能分析', createdAt: '2026-05-02' }
])

const availableModels = [
  { id: 'Qwen3.5-8B', name: 'Qwen 3.5 8B', description: '平衡性能与速度', icon: 'Star', recommended: true },
  { id: 'Qwen3.5-14B', name: 'Qwen 3.5 14B', description: '更高精度，资源占用中等', icon: 'Star', recommended: false },
  { id: 'Qwen3.5-32B', name: 'Qwen 3.5 32B', description: '高精度，适合复杂任务', icon: 'Histogram', recommended: false }
]

const quickActions = [
  { title: '故障诊断', icon: 'Search', prompt: '帮我分析最近的服务器故障', bgColor: '#f56c6c' },
  { title: '日志分析', icon: 'Document', prompt: '分析昨天的错误日志', bgColor: '#409eff' },
  { title: '生成报告', icon: 'DataLine', prompt: '生成本周运维报告摘要', bgColor: '#67c23a' },
  { title: '性能优化', icon: 'Odometer', prompt: '给出服务器性能优化建议', bgColor: '#e6a23c' }
]

const quickPrompts = [
  { title: '服务器故障排查', icon: 'Warning', bgColor: 'linear-gradient(135deg, #f56c6c, #ff7875)' },
  { title: '日志分析解读', icon: 'Document', bgColor: 'linear-gradient(135deg, #409eff, #53a8ff)' },
  { title: '脚本代码生成', icon: 'Operation', bgColor: 'linear-gradient(135deg, #67c23a, #85ce61)' },
  { title: '性能优化建议', icon: 'Odometer', bgColor: 'linear-gradient(135deg, #e6a23c, #ebb563)' }
]

const capabilities = [
  { title: '智能问答', icon: 'ChatDotRound', description: '回答运维相关问题，提供解决方案建议', bgColor: '#409eff' },
  { title: '故障诊断', icon: 'Warning', description: '分析告警原因，提供故障排查指导', bgColor: '#f56c6c' },
  { title: '脚本生成', icon: 'Operation', description: '根据需求生成自动化运维脚本', bgColor: '#67c23a' },
  { title: '日志分析', icon: 'Document', description: '解析日志内容，提取关键错误信息', bgColor: '#e6a23c' }
]

const currentContext = reactive({
  server: '',
  service: ''
})

const todayStats = reactive({
  conversations: 5,
  messages: 23,
  tokens: '12.5K'
})

const welcomeTitle = '你好，我是 AI 运维助手'
const welcomeDesc = '我可以帮你进行故障诊断、日志分析、脚本生成、性能优化等工作'

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const formatMessage = (content) => {
  if (!content) return ''
  let html = content
    .replace(/```(\w+)?\n?([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre class="code-block"><code class="language-${lang || 'plain'}">${escapeHtml(code.trim())}</code></pre>`
    })
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/\n/g, '<br>')
  return html
}

const escapeHtml = (str) => {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

const handleStartChat = () => {
  inputMessage.value = '你好，请帮我...'
}

const startNewChat = () => {
  messages.value = []
  currentChatTitle.value = '新对话'
  currentChat.createdAt = new Date()
  ElMessage.success('已创建新对话')
}

const loadChat = (chat) => {
  currentChatId.value = chat.id
  currentChatTitle.value = chat.title
  ElMessage.info('加载对话: ' + chat.title)
}

const handleHistoryCommand = (command, chat) => {
  if (command === 'rename') {
    ElMessageBox.prompt('请输入新的对话标题', '重命名', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: chat.title
    }).then(({ value }) => {
      chat.title = value
      ElMessage.success('已重命名')
    })
  } else if (command === 'delete') {
    ElMessageBox.confirm('确定要删除这个对话吗?', '删除对话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      const index = chatHistory.value.findIndex(c => c.id === chat.id)
      if (index > -1) {
        chatHistory.value.splice(index, 1)
      }
      ElMessage.success('已删除')
    })
  }
}

const sendMessage = () => {
  if (!inputMessage.value.trim() || isTyping.value) return
  
  const userMsg = {
    role: 'user',
    content: inputMessage.value,
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  messages.value.push(userMsg)
  const query = inputMessage.value
  inputMessage.value = ''
  isTyping.value = true
  scrollToBottom()
  
  setTimeout(() => {
    isTyping.value = false
    messages.value.push({
      role: 'assistant',
      content: `这是对"${query}"的模拟回复。实际使用时，AI会根据您的本地模型（Qwen3.5）进行智能回复，支持故障诊断、日志分析、脚本生成等多种能力。`,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    })
    scrollToBottom()
  }, 1500)
}

const copyMessage = (content) => {
  navigator.clipboard.writeText(content)
  ElMessage.success('已复制到剪贴板')
}

const regenerateMessage = (index) => {
  ElMessage.info('重新生成回复中...')
  messages.value.splice(index, 1)
}

const exportChat = () => {
  const content = messages.value.map(m => `${m.role === 'user' ? '用户' : 'AI'}: ${m.content}`).join('\n\n')
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `对话记录_${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('对话已导出')
}

const clearHistory = () => {
  ElMessageBox.confirm('确定要清空当前对话吗?', '清空对话', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    messages.value = []
    ElMessage.success('对话已清空')
  })
}

const selectModel = (model) => {
  currentModel.value = model.id
  showModelSelector.value = false
  ElMessage.success(`已切换到 ${model.name}`)
}

const removeContext = (type) => {
  if (type === 'server') currentContext.server = ''
  if (type === 'service') currentContext.service = ''
}

const usePrompt = (prompt) => {
  inputMessage.value = prompt.prompt
  sendMessage()
}

onMounted(() => {
  // 初始化
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.ai-copilot-page {
  height: 100%;
  background: $bg-page;
}

.copilot-container {
  display: flex;
  height: 100%;
  overflow: hidden;
}

// 侧边栏
.sidebar {
  width: 260px;
  background: $bg-container;
  border-right: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  transition: all 0.3s;

  &.collapsed {
    width: 60px;
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-lg;
  border-bottom: 1px solid $border-light;

  .logo {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-weight: $font-weight-semibold;
    font-size: $font-size-md;
    color: $primary;
  }
}

.sidebar-content {
  flex: 1;
  padding: $spacing-md;
  overflow-y: auto;
}

.new-chat-btn {
  width: 100%;
  margin-bottom: $spacing-lg;
}

.chat-history {
  .history-label {
    font-size: $font-size-xs;
    color: $text-placeholder;
    text-transform: uppercase;
    padding: $spacing-sm 0;
    letter-spacing: 0.5px;
  }

  .history-list {
    .history-item {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      padding: $spacing-sm $spacing-md;
      border-radius: $radius-md;
      cursor: pointer;
      transition: all 0.15s;
      margin-bottom: 2px;

      &:hover {
        background: $bg-page;
      }

      &.active {
        background: $primary-lighter;
        color: $primary;
      }

      .el-icon {
        flex-shrink: 0;
        color: $text-secondary;
      }

      .history-title {
        flex: 1;
        font-size: $font-size-sm;
        @include text-ellipsis;
      }

      .history-menu {
        opacity: 0;
        transition: opacity 0.15s;
      }

      &:hover .history-menu {
        opacity: 1;
      }
    }
  }
}

.sidebar-footer {
  padding: $spacing-md;
  border-top: 1px solid $border-light;
}

.model-status {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background: $bg-page;
  border-radius: $radius-md;

  .model-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    
    &.online { background: $success; }
    &.offline { background: $danger; }
    &.loading { background: $warning; animation: pulse 1s infinite; }
  }

  .model-info {
    flex: 1;
    .model-name { font-size: $font-size-sm; font-weight: $font-weight-medium; }
    .model-status-text { font-size: $font-size-xs; color: $text-secondary; }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

// 主聊天区域
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-lg $spacing-xl;
  background: $bg-container;
  border-bottom: 1px solid $border-light;

  .header-info {
    .chat-title {
      font-size: $font-size-lg;
      font-weight: $font-weight-semibold;
      margin: 0 0 $space-2 0;
    }

    .chat-meta {
      display: flex;
      gap: $spacing-md;
      font-size: $font-size-sm;
      color: $text-secondary;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }

  .header-actions {
    display: flex;
    gap: $spacing-xs;
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-xl;
  background: $bg-page;
}

// 空状态
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
}

.quick-prompts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;
  margin-top: $spacing-xl;
  max-width: 500px;
}

.prompt-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  background: $bg-container;
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-base;
    border-color: $primary-lighter;
  }

  .prompt-icon {
    width: 40px;
    height: 40px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    flex-shrink: 0;
  }

  .prompt-text {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
  }
}

.empty-actions-row {
  display: flex;
  gap: $spacing-sm;
  margin-top: $spacing-lg;
  flex-wrap: wrap;
  justify-content: center;
}

// 消息列表
.messages-list {
  max-width: 800px;
  margin: 0 auto;
}

.message-wrapper {
  display: flex;
  gap: $spacing-md;
  margin-bottom: $spacing-xl;
  animation: fadeInUp 0.3s ease-out;

  &.user {
    flex-direction: row-reverse;

    .message-bubble {
      background: $primary;
      color: #fff;
      border-radius: $radius-lg $radius-lg $radius-sm $radius-lg;

      .message-footer {
        .message-time { color: rgba(255,255,255,0.7); }
      }
    }

    .avatar-circle {
      background: linear-gradient(135deg, $primary, $primary-light);
    }
  }

  &.assistant {
    .message-bubble {
      background: $bg-container;
      border-radius: $radius-lg $radius-lg $radius-lg $radius-sm;
      box-shadow: $shadow-sm;
    }

    .avatar-circle {
      background: linear-gradient(135deg, #667eea, #764ba2);
    }
  }
}

.message-avatar {
  flex-shrink: 0;

  .avatar-circle {
    width: 40px;
    height: 40px;
    border-radius: $radius-round;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
  }
}

.message-bubble {
  flex: 1;
  max-width: 70%;
  padding: $spacing-md $spacing-lg;

  .message-content {
    font-size: $font-size-base;
    line-height: 1.7;

    :deep(.code-block) {
      background: #1e1e1e;
      color: #d4d4d4;
      padding: $spacing-md;
      border-radius: $radius-md;
      margin: $spacing-md 0;
      overflow-x: auto;
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: $font-size-sm;
    }

    :deep(.inline-code) {
      background: rgba(0,0,0,0.08);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 0.9em;
    }

    :deep(strong) { font-weight: $font-weight-semibold; }
    :deep(em) { font-style: italic; }
    :deep(ul), :deep(ol) { padding-left: $spacing-lg; margin: $spacing-sm 0; }
    :deep(li) { margin: $space-1 0; }
    :deep(h2), :deep(h3), :deep(h4) { margin: $spacing-md 0 $space-2 0; }
  }

  .message-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: $spacing-sm;
    opacity: 0;
    transition: opacity 0.2s;

    .message-time {
      font-size: $font-size-xs;
      color: $text-placeholder;
    }

    .message-actions {
      display: flex;
      gap: $space-1;
    }
  }

  &:hover .message-footer {
    opacity: 1;
  }

  &.typing {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;

  .dot {
    width: 8px;
    height: 8px;
    background: $primary;
    border-radius: 50%;
    animation: typing-bounce 1.4s infinite;

    &:nth-child(1) { animation-delay: 0s; }
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes typing-bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.typing-text {
  font-size: $font-size-sm;
  color: $text-secondary;
}

// 快捷操作栏
.quick-actions-bar {
  padding: $spacing-sm $spacing-xl;
  background: $bg-container;
  border-top: 1px solid $border-light;
  overflow-x: auto;

  &::-webkit-scrollbar { height: 0; }

  .quick-actions-scroll {
    display: flex;
    gap: $spacing-sm;
  }

  .quick-action-chip {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding: 6px 14px;
    background: $bg-page;
    border: 1px solid $border-light;
    border-radius: $radius-pill;
    font-size: $font-size-sm;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s;

    &:hover {
      background: $primary-lighter;
      border-color: $primary;
      color: $primary;
    }
  }
}

// 输入区域
.chat-footer {
  padding: $spacing-md $spacing-xl;
  background: $bg-container;
  border-top: 1px solid $border-light;
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: $spacing-sm;
  background: $bg-page;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  padding: $spacing-sm;
  transition: all 0.2s;

  &.focused {
    border-color: $primary;
    box-shadow: 0 0 0 3px rgba($primary, 0.1);
  }

  .message-input {
    flex: 1;

    :deep(.el-textarea__inner) {
      border: none;
      background: transparent;
      resize: none;
      padding: 8px 0;
      font-size: $font-size-base;

      &::placeholder {
        color: $text-placeholder;
      }

      &:focus {
        box-shadow: none;
      }
    }
  }

  .input-actions {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    flex-shrink: 0;
  }
}

.input-hint {
  text-align: center;
  font-size: $font-size-xs;
  color: $text-placeholder;
  margin-top: $spacing-sm;
}

// 功能面板
.features-panel {
  width: 300px;
  background: $bg-container;
  border-left: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  padding: $spacing-lg;
  overflow-y: auto;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-lg;

  h3 {
    font-size: $font-size-md;
    font-weight: $font-weight-semibold;
    margin: 0;
  }
}

.panel-content {
  flex: 1;
}

.capability-card {
  display: flex;
  gap: $spacing-md;
  padding: $spacing-md;
  border-radius: $radius-md;
  margin-bottom: $spacing-sm;
  transition: all 0.15s;
  cursor: pointer;

  &:hover {
    background: $bg-page;
  }

  .cap-icon {
    width: 36px;
    height: 36px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    flex-shrink: 0;
  }

  .cap-info {
    .cap-title {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      margin-bottom: 2px;
    }
    .cap-desc {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }
}

.context-section,
.stats-section {
  margin-top: $spacing-xl;

  .section-title {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-regular;
    margin-bottom: $spacing-md;
  }
}

.context-tags {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.stats-list {
  .stat-item {
    display: flex;
    justify-content: space-between;
    padding: $spacing-sm 0;
    border-bottom: 1px solid $border-light;

    &:last-child { border-bottom: none; }

    .stat-label { color: $text-secondary; font-size: $font-size-sm; }
    .stat-value { font-weight: $font-weight-medium; }
  }
}

.features-toggle {
  position: fixed;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  background: $bg-container;
  border: 1px solid $border;
  border-radius: $radius-round;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 10;

  &:hover {
    background: $primary;
    color: #fff;
    border-color: $primary;
  }
}

// 模型选择器
.model-list {
  .model-item {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-lg;
    border-radius: $radius-md;
    cursor: pointer;
    transition: all 0.15s;
    border: 2px solid transparent;

    &:hover {
      background: $bg-page;
    }

    &.active {
      border-color: $primary;
      background: $primary-lighter;
    }

    .model-icon {
      width: 48px;
      height: 48px;
      background: $primary-lighter;
      border-radius: $radius-md;
      display: flex;
      align-items: center;
      justify-content: center;
      color: $primary;
      font-size: 20px;
    }

    .model-details {
      flex: 1;
      .model-name { font-weight: $font-weight-medium; margin-bottom: 2px; }
      .model-desc { font-size: $font-size-sm; color: $text-secondary; }
    }
  }
}

// 设置抽屉
.settings-content {
  :deep(.el-form-item) {
    margin-bottom: $spacing-xl;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>