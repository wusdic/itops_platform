<template>
  <div>
    <div class="page-header">
      <h2>定时任务</h2>
      <n-button type="primary" @click="showModal=true"><template #icon><n-icon><AddOutline /></n-icon></template>新建任务</n-button>
    </div>
    <n-data-table :columns="columns" :data="tasks" :pagination="pagination" :loading="loading" />
    <n-modal v-model:show="showModal" preset="dialog" title="创建定时任务" :style="{ width: '600px' }">
      <n-form ref="formRef" :model="form" :rules="rules" label-width="80">
        <n-form-item label="任务名称" path="name"><n-input v-model:value="form.name" placeholder="输入任务名称" /></n-form-item>
        <n-form-item label="Cron表达式" path="cron"><n-input v-model:value="form.cron" placeholder="如 0 * * * *" /></n-form-item>
        <n-form-item label="任务类型" path="task_type">
          <n-select v-model:value="form.task_type" :options="[
            {label:'设备采集',value:'collect'},{label:'报表生成',value:'report'},{label:'备份',value:'backup'},{label:'巡检',value:'inspection'},{label:'清理',value:'cleanup'}
          ]" />
        </n-form-item>
        <n-form-item label="目标" path="target"><n-input v-model:value="form.target" placeholder="设备组/全部" /></n-form-item>
        <n-form-item label="参数" path="params"><n-input v-model:value="form.params" type="textarea" placeholder="JSON参数" /></n-form-item>
      </n-form>
      <template #action>
        <n-space><n-button @click="showModal=false">取消</n-button><n-button type="primary" :loading="submitting" @click="handleSubmit">创建</n-button></n-space>
      </template>
    </n-modal>
  </div>
</template>
<script setup>
import { ref, h } from 'vue'
import { useMessage, useDialog, NTag, NSpace, NButton, NIcon } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { getTasks, createTask, deleteTask, toggleTask, executeTask } from '@/api/scheduler'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const showModal = ref(false)
const submitting = ref(false)
const tasks = ref([])
const formRef = ref(null)
const form = ref({ name:'', cron:'', task_type:'', target:'', params:'' })
const rules = { name:{required:true,message:'请输入名称',trigger:'blur'}, cron:{required:true,message:'请输入Cron表达式',trigger:'blur'} }
const pagination = ref({ page:1, pageSize:20, showSizePicker:true, pageSizes:[10,20,50] })

function renderStatus(s) {
  const map = { enabled:{type:'success',text:'启用'}, disabled:{type:'default',text:'禁用'}, running:{type:'info',text:'执行中'} }
  const c = map[s] || {type:'default',text:s}
  return h(NTag,{type:c.type},{default:()=>c.text})
}

const columns = [
  { title:'任务名称', key:'name' },
  { title:'Cron', key:'cron', width:120 },
  { title:'类型', key:'task_type', width:100 },
  { title:'目标', key:'target', width:120 },
  { title:'状态', key:'status', width:80, render:row=>renderStatus(row.status) },
  { title:'上次执行', key:'last_run_at', width:170 },
  { title:'下次执行', key:'next_run_at', width:170 },
  { title:'操作', key:'actions', width:200, render:row=>h(NSpace,null,{default:()=>[
    h(NButton,{size:'small',onClick:()=>handleToggle(row)},{default:()=>row.status==='enabled'?'禁用':'启用'}),
    h(NButton,{size:'small',onClick:()=>handleExecute(row)},{default:()=>h(NIcon,null,{default:()=>h(AddOutline)})}),
    h(NButton,{size:'small',type:'error',onClick:()=>handleDelete(row.id)},{default:()=>'删除'})
  ]}) }
]

async function loadTasks() {
  loading.value = true
  try {
    const res = await getTasks({ page:pagination.value.page, page_size:pagination.value.pageSize })
    const items = res.data?.items || res.data || []
    tasks.value = Array.isArray(items) ? items : []
    pagination.value.itemCount = res.data?.total || items.length
  } catch { tasks.value = [] } finally { loading.value = false }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
    submitting.value = true
    await createTask(form.value)
    message.success('创建成功')
    showModal.value = false
    form.value = {name:'',cron:'',task_type:'',target:'',params:''}
    loadTasks()
  } catch { message.error('创建失败') } finally { submitting.value = false }
}

function handleToggle(row) { toggleTask(row.id).then(()=>{message.success('已切换');loadTasks()}).catch(()=>message.error('操作失败')) }
function handleExecute(id) { executeTask(id).then(()=>message.success('已触发执行')).catch(()=>message.error('触发失败')) }
function handleDelete(id) { dialog.warning({title:'确认删除',content:'删除后不可恢复',positiveText:'删除',onPositiveClick:()=>{deleteTask(id).then(()=>{message.success('已删除');loadTasks()}).catch(()=>message.error('删除失败'))}}) }

pagination.value.onChange = (p) => { pagination.value.page = p; loadTasks() }
pagination.value.onUpdatePageSize = (ps) => { pagination.value.pageSize = ps; pagination.value.page = 1; loadTasks() }

loadTasks()
</script>
