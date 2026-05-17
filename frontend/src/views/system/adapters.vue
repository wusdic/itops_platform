<template>
  <div class="adapter-page">
    <n-tabs type="line" animated v-model:value="activeTab">
      <n-tab-pane name="adapters" tab="协议适配器">
        <n-card title="协议适配器模板" class="mb-4">
          <template #header-extra>
            <n-button type="primary" @click="openAddModal">
              <template #icon><n-icon><AddOutline /></n-icon></template>
              新建适配器
            </n-button>
          </template>
          <n-data-table
            :columns="adapterColumns"
            :data="adapterList"
            :loading="adapterLoading"
            :pagination="{ pageSize: 20 }"
            :row-key="row => row.id"
            striped
          />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="device-config" tab="设备协议配置">
        <n-card title="设备协议配置" class="mb-4">
          <template #header-extra>
            <n-button @click="loadDeviceProtocols" :loading="protocolLoading">
              <template #icon><n-icon><RefreshOutline /></n-icon></template>
              刷新
            </n-button>
          </template>
          <n-space vertical :size="12">
            <n-space>
              <n-select
                v-model:value="selectedDeviceId"
                :options="deviceOptions"
                placeholder="选择设备"
                style="width: 300px"
                filterable
                @update:value="onDeviceChange"
              />
              <n-button @click="testDeviceProtocol" :loading="testing" :disabled="!selectedDeviceId">测试连接</n-button>
            </n-space>
            <n-data-table
              :columns="protocolColumns"
              :data="deviceProtocols"
              :loading="protocolLoading"
              :row-key="row => row.protocol_type"
              striped
            />
          </n-space>
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- 新建/编辑适配器弹窗 -->
    <n-modal v-model:show="showAddModal" preset="card" :title="editingId ? '编辑适配器' : '新建适配器'" style="width: 600px">
      <n-form label-placement="left" label-width="120">
        <n-form-item label="协议类型">
          <n-select
            v-model:value="form.protocol_type"
            :options="protocolOptions"
            placeholder="选择协议"
            :disabled="!!editingId"
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="模板名称">
          <n-input v-model:value="form.name" placeholder="如: MySQL标准模板" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" type="textarea" placeholder="模板描述" />
        </n-form-item>

        <n-divider>默认配置</n-divider>

        <template v-if="form.protocol_type === 'snmp'">
          <n-form-item label="端口">
            <n-input-number v-model:value="form.default_config.port" :min="1" :max="65535" />
          </n-form-item>
          <n-form-item label="SNMP版本">
            <n-select v-model:value="form.default_config.version" :options="snmpVersionOptions" style="width:100%" />
          </n-form-item>
          <n-form-item label="Community">
            <n-input v-model:value="form.default_config.community" placeholder="public" />
          </n-form-item>
        </template>

        <template v-if="form.protocol_type === 'ssh'">
          <n-form-item label="端口">
            <n-input-number v-model:value="form.default_config.port" :min="1" :max="65535" />
          </n-form-item>
          <n-form-item label="用户名">
            <n-input v-model:value="form.default_config.username" placeholder="root" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.default_config.password" type="password" placeholder="留空使用密钥" />
          </n-form-item>
        </template>

        <template v-if="form.protocol_type === 'http' || form.protocol_type === 'zabbix' || form.protocol_type === 'prometheus' || form.protocol_type === 'redfish'">
          <n-form-item label="端口">
            <n-input-number v-model:value="form.default_config.port" :min="1" :max="65535" />
          </n-form-item>
          <n-form-item label="用户名">
            <n-input v-model:value="form.default_config.username" placeholder="admin" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.default_config.password" type="password" placeholder="密码" />
          </n-form-item>
        </template>

        <template v-if="form.protocol_type === 'mysql' || form.protocol_type === 'postgres'">
          <n-form-item label="端口">
            <n-input-number v-model:value="form.default_config.port" :min="1" :max="65535" />
          </n-form-item>
          <n-form-item label="用户名">
            <n-input v-model:value="form.default_config.username" placeholder="root" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.default_config.password" type="password" />
          </n-form-item>
        </template>

        <template v-if="form.protocol_type === 'redis'">
          <n-form-item label="端口">
            <n-input-number v-model:value="form.default_config.port" :min="1" :max="65535" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.default_config.password" type="password" placeholder="无密码则留空" />
          </n-form-item>
        </template>

        <template v-if="form.protocol_type === 'rabbitmq'">
          <n-form-item label="端口">
            <n-input-number v-model:value="form.default_config.port" :min="1" :max="65535" />
          </n-form-item>
          <n-form-item label="用户名">
            <n-input v-model:value="form.default_config.username" placeholder="guest" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.default_config.password" type="password" placeholder="guest" />
          </n-form-item>
        </template>

        <template v-if="form.protocol_type === 'vmware'">
          <n-form-item label="端口">
            <n-input-number v-model:value="form.default_config.port" :min="1" :max="65535" />
          </n-form-item>
          <n-form-item label="用户名">
            <n-input v-model:value="form.default_config.user" placeholder="administrator@vsphere.local" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.default_config.password" type="password" />
          </n-form-item>
        </template>

        <template v-if="form.protocol_type === 'browser'">
          <n-form-item label="端口">
            <n-input-number v-model:value="form.default_config.port" :min="1" :max="65535" />
          </n-form-item>
          <n-form-item label="用户名">
            <n-input v-model:value="form.default_config.username" placeholder="admin" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.default_config.password" type="password" />
          </n-form-item>
        </template>

        <n-form-item label="超时(秒)">
          <n-input-number v-model:value="form.default_config.timeout" :min="5" :max="300" />
        </n-form-item>

        <n-form-item label="启用">
          <n-switch v-model:value="form.enabled" />
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" @click="saveAdapter" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import { AddOutline, RefreshOutline } from '@vicons/ionicons5'

const message = useMessage()
const activeTab = ref('adapters')
const adapterLoading = ref(false)
const protocolLoading = ref(false)
const saving = ref(false)
const testing = ref(false)
const showAddModal = ref(false)
const editingId = ref(null)

const adapterList = ref([])
const deviceProtocols = ref([])
const selectedDeviceId = ref(null)
const deviceOptions = ref([])

const snmpVersionOptions = [
  { label: 'v1', value: 'v1' },
  { label: 'v2c', value: 'v2c' },
  { label: 'v3', value: 'v3' },
]

const protocolOptions = [
  { label: 'SNMP', value: 'snmp' },
  { label: 'SSH', value: 'ssh' },
  { label: 'HTTP', value: 'http' },
  { label: 'WinRM', value: 'winrm' },
  { label: 'IPMI', value: 'ipmi' },
  { label: 'Kubernetes', value: 'kubernetes' },
  { label: 'Docker', value: 'docker' },
  { label: 'Zabbix', value: 'zabbix' },
  { label: 'Prometheus', value: 'prometheus' },
  { label: 'Browser', value: 'browser' },
  { label: 'Redfish', value: 'redfish' },
  { label: 'Syslog', value: 'syslog' },
  { label: 'Telnet', value: 'telnet' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgres' },
  { label: 'Redis', value: 'redis' },
  { label: 'RabbitMQ', value: 'rabbitmq' },
  { label: 'Kafka', value: 'kafka' },
  { label: 'Elasticsearch', value: 'elasticsearch' },
  { label: 'VMware', value: 'vmware' },
]

const emptyForm = () => ({
  protocol_type: '',
  name: '',
  description: '',
  default_config: { port: 22, timeout: 30 },
  enabled: true,
})
const form = reactive(emptyForm())

// ==================== 适配器管理 ====================
const loadAdapters = async () => {
  adapterLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch('/api/v1/admin/adapters', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('加载失败')
    const data = await res.json()
    adapterList.value = data.items || []
  } catch (e) {
    message.error('加载适配器失败: ' + e.message)
  } finally {
    adapterLoading.value = false
  }
}

const openAddModal = () => {
  editingId.value = null
  Object.assign(form, emptyForm())
  showAddModal.value = true
}

const editAdapter = (row) => {
  editingId.value = row.id
  Object.assign(form, {
    protocol_type: row.protocol_type,
    name: row.name,
    description: row.description || '',
    default_config: { ...row.default_config },
    enabled: row.enabled,
  })
  showAddModal.value = true
}

const saveAdapter = async () => {
  if (!form.protocol_type || !form.name) {
    message.warning('请填写协议类型和模板名称')
    return
  }
  saving.value = true
  try {
    const token = localStorage.getItem('token')
    const url = editingId.value
      ? `/api/v1/admin/adapters/${editingId.value}`
      : '/api/v1/admin/adapters'
    const method = editingId.value ? 'PUT' : 'POST'

    const res = await fetch(url, {
      method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...form }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '保存失败')
    }
    message.success('保存成功')
    showAddModal.value = false
    editingId.value = null
    loadAdapters()
  } catch (e) {
    message.error(e.message)
  } finally {
    saving.value = false
  }
}

const deleteAdapter = async (row) => {
  if (!confirm('确定删除适配器「' + row.name + '」？')) return
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/v1/admin/adapters/${row.id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('删除失败')
    message.success('删除成功')
    loadAdapters()
  } catch (e) {
    message.error(e.message)
  }
}

const adapterColumns = [
  {
    title: '协议',
    key: 'protocol_type',
    width: 120,
    render(row) {
      const colors = {
        snmp: 'info', ssh: 'success', http: 'warning', mysql: 'error',
        redis: 'info', postgres: 'success', vmware: 'warning', kafka: 'error',
      }
      return h('n-tag', { type: colors[row.protocol_type] || 'default', size: 'small' },
        { default: () => row.protocol_type.toUpperCase() })
    }
  },
  { title: '模板名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '默认端口', key: 'default_config.port', width: 100 },
  {
    title: '状态',
    key: 'enabled',
    width: 80,
    render(row) {
      return h('n-tag', { type: row.enabled ? 'success' : 'default', size: 'small' },
        { default: () => row.enabled ? '启用' : '禁用' })
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right',
    render(row) {
      return h('n-space', { size: 8 }, {
        default: () => [
          h('n-button', { size: 'small', type: 'primary', onClick: () => editAdapter(row) },
            { default: () => '编辑' }),
          h('n-button', { size: 'small', type: 'error', onClick: () => deleteAdapter(row) },
            { default: () => '删除' }),
        ]
      })
    }
  },
]

// ==================== 设备协议配置 ====================
const loadDevices = async () => {
  try {
    const token = localStorage.getItem('token')
    const res = await fetch('/api/v1/assets/device?page_size=100', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) return
    const data = await res.json()
    deviceOptions.value = (data.items || []).map(d => ({
      label: d.name + ' (' + d.ip_address + ')',
      value: d.id,
    }))
  } catch (e) {
    console.error('load devices error:', e)
  }
}

const onDeviceChange = async (deviceId) => {
  selectedDeviceId.value = deviceId
  await loadDeviceProtocols()
}

const loadDeviceProtocols = async () => {
  if (!selectedDeviceId.value) {
    deviceProtocols.value = []
    return
  }
  protocolLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch('/api/v1/admin/adapters/device/' + selectedDeviceId.value + '/protocols', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error()
    const data = await res.json()
    deviceProtocols.value = data.items || []
  } catch (e) {
    message.error('加载设备协议失败')
  } finally {
    protocolLoading.value = false
  }
}

const testDeviceProtocol = async () => {
  if (!selectedDeviceId.value) {
    message.warning('请先选择设备')
    return
  }
  testing.value = true
  try {
    const token = localStorage.getItem('token')
    const configured = deviceProtocols.value.find(p => p.enabled && p.adapter_template_id)
    const protocolType = configured ? configured.protocol_type : 'snmp'

    const res = await fetch('/api/v1/admin/adapters/device/' + selectedDeviceId.value + '/protocols/' + protocolType + '/test', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    })
    const data = await res.json()
    if (data.success) {
      message.success('连接成功: ' + data.message)
    } else {
      message.warning('连接失败: ' + data.message)
    }
  } catch (e) {
    message.error('测试失败')
  } finally {
    testing.value = false
  }
}

const updateDeviceProtocol = async (row, field, value) => {
  row[field] = value
  try {
    const token = localStorage.getItem('token')
    const payload = {
      device_id: selectedDeviceId.value,
      protocol_type: row.protocol_type,
      adapter_template_id: row.adapter_template_id || null,
      overrides: row.overrides || {},
      enabled: row.enabled,
    }

    const res = await fetch('/api/v1/admin/adapters/device/' + selectedDeviceId.value + '/protocols', {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify([payload]),
    })
    if (!res.ok) throw new Error()
    message.success('保存成功')
  } catch (e) {
    message.error('保存失败')
  }
}

const protocolColumns = [
  {
    title: '协议',
    key: 'protocol_type',
    width: 120,
    render(row) {
      const colors = {
        snmp: 'info', ssh: 'success', http: 'warning', mysql: 'error',
        redis: 'info', postgres: 'success', vmware: 'warning',
      }
      return h('n-tag', { type: colors[row.protocol_type] || 'default', size: 'small' },
        { default: () => row.protocol_type.toUpperCase() })
    }
  },
  {
    title: '适配器模板',
    key: 'adapter_template_id',
    width: 200,
    render(row) {
      const opts = adapterList.value
        .filter(a => a.protocol_type === row.protocol_type && a.enabled)
        .map(a => ({ label: a.name, value: a.id }))

      if (!opts.length) return h('span', { style: 'color:#999' }, '无可用模板')

      return h('n-select', {
        value: row.adapter_template_id,
        options: opts,
        size: 'small',
        style: 'width:180px',
        placeholder: '选择模板',
        onUpdateValue: (v) => updateDeviceProtocol(row, 'adapter_template_id', v),
        clearable: true,
      })
    }
  },
  {
    title: '覆盖参数(JSON)',
    key: 'overrides',
    ellipsis: { tooltip: true },
    render(row) {
      const json = JSON.stringify(row.overrides || {})
      return h('n-input', {
        value: json,
        size: 'small',
        placeholder: '{}',
        style: 'width:200px',
        onUpdateValue: (v) => {
          try { row.overrides = JSON.parse(v) } catch {}
        },
        onBlur: () => updateDeviceProtocol(row, 'overrides', row.overrides),
      })
    }
  },
  {
    title: '启用',
    key: 'enabled',
    width: 80,
    render(row) {
      return h('n-switch', {
        value: row.enabled,
        size: 'small',
        onUpdateValue: (v) => updateDeviceProtocol(row, 'enabled', v),
      })
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      if (!row.adapter_template_id && (!row.overrides || Object.keys(row.overrides).length === 0)) {
        return h('n-tag', { type: 'default', size: 'small' }, { default: () => '未配置' })
      }
      return h('n-tag', { type: row.enabled ? 'success' : 'warning', size: 'small' },
        { default: () => row.enabled ? '已配置' : '已禁用' })
    }
  },
]

onMounted(() => {
  loadAdapters()
  loadDevices()
})
</script>

<style scoped>
.adapter-page { padding: 16px; }
.mb-4 { margin-bottom: 16px; }
</style>
