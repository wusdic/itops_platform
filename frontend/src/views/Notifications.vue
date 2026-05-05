<template>
  <div class="notifications-page">
    <div class="page-container">
      <!-- 页面头部 -->
      <header class="page-header">
        <div class="header-left">
          <h2 class="page-title">消息中心</h2>
          <p class="page-subtitle">配置和管理告警通知渠道</p>
        </div>
        <div class="header-actions">
          <el-button @click="refreshChannels">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button type="primary" @click="openAddDialog">
            <el-icon><Plus /></el-icon>
            添加渠道
          </el-button>
        </div>
      </header>

      <!-- 统计概览 -->
      <div class="stats-overview">
        <div class="stat-card">
          <div class="stat-icon email">
            <el-icon><Message /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ channels.filter(c => c.type === 'email').length }}</div>
            <div class="stat-label">邮件渠道</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon im">
            <el-icon><ChatLineSquare /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ channels.filter(c => ['dingtalk', 'feishu', 'wecom'].includes(c.type)).length }}</div>
            <div class="stat-label">IM 渠道</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon webhook">
            <el-icon><Link /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ channels.filter(c => c.type === 'webhook').length }}</div>
            <div class="stat-label">Webhook</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon active">
            <el-icon><Bell /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ channels.filter(c => c.enabled).length }}</div>
            <div class="stat-label">已启用</div>
          </div>
        </div>
      </div>

      <!-- 渠道列表 -->
      <div class="channels-section">
        <div class="section-toolbar">
          <el-tabs v-model="activeChannelTab" @tab-change="filterChannels">
            <el-tab-pane label="全部" name="all" />
            <el-tab-pane label="已启用" name="enabled" />
            <el-tab-pane label="已禁用" name="disabled" />
          </el-tabs>
          <div class="toolbar-actions">
            <el-input v-model="searchText" placeholder="搜索渠道名称..." style="width: 200px" clearable>
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
        </div>

        <div class="channels-grid">
          <div 
            v-for="channel in filteredChannels" 
            :key="channel.id"
            class="channel-card"
            :class="{ disabled: !channel.enabled }"
          >
            <div class="card-header">
              <div class="channel-badge" :style="{ background: getChannelGradient(channel.type) }">
                <el-icon :size="24"><component :is="getChannelIcon(channel.type)" /></el-icon>
              </div>
              <div class="channel-meta">
                <div class="channel-name">{{ channel.name }}</div>
                <div class="channel-type-tag" :style="{ color: getChannelColor(channel.type) }">
                  {{ getChannelTypeText(channel.type) }}
                </div>
              </div>
              <div class="channel-toggle">
                <el-switch v-model="channel.enabled" @change="toggleChannel(channel)" />
              </div>
            </div>

            <div class="card-body">
              <div class="config-list">
                <div v-if="channel.config?.webhook" class="config-item">
                  <el-icon><Link /></el-icon>
                  <span class="config-label">地址:</span>
                  <span class="config-value">{{ truncateUrl(channel.config.webhook) }}</span>
                </div>
                <div v-if="channel.config?.email" class="config-item">
                  <el-icon><Message /></el-icon>
                  <span class="config-label">邮箱:</span>
                  <span class="config-value">{{ channel.config.email }}</span>
                </div>
                <div v-if="channel.config?.receivers?.length" class="config-item">
                  <el-icon><User /></el-icon>
                  <span class="config-label">接收人:</span>
                  <span class="config-value">{{ channel.config.receivers.join(', ') }}</span>
                </div>
                <div v-if="channel.config?.smtp_host" class="config-item">
                  <el-icon><Connection /></el-icon>
                  <span class="config-label">SMTP:</span>
                  <span class="config-value">{{ channel.config.smtp_host }}:{{ channel.config.smtp_port }}</span>
                </div>
              </div>
            </div>

            <div class="card-footer">
              <div class="footer-stats">
                <span class="stat-item">
                  <el-icon><Clock /></el-icon>
                  {{ channel.lastTest || '从未测试' }}
                </span>
              </div>
              <div class="footer-actions">
                <el-tooltip content="发送测试消息">
                  <el-button text size="small" @click="testChannel(channel)">
                    <el-icon><Promotion /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="编辑">
                  <el-button text size="small" @click="editChannel(channel)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="删除">
                  <el-button text size="small" type="danger" @click="deleteChannel(channel)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
          </div>

          <!-- 添加新渠道卡片 -->
          <div class="add-channel-card" @click="openAddDialog">
            <div class="add-icon">
              <el-icon><Plus /></el-icon>
            </div>
            <div class="add-text">添加新渠道</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑渠道' : '添加渠道'" 
      width="550px"
      :close-on-click-modal="false"
      class="channel-dialog"
    >
      <el-form :model="form" :rules="formRules" ref="formRef" label-position="top">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="form.name" placeholder="给渠道起个名字" maxlength="30">
            <template #prefix>
              <el-icon><Edit /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="渠道类型" prop="type">
          <div class="type-selector">
            <div 
              v-for="type in channelTypes" 
              :key="type.value"
              class="type-option"
              :class="{ active: form.type === type.value }"
              @click="form.type = type.value"
            >
              <div class="type-icon" :style="{ background: type.color }">
                <el-icon><component :is="type.icon" /></el-icon>
              </div>
              <div class="type-info">
                <div class="type-name">{{ type.label }}</div>
                <div class="type-desc">{{ type.desc }}</div>
              </div>
              <div class="type-check" v-if="form.type === type.value">
                <el-icon><Check /></el-icon>
              </div>
            </div>
          </div>
        </el-form-item>

        <!-- 邮件配置 -->
        <template v-if="form.type === 'email'">
          <div class="config-section">
            <div class="config-title">邮件配置</div>
            <el-form-item label="SMTP 服务器">
              <el-input v-model="form.config.smtp_host" placeholder="smtp.example.com">
                <template #prefix>
                  <el-icon><Connection /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <div class="form-row">
              <el-form-item label="SMTP 端口">
                <el-input-number v-model="form.config.smtp_port" :min="1" :max="65535" style="width: 100%" />
              </el-form-item>
              <el-form-item label="使用 SSL">
                <el-switch v-model="form.config.use_ssl" />
              </el-form-item>
            </div>
            <el-form-item label="发件人邮箱">
              <el-input v-model="form.config.from_email" placeholder="noreply@example.com">
                <template #prefix>
                  <el-icon><Message /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="收件人">
              <el-select v-model="form.config.to_emails" multiple placeholder="选择收件人" style="width: 100%">
                <el-option label="管理员 (admin@example.com)" value="admin@example.com" />
                <el-option label="运维团队 (ops@example.com)" value="ops@example.com" />
                <el-option label="值班人员 (oncall@example.com)" value="oncall@example.com" />
              </el-select>
            </el-form-item>
          </div>
        </template>

        <!-- IM 渠道配置 -->
        <template v-else-if="['dingtalk', 'feishu', 'wecom'].includes(form.type)">
          <div class="config-section">
            <div class="config-title">
              {{ getChannelTypeText(form.type) }} 配置
              <el-tag size="small" type="warning">需要配置群机器人</el-tag>
            </div>
            <el-form-item label="Webhook 地址" prop="config.webhook">
              <el-input v-model="form.config.webhook" placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx">
                <template #prefix>
                  <el-icon><Link /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item v-if="form.type === 'dingtalk'" label="加签密钥 (可选)">
              <el-input v-model="form.config.secret" placeholder="SEC 开头的密钥">
                <template #prefix>
                  <el-icon><Key /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="接收群">
              <el-select v-model="form.config.group" placeholder="选择接收群" style="width: 100%">
                <el-option label="运维告警群" value="ops-alert" />
                <el-option label="开发通知群" value="dev-notify" />
                <el-option label="值班通知群" value="oncall" />
              </el-select>
            </el-form-item>
          </div>
        </template>

        <!-- Webhook 配置 -->
        <template v-else-if="form.type === 'webhook'">
          <div class="config-section">
            <div class="config-title">Webhook 配置</div>
            <el-form-item label="请求地址" prop="config.webhook">
              <el-input v-model="form.config.webhook" placeholder="https://your-api.com/webhook">
                <template #prefix>
                  <el-icon><Link /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <div class="form-row">
              <el-form-item label="请求方法">
                <el-select v-model="form.config.method" style="width: 100%">
                  <el-option label="POST" value="POST" />
                  <el-option label="PUT" value="PUT" />
                  <el-option label="GET" value="GET" />
                </el-select>
              </el-form-item>
              <el-form-item label="Content-Type">
                <el-select v-model="form.config.content_type" style="width: 100%">
                  <el-option label="application/json" value="application/json" />
                  <el-option label="application/x-www-form-urlencoded" value="application/x-www-form-urlencoded" />
                </el-select>
              </el-form-item>
            </div>
            <el-form-item label="Headers (JSON)">
              <el-input v-model="form.config.headers" type="textarea" :rows="2" placeholder='{"Authorization": "Bearer xxx"}' />
            </el-form-item>
          </div>
        </template>

        <!-- 通用设置 -->
        <div class="general-settings">
          <el-form-item label="启用状态">
            <el-switch v-model="form.enabled" />
            <span class="enable-hint">{{ form.enabled ? '该渠道将正常接收通知' : '该渠道已停用' }}</span>
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">
          <el-icon><Check /></el-icon>
          {{ isEdit ? '保存修改' : '确认添加' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试结果对话框 -->
    <el-dialog v-model="testDialogVisible" title="测试结果" width="400px" class="test-dialog">
      <div class="test-result-content">
        <div class="result-icon" :class="testResult.success ? 'success' : 'error'">
          <el-icon :size="48">
            <component :is="testResult.success ? 'CircleCheck' : 'CircleClose'" />
          </el-icon>
        </div>
        <div class="result-message">{{ testResult.message }}</div>
        <div v-if="testResult.details" class="result-details">
          <div v-for="(val, key) in testResult.details" :key="key" class="detail-row">
            <span class="detail-key">{{ key }}:</span>
            <span class="detail-value">{{ val }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="testChannel(currentTestChannel)" v-if="currentTestChannel">
          重新测试
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh, Plus, Search, Edit, Delete, Check, Clock, Link, User,
  Message, ChatLineSquare, Bell, Connection, Key, Promotion, CircleCheck, CircleClose
} from '@element-plus/icons-vue'

// 状态
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const activeChannelTab = ref('all')
const searchText = ref('')
const currentTestChannel = ref(null)

// 渠道类型
const channelTypes = [
  { value: 'dingtalk', label: '钉钉', desc: '发送到钉钉群', icon: 'ChatLineSquare', color: '#1677ff' },
  { value: 'feishu', label: '飞书', desc: '发送到飞书群', icon: 'ChatDotRound', color: '#18a058' },
  { value: 'wecom', label: '企业微信', desc: '发送到企业微信', icon: 'Message', color: '#07c160' },
  { value: 'email', label: '邮件', desc: '发送邮件通知', icon: 'Message', color: '#409eff' },
  { value: 'webhook', label: 'Webhook', desc: 'HTTP 请求回调', icon: 'Link', color: '#909399' },
  { value: 'sms', label: '短信', desc: '发送短信通知', icon: 'Bell', color: '#f56c6c' }
]

// 渠道列表
const channels = ref([
  { 
    id: 1, 
    name: '钉钉告警群', 
    type: 'dingtalk', 
    enabled: true, 
    lastTest: '2026-05-04 10:30',
    config: { 
      webhook: 'https://oapi.dingtalk.com/robot/send?access_token=abc123', 
      receivers: ['运维团队', '开发组'],
      secret: 'SEC***'
    } 
  },
  { 
    id: 2, 
    name: '飞书告警群', 
    type: 'feishu', 
    enabled: true, 
    lastTest: '2026-05-03 18:20',
    config: { 
      webhook: 'https://open.feishu.cn/open-apis/bot/hook/xyz789', 
      receivers: ['运维团队']
    } 
  },
  { 
    id: 3, 
    name: '企业微信告警', 
    type: 'wecom', 
    enabled: true, 
    lastTest: '2026-05-04 09:15',
    config: { 
      webhook: 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=def456', 
      receivers: ['运维团队']
    } 
  },
  { 
    id: 4, 
    name: '管理员邮件', 
    type: 'email', 
    enabled: true, 
    lastTest: '2026-05-04 23:55',
    config: { 
      email: 'admin@example.com', 
      smtp_host: 'smtp.example.com', 
      smtp_port: 465,
      use_ssl: true,
      from_email: 'noreply@example.com',
      to_emails: ['admin@example.com']
    } 
  },
  { 
    id: 5, 
    name: '值班通知', 
    type: 'wecom', 
    enabled: false, 
    lastTest: '2026-04-28 14:00',
    config: { 
      webhook: 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=ghi789', 
      receivers: ['值班人员']
    } 
  },
  { 
    id: 6, 
    name: '自定义 Webhook', 
    type: 'webhook', 
    enabled: false, 
    lastTest: '从未测试',
    config: { 
      webhook: 'https://your-api.com/notify',
      method: 'POST',
      content_type: 'application/json'
    } 
  }
])

// 表单
const form = reactive({
  name: '',
  type: 'dingtalk',
  enabled: true,
  config: {
    webhook: '',
    secret: '',
    group: '',
    smtp_host: '',
    smtp_port: 465,
    use_ssl: true,
    from_email: '',
    to_emails: [],
    method: 'POST',
    content_type: 'application/json',
    headers: ''
  }
})

const formRules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择渠道类型', trigger: 'change' }],
  'config.webhook': [
    { required: true, message: '请输入 Webhook 地址', trigger: 'blur' },
    { type: 'url', message: '请输入有效的 URL', trigger: 'blur' }
  ]
}

// 测试结果
const testResult = reactive({
  success: false,
  message: '',
  details: null
})

// 计算属性
const filteredChannels = computed(() => {
  let result = channels.value

  // 标签筛选
  if (activeChannelTab.value === 'enabled') {
    result = result.filter(c => c.enabled)
  } else if (activeChannelTab.value === 'disabled') {
    result = result.filter(c => !c.enabled)
  }

  // 搜索筛选
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(c => c.name.toLowerCase().includes(search))
  }

  return result
})

// 辅助函数
const getChannelIcon = (type) => {
  const icons = { 
    dingtalk: 'ChatLineSquare', 
    feishu: 'ChatDotRound', 
    wecom: 'Message', 
    email: 'Message', 
    sms: 'Bell', 
    webhook: 'Link' 
  }
  return icons[type] || 'Bell'
}

const getChannelColor = (type) => {
  const colors = { 
    dingtalk: '#1677ff', 
    feishu: '#18a058', 
    wecom: '#07c160', 
    email: '#409eff', 
    sms: '#f56c6c', 
    webhook: '#909399' 
  }
  return colors[type] || '#909399'
}

const getChannelGradient = (type) => {
  const gradients = {
    dingtalk: 'linear-gradient(135deg, #1677ff, #409eff)',
    feishu: 'linear-gradient(135deg, #18a058, #67c23a)',
    wecom: 'linear-gradient(135deg, #07c160, #85ce61)',
    email: 'linear-gradient(135deg, #409eff, #53a8ff)',
    sms: 'linear-gradient(135deg, #f56c6c, #ff7875)',
    webhook: 'linear-gradient(135deg, #909399, #b1b3b8)'
  }
  return gradients[type] || 'linear-gradient(135deg, #909399, #b1b3b8)'
}

const getChannelTypeText = (type) => {
  const texts = { dingtalk: '钉钉', feishu: '飞书', wecom: '企业微信', email: '邮件', sms: '短信', webhook: 'Webhook' }
  return texts[type] || type
}

const truncateUrl = (url) => {
  if (!url) return ''
  try {
    const parsed = new URL(url)
    return parsed.host + (parsed.pathname.length > 20 ? parsed.pathname.slice(0, 20) + '...' : parsed.pathname)
  } catch {
    return url.length > 40 ? url.slice(0, 40) + '...' : url
  }
}

// 操作
const openAddDialog = () => {
  isEdit.value = false
  Object.assign(form, {
    name: '',
    type: 'dingtalk',
    enabled: true,
    config: {
      webhook: '',
      secret: '',
      group: '',
      smtp_host: '',
      smtp_port: 465,
      use_ssl: true,
      from_email: '',
      to_emails: [],
      method: 'POST',
      content_type: 'application/json',
      headers: ''
    }
  })
  dialogVisible.value = true
}

const editChannel = (channel) => {
  isEdit.value = true
  Object.assign(form, {
    id: channel.id,
    name: channel.name,
    type: channel.type,
    enabled: channel.enabled,
    config: { ...channel.config }
  })
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return

  await formRef.value.validate((valid) => {
    if (valid) {
      if (isEdit.value) {
        const idx = channels.value.findIndex(c => c.id === form.id)
        if (idx !== -1) {
          channels.value[idx] = { ...channels.value[idx], ...form }
        }
        ElMessage.success('渠道修改成功')
      } else {
        channels.value.push({
          id: Date.now(),
          ...form,
          lastTest: '从未测试'
        })
        ElMessage.success('渠道添加成功')
      }
      dialogVisible.value = false
    }
  })
}

const toggleChannel = (channel) => {
  const status = channel.enabled ? '启用' : '禁用'
  ElMessage.success(`${channel.name} 已${status}`)
}

const testChannel = async (channel) => {
  currentTestChannel.value = channel

  // 模拟测试
  const success = Math.random() > 0.2
  testResult.success = success
  testResult.message = success 
    ? `${channel.name} 测试成功！` 
    : `${channel.name} 测试失败，请检查配置`
  testResult.details = success ? {
    '响应时间': Math.floor(Math.random() * 500 + 100) + 'ms',
    '状态码': '200'
  } : {
    '错误类型': 'Connection Timeout',
    '建议': '请检查 Webhook 地址是否正确'
  }

  testDialogVisible.value = true

  // 更新最后测试时间
  if (success) {
    channel.lastTest = new Date().toLocaleString('zh-CN')
  }
}

const deleteChannel = async (channel) => {
  try {
    await ElMessageBox.confirm(`确定要删除通知渠道「${channel.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    channels.value = channels.value.filter(c => c.id !== channel.id)
    ElMessage.success('渠道已删除')
  } catch (e) {}
}

const refreshChannels = () => {
  ElMessage.success('渠道列表已刷新')
}

const filterChannels = () => {
  // 筛选逻辑在 computed 中处理
}

// 初始化
onMounted(() => {
  // 加载渠道列表
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.notifications-page {
  animation: fadeIn 0.3s ease;
}

.page-container {
  max-width: 1400px;
}

// ========== 页面头部 ==========
.page-header {
  @include flex-between;
  margin-bottom: $spacing-xl;

  .page-title {
    font-size: $font-size-xxl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: 0 0 4px 0;
  }

  .page-subtitle {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin: 0;
  }

  .header-actions {
    display: flex;
    gap: $spacing-sm;
  }
}

// ========== 统计概览 ==========
.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-lg;
  background: $bg-container;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-sm;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-base;
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 22px;

    &.email { background: linear-gradient(135deg, #409eff, #53a8ff); }
    &.im { background: linear-gradient(135deg, #67c23a, #85ce61); }
    &.webhook { background: linear-gradient(135deg, #909399, #b1b3b8); }
    &.active { background: linear-gradient(135deg, #165dff, #4080ff); }
  }

  .stat-info {
    .stat-value {
      font-size: $font-size-xxl;
      font-weight: $font-weight-bold;
      color: $text-primary;
    }

    .stat-label {
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }
}

// ========== 渠道列表 ==========
.channels-section {
  background: $bg-container;
  border-radius: $border-radius-lg;
  padding: $spacing-lg;
  box-shadow: $shadow-sm;
}

.section-toolbar {
  @include flex-between;
  margin-bottom: $spacing-lg;

  :deep(.el-tabs) {
    .el-tabs__header {
      margin-bottom: 0;
    }
  }
}

.toolbar-actions {
  display: flex;
  gap: $spacing-sm;
}

.channels-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: $spacing-lg;
}

.channel-card {
  background: $bg-page;
  border: 2px solid $border-light;
  border-radius: $border-radius-lg;
  overflow: hidden;
  transition: all 0.25s ease;

  &:hover {
    border-color: $primary;
    box-shadow: $shadow-base;
  }

  &.disabled {
    opacity: 0.6;

    .channel-badge {
      filter: grayscale(100%);
    }
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-lg;
    background: $bg-container;
    border-bottom: 1px solid $border-light;
  }

  .channel-badge {
    width: 48px;
    height: 48px;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    flex-shrink: 0;
  }

  .channel-meta {
    flex: 1;

    .channel-name {
      font-size: $font-size-md;
      font-weight: $font-weight-semibold;
      color: $text-primary;
      margin-bottom: 2px;
    }

    .channel-type-tag {
      font-size: $font-size-xs;
      font-weight: $font-weight-medium;
    }
  }
}

.card-body {
  padding: $spacing-md $spacing-lg;

  .config-list {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }

  .config-item {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-sm;
    color: $text-secondary;

    .el-icon {
      color: $text-placeholder;
    }

    .config-label {
      color: $text-placeholder;
    }

    .config-value {
      color: $text-primary;
      @include multi-ellipsis(1);
    }
  }
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-md $spacing-lg;
  background: $bg-page;
  border-top: 1px solid $border-light;

  .footer-stats {
    .stat-item {
      display: flex;
      align-items: center;
      gap: $spacing-xs;
      font-size: $font-size-xs;
      color: $text-secondary;

      .el-icon {
        color: $text-placeholder;
      }
    }
  }

  .footer-actions {
    display: flex;
    gap: $spacing-xs;
  }
}

// 添加新渠道卡片
.add-channel-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-md;
  padding: $spacing-xxl;
  background: $bg-page;
  border: 2px dashed $border-base;
  border-radius: $border-radius-lg;
  cursor: pointer;
  transition: all 0.25s ease;
  min-height: 200px;

  &:hover {
    border-color: $primary;
    background: rgba($primary, 0.05);

    .add-icon {
      transform: scale(1.1);
      background: $primary;
    }
  }

  .add-icon {
    width: 56px;
    height: 56px;
    background: $bg-container;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    color: $text-secondary;
    transition: all 0.25s ease;
  }

  .add-text {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

// ========== 对话框 ==========
.channel-dialog {
  :deep(.el-dialog__header) {
    padding: $spacing-lg;
    border-bottom: 1px solid $border-light;
  }

  :deep(.el-dialog__body) {
    padding: $spacing-lg;
  }
}

.type-selector {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;
}

.type-option {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md;
  background: $bg-page;
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

    .type-check {
      color: $primary;
    }
  }

  .type-icon {
    width: 40px;
    height: 40px;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 18px;
  }

  .type-info {
    flex: 1;

    .type-name {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .type-desc {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }

  .type-check {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: transparent;
  }
}

.config-section {
  padding: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-md;

  .config-title {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: $spacing-md;
  }
}

.form-row {
  display: flex;
  gap: $spacing-md;

  > * {
    flex: 1;
  }
}

.general-settings {
  .enable-hint {
    margin-left: $spacing-md;
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

// ========== 测试结果 ==========
.test-result-content {
  text-align: center;
  padding: $spacing-lg;

  .result-icon {
    margin-bottom: $spacing-lg;

    &.success {
      color: $success;
    }

    &.error {
      color: $danger;
    }
  }

  .result-message {
    font-size: $font-size-lg;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: $spacing-lg;
  }

  .result-details {
    padding: $spacing-md;
    background: $bg-page;
    border-radius: $border-radius-md;

    .detail-row {
      display: flex;
      justify-content: space-between;
      font-size: $font-size-sm;
      padding: $spacing-xs 0;

      .detail-key {
        color: $text-secondary;
      }

      .detail-value {
        color: $text-primary;
        font-weight: $font-weight-medium;
      }
    }
  }
}

// ========== 动画 ==========
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

// ========== 响应式 ==========
@include respond-to('xl') {
  .stats-overview {
    grid-template-columns: repeat(2, 1fr);
  }

  .type-selector {
    grid-template-columns: 1fr;
  }
}

@include respond-to('lg') {
  .stats-overview {
    grid-template-columns: 1fr;
  }

  .channels-grid {
    grid-template-columns: 1fr;
  }

  .section-toolbar {
    flex-direction: column;
    gap: $spacing-md;
  }
}
</style>