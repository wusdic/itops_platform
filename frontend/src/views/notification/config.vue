<template>
  <div class="page-container">
    <n-card title="通知渠道配置" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加渠道
        </n-button>
      </template>
      <n-data-table :columns="columns" :data="channelList" :loading="loading" :pagination="false" :row-key="row => row.id" />
    </n-card>
    <n-card title="通知类型" :bordered="false" style="margin-top: 16px">
      <n-space vertical>
        <n-alert v-for="t in notificationTypes" :key="t.value" :type="getAlertType(t.value)" :title="t.label">{{ t.description }}</n-alert>
      </n-space>
    </n-card>
    <n-drawer v-model:show="drawerVisible" :width="500" placement="right">
      <n-drawer-content :title="editingChannel && editingChannel.id ? '编辑渠道' : '添加渠道'">
        <n-form :model="form" label-placement="left" label-width="100">
          <n-form-item label="渠道名称"><n-input v-model:value="form.name" placeholder="如：邮件通知" /></n-form-item>
          <n-form-item label="渠道类型"><n-select v-model:value="form.type" :options="typeOptions" placeholder="选择类型" /></n-form-item>
          <n-form-item label="配置JSON"><n-input v-model:value="form.config" type="textarea" :rows="6" placeholder='{"webhook": "https://..."}' /></n-form-item>
          <n-form-item label="启用状态"><n-switch v-model:value="form.enabled" /></n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="drawerVisible = false">取消</n-button>
            <n-button type="primary" @click="handleSave" :loading="saving">保存</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const channelList = ref([])
const notificationTypes = ref([])
const drawerVisible = ref(false)
const editingChannel = ref(null)
const form = reactive({ name: '', type: '', config: '{}', enabled: true })

const typeOptions = [
  { label: '邮件 (Email)', value: 'email' },
  { label: '钉钉 (DingTalk)', value: 'dingtalk' },
  { label: '飞书 (Feishu)', value: 'feishu' },
  { label: '企业微信', value: 'wechat_work' },
  { label: 'Webhook', value: 'webhook' },
]

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name', width: 150 },
  { title: '类型', key: 'type', width: 120, render: (row) => {
    const map = { email: '邮件', dingtalk: '钉钉', feishu: '飞书', wechat_work: '企业微信', webhook: 'Webhook' }
    return map[row.type] || row.type
  }},
  { title: '状态', key: 'enabled', width: 80, render: (row) => h('span', { style: row.enabled ? 'color:#18a058' : 'color:#999' }, row.enabled ? '启用' : '停用')},
  { title: '操作', key: 'actions', width: 120, render: (row) => h('div', { style: 'display:flex;gap:8px' }, [
    h('button', { style: 'background:none;border:none;color:#18a058;cursor:pointer;font-size:13px', onClick: () => handleEdit(row) }, '编辑'),
    h('button', { style: 'background:none;border:none;color:#d03050;cursor:pointer;font-size:13px', onClick: () => handleDelete(row.id) }, '删除')
  ])}
]

onMounted(() => { loadChannels(); loadTypes() })

async function loadChannels() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/notifications/channels', { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    channelList.value = data.items || []
  } catch (e) {
    message.error('加载渠道失败: ' + e.message)
    console.error('[notification/config] loadChannels error:', e)
    channelList.value = []
  } finally {
    loading.value = false
  }
}

async function loadTypes() {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/notifications/types', { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    notificationTypes.value = data.types || []
  } catch (e) {
    console.error('[notification/config] loadTypes error:', e)
  }
}

function getAlertType(type) {
  return { email: 'info', dingtalk: 'warning', feishu: 'success', wechat_work: 'info', webhook: 'default' }[type] || 'default'
}

function handleAdd() {
  editingChannel.value = null
  Object.assign(form, { name: '', type: '', config: '{}', enabled: true })
  drawerVisible.value = true
}

function handleEdit(row) {
  editingChannel.value = row
  Object.assign(form, { name: row.name, type: row.type, config: JSON.stringify(row.config || {}), enabled: row.enabled })
  drawerVisible.value = true
}

async function handleSave() {
  if (!form.name || !form.type) { message.warning('请填写名称和类型'); return }
  saving.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const method = editingChannel.value ? 'PUT' : 'POST'
    const url = editingChannel.value ? `/api/v1/notifications/channels/${editingChannel.value.id}` : '/api/v1/notifications/channels'
    const res = await fetch(url, { method, headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ name: form.name, type: form.type, config: JSON.parse(form.config || '{}'), enabled: form.enabled }) })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success(editingChannel.value ? '更新成功' : '添加成功')
    drawerVisible.value = false
    loadChannels()
  } catch (e) {
    message.error('保存失败: ' + e.message)
    console.error('[notification/config] handleSave error:', e)
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/notifications/channels/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success('删除成功')
    loadChannels()
  } catch (e) {
    message.error('删除失败: ' + e.message)
    console.error('[notification/config] handleDelete error:', e)
  }
}
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
