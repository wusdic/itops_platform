<template>
  <div>
    <div class="page-header">
      <h2>通知渠道</h2>
      <n-button type="primary" @click="openCreate">
        <template #icon><n-icon><AddOutline /></n-icon></template>
        新建渠道
      </n-button>
    </div>

    <n-card :bordered="false">
      <n-data-table
        :columns="columns"
        :data="channels"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 创建/编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card"
      :title="isEdit ? '编辑渠道' : '新建渠道'"
      style="width: 560px" :bordered="false">
      <n-form :model="form" label-placement="left" label-width="90">
        <n-form-item label="渠道名称" required>
          <n-input v-model:value="form.name" placeholder="渠道名称" />
        </n-form-item>
        <n-form-item label="类型" required>
          <n-select v-model:value="form.type" :options="typeOptions" placeholder="选择类型" />
        </n-form-item>

        <!-- 邮件配置 -->
        <template v-if="form.type === 'email'">
          <n-form-item label="SMTP服务器">
            <n-input v-model:value="form.config.smtp_host" placeholder="smtp.example.com" />
          </n-form-item>
          <n-form-item label="端口">
            <n-input-number v-model:value="form.config.smtp_port" :min="1" :max="65535"
              style="width: 100%" />
          </n-form-item>
          <n-form-item label="发件人">
            <n-input v-model:value="form.config.from_email" placeholder="noreply@example.com" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.config.password" type="password"
              placeholder="SMTP密码" show-password-on="click" />
          </n-form-item>
        </template>

        <!-- 钉钉配置 -->
        <template v-if="form.type === 'dingtalk'">
          <n-form-item label="Webhook URL">
            <n-input v-model:value="form.config.webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
          </n-form-item>
          <n-form-item label="密钥">
            <n-input v-model:value="form.config.secret" placeholder="签名密钥（可选）"
              show-password-on="click" />
          </n-form-item>
        </template>

        <!-- 飞书配置 -->
        <template v-if="form.type === 'feishu'">
          <n-form-item label="Webhook URL">
            <n-input v-model:value="form.config.webhook_url" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
          </n-form-item>
        </template>

        <!-- 企微配置 -->
        <template v-if="form.type === 'wecom'">
          <n-form-item label="Webhook URL">
            <n-input v-model:value="form.config.webhook_url" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
          </n-form-item>
        </template>

        <!-- 站内信不需要额外配置 -->

        <n-form-item label="描述">
          <n-input v-model:value="form.description" placeholder="渠道描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="handleSave" :loading="saving">
            {{ isEdit ? '保存' : '创建' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { useMessage, useDialog, NButton, NSpace, NIcon, NTag } from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline, CheckmarkCircleOutline } from '@vicons/ionicons5'
import { getChannels, createChannel, updateChannel, deleteChannel, testChannel } from '@/api/notification'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const saving = ref(false)
const channels = ref([])
const pagination = ref({ page: 1, pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] })

const typeOptions = [
  { label: '邮件', value: 'email' },
  { label: '钉钉', value: 'dingtalk' },
  { label: '飞书', value: 'feishu' },
  { label: '企微', value: 'wecom' },
  { label: '站内信', value: 'in_app' }
]

const typeIcons = {
  email: '📧', dingtalk: '📌', feishu: '🪶', wecom: '💬', in_app: '🔔'
}

const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = ref({
  name: '', type: 'email',
  config: { smtp_host: '', smtp_port: 465, from_email: '', password: '', webhook_url: '', secret: '' },
  description: ''
})

const columns = ref([
  { title: 'ID', key: 'id', width: 80 },
  {
    title: '渠道名称', key: 'name',
    render: row => `${typeIcons[row.type] || ''} ${row.name}`
  },
  {
    title: '类型', key: 'type', width: 100,
    render: row => {
      const opt = typeOptions.find(o => o.value === row.type)
      return h(NTag, { size: 'small' }, { default: () => opt?.label || row.type })
    }
  },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'enabled', width: 80,
    render: row => h(NTag, { type: row.enabled !== false ? 'success' : 'default', size: 'small' },
      { default: () => row.enabled !== false ? '启用' : '禁用' })
  },
  {
    title: '创建时间', key: 'created_at', width: 180,
    render: row => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 260, fixed: 'right',
    render: row => h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', type: 'info', onClick: () => handleTest(row.id) },
          { default: () => '测试', icon: () => h(NIcon, null, { default: () => h(CheckmarkCircleOutline) }) }),
        h(NButton, { size: 'small', onClick: () => openEdit(row) },
          { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) },
          { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) })
      ]
    })
  }
])

async function loadChannels() {
  loading.value = true
  try {
    const res = await getChannels()
    const data = res.data || {}
    channels.value = data.items || data.channels || data || []
  } catch (e) {
    console.error('Load channels error:', e)
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  form.value = {
    name: '', type: 'email',
    config: { smtp_host: '', smtp_port: 465, from_email: '', password: '', webhook_url: '', secret: '' },
    description: ''
  }
  showModal.value = true
}

function openEdit(row) {
  isEdit.value = true
  editId.value = row.id
  form.value = {
    name: row.name,
    type: row.type || 'email',
    config: row.config || { smtp_host: '', smtp_port: 465, from_email: '', password: '', webhook_url: '', secret: '' },
    description: row.description || ''
  }
  showModal.value = true
}

async function handleSave() {
  if (!form.value.name || !form.value.type) {
    message.warning('请填写必填项')
    return false
  }
  saving.value = true
  try {
    const payload = { ...form.value }
    if (isEdit.value) {
      await updateChannel(editId.value, payload)
      message.success('渠道已更新')
    } else {
      await createChannel(payload)
      message.success('渠道已创建')
    }
    showModal.value = false
    await loadChannels()
  } catch (e) {
    message.error('操作失败')
    return false
  } finally {
    saving.value = false
  }
}

async function handleTest(id) {
  try {
    message.loading('正在测试渠道...', { key: 'test', duration: 0 })
    await testChannel(id)
    message.success('测试消息发送成功', { key: 'test' })
  } catch (e) {
    message.error('测试失败: ' + (e.response?.data?.message || e.message), { key: 'test' })
  }
}

function handleDelete(id) {
  dialog.warning({
    title: '确认删除', content: '确定删除此渠道吗？',
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteChannel(id)
        message.success('已删除')
        await loadChannels()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(() => {
  loadChannels()
})
</script>
