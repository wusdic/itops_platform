<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">通知配置</h1>
        <p class="page-subtitle">管理告警通知渠道和接收人</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加渠道
        </el-button>
      </div>
    </div>

    <!-- 通知类型卡片 -->
    <div class="channel-types">
      <div v-for="t in channelTypes" :key="t.value" class="channel-type-card">
        <el-icon :size="32" :color="t.color"><component :is="t.icon" /></el-icon>
        <div class="channel-type-info">
          <div class="channel-type-name">{{ t.label }}</div>
          <div class="channel-type-desc">{{ t.description }}</div>
        </div>
        <div class="channel-type-count">
          <el-tag size="small" type="info">{{ getCountByType(t.value) }}</el-tag>
        </div>
      </div>
    </div>

    <!-- 渠道列表 -->
    <div class="table-container">
      <el-table :data="channelList" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="渠道名称" min-width="150" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getTypeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="config" label="配置信息" min-width="200">
          <template #default="{ row }">
            <span v-if="row.config && row.config.webhook" class="config-item">webhook: {{ row.config.webhook }}</span>
            <span v-else-if="row.config && row.config.recipients" class="config-item">接收人: {{ row.config.recipients }}</span>
            <span v-else class="config-item">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="primary" link size="small" @click="handleTest(row)">测试</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加/编辑渠道对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入渠道名称" />
        </el-form-item>
        <el-form-item label="渠道类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择渠道类型" style="width: 100%">
            <el-option v-for="t in channelTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <!-- 邮件配置 -->
        <template v-if="form.type === 'email'">
          <el-form-item label="SMTP服务器" prop="smtp_host">
            <el-input v-model="form.config.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item label="SMTP端口" prop="smtp_port">
            <el-input-number v-model="form.config.smtp_port" :min="1" :max="65535" style="width: 100%" />
          </el-form-item>
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.config.username" placeholder="发件人邮箱" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.config.password" type="password" show-password placeholder="授权码或密码" />
          </el-form-item>
          <el-form-item label="收件人" prop="recipients">
            <el-select v-model="form.config.recipients" multiple filterable allow-create placeholder="输入邮箱地址" style="width: 100%">
              <el-option v-for="e in form.config.recipients" :key="e" :label="e" :value="e" />
            </el-select>
          </el-form-item>
        </template>
        <!-- 钉钉配置 -->
        <template v-else-if="form.type === 'dingtalk'">
          <el-form-item label="Webhook" prop="webhook">
            <el-input v-model="form.config.webhook" placeholder="钉钉群机器人的Webhook地址" />
          </el-form-item>
          <el-form-item label="Secret" prop="secret">
            <el-input v-model="form.config.secret" placeholder="加签密钥（可选）" />
          </el-form-item>
        </template>
        <!-- 飞书配置 -->
        <template v-else-if="form.type === 'feishu'">
          <el-form-item label="Webhook" prop="webhook">
            <el-input v-model="form.config.webhook" placeholder="飞书群机器人的Webhook地址" />
          </el-form-item>
        </template>
        <!-- 企业微信配置 -->
        <template v-else-if="form.type === 'wechat'">
          <el-form-item label="Webhook" prop="webhook">
            <el-input v-model="form.config.webhook" placeholder="企业微信群机器人的Webhook地址" />
          </el-form-item>
        </template>
        <!-- Slack配置 -->
        <template v-else-if="form.type === 'slack'">
          <el-form-item label="Webhook" prop="webhook">
            <el-input v-model="form.config.webhook" placeholder="Slack的Incoming Webhook URL" />
          </el-form-item>
        </template>
        <!-- Webhook配置 -->
        <template v-else-if="form.type === 'webhook'">
          <el-form-item label="URL" prop="url">
            <el-input v-model="form.config.url" placeholder="回调URL地址" />
          </el-form-item>
          <el-form-item label="Headers">
            <el-input v-model="form.config.headers" type="textarea" :rows="2" placeholder='{"Authorization": "Bearer xxx"}' />
          </el-form-item>
        </template>
        <!-- 短信配置 -->
        <template v-else-if="form.type === 'sms'">
          <el-form-item label="API地址" prop="api_url">
            <el-input v-model="form.config.api_url" placeholder="短信网关API地址" />
          </el-form-item>
          <el-form-item label="AppKey">
            <el-input v-model="form.config.app_key" placeholder="AppKey" />
          </el-form-item>
          <el-form-item label="AppSecret">
            <el-input v-model="form.config.app_secret" type="password" show-password placeholder="AppSecret" />
          </el-form-item>
          <el-form-item label="签名">
            <el-input v-model="form.config.signature" placeholder="短信签名" />
          </el-form-item>
          <el-form-item label="手机号" prop="recipients">
            <el-select v-model="form.config.recipients" multiple filterable allow-create placeholder="输入手机号" style="width: 100%">
              <el-option v-for="p in form.config.recipients" :key="p" :label="p" :value="p" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="备注信息（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, markRaw } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Message, Bell, ChatDotRound, Link, Iphone } from '@element-plus/icons-vue'
import { notification } from '@/api'

const loading = ref(false)
const channelList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('添加渠道')
const formRef = ref(null)
const isEdit = ref(false)

const defaultForm = () => ({
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

const form = reactive(defaultForm())

const rules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择渠道类型', trigger: 'change' }]
}

const channelTypes = [
  { value: 'email', label: '邮件', description: '通过SMTP发送邮件通知', color: '#409eff', icon: markRaw(Message) },
  { value: 'dingtalk', label: '钉钉', description: '推送到钉钉群机器人', color: '#1677ff', icon: markRaw(ChatDotRound) },
  { value: 'feishu', label: '飞书', description: '推送到飞书群机器人', color: '#00b42a', icon: markRaw(Bell) },
  { value: 'wechat', label: '企业微信', description: '推送到企业微信群机器人', color: '#00b42a', icon: markRaw(Bell) },
  { value: 'slack', label: 'Slack', description: '推送到Slack频道', color: '#165dff', icon: markRaw(Bell) },
  { value: 'webhook', label: 'Webhook', description: '通用HTTP回调', color: '#165dff', icon: markRaw(Link) },
  { value: 'sms', label: '短信', description: '通过短信网关发送', color: '#ff7d00', icon: markRaw(Iphone) }
]

const getTypeLabel = (type) => {
  const t = channelTypes.find(t => t.value === type)
  return t ? t.label : type
}

const getCountByType = (type) => {
  return channelList.value.filter(c => c.type === type).length
}

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await notification.getChannels().catch(() => ({ channels: [], total: 0 }))
    channelList.value = res.channels || res.items || []
  } catch (error) {
    console.error('Load channels error:', error)
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  Object.assign(form, defaultForm())
  dialogTitle.value = '添加渠道'
  isEdit.value = false
  dialogVisible.value = true
}

const handleEdit = (row) => {
  Object.assign(form, {
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
  dialogTitle.value = '编辑渠道'
  isEdit.value = true
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!form.name) { ElMessage.warning('请输入渠道名称'); return }
  loading.value = true
  try {
    const payload = {
      name: form.name,
      type: form.type,
      enabled: form.enabled,
      config: form.config,
      description: form.description
    }
    if (isEdit.value) {
      await notification.updateChannel(form.id, payload)
      ElMessage.success('更新成功')
    } else {
      await notification.createChannel(payload)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('Submit error:', error)
    ElMessage.error('操作失败')
  } finally {
    loading.value = false
  }
}

const handleTest = async (row) => {
  try {
    await notification.testChannel(row.id || row.channel_id)
    ElMessage.success('测试消息已发送，请检查是否收到')
  } catch (error) {
    ElMessage.error('测试发送失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该通知渠道吗？', '删除确认', { type: 'warning' })
    await notification.deleteChannel(row.id || row.channel_id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style lang="scss" scoped>
.channel-types {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.channel-type-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #f2f3f5;
}
.channel-type-info { flex: 1; }
.channel-type-name { font-size: 14px; font-weight: 500; color: #1d2129; }
.channel-type-desc { font-size: 12px; color: #86909c; margin-top: 4px; }
.config-item { font-size: 12px; color: #606266; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; display: inline-block; }
</style>
