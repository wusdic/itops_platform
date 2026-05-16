<template>
  <div class="ai-copilot">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>AI 智能问答</h3>
        <el-button type="primary" size="small" @click="newChat">新建对话</el-button>
      </div>
      <div class="conversation-list">
        <div v-for="conv in conversations" :key="conv.id" :class="['conversation-item', { active: conv.id === currentConvId }]" @click="selectConv(conv.id)">
          <span class="conv-title">{{ conv.title || '新对话' }}</span>
          <el-icon class="delete-btn" @click.stop="deleteConv(conv.id)"><Delete /></el-icon>
        </div>
        <div v-if="conversations.length === 0" class="empty-tip">暂无历史对话</div>
      </div>
    </div>

    <!-- 聊天区域 -->
    <div class="chat-area">
      <!-- 消息列表 -->
      <div class="messages" ref="messagesRef">
        <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
          <div class="message-avatar">
            <el-avatar :size="32" :icon="msg.role === 'user' ? 'UserFilled' : 'ChatDotRound'" />
          </div>
          <div class="message-content">
            <div class="message-header">
              <span>{{ msg.role === 'user' ? '我' : 'AI助手' }}</span>
              <span class="time">{{ formatTime(msg.timestamp) }}</span>
            </div>
            <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
        <div v-if="aiLoading" class="message ai">
          <div class="message-avatar">
            <el-avatar :size="32" icon="ChatDotRound" />
          </div>
          <div class="message-content">
            <div class="message-text typing">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <el-input v-model="inputText" type="textarea" :rows="2" placeholder="输入问题，AI将为你解答..." @keydown.enter.ctrl="sendMessage" />
        <div class="input-actions">
          <span class="char-count">{{ inputText.length }} 字</span>
          <el-button type="primary" @click="sendMessage" :loading="aiLoading" :disabled="!inputText.trim()">发送 (Ctrl+Enter)</el-button>
          <el-button @click="clearMessages">清空对话</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const inputText = ref('')
const messages = ref([])
const aiLoading = ref(false)
const messagesRef = ref(null)
const conversations = ref([])
const currentConvId = ref(null)

const token = () => localStorage.getItem('token')

const scrollBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const renderMarkdown = (text) => {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || aiLoading.value) return

  messages.value.push({ role: 'user', content: text, timestamp: Date.now() })
  inputText.value = ''
  aiLoading.value = true
  scrollBottom()

  try {
    // 使用流式API，发送 {message, conversation_id, stream: true}
    const res = await fetch('/api/v1/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token()}`
      },
      body: JSON.stringify({
        message: text,
        conversation_id: currentConvId.value || undefined,
        stream: true
      })
    })

    if (!res.ok) throw new Error('请求失败')

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    let assistantMsg = { role: 'assistant', content: '', timestamp: Date.now() }

    // 添加一个空的AI消息占位
    messages.value.push(assistantMsg)
    const msgIndex = messages.value.length - 1

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })

      // 解析SSE数据行: data: {"type":"content","content":"xxx"}\n\n
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'content' && data.content) {
              fullContent += data.content
              messages.value[msgIndex].content = fullContent
              scrollBottom()
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }

    // 更新最终消息
    messages.value[msgIndex].content = fullContent.trim() || 'AI服务暂未返回内容'
    // 更新会话ID
    if (res.headers.get('X-Conversation-Id')) {
      currentConvId.value = res.headers.get('X-Conversation-Id')
    }
  } catch (e) {
    ElMessage.error('AI响应失败: ' + e.message)
    messages.value.push({ role: 'assistant', content: '抱歉，AI服务暂时不可用。', timestamp: Date.now() })
  } finally {
    aiLoading.value = false
    scrollBottom()
  }
}

const clearMessages = () => {
  messages.value = []
}

const newChat = () => {
  currentConvId.value = null
  messages.value = []
}

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

const loadConversations = async () => {
  try {
    const res = await fetch('/api/v1/ai/conversations', {
      headers: { 'Authorization': `Bearer ${token()}` }
    })
    if (res.ok) {
      const data = await res.json()
      conversations.value = data.items || []
    }
  } catch (e) {
    console.warn('Load conversations failed:', e)
  }
}

const selectConv = async (id) => {
  currentConvId.value = id
  try {
    const res = await fetch(`/api/v1/ai/conversation/${id}`, {
      headers: { 'Authorization': `Bearer ${token()}` }
    })
    if (res.ok) {
      const data = await res.json()
      messages.value = (data.messages || []).map(m => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
        timestamp: new Date(m.created_at).getTime()
      }))
      scrollBottom()
    }
  } catch (e) {
    console.warn('Load conversation failed:', e)
  }
}

const deleteConv = async (id) => {
  try {
    await fetch(`/api/v1/ai/conversation/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token()}` }
    })
    conversations.value = conversations.value.filter(c => c.id !== id)
  } catch (e) {
    console.warn('Delete conversation failed:', e)
  }
}

onMounted(() => {
  messages.value = [
    { role: 'assistant', content: '你好！我是AI运维助手，有什么可以帮你解答的吗？', timestamp: Date.now() }
  ]
  loadConversations()
})
</script>

<style scoped>
.ai-copilot { display: flex; height: calc(100vh - 60px); background: #f5f7fa; }
.sidebar { width: 260px; background: #fff; border-right: 1px solid #e4e7ed; display: flex; flex-direction: column; }
.sidebar-header { padding: 16px; border-bottom: 1px solid #e4e7ed; display: flex; justify-content: space-between; align-items: center; }
.sidebar-header h3 { margin: 0; font-size: 16px; }
.conversation-list { flex: 1; overflow-y: auto; padding: 8px; }
.conversation-item { padding: 10px 12px; border-radius: 6px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.conversation-item:hover, .conversation-item.active { background: #f0f2f5; }
.conv-title { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.delete-btn { opacity: 0; font-size: 14px; }
.conversation-item:hover .delete-btn { opacity: 1; }
.empty-tip { text-align: center; color: #999; padding: 20px; font-size: 13px; }
.chat-area { flex: 1; display: flex; flex-direction: column; }
.messages { flex: 1; overflow-y: auto; padding: 20px; }
.message { display: flex; gap: 12px; margin-bottom: 20px; }
.message.user { flex-direction: row-reverse; }
.message-text { background: #fff; padding: 12px 16px; border-radius: 12px; max-width: 70%; line-height: 1.6; box-shadow: 0 1px 4px rgba(0,0,0,0.08); font-size: 14px; }
.message.user .message-text { background: #409eff; color: #fff; }
.message-text pre { background: #f6f8fa; padding: 8px; border-radius: 4px; overflow-x: auto; margin: 8px 0; }
.message-text code { background: #f6f8fa; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.message.user .message-text code { background: rgba(255,255,255,0.2); }
.typing { display: flex; gap: 4px; padding: 12px 16px; }
.typing .dot { width: 8px; height: 8px; background: #909399; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out; }
.typing .dot:nth-child(1) { animation-delay: -0.32s; }
.typing .dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
.message-header { font-size: 12px; color: #909399; margin-bottom: 4px; display: flex; gap: 8px; }
.message.user .message-header { flex-direction: row-reverse; }
.time { font-size: 11px; }
.input-area { padding: 16px 20px; background: #fff; border-top: 1px solid #e4e7ed; }
.input-actions { display: flex; justify-content: flex-end; gap: 8px; align-items: center; margin-top: 8px; }
.char-count { font-size: 12px; color: #999; margin-right: auto; }
</style>
