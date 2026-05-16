<template>
  <div>
    <div class="page-header"><h2>系统配置</h2><n-button @click="loadSystemInfo">刷新</n-button></div>
    <n-grid cols="2 s:1" :x-gap="16" :y-gap="16">
      <n-gi><n-card title="系统信息" :bordered="false">
        <n-descriptions :column="1" bordered>
          <n-descriptions-item label="版本">{{ info.version || '-' }}</n-descriptions-item>
          <n-descriptions-item label="运行时间">{{ info.uptime || '-' }}</n-descriptions-item>
          <n-descriptions-item label="环境">{{ info.environment || '-' }}</n-descriptions-item>
          <n-descriptions-item label="Python版本">{{ info.python_version || '-' }}</n-descriptions-item>
        </n-descriptions>
      </n-card></n-gi>
      <n-gi><n-card title="系统资源" :bordered="false">
        <div style="margin-bottom:16px"><span>CPU</span><n-progress type="line" :percentage="metrics.cpu || 0" /></div>
        <div style="margin-bottom:16px"><span>内存</span><n-progress type="line" :percentage="metrics.memory || 0" /></div>
        <div><span>磁盘</span><n-progress type="line" :percentage="metrics.disk || 0" /></div>
      </n-card></n-gi>
      <n-gi><n-card title="系统配置" :bordered="false">
        <n-form v-for="(v,k) in configs" :key="k" inline style="margin-bottom:8px">
          <n-form-item :label="k"><n-input v-model:value="configs[k]" style="width:200px" /></n-form-item>
          <n-button size="small" type="primary" @click="saveConfig(k)">保存</n-button>
        </n-form>
        <n-empty v-if="!configs||Object.keys(configs).length===0" description="暂无配置" />
      </n-card></n-gi>
      <n-gi><n-card title="操作" :bordered="false">
        <n-space><n-button type="warning" @click="doClearCache">清空缓存</n-button><n-button type="info" @click="loadHealth">健康检查</n-button></n-space>
        <n-alert v-if="health" :type="health.status==='healthy'?'success':'error'" style="margin-top:16px">{{ JSON.stringify(health) }}</n-alert>
      </n-card></n-gi>
    </n-grid>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import { getSystemInfo, getSystemMetrics, getSystemConfig, updateSystemConfig, clearCache as clearCacheApi, systemHealthCheck } from '@/api/system'

const message = useMessage()
const info = ref({}), metrics = ref({}), configs = ref({}), health = ref(null)

async function loadSystemInfo() {
  try {
    const [i, m, c] = await Promise.allSettled([getSystemInfo(), getSystemMetrics(), getSystemConfig()])
    if (i.status === 'fulfilled') info.value = i.value.data || {}
    if (m.status === 'fulfilled') metrics.value = m.value.data || {}
    if (c.status === 'fulfilled') configs.value = c.value.data || {}
  } catch {}
}

async function saveConfig(key) {
  try { await updateSystemConfig(key, { value: configs.value[key] }); message.success('保存成功') } catch { message.error('保存失败') }
}

async function doClearCache() { try { await clearCacheApi(); message.success('缓存已清空') } catch { message.error('操作失败') } }
async function loadHealth() { try { const r = await systemHealthCheck(); health.value = r.data } catch { message.error('检查失败') } }

loadSystemInfo()
</script>
