<template>
  <div class="ai-copilot-page">
    <div class="copilot-container">
      <!-- 左侧边栏 -->
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-header">
          <div class="logo" v-if="!sidebarCollapsed">
            <el-icon :size="24"><MagicStick /></el-icon>
            <span>AI 助手</span>
          </div>
          <el-button text @click="sidebarCollapsed = !sidebarCollapsed">
            <el-icon><component :is="sidebarCollapsed ? 'Expand' : 'Fold'" /></el-icon>
          </el-button>
        </div>

        <div class="sidebar-content" v-if="!sidebarCollapsed">
          <!-- 新建对话 -->
          <el-button type="primary" class="new-chat-btn" @click="startNewChat">
            <el-icon><Plus /></el-icon>
            新建对话
          </el-button>

          <!-- 对话历史 -->
          <div class="chat-history">
            <div class="history-label">历史对话</div>
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
                <el-dropdown trigger="click" @command="(cmd) => handleHistoryCommand(cmd, chat)" @click.stop>
                  <el-button text size="small" class="history-menu">
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="rename">重命名</el-dropdown-item>
                      <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </div>

        <!-- 模型状态 -->
        <div class="sidebar-footer" v-if="!sidebarCollapsed">
          <div class="model-status">
            <div class="model-indicator" :class="modelStatus"></div>
            <div class="model-info">
              <div class="model-name">{{ currentModel }}</div>
              <div class="model-status-text">{{ modelStatusText }}</div>
            </div>
            <el-button text size="small" @click="showModelSelector = true">
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
            <div class="chat-title">{{ currentChatTitle }}</div>
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
              <el-button text @click="exportChat">
                <el-icon><Download /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="清空对话">
              <el-button text @click="clearHistory">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>
            <el-button text @click="showSettingsDrawer = true">
              <el-icon><Setting /></el-icon>
            </el-button>
          </div>
        </header>

        <!-- 消息区域 -->
        <div class="chat-messages" ref="messagesContainer">
          <!-- 空状态 -->
          <div v-if="messages.length === 0" class="empty-state">
            <div class="empty-illustration">
              <div class="ai-orb">
                <div class="orb-inner"></div>
                <div class="orb-ring"></div>
              </div>
            </div>
            <h3 class="empty-title">你好，我是 AI 运维助手</h3>
            <p class="empty-desc">我可以帮你进行故障诊断、日志分析、脚本生成、性能优化等工作</p>

            <!-- 快捷指令 -->
            <div class="quick-prompts-grid">
              <div 
                v-for="prompt in quickPrompts" 
                :key="prompt.title"
                class="prompt-card"
                @click="usePrompt(prompt)"
              >
                <div class="prompt-icon" :style="{ background: prompt.bgColor }">
                  <el-icon><component :is="prompt.icon" /></el-icon>
                </div>
                <div class="prompt-text">{{ prompt.title }}</div>
              </div>
            </div>
          </div>

          <!-- 消息列表 -->
          <div v-else class="messages-list">
            <div 
              v-for="(msg, index) in messages" 
              :key="index"
              class="message-wrapper"
              :class="msg.role"
            >
              <div class="message-avatar">
                <div class="avatar-circle" :class="msg.role">
                  <el-icon v-if="msg.role === 'user'" :size="20"><User /></el-icon>
                  <el-icon v-else :size="20"><MagicStick /></el-icon>
                </div>
              </div>

              <div class="message-bubble">
                <div class="message-content" v-html="formatMessage(msg.content)"></div>
                <div class="message-footer">
                  <div class="message-time">{{ msg.time }}</div>
                  <div class="message-actions" v-if="msg.role === 'assistant'">
                    <el-tooltip content="复制">
                      <el-button text size="small" @click="copyMessage(msg.content)">
                        <el-icon><CopyDocument /></el-icon>
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="重新生成">
                      <el-button text size="small" @click="regenerateMessage(index)">
                        <el-icon><RefreshLeft /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </div>
                </div>
              </div>
            </div>

            <!-- 正在输入指示器 -->
            <div v-if="isTyping" class="message-wrapper assistant">
              <div class="message-avatar">
                <div class="avatar-circle assistant">
                  <el-icon :size="20"><MagicStick /></el-icon>
                </div>
              </div>
              <div class="message-bubble typing">
                <div class="typing-indicator">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
                <span class="typing-text">AI 正在思考...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 快捷操作栏 -->
        <div class="quick-actions-bar" v-if="messages.length > 0">
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
            <div class="input-wrapper" :class="{ focused: inputFocused }">
              <el-input
                v-model="inputMessage"
                type="textarea"
                :rows="1"
                :autosize="{ minRows: 1, maxRows: 4 }"
                placeholder="输入您的问题，AI 助手将为您解答..."
                @keydown.enter.exact.prevent="sendMessage"
                @focus="inputFocused = true"
                @blur="inputFocused = false"
                :disabled="isTyping"
                class="message-input"
              />
              <div class="input-actions">
                <div class="attachment-btn">
                  <el-tooltip content="上传附件">
                    <el-button text size="small" :disabled="isTyping">
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
      <aside class="features-panel" v-if="!featuresCollapsed">
        <div class="panel-header">
          <h3>功能说明</h3>
          <el-button text @click="featuresCollapsed = true">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>

        <div class="panel-content">
          <div 
            v-for="cap in capabilities" 
            :key="cap.title"
            class="capability-card"
          >
            <div class="cap-icon" :style="{ background: cap.bgColor }">
              <el-icon><component :is="cap.icon" /></el-icon>
            </div>
            <div class="cap-info">
              <div class="cap-title">{{ cap.title }}</div>
              <div class="cap-desc">{{ cap.description }}</div>
            </div>
          </div>
        </div>

        <!-- 上下文提示 -->
        <div class="context-section">
          <div class="section-title">
            <el-icon><Connection /></el-icon>
            当前上下文
          </div>
          <div class="context-tags">
            <el-tag v-if="currentContext.server" size="small" closable @close="removeContext('server')">
              服务器: {{ currentContext.server }}
            </el-tag>
            <el-tag v-if="currentContext.service" size="small" closable @close="removeContext('service')">
              服务: {{ currentContext.service }}
            </el-tag>
            <el-tag v-if="!currentContext.server && !currentContext.service" type="info" size="small">
              无上下文
            </el-tag>
          </div>
        </div>

        <!-- 使用统计 -->
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

      <!-- 展开功能面板按钮 -->
      <button class="features-toggle" @click="featuresCollapsed = false" v-if="featuresCollapsed">
        <el-icon><ArrowLeft /></el-icon>
      </button>
    </div>

    <!-- 模型选择器对话框 -->
    <el-dialog v-model="showModelSelector" title="选择 AI 模型" width="500px">
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
              <div class="model-name">{{ model.name }}</div>
              <div class="model-desc">{{ model.description }}</div>
            </div>
            <div class="model-badge" v-if="model.recommended">
              <el-tag size="small" type="success">推荐</el-tag>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 设置抽屉 -->
    <el-drawer v-model="showSettingsDrawer" title="对话设置" size="400px">
      <div class="settings-content">
        <el-form label-position="top">
          <el-form-item label="Temperature（创造性）">
            <el-slider v-model="settings.temperature" :min="0" :max="2" :step="0.1" :marks="tempMarks" />
          </el-form-item>
          <el-form-item label="Max Tokens（最大回复长度）">
            <el-input-number v-model="settings.maxTokens" :min="100" :max="4000" :step="100" />
          </el-form-item>
          <el-form-item label="上下文轮次">
            <el-input-number v-model="settings.contextTurns" :min="1" :max="20" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  MagicStick, Plus, ChatLineSquare, MoreFilled, User, Clock, ChatDotRound,
  Download, Delete, Setting, CopyDocument, RefreshLeft, Fold, Expand, Close,
  Promotion, Paperclip, Connection, DataAnalysis, ArrowLeft, VideoPlay, Document,
  DataLine, Warning, Odometer, Search, Operation, Star, Sparkles, Histogram, Bell
} from '@element-plus/icons-vue'

// 状态
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

// 模型状态
const modelStatus = ref('online')
const modelStatusText = ref('在线')
const currentModel = ref('Qwen3.5-8B')

// 设置
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

// 对话历史
const chatHistory = ref([
  { id: 1, title: '服务器故障排查', createdAt: '2026-05-04' },
  { id: 2, title: 'Nginx 配置优化', createdAt: '2026-05-03' },
  { id: 3, title: '数据库性能分析', createdAt: '2026-05-02' }
])

// 可用模型
const availableModels = [
  { id: 'Qwen3.5-8B', name: 'Qwen 3.5 8B', description: '平衡性能与速度', icon: 'Sparkles', recommended: true },
  { id: 'Qwen3.5-14B', name: 'Qwen 3.5 14B', description: '更高精度，资源占用中等', icon: 'Star', recommended: false },
  { id: 'Qwen3.5-32B', name: 'Qwen 3.5 32B', description: '高精度，适合复杂任务', icon: 'Histogram', recommended: false }
]

// 快捷操作
const quickActions = [
  { title: '故障诊断', icon: 'Search', prompt: '帮我分析最近的服务器故障', bgColor: '#f56c6c' },
  { title: '日志分析', icon: 'Document', prompt: '分析昨天的错误日志', bgColor: '#409eff' },
  { title: '生成报告', icon: 'DataLine', prompt: '生成本周运维报告摘要', bgColor: '#67c23a' },
  { title: '性能优化', icon: 'Odometer', prompt: '给出服务器性能优化建议', bgColor: '#e6a23c' }
]

// 快捷指令
const quickPrompts = [
  { title: '服务器故障排查', icon: 'Warning', bgColor: 'linear-gradient(135deg, #f56c6c, #ff7875)' },
  { title: '日志分析解读', icon: 'Document', bgColor: 'linear-gradient(135deg, #409eff, #53a8ff)' },
  { title: '脚本代码生成', icon: 'Operation', bgColor: 'linear-gradient(135deg, #67c23a, #85ce61)' },
  { title: '性能优化建议', icon: 'Odometer', bgColor: 'linear-gradient(135deg, #e6a23c, #ebb563)' }
]

// 功能说明
const capabilities = [
  { title: '智能问答', icon: 'ChatDotRound', description: '回答运维相关问题，提供解决方案建议', bgColor: '#409eff' },
  { title: '故障诊断', icon: 'Warning', description: '分析告警原因，提供故障排查指导', bgColor: '#f56c6c' },
  { title: '脚本生成', icon: 'Operation', description: '根据需求生成自动化运维脚本', bgColor: '#67c23a' },
  { title: '日志分析', icon: 'Document', description: '解析日志内容，提取关键错误信息', bgColor: '#e6a23c' }
]

// 当前上下文
const currentContext = reactive({
  server: '',
  service: ''
})

// 今日统计
const todayStats = reactive({
  conversations: 5,
  messages: 23,
  tokens: '12.5K'
})

// 辅助函数
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
    // 代码块
    .replace(/```(\w+)?\n?([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre class="code-block"><code class="language-${lang || 'plain'}">${escapeHtml(code.trim())}</code></pre>`
    })
    // 行内代码
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    // 粗体
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // 标题
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    // 列表
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    // 换行
    .replace(/\n/g, '<br>')

  return html
}

const escapeHtml = (str) => {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isTyping.value) return

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: inputMessage.value.trim(),
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })

  const userMessage = inputMessage.value
  inputMessage.value = ''
  isTyping.value = true
  scrollToBottom()

  // 更新统计
  todayStats.messages++

  try {
    // 模拟 AI 响应
    await new Promise(resolve => setTimeout(resolve, 1500))

    const response = getLocalResponse(userMessage)
    messages.value.push({
      role: 'assistant',
      content: response,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    })

    todayStats.messages++
  } catch (error) {
    console.error('AI chat error:', error)
    ElMessage.error('AI 服务暂时不可用')
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}

// 本地响应
const getLocalResponse = (question) => {
  const q = question.toLowerCase()

  if (q.includes('cpu') || q.includes('处理器') || q.includes('负载')) {
    return `根据您的问题，以下是 CPU 负载高的排查步骤：

**1. 查看系统负载**
\`\`\`bash
top -c
htop
uptime
\`\`\`

**2. 找出高占用进程**
\`\`\`bash
ps aux | sort -k3nr | head -10
\`\`\`

**3. 查看进程详情**
\`\`\`bash
pidstat -p <pid> 1 5
strace -p <pid>
\`\`\`

**4. Java 进程检查**
\`\`\`bash
jstat -gc <pid>
jstack <pid>
\`\`\`

**建议**: 如果是突发性负载，先检查是否有定时任务或批处理作业在运行。`

  } else if (q.includes('磁盘') || q.includes('空间') || q.includes('硬盘')) {
    return `磁盘空间不足的处理方案：

**1. 查看磁盘使用情况**
\`\`\`bash
df -h
du -sh /* | sort -hr | head -20
\`\`\`

**2. 查找大文件**
\`\`\`bash
find / -type f -size +100M -exec ls -lh {} \\; 2>/dev/null
\`\`\`

**3. 清理建议**
\`\`\`bash
# 清理日志
find /var/log -name "*.log" -mtime +7 -delete

# 清理缓存
yum clean all  # CentOS
apt clean      # Ubuntu

# 清理旧内核
yum autoremove
\`\`\`

**4. 设置告警阈值**
建议在磁盘使用率达到 80% 时设置告警，90% 时紧急告警。`

  } else if (q.includes('nginx')) {
    return `Nginx 配置检查与优化建议：

**1. 配置语法检查**
\`\`\`bash
nginx -t
nginx -T  # 查看完整配置
\`\`\`

**2. 查看连接状态**
\`\`\`bash
nginx -s reload
curl -I http://localhost/status
\`\`\`

**3. 常见优化参数**
\`\`\`nginx
worker_processes auto;
worker_connections 65535;
keepalive_timeout 65;
gzip on;
client_max_body_size 100m;
\`\`\`

**4. 性能监控**
- 监控活跃连接数
- 监控请求延迟
- 监控 upstream 响应时间
- 检查错误日志

需要我帮您分析具体的 Nginx 配置吗？`

  } else if (q.includes('mysql') || q.includes('数据库') || q.includes('慢查询')) {
    return `MySQL 慢查询优化指南：

**1. 开启慢查询日志**
\`\`\`sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
\`\`\`

**2. 分析慢查询**
\`\`\`bash
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log
pt-query-digest /var/log/mysql/slow.log
\`\`\`

**3. 使用 EXPLAIN**
\`\`\`sql
EXPLAIN SELECT * FROM users WHERE status = 1;
EXPLAIN ANALYZE SELECT * FROM orders WHERE created_at > '2026-01-01';
\`\`\`

**4. 索引优化**
\`\`\`sql
-- 添加索引
ALTER TABLE orders ADD INDEX idx_created_at(created_at);

-- 查看索引
SHOW INDEX FROM orders;
\`\`\`

**5. 连接数监控**
\`\`\`sql
SHOW PROCESSLIST;
SHOW STATUS LIKE 'Max_used_connections';
\`\`\`

建议使用 pt-query-digest 工具进行深度分析。`

  } else if (q.includes('内存') || q.includes('oom') || q.includes('out of memory')) {
    return `内存问题排查与优化：

**1. 查看内存使用**
\`\`\`bash
free -h
cat /proc/meminfo
vmstat 1 5
\`\`\`

**2. 找出高内存进程**
\`\`\`bash
ps aux --sort=-%mem | head -10
top -o %MEM
\`\`\`

**3. 内存泄漏检测**
\`\`\`bash
# Linux
valgrind --leak-check=full ./your_program

# Java
jmap -dump:format=b,file=heap.hprof <pid>
\`\`\`

**4. 清理缓存**
\`\`\`bash
sync
echo 3 > /proc/sys/vm/drop_caches
\`\`\`

**5. OOM 排查**
检查 /var/log/messages 或 journalctl 中是否有 OOM killer 记录。`

  } else {
    return `我来帮您分析这个问题。

**通用排查步骤：**

1. **查看系统日志**
\`\`\`bash
journalctl -xe
tail -f /var/log/messages
\`\`\`

2. **检查服务状态**
\`\`\`bash
systemctl status <service-name>
systemctl restart <service-name>
\`\`\`

3. **查看资源使用**
\`\`\`bash
top
free -h
df -h
netstat -tuln
\`\`\`

4. **检查网络连接**
\`\`\`bash
ss -s
netstat -an | grep ESTABLISHED
\`\`\`

请描述更具体的问题，我可以给出更准确的建议。例如：
- 具体的服务器 IP 或主机名？
- 问题发生的时间点？
- 有哪些错误信息？`
  }
}

// 新建对话
const startNewChat = () => {
  messages.value = []
  currentChatId.value = Date.now()
  currentChatTitle.value = '新对话'
  currentChat.createdAt = new Date()
  todayStats.conversations++
}

// 加载历史对话
const loadChat = (chat) => {
  currentChatId.value = chat.id
  currentChatTitle.value = chat.title
}

// 处理历史命令
const handleHistoryCommand = (command, chat) => {
  switch (command) {
    case 'rename':
      ElMessageBox.prompt('请输入新的对话名称', '重命名', {
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }).then(({ value }) => {
        chat.title = value
        if (currentChatId.value === chat.id) {
          currentChatTitle.value = value
        }
      }).catch(() => {})
      break
    case 'delete':
      ElMessageBox.confirm('确定要删除该对话吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        chatHistory.value = chatHistory.value.filter(c => c.id !== chat.id)
        ElMessage.success('已删除')
      }).catch(() => {})
      break
  }
}

// 清空对话
const clearHistory = async () => {
  try {
    await ElMessageBox.confirm('确定要清空当前对话记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    messages.value = []
    ElMessage.success('已清空对话')
  } catch (e) {}
}

// 复制消息
const copyMessage = (content) => {
  navigator.clipboard.writeText(content)
  ElMessage.success('已复制到剪贴板')
}

// 重新生成
const regenerateMessage = (index) => {
  if (index > 0) {
    const userMsg = messages.value[index - 1]
    messages.value.splice(index, 1)
    inputMessage.value = userMsg.content
    sendMessage()
  }
}

// 使用快捷指令
const usePrompt = (prompt) => {
  inputMessage.value = prompt.prompt || prompt.title
  sendMessage()
}

// 选择模型
const selectModel = (model) => {
  currentModel.value = model.id
  showModelSelector.value = false
  ElMessage.success(`已切换到 ${model.name}`)
}

// 移除上下文
const removeContext = (type) => {
  currentContext[type] = ''
}

// 导出对话
const exportChat = () => {
  const content = messages.value.map(m =>
    `${m.role === 'user' ? '用户' : 'AI'}: ${m.content}`
  ).join('\n\n')

  const blob = new Blob([content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `对话记录_${new Date().toLocaleDateString()}.md`
  a.click()
  URL.revokeObjectURL(url)
}

// 初始化欢迎消息
onMounted(() => {
  // 可以在这里加载历史对话
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.ai-copilot-page {
  height: calc(100vh - 140px);
  animation: fadeIn 0.3s ease;
}

.copilot-container {
  display: flex;
  height: 100%;
  gap: 0;
  background: $bg-page;
}

// ========== 侧边栏 ==========
.sidebar {
  width: 280px;
  background: $bg-container;
  border-right: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  overflow: hidden;

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
    color: $primary;
    font-weight: $font-weight-bold;
    font-size: $font-size-lg;
  }
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-lg;
}

.new-chat-btn {
  width: 100%;
  margin-bottom: $spacing-lg;
}

.chat-history {
  .history-label {
    font-size: $font-size-xs;
    color: $text-placeholder;
    margin-bottom: $spacing-sm;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
  }

  .history-item {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-sm $spacing-md;
    border-radius: $border-radius-md;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: $bg-page;
    }

    &.active {
      background: rgba($primary, 0.1);
      color: $primary;
    }

    .history-title {
      flex: 1;
      font-size: $font-size-sm;
      @include multi-ellipsis(1);
    }

    .history-menu {
      opacity: 0;
      transition: opacity 0.2s;
    }

    &:hover .history-menu {
      opacity: 1;
    }
  }
}

.sidebar-footer {
  padding: $spacing-lg;
  border-top: 1px solid $border-light;
}

.model-status {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  .model-indicator {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: $success;

    &.offline {
      background: $danger;
    }

    &.connecting {
      background: $warning;
      animation: pulse 1s infinite;
    }
  }

  .model-info {
    flex: 1;

    .model-name {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
    }

    .model-status-text {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }
}

// ========== 主聊天区域 ==========
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: $bg-container;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-lg $spacing-xl;
  border-bottom: 1px solid $border-light;
  background: $bg-container;

  .header-info {
    .chat-title {
      font-size: $font-size-lg;
      font-weight: $font-weight-semibold;
      color: $text-primary;
      margin-bottom: $spacing-xs;
    }

    .chat-meta {
      display: flex;
      gap: $spacing-lg;

      .meta-item {
        display: flex;
        align-items: center;
        gap: $spacing-xs;
        font-size: $font-size-xs;
        color: $text-secondary;
      }
    }
  }

  .header-actions {
    display: flex;
    gap: $spacing-sm;
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-xl;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-thumb {
    background: $border-light;
    border-radius: 3px;
  }
}

// 空状态
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: $spacing-xxl;

  .empty-illustration {
    margin-bottom: $spacing-xl;
  }

  .ai-orb {
    position: relative;
    width: 120px;
    height: 120px;

    .orb-inner {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 80px;
      height: 80px;
      background: linear-gradient(135deg, $primary, #4080ff);
      border-radius: 50%;
      animation: orb-pulse 3s ease-in-out infinite;

      &::after {
        content: '';
        position: absolute;
        top: 20%;
        left: 25%;
        width: 30px;
        height: 20px;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        filter: blur(5px);
      }
    }

    .orb-ring {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 120px;
      height: 120px;
      border: 2px solid rgba($primary, 0.3);
      border-radius: 50%;
      animation: ring-expand 2s ease-out infinite;
    }
  }

  .empty-title {
    font-size: $font-size-xl;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin: 0 0 $spacing-sm 0;
  }

  .empty-desc {
    font-size: $font-size-md;
    color: $text-secondary;
    margin: 0 0 $spacing-xxl 0;
    text-align: center;
  }
}

.quick-prompts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;
  width: 100%;
  max-width: 500px;

  .prompt-card {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-md $spacing-lg;
    background: $bg-container;
    border: 1px solid $border-light;
    border-radius: $border-radius-lg;
    cursor: pointer;
    transition: all 0.25s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: $shadow-base;
      border-color: $primary;
    }

    .prompt-icon {
      width: 44px;
      height: 44px;
      border-radius: $border-radius-md;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 20px;
    }

    .prompt-text {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }
  }
}

// 消息列表
.messages-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

.message-wrapper {
  display: flex;
  gap: $spacing-md;

  &.user {
    flex-direction: row-reverse;

    .message-bubble {
      background: $primary;
      color: #fff;

      .message-content {
        :deep(code.inline-code) {
          background: rgba(255, 255, 255, 0.2);
        }

        :deep(.code-block) {
          background: rgba(0, 0, 0, 0.3);
        }
      }

      .message-footer {
        .message-time {
          color: rgba(255, 255, 255, 0.7);
        }
      }
    }
  }
}

.message-avatar {
  flex-shrink: 0;

  .avatar-circle {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;

    &.user {
      background: $primary;
    }

    &.assistant {
      background: linear-gradient(135deg, $success, #23c343);
    }
  }
}

.message-bubble {
  max-width: 70%;
  padding: $spacing-md $spacing-lg;
  border-radius: $border-radius-lg;
  background: $bg-page;

  &.typing {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-md $spacing-lg;
  }

  .message-content {
    font-size: $font-size-md;
    line-height: 1.8;
    color: $text-primary;

    :deep(.code-block) {
      background: #1e1e1e;
      border-radius: $border-radius-md;
      padding: $spacing-md;
      margin: $spacing-md 0;
      overflow-x: auto;
      font-family: 'Monaco', 'Consolas', monospace;
      font-size: $font-size-sm;
      color: #d4d4d4;

      code {
        color: #d4d4d4;
      }
    }

    :deep(.inline-code) {
      background: $bg-page;
      padding: 2px 6px;
      border-radius: $border-radius-sm;
      font-family: 'Monaco', monospace;
      font-size: 0.9em;
      color: $primary;
    }

    :deep(h2, h3, h4) {
      margin: $spacing-md 0;
      color: $text-primary;
    }

    :deep(ul) {
      margin: $spacing-md 0;
      padding-left: $spacing-lg;

      li {
        margin-bottom: $spacing-xs;
      }
    }
  }

  .message-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: $spacing-sm;
    padding-top: $spacing-sm;
    border-top: 1px solid rgba(0, 0, 0, 0.05);

    .message-time {
      font-size: $font-size-xs;
      color: $text-placeholder;
    }

    .message-actions {
      display: flex;
      gap: $spacing-xs;
      opacity: 0;
      transition: opacity 0.2s;

      :deep(.el-button) {
        color: $text-secondary;

        &:hover {
          color: $primary;
        }
      }
    }
  }

  &:hover .message-actions {
    opacity: 1;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;

  .dot {
    width: 8px;
    height: 8px;
    background: $text-secondary;
    border-radius: 50%;
    animation: typing-bounce 1.4s infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

.typing-text {
  font-size: $font-size-sm;
  color: $text-secondary;
}

// 快捷操作栏
.quick-actions-bar {
  padding: $spacing-md $spacing-xl;
  border-top: 1px solid $border-light;

  .quick-actions-scroll {
    display: flex;
    gap: $spacing-sm;
    overflow-x: auto;
    padding: $spacing-xs 0;

    &::-webkit-scrollbar {
      height: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: $border-light;
      border-radius: 2px;
    }
  }

  .quick-action-chip {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding: $spacing-xs $spacing-md;
    background: $bg-page;
    border: 1px solid $border-light;
    border-radius: 20px;
    font-size: $font-size-xs;
    color: $text-secondary;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s ease;

    &:hover {
      background: $primary;
      color: #fff;
      border-color: $primary;
    }
  }
}

// 输入区域
.chat-footer {
  padding: $spacing-lg $spacing-xl;
  background: $bg-container;
  border-top: 1px solid $border-light;
}

.input-container {
  .input-wrapper {
    display: flex;
    align-items: flex-end;
    gap: $spacing-md;
    padding: $spacing-md;
    background: $bg-page;
    border: 2px solid transparent;
    border-radius: $border-radius-lg;
    transition: all 0.2s ease;

    &.focused {
      border-color: $primary;
      box-shadow: 0 0 0 3px rgba($primary, 0.1);
    }

    :deep(.message-input) {
      flex: 1;

      .el-textarea__inner {
        border: none;
        background: transparent;
        resize: none;
        font-size: $font-size-md;
        line-height: 1.6;
        padding: 0;

        &:focus {
          box-shadow: none;
        }
      }
    }

    .input-actions {
      display: flex;
      align-items: center;
      gap: $spacing-sm;

      .send-btn {
        :deep(.el-button) {
          padding: $spacing-sm $spacing-lg;
        }
      }
    }
  }

  .input-hint {
    margin-top: $spacing-xs;
    font-size: $font-size-xs;
    color: $text-placeholder;
    text-align: center;
  }
}

// ========== 功能面板 ==========
.features-panel {
  width: 300px;
  background: $bg-container;
  border-left: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-lg;
  border-bottom: 1px solid $border-light;

  h3 {
    margin: 0;
    font-size: $font-size-md;
    font-weight: $font-weight-semibold;
  }
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-lg;
}

.capability-card {
  display: flex;
  gap: $spacing-md;
  padding: $spacing-md;
  margin-bottom: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;
  transition: all 0.2s ease;

  &:hover {
    transform: translateX(4px);
  }

  .cap-icon {
    width: 40px;
    height: 40px;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 18px;
    flex-shrink: 0;
  }

  .cap-info {
    .cap-title {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
      margin-bottom: 2px;
    }

    .cap-desc {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }
}

.context-section, .stats-section {
  padding: $spacing-lg;
  border-top: 1px solid $border-light;

  .section-title {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: $spacing-md;
  }

  .context-tags {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs;
  }

  .stats-list {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;

    .stat-item {
      display: flex;
      justify-content: space-between;
      font-size: $font-size-sm;

      .stat-label {
        color: $text-secondary;
      }

      .stat-value {
        font-weight: $font-weight-medium;
        color: $text-primary;
      }
    }
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
  border: 1px solid $border-light;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  z-index: 10;

  &:hover {
    background: $primary;
    color: #fff;
    border-color: $primary;
  }
}

// ========== 模型选择器 ==========
.model-selector {
  .model-list {
    display: flex;
    flex-direction: column;
    gap: $spacing-md;
  }

  .model-item {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-md;
    border: 2px solid $border-light;
    border-radius: $border-radius-md;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      border-color: $primary;
    }

    &.active {
      border-color: $primary;
      background: rgba($primary, 0.05);
    }

    .model-icon {
      width: 48px;
      height: 48px;
      background: linear-gradient(135deg, $primary, #4080ff);
      border-radius: $border-radius-md;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 24px;
    }

    .model-details {
      flex: 1;

      .model-name {
        font-size: $font-size-md;
        font-weight: $font-weight-medium;
        color: $text-primary;
      }

      .model-desc {
        font-size: $font-size-sm;
        color: $text-secondary;
      }
    }
  }
}

// ========== 动画 ==========
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes orb-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.05); }
}

@keyframes ring-expand {
  0% { transform: translate(-50%, -50%) scale(0.8); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(1.2); opacity: 0; }
}

@keyframes typing-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

// ========== 响应式 ==========
@include respond-to('xl') {
  .features-panel {
    width: 260px;
  }
}

@include respond-to('lg') {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100%;
    z-index: 100;
    transform: translateX(-100%);

    &:not(.collapsed) {
      transform: translateX(0);
      box-shadow: $shadow-lg;
    }
  }

  .features-panel {
    position: fixed;
    right: 0;
    top: 0;
    height: 100%;
    z-index: 100;
    transform: translateX(100%);

    &:not(.collapsed) {
      transform: translateX(0);
      box-shadow: $shadow-lg;
    }
  }

  .features-toggle {
    display: flex;
  }
}
</style>