<template>
  <div>
    <div class="page-header"><h2>API密钥</h2><n-button type="primary" @click="showModal=true"><template #icon><n-icon><AddOutline /></n-icon></template>创建密钥</n-button></div>
    <n-alert type="warning" style="margin-bottom:16px">创建时请妥善保存密钥，关闭后将无法再次查看完整密钥</n-alert>
    <n-data-table :columns="columns" :data="keys" :pagination="pagination" :loading="loading" />
    <n-modal v-model:show="showModal" preset="dialog" title="创建API密钥" :style="{width:'500px'}">
      <n-form ref="formRef" :model="form" :rules="rules" label-width="80">
        <n-form-item label="名称" path="name"><n-input v-model:value="form.name" /></n-form-item>
        <n-form-item label="描述" path="description"><n-input v-model:value="form.description" type="textarea" /></n-form-item>
        <n-form-item label="过期时间" path="expires_at"><n-date-picker v-model:value="form.expires_at" type="datetime" style="width:100%" /></n-form-item>
      </n-form>
      <template #action><n-space><n-button @click="showModal=false">取消</n-button><n-button type="primary" :loading="submitting" @click="handleSubmit">创建</n-button></n-space></template>
    </n-modal>
    <n-modal v-model:show="showKeyModal" preset="dialog" title="API密钥" :style="{width:'600px'}">
      <n-alert type="success" style="margin-bottom:12px">请复制保存以下密钥，关闭后将无法再次查看</n-alert>
      <n-input v-model:value="newKeyText" readonly type="textarea" :rows="3" />
    </n-modal>
  </div>
</template>
<script setup>
import { ref, h } from 'vue'
import { useMessage, useDialog, NSpace, NButton, NIcon, NTag, NAlert } from 'naive-ui'
import { AddOutline, KeyOutline, BanOutline, SyncOutline, TrashOutline } from '@vicons/ionicons5'
import { getApiKeys, createApiKey, updateApiKey, deleteApiKey, revokeApiKey, activateApiKey, rotateApiKey } from '@/api/system'

const message = useMessage(), dialog = useDialog()
const loading = ref(false), showModal = ref(false), showKeyModal = ref(false), submitting = ref(false)
const keys = ref([]), newKeyText = ref('')
const formRef = ref(null), form = ref({ name:'', description:'', expires_at:null })
const rules = { name:{required:true,message:'请输入名称',trigger:'blur'} }
const pagination = ref({ page:1, pageSize:20 })

function renderStatus(s) { const m = {active:{type:'success',text:'激活'},revoked:{type:'error',text:'已撤销'},expired:{type:'warning',text:'已过期'}}; const c = m[s]||{type:'default',text:s}; return h(NTag,{type:c.type},{default:()=>c.text}) }

const columns = [
  {title:'名称',key:'name'},{title:'描述',key:'description'},{title:'密钥(部分)',key:'masked_key',width:160},
  {title:'状态',key:'status',width:80,render:r=>renderStatus(r.status)},{title:'过期时间',key:'expires_at',width:170},{title:'创建时间',key:'created_at',width:170},
  {title:'操作',key:'actions',render:r=>h(NSpace,null,{default:()=>[
    h(NButton,{size:'small',onClick:()=>handleRevoke(r.id),disabled:r.status==='revoked'},{default:()=>h(NIcon,null,{default:()=>h(BanOutline)})}),
    h(NButton,{size:'small',onClick:()=>handleActivate(r.id),disabled:r.status==='active'},{default:()=>h(NIcon,null,{default:()=>h(KeyOutline)})}),
    h(NButton,{size:'small',onClick:()=>handleRotate(r.id)},{default:()=>h(NIcon,null,{default:()=>h(SyncOutline)})}),
    h(NButton,{size:'small',type:'error',onClick:()=>handleDelete(r.id)},{default:()=>h(NIcon,null,{default:()=>h(TrashOutline)})})
  ]})}
]

async function loadKeys() {
  loading.value = true
  try { const r = await getApiKeys({page:pagination.value.page,page_size:pagination.value.pageSize}); const items = r.data?.items||r.data||[]; keys.value = Array.isArray(items)?items:[]; pagination.value.itemCount = r.data?.total||items.length } catch { keys.value = [] } finally { loading.value = false }
}

async function handleSubmit() {
  try { await formRef.value?.validate(); submitting.value = true; const r = await createApiKey(form.value); newKeyText.value = r.data?.key || r.data?.api_key || '获取失败'; showKeyModal.value = true; showModal.value = false; message.success('创建成功'); loadKeys() } catch { message.error('创建失败') } finally { submitting.value = false }
}

function handleRevoke(id) { dialog.warning({title:'撤销密钥',positiveText:'确认',onPositiveClick:()=>{revokeApiKey(id).then(()=>{message.success('已撤销');loadKeys()}).catch(()=>message.error('操作失败'))}}) }
function handleActivate(id) { activateApiKey(id).then(()=>{message.success('已激活');loadKeys()}).catch(()=>message.error('操作失败')) }
function handleRotate(id) { dialog.warning({title:'轮换密钥',content:'旧密钥将失效',positiveText:'确认',onPositiveClick:()=>{rotateApiKey(id).then(r=>{newKeyText.value = r.data?.key||r.data?.api_key||'获取失败';showKeyModal.value=true;loadKeys()}).catch(()=>message.error('操作失败'))}}) }
function handleDelete(id) { dialog.warning({title:'删除密钥',positiveText:'删除',onPositiveClick:()=>{deleteApiKey(id).then(()=>{message.success('已删除');loadKeys()}).catch(()=>message.error('删除失败'))}}) }

pagination.value.onChange = p => { pagination.value.page = p; loadKeys() }
loadKeys()
</script>
