<template>
  <div>
    <div class="page-header">
      <h2>角色管理</h2>
      <n-button type="primary" @click="openCreate"><template #icon><n-icon><AddOutline /></n-icon></template>新建角色</n-button>
    </div>
    <n-data-table :columns="columns" :data="roles" :loading="loading" />
    <n-modal v-model:show="showModal" preset="dialog" :title="editId ? '编辑角色' : '新建角色'" :style="{ width: '600px' }">
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" label-width="80">
        <n-form-item label="角色名称" path="name"><n-input v-model:value="form.name" /></n-form-item>
        <n-form-item label="描述" path="description"><n-input v-model:value="form.description" type="textarea" /></n-form-item>
        <n-form-item label="权限" path="permissions">
          <n-checkbox-group v-model:value="form.permissions">
            <n-grid :cols="3" :x-gap="8" :y-gap="8">
              <n-gi v-for="p in allPermissions" :key="p">
                <n-checkbox :value="p">{{ p }}</n-checkbox>
              </n-gi>
            </n-grid>
          </n-checkbox-group>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { NSpace, NButton, NIcon, NTag, NCheckboxGroup, NCheckbox, NGrid, NGi, NDataTable } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { getRoles, createRole, updateRole, deleteRole, getPermissions } from '@/api/system'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const showModal = ref(false)
const submitting = ref(false)
const editId = ref(null)
const roles = ref([])
const allPermissions = ref([])
const formRef = ref(null)
const form = ref({ name: '', description: '', permissions: [] })
const rules = { name: { required: true, message: '请输入角色名称', trigger: 'blur' } }

const columns = [
  { title: '角色名称', key: 'name' },
  { title: '描述', key: 'description' },
  {
    title: '权限数', key: 'permissions', width: 100,
    render: (r) => h(NTag, { type: 'info' }, { default: () => Array.isArray(r.permissions) ? r.permissions.length : 0 })
  },
  {
    title: '操作', key: 'actions', width: 150,
    render: (r) => h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openEdit(r) }, { default: () => '编辑' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => doDelete(r.id) }, { default: () => '删除' })
      ]
    })
  }
]

async function loadData() {
  loading.value = true
  try {
    const results = await Promise.allSettled([getRoles(), getPermissions()])
    if (results[0].status === 'fulfilled') roles.value = results[0].value.data || []
    if (results[1].status === 'fulfilled') allPermissions.value = results[1].value.data || []
  } catch {
    roles.value = []
    allPermissions.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editId.value = null
  form.value = { name: '', description: '', permissions: [] }
  showModal.value = true
}

function openEdit(r) {
  editId.value = r.id
  form.value = { name: r.name, description: r.description || '', permissions: r.permissions || [] }
  showModal.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
    submitting.value = true
    if (editId.value) {
      await updateRole(editId.value, form.value)
      message.success('更新成功')
    } else {
      await createRole(form.value)
      message.success('创建成功')
    }
    showModal.value = false
    loadData()
  } catch (e) {
    if (e?.message) return
    message.error('操作失败')
  } finally {
    submitting.value = false
  }
}

function doDelete(id) {
  dialog.warning({
    title: '确认删除',
    content: '删除后不可恢复',
    positiveText: '删除',
    onPositiveClick: () => {
      deleteRole(id)
        .then(() => { message.success('已删除'); loadData() })
        .catch(() => message.error('删除失败'))
    }
  })
}

loadData()
</script>
