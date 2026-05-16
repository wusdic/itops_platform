<template>
  <div>
    <div class="page-header"><h2>操作日志</h2></div>
    <n-space style="margin-bottom:16px">
      <n-input v-model:value="filters.user" placeholder="操作人" style="width:140px" />
      <n-select v-model:value="filters.action" :options="[{label:'创建',value:'create'},{label:'更新',value:'update'},{label:'删除',value:'delete'},{label:'登录',value:'login'}]" placeholder="操作类型" style="width:120px" clearable />
      <n-select v-model:value="filters.module" :options="[{label:'资产',value:'asset'},{label:'设备',value:'device'},{label:'告警',value:'alert'},{label:'工单',value:'workorder'},{label:'系统',value:'system'}]" placeholder="模块" style="width:120px" clearable />
      <n-date-picker v-model:value="filters.dateRange" type="daterange" style="width:240px" />
      <n-button type="primary" @click="loadLogs">查询</n-button>
    </n-space>
    <n-data-table :columns="columns" :data="logs" :pagination="pagination" :loading="loading" />
  </div>
</template>
<script setup>
import { ref, h } from 'vue'
import { NSpace, NTag } from 'naive-ui'
import { getOperationLogs } from '@/api/system'

const loading = ref(false), logs = ref([]), filters = ref({ user:'', action:'', module:'', dateRange:null })
const pagination = ref({ page:1, pageSize:20, showSizePicker:true, pageSizes:[10,20,50] })

function renderAction(a) { const m = {create:'success',update:'info',delete:'error',login:'warning'}; return h(NTag,{type:m[a]||'default'},{default:()=>a||'-'}) }

const columns = [
  {title:'ID',key:'id',width:60},{title:'操作人',key:'user',width:120},{title:'操作',key:'action',width:80,render:r=>renderAction(r.action)},
  {title:'模块',key:'module',width:100},{title:'描述',key:'description'},{title:'IP',key:'ip_address',width:130},
  {title:'时间',key:'created_at',width:170}
]

async function loadLogs() {
  loading.value = true
  try {
    const params = { page:pagination.value.page, page_size:pagination.value.pageSize, ...filters.value }
    const res = await getOperationLogs(params)
    const items = res.data?.items || res.data || []
    logs.value = Array.isArray(items) ? items : []
    pagination.value.itemCount = res.data?.total || items.length
  } catch { logs.value = [] } finally { loading.value = false }
}

pagination.value.onChange = p => { pagination.value.page = p; loadLogs() }
pagination.value.onUpdatePageSize = ps => { pagination.value.pageSize = ps; pagination.value.page = 1; loadLogs() }
loadLogs()
</script>
