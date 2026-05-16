<template>
  <div>
    <div class="page-header">
      <h2>用户管理</h2>
      <n-button type="primary" @click="showModal=true;editId=null"><template #icon><n-icon><AddOutline /></n-icon></template>新建用户</n-button>
    </div>
    <n-space style="margin-bottom:16px"><n-input v-model:value="search" placeholder="搜索用户名" style="width:200px" @input="loadUsers" /><n-select v-model:value="roleFilter" :options="roleOptions" placeholder="角色筛选" style="width:160px" @update:value="loadUsers" /></n-space>
    <n-data-table :columns="columns" :data="users" :pagination="pagination" :loading="loading" />
    <n-modal v-model:show="showModal" preset="dialog" :title="editId?'编辑用户':'新建用户'" :style="{width:'500px'}">
      <n-form ref="formRef" :model="form" :rules="rules" label-width="80">
        <n-form-item label="用户名" path="username"><n-input v-model:value="form.username" :disabled="!!editId" /></n-form-item>
        <n-form-item label="密码" :path="editId?'':'password'"><n-input v-model:value="form.password" type="password" :placeholder="editId?'留空则不修改':'输入密码'" show-password-on="click" /></n-form-item>
        <n-form-item label="邮箱" path="email"><n-input v-model:value="form.email" /></n-form-item>
        <n-form-item label="全名" path="full_name"><n-input v-model:value="form.full_name" /></n-form-item>
        <n-form-item label="角色" path="role"><n-select v-model:value="form.role" :options="roleOptions" /></n-form-item>
      </n-form>
      <template #action><n-space><n-button @click="showModal=false">取消</n-button><n-button type="primary" :loading="submitting" @click="handleSubmit">保存</n-button></n-space></template>
    </n-modal>
  </div>
</template>
<script setup>
import { ref, h } from 'vue'
import { useMessage, useDialog, NSpace, NButton, NIcon, NTag } from 'naive-ui'
import { AddOutline, KeyOutline, TrashOutline } from '@vicons/ionicons5'
import { getUsers, createUser, updateUser, deleteUser, resetPassword, getRoles } from '@/api/system'

const message = useMessage(), dialog = useDialog()
const loading = ref(false), showModal = ref(false), submitting = ref(false), editId = ref(null), search = ref(''), roleFilter = ref(null)
const users = ref([]), roleOptions = ref([{label:'管理员',value:'admin'},{label:'运维',value:'operator'},{label:'只读',value:'viewer'}])
const formRef = ref(null)
const form = ref({ username:'', password:'', email:'', full_name:'', role:'operator' })
const rules = { username:{required:true,message:'请输入用户名',trigger:'blur'} }
const pagination = ref({ page:1, pageSize:20, showSizePicker:true, pageSizes:[10,20,50] })

const columns = [
  { title:'用户名', key:'username', width:120 },
  { title:'全名', key:'full_name', width:120 },
  { title:'邮箱', key:'email', width:180 },
  { title:'角色', key:'role', width:100, render:r=>h(NTag,{type:r.role==='admin'?'error':'info'},{default:()=>r.role}) },
  { title:'状态', key:'is_active', width:80, render:r=>h(NTag,{type:r.is_active?'success':'default'},{default:()=>r.is_active?'启用':'禁用'}) },
  { title:'创建时间', key:'created_at', width:170 },
  { title:'操作', key:'actions', width:180, render:r=>h(NSpace,null,{default:()=>[
    h(NButton,{size:'small',onClick:()=>handleEdit(r)},{default:()=>'编辑'}),
    h(NButton,{size:'small',onClick:()=>handleReset(r.id)},{default:()=>h(NIcon,null,{default:()=>h(KeyOutline)})}),
    h(NButton,{size:'small',type:'error',onClick:()=>handleDelete(r.id)},{default:()=>h(NIcon,null,{default:()=>h(TrashOutline)})})
  ]}) }
]

async function loadUsers() {
  loading.value = true
  try {
    const res = await getUsers({ page:pagination.value.page, page_size:pagination.value.pageSize, search:search.value, role:roleFilter.value })
    const items = res.data?.items || res.data || []
    users.value = Array.isArray(items) ? items : []
    pagination.value.itemCount = res.data?.total || items.length
  } catch { users.value = [] } finally { loading.value = false }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
    submitting.value = true
    if (editId.value) { await updateUser(editId.value, form.value); message.success('更新成功') }
    else { await createUser(form.value); message.success('创建成功') }
    showModal.value = false; form.value = {username:'',password:'',email:'',full_name:'',role:'operator'}; loadUsers()
  } catch { message.error('操作失败') } finally { submitting.value = false }
}

function handleEdit(r) { editId.value = r.id; form.value = { username:r.username, password:'', email:r.email, full_name:r.full_name, role:r.role }; showModal.value = true }
function handleReset(id) { dialog.warning({title:'重置密码',content:'确认重置该用户密码？',positiveText:'确认',onPositiveClick:()=>{resetPassword(id,{}).then(()=>message.success('密码已重置')).catch(()=>message.error('操作失败'))}}) }
function handleDelete(id) { dialog.warning({title:'确认删除',content:'删除后不可恢复',positiveText:'删除',onPositiveClick:()=>{deleteUser(id).then(()=>{message.success('已删除');loadUsers()}).catch(()=>message.error('删除失败'))}}) }

pagination.value.onChange = p => { pagination.value.page = p; loadUsers() }
pagination.value.onUpdatePageSize = ps => { pagination.value.pageSize = ps; pagination.value.page = 1; loadUsers() }
loadUsers()
</script>
