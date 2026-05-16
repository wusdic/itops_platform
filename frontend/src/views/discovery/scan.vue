<template>
  <div>
    <div class="page-header"><h2>设备扫描</h2></div>

    <n-tabs type="line" v-model:value="activeTab">
      <!-- IP扫描 -->
      <n-tab-pane name="ip" tab="IP扫描">
        <n-card :bordered="false" style="margin-top:16px" title="IP段扫描">
          <n-form ref="ipFormRef" :model="ipForm" :rules="ipFormRules" label-placement="left" label-width="120">
            <n-form-item label="扫描名称">
              <n-input v-model:value="ipForm.name" placeholder="请输入扫描名称" />
            </n-form-item>
            <n-form-item label="IP范围" path="ip_range">
              <n-input v-model:value="ipForm.ip_range" placeholder="如: 192.168.1.1-192.168.1.254" />
            </n-form-item>
            <n-form-item label="子网掩码">
              <n-select v-model:value="ipForm.subnet_mask" :options="subnetOptions" placeholder="选择子网掩码" clearable />
            </n-form-item>
            <n-form-item label="端口范围">
              <n-input v-model:value="ipForm.ports" placeholder="如: 22,80,443 或 1-65535" />
            </n-form-item>
            <n-form-item label="超时(秒)">
              <n-input-number v-model:value="ipForm.timeout" :min="1" :max="60" style="width:120px" />
            </n-form-item>
          </n-form>
          <template #header-extra>
            <n-button type="primary" :loading="ipScanning" @click="handleIpScan">
              <template #icon><n-icon><ScanOutline /></n-icon></template>
              开始扫描
            </n-button>
          </template>

          <!-- IP扫描进度 -->
          <div v-if="ipScanning" style="margin-top:16px">
            <n-progress type="line" :percentage="ipProgress" :show-indicator="false" />
            <p style="color:#999;font-size:12px;margin-top:8px">扫描进行中... 请勿关闭页面</p>
          </div>
        </n-card>
      </n-tab-pane>

      <!-- SNMP扫描 -->
      <n-tab-pane name="snmp" tab="SNMP扫描">
        <n-card :bordered="false" style="margin-top:16px" title="SNMP扫描">
          <n-form ref="snmpFormRef" :model="snmpForm" :rules="snmpFormRules" label-placement="left" label-width="120">
            <n-form-item label="扫描名称">
              <n-input v-model:value="snmpForm.name" placeholder="请输入扫描名称" />
            </n-form-item>
            <n-form-item label="IP范围" path="ip_range">
              <n-input v-model:value="snmpForm.ip_range" placeholder="如: 192.168.1.1-192.168.1.254" />
            </n-form-item>
            <n-form-item label="Community" path="community">
              <n-input v-model:value="snmpForm.community" placeholder="如: public" />
            </n-form-item>
            <n-form-item label="SNMP版本">
              <n-select v-model:value="snmpForm.version" :options="snmpVersionOptions" />
            </n-form-item>
            <n-form-item label="超时(秒)">
              <n-input-number v-model:value="snmpForm.timeout" :min="1" :max="60" style="width:120px" />
            </n-form-item>
          </n-form>
          <template #header-extra>
            <n-button type="primary" :loading="snmpScanning" @click="handleSnmpScan">
              <template #icon><n-icon><ScanOutline /></n-icon></template>
              开始扫描
            </n-button>
          </template>

          <!-- SNMP扫描进度 -->
          <div v-if="snmpScanning" style="margin-top:16px">
            <n-progress type="line" :percentage="snmpProgress" :show-indicator="false" />
            <p style="color:#999;font-size:12px;margin-top:8px">SNMP扫描进行中... 请勿关闭页面</p>
          </div>
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { ScanOutline } from '@vicons/ionicons5'
import { startIpScan, startSnmpScan } from '@/api/discovery'

const router = useRouter()
const message = useMessage()

const activeTab = ref('ip')

// IP扫描
const ipFormRef = ref(null)
const ipScanning = ref(false)
const ipProgress = ref(0)
const ipForm = reactive({
  name: '',
  ip_range: '',
  subnet_mask: null,
  ports: '',
  timeout: 5
})
const ipFormRules = { ip_range: { required: true, message: '请输入IP范围', trigger: 'blur' } }

const subnetOptions = [
  { label: '/8 (255.0.0.0)', value: '/8' },
  { label: '/16 (255.255.0.0)', value: '/16' },
  { label: '/24 (255.255.255.0)', value: '/24' },
  { label: '/25 (255.255.255.128)', value: '/25' }
]

// SNMP扫描
const snmpFormRef = ref(null)
const snmpScanning = ref(false)
const snmpProgress = ref(0)
const snmpForm = reactive({
  name: '',
  ip_range: '',
  community: 'public',
  version: 'v2c',
  timeout: 5
})
const snmpFormRules = {
  ip_range: { required: true, message: '请输入IP范围', trigger: 'blur' },
  community: { required: true, message: '请输入Community', trigger: 'blur' }
}

const snmpVersionOptions = [
  { label: 'v1', value: 'v1' },
  { label: 'v2c', value: 'v2c' },
  { label: 'v3', value: 'v3' }
]

async function handleIpScan() {
  try {
    await ipFormRef.value?.validate()
    ipScanning.value = true
    ipProgress.value = 0

    const res = await startIpScan(ipForm)
    const taskId = res.data?.task_id || res.task_id

    message.success('IP扫描已启动')

    // 模拟进度
    const timer = setInterval(() => {
      ipProgress.value = Math.min(ipProgress.value + Math.random() * 15, 95)
    }, 2000)

    setTimeout(() => {
      clearInterval(timer)
      ipProgress.value = 100
      ipScanning.value = false
      message.success('IP扫描完成')
      router.push('/discovery/results')
    }, 15000)
  } catch (e) {
    if (e.errors) return
    message.error('启动扫描失败')
    console.error(e)
    ipScanning.value = false
  }
}

async function handleSnmpScan() {
  try {
    await snmpFormRef.value?.validate()
    snmpScanning.value = true
    snmpProgress.value = 0

    await startSnmpScan(snmpForm)
    message.success('SNMP扫描已启动')

    const timer = setInterval(() => {
      snmpProgress.value = Math.min(snmpProgress.value + Math.random() * 15, 95)
    }, 2000)

    setTimeout(() => {
      clearInterval(timer)
      snmpProgress.value = 100
      snmpScanning.value = false
      message.success('SNMP扫描完成')
      router.push('/discovery/results')
    }, 15000)
  } catch (e) {
    if (e.errors) return
    message.error('启动扫描失败')
    console.error(e)
    snmpScanning.value = false
  }
}
</script>
