<template>
  <div class="chat-page">
    <n-layout has-sider class="chat-layout" :collapsed="sidebarCollapsed" collapsible @update:collapsed="sidebarCollapsed = $event">
      <!-- 左侧会话列表 -->
      <n-layout-sider
        bordered
        :width="280"
        :collapsed-width="0"
        :native-scrollbar="false"
        class="conversation-sider"
        :collapsed="sidebarCollapsed"
      >
        <div class="sider-header">
          <n-button type="primary" block @click="createConversation">
            <template #icon><n-icon><CreateOutline /></n-icon></template>
            新建会话
          </n-button>
          <n-input
            v-model:value="searchText"
            placeholder="搜索会话..."
            size="small"
            style="margin-top: 8px"
            clearable
          >
            <template #prefix><n-icon><SearchOutline /></n-icon></template>
          </n-input>
        </div>
        <n-list class="conversation-list" hoverable clickable>
          <n-spin size="small" v-if="conversationsLoading" style="padding: 20px; display: block; text-align: center" />
          <template v-else>
          <n-list-item
            v-for="conv in filteredConversations"
            :key="conv.conversation_id"
            class="conversation-item"
            :class="{ active: currentConversation?.conversation_id === conv.conversation_id }"
            @click="selectConversation(conv)"
          >
            <template #prefix>
              <n-icon :component="StarOutline" v-if="conv.is_pinned" color="#f0a020" />
              <n-icon :component="ChatbubbleOutline" v-else color="#999" />
            </template>
            <div class="conv-info">
              <div class="conv-title">{{ conv.title || '新对话' }}</div>
              <div class="conv-time">{{ formatDate(conv.last_message_at || conv.created_at) }}</div>
            </div>
            <template #suffix>
              <n-space>
                <n-tooltip :content="conv.is_pinned ? '取消置顶' : '置顶'" placement="top">
                  <n-button text size="tiny" @click.stop="handlePin(conv)">
                    <n-icon><StarOutline /></n-icon>
                  </n-button>
                </n-tooltip>
                <n-popconfirm @positive-click="handleDelete(conv.conversation_id)">
                  <template #trigger>
                    <n-button text size="tiny" @click.stop>
                      <n-icon color="#d03050"><TrashOutline /></n-icon>
                    </n-button>
                  </template>
                  确定删除此会话？
                </n-popconfirm>
              </n-space>
            </template>
          </n-list-item>
          </template>
        </n-list>
      </n-layout-sider>

      <!-- 右侧聊天界面 -->
      <n-layout-content class="chat-content" :native-scrollbar="false" ref="chatContentRef">
        <div class="chat-main" v-if="currentConversation">
          <div class="chat-header">
            <n-button text @click="sidebarCollapsed = !sidebarCollapsed" class="collapse-btn">
              <n-icon size="20"><MenuOutline /></n-icon>
            </n-button>
            <h3>{{ currentConversation.title || '智能问答' }}</h3>
          </div>

          <!-- 消息列表 -->
          <div class="messages" ref="messagesRef">
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="message"
              :class="msg.role === 'user' ? 'message-user' : 'message-ai'"
            >
              <n-avatar
                v-if="msg.role === 'ai'"
                round
                size="small"
                :style="{ background: '#18a058' }"
              >AI</n-avatar>
              <div class="bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-ai'">
                <div class="bubble-text" :class="{ 'bubble-text-ai': msg.role === 'ai' }" v-html="msg.role === 'ai' ? renderMarkdown(msg.content) : msg.content"></div>
                <div class="bubble-footer">
                  <span class="bubble-time">{{ formatTime(msg.created_at) }}</span>
                  <n-tooltip trigger="hover">
                    <template #trigger>
                      <n-button text size="tiny" @click.stop="copyMessage(msg.content)" class="copy-btn">
                        <n-icon size="12"><CopyOutline /></n-icon>
                      </n-button>
                    </template>
                    复制
                  </n-tooltip>
                  <n-tooltip trigger="hover">
                    <template #trigger>
                      <n-button text size="tiny" @click.stop="resendMessage(msg)" class="copy-btn">
                        <n-icon size="12"><RefreshOutline /></n-icon>
                      </n-button>
                    </template>
                    重发
                  </n-tooltip>
                </div>
              </div>
              <n-avatar
                v-if="msg.role === 'user'"
                round
                size="small"
                :style="{ background: '#2080f0' }"
              >{{ userInitial }}</n-avatar>
            </div>

            <!-- 加载状态 -->
            <div v-if="loading" class="message message-ai">
              <n-avatar round size="small" :style="{ background: '#18a058' }">AI</n-avatar>
              <div class="bubble bubble-ai">
                <div class="bubble-text bubble-text-ai" v-html="streamingContent ? renderMarkdown(streamingContent) + '<span class=\'typing-cursor\'></span>' : '<span style=\'color:#999\'>正在思考<span class=\'typing-cursor\'></span></span>'"></div>
              </div>
            </div>
          </div>

          <!-- 输入框 -->
          <div class="chat-input">
            <n-input
              v-model:value="inputText"
              type="textarea"
              placeholder="输入你的问题，按 Enter 发送（Shift+Enter 换行）"
              :autosize="{ minRows: 1, maxRows: 6 }"
              @keydown="handleKeydown"
              class="input-area"
            />
            <n-button
              type="primary"
              :disabled="!inputText.trim()"
              :loading="loading"
              @click="sendMessage"
              circle
              class="send-btn"
            >
              <template #icon><n-icon><SendOutline /></n-icon></template>
            </n-button>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <n-icon size="80" color="#ddd"><ChatbubbleEllipsesOutline /></n-icon>
          <p style="color: #999; margin-top: 16px">选择一个会话或创建新会话开始对话</p>
          <n-button type="primary" @click="createConversation" style="margin-top: 16px">
            新建会话
          </n-button>
        </div>
      </n-layout-content>
    </n-layout>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import {
  CreateOutline, SearchOutline, StarOutline, ChatbubbleOutline,
  TrashOutline, SendOutline, ChatbubbleEllipsesOutline, CopyOutline,
  RefreshOutline, MenuOutline
} from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/auth'

const message = useMessage()
const authStore = useAuthStore()

const userInitial = computed(() => authStore.userInfo?.username?.charAt(0)?.toUpperCase() || 'U')

// 会话列表
const conversations = ref([])
const searchText = ref('')
const currentConversation = ref(null)
const conversationsLoading = ref(false)

// 消息
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const streamingContent = ref('')
const sidebarCollapsed = ref(false)

// refs
const messagesRef = ref(null)
const chatContentRef = ref(null)

const filteredConversations = computed(() => {
  let list = [...conversations.value]
  list.sort((a, b) => (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0))
  if (searchText.value) {
    const kw = searchText.value.toLowerCase()
    list = list.filter(c => (c.title || '').toLowerCase().includes(kw))
  }
  return list
})

function formatDate(d) {
  if (!d) return ''
  const date = new Date(d)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function formatTime(d) {
  if (!d) return ''
  return new Date(d).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function renderMarkdown(text) {
  if (!text) return ''
  // 转义HTML特殊字符（先处理，防止XSS）
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  // 代码块 - 带语言标识
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const langAttr = lang ? ` data-lang="${lang}"` : ''
    const langClass = lang ? ` class="language-${lang}"` : ''
    return `<pre${langAttr}><code${langClass}>${code.trim()}</code></pre>`
  })
  // 行内代码
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  // 标题
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  // 粗体
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // 斜体
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  // 链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  // 列表
  html = html.replace(/^\s*[-*]\s+(.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
  // 换行
  html = html.replace(/\n/g, '<br>')
  return html
}

async function copyMessage(content) {
  try {
    await navigator.clipboard.writeText(content)
    message.success('已复制')
  } catch {
    message.error('复制失败')
  }
}

async function resendMessage(msg) {
  if (msg.role !== 'user') return
  inputText.value = msg.content
  // 删除原消息
  const idx = messages.value.findIndex(m => m.id === msg.id)
  if (idx !== -1) messages.value.splice(idx, 1)
  await sendMessage()
}

async function loadConversations() {
  conversationsLoading.value = true
  try {
    const res = await fetch('/api/v1/ai/conversations?user_id=' + encodeURIComponent(authStore.userInfo.username), {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    if (res.ok) {
      const data = await res.json()
      conversations.value = data.items || data || []
    } else {
      message.error('加载会话列表失败')
    }
  } catch (e) {
    console.error('Load conversations error:', e)
    message.error('加载会话列表失败')
  } finally {
    conversationsLoading.value = false
  }
}

async function selectConversation(conv) {
  currentConversation.value = conv
  messages.value = []
  loading.value = true
  try {
    const res = await fetch(`/api/v1/ai/conversation/${conv.conversation_id}?user_id=${encodeURIComponent(authStore.userInfo.username)}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    if (res.ok) {
      const data = await res.json()
      if (data.messages) {
        messages.value = data.messages.map((m, i) => ({
          id: i,
          role: m.role === 'assistant' ? 'ai' : m.role,
          content: m.content,
          created_at: m.created_at || new Date().toISOString()
        }))
      }
    } else {
      message.error('加载会话失败')
    }
    await nextTick()
    scrollToBottom()
  } catch (e) {
    console.error('Load conversation error:', e)
    message.error('加载会话失败')
  } finally {
    loading.value = false
  }
}

function createConversation() {
  currentConversation.value = { conversation_id: null, title: '新对话' }
  messages.value = []
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  const userMsg = {
    id: Date.now(),
    role: 'user',
    content: text,
    created_at: new Date().toISOString()
  }
  messages.value.push(userMsg)
  inputText.value = ''
  loading.value = true
  streamingContent.value = ''

  await nextTick()
  scrollToBottom()

  try {
    const payload = { 
      message: text, 
      user_id: authStore.userInfo.username,
      conversation_id: currentConversation.value?.conversation_id || undefined 
    }
    const res = await fetch('/api/v1/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      throw new Error('Send message failed')
    }
    
    // 流式读取
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let fullContent = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      fullContent += chunk
      streamingContent.value = fullContent
      await nextTick()
      scrollToBottom()
    }
    
    const aiMsg = {
      id: Date.now() + 1,
      role: 'ai',
      content: fullContent,
      created_at: new Date().toISOString()
    }
    messages.value.push(aiMsg)
    streamingContent.value = ''

    if (res.headers.get('X-Conversation-Id')) {
      const convId = res.headers.get('X-Conversation-Id')
      if (!currentConversation.value.conversation_id) {
        currentConversation.value.conversation_id = convId
        currentConversation.value.title = text.slice(0, 20)
      }
      await loadConversations()
    }
  } catch (e) {
    console.error('Chat error:', e)
    message.error('AI服务暂不可用，请稍后重试')
  } finally {
    loading.value = false
    streamingContent.value = ''
    await nextTick()
    scrollToBottom()
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function handleDelete(conversation_id) {
  try {
    await fetch(`/api/v1/ai/conversations/${conversation_id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
    })
    message.success('会话已删除')
    if (currentConversation.value?.conversation_id === conversation_id) {
      currentConversation.value = null
      messages.value = []
    }
    await loadConversations()
  } catch (e) {
    console.error('Delete error:', e)
    message.error('删除失败')
  }
}

async function handlePin(conv) {
  try {
    const isPinned = !conv.is_pinned
    const res = await fetch(`/api/v1/ai/conversations/${conv.conversation_id}/pin?is_pinned=${isPinned}`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token') || ''}` 
      },
      body: JSON.stringify({ user_id: authStore.userInfo.username })
    })
    if (!res.ok) throw new Error('Pin failed')
    message.success(isPinned ? '已置顶' : '已取消置顶')
    await loadConversations()
  } catch (e) {
    console.error('Pin error:', e)
    message.error('操作失败')
  }
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

onMounted(() => {
  loadConversations()
})
</script>

<style scoped>
.chat-page { height: 100%; display: flex; flex-direction: column; }
.chat-layout { height: calc(100vh - 140px); border-radius: 8px; overflow: hidden; }
.conversation-sider { background: #fafafa; display: flex; flex-direction: column; transition: width 0.2s; }
.sider-header { padding: 12px; background: #fff; border-bottom: 1px solid #eee; }
.conversation-list { flex: 1; overflow-y: auto; }
.conversation-item { cursor: pointer; transition: background 0.2s; padding: 8px 12px !important; }
.conversation-item:hover { background: #f0f0f0; }
.conversation-item.active { background: #e8f4ff; }
.conv-info { flex: 1; min-width: 0; }
.conv-title { font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-time { font-size: 12px; color: #999; margin-top: 2px; }
.chat-main { display: flex; flex-direction: column; height: 100%; }
.chat-header { padding: 16px 20px; border-bottom: 1px solid #eee; background: #fff; display: flex; align-items: center; gap: 12px; }
.chat-header h3 { margin: 0; font-size: 16px; font-weight: 600; }
.collapse-btn { padding: 4px !important; }
.messages { flex: 1; overflow-y: auto; padding: 20px; }
.message { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 16px; }
.message-user { flex-direction: row-reverse; }
.message-ai { flex-direction: row; }
.bubble { max-width: 70%; padding: 10px 14px; border-radius: 12px; position: relative; word-break: break-word; }
.bubble-user { background: #18a058; color: #fff; border-bottom-right-radius: 4px; }
.bubble-ai { background: #f0f0f0; color: #333; border-bottom-left-radius: 4px; }
.bubble-text { line-height: 1.5; }
.bubble-text-ai { font-size: 14px; }
/* Markdown 样式 */
.bubble-text-ai :deep(pre) { background: #282c34; border-radius: 6px; padding: 12px; overflow-x: auto; margin: 8px 0; font-size: 13px; position: relative; }
.bubble-text-ai :deep(pre)::before { content: attr(data-lang); position: absolute; top: 4px; right: 8px; font-size: 11px; color: #888; text-transform: uppercase; }
.bubble-text-ai :deep(code) { background: rgba(0,0,0,0.08); border-radius: 3px; padding: 1px 4px; font-size: 13px; font-family: 'Fira Code', 'Consolas', monospace; }
.bubble-text-ai :deep(pre code) { background: transparent; padding: 0; color: #abb2bf; line-height: 1.5; }
.bubble-text-ai :deep(p) { margin: 4px 0; }
.bubble-text-ai :deep(ul), .bubble-text-ai :deep(ol) { margin: 4px 0; padding-left: 20px; }
.bubble-text-ai :deep(li) { margin: 2px 0; }
.bubble-text-ai :deep(table) { border-collapse: collapse; margin: 8px 0; }
.bubble-text-ai :deep(th), .bubble-text-ai :deep(td) { border: 1px solid #ddd; padding: 4px 8px; font-size: 13px; }
.bubble-text-ai :deep(th) { background: #e8e8e8; }
.bubble-text-ai :deep(h1), .bubble-text-ai :deep(h2), .bubble-text-ai :deep(h3) { margin: 8px 0; font-weight: 600; }
.bubble-text-ai :deep(a) { color: #18a058; }
.bubble-text-ai :deep(strong) { font-weight: 600; }
/* 打字机光标 */
.bubble-text-ai :deep(.typing-cursor)::after { content: '▊'; animation: blink 1s infinite; color: #18a058; }
@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
.bubble-footer { display: flex; align-items: center; justify-content: flex-end; gap: 4px; margin-top: 4px; }
.bubble-time { font-size: 11px; opacity: 0.6; }
.bubble-user .bubble-time { color: rgba(255,255,255,0.7); }
.bubble-ai .bubble-time { color: #999; }
.copy-btn { opacity: 0; transition: opacity 0.2s; padding: 2px !important; min-width: unset !important; }
.bubble:hover .copy-btn { opacity: 1; }
.chat-input { display: flex; align-items: flex-end; gap: 12px; padding: 16px 20px; border-top: 1px solid #eee; background: #fff; }
.input-area { flex: 1; }
.send-btn { flex-shrink: 0; }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; }

/* 响应式 - 小屏幕收起侧边栏 */
@media (max-width: 768px) {
  .chat-layout :deep(.n-layout-sider) { position: absolute; z-index: 100; height: 100%; }
}
</style>
