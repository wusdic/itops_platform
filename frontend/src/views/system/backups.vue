<template>
  <div>
    <div class="page-header"><h2>备份管理</h2><n-button type="primary" @click="handleCreate"><template #icon><n-icon><AddOutline /></n-icon></template>创建备份</n-button></div>
    <n-tabs v-model:value="activeTab">
      <n-tab-pane name="backups" tab="备份列表">
        <n-data-table :columns="columns" :data="backups" :pagination="pagination" :loading="loading" />
      </n-tab-pane>
      <n-tab-pane name="restores" tab="恢复记录">
        <n-data-table :columns="restoreColumns" :data="restores" :pagination="restorePagination" :loading="restoreLoading" />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>
<script setup>
import { ref, h } from 'vue'
import { useMessage, useDialog, NSpace, NButton, NIcon, NTag } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { getBackups, createBackup, deleteBackup, restoreBackup, getRestores, cleanupBackups } from '@/api/system'

const message = useMessage(), dialog = useDialog()
const loading = ref(false), restoreLoading = ref(false), backups = ref([]), restores = ref([]), activeTab = ref('backups')
const pagination = ref({ page:1, pageSize:20 }), restorePagination = ref({ page:1, pageSize:20 })

function renderType(t) { const m = {full:{type:'success',text:'全量'},incremental:{type:'info',text:'增量'}}; const c = m[t]||{type:'default',text:t}; return h(NTag,{type:c.type},{default:()=>c.text}) }
function renderStatus(s) { const m = {completed:{type:'success',text:'完成'},running:{type:'info',text:'执行中'},failed:{type:'error',text:'失败'}}; const c = m[s]||{type:'default',text:s}; return h(NTag,{type:c.type},{default:()=>c.text}) }

const columns = [
  {title:'备份ID',key:'id',width:80},{title:'类型',key:'type',width:80,render:r=>renderType(r.type)},{title:'状态',key:'status',width:80,render:r=>renderStatus(r.status)},
  {title:'大小',key:'size',width:100},{title:'创建时间',key:'created_at',width:170},
  {title:'操作',key:'actions',render:r=>h(NSpace,null,{default:()=>[
    h(NButton,{size:'small',onClick:()=>handleRestore(r.id)},{default:()=>'恢复'}),
    h(NButton,{size:'small',type:'error',onClick:()=>handleDelete(r.id)},{default:()=>'删除'})
  ]})}
]
const restoreColumns = [
  {title:'恢复ID',key:'id',width:80},{title:'备份ID',key:'backup_id',width:80},{title:'状态',key:'status',width:80,render:r=>renderStatus(r.status)},
  {title:'原因',key:'reason'},{title:'恢复时间',key:'created_at',width:170}
]

async function loadBackups() {
  loading.value = true
  try { const r = await getBackups({page:pagination.value.page,page_size:pagination.value.pageSize}); const items = r.data?.items||r.data||[]; backups.value = Array.isArray(items)?items:[]; pagination.value.itemCount = r.data?.total||items.length } catch { backups.value = [] } finally { loading.value = false }
}

async function loadRestores() {
  restoreLoading.value = true
  try { const r = await getRestores({page:restorePagination.value.page,page_size:restorePagination.value.pageSize}); const items = r.data?.items||r.data||[]; restores.value = Array.isArray(items)?items:[]; restorePagination.value.itemCount = r.data?.total||items.length } catch { restores.value = [] } finally { restoreLoading.value = false }
}

function handleCreate() { dialog.info({title:'创建备份',content:'确认创建新备份？',positiveText:'确认',onPositiveClick:()=>{createBackup({}).then(()=>{message.success('已创建');loadBackups()}).catch(()=>message.error('创建失败'))}}) }
function handleRestore(id) { dialog.warning({title:'恢复备份',content:'恢复将覆盖当前数据，确认？',positiveText:'恢复',onPositiveClick:()=>{restoreBackup(id,{}).then(()=>{message.success('恢复中');loadBackups()}).catch(()=>message.error('恢复失败'))}}) }
function handleDelete(id) { dialog.warning({title:'删除备份',content:'确认删除？',positiveText:'删除',onPositiveClick:()=>{deleteBackup(id).then(()=>{message.success('已删除');loadBackups()}).catch(()=>message.error('删除失败'))}}) }

pagination.value.onChange = p => { pagination.value.page = p; loadBackups() }
restorePagination.value.onChange = p => { restorePagination.value.page = p; loadRestores() }
loadBackups(); loadRestores()
</script>
