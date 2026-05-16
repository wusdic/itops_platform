<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">通知配置</h1>
        <p class="page-subtitle">管理告警通知渠道、规则和接收对象</p>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="notification-tabs">
      <!-- Tab1: 通知渠道 -->
      <el-tab-pane label="通知渠道" name="channels">
        <div class="tab-header">
          <el-button type="primary" @click="handleAddChannel">
            <el-icon><Plus /></el-icon> 添加渠道
          </el-button>
        </div>
        <el-table :data="channelList" v-loading="channelLoading" style="width: 100%">
          <el-table-column prop="name" label="渠道名称" min-width="150" />
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ getChannelTypeLabel(row.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="config" label="配置信息" min-width="200">
            <template #default="{ row }">
              <span v-if="row.config && row.config.webhook" class="config-item">webhook: {{ row.config.webhook }}</span>
              <span v-else-if="row.config && row.config.recipients" class="config-item">接收人: {{ row.config.recipients }}</span>
              <span v-else-if="row.config && row.config.api_url" class="config-item">api: {{ row.config.api_url }}</span>
              <span v-else class="config-item">-</span>
            </template>
          </el-table-column>
          <el-table-column label="启用状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="handleEditChannel(row)">编辑</el-button>
              <el-button type="primary" link size="small" @click="handleTestChannel(row)">测试</el-button>
              <el-button type="danger" link size="small" @click="handleDeleteChannel(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab2: 通知规则 -->
      <el-tab-pane label="通知规则" name="rules">
        <div class="tab-header">
          <el-button type="primary" @click="handleAddRule">
            <el-icon><Plus /></el-icon> 添加规则
          </el-button>
        </div>
        <el-table :data="ruleList" v-loading="ruleLoading" style="width: 100%">
          <el-table-column prop="name" label="规则名称" min-width="150" />
          <el-table-column label="通知类型" min-width="150">
            <template #default="{ row }">
              <el-tag v-for="t in (row.notification_types || row.types || [])" :key="t" size="small" style="margin-right: 4px">{{ t }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="告警级别" width="120">
            <template #default="{ row }">
              <el-tag :type="getLevelType(row.level)" size="small">{{ row.level || '全部' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="启用状态" width="100">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" @change="handleToggleRule(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="handleEditRule(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="handleDeleteRule(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab3: 通知对象 -->
      <el-tab-pane label="通知对象" name="targets">
        <div class="tab-header">
          <el-button type="primary" @click="handleAddTarget">
            <el-icon><Plus /></el-icon> 添加对象
          </el-button>
        </div>
        <el-table :data="targetList" v-loading="targetLoading" style="width: 100%">
          <el-table-column prop="name" label="对象名称" min-width="150" />
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ getTargetTypeLabel(row.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="联系方式" min-width="200">
            <template #default="{ row }">
              <span v-if="row.contact && row.contact.email" class="config-item">email: {{ row.contact.email }}</span>
              <span v-else-if="row.contact && row.contact.phone" class="config-item">phone: {{ row.contact.phone }}</span>
              <span v-else-if="row.contact && row.contact.webhook_url" class="config-item">webhook: {{ row.contact.webhook_url }}</span>
              <span v-else class="config-item">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="rules" label="关联规则" min-width="150">
            <template #default="{ row }">
              <el-tag v-for="r in (row.rules || [])" :key="r" size="small" style="margin-right: 4px">{{ typeof r === 'object' ? r.name : r }}</el-tag>
              <span v-if="!(row.rules && row.rules.length)" class="config-item">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="handleEditTarget(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="handleDeleteTarget(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加/编辑渠道对话框 -->
    <el-dialog v-model="channelDialogVisible" :title="channelDialogTitle" width="600px">
      <el-form :model="channelForm" label-width="100px" :rules="channelRules" ref="channelFormRef">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="channelForm.name" placeholder="请输入渠道名称" />
        </el-form-item>
        <el-form-item label="渠道类型" prop="type">
          <el-select v-model="channelForm.type" placeholder="请选择渠道类型" style="width: 100%">
            <el-option v-for="t in channelTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="channelForm.enabled" />
        </el-form-item>
        <!-- 邮件配置 -->
        <template v-if="channelForm.type === 'email'">
          <el-form-item label="SMTP服务器" prop="config.smtp_host">
            <el-input v-model="channelForm.config.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item label="SMTP端口" prop="config.smtp_port">
            <el-input-number v-model="channelForm.config.smtp_port" :min="1" :max="65535" style="width: 100%" />
          </el-form-item>
          <el-form-item label="用户名" prop="config.username">
            <el-input v-model="channelForm.config.username" placeholder="发件人邮箱" />
          </el-form-item>
          <el-form-item label="密码" prop="config.password">
            <el-input v-model="channelForm.config.password" type="password" show-password placeholder="授权码或密码" />
          </el-form-item>
          <el-form-item label="收件人" prop="config.recipients">
            <el-select v-model="channelForm.config.recipients" multiple filterable allow-create placeholder="输入邮箱地址" style="width: 100%">
              <el-option v-for="e in channelForm.config.recipients" :key="e" :label="e" :value="e" />
            </el-select>
          </el-form-item>
        </template>
        <!-- 钉钉配置 -->
        <template v-else-if="channelForm.type === 'dingtalk'">
          <el-form-item label="Webhook" prop="config.webhook">
            <el-input v-model="channelForm.config.webhook" placeholder="钉钉群机器人的Webhook地址" />
          </el-form-item>
          <el-form-item label="Secret" prop="config.secret">
            <el-input v-model="channelForm.config.secret" placeholder="加签密钥（可选）" />
          </el-form-item>
        </template>
        <!-- 飞书配置 -->
        <template v-else-if="channelForm.type === 'feishu'">
          <el-form-item label="Webhook" prop="config.webhook">
            <el-input v-model="channelForm.config.webhook" placeholder="飞书群机器人的Webhook地址" />
          </el-form-item>
        </template>
        <!-- 企业微信配置 -->
        <template v-else-if="channelForm.type === 'wechat'">
          <el-form-item label="Webhook" prop="config.webhook">
            <el-input v-model="channelForm.config.webhook" placeholder="企业微信群机器人的Webhook地址" />
          </el-form-item>
        </template>
        <!-- Webhook配置 -->
        <template v-else-if="channelForm.type === 'webhook'">
          <el-form-item label="URL" prop="config.url">
            <el-input v-model="channelForm.config.url" placeholder="回调URL地址" />
          </el-form-item>
          <el-form-item label="Headers">
            <el-input v-model="channelForm.config.headers" type="textarea" :rows="2" placeholder='{"Authorization": "Bearer xxx"}' />
          </el-form-item>
        </template>
        <!-- 短信配置 -->
        <template v-else-if="channelForm.type === 'sms'">
          <el-form-item label="API地址" prop="config.api_url">
            <el-input v-model="channelForm.config.api_url" placeholder="短信网关API地址" />
          </el-form-item>
          <el-form-item label="AppKey">
            <el-input v-model="channelForm.config.app_key" placeholder="AppKey" />
          </el-form-item>
          <el-form-item label="AppSecret">
            <el-input v-model="channelForm.config.app_secret" type="password" show-password placeholder="AppSecret" />
          </el-form-item>
          <el-form-item label="签名">
            <el-input v-model="channelForm.config.signature" placeholder="短信签名" />
          </el-form-item>
          <el-form-item label="手机号" prop="config.recipients">
            <el-select v-model="channelForm.config.recipients" multiple filterable allow-create placeholder="输入手机号" style="width: 100%">
              <el-option v-for="p in channelForm.config.recipients" :key="p" :label="p" :value="p" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item label="描述">
          <el-input v-model="channelForm.description" type="textarea" :rows="2" placeholder="备注信息（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitChannelForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑规则对话框 -->
    <el-dialog v-model="ruleDialogVisible" :title="ruleDialogTitle" width="600px">
      <el-form :model="ruleForm" label-width="100px" :rules="ruleFormRules" ref="ruleFormRef">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="通知类型" prop="notification_types">
          <el-checkbox-group v-model="ruleForm.notification_types">
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="sms">短信</el-checkbox>
            <el-checkbox label="webhook">Webhook</el-checkbox>
            <el-checkbox label="dingtalk">钉钉</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="告警级别" prop="level">
          <el-select v-model="ruleForm.level" placeholder="请选择告警级别" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="Critical" value="critical" />
            <el-option label="Warning" value="warning" />
            <el-option label="Info" value="info" />
          </el-select>
        </el-form-item>
        <el-form-item label="通知渠道" prop="channel_ids">
          <el-select v-model="ruleForm.channel_ids" multiple placeholder="选择通知渠道" style="width: 100%">
            <el-option v-for="c in channelList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="ruleForm.enabled" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="ruleForm.description" type="textarea" :rows="2" placeholder="备注信息（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRuleForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑对象对话框 -->
    <el-dialog v-model="targetDialogVisible" :title="targetDialogTitle" width="600px">
      <el-form :model="targetForm" label-width="100px" :rules="targetFormRules" ref="targetFormRef">
        <el-form-item label="对象名称" prop="name">
          <el-input v-model="targetForm.name" placeholder="请输入对象名称" />
        </el-form-item>
        <el-form-item label="对象类型" prop="type">
          <el-select v-model="targetForm.type" placeholder="请选择对象类型" style="width: 100%">
            <el-option label="用户" value="user" />
            <el-option label="角色" value="role" />
            <el-option label="用户组" value="group" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-if="targetForm.type === 'user' || targetForm.type === 'role' || targetForm.type === 'group'" v-model="targetForm.contact.email" placeholder="邮箱地址" />
          <el-input v-if="targetForm.type === 'user'" v-model="targetForm.contact.phone" placeholder="手机号" style="margin-top: 8px" />
          <el-input v-if="targetForm.type === 'role' || targetForm.type === 'group'" v-model="targetForm.contact.webhook_url" placeholder="Webhook URL" style="margin-top: 8px" />
        </el-form-item>
        <el-form-item label="关联规则">
          <el-select v-model="targetForm.rule_ids" multiple placeholder="选择关联规则" style="width: 100%">
            <el-option v-for="r in ruleList" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="targetForm.description" type="textarea" :rows="2" placeholder="备注信息（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="targetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTargetForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, markRaw } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Message, Bell, ChatDotRound, Link, Iphone } from '@element-plus/icons-vue'
import { notification } from '@/api'

const activeTab = ref('channels')

// ========== 渠道相关 ==========
const channelLoading = ref(false)
const channelList = ref([])
const channelDialogVisible = ref(false)
const channelDialogTitle = ref('添加渠道')
const channelFormRef = ref(null)
const isChannelEdit = ref(false)

const defaultChannelForm = () => ({
  id: null,
  name: '',
  type: 'email',
  enabled: true,
  config: {
    smtp_host: '',
    smtp_port: 465,
    username: '',
    password: '',
    recipients: [],
    webhook: '',
    secret: '',
    url: '',
    headers: '',
    api_url: '',
    app_key: '',
    app_secret: '',
    signature: ''
  },
  description: ''
})

const channelForm = reactive(defaultChannelForm())

const channelRules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择渠道类型', trigger: 'change' }]
}

const channelTypes = [
  { value: 'email', label: '邮件', description: '通过SMTP发送邮件通知', color: '#409eff', icon: markRaw(Message) },
  { value: 'dingtalk', label: '钉钉', description: '推送到钉钉群机器人', color: '#1677ff', icon: markRaw(ChatDotRound) },
  { value: 'feishu', label: '飞书', description: '推送到飞书群机器人', color: '#00b42a', icon: markRaw(Bell) },
  { value: 'wechat', label: '企业微信', description: '推送到企业微信群机器人', color: '#00b42a', icon: markRaw(Bell) },
  { value: 'webhook', label: 'Webhook', description: '通用HTTP回调', color: '#165dff', icon: markRaw(Link) },
  { value: 'sms', label: '短信', description: '通过短信网关发送', color: '#ff7d00', icon: markRaw(Iphone) }
]

const getChannelTypeLabel = (type) => {
  const t = channelTypes.find(t => t.value === type)
  return t ? t.label : type
}

// ========== 规则相关 ==========
const ruleLoading = ref(false)
const ruleList = ref([])
const ruleDialogVisible = ref(false)
const ruleDialogTitle = ref('添加规则')
const ruleFormRef = ref(null)
const isRuleEdit = ref(false)

const defaultRuleForm = () => ({
  id: null,
  name: '',
  notification_types: [],
  level: '',
  channel_ids: [],
  enabled: true,
  description: ''
})

const ruleForm = reactive(defaultRuleForm())

const ruleFormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  notification_types: [{ required: true, message: '请选择通知类型', trigger: 'change' }]
}

const getLevelType = (level) => {
  const map = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[level] || 'info'
}

// ========== 对象相关 ==========
const targetLoading = ref(false)
const targetList = ref([])
const targetDialogVisible = ref(false)
const targetDialogTitle = ref('添加对象')
const targetFormRef = ref(null)
const isTargetEdit = ref(false)

const defaultTargetForm = () => ({
  id: null,
  name: '',
  type: 'user',
  contact: { email: '', phone: '', webhook_url: '' },
  rule_ids: [],
  description: ''
})

const targetForm = reactive(defaultTargetForm())

const targetFormRules = {
  name: [{ required: true, message: '请输入对象名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择对象类型', trigger: 'change' }]
}

const getTargetTypeLabel = (type) => {
  const map = { user: '用户', role: '角色', group: '用户组' }
  return map[type] || type
}

// ========== 生命周期 ==========
onMounted(() => {
  loadChannels()
  loadRules()
  loadTargets()
})

// ========== 渠道方法 ==========
const loadChannels = async () => {
  channelLoading.value = true
  try {
    const res = await notification.getChannels().catch(() => ({ channels: [], items: [] }))
    channelList.value = res.channels || res.items || []
  } catch (error) {
    console.error('Load channels error:', error)
  } finally {
    channelLoading.value = false
  }
}

const handleAddChannel = () => {
  Object.assign(channelForm, defaultChannelForm())
  channelDialogTitle.value = '添加渠道'
  isChannelEdit.value = false
  channelDialogVisible.value = true
}

const handleEditChannel = (row) => {
  Object.assign(channelForm, {
    id: row.id || row.channel_id,
    name: row.name,
    type: row.type,
    enabled: row.enabled !== false,
    config: {
      smtp_host: row.config?.smtp_host || '',
      smtp_port: row.config?.smtp_port || 465,
      username: row.config?.username || '',
      password: row.config?.password || '',
      recipients: row.config?.recipients || [],
      webhook: row.config?.webhook || '',
      secret: row.config?.secret || '',
      url: row.config?.url || '',
      headers: row.config?.headers || '',
      api_url: row.config?.api_url || '',
      app_key: row.config?.app_key || '',
      app_secret: row.config?.app_secret || '',
      signature: row.config?.signature || ''
    },
    description: row.description || ''
  })
  channelDialogTitle.value = '编辑渠道'
  isChannelEdit.value = true
  channelDialogVisible.value = true
}

const submitChannelForm = async () => {
  if (!channelForm.name) { ElMessage.warning('请输入渠道名称'); return }
  channelLoading.value = true
  try {
    const payload = {
      name: channelForm.name,
      type: channelForm.type,
      enabled: channelForm.enabled,
      config: channelForm.config,
      description: channelForm.description
    }
    if (isChannelEdit.value) {
      await notification.updateChannel(channelForm.id, payload)
      ElMessage.success('更新成功')
    } else {
      await notification.createChannel(payload)
      ElMessage.success('添加成功')
    }
    channelDialogVisible.value = false
    loadChannels()
  } catch (error) {
    console.error('Submit channel error:', error)
    ElMessage.error('操作失败')
  } finally {
    channelLoading.value = false
  }
}

const handleTestChannel = async (row) => {
  try {
    await notification.testChannel(row.id || row.channel_id)
    ElMessage.success('测试消息已发送，请检查是否收到')
  } catch (error) {
    ElMessage.error('测试发送失败')
  }
}

const handleDeleteChannel = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该通知渠道吗？', '删除确认', { type: 'warning' })
    await notification.deleteChannel(row.id || row.channel_id)
    ElMessage.success('删除成功')
    loadChannels()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

// ========== 规则方法 ==========
const loadRules = async () => {
  ruleLoading.value = true
  try {
    const res = await notification.getTargetRules().catch(() => ({ items: [] }))
    ruleList.value = res.items || res.rules || []
  } catch (error) {
    console.error('Load rules error:', error)
  } finally {
    ruleLoading.value = false
  }
}

const handleAddRule = () => {
  Object.assign(ruleForm, defaultRuleForm())
  ruleDialogTitle.value = '添加规则'
  isRuleEdit.value = false
  ruleDialogVisible.value = true
}

const handleEditRule = (row) => {
  Object.assign(ruleForm, {
    id: row.id,
    name: row.name,
    notification_types: row.notification_types || row.types || [],
    level: row.level || '',
    channel_ids: row.channel_ids || [],
    enabled: row.enabled !== false,
    description: row.description || ''
  })
  ruleDialogTitle.value = '编辑规则'
  isRuleEdit.value = true
  ruleDialogVisible.value = true
}

const submitRuleForm = async () => {
  if (!ruleForm.name) { ElMessage.warning('请输入规则名称'); return }
  if (!ruleForm.notification_types.length) { ElMessage.warning('请选择通知类型'); return }
  ruleLoading.value = true
  try {
    const payload = {
      name: ruleForm.name,
      notification_types: ruleForm.notification_types,
      level: ruleForm.level,
      channel_ids: ruleForm.channel_ids,
      enabled: ruleForm.enabled,
      description: ruleForm.description
    }
    if (isRuleEdit.value) {
      await notification.updateTargetRule(ruleForm.id, payload)
      ElMessage.success('更新成功')
    } else {
      await notification.createTargetRule(payload)
      ElMessage.success('添加成功')
    }
    ruleDialogVisible.value = false
    loadRules()
  } catch (error) {
    console.error('Submit rule error:', error)
    ElMessage.error('操作失败')
  } finally {
    ruleLoading.value = false
  }
}

const handleToggleRule = async (row) => {
  try {
    await notification.toggleTargetRule(row.id)
    ElMessage.success('状态已更新')
  } catch (error) {
    ElMessage.error('切换失败')
    row.enabled = !row.enabled
  }
}

const handleDeleteRule = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该通知规则吗？', '删除确认', { type: 'warning' })
    await notification.deleteTargetRule(row.id)
    ElMessage.success('删除成功')
    loadRules()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

// ========== 对象方法 ==========
const loadTargets = async () => {
  targetLoading.value = true
  try {
    const res = await notification.getTargets().catch(() => ({ items: [] }))
    targetList.value = res.items || res.targets || []
  } catch (error) {
    console.error('Load targets error:', error)
  } finally {
    targetLoading.value = false
  }
}

const handleAddTarget = () => {
  Object.assign(targetForm, defaultTargetForm())
  targetDialogTitle.value = '添加对象'
  isTargetEdit.value = false
  targetDialogVisible.value = true
}

const handleEditTarget = (row) => {
  Object.assign(targetForm, {
    id: row.id,
    name: row.name,
    type: row.type,
    contact: {
      email: row.contact?.email || '',
      phone: row.contact?.phone || '',
      webhook_url: row.contact?.webhook_url || ''
    },
    rule_ids: row.rule_ids || (row.rules || []).map(r => typeof r === 'object' ? r.id : r),
    description: row.description || ''
  })
  targetDialogTitle.value = '编辑对象'
  isTargetEdit.value = true
  targetDialogVisible.value = true
}

const submitTargetForm = async () => {
  if (!targetForm.name) { ElMessage.warning('请输入对象名称'); return }
  targetLoading.value = true
  try {
    const payload = {
      name: targetForm.name,
      type: targetForm.type,
      contact: targetForm.contact,
      rule_ids: targetForm.rule_ids,
      description: targetForm.description
    }
    if (isTargetEdit.value) {
      await notification.updateTarget(ruleForm.id, payload)
      ElMessage.success('更新成功')
    } else {
      await notification.createTarget(payload)
      ElMessage.success('添加成功')
    }
    targetDialogVisible.value = false
    loadTargets()
  } catch (error) {
    console.error('Submit target error:', error)
    ElMessage.error('操作失败')
  } finally {
    targetLoading.value = false
  }
}

const handleDeleteTarget = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该通知对象吗？', '删除确认', { type: 'warning' })
    await notification.deleteTarget(row.id)
    ElMessage.success('删除成功')
    loadTargets()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style lang="scss" scoped>
.notification-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 16px;
  }
}
.tab-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}
.config-item {
  font-size: 12px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
  display: inline-block;
}
</style>
